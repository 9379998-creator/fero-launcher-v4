# Результат выполнения задания 004 (этап 1 исправлений)

## Статус выполнения
Все правки этапа 1 успешно применены к кодовой базе в соответствии с инструкциями. Ветка `main` содержит ровно 3 локальных коммита. `git push` для `main` НЕ выполнялся. Сервер и лаунчер не перезапускались, процессы не завершались.

---

## Отчёт по правкам

### КОММИТ 1 (`app\backend\dwg_engine.py` и `scripts\Invoke-NativeDwgPdfExport.ps1`)
- **1.1** (константы `USE_GUI_WORKER = False`, `ACCORE_EXPORT_TIMEOUT_SEC = 90`, `_NO_WINDOW`, атомарная запись JSON `_write_json_atomic`): **ok (count 1)**
- **1.2** (отключение GUI-воркера `if not USE_GUI_WORKER: return None` в `get_or_start_worker`): **ok (count 1)**
- **1.4a** (пути и имя листа передаются в PowerShell через переменные окружения `$env:FERO_*`): **ok (count 1)**
- **1.4b** (передача `env=ps_env` в `subprocess.Popen` для `Invoke-NativeDwgPdfExport.ps1`): **ok (count 1)**
- **1.5** (замена `timeout_sec=90` на `timeout_sec=ACCORE_EXPORT_TIMEOUT_SEC`): **ok (count 2)**
- **1.6** (замена `manifest_path.write_text` на `_write_json_atomic(manifest_path, manifest_data)`): **ok (count 2)**
- **1.7** (атомарная замена PNG с 6 повторами при `PermissionError`): **ok (count 1)**
- **1.8a** (`p_ready = p_png.exists() and p_png.stat().st_size > 0`): **ok (count 1)**
- **1.8b** (`p1_ready_full = page1_png.exists() and page1_png.stat().st_size > 0`): **ok (count 1)**
- **1.8c** (`(target_dir / f"page-{it['page']}.png").stat().st_size > 0`): **ok (count 1)**
- **1.8d** (`if png_path.exists() and png_path.stat().st_size > 0:`): **ok (count 1)**
- **1.3 (regex)** (скрытое окно `creationflags=_NO_WINDOW` для вызовов `taskkill` в `dwg_engine.py`): **ok (найдено и пропатчено 4 вызова)**
- **1.9** (экранирование и санитизация имени листа `$safeLayout` в `scripts\Invoke-NativeDwgPdfExport.ps1`): **ok (count 1)**

**Проверки Коммита 1:**
- `py_compile app\backend\dwg_engine.py`: **OK (успешно, ошибок нет)**
- `Invoke-NativeDwgPdfExport.ps1` PowerShell parse check:
  ```
  ps1 parse errors: 0
  ```
- **Хеш коммита 1 в `main`**: `2792c8f109fdd0cdda0240e2fbe9125d014c90a0`
- **Сообщение**: `fix(dwg): headless-only rendering (GUI worker off), paths via env, escape layout name, atomic manifests, readiness by file presence`

---

### КОММИТ 2 (`app\backend\server.py`)
- **2.1** (принудительный `dpi = DWG_PREVIEW_DPI` в `/api/dwg/model-render`): **ok (count 1)**
- **2.2** (учёт `validLayouts` из манифеста в `/api/dwg/status`): **ok (count 1)**
- **2.3** (определение `ready_pages` по реально существующим непустым файлам PNG `page-{t}.png`): **ok (count 1)**
- **2.4** (замена `st_size < 35000` на `st_size == 0` для `need_raster`): **ok (count 1)**
- **2.5a** (замена `os.set_inheritable` на `self.socket.set_inheritable(False)` в `SingleInstanceHTTPServer.server_bind`): **ok (count 1)**
- **2.5b** (удаление дублирующего блока сокета в `main()`): **ok (count 1)**
- **2.6** (замена `"dwg-smart-cad-v3"` на `"dwg-smart-cad-v4"` во всех файлах `app\backend\*.py`): **ok (4 замены в `app/backend/server.py`)**

**Проверки Коммита 2:**
- `py_compile app\backend\server.py app\backend\dwg_engine.py`: **OK (успешно, ошибок нет)**
- **Хеш коммита 2 в `main`**: `50884477fa17025897edb3ad3c319026d3eded03`
- **Сообщение**: `fix(server): DWG always 150 DPI, status by real files, socket inheritable fix, cache purpose v4`

