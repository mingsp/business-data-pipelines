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

$Python = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"

function Start-DimensionJob {
    param(
        [string]$Dimension,
        [string]$LogPath
    )

    Start-Job -Name "qnh-$Dimension" -ScriptBlock {
        param($Root, $SrcPath, $Python, $EnvPath, $ConfigPath, $Dimension, $Date, $StartDate, $EndDate, $LogPath)
        Set-Location $Root
        if ($env:PYTHONPATH) {
            $env:PYTHONPATH = "$SrcPath;$env:PYTHONPATH"
        } else {
            $env:PYTHONPATH = $SrcPath
        }
        $ArgsList = @(
            "-m", "business_data_pipelines.cli",
            "--env", $EnvPath,
            "qnh", "activity-detail",
            "--dimension", $Dimension,
            "--config", $ConfigPath
        )
        if ($Date) {
            $ArgsList += @("--date", $Date)
        } elseif ($StartDate -and $EndDate) {
            $ArgsList += @("--start", $StartDate, "--end", $EndDate)
        }
        & $Python @ArgsList 2>&1 | Tee-Object -FilePath $LogPath
        [pscustomobject]@{ Dimension = $Dimension; ExitCode = $LASTEXITCODE; LogPath = $LogPath }
    } -ArgumentList $Root, $SrcPath, $Python, $EnvPath, $ConfigPath, $Dimension, $Date, $StartDate, $EndDate, $LogPath
}

$ActivityLog = Join-Path $LogDir "qnh_activity_$Stamp.log"
$StoreLog = Join-Path $LogDir "qnh_store_$Stamp.log"
$Jobs = @(
    Start-DimensionJob -Dimension "activity" -LogPath $ActivityLog
    Start-DimensionJob -Dimension "store" -LogPath $StoreLog
)

Wait-Job $Jobs | Out-Null
$Results = $Jobs | Receive-Job
$Jobs | Remove-Job

$Failed = $Results | Where-Object { $_.ExitCode -ne 0 }
if ($Failed) {
    $Failed | Format-Table -AutoSize
    exit 1
}

$Results | Format-Table -AutoSize
exit 0
