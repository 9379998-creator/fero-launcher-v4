# Отчёт по Заданию 006: Локальное меню выделения PDF

## 1. Метаданные репозитория и окружения
- **Целевой проект:** локальная рабочая копия `FProject-Launcher`
- **Origin (без секретов):** `https://github.com/9379998-creator/FProject-Launcher.git`
- **Ветка:** `feature/pkm-context-menu`
- **Базовый HEAD (до):** `88b45a3c26280381ac3fc6432e63c11cf1d9ecde`
- **Текущий HEAD (после):** `1416fd9a2a96ad8b704f9e9d644f0363de11c48d`
- **Исходный статус:** рабочий каталог содержал незакоммиченное уточнение `app.js` (`copyTextToClipboard` safety/cleanup); изменения объединены и зафиксированы отдельным локальным коммитом `1416fd9`
- **Удалённый репозиторий целевого проекта:** `git push` НЕ выполнялся (код остался строго локально в соответствии с `push: no`)

---

## 2. Архитектура и реальные точки входа

Все действия над выделенным текстом и зоной PDF перенесены в **локальное DOM-меню внутри просмотрщика PDF (`launcher-translate.js`)**, полностью устраняя межфреймовые сбои потери фокуса, сброса выделения и рассинхронизации координат.

1. **Открытие контекстного меню:**
   - Точка входа: `document.addEventListener("contextmenu", ...)` внутри `launcher-translate.js`.
   - Пропускает стандартные элементы ввода (`input, textarea, contenteditable`), не затрагивая меню `#findInput`.
   - Фиксирует снимок выделения `snapshotText` (из `zoneSelectedText`, `window.getSelection()` или активного `activeSelectionSnapshot`).
   - Если выделена зона AutoCAD (`zoneBox`), выставляет флаг `canCadExport = true`.
   - Скрывает родительское контекстное меню (`window.parent.hideFileContextMenu()`), исключая одновременный запуск двух меню.
   - Отображает локальный элемент `#launcherSelectionContextMenu` в пределах видимой области `iframe`.

2. **Копирование («Скопировать», Ctrl+C):**
   - Точка входа: `copyPdfSelection(snapshotText)` в `launcher-translate.js`.
   - Вызывает `navigator.clipboard.writeText(text)` немедленно из пользовательского жеста клика по меню без предварительного `await fetch`.
   - При отказе — последовательный серверный резерв `POST /api/clipboard` с валидацией `resp.ok && data.ok === true`.
   - При повторном отказе — локальный резерв через временный скрытый `textarea` (`execCommand("copy")`).
   - Тост («Текст скопирован в буфер обмена») выводится однократно только после подтверждённого успеха. Текст в логи не выводится.

3. **Перевод («Перевести»):**
   - Точка входа: `window.launcherTranslateText(snapshotText)` в `launcher-translate.js`.
   - Вызывает существующую функцию перевода с передачей зафиксированного снимка текста `snapshotText`.

4. **Поиск («Найти в документе»):**
   - Точка входа: `findPdfSelection(snapshotText)` в `launcher-translate.js`.
   - Штатный путь PDF.js: открывает `app.findBar` (если закрыт), выставляет `highlightAll = true`, вставляет `findInput.value = text`, переводит фокус/выделение и диспетчеризирует стандартное событие `input`.

5. **CAD экспорт («Экспорт в CAD»):**
   - Точка входа: `window.exportCurrentZoneToCad()` в `launcher-translate.js`.
   - Полностью сохраняет контекст прямоугольной зоны (`zoneBox`, `zoneStart`, масштаб, активная страница) без подмены строкой.

6. **Жизненный цикл меню и инвалидация кэша:**
   - Пункты меню перехватывают `mousedown` (`e.preventDefault(); e.stopPropagation();`), гарантируя, что глобальные обработчики не уничтожат меню раньше события `click`.
   - Меню закрывается после клика по пункту, по клавише `Escape` (`handlePdfJsEscape`), по клику вне меню (`mousedown`), по скроллу и потере фокуса (`blur`).
   - Кэш `activeSelectionSnapshot` инвалидируется при снятии выделения (`selectionchange` при `isCollapsed`), очистке зоны (`clearZoneSelection`), а также при смене страниц/документа (`pagesinit`, `pagechanging`).

