# Отчёт по Заданию 009: Источники текста и данных при переносе PDF → CAD

## 1. Метаданные репозитория и окружения
- **Исследованный проект:** локальная рабочая копия `FProject-Launcher`
- **Origin:** `https://github.com/9379998-creator/FProject-Launcher.git`
- **Ветка:** `feature/pkm-context-menu`
- **Исследованный HEAD:** `393ebc00446c8162101200db5b7a07ce5715bdb1` (подтверждён)
- **Статус рабочего каталога:** чистый (`working tree clean`)
- **Режим выполнения:** `read-only` (код проекта не менялся и не пушился)

---

## 2. Короткий ответ понятным языком

1. **Откуда берётся текст (Скопировать / Ctrl+C):**  
   Текст извлекается **исключительно из невидимого HTML-слоя PDF.js (`.textLayer`)**, который браузер генерирует поверх страницы из векторных шрифтовых объектов PDF. Никакого OCR (распознавания со скриншота/картинки) здесь нет. Если выделить рамку — скрипт математически находит HTML-слова, попавшие внутрь координат рамки на экране, и собирает их в строки.
2. **Что на экране:**  
   Показывается полноценный движок **PDF.js в `iframe`**. Он загружает **оригинальный PDF-файл** напрямую с диска через эндпоинт `/api/file/raw`. Визуальный рисунок строится на элементе `<canvas>`, а поверх него лежит прозрачный слой с текстом. Никаких промежуточных картинок-превью в этом окне нет.
3. **Что попадает в AutoCAD при ручной вставке (Ctrl+V):**  
   Приложение кладёт в системный буфер Windows **только чистый текст (`CF_UNICODETEXT`)**. В буфере нет ни чертежей, ни картинок, ни слоёв. Поэтому в чертёжном поле AutoCAD по `Ctrl+V` появится обычный текстовый блок `MTEXT`, а не линии или контуры.
4. **Как работает «В DWG перевести»:**  
   Это совершенно другой процесс, не связанный с буфером обмена. Бэкенд получает не картинку и не текст, а **путь к исходному PDF-файлу и координаты рамки в типографских пунктах**. Библиотека `PyMuPDF` (`fitz`) извлекает из файла настоящие векторные кривые и отрезки, алгоритм сшивает их в замкнутые полилинии, определяет масштаб и раскладывает по слоям (`01_АЛЮМИНИЙ_РАМА`, `03_ТЕРМОМОСТ`, `07_РАЗМЕРЫ` и др.). Библиотека `ezdxf` сохраняет настоящий векторный **AutoCAD DXF (R2013)**, после чего Windows автоматически открывает его в CAD-программе через `os.startfile`.
5. **Что будет со сканом без текста:**  
   Текст скопировать **не удастся** (слой пуст, OCR отсутствует). Экспорт в CAD выдаст **пустой DXF-файл**, так как растровые картинки в текущей версии не векторизуются и в CAD не встраиваются.

---

## 3. Сводная таблица: Действие → Источник → Преобразование → Результат

| Действие | Источник данных | Преобразование / Обработка | Итоговый результат |
|---|---|---|---|
| **ПКМ «Скопировать» / Ctrl+C** | HTML-элементы `.textLayer span` и `.launcher-word` в DOM PDF.js | Геометрическая сортировка токенов по строкам (`extractZoneText`), каскад в буфер Windows | Текстовая строка в системном буфере обмена Windows (`CF_UNICODETEXT`) |
| **Ручная вставка в AutoCAD (`Ctrl+V`)** | Системный буфер обмена Windows | Парсинг буфера внутренними механизмами AutoCAD | Создание объекта `MTEXT`/`TEXT` в точке клика (или ввод в командную строку) |
| **Отображение в окне просмотра** | Исходный файл PDF на диске (`/api/file/raw`) | Рендеринг PDF.js на `<canvas>` + наложение прозрачного слоя `.textLayer` | Векторная растровая картинка на Canvas + интерактивный слой выделения |
| **ПКМ «В DWG перевести»** | Исходный файл PDF на диске + координаты рамки `crop` (в PDF-пунктах) | PyMuPDF `get_drawings()` -> дискретизация Безье -> сшивка полилиний -> детекция масштаба -> классификация по слоям -> генерация `ezdxf` | Векторный файл AutoCAD DXF (R2013) в `runtime/cache/cad/` -> автозапуск через `os.startfile()` |

