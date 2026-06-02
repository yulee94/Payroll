"""
services/preview_grid_filter.py - Excel 미리보기 그리드 열 필터
"""

from __future__ import annotations

from services.preview_export import GridRow

EMPTY_LABEL = "(빈 값)"

# 열 이름에 포함되면 값 개수와 관계없이 필터 허용
_CATEGORICAL_HEADER_KEYWORDS = (
    "계열사",
    "사업장",
    "법인",
    "부서",
    "근무지",
    "소속",
    "고용형태",
    "성명",
    "이름",
    "장애",
    "시니어",
    "연차표기",
    "연차/결근표기",
)

MAX_AUTO_FILTER_VALUES = 150


def find_header_row_index(grid_rows: list[GridRow]) -> int | None:
    return next((i for i, g in enumerate(grid_rows) if g.role == "header"), None)


def cell_display_value(raw: str) -> str:
    text = str(raw or "").strip()
    return text if text else EMPTY_LABEL


def column_header_label(grid_rows: list[GridRow], header_idx: int | None, col: int) -> str:
    if header_idx is None:
        return f"열{col + 1}"
    row = grid_rows[header_idx]
    if col < len(row.cells):
        label = str(row.cells[col] or "").strip()
        if label:
            return label
    return f"열{col + 1}"


def column_distinct_values(grid_rows: list[GridRow], col: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for grow in grid_rows:
        if grow.role != "data":
            continue
        display = cell_display_value(grow.cells[col] if col < len(grow.cells) else "")
        if display in seen:
            continue
        seen.add(display)
        out.append(display)
    out.sort(key=lambda x: (x == EMPTY_LABEL, x))
    return out


def _header_is_categorical(label: str) -> bool:
    text = str(label or "").strip()
    if not text:
        return False
    return any(k in text for k in _CATEGORICAL_HEADER_KEYWORDS)


def _looks_numeric(display: str) -> bool:
    if display == EMPTY_LABEL:
        return False
    t = display.replace(",", "").replace("%", "").strip()
    if not t or t in ("-", "—"):
        return False
    try:
        float(t)
        return True
    except ValueError:
        return False


def is_column_filterable(
    grid_rows: list[GridRow],
    col: int,
    *,
    header_idx: int | None = None,
) -> bool:
    if header_idx is None:
        header_idx = find_header_row_index(grid_rows)
    values = column_distinct_values(grid_rows, col)
    if len(values) < 2:
        return False
    if len(values) > MAX_AUTO_FILTER_VALUES:
        return False
    label = column_header_label(grid_rows, header_idx, col)
    if _header_is_categorical(label):
        return True
    if all(_looks_numeric(v) for v in values):
        return False
    return len(values) <= 40


def filterable_columns(grid_rows: list[GridRow], ncol: int) -> list[int]:
    header_idx = find_header_row_index(grid_rows)
    cols: list[int] = []
    for c in range(ncol):
        if is_column_filterable(grid_rows, c, header_idx=header_idx):
            cols.append(c)
    return cols


def apply_grid_filters(
    grid_rows: list[GridRow],
    filters: dict[int, frozenset[str]],
) -> list[GridRow]:
    if not filters:
        return list(grid_rows)
    active = {col: allowed for col, allowed in filters.items() if allowed}
    if not active:
        return list(grid_rows)

    out: list[GridRow] = []
    for grow in grid_rows:
        if grow.role != "data":
            out.append(grow)
            continue
        visible = True
        for col, allowed in active.items():
            display = cell_display_value(grow.cells[col] if col < len(grow.cells) else "")
            if display not in allowed:
                visible = False
                break
        if visible:
            out.append(grow)
    return out


def count_data_rows(grid_rows: list[GridRow]) -> int:
    return sum(1 for g in grid_rows if g.role == "data")


def format_filter_summary(
    grid_rows: list[GridRow],
    filters: dict[int, frozenset[str]],
    *,
    visible_rows: list[GridRow] | None = None,
) -> str:
    if not filters:
        return ""
    header_idx = find_header_row_index(grid_rows)
    parts: list[str] = []
    for col in sorted(filters):
        allowed = filters[col]
        if not allowed:
            continue
        label = column_header_label(grid_rows, header_idx, col)
        if len(allowed) == 1:
            parts.append(f"{label}={next(iter(allowed))}")
        else:
            parts.append(f"{label}({len(allowed)}개)")
    if not parts:
        return ""
    total = count_data_rows(grid_rows)
    shown = count_data_rows(visible_rows) if visible_rows is not None else total
    return f"필터: {', '.join(parts)} · 데이터 {shown}/{total}행"
