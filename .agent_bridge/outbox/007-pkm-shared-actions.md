# Отчёт по Заданию 007: Подключение ПКМ к работающим действиям

## 1. Метаданные репозитория и окружения
- **Целевой проект:** локальная рабочая копия `FProject-Launcher`
- **Origin (без секретов):** `https://github.com/9379998-creator/FProject-Launcher.git`
- **Ветка:** `feature/pkm-context-menu`
- **Базовый HEAD (до):** `1416fd9a2a96ad8b704f9e9d644f0363de11c48d` (подтверждён)
- **Текущий HEAD (после):** `d19e18cf4d7d8aea690afbecc2cf8ef9dbc4e0a0`
- **Исходный статус:** рабочий каталог чистый (`working tree clean`)
- **Удалённый репозиторий целевого проекта:** `git push` НЕ выполнялся (`push: no`, коммит остался строго локально)

---

## 2. Анализ сопоставления цепочек и установленные причины разрыва

### Сопоставление цепочек (работающие плашки vs меню ПКМ):

1. **Действие «Перевести»:**
   - **Плашка:** `<button id="launcherPillTransBtn">` (`launcher-translate.js:346`) -> клик ЛКМ -> `document.onmousedown` (`line 481`) проверяет `e.target.closest("... #launcherActionPill ...")`, плашка признаётся интерактивной, сброс зоны/выделения пропускается -> `pillTransBtn.onclick` (`lines 760-784`) считывает `zoneSelectedText` -> открывает поповер `#launcherTransCard` и выполняет `fetch("/api/translate")`. Цепочка работает безотказно.
   - **Меню до исправления:** в `showSelectionContextMenu` кнопка имела `mousedown` с `e.preventDefault()`, что блокировало активацию кнопки в WebView2. При `hasZone = false` (например, при двойном клике) строка 994 принудительно обнуляла `zoneSelectedText`, флаг `hasText` становился `false`, пункт становился `disabled`, клик закрывал меню без вызова `run()`.
   - **Меню после исправления:** `showSelectionContextMenu` получает `currentZoneText = String(zoneSelectedText || "").trim() || liveSelText || activeSelectionSnapshot || ""`. Пункт «Перевести» вызывает `window.launcherTranslateText(textToRun)`, открывающий тот же `#launcherTransCard` с запросом к `/api/translate`.

2. **Действие «В DWG»:**
   - **Плашка:** `<button id="launcherPillCadBtn">` (`launcher-translate.js:347`) -> клик ЛКМ -> `pillCadBtn.onclick` (`lines 751-757`) -> `exportCurrentZoneToCad()` (`lines 662-746`) считывает `zoneBox`, вычисляет координаты прямоугольной зоны на странице и вызывает `fetch("/api/pdf/export-cad")`.
   - **Меню до исправления:**
     1. Пункт назывался «Экспорт в CAD» вместо «В DWG».
     2. Селектор интерактивных элементов (`launcher-translate.js:481`) не содержал `#launcherSelectionContextMenu`. Любой клик по отступам меню вызывал `clearZoneSelection()`, который скрывал `zoneBox` (`display = "none"`). При последующем вызове `exportCurrentZoneToCad()` первая строка функции `if (!zoneBox || zoneBox.style.display === "none") return;` мгновенно прерывала выполнение.
   - **Меню после исправления:** `#launcherSelectionContextMenu` добавлен в интерактивные контейнеры строки 481 (сброс зоны заблокирован). Название приведено к каноническому `📐 В DWG`. Пункт напрямую вызывает `exportCurrentZoneToCad()`, полностью сохраняя геометрию прямоугольной зоны.

3. **Действие «Скопировать»:**
   - **Ctrl+C:** обработчик `keydown` (`launcher-translate.js:1383-1385`) напрямую вызывает `copyPdfSelection()`, считывая текущий текст и передавая в буфер обмена. Мышиные события не участвуют, сброс контекста не происходит.
   - **Меню до исправления:** `e.preventDefault()` на `mousedown` подавлял фокус и активацию кнопки; при пустом снимке пункт был `disabled`.
   - **Меню после исправления:** `mousedown` больше не подавляет событие (только `stopPropagation()`). Пункт передаёт зафиксированный локальный снимок `textToRun` напрямую в существующую рабочую функцию `copyPdfSelection(textToRun)`, выполняющую последовательную запись (`navigator.clipboard.writeText` -> fallback `POST /api/clipboard` -> fallback `execCommand`).

4. **Действие «Найти в документе»:**
   - **Штатный путь PDF.js:** `findPdfSelection(text)` открывает панель `PDFViewerApplication.findBar`, включает подсветку всех вхождений (`highlightAll = true`), заполняет поле `#findInput`, переводит фокус и диспетчеризирует событие `input`.
   - **Меню до исправления:** в `app.js` (строка 6570) пункт «Найти в документе» был обёрнут в `if (hasText)`. При клике в зоне без распознанного текста он полностью исключался из разметки, оставляя только 3 пункта («Скопировать», «Перевести», «Экспорт в CAD»).
   - **Меню после исправления:** пункт «Найти в документе» восстановлен на постоянной основе третьей позицией как в локальном меню iframe (`launcher-translate.js`), так и в основном адаптере (`app.js`). При отсутствии текста пункт аккуратно дизейблится (`disabled: !hasText`), при наличии текста запускает штатный поиск PDF.js.