---

## 4. Архитектурные схемы процессов

### Схема 1. Копирование текста и ручная вставка в AutoCAD
```
[Исходный PDF на диске]
          │
          ▼
   (GET /api/file/raw)
          │
          ▼
   [PDF.js Viewer]
   ├── <canvas> (визуальный рендер графики)
   └── <div class="textLayer"> (прозрачные HTML-спаны слов)
          │
          ▼  Пользователь выделяет рамку / текст
   [launcher-translate.js]
   ├── Поиск пересечений DOM-спанов с рамкой (getBoundingClientRect)
   └── extractZoneText() -> zoneSelectedText (строка текста)
          │
          ▼  ПКМ «Скопировать» или Ctrl+C
   [copyPdfSelection()]
   ├── 1. navigator.clipboard.writeText(text)
   └── 2. Резерв: POST /api/clipboard -> set_windows_clipboard() (Win32 CF_UNICODETEXT)
          │
          ▼
   [Системный буфер обмена Windows] (только plain text UTF-16LE)
          │
          ▼  Пользователь переходит в AutoCAD и нажимает Ctrl+V
   [AutoCAD]
   └── Читает CF_UNICODETEXT -> создаёт текстовый примитив MTEXT в чертеже
```

### Схема 2. Экспорт прямоугольной зоны в CAD («В DWG перевести»)
```
[Прямоугольная рамка zoneBox на экране]
          │
          ▼
   [launcher-translate.js: exportCurrentZoneToCad()]
   ├── Пересчёт координат экрана в PDF-пункты: [x0, y0, x1, y1] (с учётом scale viewport)
   └── Запрос: POST /api/pdf/export-cad { file: path, page: N, crop: [x0, y0, x1, y1] }
          │
          ▼
   [Backend: server.py -> pdf_cad_extractor.py]
   ├── 1. fitz.open(pdf_path) -> page.get_drawings() (извлечение истинных векторных операторов PDF)
   ├── 2. sample_bezier() (разбиение кубических кривых Безье на отрезки)
   ├── 3. Polyline Chaining (сшивка разрозненных линий в замкнутые контуры профилей)
   ├── 4. Инверсия оси Y и масштаб: total_scale = (25.4 / 72.0) * scale_factor_detected (в мм)
   ├── 5. Классификация по слоям (01_АЛЮМИНИЙ_РАМА, 03_ТЕРМОМОСТ, 07_РАЗМЕРЫ, 08_ОСИ, 09_ТЕКСТ)
   └── 6. ezdxf -> генерация файла .dxf (R2013) в папку runtime/cache/cad/
          │
          ▼
   [POST /api/cad/open]
          │
          ▼
   [os.startfile(filePath)] -> Windows запускает AutoCAD с готовым векторным чертежом
```

---

## 5. Детальные ответы на вопросы с кодом и номерами строк

### Вопрос 1: Источник строки при копировании, формирование `zoneSelectedText` и снимка меню
- **Источник:** Строка формируется строго из текстовых узлов DOM-дерева слоя `.textLayer`, сгенерированного PDF.js. OCR не используется.
- **Ветка 1 — Прямоугольная зона AutoCAD (Режим 0, по умолчанию):**
  - Пользователь растягивает рамку мышью. В обработчике `mousemove` (`launcher-translate.js:560-583`):
    ```javascript
    const allTokens = document.querySelectorAll(
      ".textLayer .launcher-word, .textLayer span:not(.markedContent):not(.endOfContent):not(:has(.launcher-word))"
    );
    // Проверка 2D-пересечения координат каждого токена с прямоугольником boxRect:
    const intersects = !(
      r.right < boxRect.left - 2 || r.left > boxRect.right + 2 ||
      r.bottom < boxRect.top - 5 || r.top > boxRect.bottom + 5
    );
    if (intersects) {
      tokenEl.classList.add("zone-selected");
      matchedTokens.push(tokenEl);
    }
    currentZoneSpans = matchedTokens;
    ```
  - По отпусканию кнопки мыши (`mouseup`, строка 625) вызывается `extractZoneText()` (`lines 74-114`):
    ```javascript
    // Сортировка токенов: сверху вниз (с порогом 7-8px на строку), затем слева направо
    const sorted = currentZoneSpans.slice().sort((a, b) => {
      const diffY = a.getBoundingClientRect().top - b.getBoundingClientRect().top;
      if (Math.abs(diffY) > 7) return diffY;
      return a.getBoundingClientRect().left - b.getBoundingClientRect().left;
    });
    // Сборка строк и сохранение:
    zoneSelectedText = lines.filter(Boolean).join("\n");
    ```
