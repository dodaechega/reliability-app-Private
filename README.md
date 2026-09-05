# 신뢰성 시험표준 관리 웹앱 (PT.SAMJIN QA)

Python 3.12 기준. 직접 의존성은 검증한 버전으로 고정합니다.

신규 모델이 나올 때마다 제품군 표준 템플릿을 복사해 시험표준을 세팅하고, 담당자가 직접
입력·관리하며, 엑셀로 내보내는 사내 도구입니다. (Streamlit + SQLite)

## 실행 방법 (로컬)
```bash
# 최초 1회
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 실행
.venv\Scripts\streamlit run app.py
```
브라우저에서 `http://localhost:8501` 접속.

## 사내 서버(같은 네트워크 공유) 실행
```bash
.venv\Scripts\streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
같은 사내망의 담당자는 `http://<서버IP>:8501` 로 접속.

## 구성
| 파일 | 역할 |
|------|------|
| `app.py` | 메인 UI (로그인·대시보드·등록·편집·이력) |
| `db.py` | SQLite 스키마·CRUD·변경이력 |
| `seed_data.py` | 원본 엑셀 7개 시트 → 제품군별 표준 템플릿 |
| `export_excel.py` | 모델별 시험표준 엑셀 내보내기 |
| `data/reliability.db` | 데이터 파일 (앱 중지 후 복사하여 백업) |

## 데이터
- 제품군 6종: 리모컨/IoT · 스피커 · HUB V4(IoT) · BLE Tag(IoT) · 고무(Rubber) · 사출(Injection)
- 최초 실행 시 표준 템플릿이 자동 시드됩니다.

## 현재 기능
모델 생성·편집·엑셀 내보내기·변경이력, 제품군 비교표, 템플릿 관리, 통계 리포트.

## 개발·검증
```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python verify.py
```

`verify.py`는 Ruff와 pytest를 실행하고 실패 시 즉시 종료합니다. GitHub Actions도
Windows/Linux에서 같은 명령을 실행합니다. 테스트는 임시 DB만 사용하며, 실제 업무 DB는 읽거나 수정하지 않습니다.
앱을 개발용 데이터로 실행하려면 실행 전에 `$env:RELIABILITY_DB_PATH = 'C:\temp\reliability-dev.db'`를 설정합니다.

테스트 범위: 기존 스키마 마이그레이션, 시드 실패 복구, 빈 템플릿 보존, 저장·감사이력 원자성,
모델 복사/삭제, 통계 집계/조회 수, 엑셀 값·수식 방지, HTML escape, 로그인/생성/메뉴 이동/로그아웃,
엑셀 캐시 재사용·저장 후 갱신. 브라우저의 캔버스 편집·픽셀 검증은 포함하지 않습니다.

변경 시 재현 테스트를 먼저 추가하고 수정 후 위 명령을 실행합니다. 작업 구조는 [AGENTS.md](AGENTS.md),
배포·백업은 [DEPLOY.md](DEPLOY.md)를 참고하세요. 과거 수동 검증 기록은 `context-notes.md`에 보존합니다.

DB 초기화는 프로세스에서 경로별 1회 실행하며, DB 교체·복원 후에는 앱을 재시작해야 합니다.
엑셀 내보내기는 마지막 저장본 기준이며, 저장된 내용이 바뀌면 캐시가 갱신됩니다.
