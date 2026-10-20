# Task 004 - этап 1 исправлений (apply, без push)
mode: apply
push: no

ЦЕЛЬ: убрать запуск GUI-воркера (он открывает документы в окне AutoCAD пользователя и не закрывает их при принудительной остановке), перевести рендер DWG на headless accoreconsole, сделать DPI для DWG всегда 150, считать листы готовыми по реально существующим файлам, передавать пути в PowerShell как данные, экранировать имя листа в скрипте AutoCAD, поправить мелкие ошибки сокета и записи PNG.

ПРАВИЛА:
- Менять ТОЛЬКО перечисленные файлы. Каждая замена - точное совпадение текста OLD -> NEW. Если число совпадений не равно указанному (count) - файл НЕ менять, записать расхождение в результат (вместе с началом текста OLD) и перейти к следующему файлу.
- Файлы проекта могут быть с CRLF. Используй функцию apply() ниже: она приводит переводы строк OLD/NEW к стилю файла. Кодировка UTF-8. Тексты для .ps1 - ASCII.
- После каждой группы выполни проверку (py_compile; для app.js - `node --check`, если node установлен, иначе напиши, что пропущено; для .ps1 - проверка разбора).
- Три отдельных коммита (см. ниже), `git add` только изменённых файлов. НЕ делать git push. Не запускать и не перезапускать сервер и лаунчер. Не завершать процессы. Не менять другие файлы.
- Результат в outbox/004-stage1-fixes.md: по каждой правке ok / MISMATCH (найдено N) / failed; вывод py_compile; `git log -4 --stat`; `git status -sb`; для regex-правки - число найденных вызовов; в конце строка: "Лаунчер нужно перезапустить вручную, чтобы изменения вступили в силу".

Функция (Python, запускать через C:\Python314\python.exe):
```python
def apply(path, edits):
    raw = open(path, 'r', encoding='utf-8', newline='').read()
    crlf = '\r\n' in raw
    text = raw
    for old, new, count in edits:
        if crlf:
            old = old.replace('\r\n', '\n').replace('\n', '\r\n')
            new = new.replace('\r\n', '\n').replace('\n', '\r\n')
        found = text.count(old)
        if found != count:
            print('MISMATCH', path, 'expected', count, 'found', found, repr(old[:90]))
            return False
        text = text.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='').write(text)
    return True
```

## КОММИТ 1: app\backend\dwg_engine.py и scripts\Invoke-NativeDwgPdfExport.ps1
Сообщение: `fix(dwg): headless-only rendering (GUI worker off), paths via env, escape layout name, atomic manifests, readiness by file presence`

### Файл app\backend\dwg_engine.py - сначала edits через apply(), потом regex-правка 1.3

1.1 (count 1) константы и вспомогательные функции
OLD:
```
_ACCORE_JOBS_LOCK = threading.Lock()
```
NEW:
```
_ACCORE_JOBS_LOCK = threading.Lock()

# GUI-воркер (COM в AutoCAD пользователя) отключён: он открывал документы в окне пользователя
# и не закрывал их при принудительной остановке. Рендер идёт только через headless accoreconsole.
USE_GUI_WORKER = False
ACCORE_EXPORT_TIMEOUT_SEC = 90
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0


def _write_json_atomic(path, data) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
```

1.2 (count 1) воркер не запускается
OLD:
```
    def get_or_start_worker(cls, input_dwg: Path, output_dir: Path, priority_tab: int = 1) -> Optional[subprocess.Popen]:
        key = cls._worker_key(input_dwg)
```
NEW:
```
    def get_or_start_worker(cls, input_dwg: Path, output_dir: Path, priority_tab: int = 1) -> Optional[subprocess.Popen]:
        if not USE_GUI_WORKER:
            return None
        key = cls._worker_key(input_dwg)
```

