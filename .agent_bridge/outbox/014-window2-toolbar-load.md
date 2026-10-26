# Отчёт по Заданию 014 — Панель во втором окне и неработающая «Загрузить»

**status**: partial  
**push**: yes  
**Дата/время**: 2026-10-26 12:50 UTC+3  

---

## 1. Репозитории, сборка и объяснение расхождения

### Точная конфигурация рабочей сборки
- **Рабочий репозиторий приложения**: `C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher`
- **Origin приложения**: `https://github.com/9379998-creator/FProject-Launcher.git`
- **Ветка**: `main`
- **HEAD приложения после фиксов**: `cb49ede`
- **Фактический процесс пользователя**:
  - GUI: `"C:\Python314\pythonw.exe" "C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher\app\flauncher.pyw"` (PID 3448)
  - Backend: `C:\Python314\pythonw.exe C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher\app\backend\server.py --port 8780` (PID 20104)
  - Порт GUI mutex: 8799 (PID 3448)
  - Порт API backend: 8780 (PID 20104)

### Репозиторий обмена (Bridge)
- **Путь**: `C:\Users\a9379\.gemini\antigravity\scratch\fero-bridge`
- **Origin**: `https://github.com/9379998-creator/fero-launcher-v4.git`
- **Ветка**: `bridge`

### Разрешение расхождения (fero-launcher-v4 vs FProject-Launcher)
1. Репозиторий `9379998-creator/fero-launcher-v4` используется исключительно как транспортный мост для обмена заданиями и отчётами в ветке `bridge` (`.agent_bridge/inbox` и `.agent_bridge/outbox`).
2. Вся разработка и исполняемый код приложения `FProject Launcher` ведутся в репозитории `9379998-creator/FProject-Launcher` на ветке `main`.
3. Запущенный у пользователя процесс `flauncher.pyw` и его сервер `server.py` физически исполняются из папки `C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher`. Внесение правок в `fero-launcher-v4` не повлияло бы на запущенную сборку. Все правки кода внесены и отправлены строго в ветку `main` репозитория `FProject-Launcher`.

---

## 2. Локализация и устранение причин ошибок

### Ошибка 1: Преждевременное исчезновение панели во втором окне при двойном щелчке по PDF
- **Точная причина**:
  В коммите `3ba738d` (`feat(ui): restore PDF toolbar and hide launcher header in Window 3`) функция `inWindow3()` была переписана с добавлением проверки:
  ```javascript
  if (els.pdfDocViewer && !els.pdfDocViewer.hidden) {
    return true;
  }
  ```
  И в `showPdfPage()` был добавлен вызов:
  ```javascript
  if (els.pdfDocViewer) els.pdfDocViewer.hidden = false;
  syncActionGridVisibility();
  ```
  При двойном щелчке по PDF в дереве (Окно 1) вызывается `previewFileDirectly(n, { fullView: false })` для отображения файла в стандартном сплит-режиме (Окно 2).
  Однако отображение PDF устанавливало `els.pdfDocViewer.hidden = false`. Функция `inWindow3()` ошибочно определяла это как нахождение в Окне 3, и `syncActionGridVisibility()` скрывала верхнюю панель `.action-grid` (`display: none !important`), а `updateObjectButtons()` отключала все кнопки кроме «Назад».
- **Исправление**:
  Функция `inWindow3()` в `app/frontend/app.js` приведена к каноническому определению Окна 3:
  ```javascript
  function inWindow3() {
    return Boolean(state.viewMode === "full" || els.shell?.classList.contains("full-view"));
  }
  ```
  В Окне 2 (`viewMode === "standard"`) `inWindow3()` гарантированно возвращает `false`. Верхняя панель со всеми кнопками («Объекты», «Загрузить», «Обновить», «Отобразить», «Исключить», «Параметры») остаётся полностью видимой и активной.
  В Окне 3 (`viewMode === "full"`) панель скрывается для максимизации рабочего пространства чертежа/документа.
  При нажатии `Escape` в Окне 3 выполняется `exitWindow3()`, сбрасывающий режим в `standard`, и панель со всеми кнопками мгновенно возвращается.
  Версия бандла в `index.html` обновлена на `?v=20261026-task014-win2-toolbar-load`.

### Ошибка 2: Неработающая кнопка «Загрузить»
- **Точная причина (глубокий анализ цепочки)**:
  Журнал сервера `runtime/logs/server_startup.log` зафиксировал критическое исключение при вызове `/api/choose-folder`:
  ```
  File "server.py", line 3670, in do_POST
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
  UnboundLocalError: cannot access local variable 'subprocess' where it is not associated with a value
  ```
  В строке 3953 внутри метода `do_POST` (обработчик `/api/cad/show-folder`) кем-то была добавлена локальная инструкция `import subprocess`.
  В языке Python наличие инструкции `import <name>` или `<name> = ...` в любом месте тела функции превращает этот идентификатор в **локальную переменную для всей функции**.
  При обращении к `subprocess` в начале `do_POST` (в строках 3670, 3671 и в обработчике `except subprocess.TimeoutExpired:` строки 3704) переменная `subprocess` ещё не была инициализирована.
  В результате каждый вызов `POST /api/choose-folder` мгновенно падал с `UnboundLocalError`, поток сервера аварийно закрывал сокет (`Remote end closed connection without response`), системный диалог не запускался, а кнопка «Загрузить» выдавала сетевую ошибку.
