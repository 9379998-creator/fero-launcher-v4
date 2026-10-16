"""
Тесты для модуля volume_engine.py (Шаг 2 дорожной карты).
Проверяют:
1. Вычисление площади полигонов по формуле Гаусса (Shoelace) и периметра.
2. Автоматическое определение формата листа (A0..A4) по размерам в пунктах.
3. Поиск масштаба в тексте штампа (1:200, 1:100, 1:50).
4. Расчет калибровочных коэффициентов k (м/pt) и k^2 (м^2/pt^2).
5. Классификацию слоев по фасадным категориям.
6. Расчет дельты и сходимости (Reconciliation) с определением принятого объема.
7. Идемпотентное сохранение и извлечение сверок из SQLite.
8. Сквозное извлечение геометрии из синтетического PDF через fitz.
"""

from __future__ import annotations

import math
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.backend import db
from app.backend.volume_engine import (
    MM_PER_PT,
    PdfVolumeExtractor,
    calculate_calibration,
    classify_layer,
    compute_polygon_area,
    compute_polygon_perimeter,
    compute_reconciliation_row,
    detect_paper_format,
    detect_scale_from_text,
    get_reconciliations_from_db,
    save_reconciliations_to_db,
)


class TestGeometryMath(unittest.TestCase):
    """Тесты математики контуров (Гаусс / Shoelace)."""

    def test_shoelace_square(self):
        # Квадрат 100 x 100 пунктов
        square = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
        area = compute_polygon_area(square)
        self.assertAlmostEqual(area, 10000.0, places=3)
        perim = compute_polygon_perimeter(square)
        self.assertAlmostEqual(perim, 400.0, places=3)

    def test_shoelace_triangle(self):
        # Прямоугольный треугольник катеты 30 и 40, гипотенуза 50
        triangle = [(0.0, 0.0), (30.0, 0.0), (0.0, 40.0)]
        area = compute_polygon_area(triangle)
        self.assertAlmostEqual(area, 600.0, places=3)
        perim = compute_polygon_perimeter(triangle)
        self.assertAlmostEqual(perim, 120.0, places=3)

    def test_shoelace_degenerate(self):
        self.assertEqual(compute_polygon_area([]), 0.0)
        self.assertEqual(compute_polygon_area([(1.0, 1.0)]), 0.0)
        self.assertEqual(compute_polygon_area([(1.0, 1.0), (2.0, 2.0)]), 0.0)


class TestCalibration(unittest.TestCase):
    """Тесты калибровки и определения форматов листов."""

    def test_detect_paper_format_a2(self):
        # A2: 594 x 420 мм -> в пунктах ~ 1683.78 x 1190.55
        w_pt = 594.0 / MM_PER_PT
        h_pt = 420.0 / MM_PER_PT
        fmt, w_mm, h_mm, delta = detect_paper_format(w_pt, h_pt)
        self.assertEqual(fmt, "A2")
        self.assertAlmostEqual(w_mm, 594.0, delta=1.0)
        self.assertAlmostEqual(h_mm, 420.0, delta=1.0)
        self.assertLess(delta, 1.0)

    def test_detect_paper_format_a1(self):
        # A1: 841 x 594 мм
        w_pt = 841.0 / MM_PER_PT
        h_pt = 594.0 / MM_PER_PT
        fmt, _, _, _ = detect_paper_format(w_pt, h_pt)
        self.assertEqual(fmt, "A1")

    def test_detect_scale_from_text(self):
        self.assertEqual(detect_scale_from_text("Фасад в осях 1-8. Масштаб 1:200. Лист 4"), 200)
        self.assertEqual(detect_scale_from_text("Разрез 1-1 М 1:100 ГАП Иванов"), 100)
        self.assertEqual(detect_scale_from_text("Узел примыкания парапета М 1:20"), 20)
        self.assertIsNone(detect_scale_from_text("Просто текст без масштаба"))

    def test_calculate_calibration_ready(self):
        # Масштаб 1:200 на листе A2
        w_pt = 594.0 / MM_PER_PT
        h_pt = 420.0 / MM_PER_PT
        text = "Лист 4. Фасад в осях 1-8. Масштаб 1:200"

        calib = calculate_calibration(None, w_pt, h_pt, text)
        self.assertEqual(calib.status, "ready")
        self.assertEqual(calib.scale, 200)
        self.assertEqual(calib.detected_format, "A2")
        # k = 200 * 0.352777778 / 1000 = 0.070555556
        self.assertAlmostEqual(calib.k_m_per_pt, 0.070555, places=4)
        # k^2 ~ 0.004978
        self.assertAlmostEqual(calib.k2_m2_per_pt2, 0.004978, places=5)

    def test_calculate_calibration_pending(self):
        w_pt = 500.0
        h_pt = 500.0
        text = "Штамп без масштаба"

        calib = calculate_calibration(None, w_pt, h_pt, text)
        self.assertEqual(calib.status, "pending_calibration")
        self.assertIsNotNone(calib.warning)