1.4a (count 1) пути и имя листа - как данные через окружение
OLD:
```
    ps_cmd = (
        f'. "{script_path}"; '
        f'Invoke-NativeDwgPdfExport -InputPath "{input_dwg}" -OutputPdf "{output_pdf}" -WorkDir "{work_dir}" -TimeoutSec {timeout_sec}'
    )
    if layout_name:
        ps_cmd += f' -LayoutName "{layout_name}"'
```
NEW:
```
    # Пути и имя листа передаются через окружение как данные, а не как код PowerShell.
    ps_cmd = (
        ". $env:FERO_PS_SCRIPT; "
        "Invoke-NativeDwgPdfExport -InputPath $env:FERO_DWG_IN -OutputPdf $env:FERO_PDF_OUT "
        f"-WorkDir $env:FERO_WORK_DIR -TimeoutSec {int(timeout_sec)}"
    )
    if layout_name:
        ps_cmd += " -LayoutName $env:FERO_LAYOUT"
    ps_env = dict(os.environ)
    ps_env.update({
        "FERO_PS_SCRIPT": str(script_path),
        "FERO_DWG_IN": str(input_dwg),
        "FERO_PDF_OUT": str(output_pdf),
        "FERO_WORK_DIR": str(work_dir),
        "FERO_LAYOUT": layout_name or "",
    })
```

1.4b (count 1) передать env в Popen экспорта
OLD:
```
            creationflags=creation_flags,
            close_fds=True,
        )
        try:
            stdout_data, stderr_data = proc.communicate(timeout=timeout_sec + 15)
```
NEW:
```
            creationflags=creation_flags,
            close_fds=True,
            env=ps_env,
        )
        try:
            stdout_data, stderr_data = proc.communicate(timeout=timeout_sec + 15)
```

1.5 (count 2) таймаут экспорта - константа
OLD: `timeout_sec=90`
NEW: `timeout_sec=ACCORE_EXPORT_TIMEOUT_SEC`

1.6 (count 2) атомарная запись манифеста
OLD: `manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")`
NEW: `_write_json_atomic(manifest_path, manifest_data)`

1.7 (count 1) замена PNG с повтором при PermissionError (WinError 5)
OLD:
```
                        os.replace(str(tmp_png), str(out_png))
                        return True
```
NEW:
```
                        replaced = False
                        for _attempt in range(6):
                            try:
                                os.replace(str(tmp_png), str(out_png))
                                replaced = True
                                break
                            except PermissionError:
                                time.sleep(0.15)
                        if not replaced:
                            try:
                                tmp_png.unlink()
                            except OSError:
                                pass
                            return out_png.exists() and out_png.stat().st_size > 0
                        return True
```

1.8 готовность PNG без порога 35000 (запись PNG атомарна, существующий непустой файл целый). Четыре отдельные замены, каждая count 1:
- OLD `p_ready = p_png.exists() and p_png.stat().st_size > 35000` NEW `p_ready = p_png.exists() and p_png.stat().st_size > 0`
- OLD `p1_ready_full = page1_png.exists() and page1_png.stat().st_size > 35000` NEW `p1_ready_full = page1_png.exists() and page1_png.stat().st_size > 0`
- OLD `(target_dir / f"page-{it['page']}.png").stat().st_size > 35000` NEW `(target_dir / f"page-{it['page']}.png").stat().st_size > 0`
- OLD `if png_path.exists() and png_path.stat().st_size > 35000:` NEW `if png_path.exists() and png_path.stat().st_size > 0:`

1.3 (regex, ПОСЛЕ успешного apply() для dwg_engine.py; ожидается ровно 4 вызова, иначе файл не менять и сообщить число) - скрытое окно для taskkill
```python
import re
p = 'app/backend/dwg_engine.py'
s = open(p, 'r', encoding='utf-8', newline='').read()
pat = re.compile(r'(subprocess\.run\(\s*\[\s*"taskkill"[^\]]*\][^)]*?close_fds=True)(,?\s*\))')
s2, n = pat.subn(r'\1, creationflags=_NO_WINDOW\2', s)
print('taskkill calls patched:', n)
if n == 4:
    open(p, 'w', encoding='utf-8', newline='').write(s2)
```
Проверка: `C:\Python314\python.exe -m py_compile app\backend\dwg_engine.py`

