"""Тесты Шага 1: миграция схемы БД и импорт единичных расценок.

Проверяется:
1. Чистая база получает целевую схему (volume_reconciliations, unit_rates в новой схеме).
2. Миграция идемпотентна: повторный запуск не меняет схему и не дублирует записи.
3. Существующие данные (roots/documents) не теряются: только ADD COLUMN.
4. Legacy-таблица unit_rates: пустая пересоздаётся, заполненная расширяется без потери строк.
5. Разбор ведомости расценок: BOM, разделитель ';', кавычки, пробелы/запятые в числах.
6. Импорт расценок идемпотентен (повторный импорт обновляет, а не дублирует).
"""

from __future__ import annotations

import csv
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend import db
from scripts.import_unit_rates import (
    SECTION_CATEGORIES,
    _category_for,
    _to_float,
    parse_rates_csv,
    upsert_rates,
)

SAMPLE_CSV = (
    "\ufeff"
    "№;Наименование работ и конструкций;Спецификация и марка материала;Ед. изм.;"
    "Объем по проекту (DWG);Цена Материалы без НДС (руб./ед.);"
    "Цена СМР / Монтаж без НДС (руб./ед.);Итого расценка без НДС (руб./ед.);"
    "Итого расценка с НДС 22% (руб./ед.);Стоимость Материалы без НДС (руб.);"
    "Стоимость СМР без НДС (руб.);ИТОГО Стоимость без НДС (руб.);"
    "ИТОГО Стоимость с НДС 22% (руб.)\n"
    "\n"
    '"1.1";"Монтаж стоечно-ригельного каркаса витражей";"Теплая система";"м²";7642.0;27799;12741;'
    '40540;49459;212439958;97366722;309806680;377964150\n'
    "\n"
    '"2.2";"Монтаж минераловатного утеплителя; в 2 слоя";"Базальтовая вата";"м²";3130.4;'
    '"4 828";"2 179";7007;8549;15113571;6821142;21934713;26760350\n'
    "\n"
    '"3.4";"Монтаж подвесных стеклянных козырьков над входами";"Стекло";"шт.";6;42430;10729;'
    '53159;64854;254580;64374;318954;388848\n'
)

LEGACY_UNIT_RATES_DDL = """
    CREATE TABLE unit_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_category TEXT NOT NULL,
        material_name TEXT NOT NULL,
        unit_type TEXT NOT NULL,
        price_per_unit REAL NOT NULL,
        updated_at TEXT NOT NULL
    )
"""


