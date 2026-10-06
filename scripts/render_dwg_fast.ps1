param(
  [Parameter(Mandatory = $true)][string]$InputPath,
  [Parameter(Mandatory = $false)][string]$OutputPath = "",
  [Parameter(Mandatory = $false)][string]$FallbackCachePath = "",
  [Parameter(Mandatory = $false)][string]$PythonExe = ""
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

# 1. СНАЧАЛА БЫСТРЫЙ РЕЖИМ: нативный экспорт через accoreconsole.exe (_.-EXPORT _PDF)
# Работает без поднятия GUI AutoCAD за 3-8 секунд
$nativeExportScript = Join-Path $PSScriptRoot 'Invoke-NativeDwgPdfExport.ps1'
if (Test-Path -LiteralPath $nativeExportScript) {
  try {
    . $nativeExportScript
    $accore = Find-NativeAccoreConsole
    if ($accore) {
      $fileId = [System.BitConverter]::ToString([System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($InputPath))).Replace("-","").Substring(0,12)
      $tempWorkDir = Join-Path ([System.IO.Path]::GetTempPath()) "FEng_accore_$fileId"
      $tempTargetPdf = Join-Path $tempWorkDir "accore_out.pdf"
      
      $res = Invoke-NativeDwgPdfExport -InputPath $InputPath -OutputPdf $tempTargetPdf -WorkDir $tempWorkDir -TimeoutSec 120
      if ((Test-Path -LiteralPath $tempTargetPdf) -and (Get-Item -LiteralPath $tempTargetPdf).Length -gt 1024) {
        $finalDestination = $OutputPath
        $writeSuccess = $false
        try {
          Copy-Item -LiteralPath $tempTargetPdf -Destination $OutputPath -Force -ErrorAction Stop
          $writeSuccess = $true
        } catch {
          if (-not [string]::IsNullOrWhiteSpace($FallbackCachePath)) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $FallbackCachePath) | Out-Null
            Copy-Item -LiteralPath $tempTargetPdf -Destination $FallbackCachePath -Force
            $finalDestination = $FallbackCachePath
            $writeSuccess = $true
          }
        }
        
        try { Remove-Item -LiteralPath $tempWorkDir -Recurse -Force -ErrorAction SilentlyContinue } catch {}
        
        if ($writeSuccess) {
          $result = @{
            ok = $true
            finalPath = $finalDestination
            isLocalFolder = ($finalDestination -eq $OutputPath)
            pageCount = 1
            mode = "accoreconsole"
          }
          Write-Output ($result | ConvertTo-Json -Compress)
          exit 0
        }
      }
    }
  } catch {
    # При сбое accoreconsole не прерываемся, а переходим к тяжелому многостраничному COM-плоттеру
  }
}

# 2. РЕЗЕРВ: Полный многостраничный обход листов через AutoCAD COM (render_dwg_smart.ps1)
$smartScript = Join-Path $PSScriptRoot 'render_dwg_smart.ps1'
if (Test-Path -LiteralPath $smartScript) {
  & $smartScript -InputPath $InputPath -OutputPath $OutputPath -FallbackCachePath $FallbackCachePath -PythonExe $PythonExe
} else {
  throw "Скрипт рендера DWG не найден"
}
