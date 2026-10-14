param(
  [Parameter(Mandatory = $true)][string]$InputPath,
  [Parameter(Mandatory = $true)][string]$OutputDir,
  [Parameter(Mandatory = $false)][int]$PriorityTabOrder = -1,
  [Parameter(Mandatory = $false)][switch]$ListOnly,
  [Parameter(Mandatory = $false)][string]$LogFile = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
  Write-Output (@{ event = "error"; message = "DWG file not found: $InputPath" } | ConvertTo-Json -Compress)
  exit 1
}

if (-not (Test-Path -LiteralPath $OutputDir)) {
  New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

function Log-Msg([string]$text) {
  if ($LogFile) {
    try {
      $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss.fff")
      Add-Content -LiteralPath $LogFile -Value "[$ts] $text" -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
  }
}

# 1. Регистрация IOleMessageFilter для перехвата сообщений COM/RPC (чтобы AutoCAD не отваливался при занятости)
if (-not ([System.Management.Automation.PSTypeName]'DwgPlotMessageFilter').Type) {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[ComImport(), InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("00000016-0000-0000-C000-000000000046")]
public interface IOleMessageFilter {
    [PreserveSig] int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo);
    [PreserveSig] int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType);
    [PreserveSig] int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType);
}

public class DwgPlotMessageFilter : IOleMessageFilter {
    [DllImport("ole32.dll")] private static extern int CoRegisterMessageFilter(IOleMessageFilter newFilter, out IOleMessageFilter oldFilter);
    public static void Register() {
        IOleMessageFilter newFilter = new DwgPlotMessageFilter();
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
[DwgPlotMessageFilter]::Register()

# 2. Подключение к AutoCAD COM
$comProgIds = @(
  "AutoCAD.Application.25",
  "AutoCAD.Application.24.3",
  "AutoCAD.Application.24.2",
  "AutoCAD.Application.24.1",
  "AutoCAD.Application.24.0",
  "AutoCAD.Application.24",
  "AutoCAD.Application.23.1",
  "AutoCAD.Application.23",
  "AutoCAD.Application.22",
  "AutoCAD.Application"
)

$app = $null
$usedProgId = ""
foreach ($progId in $comProgIds) {
  try {
    $app = New-Object -ComObject $progId -ErrorAction Stop
    if ($app) {
      $usedProgId = $progId
      break
    }
  } catch {}
}

if (-not $app) {
  Write-Output (@{ event = "error"; message = "AutoCAD COM application not found" } | ConvertTo-Json -Compress)
  exit 1
}

$app.Visible = $false
$document = $null

try {
  Log-Msg "Opening document: $InputPath"
  $swOpen = [System.Diagnostics.Stopwatch]::StartNew()
  
  $openAttempts = 0
  while (-not $document -and $openAttempts -lt 3) {
    $openAttempts++
    try {
      $document = $app.Documents.Open($InputPath, $true) # ReadOnly = True
    } catch {
      if ($openAttempts -ge 3) { throw }
      Start-Sleep -Seconds 5
    }
  }
  $openMs = $swOpen.ElapsedMilliseconds
  Log-Msg "Opened in $openMs ms"

  # Оптимизация системных переменных чертежа для ускорения печати
  try { $document.SetVariable("LAYOUTREGENCTL", 2) } catch {}
  try { $document.SetVariable("REGENMODE", 0) } catch {}
  try { $document.SetVariable("BACKGROUNDPLOT", 0) } catch {}
  try { $document.SetVariable("EXPERT", 5) } catch {}
  try { $document.SetVariable("FILEDIA", 0) } catch {}
  try { $document.SetVariable("CMDDIA", 0) } catch {}
  try { $document.SetVariable("PROXYNOTICE", 0) } catch {}
  try { $document.SetVariable("DRAWORDERCTL", 0) } catch {}

  # Сбор всех пространств листа (Layouts)
  $candidateLayouts = @($document.Layouts | Where-Object { -not $_.ModelType } | Sort-Object TabOrder)
  $nonEmptyLayouts = @($candidateLayouts | Where-Object { $_.Block.Count -gt 1 })

  $layoutMetadata = @()
  foreach ($l in $nonEmptyLayouts) {
    $rot = 0
    try { $rot = [int]$l.PlotRotation } catch {}
    $layoutMetadata += @{
      name = [string]$l.Name
      tabOrder = [int]$l.TabOrder
      plotRotation = $rot
      configName = [string]$l.ConfigName
      canonicalMediaName = [string]$l.CanonicalMediaName
    }
  }

  # Уведомление о структуре листов
  $startEvent = @{
    event = "doc_opened"
    inputPath = $InputPath
    progId = $usedProgId
    openMs = $openMs
    totalLayouts = $candidateLayouts.Count
    validLayouts = $nonEmptyLayouts.Count
    layouts = $layoutMetadata
  }
  Write-Output ($startEvent | ConvertTo-Json -Compress -Depth 4)

  # Сохраняем начальный манифест структуры листов
  $manifestFile = Join-Path $OutputDir "manifest.json"
  try {
    $itemStat = Get-Item -LiteralPath $InputPath
    $manifestData = [ordered]@{
      sourcePath = $InputPath
      sourceName = [System.IO.Path]::GetFileName($InputPath)
      sourceSize = $itemStat.Length
      sourceMtimeNs = $itemStat.LastWriteTimeUtc.Ticks * 100
      outputDir = $OutputDir
      isComplete = $false
      totalLayouts = $candidateLayouts.Count
      validLayouts = $nonEmptyLayouts.Count
      layouts = $layoutMetadata
      completedPages = @{}
    }
    Set-Content -LiteralPath $manifestFile -Value ($manifestData | ConvertTo-Json -Depth 5) -Encoding UTF8
  } catch {}

  if ($ListOnly) {
    exit 0
  }

  # Функция настройки плоттера листа (с кэшированием устройств)
  function Prepare-LayoutPlotter($layoutObj) {
    $currentDev = [string]$layoutObj.ConfigName
    $devices = @($layoutObj.GetPlotDeviceNames())
    if (-not ($currentDev -and ($devices -contains $currentDev))) {
      $preferred = @(
        "DWG To PDF.pc3",
        "AutoCAD PDF (General Documentation).pc3",
        "AutoCAD PDF (High Quality Print).pc3",
        "Microsoft Print to PDF"
      )
      foreach ($dev in $preferred) {
        if ($devices -contains $dev) {
          try {
            $layoutObj.ConfigName = $dev
            $layoutObj.RefreshPlotDeviceInfo()
          } catch {}
          break
        }
      }
    }

    $allMedia = @($layoutObj.GetCanonicalMediaNames())
    if ($allMedia.Count -gt 0) {
      $curMedia = [string]$layoutObj.CanonicalMediaName
      if (-not ($curMedia -and ($allMedia -contains $curMedia))) {
        $matched = $null
        foreach ($code in @("A0", "A1", "A2", "A3", "A4")) {
          if ($curMedia -match $code) {
            $matched = @($allMedia | Where-Object { $_ -match $code } | Select-Object -First 1)
            if ($matched.Count -gt 0) { break }
          }
        }
        if ($matched -and $matched.Count -gt 0) {
          try { $layoutObj.CanonicalMediaName = $matched[0] } catch {}
        } elseif ($allMedia -contains "ISO_full_bleed_A3_(420.00_x_297.00_MM)") {
          try { $layoutObj.CanonicalMediaName = "ISO_full_bleed_A3_(420.00_x_297.00_MM)" } catch {}
        } else {
          try { $layoutObj.CanonicalMediaName = $allMedia[0] } catch {}
        }
      }
    }

    try { $layoutObj.PlotType = 4 } catch {} # acLayout
    $layoutObj.PlotWithLineweights = $true
    $layoutObj.PlotWithPlotStyles = $true
  }

  # Функция печати одного листа
  function Plot-OneLayout($layoutObj) {
    $tabOrder = [int]$layoutObj.TabOrder
    $name = [string]$layoutObj.Name
    $pdfFile = Join-Path $OutputDir ("page_{0:D4}.pdf" -f $tabOrder)

    # Проверка существующего кэша (RESUME)
    if ((Test-Path -LiteralPath $pdfFile) -and (Get-Item -LiteralPath $pdfFile).Length -gt 1024) {
      $res = @{
        event = "sheet_ready"
        tabOrder = $tabOrder
        name = $name
        pdfPath = $pdfFile
        bytes = (Get-Item -LiteralPath $pdfFile).Length
        fromCache = $true
        elapsedMs = 0
      }
      Write-Output ($res | ConvertTo-Json -Compress)
      return
    }

    $swPlot = [System.Diagnostics.Stopwatch]::StartNew()
    Log-Msg "Activating layout $tabOrder ('$name')..."
    $document.ActiveLayout = $layoutObj
    $switchMs = $swPlot.ElapsedMilliseconds

    Prepare-LayoutPlotter $layoutObj

    $swFile = [System.Diagnostics.Stopwatch]::StartNew()
    $success = $document.Plot.PlotToFile($pdfFile)
    $plotFileMs = $swFile.ElapsedMilliseconds
    $totalSheetMs = $swPlot.ElapsedMilliseconds

    if ($success -and (Test-Path -LiteralPath $pdfFile) -and (Get-Item -LiteralPath $pdfFile).Length -gt 1024) {
      $res = @{
        event = "sheet_ready"
        tabOrder = $tabOrder
        name = $name
        pdfPath = $pdfFile
        bytes = (Get-Item -LiteralPath $pdfFile).Length
        fromCache = $false
        switchMs = $switchMs
        plotMs = $plotFileMs
        elapsedMs = $totalSheetMs
      }
      Write-Output ($res | ConvertTo-Json -Compress)
      try {
        if ($manifestFile -and (Test-Path -LiteralPath $manifestFile)) {
          $mf = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
          if (-not $mf.completedPages) { $mf | Add-Member -NotePropertyName completedPages -NotePropertyValue (@{}) }
          $mf.completedPages | Add-Member -NotePropertyName ([string]$tabOrder) -NotePropertyValue (@{
            tabOrder = $tabOrder
            name = $name
            pdf = $pdfFile
            elapsedMs = $totalSheetMs
          }) -Force
          Set-Content -LiteralPath $manifestFile -Value ($mf | ConvertTo-Json -Depth 5) -Encoding UTF8
        }
      } catch {}
    } else {
      $err = @{
        event = "sheet_error"
        tabOrder = $tabOrder
        name = $name
        message = "PlotToFile failed or output file is corrupt"
        elapsedMs = $totalSheetMs
      }
      Write-Output ($err | ConvertTo-Json -Compress)
    }
    [System.GC]::Collect()
  }

  # Сортировка очереди печати: сначала приоритетный лист (если задан), затем остальные
  if ($nonEmptyLayouts.Count -gt 0) {
    $queue = @()
    if ($PriorityTabOrder -ge 0) {
      $prio = @($nonEmptyLayouts | Where-Object { $_.TabOrder -eq $PriorityTabOrder })
      if ($prio.Count -gt 0) {
        $queue += $prio[0]
      }
    }
    foreach ($l in $nonEmptyLayouts) {
      if ($l.TabOrder -ne $PriorityTabOrder) {
        $queue += $l
      }
    }

    foreach ($layoutItem in $queue) {
      try {
        Plot-OneLayout $layoutItem
      } catch {
        $errEvent = @{
          event = "sheet_error"
          tabOrder = [int]$layoutItem.TabOrder
          name = [string]$layoutItem.Name
          message = $_.Exception.Message
        }
        Write-Output ($errEvent | ConvertTo-Json -Compress)
      }
    }
  } else {
    # Сценарий без листов (Model Space Only)
    Log-Msg "No paper layouts found. Plotting Model Space..."
    $modelLayout = $document.ModelSpace.Layout
    $swModel = [System.Diagnostics.Stopwatch]::StartNew()
    $modelPdf = Join-Path $OutputDir "page_0000.pdf"

    $devices = @($modelLayout.GetPlotDeviceNames())
    foreach ($dev in @("DWG To PDF.pc3", "AutoCAD PDF (General Documentation).pc3", "Microsoft Print to PDF")) {
      if ($devices -contains $dev) {
        try { $modelLayout.ConfigName = $dev } catch {}
        break
      }
    }
    try { $modelLayout.PlotType = 1 } catch {} # acExtents
    $modelLayout.CenterPlot = $true
    $modelLayout.UseStandardScale = $true
    $modelLayout.StandardScale = 0 # acScaleToFit
    $modelLayout.PlotWithLineweights = $false
    $modelLayout.PlotWithPlotStyles = $true

    $success = $document.Plot.PlotToFile($modelPdf)
    $ms = $swModel.ElapsedMilliseconds
    if ($success -and (Test-Path -LiteralPath $modelPdf) -and (Get-Item -LiteralPath $modelPdf).Length -gt 1024) {
      $res = @{
        event = "sheet_ready"
        tabOrder = 0
        name = "Model"
        pdfPath = $modelPdf
        bytes = (Get-Item -LiteralPath $modelPdf).Length
        fromCache = $false
        elapsedMs = $ms
      }
      Write-Output ($res | ConvertTo-Json -Compress)
    } else {
      Write-Output (@{ event = "sheet_error"; tabOrder = 0; name = "Model"; message = "Model plot failed" } | ConvertTo-Json -Compress)
    }
  }

  try {
    if ($manifestFile -and (Test-Path -LiteralPath $manifestFile)) {
      $mf = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
      $mf.isComplete = $true
      Set-Content -LiteralPath $manifestFile -Value ($mf | ConvertTo-Json -Depth 5) -Encoding UTF8
    }
  } catch {}
  Write-Output (@{ event = "complete"; totalTimeMs = $swOpen.ElapsedMilliseconds } | ConvertTo-Json -Compress)
} finally {
  try { [DwgPlotMessageFilter]::Revoke() } catch {}
  if ($document) {
    try { $document.Close($false) } catch {}
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null } catch {}
  }
  if ($app) {
    try { $app.Quit() } catch {}
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
  }
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}
