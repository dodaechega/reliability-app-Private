# 신뢰성 시험표준 관리 웹앱 (PT.SAMJIN QA)

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
| `data/reliability.db` | 데이터 파일 (백업 = 이 파일 복사) |

## 데이터
- 제품군 6종: 리모컨/IoT · 스피커 · HUB V4(IoT) · BLE Tag(IoT) · 고무(Rubber) · 사출(Injection)
- 최초 실행 시 표준 템플릿이 자동 시드됩니다.

## Phase
- **Phase 1 (현재)**: 신규모델 시험표준 생성·편집·엑셀 내보내기·변경이력
- **Phase 2**: 제품군 비교표 (시험항목 × 제품군 매트릭스), 템플릿 관리 UI
