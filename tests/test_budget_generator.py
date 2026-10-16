"""
Тесты для модуля budget_generator.py (Шаг 3 дорожной карты).
Проверяют:
1. Расчет сметы по принятым объемам (volume_reconciliations) и расценкам (unit_rates).
2. Расчет долей материалов, СМР, НДС 22% и удельной цены за 1 м².
3. Сохранение сметы и ее строк в таблицы estimates и estimate_rows.
4. Экспорт сметы в CSV с разделителем ';' и UTF-8 BOM.
5. Генерацию интерактивного HTML-паспорта фасадов.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.backend import db
from app.backend.budget_generator import (
    calculate_estimate_for_root,
    export_estimate_to_csv,
    generate_facade_passport_html,
)
from app.backend.volume_engine import (
    compute_reconciliation_row,
    save_reconciliations_to_db,
)
from scripts.import_unit_rates import parse_rates_csv, upsert_rates

SAMPLE_RATES_CSV = (
    "\ufeff"
    "№;Наименование работ и конструкций;Спецификация и марка материала;Ед. изм.;"
    "Объем по проекту (DWG);Цена Материалы без НДС (руб./ед.);"
    "Цена СМР / Монтаж без НДС (руб./ед.);Итого расценка без НДС (руб./ед.);"
    "Итого расценка с НДС 22% (руб./ед.);Стоимость Материалы без НДС (руб.);"
    "Стоимость СМР без НДС (руб.);ИТОГО Стоимость без НДС (руб.);"
    "ИТОГО Стоимость с НДС 22% (руб.)\n"
    '"1.1";"Монтаж каркаса витражей";"Теплая система";"м²";7642.0;27799;12741;40540;49459;0;0;0;0\n'
    '"1.2";"Витражное остекление СПД";"Двухкамерный СПД";"м²";6159.5;18500;7500;26000;31720;0;0;0;0\n'
    '"2.1";"Подсистема вентфасада";"Алюминий";"м²";2100.0;4500;3200;7700;9394;0;0;0;0\n'
    '"3.4";"Стеклянные козырьки";"Триплекс";"шт.";6;42430;10729;53159;64854;0;0;0;0\n'
)


class TestBudgetGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_budget.sqlite"
        self.orig_path = db.DB_PATH
        self.orig_dir = db.DB_DIR
        db.DB_PATH = self.db_path
        db.DB_DIR = self.db_path.parent

        db.init_db()
        self.conn = db.get_connection()

        # Создаем тестовый объект
        self.conn.execute("INSERT INTO roots (path, is_active) VALUES ('/test/facade_root', 1)")
        self.conn.commit()
        self.root_id = self.conn.execute("SELECT id FROM roots WHERE path = '/test/facade_root'").fetchone()[0]

        # Наполняем unit_rates
        rates = parse_rates_csv(SAMPLE_RATES_CSV)
        upsert_rates(self.conn, rates, "2026-10-16")

        # Наполняем volume_reconciliations
        rec_rows = [
            compute_reconciliation_row("1.1", "I. СПК", "Монтаж каркаса витражей", "м²", 7400.0, 7642.0),
            compute_reconciliation_row("1.2", "I. СПК", "Витражное остекление СПД", "м²", 6000.0, 6159.5),
            compute_reconciliation_row("2.1", "II. НВФ", "Подсистема вентфасада", "м²", 2050.0, 2100.0),
            compute_reconciliation_row("3.4", "III. Двери и козырьки", "Стеклянные козырьки", "шт.", 6, 6),
        ]
        save_reconciliations_to_db(self.conn, self.root_id, rec_rows)

    def tearDown(self):
        self.conn.close()
        db.DB_PATH = self.orig_path
        db.DB_DIR = self.orig_dir
        self.temp_dir.cleanup()

    def test_calculate_estimate(self):
        est = calculate_estimate_for_root(self.conn, self.root_id, "Тестовый первоначальный бюджет")

        self.assertIsNotNone(est["estimate_id"])
        self.assertEqual(est["name"], "Тестовый первоначальный бюджет")
        self.assertGreater(est["total_materials_no_vat"], 0.0)
        self.assertGreater(est["total_smr_no_vat"], 0.0)
        self.assertGreater(est["total_cost_with_vat"], est["total_cost_no_vat"])
        self.assertAlmostEqual(est["total_cost_with_vat"], est["total_cost_no_vat"] * 1.22, places=1)
        self.assertGreater(est["avg_price_per_m2"], 0.0)

        # Проверка записей в SQLite
        cur = self.conn.cursor()
        saved_est = cur.execute("SELECT id, total_cost_with_vat FROM estimates WHERE id = ?", (est["estimate_id"],)).fetchone()
        self.assertIsNotNone(saved_est)
        self.assertEqual(saved_est["total_cost_with_vat"], est["total_cost_with_vat"])

        rows_count = cur.execute("SELECT COUNT(*) FROM estimate_rows WHERE estimate_id = ?", (est["estimate_id"],)).fetchone()[0]
        self.assertEqual(rows_count, 4)

    def test_export_estimate_to_csv(self):
        est = calculate_estimate_for_root(self.conn, self.root_id)
        csv_text = export_estimate_to_csv(est)

        self.assertTrue(csv_text.startswith("\ufeff"), "CSV должен содержать UTF-8 BOM для Excel")
        self.assertIn("1.1", csv_text)
        self.assertIn("6159.5", csv_text)
        self.assertIn("ИТОГО ПО ОБЪЕКТУ:", csv_text)

    def test_generate_html_passport(self):
        est = calculate_estimate_for_root(self.conn, self.root_id)
        recs = self.conn.execute("SELECT * FROM volume_reconciliations WHERE root_id = ?", (self.root_id,)).fetchall()
        recs_list = [dict(r) for r in recs]

        html = generate_facade_passport_html("БЦ на Энгельса", est, recs_list)
        self.assertIn("<!doctype html>", html)
        self.assertIn("БЦ на Энгельса", html)
        self.assertIn("tab-reconcile", html)
        self.assertIn("tab-estimate", html)
        self.assertIn("85 000 ₽/м²", html)
        self.assertIn("87 500 ₽/м²", html)


if __name__ == "__main__":
    unittest.main()
