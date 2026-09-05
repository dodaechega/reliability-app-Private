# SQLite 데이터베이스 초기화 · 시드 · CRUD · 변경이력 기록을 담당하는 데이터 계층

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from seed_data import PRODUCT_GROUPS, TEMPLATE_ITEMS

DB_PATH = os.environ.get("RELIABILITY_DB_PATH",
                         os.path.join(os.path.dirname(__file__), "data", "reliability.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    """읽기/쓰기 모두 연결을 닫고, 실패한 쓰기는 전체 롤백한다."""
    conn = get_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """테이블 생성 + 최초 1회 시드 데이터 적재."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        c = conn.cursor()
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version >= 1:
            return
        fresh = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='template_items'"
        ).fetchone() is None
        schema = """
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
            CREATE INDEX IF NOT EXISTS idx_model_items_model_seq
                ON model_test_items(model_id, seq, id);
            CREATE INDEX IF NOT EXISTS idx_template_group_seq
                ON template_items(product_group, seq, id);
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
        for statement in schema.split(";"):
            if statement.strip():
                c.execute(statement)
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
        # 새 DB에서만 시드한다. 기존 DB의 빈 템플릿은 사용자 편집 결과다.
        if fresh:
            for pg in PRODUCT_GROUPS:
                for row in TEMPLATE_ITEMS.get(pg, []):
                    seq, category, item_name, code, spec, criteria, qty, days, available, remark = row
                    c.execute(
                        """INSERT INTO template_items
                           (product_group, seq, category, item_name, code, spec, criteria, qty, days, available, remark)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (pg, seq, category, item_name, code, spec, criteria, qty, days, available, remark),
                    )
        c.execute("PRAGMA user_version = 1")


def log_change(user_name, entity, entity_id, action, detail="", *, conn=None):
    if conn is None:
        with connection() as conn:
            log_change(user_name, entity, entity_id, action, detail, conn=conn)
        return
    conn.execute(
        "INSERT INTO change_log (ts, user_name, entity, entity_id, action, detail) VALUES (?,?,?,?,?,?)",
        (now(), user_name, entity, entity_id, action, detail),
    )


# ---------- 사용자 ----------
def get_or_create_user(name, login_id=None):
    login_id = login_id or name
    with connection() as conn:
        conn.execute(
            """INSERT INTO users (login_id, name, role, created_at) VALUES (?,?,?,?)
               ON CONFLICT(login_id) DO NOTHING""",
            (login_id, name, "user", now()),
        )
        row = conn.execute("SELECT * FROM users WHERE login_id = ?", (login_id,)).fetchone()
        return dict(row)


def list_users():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
        return [dict(r) for r in rows]


# ---------- 템플릿 ----------
def get_template_items(product_group):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM template_items WHERE product_group = ? ORDER BY seq, id",
            (product_group,),
        ).fetchall()
        return [dict(r) for r in rows]


def replace_template_items(product_group, items, user_name):
    """편집된 표준 템플릿으로 해당 제품군 전체 교체. 이후 신규 모델 생성부터 반영."""
    with connection() as conn:
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
        log_change(user_name, "template", 0, "저장", f"{product_group} 템플릿 {len(items)}건 저장", conn=conn)


def count_template_items(product_group):
    with connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM template_items WHERE product_group = ?", (product_group,)
        ).fetchone()[0]
        return n


# ---------- 모델 ----------
def create_model(name, code, product_group, dev_stage, owner, start_date, end_date, created_by):
    """모델 생성 + 해당 제품군 템플릿을 model_test_items로 복사."""
    with connection() as conn:
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
        log_change(created_by, "model", model_id, "생성",
                   f"{name} ({product_group}/{dev_stage}) 템플릿 {len(templates)}건 복사", conn=conn)
        return model_id


def list_models():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM models ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_model(model_id):
    with connection() as conn:
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(row) if row else None


def update_model_meta(model_id, fields, user_name):
    allowed = {"owner", "status", "dev_stage", "start_date", "end_date"}
    if not fields or not set(fields) <= allowed:
        raise ValueError("수정할 모델 정보 필드가 올바르지 않습니다.")
    with connection() as conn:
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE models SET {sets} WHERE id = ?", (*fields.values(), model_id))
        log_change(user_name, "model", model_id, "수정", ", ".join(f"{k}={v}" for k, v in fields.items()), conn=conn)


def delete_model(model_id, user_name):
    with connection() as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        log_change(user_name, "model", model_id, "삭제", "", conn=conn)


# ---------- 모델별 시험항목 ----------
def get_model_items(model_id):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM model_test_items WHERE model_id = ? ORDER BY seq, id", (model_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def replace_model_items(model_id, items, user_name):
    """편집된 시험항목 목록으로 전체 교체(간단·확실). 변경 건수만 이력에 기록."""
    with connection() as conn:
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
        log_change(user_name, "model_items", model_id, "저장", f"{len(items)}건 저장", conn=conn)


# ---------- 변경이력 ----------
def get_change_log(limit=300):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM change_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_items_by_model():
    """통계 화면의 모델별 N회 조회를 한 번의 순회로 대체한다."""
    grouped = {}
    with connection() as conn:
        for row in conn.execute("SELECT * FROM model_test_items ORDER BY model_id, seq, id"):
            grouped.setdefault(row["model_id"], []).append(dict(row))
    return grouped
