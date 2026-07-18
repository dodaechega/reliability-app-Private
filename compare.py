# 제품군 간 시험조건 비교 매트릭스 생성 로직 (키워드 분류 · 라이트/다크 적응형 HTML 렌더링)

import html

# (비교 카테고리 라벨, 매칭 키워드) — 위에서부터 첫 매칭 우선.
# code 는 제품군마다 체계가 달라(HUB/BLE/고무/사출은 공란) 항목명 키워드로 묶는다.
CATEGORY_RULES = [
    ("진동 (Vibration)", ["vibration"]),
    ("낙하 (Drop)", ["drop"]),
    ("고온 (Hot / High Temp)", ["high temperature", "hot"]),
    ("저온 (Cold / Low Temp)", ["low temperature", "cold"]),
    ("보관 사이클 (Storage)", ["storage"]),
    ("항온항습 (Temp/Humidity)", ["humidity"]),
    ("열충격 (Thermal Shock)", ["thermal shock"]),
    ("마모/인쇄 (Wear/Eraser)", ["eraser", "rubbing", "wear"]),
    ("액체 유입 (Liquid)", ["liquid"]),
    ("에이징 (Aging)", ["aging"]),
    ("파괴 시험 (Destructive)", ["destructive", "voice"]),
    ("연속 부하 (Load/Durability)", ["load", "durability"]),
    ("동작 수명 (Operating Life)", ["operating life"]),
    ("인체 하중 (Body Weight)", ["human", "body weight"]),
    ("내화학 (Chemical)", ["chemical"]),
    ("초기 시험 (Initial/OQC)", ["initial"]),
]
ETC = "기타"
CATEGORY_ORDER = [label for label, _ in CATEGORY_RULES] + [ETC]


def classify(item_name):
    name = (item_name or "").lower()
    for label, keywords in CATEGORY_RULES:
        if any(k in name for k in keywords):
            return label
    return ETC


def _cell_signature(items):
    """조건 비교용 정규화 시그니처 (항목명·조건·수량·기간)."""
    parts = []
    for it in items:
        raw = f"{it.get('item_name','')}|{it.get('spec','')}|{it.get('qty','')}|{it.get('days','')}"
        parts.append(" ".join(raw.split()))
    return "\n".join(sorted(parts))


def build_matrix(items_by_group, groups):
    """rows: [{category, cells: {group: [item,...]}, present, diff}] (카테고리 순서 고정)."""
    grouped = {}  # category -> group -> [items]
    for g in groups:
        for it in items_by_group.get(g, []):
            grouped.setdefault(classify(it["item_name"]), {}).setdefault(g, []).append(it)

    rows = []
    for cat in CATEGORY_ORDER:
        if cat not in grouped:
            continue
        cells = {g: grouped[cat].get(g, []) for g in groups}
        sigs = {_cell_signature(v) for v in cells.values() if v}
        present = sum(1 for v in cells.values() if v)
        rows.append({
            "category": cat,
            "cells": cells,
            "present": present,
            "diff": present >= 2 and len(sigs) > 1,
        })
    return rows


# ---------- Apple 스타일 팔레트 (라이트/다크 모두 글자색을 명시해 테마 독립적) ----------
_PALETTES = {
    "light": dict(
        text="#1D1D1F", sub="#6E6E73", faint="#AEAEB2",
        border="rgba(0,0,0,0.10)", hairline="rgba(0,0,0,0.07)",
        headbg="rgba(0,0,0,0.03)", headtext="#6E6E73",
        diffbg="rgba(255,149,0,0.10)", diffbar="#FF9500",
        samebg="rgba(52,199,89,0.09)", samebar="#34C759",
        redtext="#FF3B30", redbg="rgba(255,59,48,0.10)",
    ),
    "dark": dict(
        text="#F5F5F7", sub="#A1A1A6", faint="#6E6E73",
        border="rgba(255,255,255,0.14)", hairline="rgba(255,255,255,0.09)",
        headbg="rgba(255,255,255,0.05)", headtext="#A1A1A6",
        diffbg="rgba(255,159,10,0.14)", diffbar="#FF9F0A",
        samebg="rgba(48,209,88,0.12)", samebar="#30D158",
        redtext="#FF453A", redbg="rgba(255,69,58,0.16)",
    ),
}
_FONT = ('-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, '
         '"Noto Sans KR", sans-serif')


