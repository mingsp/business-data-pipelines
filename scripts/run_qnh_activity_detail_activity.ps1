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

$ArgsList = @(
    "-m", "business_data_pipelines.cli",
    "--env", $EnvPath,
    "qnh", "activity-detail",
    "--dimension", "activity",
    "--config", $ConfigPath
)

if ($Date) {
    $ArgsList += @("--date", $Date)
} elseif ($StartDate -and $EndDate) {
    $ArgsList += @("--start", $StartDate, "--end", $EndDate)
}

& $Python @ArgsList
exit $LASTEXITCODE
