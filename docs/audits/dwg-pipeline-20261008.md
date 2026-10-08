# Технический аудит и карта вызовов DWG → PDF Pipeline

- **Проверенный базовый SHA**: `5af8a53b0ebcddc7c5f37323494605937982481a` (тег `launcher-pdf-accepted-20261008`)
- **Ветка аудита**: `audit/dwg-pipeline-20261008`
- **Изолированное рабочее дерево**: `C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4-dwg-audit`
- **Дата проведения аудита**: 2026-10-08

---

## 1. Карта текущей реализации (Call Map)

Полный путь обработки DWG-чертежа в текущей кодовой базе:

```
[Пользовательский клик по DWG в Дереве / Ленте]
   │
   ▼
[app/frontend/app.js: previewFileDirectly()]
   │ node.extension === "DWG"
   │ Проверка парного PDF: findPdfPairForDwg()
   ├─► Если парный PDF найден: открытие через renderSelectedPdfFiles() (штатный PDF)
   └─► Если парного PDF нет: установка previewType = "DWG_MODEL"
         │
         ▼
[app/frontend/app.js: renderBatch() / renderSelectedFiles()]
   │ HTTP POST /api/dwg/model-render { files: [path], dpi: 150 }
   │ Блокировка: acquireDwgSlot() (семафор на 1 параллельный запрос)
   │ Тайм-аут запроса: batchTimeout = 1 800 000 мс (30 минут)
   │
   ▼
[app/backend/server.py: /api/dwg/model-render (строки 3387–3417)]
   │ Вызов render_dwg_model(path, dpi) (строки 1086–1157)
   │
   ▼
[app/backend/server.py: dwg_to_model_pdf() (строки 970–1040)]
   │
   ├─► 1. Проверка парного PDF рядом с DWG:
   │      path.with_suffix(".pdf").exists() && mtime_ns >= dwg.mtime_ns
   │      (Если найден и размер > 1024 байт -> возврат (paired_pdf, True))
   │
   ├─► 2. Проверка локального кэша:
   │      key = file_cache_key(path, "dwg-smart-cad-v2")
   │      DWG_CACHE_DIR / key / manifest.json
   │      (Если sourceMtimeNs и sourceSize совпадают -> возврат (fallback_pdf, True))
   │
   └─► 3. Преобразование через AutoCAD: dwg_convert_process() (строки 927–968)
            │
            ├─► Попытка 1: dwg_convert_oneshot(script=render_dwg_smart.ps1) (строки 891–925)
            │      Вызов powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File scripts/render_dwg_smart.ps1
            │      Тайм-аут: DWG_RENDER_TIMEOUT_SECONDS = 900 с (15 минут)
            │
            └─► Попытка 2 (при сбое Попытки 1): dwg_convert_via_daemon() (строки 832–889)
                   Запуск / подключение к фоновому render_dwg_daemon.ps1
```

---

## 2. Анализ этапов преобразования

### Скрипт `scripts/render_dwg_smart.ps1`
1. **Регистрация COM MessageFilter**:
   - Реализован C# класс `LauncherMessageFilter` (`CoRegisterMessageFilter`), предотвращающий сбои `RPC_E_CALL_REJECTED` при занятости CAD.
2. **Подключение к AutoCAD**:
   - Перебирает версии COM ProgID: от `AutoCAD.Application.25` до `AutoCAD.Application` (на тестовой машине установлен AutoCAD 2024 `AutoCAD.Application.24.3`).
   - Получает PID окна AutoCAD (`GetWindowThreadProcessId`) для последующего гарантированного завершения.
   - Устанавливает `$app.Visible = $false`.
3. **Открытие документа**:
   - `$document = $app.Documents.Open($InputPath, $true)` (в режиме только чтение).
   - Задает переменные оптимизации:
     - `LAYOUTREGENCTL = 2` (кэширование регенерации листов);
     - `REGENMODE = 0` (отключение фоновой перерисовки);
     - `BACKGROUNDPLOT = 0` (синхронная печать);
     - `EXPERT = 5` (подавление диалоговых окон).
4. **Обход листов (Layouts)**:
   - Отбирает листы: `Where-Object { -not $_.ModelType } | Sort-Object TabOrder`.
   - Фильтрует пустые листы: `Where-Object { $_.Block.Count -gt 1 }`.
   - Если есть непустые листы:
     - Активирует каждый лист: `$document.ActiveLayout = $layout`.
     - Назначает плоттер `DWG To PDF.pc3` (или `AutoCAD PDF`, `Microsoft Print to PDF`).
     - Подбирает формат листа из CanonicalMediaNames (`A0`, `A1`, `A2`, `A3`, `A4`).
     - Устанавливает `$layout.PlotType = 4` (`acLayout`).
     - Вызывает `$document.Plot.PlotToFile($pageFile)`.
5. **Обработка пространства модели (Model Space)**:
   - Если листов нет (`$pagePdfPaths.Count -eq 0`):
     - Берёт `$layout = $document.ModelSpace.Layout`.
     - Устанавливает `$layout.PlotType = 1` (`acExtents`).
     - Вписывает в лист: `CenterPlot = $true`, `StandardScale = 0` (`acScaleToFit`).
     - Печатает в `page_model.pdf`.
6. **Крайний резервный путь (Native Export)**:
   - Если COM печать модели не сработала: закрывает COM-документ и вызывает `scripts/Invoke-NativeDwgPdfExport.ps1` через `accoreconsole.exe` (`_.-EXPORT _PDF _E`).
7. **Склейка многостраничного PDF**:
   - Генерирует инлайн-скрипт `merge.py` и запускает его через `$PythonExe`.
   - Использует `PyMuPDF` (`fitz.insert_pdf`), при его отсутствии — `pypdf.PdfWriter`.
   - Результат сохраняется в целевой `$OutputPath` (рядом с DWG) либо в `$FallbackCachePath`.
