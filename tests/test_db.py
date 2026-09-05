# 데이터 보존·이력 원자성·조회 비용 회귀 검증.
import sqlite3

import pytest

import db
from seed_data import PRODUCT_GROUPS


def test_seed_once_and_keep_intentionally_empty_templates():
    assert sum(db.count_template_items(g) for g in PRODUCT_GROUPS) == 52
    for group in PRODUCT_GROUPS:
        db.replace_template_items(group, [], "QA")
    db.init_db()
    assert sum(db.count_template_items(g) for g in PRODUCT_GROUPS) == 0


def test_empty_legacy_templates_are_not_reseeded():
    with db.connection() as conn:
        conn.execute("DELETE FROM template_items")
        conn.execute("PRAGMA user_version = 0")
    db.init_db()
    assert sum(db.count_template_items(g) for g in PRODUCT_GROUPS) == 0


def test_failed_initial_seed_rolls_back_schema_and_can_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "fresh.db"))
    original = db.TEMPLATE_ITEMS
    monkeypatch.setattr(db, "TEMPLATE_ITEMS", {PRODUCT_GROUPS[0]: [(1,)]})
    with pytest.raises(ValueError):
        db.init_db()
    with db.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    monkeypatch.setattr(db, "TEMPLATE_ITEMS", original)
    db.init_db()
    assert sum(db.count_template_items(g) for g in PRODUCT_GROUPS) == 52


def test_legacy_migration_preserves_data(model_id):
    before = db.get_model_items(model_id)
    with db.connection() as conn:
        conn.execute("ALTER TABLE model_test_items DROP COLUMN stage")
        conn.execute("PRAGMA user_version = 0")
    db.init_db()
    assert db.get_model_items(model_id) == before
    assert len(db.get_change_log()) == 1


def test_copy_is_independent_and_stage_round_trips(model_id):
    items = db.get_model_items(model_id)
    assert len(items) == 17
    assert {it["stage"] for it in items} == {"PR"}
    db.replace_template_items("리모컨/IoT", [], "QA")
    assert db.get_model_items(model_id) == items
    items[0].update(stage="MP", result="NG", progress="완료")
    db.replace_model_items(model_id, items, "QA")
    saved = db.get_model_items(model_id)
    assert saved[0]["stage"] == "MP"
    assert saved[0]["result"] == "NG"
    db.delete_model(model_id, "QA")
    assert db.get_model(model_id) is None
    assert db.get_model_items(model_id) == []
    assert db.get_change_log()[0]["action"] == "삭제"


@pytest.mark.parametrize("mutation", ["create", "items", "template", "meta", "delete"])
def test_audit_failure_rolls_back_mutation(model_id, mutation):
    before_model = db.get_model(model_id)
    before_items = db.get_model_items(model_id)
    before_template = db.get_template_items("리모컨/IoT")
    before_logs = db.get_change_log()
    with db.connection() as conn:
        conn.execute("""CREATE TRIGGER fail_audit BEFORE INSERT ON change_log
                        BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        if mutation == "create":
            db.create_model("Fail", "", "리모컨/IoT", "PR", "QA", "", "", "QA")
        elif mutation == "items":
            db.replace_model_items(model_id, [], "QA")
        elif mutation == "template":
            db.replace_template_items("리모컨/IoT", [], "QA")
        elif mutation == "meta":
            db.update_model_meta(model_id, {"owner": "changed"}, "QA")
        else:
            db.delete_model(model_id, "QA")
    assert db.get_model(model_id) == before_model
    assert db.get_model_items(model_id) == before_items
    assert db.get_template_items("리모컨/IoT") == before_template
    assert db.get_change_log() == before_logs
    assert len(db.list_models()) == 1
    # A failed transaction must also release its write lock.
    with db.connection() as conn:
        conn.execute("DROP TRIGGER fail_audit")
    db.update_model_meta(model_id, {"owner": "recovered"}, "QA")


def test_bad_item_rolls_back_delete_and_partial_insert(model_id):
    items = db.get_model_items(model_id)
    with pytest.raises(sqlite3.ProgrammingError):
        db.replace_model_items(model_id, [items[0], {"item_name": object()}], "QA")
    assert db.get_model_items(model_id) == items


def test_metadata_fields_are_allowlisted(model_id):
    with pytest.raises(ValueError):
        db.update_model_meta(model_id, {"name = 'oops', owner": "QA"}, "QA")
    assert db.get_model(model_id)["name"] == "Test"


def test_bulk_statistics_query_count_and_indexes(model_id, monkeypatch):
    expected = {model_id: db.get_model_items(model_id)}
    for i in range(9):
        mid = db.create_model(str(i), "", "스피커", "SR", "QA", "", "", "QA")
        expected[mid] = db.get_model_items(mid)
    queries = []
    original = db.get_conn

    def traced_conn():
        conn = original()
        conn.set_trace_callback(queries.append)
        return conn

    monkeypatch.setattr(db, "get_conn", traced_conn)
    assert db.get_items_by_model() == expected
    assert len([q for q in queries if q.startswith("SELECT")]) == 1
    with db.connection() as conn:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM model_test_items WHERE model_id=? ORDER BY seq,id",
            (model_id,),
        ).fetchall()
    assert any("idx_model_items_model_seq" in row[3] for row in plan)
