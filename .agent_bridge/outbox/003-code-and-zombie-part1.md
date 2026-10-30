# Result 003 - Part 1 (Разделы A, B: Воркер печати, Обработчики DPI)
status: ok
branch/commit: ed362f3 (bridge) / 4f44ce1 (main)

## Что выполнено
- A. Воркер печати scripts\dwg_plot_worker.ps1 (строки 140-389, 390-440): ok
- B. Обработчики сервера в app\backend\server.py (model-render, preview, model-page) и DPI: ok

## Вывод команд

### A. Show-Range 'scripts\dwg_plot_worker.ps1' 140 389
```text
140:   try { $document.SetVariable("NOMUTT", 1) } catch {}
141:   try { $document.SetVariable("PROXYNOTICE", 0) } catch {}
142:   try { $document.SetVariable("DRAWORDERCTL", 0) } catch {}
143: 
144:   # Сбор всех пространств листа (Layouts)
145:   $candidateLayouts = @($document.Layouts | Where-Object { -not $_.ModelType } | Sort-Object TabOrder)
146:   $nonEmptyLayouts = @($candidateLayouts | Where-Object { $_.Block.Count -ge 1 })
147: 
148:   $layoutMetadata = @()
149:   foreach ($l in $nonEmptyLayouts) {
150:     $rot = 0
151:     try { $rot = [int]$l.PlotRotation } catch {}
152:     $layoutMetadata += @{
153:       name = [string]$l.Name
154:       tabOrder = [int]$l.TabOrder
155:       plotRotation = $rot
156:       configName = [string]$l.ConfigName
157:       canonicalMediaName = [string]$l.CanonicalMediaName
158:     }
159:   }
160: 
161:   # Уведомление о структуре листов
162:   $startEvent = @{
163:     event = "doc_opened"
164:     inputPath = $InputPath
165:     progId = $usedProgId
166:     openMs = $openMs
167:     totalLayouts = $candidateLayouts.Count
168:     validLayouts = $nonEmptyLayouts.Count
169:     layouts = $layoutMetadata
170:   }
171:   Write-Output ($startEvent | ConvertTo-Json -Compress -Depth 4)
172: 
173:   # Сохраняем начальный манифест структуры листов
174:   $manifestFile = Join-Path $OutputDir "manifest.json"
175:   try {
176:     $itemStat = Get-Item -LiteralPath $InputPath
177:     $epoch = [datetime]'1970-01-01 00:00:00Z'
178:     $mtimeSec = [int64]($itemStat.LastWriteTimeUtc - $epoch).TotalSeconds
179:     $manifestData = [ordered]@{
180:       sourcePath = $InputPath
181:       sourceName = [System.IO.Path]::GetFileName($InputPath)
182:       sourceSize = $itemStat.Length
183:       sourceMtime = $mtimeSec
184:       outputDir = $OutputDir
185:       isComplete = $false
186:       totalLayouts = $candidateLayouts.Count
187:       validLayouts = $nonEmptyLayouts.Count
188:       layouts = $layoutMetadata
189:       completedPages = @{}
190:     }
191:     $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
192:     [System.IO.File]::WriteAllText($manifestFile, ($manifestData | ConvertTo-Json -Depth 5), $utf8NoBom)
193:   } catch {}
194: 
195:   if ($ListOnly) {
196:     exit 0
197:   }
198: 
199:   # Функция настройки плоттера листа (с кэшированием устройств)
200:   function Prepare-LayoutPlotter($layoutObj) {
201:     # ВСЕГДА проверяем, что выбран именно PDF-плоттер (физические принтеры вызывают E_INVALIDARG в PlotToFile)
202:     $curDev = [string]$layoutObj.ConfigName
203:     $isPdfDev = ($curDev -and ($curDev -match "DWG To PDF" -or $curDev -match "AutoCAD PDF" -or $curDev -match "Microsoft Print to PDF"))
204:     if (-not $isPdfDev) {
205:       $preferred = @(
206:         "DWG To PDF.pc3",
207:         "AutoCAD PDF (General Documentation).pc3",
208:         "AutoCAD PDF (High Quality Print).pc3",
209:         "AutoCAD PDF (Smallest File).pc3",
210:         "Microsoft Print to PDF"
211:       )
212:       foreach ($dev in $preferred) {
213:         try {
214:           $layoutObj.ConfigName = $dev
215:           $layoutObj.RefreshPlotDeviceInfo()
216:           break
217:         } catch {}
218:       }
219:     }
220: 
221:     try {
222:       $allMedia = @($layoutObj.GetCanonicalMediaNames())
223:       $curMedia = [string]$layoutObj.CanonicalMediaName
224:       $hasIsoMedia = ($curMedia -and ($curMedia -match "ISO|A3|A4|A2|A1|A0"))
225:       if (-not $hasIsoMedia -and $allMedia.Count -gt 0) {
226:         $preferredMedia = @(
227:           "ISO_full_bleed_A3_(420.00_x_297.00_MM)",
228:           "ISO_A3_(420.00_x_297.00_MM)",
229:           "ISO_full_bleed_A4_(297.00_x_210.00_MM)",
230:           "ISO_A4_(297.00_x_210.00_MM)"
231:         )
232:         foreach ($pm in $preferredMedia) {
233:           if ($allMedia -contains $pm) {
234:             try { $layoutObj.CanonicalMediaName = $pm; break } catch {}
235:           }
236:         }
237:       }
238:     } catch {}
239: 
240:     try { $layoutObj.PlotType = 5 } catch {} # acLayout (5 is acLayout in AutoCAD COM; 4 is acWindow)
241:     $layoutObj.PlotWithLineweights = $true
242:     $layoutObj.PlotWithPlotStyles = $true
243:   }
244: 
245:   # Функция печати одного листа
246:   function Plot-OneLayout($layoutObj) {
247:     $tabOrder = [int]$layoutObj.TabOrder
248:     $name = [string]$layoutObj.Name
249:     $pdfFile = Join-Path $OutputDir ("page_{0:D4}.pdf" -f $tabOrder)
250: 
251:     # Проверка существующего кэша (RESUME, > 4KB исключает пустые/битые файлы)
252:     if ((Test-Path -LiteralPath $pdfFile) -and (Get-Item -LiteralPath $pdfFile).Length -gt 4096) {
253:       $res = @{
254:         event = "sheet_ready"
255:         tabOrder = $tabOrder
256:         name = $name
257:         pdfPath = $pdfFile
258:         bytes = (Get-Item -LiteralPath $pdfFile).Length
259:         fromCache = $true
260:         elapsedMs = 0
261:       }
262:       Write-Output ($res | ConvertTo-Json -Compress)
263:       return
264:     }
265: 
266:     $swPlot = [System.Diagnostics.Stopwatch]::StartNew()
267:     Log-Msg "Activating layout $tabOrder ('$name')..."
268:     $document.ActiveLayout = $layoutObj
269:     $switchMs = $swPlot.ElapsedMilliseconds
270: 
271:     Prepare-LayoutPlotter $layoutObj
272: 
273:     # Попытка 1: стандартная печать acLayout
274:     $swFile = [System.Diagnostics.Stopwatch]::StartNew()
275:     $success = $false
276:     try {
277:       $success = $document.Plot.PlotToFile($pdfFile)
278:     } catch {
279:       Log-Msg "PlotToFile acLayout failed for ${name}: $($_.Exception.Message)"
280:     }
281: 
282:     # Резервный шаг: если acLayout не сработал или сгенерировал файл <= 4096 байт
283:     # (как в чертежах с рамками вне начала координат, например Остров Первых)
284:     $needExtents = (-not $success) -or (-not (Test-Path -LiteralPath $pdfFile)) -or ((Get-Item -LiteralPath $pdfFile).Length -le 4096)
285:     if ($needExtents) {
286:       try {
287:         Log-Msg "Retrying layout $tabOrder ('$name') with acExtents..."
288:         $layoutObj.PlotType = 1 # acExtents
289:         $layoutObj.CenterPlot = $true
290:         $layoutObj.UseStandardScale = $true
291:         $layoutObj.StandardScale = 0 # acScaleToFit
292:         if (Test-Path -LiteralPath $pdfFile) { Remove-Item -LiteralPath $pdfFile -Force -ErrorAction SilentlyContinue }
293:         $success = $document.Plot.PlotToFile($pdfFile)
294:       } catch {
295:         Log-Msg "PlotToFile acExtents retry failed for ${name}: $($_.Exception.Message)"
296:       }
297:     }
298: 
299:     $plotFileMs = $swFile.ElapsedMilliseconds
300:     $totalSheetMs = $swPlot.ElapsedMilliseconds
301: 
302:     if ($success -and (Test-Path -LiteralPath $pdfFile) -and (Get-Item -LiteralPath $pdfFile).Length -gt 4096) {
303:       $res = @{
304:         event = "sheet_ready"
305:         tabOrder = $tabOrder
306:         name = $name
307:         pdfPath = $pdfFile
308:         bytes = (Get-Item -LiteralPath $pdfFile).Length
309:         fromCache = $false
310:         switchMs = $switchMs
311:         plotMs = $plotFileMs
312:         elapsedMs = $totalSheetMs
313:       }
314:       Write-Output ($res | ConvertTo-Json -Compress)
315:       try {
316:         if ($manifestFile -and (Test-Path -LiteralPath $manifestFile)) {
317:           $mf = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
318:           if (-not $mf.completedPages) { $mf | Add-Member -NotePropertyName completedPages -NotePropertyValue (@{}) }
319:           $mf.completedPages | Add-Member -NotePropertyName ([string]$tabOrder) -NotePropertyValue (@{
320:             tabOrder = $tabOrder
321:             name = $name
322:             pdf = $pdfFile
323:             elapsedMs = $totalSheetMs
324:           }) -Force
325:           $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
326:           [System.IO.File]::WriteAllText($manifestFile, ($mf | ConvertTo-Json -Depth 5), $utf8NoBom)
327:         }
328:       } catch {}
329:     } else {
330:       $err = @{
331:         event = "sheet_error"
332:         tabOrder = $tabOrder
333:         name = $name
334:         message = "PlotToFile failed or output file is corrupt"
335:         elapsedMs = $totalSheetMs
336:       }
337:       Write-Output ($err | ConvertTo-Json -Compress)
338:     }
339:     [System.GC]::Collect()
340:   }
341: 
342:   # Сортировка очереди печати: сначала приоритетный лист (если задан), затем остальные
343:   if ($nonEmptyLayouts.Count -gt 0) {
344:     $queue = @()
345:     if ($PriorityTabOrder -ge 0) {
346:       $prio = @($nonEmptyLayouts | Where-Object { $_.TabOrder -eq $PriorityTabOrder })
347:       if ($prio.Count -gt 0) {
348:         $queue += $prio[0]
349:       }
350:     }
351:     foreach ($l in $nonEmptyLayouts) {
352:       if ($l.TabOrder -ne $PriorityTabOrder) {
353:         $queue += $l
354:       }
355:     }
356: 
357:     foreach ($layoutItem in $queue) {
358:       try {
359:         Plot-OneLayout $layoutItem
360:       } catch {
361:         $errEvent = @{
362:           event = "sheet_error"
363:           tabOrder = [int]$layoutItem.TabOrder
364:           name = [string]$layoutItem.Name
365:           message = $_.Exception.Message
366:         }
367:         Write-Output ($errEvent | ConvertTo-Json -Compress)
368:       }
369:     }
370:   } else {
371:     # Сценарий без листов (Model Space Only)
372:     Log-Msg "No paper layouts found. Plotting Model Space..."
373:     $modelLayout = $document.ModelSpace.Layout
374:     $swModel = [System.Diagnostics.Stopwatch]::StartNew()
375:     $modelPdf = Join-Path $OutputDir "page_0000.pdf"
376: 
377:     $devices = @($modelLayout.GetPlotDeviceNames())
378:     foreach ($dev in @("DWG To PDF.pc3", "AutoCAD PDF (General Documentation).pc3", "Microsoft Print to PDF")) {
379:       if ($devices -contains $dev) {
380:         try { $modelLayout.ConfigName = $dev } catch {}
381:         break
382:       }
383:     }
384:     try { $modelLayout.PlotType = 1 } catch {} # acExtents
385:     $modelLayout.CenterPlot = $true
386:     $modelLayout.UseStandardScale = $true
387:     $modelLayout.StandardScale = 0 # acScaleToFit
388:     $modelLayout.PlotWithLineweights = $false
389:     $modelLayout.PlotWithPlotStyles = $true
```

