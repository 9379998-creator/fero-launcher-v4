# Шаг 1 — база данных: схема, миграция и расценки

Дата: 16.10.2026. Ветка: `main`. Ссылка на план: `PROJECT_HANDOVER_SUMMARY.md`, раздел 6, Шаг 1.

## Что сделано

1. **Миграция схемы** — `app/backend/db.py`, функция `migrate_schema()`.
   Вызывается автоматически из `init_db()` при каждом старте сервера, поэтому база
   обновляется сама. Миграция **идемпотентна** и **ничего не удаляет**: только
   `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN` и `CREATE INDEX IF NOT EXISTS`.

2. **Наполнение `unit_rates`** — `scripts/import_unit_rates.py`.
   Источник: `Ведомость_объемов_работ_фасады_БЦ_Энгельса.csv` (эталонный кейс БЦ на Энгельса).

## Версия схемы

`schema_version` в таблице `schema_version` (текущая — `2`).

## Изменения схемы

| Таблица | Что добавлено |
|---|---|
| `roots` | `project_name`, `address`, `client`, `total_facade_area_m2` |
| `documents` | `facade_orientation` |
| `parsed_elements` | `source_type`, `layer`, `material_category`, `raw_value`, `raw_units`, `normalized_value`, `normalized_units`, `measurement_method`, `review_status` |
| `unit_rates` | переведена в целевую схему: `item_code` (уникальный), `category`, `work_name`, `material_specification`, `material_price_no_vat`, `smr_price_no_vat` |
| `volume_reconciliations` | **новая таблица** — сверка объёмов PDF vs DWG |
| `estimates` | `root_id`, `name`, `total_materials_no_vat`, `total_smr_no_vat`, `total_cost_no_vat`, `vat_22`, `total_cost_with_vat`, `avg_price_per_m2` |
| `estimate_rows` | `reconciliation_id`, `unit_rate_id`, `quantity`, `material_cost`, `smr_cost`, `total_row_cost_no_vat`, `total_row_cost_with_vat` |

Новые поля сделаны nullable (или с DEFAULT), чтобы существующие 8 корней и 4170 документов
не пострадали. Колонки старой схемы (`work_category`, `material_name`, `price_per_unit`
в `unit_rates`; `specifications`/`specification_items`) сохранены для совместимости.

## Как применить и наполнить

```powershell
# 1. Схема (достаточно запустить сервер или явно):
python -c "from app.backend import db; db.init_db()"

# 2. Посмотреть, что будет импортировано (без записи):
python scripts/import_unit_rates.py --csv "<путь>\Ведомость_объемов_работ_фасады_БЦ_Энгельса.csv" --dry-run

# 3. Импорт расценок (идемпотентно, повторный запуск обновляет позиции):
python scripts/import_unit_rates.py --csv "<путь>\Ведомость_объемов_работ_фасады_БЦ_Энгельса.csv" --source-date 2026-10-14
```

## Проверка

```powershell
python -m unittest tests.test_db_step1_schema_and_rates -v
```

Тесты покрывают: целевую схему на чистой базе, идемпотентность миграции, сохранение
существующих строк, legacy-таблицу `unit_rates` (пустую и заполненную), разбор ведомости
(BOM, кавычки, разделитель `;`, пробелы/запятые в числах), идемпотентность импорта.

## Расценки: разделы ведомости

Соответствие разделов задано в `scripts/import_unit_rates.py` (`SECTION_CATEGORIES`):

| Префикс позиции | Раздел |
|---|---|
| `1.x` | I. Светопрозрачные конструкции |
| `2.x` | II. Навесной вентилируемый фасад |
| `3.x` | III. Двери и входные группы |
| `4.x` | IV. Кровельные примыкания и ограждения |

Колонки проекта (объём, стоимости) в `unit_rates` **не пишутся**: они зависят от объекта
и считаются на Шаге 4 (сметы).

## Известные ограничения (для следующих шагов)

1. `app/backend/analytics_parser.py` использует аннотацию `Tuple`
   (`PdfVectorAdapter._polygon_area`) без импорта из `typing` — упадёт при вызове.
   Правка вне Шага 1, вынести отдельным коммитом.
2. Контракт `ParsedFact` в `analytics_parser.py` шире таблицы `parsed_elements`; часть
   полей (`engine`, `quantity_type`, `review_status`) требует записи в новые колонки —
   экспортёр `ParsedFact -> parsed_elements` пишется на Шаге 2.
3. `specifications` / `specification_items` из старой схемы не используются новой моделью
   (её заменяют `volume_reconciliations` + `estimates`). Не удалены — решение по ним отдельно.
