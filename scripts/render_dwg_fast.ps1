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
  throw "DWG-файл не найден: $InputPath"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = [System.IO.Path]::ChangeExtension($InputPath, ".pdf")
}

$outputDir = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outputDir) -and -not (Test-Path -LiteralPath $outputDir)) {
  try {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
  } catch {}
}

# 1. ПРИОРИТЕТ: Изолированный рендер через accoreconsole (строго 1 процесс на 1 лист)
# Гарантирует нулевую утечку памяти, отсутствие зависаний и поддержку кэша с допечатыванием (RESUME).
$isolatedScript = Join-Path $PSScriptRoot 'render_dwg_isolated.ps1'
if (Test-Path -LiteralPath $isolatedScript) {
  try {
    & $isolatedScript -InputPath $InputPath -OutputPath $OutputPath -FallbackCachePath $FallbackCachePath -PythonExe $PythonExe -TimeoutPerSheetSec $TimeoutPerSheetSec
    exit 0
  } catch {
    Write-Output ("WARN: render_dwg_isolated failed: {0}. Falling back to COM..." -f $_)
  }
}

# 2. РЕЗЕРВ: Полный обход листов через AutoCAD COM (render_dwg_smart.ps1)
$smartScript = Join-Path $PSScriptRoot 'render_dwg_smart.ps1'
if (Test-Path -LiteralPath $smartScript) {
  & $smartScript -InputPath $InputPath -OutputPath $OutputPath -FallbackCachePath $FallbackCachePath -PythonExe $PythonExe
} else {
  throw "Скрипт рендера DWG не найден"
}
