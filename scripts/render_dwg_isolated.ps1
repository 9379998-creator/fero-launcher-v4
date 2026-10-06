param(
  [Parameter(Mandatory = $true)][string]$InputPath,
  [Parameter(Mandatory = $false)][string]$OutputPath = "",
  [Parameter(Mandatory = $false)][string]$FallbackCachePath = "",
  [Parameter(Mandatory = $false)][string]$PythonExe = "",
  [Parameter(Mandatory = $false)][int]$TimeoutPerSheetSec = 180,
  [Parameter(Mandatory = $false)][switch]$GenerateHtml
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
  throw "DWG file not found: $InputPath"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = [System.IO.Path]::ChangeExtension($InputPath, ".pdf")
}

$outputDir = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outputDir) -and -not (Test-Path -LiteralPath $outputDir)) {
  try { New-Item -ItemType Directory -Force -Path $outputDir | Out-Null } catch {}
}

# Resolve Python interpreter
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  foreach ($cmd in @("python", "pythonw", "py")) {
    try {
      $found = (Get-Command $cmd -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
      if ($found) { $PythonExe = $found; break }
    } catch {}
  }
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  throw "Python interpreter not found: pass -PythonExe or install Python."
}

# Load native accoreconsole helper
$nativeExportScript = Join-Path $PSScriptRoot 'Invoke-NativeDwgPdfExport.ps1'
if (-not (Test-Path -LiteralPath $nativeExportScript)) {
  throw "Invoke-NativeDwgPdfExport.ps1 not found in $PSScriptRoot"
}
. $nativeExportScript
$accore = Find-NativeAccoreConsole
if (-not $accore) {
  throw "accoreconsole.exe not found"
}

# Deterministic cache directory based on MD5 of input path
$fileId = [System.BitConverter]::ToString([System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($InputPath))).Replace("-","").Substring(0,12)
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("FEng_dwg_" + $fileId)
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$totalSw = [System.Diagnostics.Stopwatch]::StartNew()
Write-Output ("START_PROCESS input={0} cacheDir={1}" -f $InputPath, $tempDir)

if (-not ([System.Management.Automation.PSTypeName]'LauncherWin32').Type) {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class LauncherWin32 {
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@
}

if (-not ([System.Management.Automation.PSTypeName]'LauncherMessageFilter').Type) {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[ComImport(), InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("00000016-0000-0000-C000-000000000046")]
public interface IOleMessageFilter
{
    [PreserveSig] int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo);
    [PreserveSig] int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType);
    [PreserveSig] int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType);
}

public class LauncherMessageFilter : IOleMessageFilter
{
    [DllImport("ole32.dll")] private static extern int CoRegisterMessageFilter(IOleMessageFilter newFilter, out IOleMessageFilter oldFilter);
    public static void Register() {
        IOleMessageFilter newFilter = new LauncherMessageFilter();
        IOleMessageFilter oldFilter = null;
        CoRegisterMessageFilter(newFilter, out oldFilter);
    }
    public static void Revoke() {
        IOleMessageFilter oldFilter = null;
        CoRegisterMessageFilter(null, out oldFilter);
    }
    public int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo) { return 0; }
    public int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType) {
        if (dwRejectType == 2) return 100;
        return -1;
    }
    public int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType) { return 2; }
}
"@
}
[LauncherMessageFilter]::Register()

# 1. Discover Layouts via fast AutoCAD COM query (read-only metadata, closes immediately)
$layouts = @()
$app = $null
$document = $null
$cadPid = 0

