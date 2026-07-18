# Context Notes — 신뢰성 시험표준 관리 웹앱

작업 중 내린 결정과 근거를 계속 append 한다.

## 배경 (2026-07-18)
- 원본: `C:\Users\ssss\Downloads\PT.SAMJIN_Reliability_Test_Item.xlsx` (7개 시트).
- PT.SAMJIN(인도네시아 법인) QA/품질팀의 제품군별 신뢰성 시험 항목·조건 관리표.
- 사용자: 품질경영 담당(김영호P). 신규 모델 나올 때마다 시험표준화 작업 필요.

## 인터뷰 결정사항
| 항목 | 결정 | 근거 |
|------|------|------|
| MVP | 신규모델 시험표준 생성 (템플릿 복사→수정) | 반복 업무 자동화 효과 가장 큼 |
| 사용자 | 소수 순차 · 간단 로그인 + 수정이력 | 사내망 소수 사용, 책임추적만 필요 |
| 배포 | 사내 IT 전용 서버 (상시 구동) | IT부서 지원 가능 |
| 저장 | SQLite (앱 내장 파일) | 소수 순차엔 충분, 백업=파일복사 |
| 산출물 | 엑셀 내보내기 | 보고·제출은 여전히 엑셀 |
| 스택 | Python Streamlit | 표·폼·엑셀 강점, 빠른 구축 |
| 템플릿 | 이 엑셀 내용 그대로 초기 탑재 | 현업 기준 유지 |
| 비교표 | 시험항목 × 제품군 매트릭스 (Phase 2) | MVP 완성 후 추가 |

## 데이터 모델 결정
- 제품군 6종: 리모컨/IoT, 스피커, HUB V4(IoT), BLE Tag(IoT), 고무(Rubber), 사출(Injection).
- 원본 시트 중 RCU/V4/BLE 는 사실 "특정 모델의 시험계획"(= 우리 앱의 산출물)에 해당하나,
  MVP 단계에선 각 제품군의 표준 템플릿 소스로 사용.
- template_item 스키마는 시트마다 컬럼이 달라 유연한 공통 스키마로 통일:
  seq / category(종류·Test Type) / item_name / code / spec(조건) / criteria(판정기준) /
  qty / days(기간) / available(수행가능) / remark.
- model 생성 시 해당 제품군 template_item 을 model_test_item 으로 **복사**. 이후 독립 편집.

## 구현 메모
- Python 인터프리터: 프로젝트 내 `.venv` (streamlit/pandas/openpyxl 설치).
- 로그인은 사내망 전제라 비밀번호 없이 이름/ID 선택 수준. 감사추적용 change_log 만 확실히.
- 파일 헤더에 한글 1줄 주석 (CLAUDE.md 지침).

## Phase 1 구현 완료 (2026-07-18)
- 시드 결과: 리모컨/IoT 17 · 스피커 8 · HUB V4 5 · BLE Tag 4 · 고무 7 · 사출 11 = 52항목.
- 편집표는 st.data_editor(num_rows="dynamic")로 행 추가/삭제·셀 편집. 저장 시 전체 교체 방식.
  (변경 diff 추적은 Phase 3에서 필요 시 세분화. 지금은 '저장 N건' 이력만.)
- 적용여부(applicable): 템플릿 available=="can't" 항목은 기본 N, 엑셀에서 회색 강조.
- 실행: preview name="reliability" (launch.json), 포트 8501. 세션은 새로고침 시 초기화(로그인 재요구)
  — Streamlit 특성. 데이터는 SQLite에 영속.
- 검증: DB 스모크테스트 + 브라우저 walkthrough(로그인→등록→템플릿복사17건→편집뷰) 통과,
  change_log에 담당자/동작 기록 확인, xlsx 7327 bytes 생성.
- 미해결/주의: 브라우저 pane screenshot이 data_editor(canvas grid)에서 타임아웃 → 시각 캡처 대신
  read_page/DB로 검증. 앱 자체 문제 아님.