---

## 3. Проверки и коды возврата

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

## 4. Ограничения и статус тестирования (Zero-Fake Policy)

- **Фактический статус:** **исправление реализовано и проверено синтаксически; требуется пользовательская GUI-приёмка**.
- **Причина:** Агент функционирует в консольной среде без графического монитора и курсора в активном WebView2 окне пользователя. Программные вызовы не заменяют реальный физический клик мыши. Статус PASS агентом не присваивается.
- Пользовательские процессы не останавливались, порты не блокировались.

### Сценарий пользовательской приёмки:
1. Выделить фразу А мышью в документе PDF -> ПКМ -> «Скопировать» -> вставить в Блокнот (проверить фразу А).
2. Выделить фразу Б -> ПКМ -> «Скопировать» -> вставить в Блокнот (проверить фразу Б).
3. ПКМ по выделенной фразе Б -> «Перевести» (проверить перевод фразы Б).
4. ПКМ по выделенной фразе Б -> «Найти в документе» (проверить заполнение поля поиска и подсветку).
5. Снять выделение кликом на пустое место -> проверить, что старый текст не вызывается.
6. Проверить сохранение `Ctrl+C`, `Ctrl+V` и ПКМ «Вставить» в строке поиска `#findInput`.

---

## 5. Полный diff задания (коммит 1416fd9)