try {
  $comProgIds = @(
    "AutoCAD.Application.25",
    "AutoCAD.Application.24.3",
    "AutoCAD.Application.24.2",
    "AutoCAD.Application.24.1",
    "AutoCAD.Application.24.0",
    "AutoCAD.Application.24",
    "AutoCAD.Application.23.1",
    "AutoCAD.Application.23",
    "AutoCAD.Application"
  )
  foreach ($progId in $comProgIds) {
    try {
      $app = New-Object -ComObject $progId -ErrorAction Stop
      if ($app) { break }
    } catch {}
  }

  if ($app) {
    try {
      $hwnd = [IntPtr]::new([long]$app.HWND)
      [uint32]$pidOut = 0
      [void][LauncherWin32]::GetWindowThreadProcessId($hwnd, [ref]$pidOut)
      if ($pidOut -gt 0) { $cadPid = [int]$pidOut }
    } catch {}
    $app.Visible = $false
    $openAttempts = 0
    while (-not $document -and $openAttempts -lt 3) {
      $openAttempts++
      try {
        $document = $app.Documents.Open($InputPath, $true)
      } catch {
        if ($openAttempts -ge 3) { throw }
        Start-Sleep -Seconds 5
      }
    }
    foreach ($lay in $document.Layouts) {
      if (-not $lay.ModelType -and $lay.Block.Count -gt 1) {
        $layouts += [PSCustomObject]@{
          TabOrder = [int]$lay.TabOrder
          Name     = [string]$lay.Name
        }
      }
    }
  }
} catch {
  Write-Output ("WARN: COM layout discovery failed: {0}" -f $_)
} finally {
  try { [LauncherMessageFilter]::Revoke() } catch {}
  if ($document) {
    try { $document.Close($false) } catch {}
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null } catch {}
  }
  if ($app) {
    try { $app.Quit() } catch {}
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
  }
  [System.GC]::Collect()
  if ($cadPid -gt 0) {
    $deadline = (Get-Date).AddSeconds(3)
    while ((Get-Date) -lt $deadline) {
      $p = Get-Process -Id $cadPid -ErrorAction SilentlyContinue
      if (-not $p -or $p.HasExited) { break }
      Start-Sleep -Milliseconds 200
    }
    try {
      $p = Get-Process -Id $cadPid -ErrorAction SilentlyContinue
      if ($p -and -not $p.HasExited) {
        Stop-Process -Id $cadPid -Force -ErrorAction SilentlyContinue
      }
    } catch {}
  }
}

$sortedLayouts = @($layouts | Sort-Object TabOrder)
Write-Output ("LAYOUTS_DISCOVERED count={0}" -f $sortedLayouts.Count)

$pagePdfPaths = [System.Collections.Generic.List[string]]::new()
$ansiEncoding = [System.Text.Encoding]::GetEncoding(1251)