- **Исправление**:
  1. Из строки 3953 удалена затеняющая инструкция `import subprocess`. Теперь весь метод `do_POST` использует проверенный модуль `subprocess`, импортированный на уровне файла (строка 19).
  2. Восстановлена штатная цепочка контракта `docs/LOAD_BUTTON_CONTRACT.md`:
     `Клик «Загрузить»` $\rightarrow$ `triggerSystemPicker()` $\rightarrow$ `POST /api/choose-folder` $\rightarrow$ `PowerShell FolderBrowserDialog` (Win32 класс `#32770`) с доводчиком на передний план $\rightarrow$ ответ `{ "path": "..." }` $\rightarrow$ `importObjectByPath()` $\rightarrow$ `loadObjectSummaries()` $\rightarrow$ обновление интерфейса.
     При отмене диалога сервер штатно возвращает `{"path": ""}`, фронтенд тихо разблокирует кнопку без ошибок.

---

## 3. Коммиты и изменения в репозитории FProject-Launcher

Ветка `main` репозитория `FProject-Launcher`:
1. **`115db2c`** — `fix(ui): keep action toolbar visible in Window 2 and limit Window 3 hiding to full-view`  
   Изменены файлы:
   - `app/frontend/app.js` (упрощение `inWindow3()` строго до проверки `full-view`)
   - `app/frontend/index.html` (актуализация версии `?v=20261026-task014-win2-toolbar-load`)
2. **`29bac22`** — `fix(load): remove local subprocess shadowing in do_POST restoring choose-folder handler`  
   Изменены файлы:
   - `app/backend/server.py` (удалён локальный `import subprocess`, вызывавший `UnboundLocalError`)
3. **`cb49ede`** — `test(regression): add automated tests for Window 2 toolbar visibility and choose-folder contract`  
   Изменены файлы:
   - `tests/test_regression_014_toolbar_load.py` (4 сквозных автоматических теста контрактов)

Push в `origin main` выполнен успешно:
`To https://github.com/9379998-creator/FProject-Launcher.git d746f76..cb49ede main -> main`

---

## 4. Результаты приёмки и проверок

| № | Пункт приёмки по ТЗ 014 | Метод проверки | Фактический результат |
|---|--------------------------|----------------|------------------------|
| 1 | Отображение PDF во 2-м окне: PDF виден, верхняя панель и кнопки не исчезают | Автотест контракта DOM + статический анализ логики `inWindow3()` | **PASS (автотест)**. В Окне 2 `inWindow3()` возвращает `false`, `.action-grid` не скрывается, кнопки активны. |
| 2 | Переход в 3-е окно и возврат Escape с разным фокусом | Автотесты `test_regression_013_escape_load.py` (4 теста) | **PASS (автотесты)**. При `full-view` Escape закрывает локальные элементы и вызывает `exitWindow3()`. |
| 3 | Кнопка «Загрузить»: появление системного диалога, выбор каталога, импорт и отмена | Сквозной интеграционный автотест `test_choose_folder_handler_without_unbound_local_error` и `test_object_import_flow` | **PASS (автотест)**. Реальный процесс сервера поднимает PowerShell, диалог `#32770` («Browse For Folder») реально создаётся на экране, ловится через Win32 API `EnumWindows`, закрытие возвращает `{"path": ""}` с HTTP 200 без сбоев. Импорт каталога через API создаёт манифест и обновляет `/api/objects`. |
| 4 | Цепочка: PDF во 2-м окне $\rightarrow$ 3-е окно $\rightarrow$ Escape $\rightarrow$ загрузка | Анализ переходов состояний и автотесты `test_regression_014_toolbar_load.py` | **PASS (автотест)**. Состояние панели синхронизировано, `isPickerOpen` сбрасывается в `finally`. |

### Ограничения физической GUI-приёмки (Zero-Fake Policy)
- **Причина статуса `partial`**: В среде агента отсутствует интерактивный контроллер курсора мыши для физического клика по живому pywebview-окну пользователя (PID 3448).
- **Что проверено сквозными тестами**:
  1. Запуск тестового инстанса сервера и прохождение реального `POST /api/choose-folder`.
  2. Физическое появление нативного окна диалога `#32770` в подсистеме Win32 Windows.
  3. Корректность ответа при отмене диалога и обработка ошибок.
  4. Синтаксис и поведение `app.js` и `server.py`.
- **Что требуется выполнить пользователю в запущенном окне**:
  1. Перезапустить лаунчер (чтобы запущенный процесс `server.py` подхватил исправленный код из `cb49ede`).
  2. Убедиться, что в заголовке окна отображается версия: `FProject Launcher · 20261026-task014-win2-toolbar-load`.
  3. Кликнуть по PDF: проверить, что панель с кнопками во 2-м окне видна.
  4. Нажать кнопку «Загрузить»: проверить появление диалога выбора папки поверх окна.
