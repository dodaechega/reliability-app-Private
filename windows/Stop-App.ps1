$ErrorActionPreference = 'Stop'
$appEntry = Join-Path $PSScriptRoot 'app\app.py'
$appPython = Join-Path $PSScriptRoot 'Python\python.exe'
$running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.ExecutablePath -eq $appPython -and $_.CommandLine.Contains($appEntry)
})
foreach ($process in $running) {
    Stop-Process -Id $process.ProcessId
    Wait-Process -Id $process.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
}
Write-Output 'Reliability app stopped.'