## 버그 수정 (2026-07-18) — 메뉴 첫 클릭 깜박임/두 번 클릭
- 증상: 사이드바 메뉴 첫 클릭 시 페이지가 안 바뀌고 두 번째 클릭에 반영.
- 원인: st.radio 를 `index=default`(이전 page 기준)로 그리면서 반환값을 다시 page 에 써서,
  클릭 첫 실행에서 index 계산이 한 박자 늦음 (Streamlit 위젯 index/state 충돌).
- 수정: 라디오에 `key="page"` 부여해 세션 상태를 단일 소스로 사용. `index=` 제거.
  버튼 이동은 위젯 생성 후 page 직접 수정이 불가하므로, 비위젯 키 `_goto` 에 담고
  다음 실행 시작 시 page 로 옮기는 `goto()` 헬퍼로 통일. (app.py: goto/main)
- 검증: 라디오 단일 클릭 전환 OK, 버튼 goto 이동 OK, 서버 에러 없음.

## Phase 2 구현 완료 (2026-07-18)
- 비교표 매칭 키 변경: 착수 메모의 "code 우선" 대신 **항목명 키워드 분류**(compare.py CATEGORY_RULES)
  채택. 이유: HUB/BLE/고무/사출은 code 공란이고 제품군마다 코드 체계가 달라 code 매칭 불성립.
  52항목 → 16개 비교 카테고리, '기타' 0건 (스모크 테스트로 전수 확인).
- 렌더링: st.dataframe 은 셀 내 줄바꿈·행 하이라이트 표현이 약해서 HTML 테이블 직접 생성
  (render_html). 셀 텍스트는 html.escape 후 \n→<br> (BLE spec의 "<10kg" escape 확인).