- **Ветка 2 — Обычное текстовое выделение (Режим 2):**
  - Пользователь выделяет текст курсором-палочкой. Работает нативный `window.getSelection()`.
  - В обработчике `mouseup` (`line 584`) вызывается `updateSelectionTooltip()` (`lines 139-154`):
    ```javascript
    const sel = window.getSelection();
    const txt = sel ? sel.toString().trim() : "";
    zoneSelectedText = txt;
    ```
- **Снимок меню ПКМ (`contextmenu`, lines 940-960):**
  - При правом клике фиксируется:
    ```javascript
    const currentZoneText = String(zoneSelectedText || "").trim();
    const sel = window.getSelection();
    const liveSelText = (sel && !sel.isCollapsed) ? sel.toString().trim() : "";
    const textSnapshot = currentZoneText || liveSelText || activeSelectionSnapshot || "";
    showSelectionContextMenu(event.clientX, event.clientY, textSnapshot, canCadExport);
    ```
- **Запись в системный буфер (`launcher-translate.js:1140-1200`):**
  - Кнопка меню «Скопировать» вызывает `copyPdfSelection(textToRun)`, а `Ctrl+C` (`line 1358`) вызывает `copyPdfSelection()`.
  - Каскад: `navigator.clipboard.writeText(text)` -> при отказе `fetch("/api/clipboard")` -> при отказе `execCommand("copy")`.
  - На бэкенде (`server.py:843-899`):
    ```python
    user32.OpenClipboard(None)
    user32.EmptyClipboard()
    encoded = (normalized_text + "\0").encode("utf-16le")
    # Выделение памяти и запись CF_UNICODETEXT:
    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    user32.CloseClipboard()
    ```

---

### Вопрос 2: Что показывается на экране и откуда viewer получает документ
- **Технология отображения:** Полноценный PDF.js просмотрщик внутри iframe (`app.js:4040-4060`):
  ```javascript
  const rawUrl = "/api/file/raw?path=" + encodeURIComponent(targetDocPath);
  const viewerUrl = "/lib/pdfjs/web/viewer.html?file=" + encodeURIComponent(rawUrl) + "#page=" + targetPageNum;
  els.pdfDocFrame.src = viewerUrl;
  ```
- **Рендеринг:**
  - Графика: HTML5 `<canvas>` (векторная отрисовка страниц библиотекой PDF.js в браузере).
  - Текст: Слой `<div class="textLayer">` с прозрачными `<span>` элементами.
  - Это **НЕ предварительно растеризованный PNG или JPEG**.
- **Источник документа:**
  - Эндпоинт `/api/file/raw` (`server.py:3415-3485`) читает **исходный оригинальный PDF-файл с диска** без конвертаций и изменений:
    ```python
    target = Path(raw_path).expanduser().resolve()
    # Отдача файла с поддержкой HTTP 206 Partial Content (Range bytes)
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    ```

---

### Вопрос 3: Копирование и ручная вставка в AutoCAD
- **Что приложение пишет в буфер:**
  - Исключительно **`CF_UNICODETEXT` (Win32 Clipboard Format 13)** в кодировке UTF-16LE (соответствует MIME-типу `text/plain`).
  - Приложение **не пишет** в буфер форматы `CF_DIB` (картинка), HTML, RTF или структуры чертежей DWG/DXF.
- **Что доказано кодом:** Код подтверждает передачу только плоского текста строки.
- **Поведение AutoCAD при вставке:**
  - Полностью определяется механизмами самого AutoCAD:
    - При вставке в графическое поле чертежа AutoCAD считывает `CF_UNICODETEXT` и вызывает команду создания многострочного текста **`MTEXT`** (или `TEXT`).
    - При активной командной строке текст подставляется как ввод команды или координат.
    - Векторные контуры, полилинии или штриховки из текстового буфера AutoCAD создать не может.