def _render_item(it, c):
    """셀 내 항목 1건 — 항목명(강조) / 조건(보조) / 메타(캡션) 3단 위계."""
    name = html.escape(it.get("item_name") or "")
    spec = html.escape(it.get("spec") or "")
    badge = ""
    if (it.get("available") or "").strip().lower() == "can't":
        badge = (f'<span style="font-size:10px; font-weight:600; color:{c["redtext"]}; '
                 f'background:{c["redbg"]}; padding:1px 7px; border-radius:99px; '
                 f'margin-left:5px; white-space:nowrap; vertical-align:1px;">수행 불가</span>')
    meta_bits = []
    if (it.get("qty") or "").strip():
        meta_bits.append(f"Qty {html.escape(it['qty'])}")
    if (it.get("days") or "").strip() not in ("", "-"):
        meta_bits.append(f"{html.escape(it['days'])}일")
    out = [f'<div style="font-weight:600; font-size:12.5px; line-height:1.4; '
           f'color:{c["text"]};">{name}{badge}</div>']
    if spec:
        out.append(f'<div style="font-size:12px; line-height:1.55; color:{c["sub"]}; '
                   f'margin-top:2px;">{spec}</div>')
    if meta_bits:
        out.append(f'<div style="font-size:11px; color:{c["faint"]}; '
                   f'margin-top:3px;">{" · ".join(meta_bits)}</div>')
    return "".join(out)


def _legend(c):
    def dot(color):
        return (f'<span style="display:inline-block; width:8px; height:8px; '
                f'border-radius:50%; background:{color}; margin-right:5px; '
                f'vertical-align:0.5px;"></span>')
    badge = (f'<span style="font-size:10px; font-weight:600; color:{c["redtext"]}; '
             f'background:{c["redbg"]}; padding:1px 7px; border-radius:99px; '
             f'margin-right:5px;">수행 불가</span>')
    item = 'style="white-space:nowrap;"'
    return (f'<div style="display:flex; gap:16px; flex-wrap:wrap; align-items:center; '
            f'margin:2px 0 12px; font-size:12px; color:{c["sub"]};">'
            f'<span {item}>{dot(c["diffbar"])}제품군 간 조건 상이</span>'
            f'<span {item}>{dot(c["samebar"])}조건 동일</span>'
            f'<span {item}>표시 없음 = 단일 제품군 전용</span>'
            f'<span {item}>{badge}자체 시험 불가</span></div>')


def render_html(rows, groups, dark=False):
    """비교 매트릭스를 Apple 스타일(틴트+액센트 바, 3단 타이포) HTML로 렌더링한다."""
    c = _PALETTES["dark" if dark else "light"]

    td_base = ("padding:11px 13px; vertical-align:top; "
               f"border-top:1px solid {c['hairline']};")
    th = (f"padding:10px 13px; font-size:12px; font-weight:600; text-align:left; "
          f"letter-spacing:0.01em; color:{c['headtext']}; background:{c['headbg']}; "
          f"border-bottom:1px solid {c['border']};")

    min_w = 150 + 190 * len(groups)
    out = [f'<div style="font-family:{_FONT};">', _legend(c)]
    out.append(f'<div style="border:1px solid {c["border"]}; border-radius:12px; '
               f'overflow:hidden;"><div style="overflow-x:auto;">')
    out.append(f'<table style="border-collapse:separate; border-spacing:0; width:100%; '
               f'min-width:{min_w}px; table-layout:fixed;">')
    out.append('<colgroup><col style="width:150px;">'
               + f'<col span="{len(groups)}">' + '</colgroup>')
    out.append("<tr>" + f'<th style="{th}">시험항목</th>'
               + "".join(f'<th style="{th}">{html.escape(g)}</th>' for g in groups)
               + "</tr>")

    for i, r in enumerate(rows):
        if r["diff"]:
            bg, bar = c["diffbg"], c["diffbar"]
        elif r["present"] >= 2:
            bg, bar = c["samebg"], c["samebar"]
        else:
            bg, bar = "", ""
        row_bg = f" background:{bg};" if bg else ""
        border = td_base if i > 0 else td_base.replace(
            f"border-top:1px solid {c['hairline']};", "")
        accent = f" box-shadow:inset 3px 0 0 {bar};" if bar else ""

        head_td = (f'<td style="{border}{row_bg}{accent} font-weight:600; '
                   f'font-size:12.5px; line-height:1.4; color:{c["text"]};">'
                   f'{html.escape(r["category"])}</td>')
        cells = []
        for g in groups:
            items = r["cells"][g]
            if items:
                body = "".join(
                    f'<div style="margin-top:{"9px" if j else "0"};">'
                    f'{_render_item(it, c)}</div>'
                    for j, it in enumerate(items))
            else:
                body = f'<span style="color:{c["faint"]};">—</span>'
            cells.append(f'<td style="{border}{row_bg}">{body}</td>')
        out.append("<tr>" + head_td + "".join(cells) + "</tr>")

    out.append("</table></div></div></div>")
    return "".join(out)
