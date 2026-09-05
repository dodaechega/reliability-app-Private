# 모델별 시험표준을 기존 양식과 유사한 엑셀(.xlsx)로 내보내는 유틸

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HEADER_FILL = PatternFill("solid", fgColor="165ABC")
TITLE_FILL = PatternFill("solid", fgColor="E7E7E7")
NA_FILL = PatternFill("solid", fgColor="F2DEDE")
WHITE = Font(color="FFFFFF", bold=True)
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="center", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

COLUMNS = [
    ("No", 6), ("종류", 16), ("Item Test", 30), ("State", 8), ("Code", 8),
    ("Specification / Setting Condition", 48), ("판정기준", 26),
    ("Qty", 10), ("Days", 7), ("적용", 7), ("진행상태", 10),
    ("결과", 7), ("Remark", 18),
]
FIELDS = ["seq", "category", "item_name", "stage", "code", "spec", "criteria",
          "qty", "days", "applicable", "progress", "result", "remark"]


def build_model_xlsx(model, items):
    wb = Workbook()
    ws = wb.active
    ws.title = "Reliability Test"
    ncol = len(COLUMNS)

    # 제목 행
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    t = ws.cell(1, 1, f"□ {model['name']} ({model.get('code') or '-'}) — Reliability Test Standard")
    t.font = Font(bold=True, size=13)
    t.fill = TITLE_FILL
    t.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26

    # 메타 행
    meta = (f"제품군: {model['product_group']}   |   개발단계: {model.get('dev_stage') or '-'}   |   "
            f"담당자: {model.get('owner') or '-'}   |   일정: {model.get('start_date') or '-'} ~ "
            f"{model.get('end_date') or '-'}   |   상태: {model.get('status') or '-'}")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
    m = ws.cell(2, 1, meta)
    m.alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 20

    # 헤더 행
    hr = 3
    for j, (title, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(hr, j, title)
        cell.fill = HEADER_FILL
        cell.font = WHITE
        cell.alignment = CENTER
        cell.border = BORDER
        ws.column_dimensions[chr(64 + j)].width = width
    ws.row_dimensions[hr].height = 24

    # 데이터 행
    for i, it in enumerate(items):
        r = hr + 1 + i
        for j, f in enumerate(FIELDS, start=1):
            val = it.get(f, "")
            cell = ws.cell(r, j, val if val is not None else "")
            if isinstance(val, str):
                cell.data_type = "s"  # 입력 문자열을 엑셀 수식으로 실행하지 않는다.
            cell.border = BORDER
            cell.alignment = CENTER if f in ("seq", "stage", "code", "qty", "days", "applicable", "progress", "result") else WRAP
        # 적용=N 이면 회색조 강조
        if str(it.get("applicable", "")).strip().upper() == "N":
            for j in range(1, ncol + 1):
                ws.cell(r, j).fill = NA_FILL

    ws.freeze_panes = "A4"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
