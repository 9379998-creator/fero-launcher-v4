# Task 003 - фрагменты кода + завершение зависшего сервера PID 15128
mode: apply
push: no

ПРАВИЛА:
- Пункты A-E: ТОЛЬКО чтение. Вывод дословно, с номерами строк, без пересказа и сокращений. Если вывод больше 250 строк - разбей на файлы outbox/003-code-and-zombie-part1.md, part2.md ... и запушь все в origin bridge.
- Единственное действие, меняющее состояние, - пункт Z (завершить процесс PID 15128 при выполнении условий). Больше НИЧЕГО не завершать и не закрывать. Не трогать acad.exe (в том числе PID 26832), текущий сервер (PID 32432) и лаунчер (PID 26668).
- Не запускать сервер, не менять файлы проекта, не трогать историю main.
- Не выводить секреты (.env, токены, пароли, ключи).
- Если команда не сработала - покажи ошибку и переходи к следующей. Рабочая папка: корень репозитория main.

Сначала определи в сеансе две функции (они только читают):
```powershell
function Show-Range($file,$a,$b){ $i=0; Get-Content -Encoding UTF8 $file | ForEach-Object { $i++; if($i -ge $a -and $i -le $b){ "{0}: {1}" -f $i,$_ } } }
function Show-Around($file,$pattern,$before,$after){ $lines=@(Get-Content -Encoding UTF8 $file); for($i=0;$i -lt $lines.Count;$i++){ if($lines[$i] -match $pattern){ $s=[Math]::Max(0,$i-$before); $e=[Math]::Min($lines.Count-1,$i+$after); "### $file match at line $($i+1)"; for($j=$s;$j -le $e;$j++){ "{0}: {1}" -f ($j+1),$lines[$j] } } } }
```

## A. Воркер печати (scripts\dwg_plot_worker.ps1)
```powershell
Show-Range 'scripts\dwg_plot_worker.ps1' 140 389
Show-Range 'scripts\dwg_plot_worker.ps1' 390 440
```

## B. Обработчики сервера: откуда берётся DPI для DWG
```powershell
Show-Around 'app\backend\server.py' 'parsed\.path == "/api/dwg/model-render"|parsed\.path == "/api/preview"|parsed\.path == "/api/dwg/model-page"' 3 60
Select-String -Path app\backend\server.py -Pattern 'DEFAULT_PDF_DPI','DWG_PREVIEW_DPI' | ForEach-Object { "{0}:{1}: {2}" -f $_.Path,$_.LineNumber,$_.Line.Trim() }
```

## C. Модули rendering (целиком)
```powershell
Show-Range 'app\rendering\dispatcher.py' 1 159
Show-Range 'app\rendering\engine_dwg_pdf.py' 1 109
```

## D. Фронтенд (app\frontend\app.js): DPI, выбор кэша PDF, запросы рендера
```powershell
Select-String -Path app\frontend\app.js -Pattern 'dpi','firstPageOnly','/api/dwg/model-render','/api/dwg/model-page','/api/preview','/api/pdf/render' | ForEach-Object { "{0}: {1}" -f $_.LineNumber,$_.Line.Trim() }
Show-Range 'app\frontend\app.js' 2660 2715
Show-Range 'app\frontend\app.js' 4100 4220
Show-Range 'app\frontend\app.js' 4640 4730
Show-Range 'app\frontend\app.js' 4880 4935
```

## E. DWG-движок: чтение листов без AutoCAD
```powershell
Show-Range 'app\backend\dwg_engine.py' 224 473
Show-Range 'app\backend\dwg_engine.py' 474 512
```

## Z. Зависший сервер PID 15128 (единственный пункт с изменением состояния)
Условия: имя pythonw.exe, командная строка содержит fero-launcher-v4\app\backend\server.py, дата запуска раньше 2026-10-19. Если условия не выполнены - НЕ убивать, вывести данные процесса. Если taskkill вернул ошибку (например «Отказано в доступе») - покажи её дословно и НЕ пытайся повышать права и другими способами.
```powershell
$p = Get-CimInstance Win32_Process -Filter "ProcessId=15128" -ErrorAction SilentlyContinue
if ($p) { $p | Format-List ProcessId,ParentProcessId,Name,CreationDate,CommandLine | Out-String -Width 300 } else { 'PID 15128 not found (already gone)' }
if ($p -and $p.Name -eq 'pythonw.exe' -and $p.CommandLine -match 'fero-launcher-v4\\app\\backend\\server\.py' -and $p.CreationDate -lt (Get-Date '2026-10-19')) { & taskkill /F /T /PID 15128 2>&1; "taskkill exit code: $LASTEXITCODE" } elseif ($p) { 'PRECONDITION FAILED - process NOT killed' }
Start-Sleep -Seconds 2
Get-Process -Id 15128 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime | Out-String
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8700 -and $_.LocalPort -le 8899 } | Select-Object LocalPort,OwningProcess | Format-Table -AutoSize | Out-String
try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8780/api/health -TimeoutSec 5).StatusCode } catch { $_.Exception.Message }
```

Результат - в `.agent_bridge/outbox/003-code-and-zombie.md` (или -partN) по формату из PROTOCOL.md; запушь в `origin bridge`.
