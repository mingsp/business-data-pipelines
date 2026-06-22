param(
    [string]$StartDate = "",
    [string]$EndDate = "",
    [string]$EnvPath = ".env",
    [string]$ConfigPath = "config/qnh_review_detail.example.yaml"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$SrcPath = Join-Path $Root "src"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$SrcPath;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $SrcPath
}

$Python = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "qnh_review_detail_$Stamp.log"

$ArgsList = @(
    "-m", "business_data_pipelines.cli",
    "--env", $EnvPath,
    "qnh", "review-detail",
    "--config", $ConfigPath
)

if ($StartDate -and $EndDate) {
    $ArgsList += @("--start", $StartDate, "--end", $EndDate)
}

& $Python @ArgsList 2>&1 | Tee-Object -FilePath $LogPath
exit $LASTEXITCODE
