# 신뢰성 시험표준 관리 웹앱 — 로그인 · 대시보드 · 신규모델 등록 · 시험항목 편집 · 엑셀 내보내기 메인

import streamlit as st
import pandas as pd

import db
from seed_data import PRODUCT_GROUPS, DEV_STAGES, ITEM_STAGES, PROGRESS_STATES, RESULTS
from export_excel import build_model_xlsx
from compare import build_matrix, render_html

st.set_page_config(page_title="신뢰성 시험표준 관리", page_icon="🧪",
                   layout="wide", initial_sidebar_state="expanded")
db.init_db()

FIELDS = ["seq", "category", "item_name", "stage", "code", "spec", "criteria",
          "qty", "days", "applicable", "progress", "result", "remark"]
COL_LABELS = {
    "seq": "No", "category": "종류", "item_name": "시험항목", "stage": "State",
    "code": "Code", "spec": "조건 (Specification)", "criteria": "판정기준",
    "qty": "Qty", "days": "Days", "applicable": "적용", "progress": "진행상태",
    "result": "결과", "remark": "Remark",
}

PAGES = ["대시보드", "신규 모델 등록", "모델 상세", "제품군 비교표", "템플릿 관리", "변경 이력"]

# 템플릿 관리 표 컬럼 (모델 편집표와 달리 판정채널·수행가능 컬럼 사용)
TPL_FIELDS = ["seq", "category", "item_name", "code", "spec", "criteria",
              "qty", "days", "available", "remark"]
TPL_LABELS = {
    "seq": "No", "category": "종류", "item_name": "시험항목", "code": "Code",
    "spec": "조건 (Specification)", "criteria": "판정기준", "qty": "Qty",
    "days": "Days", "available": "수행가능", "remark": "Remark",
}


def goto(page):
    """버튼 등 위젯 생성 이후 시점에서 안전하게 페이지를 이동한다.
    라디오(key='page')는 위젯 생성 후 직접 수정할 수 없으므로,
    비(非)위젯 키 _goto 에 담아 두고 다음 실행 시작 시 page 로 옮긴다."""
    st.session_state._goto = page
    st.rerun()


# ---------------- 로그인 ----------------
def login_view():
    st.title("🧪 신뢰성 시험표준 관리 시스템")
    st.caption("PT.SAMJIN · QA / 품질팀")
    with st.form("login"):
        st.subheader("로그인")
        users = db.list_users()
        names = [u["name"] for u in users]
        pick = st.selectbox("기존 사용자 선택", ["＋ 새 사용자"] + names)
        new_name = st.text_input("새 사용자 이름 (신규일 때만 입력)")
        ok = st.form_submit_button("로그인", type="primary")
    if ok:
        name = new_name.strip() if pick == "＋ 새 사용자" else pick
        if not name:
            st.error("이름을 선택하거나 입력해 주세요.")
            return
        st.session_state.user = db.get_or_create_user(name)
        st.session_state.page = "대시보드"
        st.rerun()