class TestLayerClassification(unittest.TestCase):
    """Тесты классификации слоев чертежа."""

    def test_layer_patterns(self):
        cat, _, code = classify_layer("2_ Витражи")
        self.assertEqual(cat, "glazing_spd")
        self.assertEqual(code, "1.2")

        cat, _, code = classify_layer("2_Фасад")
        self.assertEqual(cat, "facade_panels")
        self.assertEqual(code, "2.3")

        cat, _, code = classify_layer("2_ Утеплитель")
        self.assertEqual(cat, "insulation")
        self.assertEqual(code, "2.2")

        cat, _, code = classify_layer("3_ Ограждение_кровля")
        self.assertEqual(cat, "roof_fencing")
        self.assertEqual(code, "4.2")

        cat, _, code = classify_layer("11I К_Кровельные отливы")
        self.assertEqual(cat, "roof_flashing")
        self.assertEqual(code, "4.1")

        cat, _, code = classify_layer("3_ Козырек")
        self.assertEqual(cat, "canopy")
        self.assertEqual(code, "3.4")

        cat, _, code = classify_layer("НеизвестныйСлой")
        self.assertEqual(cat, "other")
        self.assertEqual(code, "9.9")


class TestReconciliationMath(unittest.TestCase):
    """Тесты сверки объемов (Reconciliation)."""

    def test_reconciliation_row_calculation(self):
        # Эталонный кейс: PDF = 5980 м², DWG = 6159.5 м² -> Дельта +179.5 м², сходимость 97.1%
        row = compute_reconciliation_row(
            item_code="1.2",
            category_name="I. СВЕТОПРОЗРАЧНЫЕ КОНСТРУКЦИИ",
            element_name="Витражное остекление (СПД)",
            unit="м²",
            pdf_volume=5980.0,
            dwg_volume=6159.5,
            engineering_note="Технологический нахлест под парапеты и узлы примыкания",
        )
        self.assertEqual(row["delta_volume"], 179.5)
        self.assertEqual(row["convergence_pct"], 97.1)
        self.assertEqual(row["accepted_volume"], 6159.5)

    def test_reconciliation_db_persistence(self):
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test_rec.sqlite"

        orig_path = db.DB_PATH
        orig_dir = db.DB_DIR
        db.DB_PATH = db_path
        db.DB_DIR = db_path.parent

        try:
            db.init_db()
            conn = db.get_connection()
            try:
                # Создаем тестовый объект
                conn.execute("INSERT INTO roots (path, is_active) VALUES ('/test/project', 1)")
                conn.commit()
                root_id = conn.execute("SELECT id FROM roots WHERE path = '/test/project'").fetchone()[0]

                rows = [
                    compute_reconciliation_row("1.2", "I. СПК", "Витражное остекление", "м²", 1956.0, 2000.0),
                    compute_reconciliation_row("2.3", "II. НВФ", "Фибробетон", "м²", 669.0, 680.0),
                ]

                saved = save_reconciliations_to_db(conn, root_id, rows)
                self.assertEqual(saved, 2)

                # Чтение из базы
                loaded = get_reconciliations_from_db(conn, root_id)
                self.assertEqual(len(loaded), 2)
                self.assertEqual(loaded[0]["item_code"], "1.2")
                self.assertEqual(loaded[0]["accepted_volume"], 2000.0)

                # Повторный запуск обновляет строки (идемпотентность)
                rows[0]["pdf_volume"] = 1960.0
                save_reconciliations_to_db(conn, root_id, rows)
                loaded2 = get_reconciliations_from_db(conn, root_id)
                self.assertEqual(len(loaded2), 2)
                self.assertEqual(loaded2[0]["pdf_volume"], 1960.0)
            finally:
                conn.close()
        finally:
            db.DB_PATH = orig_path
            db.DB_DIR = orig_dir
            temp_dir.cleanup()


class TestSyntheticPdfExtraction(unittest.TestCase):
    """Сквозной тест извлечения векторов из синтетического PDF."""

    def test_extract_vectors_from_pdf(self):
        import fitz

        temp_dir = tempfile.TemporaryDirectory()
        pdf_path = Path(temp_dir.name) / "test_sheet.pdf"

        # Создаем PDF лист формата A2 (1684 x 1191 pt)
        doc = fitz.open()
        page = doc.new_page(width=1684, height=1191)

        # Пишем штамп
        page.insert_text((100, 100), "Фасад в осях 1-8. Масштаб 1:200", fontsize=14)

        # Рисуем фигуру (прямоугольник 200 x 100 пунктов)
        # При масштабе 1:200, 1 pt = 0.070555 м.
        # Ширина: 200 * 0.070555 = 14.11 м
        # Высота: 100 * 0.070555 = 7.05 м
        # Ожидаемая площадь ~ 99.56 м²
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(200, 200, 400, 300))
        shape.finish(fill=(0.2, 0.4, 0.8), color=(0, 0, 0))
        shape.commit()

        doc.save(str(pdf_path))
        doc.close()

        # Извлекаем геометрию через PdfVolumeExtractor
        extractor = PdfVolumeExtractor()
        res = extractor.extract_from_file(pdf_path)

        self.assertEqual(res["pages_count"], 1)
        page_info = res["pages"][0]
        self.assertEqual(page_info["calibration"]["status"], "ready")
        self.assertEqual(page_info["calibration"]["scale"], 200)
        self.assertEqual(page_info["calibration"]["detected_format"], "A2")
        self.assertGreaterEqual(page_info["elements_count"], 1)

        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