```diff
diff --git a/app/frontend/app.js b/app/frontend/app.js
index 9cfa1c4..2fb0079 100644
--- a/app/frontend/app.js
+++ b/app/frontend/app.js
@@ -1830,7 +1830,7 @@ async function copyTextToClipboard(rawText, successToast = "Текст скоп
       await navigator.clipboard.writeText(text);
       success = true;
     } catch (err) {
-      console.warn("[app copy] navigator.clipboard.writeText failed:", err);
+      console.warn("[app copy] navigator.clipboard.writeText failed:", err?.name || "Error");
     }
   }
 
@@ -1844,19 +1844,20 @@ async function copyTextToClipboard(rawText, successToast = "Текст скоп
       });
       if (resp.ok) {
         const data = await resp.json();
-        if (data && data.ok) {
+        if (data && data.ok === true) {
           success = true;
         }
       }
     } catch (err) {
-      console.warn("[app copy] backend /api/clipboard fallback failed:", err);
+      console.warn("[app copy] backend /api/clipboard fallback failed:", err?.name || "Error");
     }
   }
 
   // 3. Fallback 2: execCommand on temporary textarea (only if both above failed)
   if (!success) {
+    let textarea = null;
     try {
-      const textarea = document.createElement("textarea");
+      textarea = document.createElement("textarea");
       textarea.value = text;
       textarea.style.position = "fixed";
       textarea.style.top = "0";
@@ -1867,9 +1868,12 @@ async function copyTextToClipboard(rawText, successToast = "Текст скоп
       textarea.select();
       textarea.setSelectionRange(0, text.length);
       success = document.execCommand("copy");
-      document.body.removeChild(textarea);
     } catch (err) {
-      console.warn("[app copy] execCommand fallback failed:", err);
+      console.warn("[app copy] execCommand fallback failed:", err?.name || "Error");
     } finally {
       if (textarea && textarea.parentNode) {
         textarea.parentNode.removeChild(textarea);
       }
     }
   }
 
@@ -7079,7 +7083,7 @@ try {
 // Двусторонняя синхронизация (лента миниатюр ↔ страницы PDF) и поиск
 // =============================================================================
 
-function openPdfJsSearch() {
+function openPdfJsSearch(text) {
   const win = els.pdfDocFrame?.contentWindow;
   if (!win) return;
   win.focus();
@@ -7093,12 +7097,18 @@ function openPdfJsSearch() {
       }
       const findInput = win.document?.getElementById("findInput");
       if (findInput) {
+        if (text) {
+          findInput.value = text;
+        }
         findInput.focus();
         findInput.select();
+        if (text) {
+          findInput.dispatchEvent(new Event("input", { bubbles: true }));
+        }
       }
     }
   } catch (err) {
-    console.warn("openPdfJsSearch error:", err);
+    console.warn("openPdfJsSearch error:", err?.name || "Error");
   }
 }
 
diff --git a/app/frontend/lib/pdfjs/web/launcher-translate.js b/app/frontend/lib/pdfjs/web/launcher-translate.js
index 549e0a4..24b2ffc 100644
--- a/app/frontend/lib/pdfjs/web/launcher-translate.js
+++ b/app/frontend/lib/pdfjs/web/launcher-translate.js
@@ -12,6 +12,8 @@
   let zoneStart = { clientX: 0, clientY: 0, target: null };
   let zoneSelectedText = "";
   let currentZoneSpans = [];
+  let activeSelectionSnapshot = "";
+  let selectionMenu = null;
 
   function clearZoneSelection() {
     const hadSelection = Boolean(zoneSelectedText || (zoneBox && zoneBox.style.display !== "none") || currentZoneSpans.length > 0);
@@ -25,6 +27,8 @@
     });
     currentZoneSpans = [];
     zoneSelectedText = "";
+    activeSelectionSnapshot = "";
+    if (selectionMenu) selectionMenu.style.display = "none";
     return hadSelection;
   }
 
@@ -780,9 +784,191 @@
       };
     }
 
-    // Unified Right-Click Context Menu for PDF Viewer
+    // -------------------------------------------------------------------------
+    // Dedicated Local Context Menu for PDF Document Selection (Task 006)
+    // -------------------------------------------------------------------------
+    document.addEventListener("selectionchange", () => {
+      const s = window.getSelection();
+      if (!s || s.isCollapsed) {
+        if (!selectionMenu || selectionMenu.style.display === "none") {
+          activeSelectionSnapshot = "";
+        }
+      } else {
+        activeSelectionSnapshot = s.toString().trim();
+      }
+    });
+
+    function hideSelectionContextMenu() {
+      if (selectionMenu && selectionMenu.style.display !== "none") {
+        selectionMenu.style.display = "none";
+        return true;
+      }
+      return false;
+    }
+
+    function findPdfSelection(text) {
+      if (!text) return;
+      const app = window.PDFViewerApplication;
+      if (app && app.findBar) {
+        if (!app.findBar.opened) {
+          app.findBar.open();
+        }
+        if (app.findBar.highlightAll) {
+          app.findBar.highlightAll.checked = true;
+        }
+      }
+      const findInput = document.getElementById("findInput");
+      if (findInput) {
+        findInput.value = text;
+        findInput.focus();
+        findInput.select();
+        findInput.dispatchEvent(new Event("input", { bubbles: true }));
+      }
+    }
+
+    function showSelectionContextMenu(clientX, clientY, snapshotText, canCadExport) {
+      if (!selectionMenu) {
+        selectionMenu = document.createElement("div");
+        selectionMenu.id = "launcherSelectionContextMenu";
+        selectionMenu.style.position = "fixed";
+        selectionMenu.style.zIndex = "99999";
+        selectionMenu.style.minWidth = "175px";
+        selectionMenu.style.padding = "4px";
+        selectionMenu.style.background = "#ffffff";
+        selectionMenu.style.border = "1px solid #d1d9e0";
+        selectionMenu.style.borderRadius = "4px";
+        selectionMenu.style.boxShadow = "0 4px 12px rgba(15, 23, 42, 0.15)";
+        selectionMenu.style.font = "12px/1.4 'Segoe UI', -apple-system, system-ui, sans-serif";
+        selectionMenu.style.color = "#0F172A";
+        selectionMenu.style.display = "none";
+        document.body.appendChild(selectionMenu);
+      }
+
+      selectionMenu.innerHTML = "";
+      const hasText = Boolean(snapshotText);
+
+      const items = [
+        {
+          icon: "📋",
+          label: "Скопировать",
+          hint: "Ctrl+C",
+          disabled: !hasText,
+          run: async () => {
+            if (!hasText) return;
+            await copyPdfSelection(snapshotText);
+          }
+        },
+        {
+          icon: "🌐",
+          label: "Перевести",
+          hint: "",
+          disabled: !hasText,
+          run: () => {
+            if (!hasText) return;
+            if (typeof window.launcherTranslateText === "function") {
+              window.launcherTranslateText(snapshotText);
+            }
+          }
+        },
+        {
+          icon: "🔍",
+          label: "Найти в документе",
+          hint: "",
+          disabled: !hasText,
+          run: () => {
+            if (!hasText) return;
+            findPdfSelection(snapshotText);
+          }
+        }
+      ];
+
+      if (canCadExport) {
+        items.push({
+          icon: "📐",
+          label: "Экспорт в CAD",
+          hint: "",
+          disabled: false,
+          run: () => {
+            if (typeof window.exportCurrentZoneToCad === "function") {
+              window.exportCurrentZoneToCad();
+            }
+          }
+        });
+      }
+
+      for (const it of items) {
+        const btn = document.createElement("button");
+        btn.type = "button";
+        btn.style.display = "flex";
+        btn.style.alignItems = "center";
+        btn.style.gap = "8px";
+        btn.style.width = "100%";
+        btn.style.padding = "6px 10px 6px 8px";
+        btn.style.border = "0";
+        btn.style.borderRadius = "3px";
+        btn.style.background = "transparent";
+        btn.style.color = it.disabled ? "#94a3b8" : "#0F172A";
+        btn.style.font = "inherit";
+        btn.style.textAlign = "left";
+        btn.style.cursor = it.disabled ? "default" : "pointer";
+        btn.style.whiteSpace = "nowrap";
+
+        if (!it.disabled) {
+          btn.addEventListener("mouseenter", () => { btn.style.background = "#f6f8fa"; });
+          btn.addEventListener("mouseleave", () => { btn.style.background = "transparent"; });
+        }
+
+        // Prevent mousedown from blurring or triggering dismiss handlers prematurely
+        btn.addEventListener("mousedown", (e) => {
+          e.preventDefault();
+          e.stopPropagation();
+        });
+
+        btn.addEventListener("click", async (e) => {
+          e.preventDefault();
+          e.stopPropagation();
+          hideSelectionContextMenu();
+          if (!it.disabled && typeof it.run === "function") {
+            await it.run();
+          }
+        });
+
+        const iconSpan = document.createElement("span");
+        iconSpan.style.display = "inline-block";
+        iconSpan.style.width = "16px";
+        iconSpan.style.textAlign = "center";
+        iconSpan.style.fontSize = "13px";
+        iconSpan.textContent = it.icon;
+
+        const labelSpan = document.createElement("span");
+        labelSpan.style.flex = "1 1 auto";
+        labelSpan.textContent = it.label;
+
+        btn.append(iconSpan, labelSpan);
+
+        if (it.hint) {
+          const hintSpan = document.createElement("span");
+          hintSpan.style.fontSize = "11px";
+          hintSpan.style.color = "#64748b";
+          hintSpan.style.marginLeft = "12px";
+          hintSpan.textContent = it.hint;
+          btn.append(hintSpan);
+        }
+
+        selectionMenu.appendChild(btn);
+      }
+
+      selectionMenu.style.display = "block";
+      const menuWidth = selectionMenu.offsetWidth || 180;
+      const menuHeight = selectionMenu.offsetHeight || 130;
+      const x = Math.max(8, Math.min(clientX, window.innerWidth - menuWidth - 8));
+      const y = Math.max(8, Math.min(clientY, window.innerHeight - menuHeight - 8));
+      selectionMenu.style.left = x + "px";
+      selectionMenu.style.top = y + "px";
+    }
+
     document.addEventListener("contextmenu", (event) => {
-      // 1. Pass through input, textarea, and contenteditable elements without preventDefault or stopPropagation
+      // 1. Pass through input, textarea, and contenteditable elements
       const targetEl = event.target instanceof Element ? event.target : null;
       if (targetEl && (targetEl.closest("input, textarea") || targetEl.isContentEditable)) {
         return;
@@ -791,30 +977,37 @@
       event.preventDefault();
       event.stopPropagation();
 
-      const sel = window.getSelection();
-      const selText = sel ? sel.toString().trim() : "";
-      const textToUse = zoneSelectedText || selText || "";
+      // Ensure any existing parent menus are dismissed
+      try {
+        if (window.parent && window.parent !== window && typeof window.parent.hideFileContextMenu === "function") {
+          window.parent.hideFileContextMenu();
+        }
+      } catch (_) {}
+      const findMenu = document.getElementById("launcherFindContextMenu");
+      if (findMenu) findMenu.style.display = "none";
+
+      // Snapshot text and zone context strictly at menu open
       const hasZone = Boolean(
         zoneBox && zoneBox.style.display !== "none" &&
         parseInt(zoneBox.style.width, 10) > 4 && parseInt(zoneBox.style.height, 10) > 4
       );
+      const zoneText = hasZone ? String(zoneSelectedText || "").trim() : "";
 
-      try {
-        if (window.parent && window.parent !== window && typeof window.parent.showPdfViewerContextMenu === "function") {
-          const frameRect = window.frameElement ? window.frameElement.getBoundingClientRect() : { left: 0, top: 0 };
-          window.parent.showPdfViewerContextMenu(
-            frameRect.left + event.clientX,
-            frameRect.top + event.clientY,
-            {
-              isPdf: true,
-              selectedText: textToUse,
-              hasZone: hasZone,
-              canCadExport: hasZone
-            }
-          );
-        }
-      } catch (_) {}
+      const sel = window.getSelection();
+      const liveSelText = (sel && !sel.isCollapsed) ? sel.toString().trim() : "";
+      const textSnapshot = zoneText || liveSelText || activeSelectionSnapshot || "";
+      const canCadExport = hasZone;
+
+      showSelectionContextMenu(event.clientX, event.clientY, textSnapshot, canCadExport);
+    });
+
+    document.addEventListener("mousedown", (e) => {
+      if (selectionMenu && selectionMenu.style.display !== "none" && !selectionMenu.contains(e.target)) {
+        hideSelectionContextMenu();
+      }
     });
+    window.addEventListener("scroll", () => hideSelectionContextMenu(), true);
+    window.addEventListener("blur", () => hideSelectionContextMenu());
 
     // Dismiss parent's context menu on any mouse click or scroll inside the PDF viewer
     const dismissParentContextMenu = (e) => {
@@ -853,7 +1046,11 @@
     };
 
     function handlePdfJsEscape() {
-      // 1. Сброс контекстного меню
+      // 0. Сброс локального контекстного меню выделения PDF
+      if (hideSelectionContextMenu()) {
+        return true;
+      }
+      // 1. Сброс контекстного меню родителя
       try {
         if (window.parent && window.parent !== window && typeof window.parent.hideFileContextMenu === "function") {
           if (window.parent.hideFileContextMenu()) return true;
@@ -1232,10 +1429,16 @@
         document.querySelectorAll(".textLayer").forEach(tokenizeTextLayerWords);
       });
       app.eventBus.on("pagesinit", () => {
+        activeSelectionSnapshot = "";
+        hideSelectionContextMenu();
         if (!lockedScale) {
           freezeScale();
         }
       });
+      app.eventBus.on("pagechanging", () => {
+        activeSelectionSnapshot = "";
+        hideSelectionContextMenu();
+      });
 
       // When user zooms manually (buttons, dropdown, or Ctrl+wheel), remember new scale
       app.eventBus.on("scalechanging", (evt) => {
```
