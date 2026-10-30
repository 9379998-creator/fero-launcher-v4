# Task 002 - diagnostics (состояние лаунчера, процессы, порты, кэш DWG/PDF)
mode: read-only
push: no

ПРАВИЛА (важно):
- НИЧЕГО не завершать, не закрывать, не запускать. Не рестартовать лаунчер. Не закрывать окна AutoCAD до конца задания - нужно увидеть текущее состояние как есть.
- Выполнять ТОЛЬКО команды ниже, в рабочей папке main (корень репозитория). Вывод ДОСЛОВНО, без пересказа и без сокращений.
- Если вывод больше 250 строк, разбей результат на файлы outbox/002-diagnostics-part1.md, part2.md ... и запушь все в origin bridge.
- Не выводить секреты (.env, токены, пароли).
- Если команда не сработала - покажи ошибку и переходи к следующей.

## A. Процессы (количество, родители, время старта, командная строка)
A1. Количество по имени:
```powershell
Get-Process | Where-Object { $_.ProcessName -match '^(acad|accoreconsole|AcLauncher|python|pythonw|powershell|pwsh|FEngineeringLauncher|msedgewebview2|conhost|GoogleDriveFS)$' } | Group-Object ProcessName | Select-Object Name,Count | Format-Table -AutoSize | Out-String -Width 200
```
A2. Полный список (PID, родитель, старт, первые 300 символов командной строки):
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(acad|accoreconsole|AcLauncher|python|pythonw|powershell|pwsh|FEngineeringLauncher)\.exe$' } | Sort-Object Name,CreationDate | Select-Object ProcessId,ParentProcessId,Name,@{n='Start';e={$_.CreationDate}},@{n='Cmd';e={ if ($_.CommandLine) { $_.CommandLine.Substring(0,[Math]::Min(300,$_.CommandLine.Length)) } }} | Format-List | Out-String -Width 400
```
A3. Окна AutoCAD (сколько видимых, заголовки):
```powershell
Get-Process acad -ErrorAction SilentlyContinue | Select-Object Id,MainWindowHandle,@{n='Title';e={$_.MainWindowTitle}},StartTime | Format-Table -AutoSize | Out-String -Width 300
```

## B. Порты
B1.
```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8700 -and $_.LocalPort -le 8899 } | Select-Object LocalAddress,LocalPort,OwningProcess,@{n='Proc';e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Format-Table -AutoSize | Out-String -Width 200
```
B2. Состояния соединений на 8780:
```powershell
Get-NetTCPConnection -LocalPort 8780 -ErrorAction SilentlyContinue | Group-Object State | Select-Object Name,Count | Format-Table -AutoSize | Out-String
```
B3. Health (только GET):
```powershell
try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8780/api/health -TimeoutSec 5).Content } catch { $_.Exception.Message }
```

## C. Логи (последние 150 строк)
```powershell
foreach ($f in 'runtime\logs\launcher_gui.log','runtime\logs\server_startup.log','runtime\logs\server.log','runtime\logs\native-front.log') { "### $f"; if (Test-Path $f) { (Get-Item $f | Select-Object Length,LastWriteTime | Out-String).Trim(); Get-Content -Encoding UTF8 -Tail 150 $f } else { 'NOT FOUND' } }
```

## D. Кэш DWG и PDF
D1. Сводка по 40 последним каталогам DWG:
```powershell
Get-ChildItem runtime\cache\dwg -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 40 | ForEach-Object { $f = Get-ChildItem $_.FullName -File -ErrorAction SilentlyContinue; "{0} {1:s} files={2} pdf={3} png={4} manifest={5}" -f $_.Name, $_.LastWriteTime, $f.Count, ($f | Where-Object Extension -eq '.pdf').Count, ($f | Where-Object Extension -eq '.png').Count, (Test-Path (Join-Path $_.FullName 'manifest.json')) }
```
D2. Геометрия PDF-листов и PNG (12 последних каталогов DWG):
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
dirs = sorted([d for d in root.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)[:12]
for d in dirs:
    print("==", d.name)
    for pdf in sorted(d.glob("page_*.pdf"))[:6]:
        try:
            with fitz.open(str(pdf)) as doc:
                r = doc[0].rect
                print(" ", pdf.name, "pdf_pages=%d" % len(doc), "size_pt=%.0fx%.0f" % (r.width, r.height), "bytes=%d" % pdf.stat().st_size)
        except Exception as e:
            print(" ", pdf.name, "ERR", e)
    for png in sorted(d.glob("page-*.png"))[:6]:
        try:
            with Image.open(png) as im:
                print(" ", png.name, "px=%dx%d" % im.size, "bytes=%d" % png.stat().st_size)
        except Exception as e:
            print(" ", png.name, "ERR", e)
'@ | C:\Python314\python.exe -
```
D3. manifest.json 3 самых свежих каталогов DWG (первые 80 строк каждого):
```powershell
Get-ChildItem runtime\cache\dwg -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { "### $($_.Name)"; $m = Join-Path $_.FullName 'manifest.json'; if (Test-Path $m) { Get-Content -Encoding UTF8 -TotalCount 80 $m } else { 'NO MANIFEST' } }
```
D4. 5 последних каталогов PDF-кэша: содержимое и первые 40 строк manifest.json:
```powershell
Get-ChildItem runtime\cache\pdf -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object { "### $($_.Name) $($_.LastWriteTime.ToString('s'))"; Get-ChildItem $_.FullName -File | Select-Object -First 30 Name,Length | Format-Table -AutoSize | Out-String; $m = Join-Path $_.FullName 'manifest.json'; if (Test-Path $m) { Get-Content -Encoding UTF8 -TotalCount 40 $m } else { 'NO MANIFEST' } }
```

