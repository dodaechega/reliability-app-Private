# 모든 검증은 운영 DB와 분리된 임시 데이터베이스에서 실행한다.
import pytest
import streamlit as st

import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    st.cache_resource.clear()
    st.cache_data.clear()
    db.init_db()
    yield
    st.cache_resource.clear()
    st.cache_data.clear()


@pytest.fixture
def model_id():
    return db.create_model("Test", "T01", "리모컨/IoT", "PR", "QA", "", "", "QA")