- 하이라이트 규칙: 2개군 이상 & 조건 상이=노랑(#FFF3CD) 8행, 동일=연녹(#E8F5E9) 2행(열충격·동작수명),
  단일 제품군=무색, 자체 수행 불가 항목 ⛔ 표시.
- 필터 위젯: st.checkbox → st.radio(horizontal) 로 변경. 이 브라우저 자동화 환경에서 BaseWeb
  체크박스가 합성 클릭을 못 받아 검증 불가였고, 라디오는 동작 검증됨 (UX 동등).
- 템플릿 관리: 인터뷰에서 관리자/일반 권한 분리를 선택하지 않았으므로(간단 로그인+이력만)
  전체 사용자 편집 가능 + change_log 기록으로 확정. 수정은 신규 모델 생성분부터 반영,
  기존 모델 영향 없음 (화면에 명시).
- 검증: 분류 전수·HTML escape·저장 라운드트립(스모크) + 브라우저에서 비교표 렌더(17행 테이블),
  하이라이트 셀 수(노랑48/연녹12), '차이만' 필터(8행) 확인.

## 비교표 가독성 재설계 — Apple design 적용 (2026-07-18)
- 증상: 다크 모드에서 셀 배경(#FFF3CD 등 라이트 전용)에 테마 상속 흰 글자가 얹혀 판독 불가.
  + 항목명·조건·수량이 한 줄 연결이라 위계 없음.
- 재설계 (compare.py 전면 개정, apple-design 스킬 기준):
  * 전면 채색 → 저채도 틴트(10~14%) + 행 첫 셀 3px 액센트 바 (HIG systemOrange/Green).
  * 셀 3단 타이포 위계: 항목명(600·12.5px) / 조건(secondary·12px) / Qty·일수(caption·11px).
  * 라이트/다크 팔레트 분리, 글자색까지 전부 명시 → 테마 독립적. st.context.theme.type 으로 선택.
  * 시스템 폰트 스택, 헤어라인 보더, 12px 라운드 카드, ⛔ → "수행 불가" pill 배지.
  * 범례는 이모지 → 컬러 도트 칩으로 render_html 내장.
- 함정 2개 (재발 주의):
  * Streamlit 은 메인 스크립트만 핫리로드 → compare.py 수정 후 "unexpected keyword argument"
    는 모듈 캐시. **서버 재시작 필요.**
  * `.streamlit/config.toml` 에 [theme] 키를 하나라도 넣으면(primaryColor 포함) 커스텀 라이트
    테마로 고정되어 **시스템 다크 추종이 꺼짐**. Apple 블루 시도했다가 제거함.
- 검증: 스모크(라이트/다크 렌더, div/td 짝, escape, 글자색 명시) + 브라우저 다크 모드에서
  다크 팔레트 적용·액센트 바 10개·타이포 위계 computed style 확인. 라이트 모드도 실측 확인.

## 실제 모델 데이터 등록 (2026-07-18)
- 사용자 확인 후: 원본 엑셀의 모델별 시험계획 시트 3개를 실데이터로 등록 (시트 내용 그대로,
  템플릿 복사본 아님 — create_model 후 replace_model_items 로 교체).
  * [3] Y26 Smart TM2660 (리모컨/IoT · PR) — RCU Smart 시트 5건 (카톤 진동 1.5mm, 적재 91kg 등)
  * [4] SR HUB V4 (HUB V4(IoT) · SR) — V4 시트 5건
  * [5] BLE Tag ALPS Alpine (BLE Tag(IoT) · PR) — BLE 시트 4건 (HQ Request 여부는 remark 에)
- Phase 1 검증용 테스트 모델 Y27 Smart TM2700 은 사용자 확인 후 삭제.
- 시트의 Test Purpose → criteria 필드, HQ Request → remark 로 매핑.

## State 컬럼 추가 (2026-07-18, 사용자 요청)
- 모델 상세 편집 표에 시험항목별 State 컬럼(PV/PR/SR/MP 드롭다운, SelectboxColumn) 추가.
  위치는 시험항목 다음. ITEM_STAGES 는 seed_data.py 에 (모델 단위 DEV_STAGES 와 별개 —
  DEV_STAGES 엔 OQC 가 있지만 항목 State 는 사용자 지정 4개만).
- DB: model_test_items 에 stage TEXT 추가. init_db 에서 PRAGMA 로 컬럼 존재 확인 후
  ALTER TABLE 마이그레이션, 기존 항목은 모델 dev_stage 로 백필(PV/PR/SR/MP 일 때만).
- create_model 템플릿 복사 시 모델 dev_stage 상속(4개 외 값이면 NULL). 엑셀 내보내기에도 State 열 추가.
- 검증: 마이그레이션 백필(3모델 PR/SR/PR), 신규 생성 상속, 편집 저장 보존, 엑셀 헤더/값 — 통과.
- 한계: 이 브라우저 pane 에서 glide 그리드 canvas 가 0x0 으로 렌더되지 않아(스크린샷 timeout 의
  원인이기도 함) 그리드 UI 의 픽셀 검증은 불가. 데이터 경로 검증으로 갈음.

## Phase 3 구현 완료 (2026-07-18)
- 통계 리포트 페이지 (app.py stats_view): 전체 요약 metric 4개(모델/적용항목/완료율/NG),
  모델별 진행률 st.progress 바, 모델별 현황 표, NG 현황 표(없으면 success 메시지).
  집계 기준: 적용=Y 이고 진행상태 '해당없음' 아닌 항목만. 차트 라이브러리 없이
  metric+progress+dataframe 으로 구성(3~수십 모델 규모에 적정, 의존성 無).
- DEPLOY.md: 사내 Windows 서버 기준 — 설치, 0.0.0.0 공유 실행, 작업 스케줄러 상시구동,
  방화벽(Domain/Private 만), 백업(=db 파일 복사), git pull 업데이트, 트러블슈팅 표.
- 검증: 브라우저 실측 — 메뉴 7개, 통계 페이지 모델 3·적용 14(5+5+4)·완료율 0%·NG 0 정확.
- 알림 기능은 보류(요구 불명확 — 메일/메신저 인프라 결정 필요).
- 참고: lean-ctx 활성 세션 — ctx_shell 에서 python.exe 비허용, ctx_execute python 은
  Store 스텁(9009) 문제. 검증은 서버 기동 + 브라우저로 수행.