if ($sortedLayouts.Count -gt 0) {
  # 2. Render each layout strictly 1 sheet per process via accoreconsole.exe
  $sheetIndex = 0
  foreach ($item in $sortedLayouts) {
    $sheetIndex++
    $tabOrder = $item.TabOrder
    $layoutName = $item.Name
    $pageFile = Join-Path $tempDir ("page_{0:D4}.pdf" -f $tabOrder)

    # Resume support: skip if valid PDF already exists in cache
    if ((Test-Path -LiteralPath $pageFile) -and (Get-Item -LiteralPath $pageFile).Length -gt 1024) {
      Write-Output ("PAGE_EXISTS: tabOrder={0} name='{1}' using cached page" -f $tabOrder, $layoutName)
      $pagePdfPaths.Add($pageFile)
      continue
    }

    Write-Output ("RENDERING_SHEET [{0}/{1}]: tabOrder={2} name='{3}'" -f $sheetIndex, $sortedLayouts.Count, $tabOrder, $layoutName)

    # Generate single-sheet SCR script
    $scrFile = Join-Path $tempDir ("render_sheet_{0:D4}.scr" -f $tabOrder)
    $normalizedOut = $pageFile.Replace('\', '/')
    $scrLines = @(
      '(setvar "EXPERT" 5)',
      '(setvar "BACKGROUNDPLOT" 0)',
      '(setvar "FILEDIA" 0)',
      '(setvar "CMDDIA" 0)',
      ('(setvar "CTAB" "{0}")' -f $layoutName),
      ('(command "_.-EXPORT" "_PDF" "_C" "_N" "{0}")' -f $normalizedOut),
      '_.QUIT',
      '_N'
    )
    [System.IO.File]::WriteAllLines($scrFile, $scrLines, $ansiEncoding)

    # Run accoreconsole.exe in isolated child process
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $accore
    $psi.Arguments = ('/i "{0}" /s "{1}" /readonly' -f $InputPath, $scrFile)
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $proc = [System.Diagnostics.Process]::Start($psi)
    try {
      $outTask = $proc.StandardOutput.ReadToEndAsync()
      $errTask = $proc.StandardError.ReadToEndAsync()
      if (-not $proc.WaitForExit($TimeoutPerSheetSec * 1000)) {
        try { $proc.Kill() } catch {}
        Write-Output ("TIMEOUT on layout {0} ('{1}') after {2}s" -f $tabOrder, $layoutName, $TimeoutPerSheetSec)
      }
    } finally {
      try { if (-not $proc.HasExited) { $proc.Kill() } } catch {}
      try { $proc.Dispose() } catch {}
    }
    $sw.Stop()

    if ((Test-Path -LiteralPath $pageFile) -and (Get-Item -LiteralPath $pageFile).Length -gt 1024) {
      $pagePdfPaths.Add($pageFile)
      Write-Output ("PROGRESS layout={0} done={1}/{2} elapsed={3:N1}s file={4}" -f $tabOrder, $pagePdfPaths.Count, $sortedLayouts.Count, ($sw.ElapsedMilliseconds / 1000.0), [System.IO.Path]::GetFileName($pageFile))
    } else {
      Write-Output ("WARN: Failed to export layout {0} ('{1}')" -f $tabOrder, $layoutName)
    }
  }
}

# 3. Fallback: if no layouts were rendered, export Model space
if ($pagePdfPaths.Count -eq 0) {
  Write-Output "No layouts found or exported. Falling back to Model space export..."
  $modelPdf = Join-Path $tempDir "page_model.pdf"
  $scrFile = Join-Path $tempDir "render_model.scr"
  $normalizedOut = $modelPdf.Replace('\', '/')
  $scrLines = @(
    '(setvar "EXPERT" 5)',
    '(setvar "BACKGROUNDPLOT" 0)',
    '(setvar "FILEDIA" 0)',
    '(setvar "CMDDIA" 0)',
    '(setvar "CTAB" "Model")',
    ('(command "_.-EXPORT" "_PDF" "_E" "_N" "{0}")' -f $normalizedOut),
    '_.QUIT',
    '_N'
  )
  [System.IO.File]::WriteAllLines($scrFile, $scrLines, $ansiEncoding)

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $accore
  $psi.Arguments = ('/i "{0}" /s "{1}" /readonly' -f $InputPath, $scrFile)
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden

  $proc = [System.Diagnostics.Process]::Start($psi)
  if ($proc.WaitForExit($TimeoutPerSheetSec * 1000)) {
    if ((Test-Path -LiteralPath $modelPdf) -and (Get-Item -LiteralPath $modelPdf).Length -gt 1024) {
      $pagePdfPaths.Add($modelPdf)
    }
  } else {
    try { $proc.Kill() } catch {}
  }
}

if ($pagePdfPaths.Count -eq 0) {
  throw "Failed to render any sheets or model space from DWG: $InputPath"
}

# 4. Merge all generated single-sheet PDFs into final combined PDF
$tempCombinedPdf = Join-Path $tempDir "combined.pdf"
if ($pagePdfPaths.Count -eq 1) {
  Copy-Item -LiteralPath $pagePdfPaths[0] -Destination $tempCombinedPdf -Force
} else {
  $mergeScript = @'
import sys
try:
    import fitz
    doc = fitz.open()
    for p in sys.argv[2:]:
        with fitz.open(p) as page_doc:
            doc.insert_pdf(page_doc)
    doc.save(sys.argv[1])
    doc.close()
except ImportError:
    import pypdf
    writer = pypdf.PdfWriter()
    for p in sys.argv[2:]:
        reader = pypdf.PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    with open(sys.argv[1], "wb") as f:
        writer.write(f)
'@
  $mergePyFile = Join-Path $tempDir "merge.py"
  [System.IO.File]::WriteAllText($mergePyFile, $mergeScript, [System.Text.Encoding]::UTF8)

  $psi = [System.Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $PythonExe
  $psi.Arguments = "`"$mergePyFile`" `"$tempCombinedPdf`" " + (($pagePdfPaths | ForEach-Object { "`"$_`"" }) -join " ")
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
  $psi.RedirectStandardError = $true
  $pyProc = [System.Diagnostics.Process]::Start($psi)
  $pyProc.WaitForExit(120000)
  if ($pyProc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $tempCombinedPdf)) {
    $err = $pyProc.StandardError.ReadToEnd()
    throw "PDF merge failed: $err"
  }
}