---

### Вопрос 4: Трассировка ПКМ «В DWG перевести»
- **Что получает backend (`launcher-translate.js:662-715` -> `server.py:3892-3915`):**
  ```json
  {
    "file": "C:/Projects/.../catalog.pdf",
    "page": 293,
    "crop": [120.4, 340.2, 450.8, 680.1]
  }
  ```
  Backend получает путь к файлу и координаты рамки в типографских пунктах. Текст и пиксели в запрос не входят.
- **Преобразование координат (`pdf_cad_extractor.py:278-288`):**
  - Точка отсчёта переносится в левый нижний угол рамки: `ox = filter_rect.x0`, `oy = filter_rect.y1`.
  - Ось Y инвертируется (вверх — положительное направление в CAD):
    ```python
    cad_x = (pt[0] - ox) * total_scale
    cad_y = (oy - pt[1]) * total_scale
    ```
  - Масштаб: `total_scale = (25.4 / 72.0) * scale_factor_detected` (перевод пунктов в миллиметры с учётом найденного на чертеже масштаба `1:1`, `1:2` и т.д.).
- **Извлечение геометрии и текста:**
  - Модуль **`fitz` (PyMuPDF)**:
    - `page.get_drawings()` извлекает исходные векторные пути (отрезки `l`, Безье `c`, прямоугольники `re`).
    - Функция `sample_bezier(..., steps=8)` аппроксимирует сплайны отрезками полилиний.
    - `page.get_text("words")` извлекает текстовые надписи размеров и артикулов.
  - Алгоритм **Polyline Chaining** (`lines 220-276`):
    - Сшивает отрезки с допуском `chain_tol = 0.5 pt` (~0.18 мм) в сплошные замкнутые полилинии контуров профилей.
  - Библиотека **`ezdxf`**:
    - Создаёт чертёж стандарта **AutoCAD R2013**.
    - Раскладывает примитивы по слоям:
      - `01_АЛЮМИНИЙ_РАМА` (толщина 0.35 мм)
      - `03_ТЕРМОМОСТ` (толщина 0.25 мм)
      - `07_РАЗМЕРЫ` (толщина 0.18 мм, цвет Red)
      - `08_ОСИ` (толщина 0.18 мм, цвет Magenta, тип линии CENTER)
      - `09_ТЕКСТ` (толщина 0.20 мм)
- **Использование OCR:**
  - **OCR не используется.** Чертёж извлекается из исходных векторных операторов PDF.
- **Формат и открытие:**
  - Создаётся файл **`.dxf` (ASCII DXF R2013)** по пути `runtime/cache/cad/<имя>_стр_<N>.dxf`.
  - Вызов `os.startfile(filepath)` запускает ассоциированную в Windows CAD-программу (AutoCAD, DWG TrueView).

---

### Вопрос 5: Поведение при работе со сканированным PDF (без векторного слоя)
1. **Копирование текста:**
   - В растровом скане слой `.textLayer` пуст.
   - `zoneSelectedText` останется пустым, в контекстном меню пункт «Скопировать» будет отключён (`disabled: true`), `Ctrl+C` ничего в буфер не запишет.
2. **Экспорт в CAD («В DWG перевести»):**
   - Метод `page.get_drawings()` вернёт пустой список (в скане нет векторных путей, только растровый объект `Image`).
   - Метод `page.get_text("words")` вернёт пустой список слов.
   - Экспорт завершится созданием **пустого DXF-файла** (0 примитивов, без геометрии).
   - Растровая векторизация (трассировка растра в вектор) и OCR в коде лаунчера отсутствуют.

---

## 6. Что остаётся НЕ УСТАНОВЛЕНО
1. Поведение команды вставки в AutoCAD (`Ctrl+V`) при нестандартных системных переменных (например, при выключенном диалоге `TEXTED` или специфических скриптах автозапуска AutoCAD).
2. Конкретное приложение, которое откроет файл DXF по `os.startfile()`, определяется ассоциациями файлов текущей учётной записи Windows пользователя.