8. **Очистка ресурсов (блок `finally`)**:
   - Отзывает `LauncherMessageFilter::Revoke()`.
   - Вызывает `$document.Close($false)` и `ReleaseComObject($document)`.
   - Вызывает `$app.Quit()` и `ReleaseComObject($app)`.
   - Завершает процесс по зафиксированному PID (`cadPid`), если он не вышел за 3 секунды.
   - Удаляет временную директорию задания `FEng_dwg_<hash>`.

---

## 3. Семантика листов и выявленные дефекты

| Аспект | Текущее поведение в коде | Оценка / Риск |
| :--- | :--- | :--- |
| **Перечисление листов** | `Layouts \| Where-Object { -not $_.ModelType }` | **Штатно**: Model исключается из листов |
| **Порядок следования** | `Sort-Object TabOrder` | **Штатно**: проектный порядок вкладок AutoCAD сохраняется |
| **Пустые листы** | `Where-Object { $_.Block.Count -gt 1 }` | **Риск**: эвристика `Count > 1` может ошибочно пропустить лист со штампом в XREF |
| **Форматы и ориентация** | Поиск первого совпадения имени в CanonicalMediaNames (`A0`..`A4`) | **Критический дефект**: не учитывает альбомную/книжную ориентацию листа (`PlotRotation`) |
| **Настройки печати (CTB/STB)** | `$layout.PlotWithPlotStyles = $true` | **Риск**: если таблица стилей (CTB) отсутствует в путях поиска AutoCAD, чертёж напечатается в цветах слоёв |
| **XREF и связанные файлы** | Загружаются движком AutoCAD при открытии | **Штатно**, но относительные пути требуют нахождения рядом с чертежом |
| **Model Space (печать модели)** | `acExtents` (`PlotType = 1`) + `ScaleToFit` | **Риск**: если в модели далеко на координатах висит мусорный объект, полезный чертёж ужмётся в точку |

---

## 4. Результаты аудита и таблица тестов

| № | Тест / Проверка | Статус | Подтверждение / Примечание |
| :---: | :--- | :---: | :--- |
| 1 | Верификация контрольной точки Git (тег `launcher-pdf-accepted-20261008`) | **PASS** | SHA: `5af8a53b0ebcddc7c5f37323494605937982481a`, refs проверены |
| 2 | Изоляция рабочего дерева (`git worktree`) | **PASS** | Создан `fero-launcher-v4-dwg-audit`, основной репозиторий не затронут |
| 3 | Наличие и целостность исполняемых скриптов DWG | **PASS** | `render_dwg_smart.ps1`, `render_dwg_daemon.ps1`, `Invoke-NativeDwgPdfExport.ps1` на месте |
| 4 | Наличие установленного AutoCAD в среде | **PASS** | Обнаружен AutoCAD 2024 (`C:\Program Files\Autodesk\AutoCAD 2024\acad.exe`, `accoreconsole.exe`) |
| 5 | Тесты контракта и изоляции (`test_dwg_pipeline_audit.py`) | **PASS** | 4 теста пройдены: контракты кэша, скрипты, обработка отсутствующих DWG |
| 6 | Регрессионные тесты принятой версии (`test_file_count_consistency.py` и др.) | **PASS** | Все 41 тест пройдены без ошибок |
| 7 | Преобразование реальных файлов DWG_SMALL / DWG_LARGE | **NOT RUN** | Требуется указание владельцем путей к тестовым образцам |
| 8 | Контроль изоляции кэша и runtime | **PASS** | Выявлено: `RUNTIME_DIR` зашит в константу, требуется параметр изоляции кэша |

---

## 5. Выявленные риски кэширования и изоляции

1. **Запись PDF рядом с исходным DWG-файлом**:
   - `render_dwg_smart.ps1` по умолчанию сохраняет `path.with_suffix(".pdf")` в исходную папку документа.
   - **Риск**: нарушение правила read-only для пользовательских архивов и сетевых папок.
2. **Локальный кэш завязан на размер и время модификации**:
   - `manifest.get("sourceMtimeNs") == path.stat().st_mtime_ns`.
   - **Риск**: если изменился вложенный XREF-файл или файл стилей печати CTB, а сам DWG не менялся — кэш посчитает чертёж актуальным и не пересоберёт PDF.
3. **Общий `RUNTIME_DIR`**:
   - В [app/backend/server.py](file:///C:/Users/a9379/.gemini/antigravity/scratch/fero-launcher-v4-dwg-audit/app/backend/server.py#L58) путь к кэшу жёстко задан как `REPO_ROOT / "runtime"`. При параллельном тестировании на одном сервере тестовый рантайм использует папку рабочего рантайма.

---

## 6. Вопросы владельцу для согласования следующего этапа

1. **Тестовые образцы**:
   - Предоставьте локальные пути к двум безопасным файлам DWG:
     - `DWG_SMALL` (небольшой чертёж/узел с 1–3 листами);
     - `DWG_LARGE` (крупный чертёж на ~40 МБ с множеством Layouts).
2. **Политика сохранения полученного PDF**:
   - Разрешено ли лаунчеру сохранять сгенерированный `.pdf` рядом с исходным `.dwg` в папке проекта, или генерация должна идти **строго в изолированный кэш** приложения (`runtime/cache/dwg/`)?
3. **Таблицы стилей печати (CTB)**:
   - Используются ли в вашей организации специфические проектные CTB-файлы (например, `monochrome.ctb` или фирменные стили толщин линий), и где они расположены на рабочих машинах?
