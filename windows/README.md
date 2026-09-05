# Windows PC 설치본 운영 파일

PC 설치에 사용한 실행·종료·백업 스크립트입니다. 자동 설치 프로그램은 아니며,
아래 폴더 구조와 앱 의존성이 준비된 설치본에서 사용합니다.

```text
%LOCALAPPDATA%\Programs\ReliabilityApp\
  Start-App.ps1
  Stop-App.ps1
  backup.py
  Python\python.exe
  Python\pythonw.exe
  app\app.py
  app\requirements.txt
  app\... (저장소 앱 파일)
```

이 디렉터리의 스크립트 3개를 설치 루트에 복사합니다. Python 실행환경은 앱 의존성을
포함해야 하며, 검증 기준은 Python 3.12입니다. 설치본의 `app` 디렉터리에서
`..\Python\python.exe verify.py`로 검증합니다 (`requirements-dev.txt` 의존성 필요).

## 실행과 종료

바탕화면/시작 메뉴의 실행 바로가기는 Windows PowerShell을 다음 인수로 실행합니다.
`<설치 루트>`는 위의 실제 절대 경로로 바꿉니다.

```text
-NoProfile -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "<설치 루트>\Start-App.ps1"
```

- 앱을 백그라운드로 시작하고 준비되면 기본 브라우저를 엽니다.
- 주소는 `http://127.0.0.1:8501`이며 해당 PC에서만 접속합니다.
- 이미 실행 중이면 서버를 추가로 만들지 않고 브라우저만 엽니다.
- 브라우저 없이 상태를 확인하려면 `-NoBrowser` 인수를 추가합니다.
- 종료 바로가기는 같은 인수에서 파일명을 `Stop-App.ps1`로 바꿉니다.
- 재부팅 후에는 실행 바로가기를 다시 실행합니다. 자동 시작은 구성하지 않습니다.

## 데이터와 백업

- DB: `%LOCALAPPDATA%\ReliabilityApp\data\reliability.db`
- 로그: `%LOCALAPPDATA%\ReliabilityApp\logs`
- 백업: `%LOCALAPPDATA%\ReliabilityApp\backups`

백업 바로가기는 설치본의 `Python\pythonw.exe`에 `"<설치 루트>\backup.py"`를 인수로 전달합니다.
실행 중인 DB도 SQLite backup API로 일관된 사본을 생성하며, 완료 후 백업 폴더를 엽니다.
별도 저장장치에도 백업을 보관하세요. 복원은 앱 종료 후 기존 DB를 별도 보관하고,
백업 파일을 실제 데이터 경로에 `reliability.db` 이름으로 복사한 다음 앱을 다시 실행합니다.

## 설치본 검증 기록

2026-09-05에 실행·종료·재실행 후 데이터 보존, 중복 서버 방지, 브라우저 로그인/생성/저장/삭제,
실행 중 백업과 SQLite 무결성을 확인했습니다. 설치 확인용 모델은 삭제했습니다.
업무 DB, 설치된 Python, 가상환경, 로그와 개인 바로가기는 저장소에 포함하지 않습니다.