### Файл scripts\Invoke-NativeDwgPdfExport.ps1 (ASCII)

1.9 (count 1) имя листа из DWG - неподконтрольные данные: убрать управляющие символы и экранировать для строки AutoLISP
OLD:
```
  if ($LayoutName -and $LayoutName -ne "Model" -and $LayoutName -ne "Layout1") {
    $scriptLines += ('(setvar "CTAB" "{0}")' -f $LayoutName)
```
NEW:
```
  # LayoutName comes from DWG content (untrusted): drop control chars, escape for an AutoLISP string.
  $safeLayout = ''
  if ($LayoutName) {
    $safeLayout = ($LayoutName -replace '[\x00-\x1F\x7F]', '').Replace('\', '\\').Replace('"', '\"')
  }
  if ($safeLayout -and $safeLayout -ne "Model" -and $safeLayout -ne "Layout1") {
    $scriptLines += ('(setvar "CTAB" "{0}")' -f $safeLayout)
```
Проверка разбора:
```powershell
$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'scripts\Invoke-NativeDwgPdfExport.ps1'),[ref]$null,[ref]$e); "ps1 parse errors: $($e.Count)"; $e | ForEach-Object { $_.Message }
```

## КОММИТ 2: app\backend\server.py
Сообщение: `fix(server): DWG always 150 DPI, status by real files, socket inheritable fix, cache purpose v4`

2.1 (count 1) DWG всегда 150 DPI (72 давал размытые листы и ложный cache-hit)
OLD:
```
                dpi = int(body.get("dpi") or DEFAULT_PDF_DPI)
                force = bool(body.get("force", False))
```
NEW:
```
                dpi = DWG_PREVIEW_DPI  # DWG всегда 150 DPI: 72 давал размытые листы и ложные cache-hit
                force = bool(body.get("force", False))
```

2.2 (count 1) число листов в /api/dwg/status: печатаются только непустые листы
OLD (24 пробела отступа):
```
                        total_layouts = int(manifest_data.get("totalLayouts", 0)) or len(manifest_data.get("layouts", []))
```
NEW:
```
                        valid_layouts = manifest_data.get("validLayouts")
                        if valid_layouts is not None:
                            total_layouts = int(valid_layouts)
                        else:
                            total_layouts = int(manifest_data.get("totalLayouts", 0)) or len(manifest_data.get("layouts", []))
                        if total_layouts <= 0 and is_complete:
                            total_layouts = 1
```

2.3 (count 1) готовые листы - по реально существующим PNG, а не по range(total)
OLD:
```
                        else:
                            ready_pages = list(range(1, total_layouts + 1)) if total_layouts > 0 else [1]
```
NEW:
```
                        else:
                            # totalLayouts включает пустые листы, которые не печатаются: считаем по файлам.
                            tabs = [int(lay.get("tabOrder", 1)) for lay in manifest_data.get("layouts", []) if isinstance(lay, dict)] or [0, 1]
                            ready_pages = sorted(t for t in tabs if (target_dir / f"page-{t}.png").is_file() and (target_dir / f"page-{t}.png").stat().st_size > 0)
```

2.4 (count 1) без постоянной перерастеризации маленьких PNG
OLD: `need_raster = (not png_p.exists()) or (png_p.stat().st_size < 35000) or (png_p.stat().st_mtime < pdf_file.stat().st_mtime)`
NEW: `need_raster = (not png_p.exists()) or (png_p.stat().st_size == 0) or (png_p.stat().st_mtime < pdf_file.stat().st_mtime)`

2.5a (count 1) сокет: set_inheritable на дескрипторе сокета Windows падал с [Errno 9]
OLD:
```
    def server_bind(self):
        super().server_bind()
        if os.name == "nt":
            try:
                os.set_inheritable(self.socket.fileno(), False)
                ctypes.windll.kernel32.SetHandleInformation(
                    int(self.socket.fileno()), 1, 0  # HANDLE_FLAG_INHERIT = 1, 0 = disable inheritance
                )
            except Exception as e:
                logger.warning("Could not set socket non-inheritable: %s", e)
```
NEW:
```
    def server_bind(self):
        super().server_bind()
        try:
            self.socket.set_inheritable(False)
        except OSError as e:
            logger.warning("Could not set socket non-inheritable: %s", e)
```