## E. Объект и настройки
Путь объекта: H:\Общие диски\007_Коммерческий отдел\ОБЪЕКТЫ 2026\13_Попова_38_Стройтрест\Попова АР
E1. Состав папки объекта (расширения и количество):
```powershell
$p = 'H:\Общие диски\007_Коммерческий отдел\ОБЪЕКТЫ 2026\13_Попова_38_Стройтрест\Попова АР'; "exists=$(Test-Path -LiteralPath $p)"; if (Test-Path -LiteralPath $p) { Get-ChildItem -LiteralPath $p -Recurse -File -ErrorAction SilentlyContinue | Group-Object Extension | Select-Object Name,Count | Sort-Object Count -Descending | Format-Table -AutoSize | Out-String }
```
E1b. Тип диска H: и состояние файлов (скачаны ли на компьютер или это заглушки потоковой загрузки):
```powershell
Get-PSDrive H -ErrorAction SilentlyContinue | Format-List Name,Provider,Root,Used,Free | Out-String
Get-Volume -DriveLetter H -ErrorAction SilentlyContinue | Format-List DriveLetter,FileSystemLabel,FileSystem,DriveType,Size,SizeRemaining | Out-String
$p = 'H:\Общие диски\007_Коммерческий отдел\ОБЪЕКТЫ 2026\13_Попова_38_Стройтрест\Попова АР'; Get-ChildItem -LiteralPath $p -Recurse -File -Include *.dwg,*.pdf -ErrorAction SilentlyContinue | Group-Object { $_.Extension + ' | ' + $_.Attributes.ToString() } | Select-Object Name,Count | Format-Table -AutoSize | Out-String -Width 200
```
E1c. 15 самых больших DWG/PDF объекта (имя, размер, дата):
```powershell
$p = 'H:\Общие диски\007_Коммерческий отдел\ОБЪЕКТЫ 2026\13_Попова_38_Стройтрест\Попова АР'; Get-ChildItem -LiteralPath $p -Recurse -File -Include *.dwg,*.pdf -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 15 Name,@{n='MB';e={[math]::Round($_.Length/1MB,1)}},LastWriteTime | Format-Table -AutoSize | Out-String -Width 250
```
E2. Настройки нативных приложений (если файл не содержит секретов):
```powershell
Get-Content -Encoding UTF8 runtime\native_apps.json
```
E3. Установленные версии AutoCAD:
```powershell
Get-ChildItem 'C:\Program Files\Autodesk' -Directory -ErrorAction SilentlyContinue | Select-Object Name
```

## F. Кто запускает AutoCAD в коде
```powershell
Select-String -Path app\backend\*.py,app\*.pyw,app\rendering\*.py,scripts\*.ps1,scripts\*.py -Pattern 'AutoCAD.Application','CreateObject','ComObject','AcLauncher','Start-Process','/Automation','acad.exe' | ForEach-Object { "{0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim() }
```

## G. Скрипт воркера (строки 1-250 с номерами)
```powershell
$i=0; Get-Content -Encoding UTF8 scripts\dwg_plot_worker.ps1 | ForEach-Object { $i++; if ($i -le 250) { "{0}: {1}" -f $i, $_ } }
```

Результат - в `.agent_bridge/outbox/002-diagnostics.md` (или -partN) по формату из PROTOCOL.md; запушь в `origin bridge`.
