param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$installRoot = $PSScriptRoot
$appEntry = Join-Path $installRoot 'app\app.py'
$appPython = Join-Path $installRoot 'Python\python.exe'
$dataRoot = Join-Path $env:LOCALAPPDATA 'ReliabilityApp'
$url = 'http://127.0.0.1:8501'
$mutexName = 'Local\ReliabilityApp-' + [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$mutex = [System.Threading.Mutex]::new($false, $mutexName)
$locked = $false
try {
    $locked = $mutex.WaitOne(45000)
    if (-not $locked) { throw '앱이 시작 중입니다. 잠시 후 다시 실행해 주세요.' }
    New-Item -ItemType Directory -Force (Join-Path $dataRoot 'data'), (Join-Path $dataRoot 'logs') | Out-Null
    $running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.ExecutablePath -eq $appPython -and $_.CommandLine.Contains($appEntry)
    })
    if (-not $running) {
        if (Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue) {
            throw '8501 포트를 다른 프로그램이 사용 중입니다. 앱 담당자에게 문의해 주세요.'
        }
        $env:RELIABILITY_DB_PATH = Join-Path $dataRoot 'data\reliability.db'
        $arguments = '-m streamlit run "{0}" --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false' -f $appEntry
        $server = Start-Process -FilePath $appPython -ArgumentList $arguments -WorkingDirectory (Join-Path $installRoot 'app') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataRoot 'logs\server.stdout.log') -RedirectStandardError (Join-Path $dataRoot 'logs\server.stderr.log') -PassThru
    }
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri "$url/_stcore/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok') { $ready = $true; break }
        } catch { }
        if ($server -and $server.HasExited) { throw '앱 시작에 실패했습니다. 로그 폴더를 확인해 주세요.' }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw '앱 응답을 기다리는 시간이 초과됐습니다. 잠시 후 다시 실행해 주세요.' }
    if (-not $NoBrowser) { Start-Process $url }
    Write-Output $url
} catch {
    New-Item -ItemType Directory -Force (Join-Path $dataRoot 'logs') | Out-Null
    $_ | Out-String | Add-Content -LiteralPath (Join-Path $dataRoot 'logs\launcher.log') -Encoding UTF8
    if (-not $NoBrowser) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($_.Exception.Message, '신뢰성 시험표준 관리') | Out-Null
    }
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
