param(
    [string]$StartDate = "",
    [string]$EndDate = "",
    [string]$Date = "",
    [string]$EnvPath = ".env",
    [string]$ConfigPath = "config/qnh_activity_detail.example.yaml"
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

$DateArgs = @()

if ($Date) {
    $DateArgs += @("--date", $Date)
} elseif ($StartDate -and $EndDate) {
    $DateArgs += @("--start", $StartDate, "--end", $EndDate)
}

function Invoke-Dimension {
    param(
        [string]$Dimension,
        [string]$LogPath
    )

    $ArgsList = @(
        "-m", "business_data_pipelines.cli",
        "--env", $EnvPath,
        "qnh", "activity-detail",
        "--dimension", $Dimension,
        "--config", $ConfigPath
    ) + $DateArgs

    & $Python @ArgsList 2>&1 | Tee-Object -FilePath $LogPath
    return $LASTEXITCODE
}

$ActivityLog = Join-Path $LogDir "qnh_activity_$Stamp.log"
$StoreLog = Join-Path $LogDir "qnh_store_$Stamp.log"

$ActivityExit = Invoke-Dimension -Dimension "activity" -LogPath $ActivityLog
if ($ActivityExit -ne 0) {
    exit $ActivityExit
}

$StoreExit = Invoke-Dimension -Dimension "store" -LogPath $StoreLog
exit $StoreExit