### A. Show-Range 'scripts\dwg_plot_worker.ps1' 390 440
```text
390: 
391:     $success = $document.Plot.PlotToFile($modelPdf)
392:     $ms = $swModel.ElapsedMilliseconds
393:     if ($success -and (Test-Path -LiteralPath $modelPdf) -and (Get-Item -LiteralPath $modelPdf).Length -gt 4096) {
394:       $res = @{
395:         event = "sheet_ready"
396:         tabOrder = 0
397:         name = "Model"
398:         pdfPath = $modelPdf
399:         bytes = (Get-Item -LiteralPath $modelPdf).Length
400:         fromCache = $false
401:         elapsedMs = $ms
402:       }
403:       Write-Output ($res | ConvertTo-Json -Compress)
404:     } else {
405:       Write-Output (@{ event = "sheet_error"; tabOrder = 0; name = "Model"; message = "Model plot failed" } | ConvertTo-Json -Compress)
406:     }
407:   }
408: 
409:   try {
410:     if ($manifestFile -and (Test-Path -LiteralPath $manifestFile)) {
411:       $mf = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
412:       $mf.isComplete = $true
413:       $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
414:       [System.IO.File]::WriteAllText($manifestFile, ($mf | ConvertTo-Json -Depth 5), $utf8NoBom)
415:     }
416:   } catch {}
417:   Write-Output (@{ event = "complete"; totalTimeMs = $swOpen.ElapsedMilliseconds } | ConvertTo-Json -Compress)
418: } finally {
419:   try { [DwgPlotMessageFilter]::Revoke() } catch {}
420:   if ($document) {
421:     try { $document.Close($false) } catch {}
422:     try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null } catch {}
423:   }
424:   if ($app -and $isNewInstance) {
425:     try { $app.Quit() } catch {}
426:     try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
427:     if ($acadPid -gt 0) {
428:       Start-Sleep -Milliseconds 400
429:       try {
430:         $p = Get-Process -Id $acadPid -ErrorAction SilentlyContinue
431:         if ($p) { Stop-Process -Id $acadPid -Force -ErrorAction SilentlyContinue }
432:       } catch {}
433:     }
434:   } elseif ($app) {
435:     try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
436:   }
437:   [System.GC]::Collect()
438:   [System.GC]::WaitForPendingFinalizers()
439: }
```

