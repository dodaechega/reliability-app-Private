# 실제 앱을 AppTest로 실행해 로그인·탐색·생성·통계 흐름을 검증한다.
from pathlib import Path

from streamlit.testing.v1 import AppTest

import db

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def button(at, label):
    return next(b for b in at.button if b.label == label)


def test_login_create_navigate_and_logout():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.text_input[0].set_value("QA tester")
    button(at, "로그인").click().run()
    assert not at.exception
    at.radio(key="page").set_value("신규 모델 등록").run()
    at.selectbox[0].select("스피커").run()
    assert "8개 항목" in at.info[0].value
    at.text_input[0].set_value("Speaker test")
    button(at, "모델 생성 + 템플릿 복사").click().run()
    assert not at.exception
    assert at.session_state.page == "모델 상세"
    mid = at.session_state.selected_model
    assert len(db.get_model_items(mid)) == 8
    button(at, "💾 저장").click().run()
    assert not at.exception
    assert len(db.get_model_items(mid)) == 8
    for page in ["대시보드", "제품군 비교표", "통계 리포트", "템플릿 관리", "변경 이력"]:
        at.radio(key="page").set_value(page).run()
        assert not at.exception, page
    button(at, "로그아웃").click().run()
    assert not at.exception
    assert "user" not in at.session_state


def test_statistics_excludes_not_applicable_and_keeps_empty_models(model_id):
    items = db.get_model_items(model_id)[:4]
    for it in items:
        it.update(applicable="Y", progress="완료", result="NG")
    items[1]["applicable"] = "N"
    items[2]["progress"] = "해당없음"
    items[3].update(result="OK", progress="진행")
    db.replace_model_items(model_id, items, "QA")
    db.create_model("Empty", "", "Empty", "PR", "QA", "", "", "QA")
    at = AppTest.from_file(APP, default_timeout=15)
    at.session_state.user = {"name": "QA", "role": "user"}
    at.session_state.page = "통계 리포트"
    at.run()
    assert not at.exception
    assert [m.value for m in at.metric] == ["2", "2", "50%", "1"]


def test_rerun_reuses_export_and_refreshes_after_save(model_id, monkeypatch):
    import export_excel

    calls = []
    original = export_excel.build_model_xlsx

    def build(model, items):
        calls.append(items[0]["spec"])
        return original(model, items)

    monkeypatch.setattr(export_excel, "build_model_xlsx", build)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state.user = {"name": "QA", "role": "user"}
    at.session_state.page = "모델 상세"
    at.session_state.selected_model = model_id
    at.run()
    assert not at.exception
    at.run()
    assert not at.exception
    assert len(calls) == 1
    items = db.get_model_items(model_id)
    items[0]["spec"] = "new saved specification"
    db.replace_model_items(model_id, items, "QA")
    at.run()
    assert not at.exception
    assert calls[-1] == "new saved specification"
    assert len(calls) == 2
