"""
Шаг 1: наполнение таблицы unit_rates эталонной ведомостью расценок.

Источник (эталонный кейс): Ведомость_объемов_работ_фасады_БЦ_Энгельса.csv
Формат: UTF-8 с BOM, разделитель ";", все значения в кавычках.

Использование:
    python scripts/import_unit_rates.py --csv "<путь к ведомости>"
    python scripts/import_unit_rates.py --csv "<путь>" --db "<путь к launcher.sqlite>" --dry-run
    python scripts/import_unit_rates.py --csv "<путь>" --source-date 2026-10-14

Скрипт идемпотентен: повторный импорт обновляет существующие позиции по item_code.
Колонки проекта (объём, стоимости) в unit_rates не пишутся — они зависят от объекта
и считаются на Шаге 4 (сметы).
"""

import argparse
import csv
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Корень репозитория: scripts/import_unit_rates.py -> <repo>
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backend import db as db_module  # noqa: E402

# Разделы ведомости (по нумерации позиций).
SECTION_CATEGORIES = {
    "1": "I. Светопрозрачные конструкции",
    "2": "II. Навесной вентилируемый фасад",
    "3": "III. Двери и входные группы",
    "4": "IV. Кровельные примыкания и ограждения",
}

# Ожидаемые заголовки ведомости (нормализованные) и их синонимы.
COLUMN_ALIASES = {
    "item_code": ("№", "№ п/п", "КОД", "ITEM", "ITEM_CODE"),
    "work_name": ("НАИМЕНОВАНИЕ РАБОТ И КОНСТРУКЦИЙ", "НАИМЕНОВАНИЕ", "РАБОТА", "WORK_NAME"),
    "material_specification": ("СПЕЦИФИКАЦИЯ И МАРКА МАТЕРИАЛА", "СПЕЦИФИКАЦИЯ", "МАТЕРИАЛ",
                              "MATERIAL_SPECIFICATION"),
    "unit_type": ("ЕД. ИЗМ.", "ЕДИНИЦА", "ЕД.ИЗМ.", "UNIT_TYPE"),
    "material_price_no_vat": ("ЦЕНА МАТЕРИАЛЫ БЕЗ НДС (РУБ./ЕД.)", "ЦЕНА МАТЕРИАЛЫ БЕЗ НДС",
                              "МАТЕРИАЛЫ, РУБ./ЕД.", "MATERIAL_PRICE_NO_VAT"),
    "smr_price_no_vat": ("ЦЕНА СМР / МОНТАЖ БЕЗ НДС (РУБ./ЕД.)", "ЦЕНА СМР / МОНТАЖ БЕЗ НДС",
                         "СМР, РУБ./ЕД.", "SMR_PRICE_NO_VAT"),
}


def _normalize_header(value: str) -> str:
    """Нормализует заголовок: верхний регистр, без кавычек, лишних пробелов и точек."""
    text = (value or "").strip().strip('"')
    text = text.replace("Ё", "Е").replace("ё", "е")
    text = " ".join(text.split())
    return text.upper()