---

### КОММИТ 3 (`app\frontend\app.js`)
- **3.1a** (`(page.bytes > 0)`): **ok (count 1)**
- **3.1b** (`(displayPage.bytes > 0)`): **ok (count 1)**
- **3.2** (защита `pollInFlight`, `pollStartedAt` и таймаут 15 минут в `startDwgStatusPolling`): **ok (count 1)**
- **3.3** (сброс `pollInFlight = false` в блоке `finally`): **ok (count 1)**
- **3.4** (привязка обработчика `els.pdfPageImage.onload` ДО смены `els.pdfPageImage.src`): **ok (count 1)**

**Проверки Коммита 3:**
- `node --check app\frontend\app.js`: пропущено (Node.js не установлен в системе).
- **Хеш коммита 3 в `main`**: `cf7faf662affbfce8958f9d607e8b48cb24edb08`
- **Сообщение**: `fix(ui): DWG page readiness without size heuristic, poll in-flight guard and deadline`

---

## Финальная проверка наличия порога 35000

Команда:
```powershell
Select-String -Path app\backend\dwg_engine.py,app\backend\server.py,app\frontend\app.js -Pattern '35000'
```

Вывод:
```
app\backend\dwg_engine.py:770:                        if not png_p.exists() or png_p.stat().st_size < 35000 or png_p.stat().st_mtime < pdf_p.stat().st_mtime:
app\backend\dwg_engine.py:787:                        if not png_p.exists() or png_p.stat().st_size < 35000 or png_p.stat().st_mtime < pdf_p.stat().st_mtime:
app\backend\dwg_engine.py:798:                    if not png_p.exists() or png_p.stat().st_size < 35000 or png_p.stat().st_mtime < pdf_p.stat().st_mtime:
```
*(Все оставшиеся 3 вхождения находятся исключительно в `_pump` / `_watcher` в `dwg_engine.py`, как и предусмотрено заданием; в `server.py` и `app.js` вхождений нет).*

---

## Состояние репозитория (ветка `main`)

### `git log -4 --stat`
```
commit cf7faf662affbfce8958f9d607e8b48cb24edb08
Author: Alexander <alexander@f-engineering.spb.ru>
Date:   Tue Oct 20 13:13:38 2026 +0300

    fix(ui): DWG page readiness without size heuristic, poll in-flight guard and deadline

 app/frontend/app.js | 17 ++++++++++++++---
 1 file changed, 14 insertions(+), 3 deletions(-)

commit 50884477fa17025897edb3ad3c319026d3eded03
Author: Alexander <alexander@f-engineering.spb.ru>
Date:   Tue Oct 20 13:13:07 2026 +0300

    fix(server): DWG always 150 DPI, status by real files, socket inheritable fix, cache purpose v4

 app/backend/server.py | 44 ++++++++++++++++++++------------------------
 1 file changed, 20 insertions(+), 24 deletions(-)

commit 2792c8f109fdd0cdda0240e2fbe9125d014c90a0
Author: Alexander <alexander@f-engineering.spb.ru>
Date:   Tue Oct 20 13:12:26 2026 +0300

    fix(dwg): headless-only rendering (GUI worker off), paths via env, escape layout name, atomic manifests, readiness by file presence

 app/backend/dwg_engine.py             | 76 +++++++++++++++++++++++++++--------
 scripts/Invoke-NativeDwgPdfExport.ps1 |  9 ++++-
 2 files changed, 67 insertions(+), 18 deletions(-)

commit 4f44ce16e39f6e4b6acde9810b19122d69630c49
Author: Developer <developer@local>
Date:   Tue Oct 20 06:44:35 2026 +0300

    fix(dwg): init total_layouts, harden DWG status polling, ready-check by file size, and update .gitignore

 .gitignore            |  6 ++++++
 app/backend/server.py |  5 +++++
 app/frontend/app.js   | 55 +++++++++++++++++++++++++++++++++++----------------
 3 files changed, 49 insertions(+), 17 deletions(-)
```

### `git status -sb`
```
## main...origin/main [ahead 3]
```

---

Лаунчер нужно перезапустить вручную, чтобы изменения вступили в силу