class TestSchemaMigration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_launcher.sqlite"
        self.original_db_path = db.DB_PATH
        self.original_db_dir = db.DB_DIR
        db.DB_PATH = self.db_path
        db.DB_DIR = self.db_path.parent

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        db.DB_DIR = self.original_db_dir
        self.temp_dir.cleanup()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _columns(self, table):
        conn = self._connect()
        try:
            return {row[1] for row in conn.execute('PRAGMA table_info("%s")' % table)}
        finally:
            conn.close()

    def _tables(self):
        conn = self._connect()
        try:
            return {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_fresh_database_gets_target_schema(self):
        db.init_db()

        tables = self._tables()
        for table in ("roots", "documents", "parsed_elements", "unit_rates",
                      "volume_reconciliations", "estimates", "estimate_rows", "schema_version"):
            self.assertIn(table, tables, "нет таблицы %s" % table)

        self.assertTrue({"project_name", "address", "client", "total_facade_area_m2"}
                        <= self._columns("roots"))
        self.assertIn("facade_orientation", self._columns("documents"))
        self.assertTrue({"source_type", "layer", "material_category", "raw_value",
                         "raw_units", "normalized_value", "review_status"}
                        <= self._columns("parsed_elements"))
        self.assertTrue({"item_code", "category", "work_name", "material_specification",
                         "material_price_no_vat", "smr_price_no_vat"}
                        <= self._columns("unit_rates"))
        self.assertTrue({"root_id", "item_code", "pdf_volume", "dwg_volume", "delta_volume",
                         "convergence_pct", "accepted_volume"}
                        <= self._columns("volume_reconciliations"))
        self.assertTrue({"root_id", "total_materials_no_vat", "vat_22",
                         "total_cost_with_vat", "avg_price_per_m2"}
                        <= self._columns("estimates"))

    def test_migration_is_idempotent(self):
        db.init_db()
        conn = self._connect()
        try:
            first = db.migrate_schema(conn)
            second = db.migrate_schema(conn)
        finally:
            conn.close()

        self.assertEqual(sum(len(v) for v in second["added_columns"].values()), 0,
                         "повторная миграция добавила колонки: %s" % second["added_columns"])
        self.assertEqual(second["created_tables"], [])
        self.assertEqual(first["schema_version"], db.SCHEMA_VERSION)

        conn = self._connect()
        try:
            versions = conn.execute(
                "SELECT COUNT(*) FROM schema_version WHERE version = ?",
                (db.SCHEMA_VERSION,)).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(versions, 1, "версия схемы записана более одного раза")

    def test_existing_rows_are_preserved(self):
        # Имитируем боевую базу: roots/documents уже заполнены в старой схеме.
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE roots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                );
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_id INTEGER NOT NULL,
                    rel_path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    observed_revision INTEGER NOT NULL DEFAULT 1,
                    hash_state TEXT NOT NULL DEFAULT 'pending',
                    verified_content_hash TEXT,
                    UNIQUE (root_id, rel_path)
                );
            """)
            conn.execute("INSERT INTO roots (path, is_active) VALUES (?, 1)",
                         (r"G:\Общие диски\024_TD_Okna",))
            root_id = conn.execute("SELECT id FROM roots").fetchone()[0]
            for index in range(25):
                conn.execute(
                    "INSERT INTO documents (root_id, rel_path, name, ext, size, mtime_ns) "
                    "VALUES (?, ?, ?, 'DWG', 100, 123456789)", (root_id, "obj/%d.dwg" % index,
                                                                "%d.dwg" % index))
            conn.commit()
        finally:
            conn.close()

        db.init_db()

        conn = self._connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM roots").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 25)
            row = conn.execute(
                "SELECT project_name, total_facade_area_m2 FROM roots").fetchone()
            self.assertIsNone(row["project_name"])
            self.assertEqual(row["total_facade_area_m2"], 0.0)
            self.assertIsNone(conn.execute(
                "SELECT facade_orientation FROM documents LIMIT 1").fetchone()["facade_orientation"])
        finally:
            conn.close()

    def test_legacy_empty_unit_rates_is_recreated(self):
        conn = self._connect()
        try:
            conn.executescript(LEGACY_UNIT_RATES_DDL)
            conn.commit()
        finally:
            conn.close()

        db.init_db()

        self.assertIn("item_code", self._columns("unit_rates"))
        conn = self._connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM unit_rates").fetchone()[0], 0)
        finally:
            conn.close()

    def test_legacy_filled_unit_rates_keeps_rows(self):
        conn = self._connect()
        try:
            conn.executescript(LEGACY_UNIT_RATES_DDL)
            conn.execute(
                "INSERT INTO unit_rates (work_category, material_name, unit_type, "
                "price_per_unit, updated_at) VALUES ('СТАРОЕ', 'Профиль', 'м²', 123.0, '2026-01-01')")
            conn.commit()
        finally:
            conn.close()

        db.init_db()

        columns = self._columns("unit_rates")
        self.assertIn("item_code", columns)
        self.assertIn("work_category", columns, "legacy-колонка не должна исчезать")
        conn = self._connect()
        try:
            row = conn.execute("SELECT work_category, price_per_unit FROM unit_rates").fetchone()
            self.assertEqual(row["work_category"], "СТАРОЕ")
            self.assertEqual(row["price_per_unit"], 123.0)
        finally:
            conn.close()


class TestRateParsing(unittest.TestCase):
    def test_parses_quoted_semicolon_csv_with_bom(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        self.assertEqual([r["item_code"] for r in rates], ["1.1", "2.2", "3.4"])

    def test_numbers_with_spaces_are_parsed(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        self.assertEqual(rates[1]["material_price_no_vat"], 4828.0)
        self.assertEqual(rates[1]["smr_price_no_vat"], 2179.0)

    def test_semicolon_inside_quoted_value(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        self.assertEqual(rates[1]["work_name"], "Монтаж минераловатного утеплителя; в 2 слоя")
        self.assertEqual(rates[1]["material_specification"], "Базальтовая вата")

    def test_categories_by_section(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        self.assertEqual(rates[0]["category"], SECTION_CATEGORIES["1"])
        self.assertEqual(rates[1]["category"], SECTION_CATEGORIES["2"])
        self.assertEqual(rates[2]["category"], SECTION_CATEGORIES["3"])
        self.assertEqual(_category_for("4.2"), SECTION_CATEGORIES["4"])
        self.assertEqual(_category_for("9.9"), "Без раздела")

    def test_project_columns_are_not_stored(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        for rate in rates:
            self.assertNotIn("project_volume", rate)
            self.assertNotIn("total_cost_with_vat", rate)

    def test_to_float_variants(self):
        self.assertEqual(_to_float("27 799"), 27799.0)
        self.assertEqual(_to_float("27,5"), 27.5)
        self.assertEqual(_to_float(""), 0.0)
        self.assertEqual(_to_float("—"), 0.0)

    def test_missing_columns_raise(self):
        bad_csv = '"№";"Наименование работ и конструкций"\n"1.1";"Работа"\n'
        with self.assertRaises(ValueError):
            parse_rates_csv(bad_csv)


class TestRatesImport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "import_test.sqlite"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE unit_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                work_name TEXT NOT NULL,
                material_specification TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                material_price_no_vat REAL NOT NULL,
                smr_price_no_vat REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def test_import_then_reimport_updates_without_duplicates(self):
        rates = parse_rates_csv(SAMPLE_CSV)
        conn = self._connect()
        try:
            first = upsert_rates(conn, rates, "2026-10-14")
            second = upsert_rates(conn, rates, "2026-10-16")
            count = conn.execute("SELECT COUNT(*) FROM unit_rates").fetchone()[0]
            row = conn.execute(
                "SELECT material_price_no_vat, updated_at FROM unit_rates WHERE item_code='1.1'"
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(first, 3)
        self.assertEqual(second, 3)
        self.assertEqual(count, 3, "повторный импорт создал дубликаты")
        self.assertEqual(row["material_price_no_vat"], 27799.0)
        self.assertEqual(row["updated_at"], "2026-10-16")

    def test_import_rejects_legacy_schema(self):
        legacy = Path(self.temp_dir.name) / "legacy.sqlite"
        conn = sqlite3.connect(legacy)
        conn.row_factory = sqlite3.Row
        conn.executescript(LEGACY_UNIT_RATES_DDL)
        conn.commit()
        try:
            with self.assertRaises(RuntimeError):
                upsert_rates(conn, parse_rates_csv(SAMPLE_CSV), "2026-10-14")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
