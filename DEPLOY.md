# 사내 서버 배포 가이드 — 신뢰성 시험표준 관리 웹앱

IT부서 관리 Windows 서버에 상시 구동으로 배포하는 절차입니다.

## 1. 사전 요구사항

- Windows 서버 (사내망), Python 3.12 설치 (검증 기준)
- Git 설치 (또는 소스 zip 복사)
- 포트 1개 개방 (기본 8501, 사내망 한정)

## 2. 설치

```powershell
# 소스 받기
cd C:\apps
git clone https://github.com/dodaechega/reliability-app-Private.git reliability-app
cd reliability-app

# 가상환경 + 의존성
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 3. 실행 (사내망 공유)

```powershell
.venv\Scripts\streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

- 담당자 접속: `http://<서버IP>:8501`
- 첫 실행 시 `data\reliability.db` 가 자동 생성되고 표준 템플릿이 시드됩니다.

## 4. 상시 구동 (서버 재부팅 후 자동 시작)

작업 스케줄러 등록 (관리자 PowerShell에서 1회 실행):

```powershell
$action = New-ScheduledTaskAction -Execute "C:\apps\reliability-app\.venv\Scripts\python.exe" `
  -Argument "-m streamlit run C:\apps\reliability-app\app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true" `
  -WorkingDirectory "C:\apps\reliability-app"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "ReliabilityApp" -Action $action -Trigger $trigger `
  -RunLevel Highest -Description "신뢰성 시험표준 관리 웹앱"
Start-ScheduledTask -TaskName "ReliabilityApp"
```

중지/재시작:

```powershell
Stop-ScheduledTask -TaskName "ReliabilityApp"
Start-ScheduledTask -TaskName "ReliabilityApp"
```

## 5. 방화벽 (사내망 한정 개방)

```powershell
New-NetFirewallRule -DisplayName "ReliabilityApp 8501" -Direction Inbound `
  -Protocol TCP -LocalPort 8501 -Action Allow -Profile Domain,Private
```

외부(Public) 프로파일은 열지 않습니다. 사내망 전용 원칙.

## 6. 백업

- 기본 데이터 경로는 `data\reliability.db`입니다 (`RELIABILITY_DB_PATH` 설정 시 해당 경로 사용).
- 파일 복사 백업은 **앱 중지 → DB 파일 복사 → 앱 시작** 순서로 실행합니다. 쓰기 중인 파일만 복사하면 일관된 백업을 보장할 수 없습니다.
- 복원: 앱 중지 → db 파일 교체 → 시작.

## 7. 업데이트 (코드 갱신)

```powershell
Stop-ScheduledTask -TaskName "ReliabilityApp"
cd C:\apps\reliability-app
git pull
.venv\Scripts\pip install -r requirements.txt   # 의존성 변경 시
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python verify.py
# 검증 성공을 확인한 뒤 시작
Start-ScheduledTask -TaskName "ReliabilityApp"
```

- DB 스키마 변경은 앱 시작 시 자동 마이그레이션됩니다 (db.py init_db).
- `data\` 는 git 대상이 아니므로 업데이트해도 데이터는 유지됩니다.

## 8. 문제 해결

| 증상 | 확인 |
|------|------|
| 접속 불가 | 서버에서 `curl http://localhost:8501` → 되면 방화벽/IP 문제 |
| 포트 충돌 | `netstat -ano | findstr 8501` 로 점유 프로세스 확인, 포트 변경 가능 |
| 코드 수정이 반영 안 됨 | import 모듈(compare.py 등)은 핫리로드 안 됨 — 앱 재시작 필요 |
| 화면 깨짐/테마 | `.streamlit/config.toml` 에 [theme] 키를 넣으면 다크 모드 자동 전환이 꺼지므로 사용 금지 |