### B. Show-Around 'app\backend\server.py' (model-render / preview / model-page)
```text
### app\backend\server.py match at line 3483
3480:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3481:             return
3482: 
3483:         if parsed.path == "/api/dwg/model-render":
3484:             try:
3485:                 body = self.read_json()
3486:                 raw_files = body.get("files", [])
3487:                 dpi = int(body.get("dpi") or DEFAULT_PDF_DPI)
3488:                 force = bool(body.get("force", False))
3489:                 if dpi < 72 or dpi > 600:
3490:                     raise ValueError("DPI должен быть в диапазоне 72-600")
3491:                 if not isinstance(raw_files, list) or not raw_files:
3492:                     raise ValueError("Не выбраны DWG-файлы для отображения")
3493:                 if len(raw_files) > 1:
3494:                     raise ValueError("Model Space preview пока создаётся по одному DWG-файлу")
3495:                 documents = [render_dwg_model(Path(str(file_path)), dpi=dpi, force=force) for file_path in raw_files]
3496:                 document_errors = [
3497:                     {"document": document["name"], "path": document["path"], **error}
3498:                     for document in documents
3499:                     for error in document.get("errors", [])
3500:                 ]
3501:                 self.send_json(
3502:                     HTTPStatus.OK,
3503:                     {
3504:                         "dpi": dpi,
3505:                         "documents": documents,
3506:                         "totalPages": sum(document["pages"] for document in documents),
3507:                         "renderedPages": sum(document["renderedPages"] for document in documents),
3508:                         "errors": document_errors,
3509:                         "renderedAt": datetime.now().isoformat(timespec="seconds"),
3510:                     },
3511:                 )
3512:             except (ValueError, FileNotFoundError, RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
3513:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3514:             return
3515: 
3516:         if parsed.path == "/api/dwg/status":
3517:             try:
3518:                 body = self.read_json()
3519:                 raw_file = str(body.get("file", "")).strip()
3520:                 if not raw_file:
3521:                     raise ValueError("Не указан DWG-файл")
3522:                 file_path = Path(raw_file)
3523:                 key = file_cache_key(file_path, "dwg-smart-cad-v3")
3524:                 target_dir = DWG_CACHE_DIR / key
3525:                 manifest_path = target_dir / "manifest.json"
3526: 
3527:                 ready_pages = []
3528:                 empty_pages = []
3529:                 first_content_page = None
3530:                 is_complete = False
3531:                 manifest_data = {}
3532:                 # manifest.json появляется только ПОСЛЕ завершения экспорта. На фазе 0
3533:                 # в кэше лежит лишь header_thumb.png, манифеста нет — и обращение к
3534:                 # total_layouts ниже падало с UnboundLocalError (HTTP 400), из-за чего
3535:                 # фронтенд гасил опрос статуса и HD-рендер никогда не подхватывался.
3536:                 total_layouts = 0
3537:                 if manifest_path.exists():
3538:                     try:
3539:                         manifest_data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
3540:                         is_complete = bool(manifest_data.get("isComplete", False))
3541:                         total_layouts = int(manifest_data.get("totalLayouts", 0)) or len(manifest_data.get("layouts", []))
3542:                     except Exception:
3543:                         pass
### app\backend\server.py match at line 3621
3618:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3619:             return
3620: 
3621:         if parsed.path == "/api/dwg/model-page":
3622:             try:
3623:                 body = self.read_json()
3624:                 raw_file = str(body.get("file", "")).strip()
3625:                 page = int(body.get("page") or 1)
3626:                 # Срез страницы DWG по стандарту: 150 DPI PNG (DWG_PREVIEW_DPI).
3627:                 # Явный dpi клиента уважаем (HiDPI-зум), дефолт 300 запрещен.
3628:                 dpi = int(body.get("dpi") or DWG_PREVIEW_DPI)
3629:                 if dpi < 72 or dpi > 600:
3630:                     raise ValueError("DPI должен быть в диапазоне 72-600")
3631:                 if not raw_file:
3632:                     raise ValueError("Не выбран DWG-файл для отображения")
3633:                 file_path = Path(raw_file)
3634:                 key = file_cache_key(file_path, "dwg-smart-cad-v3")
3635:                 target_dir = DWG_CACHE_DIR / key
3636:                 target_dir.mkdir(parents=True, exist_ok=True)
3637: 
3638:                 try:
3639:                     from app.backend.dwg_engine import render_dwg_page_progressive
3640:                 except ImportError:
3641:                     from dwg_engine import render_dwg_page_progressive
3642: 
3643:                 payload = render_dwg_page_progressive(file_path=file_path, target_dir=target_dir, cache_key=key, page=page, dpi=dpi)
3644:                 self.send_json(HTTPStatus.OK, payload)
3645:             except (ValueError, FileNotFoundError, RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
3646:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3647:             return
3648: 
3649:         if parsed.path == "/api/excel/workbook":
3650:             try:
3651:                 body = self.read_json()
3652:                 raw_file = str(body.get("file", "")).strip()
3653:                 if not raw_file:
3654:                     raise ValueError("Не выбран Excel-файл для отображения")
3655:                 self.send_json(HTTPStatus.OK, excel_workbook_preview(Path(raw_file)))
3656:             except Exception as error:
3657:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3658:             return
3659: 
3660:         if parsed.path == "/api/excel/sheet":
3661:             try:
3662:                 body = self.read_json()
3663:                 raw_file = str(body.get("file", "")).strip()
3664:                 sheet_index = int(body.get("sheetIndex", 0))
3665:                 sheet = excel_sheet_preview(Path(raw_file), sheet_index)
3666:                 self.send_json(HTTPStatus.OK, sheet)
3667:             except Exception as error:
3668:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3669:             return
3670: 
3671: 
3672:         if parsed.path == "/api/preview":
3673:             try:
3674:                 body = self.read_json()
3675:                 raw_file = str(body.get("file", "")).strip()
3676:                 if not raw_file:
3677:                     raise ValueError("Не выбран файл для отображения")
3678:                 if rendering_dispatcher is None:
3679:                     raise RuntimeError("Ядро rendering недоступно (app.rendering)")
3680:                 payload = rendering_dispatcher.get_file_preview(
3681:                     Path(raw_file), runtime_dir=RUNTIME_DIR)
### app\backend\server.py match at line 3672
3669:             return
3670: 
3671: 
3672:         if parsed.path == "/api/preview":
3673:             try:
3674:                 body = self.read_json()
3675:                 raw_file = str(body.get("file", "")).strip()
3676:                 if not raw_file:
3677:                     raise ValueError("Не выбран файл для отображения")
3678:                 if rendering_dispatcher is None:
3679:                     raise RuntimeError("Ядро rendering недоступно (app.rendering)")
3680:                 payload = rendering_dispatcher.get_file_preview(
3681:                     Path(raw_file), runtime_dir=RUNTIME_DIR)
3682:                 self.send_json(HTTPStatus.OK, payload)
3683:             except Exception as error:
3684:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3685:             return
3686: 
3687:         if parsed.path in {"/api/word/preview", "/api/word/document"}:
3688:             try:
3689:                 body = self.read_json()
3690:                 raw_file = str(body.get("file", "")).strip()
3691:                 if not raw_file:
3692:                     raise ValueError("Не выбран Word-файл для отображения")
3693:                 self.send_json(HTTPStatus.OK, word_document_preview(Path(raw_file)))
3694:             except Exception as error:
3695:                 self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
3696:             return
3697: 
3698:         if parsed.path == "/api/open-file":
3699:             started = time.perf_counter()
3700:             raw_file = ""
3701:             target: Path | None = None
3702:             try:
3703:                 body = self.read_json()
3704:                 raw_file = str(body.get("path", "")).strip()
3705:                 if not raw_file:
3706:                     raise ValueError("Не выбран файл для открытия")
3707:                 target = Path(raw_file).expanduser()
3708:                 if not target.exists():
3709:                     raise FileNotFoundError(f"Файл не найден: {target}")
3710:                 opened_path = str(target)
3711: 
3712:                 # Защита от двойного запуска (двойной клик пользователя или повторный вызов)
3713:                 target_key = str(target).casefold()
3714:                 now_ts = time.perf_counter()
3715:                 with _OPEN_FILE_LOCK:
3716:                     last_time = _LAST_OPENED_TARGETS.get(target_key, 0.0)
3717:                     if (now_ts - last_time) < 4.0:
3718:                         self.send_json(
3719:                             HTTPStatus.OK,
3720:                             {
3721:                                 "ok": True,
3722:                                 "path": str(target),
3723:                                 "openedPath": opened_path,
3724:                                 "mode": "deduplicated",
3725:                                 "longPathWarning": None,
3726:                             },
3727:                         )
3728:                         return
3729:                     _LAST_OPENED_TARGETS[target_key] = now_ts
3730:                     if len(_LAST_OPENED_TARGETS) > 100:
3731:                         _LAST_OPENED_TARGETS.clear()
3732:
```