def _to_float(value) -> float:
    """Мягкий парсинг числа: '27 799', '27 799,50', '27799.0' -> float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if text in ("", "-", "—"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _category_for(item_code: str) -> str:
    """Раздел ведомости по номеру позиции ('1.2' -> 'I. Светопрозрачные конструкции')."""
    section = str(item_code).split(".")[0].strip()
    return SECTION_CATEGORIES.get(section, "Без раздела")


def parse_rates_csv(text: str) -> list:
    """
    Разбирает ведомость и возвращает список записей расценок:
    {"item_code", "category", "work_name", "material_specification", "unit_type",
     "material_price_no_vat", "smr_price_no_vat"}.
    Пустые строки и строки без кода позиции пропускаются.
    """
    # utf-8-sig: снимает BOM, если поток читается как текст
    stream = io.StringIO(text.lstrip("\ufeff"))
    reader = csv.reader(stream, delimiter=";")
    rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not rows:
        return []

    header = [_normalize_header(cell) for cell in rows[0]]
    index = {}
    for field, aliases in COLUMN_ALIASES.items():
        for position, column in enumerate(header):
            if column in {_normalize_header(alias) for alias in aliases}:
                index[field] = position
                break

    missing = [field for field in COLUMN_ALIASES if field not in index]
    if missing:
        raise ValueError(
            "В ведомости не найдены обязательные колонки: %s. Заголовок: %s"
            % (", ".join(sorted(missing)), "; ".join(header))
        )

    def cell(row, field):
        position = index[field]
        return row[position].strip().strip('"') if position < len(row) else ""

    rates = []
    for row in rows[1:]:
        item_code = cell(row, "item_code").strip().strip('"')
        if not item_code or not any(ch.isdigit() for ch in item_code):
            continue  # заголовок раздела или пустая строка
        rates.append({
            "item_code": item_code,
            "category": _category_for(item_code),
            "work_name": cell(row, "work_name"),
            "material_specification": cell(row, "material_specification"),
            "unit_type": cell(row, "unit_type"),
            "material_price_no_vat": _to_float(cell(row, "material_price_no_vat")),
            "smr_price_no_vat": _to_float(cell(row, "smr_price_no_vat")),
        })
    return rates


def upsert_rates(conn: sqlite3.Connection, rates: list, updated_at: str) -> int:
    """Идемпотентно записывает расценки. Возвращает число обработанных позиций."""
    columns = [row[1] for row in conn.execute('PRAGMA table_info("unit_rates")')]
    if "item_code" not in columns:
        raise RuntimeError(
            "Таблица unit_rates не в целевой схеме (нет item_code). "
            "Сначала выполните: python -c \"from app.backend import db; db.init_db()\""
        )

    cursor = conn.cursor()
    processed = 0
    for rate in rates:
        existing_id = None
        row = cursor.execute(
            "SELECT id FROM unit_rates WHERE item_code = ?", (rate["item_code"],)
        ).fetchone()
        if row:
            existing_id = row[0]

        if existing_id is None:
            cursor.execute(
                """
                INSERT INTO unit_rates (
                    item_code, category, work_name, material_specification, unit_type,
                    material_price_no_vat, smr_price_no_vat, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rate["item_code"], rate["category"], rate["work_name"],
                    rate["material_specification"], rate["unit_type"],
                    rate["material_price_no_vat"], rate["smr_price_no_vat"], updated_at,
                ),
            )
        else:
            cursor.execute(
                """
                UPDATE unit_rates SET
                    category = ?, work_name = ?, material_specification = ?, unit_type = ?,
                    material_price_no_vat = ?, smr_price_no_vat = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    rate["category"], rate["work_name"], rate["material_specification"],
                    rate["unit_type"], rate["material_price_no_vat"], rate["smr_price_no_vat"],
                    updated_at, existing_id,
                ),
            )
        processed += 1
    conn.commit()
    return processed


def _resolve_source_date(csv_path: Path, override: str = None) -> str:
    if override:
        return override
    try:
        stamp = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc)
        return stamp.astimezone().strftime("%Y-%m-%d")
    except OSError:
        return datetime.now().strftime("%Y-%m-%d")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Импорт единичных расценок в unit_rates")
    parser.add_argument("--csv", required=True, help="Путь к Ведомость_объемов_работ_*.csv")
    parser.add_argument("--db", default=None, help="Путь к launcher.sqlite (по умолчанию runtime/db)")
    parser.add_argument("--source-date", default=None, help="Дата актуальности расценок (ГГГГ-ММ-ДД)")
    parser.add_argument("--dry-run", action="store_true", help="Только разобрать и показать, без записи")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print("Файл ведомости не найден: %s" % csv_path, file=sys.stderr)
        return 2

    text = csv_path.read_text(encoding="utf-8-sig")
    rates = parse_rates_csv(text)
    if not rates:
        print("В ведомости не найдено ни одной позиции расценок.", file=sys.stderr)
        return 3

    updated_at = _resolve_source_date(csv_path, args.source_date)
    print("Источник: %s" % csv_path)
    print("Позиций разобрано: %d" % len(rates))
    print("Дата актуальности: %s" % updated_at)

    if args.dry_run:
        for rate in rates:
            print("  %-5s %-38s %-12s мат=%10.2f смр=%10.2f"
                  % (rate["item_code"], rate["category"][:38], rate["unit_type"],
                     rate["material_price_no_vat"], rate["smr_price_no_vat"]))
        print("--dry-run: в базу ничего не записано.")
        return 0

    target = Path(args.db) if args.db else db_module.DB_PATH
    if args.db:
        conn = sqlite3.connect(str(target), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
    else:
        conn = db_module.get_connection()
        db_module.init_db()

    try:
        processed = upsert_rates(conn, rates, updated_at)
        total = conn.execute("SELECT COUNT(*) FROM unit_rates").fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COUNT(*) FROM unit_rates GROUP BY category ORDER BY category"
        ).fetchall()
    finally:
        conn.close()

    print("Записано/обновлено позиций: %d" % processed)
    print("Всего в unit_rates: %d" % total)
    for category, count in by_category:
        print("  %-40s %d" % (category, count))
    print("Готово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