# 5. Copy to target destination
$finalDestination = $OutputPath
$writeSuccess = $false
try {
  Copy-Item -LiteralPath $tempCombinedPdf -Destination $OutputPath -Force -ErrorAction Stop
  $writeSuccess = $true
} catch {
  if (-not [string]::IsNullOrWhiteSpace($FallbackCachePath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $FallbackCachePath) | Out-Null
    Copy-Item -LiteralPath $tempCombinedPdf -Destination $FallbackCachePath -Force
    $finalDestination = $FallbackCachePath
    $writeSuccess = $true
  } else {
    throw "Failed to write PDF to target '$OutputPath': $_"
  }
}

# 6. Generate standalone interactive HTML (always alongside PDF for full DWG HTML viewer experience)
$htmlDestination = ""
if ($true) {
  try {
    $targetHtmlPath = [System.IO.Path]::ChangeExtension($finalDestination, ".html")
    $genHtmlScript = @'
import sys, os, base64, html
import fitz

pdf_path = sys.argv[1]
html_out = sys.argv[2]
doc_title = os.path.basename(sys.argv[3]) if len(sys.argv) > 3 else os.path.basename(pdf_path)

doc = fitz.open(pdf_path)
page_count = len(doc)
pages_data = []

for i in range(page_count):
    page = doc[i]
    rect = page.rect
    # 150 DPI render for clear architectural text & mullions
    pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72.0, 150 / 72.0), alpha=False)
    img_b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")
    pages_data.append({
        "num": i + 1,
        "width": rect.width,
        "height": rect.height,
        "pix_width": pix.width,
        "pix_height": pix.height,
        "img": f"data:image/png;base64,{img_b64}"
    })
doc.close()