---

## 3. Таблица связывания: Плашка / Меню → Фактическая функция

| Действие | Плашка / Шорткат (рабочий эталон) | Меню ПКМ (подключение в 007) | Фактическая функция / эндпоинт |
|---|---|---|---|
| **Перевести** | `#launcherPillTransBtn.onclick` | Кнопка «Перевести» -> `it.run()` | `window.launcherTranslateText(textToRun)` -> `POST /api/translate` -> `#launcherTransCard` |
| **В DWG** | `#launcherPillCadBtn.onclick` | Кнопка «В DWG» -> `it.run()` | `window.exportCurrentZoneToCad()` -> `POST /api/pdf/export-cad` -> `#launcherCadCard` (геометрия `zoneBox` сохранена) |
| **Скопировать** | Шорткат `Ctrl+C` | Кнопка «Скопировать» -> `it.run()` | `copyPdfSelection(textToRun)` -> `navigator.clipboard.writeText` / `POST /api/clipboard` / `execCommand` |
| **Найти в документе** | Поле `#findInput` PDF.js | Кнопка «Найти в документе» -> `it.run()` | `findPdfSelection(textToRun)` -> `PDFViewerApplication.findBar.open()` -> `findInput.value = textToRun` -> `Event("input")` |

---

## 4. Снимок контекста и жизненный цикл событий

1. **Фиксация снимка для текущего нажатия:**
   - В точке вызова меню вычисляется `textToRun = String(snapshotText || "").trim()`.
   - Значение захватывается лексической областью замыкания для каждого создаваемого элемента `items`.
   - Вызов `hideSelectionContextMenu()` перед `it.run()` скрывает только визуальный контейнер меню (`display = "none"`) и не обнуляет аргументы выполняемой команды.
2. **Исключение конфликтов событий:**
   - С кнопок меню снят `e.preventDefault()` на фазе `mousedown`. Оставлен только `e.stopPropagation()`.
   - В селектор интерактивных элементов (`launcher-translate.js:481`) добавлен `#launcherSelectionContextMenu`, исключающий ложное срабатывание `clearZoneSelection()`.
   - Выполнение каждой команды происходит строго однократно (`await it.run()`).

---

## 5. Проверки и коды возврата

Команды проверки выполнены в рабочей директории `FProject-Launcher`:
```powershell
node --check app/frontend/app.js
# Код возврата: 0

node --check app/frontend/lib/pdfjs/web/launcher-translate.js
# Код возврата: 0

git diff --check
# Код возврата: 0
```

---

## 6. Ограничения и статус тестирования (Zero-Fake Policy)

- **Фактический статус:** **НЕ ПРОВЕРЕНО (требуется пользовательская приёмка в GUI)**.
- **Причина:** Агент функционирует в консольной среде без графического монитора и курсора в активном WebView2-окне пользователя. Синтаксические чеки `node --check` и `git diff --check` подтверждают отсутствие синтаксических ошибок, но не заменяют реальный физический клик мыши. Статус PASS агентом не присваивается.
- Пользовательские процессы не останавливались, порты не блокировались.

### Чек-лист пользовательской приёмки:
1. **ПКМ по выделенному тексту -> «Перевести»:** проверить появление карточки перевода `#launcherTransCard` с переводом фразы.
2. **ПКМ по выделенному тексту -> «Скопировать»:** скопировать текст, проверить вставку в стороннее приложение (Блокнот). Повторить для другой фразы (проверить обновление буфера).
3. **ПКМ по выделенному тексту -> «Найти в документе»:** проверить открытие штатной панели поиска PDF.js с подсветкой слова.
4. **ПКМ по прямоугольной зоне AutoCAD -> «В DWG»:** проверить отправку зоны на экспорт и появление карточки `#launcherCadCard`.
5. **Проверка сохранения базовой функциональности:** плашки «Перевести» и «В DWG», `Ctrl+C` / `Ctrl+V`, ПКМ «Вставить» в строке поиска `#findInput`.

---

## 7. Полный diff задания 007 (коммит d19e18c)