# ---------------- 대시보드 ----------------
def dashboard_view():
    st.header("📋 모델 대시보드")
    models = db.list_models()
    if not models:
        st.info("등록된 모델이 없습니다. 왼쪽 메뉴에서 **신규 모델 등록**을 진행해 주세요.")
        return
    df = pd.DataFrame(models)[
        ["id", "name", "code", "product_group", "dev_stage", "owner",
         "start_date", "end_date", "status", "created_by", "created_at"]
    ]
    df.columns = ["ID", "모델명", "코드", "제품군", "단계", "담당자",
                  "시작", "완료예정", "상태", "등록자", "등록일시"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    labels = {m["id"]: f"[{m['id']}] {m['name']} ({m['product_group']})" for m in models}
    sel = st.selectbox("편집할 모델 선택", list(labels), format_func=lambda x: labels[x])
    if st.button("➡ 상세 · 편집 열기", type="primary"):
        st.session_state.selected_model = sel
        goto("모델 상세")


# ---------------- 신규 모델 등록 ----------------
def new_model_view():
    st.header("🆕 신규 모델 등록")
    st.caption("제품군을 선택하면 해당 표준 템플릿이 자동으로 복사됩니다.")
    with st.form("new_model"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("모델명 *", placeholder="예: Y26 Smart TM2660")
            code = st.text_input("모델 코드")
            product_group = st.selectbox("제품군 *", PRODUCT_GROUPS)
        with c2:
            dev_stage = st.selectbox("개발 단계", DEV_STAGES)
            owner = st.text_input("담당자", value=st.session_state.user["name"])
            d1, d2 = st.columns(2)
            start_date = d1.text_input("시작일", placeholder="2026-07-18")
            end_date = d2.text_input("완료예정일", placeholder="2026-08-01")
        n = db.count_template_items(product_group)
        st.info(f"'{product_group}' 표준 템플릿 **{n}개 항목**이 복사됩니다.")
        ok = st.form_submit_button("모델 생성 + 템플릿 복사", type="primary")
    if ok:
        if not name.strip():
            st.error("모델명을 입력해 주세요.")
            return
        mid = db.create_model(name.strip(), code.strip(), product_group, dev_stage,
                              owner.strip(), start_date.strip(), end_date.strip(),
                              st.session_state.user["name"])
        st.success(f"모델이 생성되었습니다. (ID {mid}) 상세 화면으로 이동합니다.")
        st.session_state.selected_model = mid
        goto("모델 상세")


# ---------------- 모델 상세 · 편집 ----------------
def model_detail_view():
    mid = st.session_state.get("selected_model")
    model = db.get_model(mid) if mid else None
    if not model:
        st.warning("선택된 모델이 없습니다. 대시보드에서 모델을 선택해 주세요.")
        return

    st.header(f"🔧 {model['name']} — 시험표준 편집")
    st.caption(f"제품군 {model['product_group']} · 단계 {model['dev_stage']} · 담당자 {model['owner']}")

    # 메타 편집
    with st.expander("모델 정보 수정"):
        with st.form("edit_meta"):
            c1, c2, c3 = st.columns(3)
            owner = c1.text_input("담당자", value=model["owner"] or "")
            status = c2.selectbox("상태", PROGRESS_STATES,
                                  index=PROGRESS_STATES.index(model["status"])
                                  if model["status"] in PROGRESS_STATES else 0)
            stage = c3.selectbox("단계", DEV_STAGES,
                                 index=DEV_STAGES.index(model["dev_stage"])
                                 if model["dev_stage"] in DEV_STAGES else 0)
            d1, d2 = st.columns(2)
            start_date = d1.text_input("시작일", value=model["start_date"] or "")
            end_date = d2.text_input("완료예정일", value=model["end_date"] or "")
            if st.form_submit_button("정보 저장"):
                db.update_model_meta(mid, {
                    "owner": owner.strip(), "status": status, "dev_stage": stage,
                    "start_date": start_date.strip(), "end_date": end_date.strip(),
                }, st.session_state.user["name"])
                st.success("모델 정보를 저장했습니다.")
                st.rerun()

    # 시험항목 편집 표
    items = db.get_model_items(mid)
    df = pd.DataFrame(items)[FIELDS] if items else pd.DataFrame(columns=FIELDS)
    df = df.rename(columns=COL_LABELS)

    st.markdown("#### 시험항목 (셀을 직접 편집 · 행 추가/삭제 가능)")
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            COL_LABELS["seq"]: st.column_config.NumberColumn(width="small"),
            COL_LABELS["category"]: st.column_config.TextColumn(width="medium"),
            COL_LABELS["stage"]: st.column_config.SelectboxColumn(options=ITEM_STAGES, width="small"),
            COL_LABELS["applicable"]: st.column_config.SelectboxColumn(options=["Y", "N"], width="small"),
            COL_LABELS["progress"]: st.column_config.SelectboxColumn(options=PROGRESS_STATES, width="small"),
            COL_LABELS["result"]: st.column_config.SelectboxColumn(options=RESULTS, width="small"),
            COL_LABELS["spec"]: st.column_config.TextColumn(width="large"),
            COL_LABELS["criteria"]: st.column_config.TextColumn(width="large"),
        },
        key=f"editor_{mid}",
    )

    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("💾 저장", type="primary"):
        inv = {v: k for k, v in COL_LABELS.items()}
        records = edited.rename(columns=inv).to_dict("records")
        cleaned = []
        for rec in records:
            if not (str(rec.get("item_name") or "").strip()):
                continue  # 빈 항목 스킵
            cleaned.append({f: rec.get(f) for f in FIELDS})
        db.replace_model_items(mid, cleaned, st.session_state.user["name"])
        st.success(f"{len(cleaned)}건 저장했습니다.")
        st.rerun()

    xlsx = build_model_xlsx(model, db.get_model_items(mid))
    c2.download_button("⬇ 엑셀 내보내기", data=xlsx,
                       file_name=f"{model['name']}_Reliability_Test.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander("⚠ 모델 삭제"):
        if st.button("이 모델 삭제", type="secondary"):
            db.delete_model(mid, st.session_state.user["name"])
            st.session_state.selected_model = None
            goto("대시보드")


# ---------------- 제품군 비교표 ----------------
def compare_view():
    st.header("📊 제품군 비교표")
    st.caption("표준 템플릿 기준 · 시험항목 × 제품군 매트릭스")
    groups = st.multiselect("비교할 제품군", PRODUCT_GROUPS, default=PRODUCT_GROUPS)
    view_mode = st.radio("표시", ["전체", "조건이 다른 항목만"], horizontal=True)
    only_diff = view_mode == "조건이 다른 항목만"
    if not groups:
        st.warning("비교할 제품군을 1개 이상 선택해 주세요.")
        return

    items_by_group = {g: db.get_template_items(g) for g in groups}
    rows = build_matrix(items_by_group, groups)
    if only_diff:
        rows = [r for r in rows if r["diff"]]
    if not rows:
        st.info("표시할 항목이 없습니다.")
        return

    # Streamlit 테마(라이트/다크)에 맞춰 팔레트 선택 — 글자색까지 명시해 가독성 보장
    try:
        dark = st.context.theme.type == "dark"
    except Exception:
        dark = False
    st.markdown(render_html(rows, groups, dark=dark), unsafe_allow_html=True)


# ---------------- 템플릿 관리 ----------------
def template_manage_view():
    st.header("🗂 표준 템플릿 관리")
    st.caption("여기서 수정한 표준은 이후 **신규 모델 등록** 시 복사본에 반영됩니다. "
               "이미 생성된 모델의 시험항목에는 영향이 없습니다.")
    pg = st.selectbox("제품군", PRODUCT_GROUPS)
    items = db.get_template_items(pg)
    df = pd.DataFrame(items)[TPL_FIELDS] if items else pd.DataFrame(columns=TPL_FIELDS)
    df = df.rename(columns=TPL_LABELS)

    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            TPL_LABELS["seq"]: st.column_config.NumberColumn(width="small"),
            TPL_LABELS["spec"]: st.column_config.TextColumn(width="large"),
            TPL_LABELS["criteria"]: st.column_config.TextColumn(width="large"),
        },
        key=f"tpl_editor_{pg}",
    )

    if st.button("💾 템플릿 저장", type="primary"):
        inv = {v: k for k, v in TPL_LABELS.items()}
        records = edited.rename(columns=inv).to_dict("records")
        cleaned = [
            {f: rec.get(f) for f in TPL_FIELDS}
            for rec in records
            if str(rec.get("item_name") or "").strip()
        ]
        db.replace_template_items(pg, cleaned, st.session_state.user["name"])
        st.success(f"'{pg}' 템플릿 {len(cleaned)}건을 저장했습니다.")
        st.rerun()


