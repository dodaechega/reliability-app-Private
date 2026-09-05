# 작업 안내

- Python 3.12 기준. 설치: `python -m pip install -r requirements-dev.txt`.
- 진입점은 `app.py`, DB/트랜잭션은 `db.py`, 비교는 `compare.py`, 엑셀은 `export_excel.py`.
- 검증: `python verify.py`. Ruff → pytest 순서이며 실패 시 비정상 종료한다. CI도 같은 명령을 쓴다.
- 테스트는 `tests/conftest.py`가 임시 DB와 캐시를 격리한다. 운영 `data/`로 테스트하지 않는다.
- 별도 앱 데이터 경로는 실행 전에 `RELIABILITY_DB_PATH`로 설정한다. DB/업무 자료는 커밋하지 않는다.
- 데이터 변경과 `change_log`는 같은 트랜잭션을 사용한다. 스키마 변경은 `init_db`의 버전 마이그레이션과 기존 DB 회귀 테스트를 함께 수정한다.
- SQLite 연결은 호출별로 열고 닫는다. 전역 연결 캐시를 만들지 않는다. 엑셀 캐시 키에는 저장된 모델/항목 내용을 모두 포함한다.
- 오류 수정은 실패 재현 테스트 → 최소 수정 → `python verify.py` 순서로 진행한다. DB 무결성, 통계 기준, 한 번 클릭하는 화면 이동을 유지한다.
- AppTest는 브라우저 픽셀/캔버스 조작을 검증하지 않는다. 해당 UI를 바꾸면 수동 검증 결과와 한계를 기록한다.
- 현재 앱은 사내망 이름 선택 방식이다. 인증/권한 시스템 또는 대규모 구조 개편은 별도 요구 없이 추가하지 않는다.
