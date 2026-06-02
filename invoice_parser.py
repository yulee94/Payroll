"""
invoice_parser.py - 도급비 청구서(26년05월 형식) 데이터 추출

- 1번 시트(청구내역): 급여·보험 등
- 2번 시트(근태): 지조외 = 조퇴시간(시간)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from roster_constants import find_fuzzy_name_key, norm_name_key
from utils import safe_number

from core.payroll.site_benefits import find_workers_day_column

DATA_START_ROW = 5

# 실제 청구서 열 번호 (1-based)
COL = {
    "no": 1,           # A
    "dept": 2,         # B 소속
    "name": 3,         # C 성명
    "hire": 4,         # D 입사일
    "base_days": 9,    # I 기준일
    "work_days": 10,   # J 근무일
    "unpaid": 11,      # K 무급/결근
    "leave": 12,       # L 휴가/연차
    "ot_hours": 13,    # M O/T(150%)
    "shift_hours": 14, # N 교대
    "night_hours": 15, # O 심야(50%)
    "special_hours": 16,   # P 특근(150%)
    "special_ext_hours": 17,  # Q 특근연장(50%)
    "early_leave": 18, # R 지조외 (청구 시트 — 근태 시트가 있으면 근태 우선)
    "base_hourly": 7,  # G
    "ordinary_hourly": 8,  # H
    "base_salary": 19,     # S 기본급
    "base_deduction": 20,  # T 기본공제
    "ot_pay": 22,          # V O/T수당
    "night_pay": 23,       # W 심야수당
    "special_pay": 24,     # X 특근수당
    "special_ext_pay": 25, # Y 특근연장
    "position_pay": 26,    # Z 직책수당
    "shift_pay": 27,       # AA 교대수당
    "subtotal": 28,        # AB 소계
    "annual_pay": 31,      # AE (업무추진비 등 — 소계 포함, 미사용)
    "transport": 47,       # AU 교통비
    "health": 35,          # AI 건강보험
    "long_term_care": 36,  # AJ 장기요양
    "pension": 37,         # AK 국민연금
    "employment": 39,      # AM 고용보험
}


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _header_matches_early_leave(header: str) -> bool:
    h = header.replace(" ", "").replace("\n", "")
    if not h:
        return False
    if "지조외" in h:
        return True
    if h in ("조퇴", "조퇴시간", "조퇴누계", "조퇴합계"):
        return True
    if "조퇴" in h and "공제" not in h:
        return True
    return False


def _header_matches_name(header: str) -> bool:
    h = header.replace(" ", "").strip()
    return h in ("성명", "이름", "사원명", "성명(한글)", "근로자명")


def find_billing_worksheet(wb: Workbook, period_hint: str | None = None) -> Worksheet:
    """
    도급비 청구내역 시트 선택.

    통합 청구서(청구내역·연차·근태 다수 시트)에서 active가 연차 시트인 경우가 있어
    이름·기간 힌트로 청구 시트를 고릅니다.
    """
    from invoice_leave_sheet import infer_period_from_workbook as _infer_period

    hint = period_hint or _infer_period(wb)
    scored: list[tuple[int, str]] = []

    for name in wb.sheetnames:
        compact = name.replace(" ", "")
        lower = name.lower()
        if any(
            skip in compact
            for skip in ("연차", "근태", "Summary", "analysis", "Outsourcing", "작업", "work")
        ):
            continue
        if "청구" not in compact:
            continue
        score = 0
        if "내역" in compact:
            score += 10
        if hint and _PERIOD_IN_NAME_RE.search(name):
            try:
                y, m = hint.split("-")
                yy = int(y)
                mm = int(m)
                if f"{yy % 100:02d}" in compact and (f"{mm:02d}" in compact or f"{mm}월" in name):
                    score += 25
                if f"{yy}년" in name and f"{mm}월" in name:
                    score += 25
            except ValueError:
                pass
        if score > 0 or "내역" in compact:
            scored.append((score, name))

    if scored:
        scored.sort(key=lambda x: (-x[0], x[1]))
        return wb[scored[0][1]]

    for name in wb.sheetnames:
        compact = name.replace(" ", "")
        if "연차" in compact or "근태" in compact:
            continue
        if _sheet_has_billing_headers(wb[name]):
            return wb[name]

    return wb.active


_PERIOD_IN_NAME_RE = re.compile(r"(20\d{2}|26|25|24)\D{0,3}(\d{1,2})")


def _sheet_has_billing_headers(ws: Worksheet) -> bool:
    for r in range(1, min(10, ws.max_row + 1)):
        for c in range(1, min(30, ws.max_column + 1)):
            raw = ws.cell(r, c).value
            if raw is None:
                continue
            if _header_matches_name(str(raw).strip()):
                return True
    return False


def find_attendance_worksheet(wb: Workbook) -> Worksheet | None:
    """도급비 청구서 2번째 시트(근태) 또는 이름에 '근태' 포함 시트."""
    for name in wb.sheetnames:
        if "근태" in name.replace(" ", ""):
            return wb[name]
    if len(wb.sheetnames) >= 2:
        second = wb[wb.sheetnames[1]]
        first = wb[wb.sheetnames[0]]
        if second.title != first.title:
            return second
    return None


def _scan_attendance_columns(ws: Worksheet) -> tuple[int, int, int] | None:
    """헤더 행, 성명 열, 지조외(조퇴시간) 열."""
    name_col = early_col = None
    header_row = 1
    for r in range(1, min(12, ws.max_row + 1)):
        for c in range(1, ws.max_column + 1):
            raw = ws.cell(r, c).value
            if raw is None:
                continue
            text = str(raw).strip()
            if _header_matches_name(text):
                name_col = c
                header_row = r
            if _header_matches_early_leave(text):
                early_col = c
                header_row = r
        if name_col and early_col:
            return header_row, name_col, early_col
    return None


def load_attendance_early_leave_hours(
    wb: Workbook,
) -> tuple[dict[str, float], dict[str, str]]:
    """
    근태 시트에서 성명별 지조외(조퇴시간)를 읽습니다.

    Returns:
        ({정규화된 성명 키: 조퇴시간}, {정규화된 성명 키: 표시 이름})
    """
    ws = find_attendance_worksheet(wb)
    if ws is None:
        return {}, {}

    scanned = _scan_attendance_columns(ws)
    if not scanned:
        return {}, {}

    header_row, name_col, early_col = scanned
    hours_by_key: dict[str, float] = {}
    display_by_key: dict[str, str] = {}
    for row in range(header_row + 1, ws.max_row + 1):
        name = _cell_str(ws.cell(row, name_col).value)
        if not _is_valid_name(name):
            continue
        hours = safe_number(ws.cell(row, early_col).value, 0.0)
        if hours < 0:
            hours = 0.0
        key = norm_name_key(name)
        if key:
            hours_by_key[key] = hours
            display_by_key[key] = name
    return hours_by_key, display_by_key


def _resolve_attendance_hours(
    name_key: str,
    attendance_early: dict[str, float],
) -> tuple[float, str | None]:
    """
    근태 조퇴시간 조회. 정확히 일치하지 않으면 1글자 유사 이름으로 매칭.

    Returns:
        (조퇴시간, 유사매칭된 근태 키 또는 None)
    """
    if name_key in attendance_early:
        return attendance_early[name_key], None
    fuzzy_key = find_fuzzy_name_key(name_key, attendance_early.keys())
    if fuzzy_key:
        return attendance_early[fuzzy_key], fuzzy_key
    return 0.0, None


def attendance_name_warnings(
    invoice_path: Path,
    invoice_rows: list[dict[str, Any]],
) -> list[str]:
    """근태 시트 성명이 청구서와 어긋난 경우(오타·미등록) 경고."""
    wb = openpyxl.load_workbook(invoice_path, data_only=True)
    attendance_early, attendance_display = load_attendance_early_leave_hours(wb)
    wb.close()

    if not attendance_early:
        return []

    invoice_by_key: dict[str, str] = {}
    for row in invoice_rows:
        key = norm_name_key(row.get("name"))
        if key:
            invoice_by_key[key] = str(row["name"]).strip()

    invoice_keys = set(invoice_by_key.keys())
    warnings: list[str] = []
    seen: set[str] = set()

    for att_key, hours in attendance_early.items():
        if att_key in invoice_keys:
            continue

        att_name = attendance_display.get(att_key, att_key)
        fuzzy_inv = find_fuzzy_name_key(att_key, invoice_keys)
        if fuzzy_inv:
            inv_name = invoice_by_key[fuzzy_inv]
            msg = (
                f"근태 시트 '{att_name}' ↔ 청구서 '{inv_name}' 이름이 1글자 다릅니다(오타 가능). "
                f"근태 시트 성명을 '{inv_name}'으로 수정하세요."
            )
            if msg not in seen:
                seen.add(msg)
                warnings.append(msg)
            continue

        if hours > 0:
            msg = f"근태 시트 '{att_name}' 가 청구서에 없어 조퇴시간({hours}h)이 반영되지 않습니다."
            if msg not in seen:
                seen.add(msg)
                warnings.append(msg)

    return warnings


def _is_valid_name(name: str) -> bool:
    """합계·빈 행 등 비직원 이름을 걸러냅니다."""
    if not name or name in ("0", "합계", "소계", "계"):
        return False
    if name.replace(".", "").isdigit():
        return False
    return True


def extract_invoice_data(invoice_path: Path) -> list[dict[str, Any]]:
    """청구서에서 직원별 급여·근태·공제 데이터를 추출합니다."""
    from invoice_leave_sheet import apply_leave_sheet_to_invoice_rows, load_invoice_leave_sheet

    from invoice_leave_sheet import infer_period_from_workbook

    wb = openpyxl.load_workbook(invoice_path, data_only=True)
    period_hint = infer_period_from_workbook(wb)
    ws = find_billing_worksheet(wb, period_hint)
    attendance_early, _attendance_display = load_attendance_early_leave_hours(wb)
    leave_by_key, _leave_period = load_invoice_leave_sheet(wb)
    workers_day_col = find_workers_day_column(ws)
    rows: list[dict[str, Any]] = []

    for row in range(DATA_START_ROW, ws.max_row + 1):
        name = _cell_str(ws.cell(row, COL["name"]).value)
        if not _is_valid_name(name):
            continue

        subtotal = safe_number(ws.cell(row, COL["subtotal"]).value)
        if subtotal <= 0:
            continue
        transport = safe_number(ws.cell(row, COL["transport"]).value)
        # 업무추진비(AE 등)는 소계(AB)에 포함 — 별도 가산하지 않음
        gross = subtotal + transport

        health = int(safe_number(ws.cell(row, COL["health"]).value))
        ltc = int(safe_number(ws.cell(row, COL["long_term_care"]).value))
        pension = int(safe_number(ws.cell(row, COL["pension"]).value))
        employment = int(safe_number(ws.cell(row, COL["employment"]).value))
        insurance_total = health + ltc + pension + employment

        name_key = norm_name_key(name)
        early_leave_hours, _fuzzy_att_key = _resolve_attendance_hours(name_key, attendance_early)
        if early_leave_hours == 0.0 and name_key not in attendance_early:
            early_leave_hours = safe_number(ws.cell(row, COL["early_leave"]).value)

        workers_day_pay = 0
        if workers_day_col:
            workers_day_pay = int(safe_number(ws.cell(row, workers_day_col).value))

        rows.append({
            "row": row,
            "name": name,
            "dept": _cell_str(ws.cell(row, COL["dept"]).value),
            "hire_date": _cell_str(ws.cell(row, COL["hire"]).value),
            "base_hourly": safe_number(ws.cell(row, COL["base_hourly"]).value),
            "ordinary_hourly": safe_number(ws.cell(row, COL["ordinary_hourly"]).value),
            "base_days": safe_number(ws.cell(row, COL["base_days"]).value),
            "work_days": safe_number(ws.cell(row, COL["work_days"]).value),
            "unpaid_days": safe_number(ws.cell(row, COL["unpaid"]).value),
            "leave_days": safe_number(ws.cell(row, COL["leave"]).value),
            "ot_hours": safe_number(ws.cell(row, COL["ot_hours"]).value),
            "shift_hours": safe_number(ws.cell(row, COL["shift_hours"]).value),
            "night_hours": safe_number(ws.cell(row, COL["night_hours"]).value),
            "special_hours": safe_number(ws.cell(row, COL["special_hours"]).value),
            "special_ext_hours": safe_number(ws.cell(row, COL["special_ext_hours"]).value),
            "early_leave_hours": early_leave_hours,
            "base_salary": int(safe_number(ws.cell(row, COL["base_salary"]).value)),
            "base_deduction": int(safe_number(ws.cell(row, COL["base_deduction"]).value)),
            "ot_pay": int(safe_number(ws.cell(row, COL["ot_pay"]).value)),
            "night_pay": int(safe_number(ws.cell(row, COL["night_pay"]).value)),
            "special_pay": int(safe_number(ws.cell(row, COL["special_pay"]).value)),
            "special_ext_pay": int(safe_number(ws.cell(row, COL["special_ext_pay"]).value)),
            "position_pay": int(safe_number(ws.cell(row, COL["position_pay"]).value)),
            "shift_pay": int(safe_number(ws.cell(row, COL["shift_pay"]).value)),
            "workers_day_pay": workers_day_pay,
            "annual_pay": 0,
            "transport": int(transport),
            "subtotal": int(subtotal),
            "gross_pay": int(gross),
            "health_insurance": health,
            "long_term_care": ltc,
            "national_pension": pension,
            "employment_insurance": employment,
            "insurance_total": insurance_total,
        })

    apply_leave_sheet_to_invoice_rows(rows, leave_by_key, prefer_sheet=True)
    wb.close()
    return rows