# ---------------- 변경이력 ----------------
def changelog_view():
    st.header("🕑 변경 이력")
    logs = db.get_change_log()
    if not logs:
        st.info("기록된 변경 이력이 없습니다.")
        return
    df = pd.DataFrame(logs)[["ts", "user_name", "entity", "entity_id", "action", "detail"]]
    df.columns = ["일시", "사용자", "대상", "대상ID", "동작", "상세"]
    st.dataframe(df, use_container_width=True, hide_index=True)


# ---------------- 라우팅 ----------------
def main():
    if "user" not in st.session_state:
        login_view()
        return

    # 버튼으로 요청된 이동을 라디오(위젯) 생성 전에 반영한다.
    if "_goto" in st.session_state:
        st.session_state.page = st.session_state.pop("_goto")
    if st.session_state.get("page") not in PAGES:
        st.session_state.page = "대시보드"

    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.user['name']}**  \n`{st.session_state.user['role']}`")
        st.divider()
        page = st.radio("메뉴", PAGES, key="page")
        st.divider()
        if st.button("로그아웃"):
            for k in ("user", "page", "selected_model"):
                st.session_state.pop(k, None)
            st.rerun()

    if page == "대시보드":
        dashboard_view()
    elif page == "신규 모델 등록":
        new_model_view()
    elif page == "모델 상세":
        model_detail_view()
    elif page == "제품군 비교표":
        compare_view()
    elif page == "템플릿 관리":
        template_manage_view()
    elif page == "변경 이력":
        changelog_view()


main()
