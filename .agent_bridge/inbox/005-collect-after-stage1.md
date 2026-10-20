# Task 005 - сбор данных ПОСЛЕ теста этапа 1 (только чтение)
mode: read-only
push: no

ПРЕДУСЛОВИЕ (делает пользователь, не агент): лаунчер перезапущен вручную после коммитов 2792c8f / 5088447 / cf7faf6, объект «Попова АР» загружен заново и отрендерен. Окна и процессы не закрывать до конца задания.

ПРАВИЛА:
- ТОЛЬКО чтение. Ничего не завершать, не закрывать, не запускать, не менять файлы проекта. Выполнять только команды ниже, в корне репозитория main.
- Вывод ДОСЛОВНО, без пересказа и без «сводок вместо вывода». Если больше 250 строк - разбей на outbox/005-collect-after-stage1-part1.md, part2.md ... и запушь все в origin bridge.
- Без секретов. Ошибка команды - покажи её дословно и иди дальше.
- Не добавляй своих выводов и оценок в сводный файл, только сырой вывод команд и статус ok/failed по каждому пункту.

## A. Процессы и окна
A1. Количество по имени:
```powershell
Get-Process | Where-Object { $_.ProcessName -match '^(acad|accoreconsole|AcLauncher|python|pythonw|powershell|pwsh|FEngineeringLauncher|msedgewebview2|conhost|GoogleDriveFS)$' } | Group-Object ProcessName | Select-Object Name,Count | Format-Table -AutoSize | Out-String -Width 200
```
A2. Полный список (PID, родитель, старт, первые 300 символов командной строки):
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(acad|accoreconsole|AcLauncher|python|pythonw|powershell|pwsh|FEngineeringLauncher)\.exe$' } | Sort-Object Name,CreationDate | Select-Object ProcessId,ParentProcessId,Name,@{n='Start';e={$_.CreationDate}},@{n='Cmd';e={ if ($_.CommandLine) { $_.CommandLine.Substring(0,[Math]::Min(300,$_.CommandLine.Length)) } }} | Format-List | Out-String -Width 400
```
A3. Количество открытых документов в AutoCAD (только чтение через COM):
```powershell
try { $a=[System.Runtime.InteropServices.Marshal]::GetActiveObject('AutoCAD.Application'); "documents open: $($a.Documents.Count)"; foreach($d in $a.Documents){ $d.FullName } } catch { "no active AutoCAD COM: $($_.Exception.Message)" }
```
A4. Окна AutoCAD:
```powershell
Get-Process acad -ErrorAction SilentlyContinue | Select-Object Id,MainWindowHandle,@{n='Title';e={$_.MainWindowTitle}},StartTime | Format-Table -AutoSize | Out-String -Width 300
```

## B. Порты и здоровье
```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8700 -and $_.LocalPort -le 8899 } | Select-Object LocalAddress,LocalPort,OwningProcess,@{n='Proc';e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Format-Table -AutoSize | Out-String -Width 200
try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8780/api/health -TimeoutSec 5).Content } catch { $_.Exception.Message }
Select-String -Path app\backend\dwg_engine.py -Pattern 'USE_GUI_WORKER' | ForEach-Object { "{0}: {1}" -f $_.LineNumber,$_.Line.Trim() }
git log -4 --oneline
```

## C. Логи
```powershell
foreach ($f in 'runtime\logs\launcher_gui.log','runtime\logs\server_startup.log','runtime\logs\server.log') { "### $f"; if (Test-Path $f) { (Get-Item $f | Select-Object Length,LastWriteTime | Out-String).Trim(); Get-Content -Encoding UTF8 -Tail 150 $f } else { 'NOT FOUND' } }
"### errors in server_startup.log (last 80)"
Select-String -Path runtime\logs\server_startup.log -Pattern 'Error','Traceback','WARN','failed','incomplete','Exception' | Select-Object -Last 80 | ForEach-Object { $_.Line }
```

## D. Кэш DWG
D1. Сводка по 40 последним каталогам:
```powershell
Get-ChildItem runtime\cache\dwg -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 40 | ForEach-Object { $f = Get-ChildItem $_.FullName -File -ErrorAction SilentlyContinue; "{0} {1:s} files={2} pdf={3} png={4} tmp={5} manifest={6}" -f $_.Name, $_.LastWriteTime, $f.Count, ($f | Where-Object Extension -eq '.pdf').Count, ($f | Where-Object Extension -eq '.png').Count, ($f | Where-Object { $_.Name -like '*.tmp.*' }).Count, (Test-Path (Join-Path $_.FullName 'manifest.json')) }
```
D2. Геометрия всех PDF и PNG в 20 последних каталогах (размер страницы pt и пиксели):
```powershell
@'
import sys
from pathlib import Path
try:
    import fitz
    from PIL import Image
except Exception as e:
    print("import error:", e)
    sys.exit(0)
root = Path("runtime/cache/dwg")
if not root.exists():
    print("no dwg cache")
    sys.exit(0)
dirs = sorted([d for d in root.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)[:20]
for d in dirs:
    src = ""
    m = d / "manifest.json"
    if m.exists():
        try:
            import json
            src = json.loads(m.read_text(encoding="utf-8-sig")).get("sourceName", "")
        except Exception as e:
            src = "manifest err: %s" % e
    print("==", d.name, src)
    for pdf in sorted(d.glob("page_*.pdf"))[:8]:
        try:
            with fitz.open(str(pdf)) as doc:
                r = doc[0].rect
                print(" ", pdf.name, "pdf_pages=%d" % len(doc), "size_pt=%.0fx%.0f" % (r.width, r.height), "bytes=%d" % pdf.stat().st_size)
        except Exception as e:
            print(" ", pdf.name, "ERR", e)
    for png in sorted(d.glob("page-*.png"))[:8]:
        try:
            with Image.open(png) as im:
                print(" ", png.name, "px=%dx%d" % im.size, "bytes=%d" % png.stat().st_size)
        except Exception as e:
            print(" ", png.name, "ERR", e)
'@ | C:\Python314\python.exe -
```
D3. manifest.json 5 самых свежих каталогов (первые 60 строк каждого):
```powershell
Get-ChildItem runtime\cache\dwg -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object { "### $($_.Name)"; $m = Join-Path $_.FullName 'manifest.json'; if (Test-Path $m) { Get-Content -Encoding UTF8 -TotalCount 60 $m } else { 'NO MANIFEST' } }
```

## E. Кэш PDF (5 последних, содержимое и первые 30 строк manifest.json)
```powershell
Get-ChildItem runtime\cache\pdf -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object { "### $($_.Name) $($_.LastWriteTime.ToString('s'))"; Get-ChildItem $_.FullName -File | Select-Object -First 30 Name,Length | Format-Table -AutoSize | Out-String; $m = Join-Path $_.FullName 'manifest.json'; if (Test-Path $m) { Get-Content -Encoding UTF8 -TotalCount 30 $m } else { 'NO MANIFEST' } }
```

## F. Время рендера (по журналу запросов)
```powershell
Get-Content -Encoding UTF8 runtime\logs\server.log -Tail 600 | Select-String -Pattern 'dwg/model-render','dwg/status','dwg/model-page' | Select-Object -Last 60 | ForEach-Object { $_.Line }
```

Результат - в `.agent_bridge/outbox/005-collect-after-stage1.md` (или -partN) по формату из PROTOCOL.md; запушь в `origin bridge`.
