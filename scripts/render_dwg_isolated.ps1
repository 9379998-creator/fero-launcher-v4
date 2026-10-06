param(
  [Parameter(Mandatory = $true)][string]$InputPath,
  [Parameter(Mandatory = $false)][string]$OutputPath = "",
  [Parameter(Mandatory = $false)][string]$FallbackCachePath = "",
  [Parameter(Mandatory = $false)][string]$PythonExe = "",
  [Parameter(Mandatory = $false)][int]$TimeoutPerSheetSec = 180
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
    $document = $app.Documents.Open($InputPath, $true)
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

$result = @{
  ok = $true
  finalPath = $finalDestination
  isLocalFolder = ($finalDestination -eq $OutputPath)
  pageCount = $pagePdfPaths.Count
  mode = "accoreconsole_1sheet_per_proc"
}
Write-Output ($result | ConvertTo-Json -Compress)