```diff
diff --git a/app/frontend/app.js b/app/frontend/app.js
index 2fb0079..4fa0171 100644
--- a/app/frontend/app.js
+++ b/app/frontend/app.js
@@ -6549,12 +6549,25 @@ function showFileContextMenu(clientX, clientY, target) {
       },
     });
 
-    // 3. Экспорт в CAD: доступен для выделенной области (с текстом или без текста)
+    // 3. Найти в документе: штатный поиск PDF.js
+    items.push({
+      icon: "\uD83D\uDD0D",
+      label: "\u041D\u0430\u0439\u0442\u0438 \u0432 \u0434\u043E\u043A\u0443\u043C\u0435\u043D\u0442\u0435",
+      hint: "",
+      disabled: !hasText,
+      run: () => {
+        if (!hasText) return;
+        triggerSearchText(pdfSelectedText);
+      },
+    });
+
+    // 4. В DWG: доступен для выделенной прямоугольной зоны
     if (canCad) {
       items.push({
         icon: "\uD83D\uDCD0",
-        label: "\u042D\u043A\u0441\u043F\u043E\u0440\u0442 \u0432 CAD",
+        label: "\u0412 DWG",
         hint: "",
+        disabled: false,
         run: () => {
           const pdfWin = els.pdfDocFrame?.contentWindow;
           if (pdfWin && typeof pdfWin.exportCurrentZoneToCad === "function") {
@@ -6566,16 +6579,6 @@ function showFileContextMenu(clientX, clientY, target) {
       });
     }
 
-    // 4. Найти в документе: показывается только если есть текст
-    if (hasText) {
-      items.push({
-        icon: "\uD83D\uDD0D",
-        label: "\u041D\u0430\u0439\u0442\u0438 \u0432 \u0434\u043E\u043A\u0443\u043C\u0435\u043D\u0442\u0435",
-        hint: "",
-        run: () => triggerSearchText(pdfSelectedText),
-      });
-    }
-
     items.push({ sep: true });
   } else if (genericSelectedText) {
     // Прежнее поведение меню других окон без изменений
diff --git a/app/frontend/lib/pdfjs/web/launcher-translate.js b/app/frontend/lib/pdfjs/web/launcher-translate.js
index 24b2ffc..276f248 100644
--- a/app/frontend/lib/pdfjs/web/launcher-translate.js
+++ b/app/frontend/lib/pdfjs/web/launcher-translate.js
@@ -478,7 +478,7 @@
     // Selection Handlers (Mode 0: AutoCAD Zone, Mode 2: Text I-beam)
     document.addEventListener("mousedown", (e) => {
       // Don't intercept toolbar controls, findbar, or popovers
-      const interactive = e.target.closest("button, input, select, textarea, #toolbarViewer, #findbar, #launcherActionPill, #launcherTransPill, #launcherTransCard, #launcherCadCard");
+      const interactive = e.target.closest("button, input, select, textarea, #toolbarViewer, #findbar, #launcherActionPill, #launcherSelectionContextMenu, #launcherTransPill, #launcherTransCard, #launcherCadCard");
       if (interactive) return;
 
       // Right-click or middle-click: do NOT hide the floating action pill or alter selection
@@ -845,7 +845,8 @@
       }
 
       selectionMenu.innerHTML = "";
-      const hasText = Boolean(snapshotText);
+      const textToRun = String(snapshotText || "").trim();
+      const hasText = Boolean(textToRun);
 
       const items = [
         {
@@ -855,7 +856,7 @@
           disabled: !hasText,
           run: async () => {
             if (!hasText) return;
-            await copyPdfSelection(snapshotText);
+            await copyPdfSelection(textToRun);
           }
         },
         {
@@ -866,7 +867,7 @@
           run: () => {
             if (!hasText) return;
             if (typeof window.launcherTranslateText === "function") {
-              window.launcherTranslateText(snapshotText);
+              window.launcherTranslateText(textToRun);
             }
           }
         },
@@ -877,7 +878,7 @@
           disabled: !hasText,
           run: () => {
             if (!hasText) return;
-            findPdfSelection(snapshotText);
+            findPdfSelection(textToRun);
           }
         }
       ];
@@ -885,7 +886,7 @@
       if (canCadExport) {
         items.push({
           icon: "📐",
-          label: "Экспорт в CAD",
+          label: "В DWG",
           hint: "",
           disabled: false,
           run: () => {
@@ -918,9 +919,8 @@
           btn.addEventListener("mouseleave", () => { btn.style.background = "transparent"; });
         }
 
-        // Prevent mousedown from blurring or triggering dismiss handlers prematurely
+        // Keep mousedown from triggering external dismiss handlers, while preserving button activation
         btn.addEventListener("mousedown", (e) => {
-          e.preventDefault();
           e.stopPropagation();
         });
 
@@ -991,11 +991,11 @@
         zoneBox && zoneBox.style.display !== "none" &&
         parseInt(zoneBox.style.width, 10) > 4 && parseInt(zoneBox.style.height, 10) > 4
       );
-      const zoneText = hasZone ? String(zoneSelectedText || "").trim() : "";
+      const currentZoneText = String(zoneSelectedText || "").trim();
 
       const sel = window.getSelection();
       const liveSelText = (sel && !sel.isCollapsed) ? sel.toString().trim() : "";
-      const textSnapshot = zoneText || liveSelText || activeSelectionSnapshot || "";
+      const textSnapshot = currentZoneText || liveSelText || activeSelectionSnapshot || "";
       const canCadExport = hasZone;
 
       showSelectionContextMenu(event.clientX, event.clientY, textSnapshot, canCadExport);
```