2.5b (count 1) убрать дубль в main()
OLD:
```
        server = SingleInstanceHTTPServer((args.host, args.port), LauncherHandler)
        if os.name == "nt":
            try:
                os.set_inheritable(server.socket.fileno(), False)
                ctypes.windll.kernel32.SetHandleInformation(
                    int(server.socket.fileno()), 1, 0  # HANDLE_FLAG_INHERIT = 1, 0 = disable inheritance
                )
            except Exception:
                pass
    except OSError as err:
```
NEW:
```
        server = SingleInstanceHTTPServer((args.host, args.port), LauncherHandler)
    except OSError as err:
```

2.6 версия кэша DWG: во всех файлах app\backend\*.py заменить строку `"dwg-smart-cad-v3"` на `"dwg-smart-cad-v4"` (все вхождения; ожидается не менее 3, сообщи точное число и файлы). Старые кэши 72 DPI перестанут использоваться.
Проверка: `C:\Python314\python.exe -m py_compile app\backend\server.py app\backend\dwg_engine.py`

## КОММИТ 3: app\frontend\app.js
Сообщение: `fix(ui): DWG page readiness without size heuristic, poll in-flight guard and deadline`

3.1 (count 1 каждая) готовность листа без порога 35000
- OLD `(page.bytes > 35000)` NEW `(page.bytes > 0)`
- OLD `(displayPage.bytes > 35000)` NEW `(displayPage.bytes > 0)`

3.2 (count 1) защита от наложения запросов опроса и общий срок
OLD:
```
  const pollController = new AbortController();
  state.dwgStatusAbortController = pollController;

  state.dwgPollTimer = setInterval(async () => {
    if (state.renderEpoch !== epoch || state.progressCancelled || state.activeDwgPath !== filePath || pollController.signal.aborted) {
      stopDwgStatusPolling();
      return;
    }
    try {
```
NEW:
```
  const pollController = new AbortController();
  state.dwgStatusAbortController = pollController;
  const pollStartedAt = Date.now();
  let pollInFlight = false;

  state.dwgPollTimer = setInterval(async () => {
    if (pollInFlight) return;
    if (state.renderEpoch !== epoch || state.progressCancelled || state.activeDwgPath !== filePath || pollController.signal.aborted) {
      stopDwgStatusPolling();
      return;
    }
    if (Date.now() - pollStartedAt > 15 * 60 * 1000) {
      stopDwgStatusPolling();
      showNotice("Рендеринг листов DWG занимает слишком долго - опрос остановлен.");
      return;
    }
    pollInFlight = true;
    try {
```

3.3 (count 1) снятие флага в конце опроса
OLD:
```
    } catch (err) {
      if (err?.name === "AbortError") return;
      console.warn("DWG status poll error:", err);
    }
  }, 1500);
```
NEW:
```
    } catch (err) {
      if (err?.name === "AbortError") return;
      console.warn("DWG status poll error:", err);
    } finally {
      pollInFlight = false;
    }
  }, 1500);
```

3.4 (count 1) обработчик onload ставить ДО смены src
OLD:
```
              els.pdfPageImage.src = newUrl;
              els.pdfPageImage.onload = () => {
                applyPageView();
              };
```
NEW:
```
              els.pdfPageImage.onload = () => {
                applyPageView();
              };
              els.pdfPageImage.src = newUrl;
```
Проверка: `node --check app\frontend\app.js` (если node есть).

## ЗАВЕРШЕНИЕ
Выведи: `Select-String -Path app\backend\dwg_engine.py,app\backend\server.py,app\frontend\app.js -Pattern '35000'` с номерами строк (оставшиеся вхождения допустимы только в _pump/_watcher dwg_engine.py), затем `git log -4 --stat` и `git status -sb`. Не пушить.