### B. Select-String DEFAULT_PDF_DPI, DWG_PREVIEW_DPI в app\backend\server.py
```text
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:103: DEFAULT_PDF_DPI = 72
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:107: DWG_PREVIEW_DPI = 150
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:459: dpi_tag = f"|dpi={dpi}" if dpi and dpi != DEFAULT_PDF_DPI else ""
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:753: doc = render_pdf(pdf_path, dpi=DEFAULT_PDF_DPI, first_page_only=True)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:803: def render_dwg_model(path: Path, dpi: int = DEFAULT_PDF_DPI, force: bool = False) -> dict:
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2485: dpi: int = DEFAULT_PDF_DPI,
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2720: def render_pdf_page(path: Path, page: int, dpi: int = DEFAULT_PDF_DPI, page_timeout_seconds: int = PDF_PAGE_TIMEOUT_SECONDS) -> dict:
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3398: dpi = int(body.get("dpi") or DEFAULT_PDF_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3433: dpi = int(body.get("dpi") or DEFAULT_PDF_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3487: dpi = int(body.get("dpi") or DEFAULT_PDF_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3568: _rasterize_pdf_page(pdf_file, png_p, DWG_PREVIEW_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3626: # Срез страницы DWG по стандарту: 150 DPI PNG (DWG_PREVIEW_DPI).
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3628: dpi = int(body.get("dpi") or DWG_PREVIEW_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3973: _rasterize_pdf_page(pdf_candidate, target, DWG_PREVIEW_DPI)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3984: dpi = DEFAULT_PDF_DPI
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3987: dpi = manifest.get("dpi", DEFAULT_PDF_DPI)
```