# Generate self-contained standalone HTML shell
html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(doc_title)}</title>
<style>
  :root {{
    --bg-main: #1e1e24;
    --bg-panel: #282830;
    --text-primary: #e6e6eb;
    --text-secondary: #9a9ab0;
    --accent: #3a86ff;
    --accent-hover: #2670e8;
    --border: #383844;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-main);
    color: var(--text-primary);
    overflow: hidden;
  }}
  header {{
    height: 48px;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 10;
  }}
  .title-group {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .badge {{
    background: var(--accent);
    color: #fff;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
  }}
  .doc-title {{
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 50vw;
  }}
  .controls {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  button {{
    background: #33333d;
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
  }}
  button:hover {{ background: #40404e; }}
  .main-layout {{
    display: flex;
    flex: 1;
    overflow: hidden;
  }}
  aside {{
    width: 220px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .thumb-card {{
    background: #202026;
    border: 2px solid transparent;
    border-radius: 6px;
    padding: 6px;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .thumb-card:hover {{ border-color: #555566; }}
  .thumb-card.active {{ border-color: var(--accent); background: #262a36; }}
  .thumb-card img {{
    width: 100%;
    height: auto;
    border-radius: 4px;
    display: block;
    background: #fff;
  }}
  .thumb-label {{
    font-size: 11px;
    color: var(--text-secondary);
    text-align: center;
    margin-top: 4px;
  }}
  main {{
    flex: 1;
    overflow: auto;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 24px;
    background: #18181c;
  }}
  .viewport {{
    display: flex;
    flex-direction: column;
    gap: 24px;
    align-items: center;
  }}
  .page-container {{
    background: #fff;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    border-radius: 4px;
    overflow: hidden;
  }}
  .page-container img {{
    display: block;
    width: 100%;
    height: auto;
  }}
</style>
</head>
<body>
<header>
  <div class="title-group">
    <span class="badge">DWG HTML</span>
    <span class="doc-title">{html.escape(doc_title)}</span>
  </div>
  <div class="controls">
    <span style="font-size: 12px; color: var(--text-secondary);">Страниц: {page_count}</span>
    <button onclick="window.print()">🖨️ Печать</button>
  </div>
</header>
<div class="main-layout">
  <aside>
"""

for p in pages_data:
    html_content += f"""    <div class="thumb-card" id="thumb-{p['num']}" onclick="scrollToPage({p['num']})">
      <img src="{p['img']}" loading="lazy" alt="Лист {p['num']}">
      <div class="thumb-label">Лист {p['num']}</div>
    </div>
"""

html_content += f"""  </aside>
  <main id="scroll-main">
    <div class="viewport">
"""

for p in pages_data:
    html_content += f"""      <div class="page-container" id="page-{p['num']}" style="max-width: min(100%, 1400px);">
        <img src="{p['img']}" alt="Лист {p['num']}">
      </div>
"""

html_content += """    </div>
  </main>
</div>
<script>
  function scrollToPage(num) {
    const el = document.getElementById('page-' + num);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
    document.querySelectorAll('.thumb-card').forEach(c => c.classList.remove('active'));
    const thumb = document.getElementById('thumb-' + num);
    if (thumb) thumb.classList.add('active');
  }
</script>
</body>
</html>
"""

with open(html_out, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"HTML written to {html_out} ({len(html_content)} bytes)")
'@
    $genPyFile = Join-Path $tempDir "make_html.py"
    [System.IO.File]::WriteAllText($genPyFile, $genHtmlScript, [System.Text.Encoding]::UTF8)

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $PythonExe
    $psi.Arguments = "`"$genPyFile`" `"$finalDestination`" `"$targetHtmlPath`" `"$InputPath`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.RedirectStandardError = $true
    $pyProc = [System.Diagnostics.Process]::Start($psi)
    $pyProc.WaitForExit(180000)
    if ($pyProc.ExitCode -eq 0 -and (Test-Path -LiteralPath $targetHtmlPath)) {
      $htmlDestination = $targetHtmlPath
      Write-Output ("HTML_GENERATED path={0}" -f $htmlDestination)
    }
  } catch {
    Write-Output ("WARN: HTML generation failed: {0}" -f $_)
  }
}

$totalSw.Stop()
$elapsedSec = [math]::Round($totalSw.ElapsedMilliseconds / 1000.0, 1)
$elapsedMin = [math]::Floor($elapsedSec / 60)
$remSec = [math]::Round($elapsedSec % 60, 1)
$timeFormatted = ("{0} мин {1} сек" -f $elapsedMin, $remSec)

$result = @{
  ok = $true
  finalPath = $finalDestination
  isLocalFolder = ($finalDestination -eq $OutputPath)
  pageCount = $pagePdfPaths.Count
  mode = "accoreconsole_1sheet_per_proc"
  elapsedSeconds = $elapsedSec
  elapsedFormatted = $timeFormatted
  timePerSheetSec = if ($pagePdfPaths.Count -gt 0) { [math]::Round($elapsedSec / $pagePdfPaths.Count, 1) } else { 0 }
  htmlPath = $htmlDestination
}
Write-Output ("COMPLETED in {0} ({1}s total, ~{2}s per sheet)" -f $timeFormatted, $elapsedSec, $result.timePerSheetSec)
Write-Output ($result | ConvertTo-Json -Compress)
