# SQLite 데이터베이스 초기화 · 시드 · CRUD · 변경이력 기록을 담당하는 데이터 계층

import sqlite3
import os
from datetime import datetime
from seed_data import PRODUCT_GROUPS, TEMPLATE_ITEMS

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "reliability.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """테이블 생성 + 최초 1회 시드 데이터 적재."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_id TEXT UNIQUE,
            name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_group TEXT,
            seq INTEGER,
            category TEXT,
            item_name TEXT,
            code TEXT,
            spec TEXT,
            criteria TEXT,
            qty TEXT,
            days TEXT,
            available TEXT,
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT,
            product_group TEXT,
            dev_stage TEXT,
            owner TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            created_by TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS model_test_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER,
            seq INTEGER,
            category TEXT,
            item_name TEXT,
            stage TEXT,
            code TEXT,
            spec TEXT,
            criteria TEXT,
            qty TEXT,
            days TEXT,
            applicable TEXT,
            progress TEXT,
            result TEXT,
            remark TEXT,
            FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            user_name TEXT,
            entity TEXT,
            entity_id INTEGER,
            action TEXT,
            detail TEXT
        );
        """
    )
    # stage 컬럼 마이그레이션 (State 드롭다운) — 기존 항목은 모델의 개발단계로 백필
    cols = [r[1] for r in c.execute("PRAGMA table_info(model_test_items)").fetchall()]
    if "stage" not in cols:
        c.execute("ALTER TABLE model_test_items ADD COLUMN stage TEXT")
        c.execute(
            """UPDATE model_test_items SET stage = (
                   SELECT m.dev_stage FROM models m
                   WHERE m.id = model_test_items.model_id
                     AND m.dev_stage IN ('PV','PR','SR','MP'))"""
        )
    # 관리자 계정 시드
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (login_id, name, role, created_at) VALUES (?,?,?,?)",
            ("admin", "관리자", "admin", now()),
        )
    # 표준 템플릿 시드 (비어있을 때만)
    if c.execute("SELECT COUNT(*) FROM template_items").fetchone()[0] == 0:
        for pg in PRODUCT_GROUPS:
            for row in TEMPLATE_ITEMS.get(pg, []):
                seq, category, item_name, code, spec, criteria, qty, days, available, remark = row
                c.execute(
                    """INSERT INTO template_items
                       (product_group, seq, category, item_name, code, spec, criteria, qty, days, available, remark)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (pg, seq, category, item_name, code, spec, criteria, qty, days, available, remark),
                )
    conn.commit()
    conn.close()


def log_change(user_name, entity, entity_id, action, detail=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO change_log (ts, user_name, entity, entity_id, action, detail) VALUES (?,?,?,?,?,?)",
        (now(), user_name, entity, entity_id, action, detail),
    )
    conn.commit()
    conn.close()


# ---------- 사용자 ----------
def get_or_create_user(name, login_id=None):
    login_id = login_id or name
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE login_id = ?", (login_id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (login_id, name, role, created_at) VALUES (?,?,?,?)",
            (login_id, name, "user", now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE login_id = ?", (login_id,)).fetchone()
    conn.close()
    return dict(row)


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- 템플릿 ----------
def get_template_items(product_group):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM template_items WHERE product_group = ? ORDER BY seq, id",
        (product_group,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def replace_template_items(product_group, items, user_name):
    """편집된 표준 템플릿으로 해당 제품군 전체 교체. 이후 신규 모델 생성부터 반영."""
    conn = get_conn()
    conn.execute("DELETE FROM template_items WHERE product_group = ?", (product_group,))
    for it in items:
        conn.execute(
            """INSERT INTO template_items
               (product_group, seq, category, item_name, code, spec, criteria, qty, days, available, remark)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (product_group, it.get("seq"), it.get("category"), it.get("item_name"), it.get("code"),
             it.get("spec"), it.get("criteria"), it.get("qty"), it.get("days"),
             it.get("available"), it.get("remark")),
        )
    conn.commit()
    conn.close()
    log_change(user_name, "template", 0, "저장", f"{product_group} 템플릿 {len(items)}건 저장")


def count_template_items(product_group):
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM template_items WHERE product_group = ?", (product_group,)
    ).fetchone()[0]
    conn.close()
    return n


# ---------- 모델 ----------
def create_model(name, code, product_group, dev_stage, owner, start_date, end_date, created_by):
    """모델 생성 + 해당 제품군 템플릿을 model_test_items로 복사."""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO models (name, code, product_group, dev_stage, owner, start_date, end_date, status, created_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (name, code, product_group, dev_stage, owner, start_date, end_date, "계획", created_by, now()),
    )
    model_id = cur.lastrowid
    templates = conn.execute(
        "SELECT * FROM template_items WHERE product_group = ? ORDER BY seq, id",
        (product_group,),
    ).fetchall()
    # State 기본값: 모델 개발단계가 PV/PR/SR/MP 중 하나면 그대로 물려받음
    stage = dev_stage if dev_stage in ("PV", "PR", "SR", "MP") else None
    for t in templates:
        # available(수행가능 여부)로 적용여부 기본값 결정
        applicable = "N" if (t["available"] or "").strip().lower() == "can't" else "Y"
        remark = t["remark"] or ""
        if t["available"]:
            note = f"[수행:{t['available']}]"
            remark = (note + " " + remark).strip()
        conn.execute(
            """INSERT INTO model_test_items
               (model_id, seq, category, item_name, stage, code, spec, criteria, qty, days, applicable, progress, result, remark)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (model_id, t["seq"], t["category"], t["item_name"], stage, t["code"], t["spec"],
             t["criteria"], t["qty"], t["days"], applicable, "계획", "-", remark),
        )
    conn.commit()
    conn.close()
    log_change(created_by, "model", model_id, "생성",
               f"{name} ({product_group}/{dev_stage}) 템플릿 {len(templates)}건 복사")
    return model_id


def list_models():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM models ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_model(model_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_model_meta(model_id, fields, user_name):
    conn = get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE models SET {sets} WHERE id = ?", (*fields.values(), model_id))
    conn.commit()
    conn.close()
    log_change(user_name, "model", model_id, "수정", ", ".join(f"{k}={v}" for k, v in fields.items()))


def delete_model(model_id, user_name):
    conn = get_conn()
    conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
    conn.commit()
    conn.close()
    log_change(user_name, "model", model_id, "삭제", "")


# ---------- 모델별 시험항목 ----------
def get_model_items(model_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM model_test_items WHERE model_id = ? ORDER BY seq, id", (model_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def replace_model_items(model_id, items, user_name):
    """편집된 시험항목 목록으로 전체 교체(간단·확실). 변경 건수만 이력에 기록."""
    conn = get_conn()
    conn.execute("DELETE FROM model_test_items WHERE model_id = ?", (model_id,))
    for it in items:
        conn.execute(
            """INSERT INTO model_test_items
               (model_id, seq, category, item_name, stage, code, spec, criteria, qty, days, applicable, progress, result, remark)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (model_id, it.get("seq"), it.get("category"), it.get("item_name"), it.get("stage"),
             it.get("code"), it.get("spec"), it.get("criteria"), it.get("qty"), it.get("days"),
             it.get("applicable"), it.get("progress"), it.get("result"), it.get("remark")),
        )
    conn.commit()
    conn.close()
    log_change(user_name, "model_items", model_id, "저장", f"{len(items)}건 저장")


# ---------- 변경이력 ----------
def get_change_log(limit=300):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM change_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
