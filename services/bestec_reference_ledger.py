"""
services/bestec_reference_ledger.py - ㈜베스텍 밀양 급여대장 .xls 참조 파싱·비교
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import xlrd

from roster_constants import norm_name_key
from utils import safe_number

# 시트명: 2026.01월 …
SHEET_BY_PERIOD = {
    "2026-01": "2026.01월",
    "2026-02": "2026.02월",
    "2026-03": "2026.03월",
    "2026-04": "2026.04월",
}


@dataclass
class BestecLedgerEmployee:
    name: str
    title: str = ""
    dept: str = ""
    hire_date: Any = ""
    base_hourly: float = 0.0
    work_hours: float = 0.0
    weekly_hours: float = 0.0
    mgmt_allowance: float = 0.0
    car_allowance: float = 0.0
    ot_hours: float = 0.0
    night_hours: float = 0.0
    special_hours: float = 0.0
    special_night_hours: float = 0.0
    special_ext_hours: float = 0.0
    early_leave_hours: float = 0.0
    daily_wage: float = 0.0
    ordinary_hourly: float = 0.0
    base_salary: float = 0.0
    weekly_pay: float = 0.0
    tech_allowance: float = 0.0
    meal: float = 0.0
    ot_pay: float = 0.0
    night_pay: float = 0.0
    special_pay: float = 0.0
    special_night_pay: float = 0.0
    special_ext_pay: float = 0.0
    early_leave_ded: float = 0.0
    incentive: float = 0.0
    transport: float = 0.0
    gross: float = 0.0
    income_tax: float = 0.0
    local_tax: float = 0.0
    health: float = 0.0
    pension: float = 0.0
    long_term_care: float = 0.0
    employment: float = 0.0
    year_end_adj: float = 0.0
    other_ded: float = 0.0
    deduction_total: float = 0.0
    net: float = 0.0
    preset_income_tax_seq: float = 0.0
    seq_health_insurance: float = 0.0
    seq_national_pension: float = 0.0
    seq_long_term_care: float = 0.0
    seq_employment: float = 0.0


def _num(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _sheet_for_period(wb: xlrd.book.Book, period: str) -> xlrd.sheet.Sheet:
    name = SHEET_BY_PERIOD.get(period)
    if name and name in wb.sheet_names():
        return wb.sheet_by_name(name)
    for s in wb.sheet_names():
        if period.replace("-", ".") in s or period[2:] in s:
            return wb.sheet_by_name(s)
    raise ValueError(f"시트 없음: {period} in {wb.sheet_names()[:8]}…")


def load_reference_ledger(path: Path, period: str) -> dict[str, BestecLedgerEmployee]:
    wb = xlrd.open_workbook(str(path))
    ws = _sheet_for_period(wb, period)
    out: dict[str, BestecLedgerEmployee] = {}

    r = 6
    while r < ws.nrows:
        seq = ws.cell_value(r, 0)
        name = ws.cell_value(r, 1)
        if not (isinstance(seq, (int, float)) and seq == int(seq) and name):
            r += 1
            continue
        name_s = str(name).strip()
        if not name_s or name_s in ("합계", "소계"):
            r += 2
            continue
        d = r + 1
        if d >= ws.nrows:
            break
        emp = BestecLedgerEmployee(
            name=name_s,
            title=str(ws.cell_value(d, 1) or "").strip(),
            dept=str(ws.cell_value(r, 4) or "").strip(),
            hire_date=ws.cell_value(r, 3),
            base_hourly=_num(ws.cell_value(r, 5)),
            work_hours=_num(ws.cell_value(r, 6)),
            weekly_hours=_num(ws.cell_value(r, 7)),
            mgmt_allowance=_num(ws.cell_value(r, 8)),
            car_allowance=_num(ws.cell_value(r, 9)),
            ot_hours=_num(ws.cell_value(r, 10)),
            night_hours=_num(ws.cell_value(r, 11)),
            special_hours=_num(ws.cell_value(r, 12)),
            special_night_hours=_num(ws.cell_value(r, 13)),
            special_ext_hours=_num(ws.cell_value(r, 14)),
            early_leave_hours=_num(ws.cell_value(r, 15)),
            preset_income_tax_seq=_num(ws.cell_value(r, 19)),
            seq_health_insurance=_num(ws.cell_value(r, 20)),
            seq_national_pension=_num(ws.cell_value(r, 21)),
            daily_wage=_num(ws.cell_value(d, 4)),
            ordinary_hourly=_num(ws.cell_value(d, 5)),
            base_salary=_num(ws.cell_value(d, 6)),
            weekly_pay=_num(ws.cell_value(d, 7)),
            tech_allowance=_num(ws.cell_value(d, 8)),
            meal=_num(ws.cell_value(d, 9)),
            ot_pay=_num(ws.cell_value(d, 10)),
            night_pay=_num(ws.cell_value(d, 11)),
            special_pay=_num(ws.cell_value(d, 12)),
            special_night_pay=_num(ws.cell_value(d, 13)),
            special_ext_pay=_num(ws.cell_value(d, 14)),
            early_leave_ded=_num(ws.cell_value(d, 15)),
            incentive=_num(ws.cell_value(d, 16)),
            transport=_num(ws.cell_value(d, 17)),
            gross=_num(ws.cell_value(d, 18)),
            income_tax=_num(ws.cell_value(d, 19)),
            local_tax=_num(ws.cell_value(d, 19)),
            health=_num(ws.cell_value(r, 20)),
            pension=_num(ws.cell_value(r, 21)),
            employment=_num(ws.cell_value(d, 21)),
            year_end_adj=_num(ws.cell_value(d, 22)) if ws.ncols > 22 else 0.0,
            other_ded=_num(ws.cell_value(d, 23)) if ws.ncols > 23 else 0.0,
            deduction_total=_num(ws.cell_value(d, 23)) if ws.ncols > 23 else 0.0,
            net=_num(ws.cell_value(d, 24)) if ws.ncols > 24 else 0.0,
        )
        emp.gross = _num(ws.cell_value(d, 18))
        emp.local_tax = _num(ws.cell_value(d, 19))
        emp.seq_long_term_care = _num(ws.cell_value(d, 20))
        emp.long_term_care = emp.seq_long_term_care
        emp.seq_employment = _num(ws.cell_value(d, 21))
        emp.employment = emp.seq_employment
        emp.year_end_adj = _num(ws.cell_value(d, 22)) if ws.ncols > 22 else 0.0
        emp.other_ded = _num(ws.cell_value(d, 23)) if ws.ncols > 23 else 0.0
        emp.net = _num(ws.cell_value(d, 24)) if ws.ncols > 24 else 0.0
        emp.deduction_total = max(0.0, emp.gross - emp.net) if emp.net > 0 else 0.0
        out[norm_name_key(name_s)] = emp
        r += 2
    return out


def build_roster_from_reference(
    reference: dict[str, BestecLedgerEmployee],
) -> dict[str, dict[str, Any]]:
    return {k: reference_to_roster_row(v) for k, v in reference.items()}


def reference_to_roster_row(
    emp: BestecLedgerEmployee,
    *,
    seq_health: float = 0.0,
    seq_pension: float = 0.0,
) -> dict[str, Any]:
    """근로자명부 행."""
    fixed_allowance = emp.tech_allowance + emp.mgmt_allowance + emp.car_allowance
    row: dict[str, Any] = {
        "성명": emp.name,
        "직책": emp.title,
        "근무지": "밀양공장",
        "계열사": "㈜베스텍",
        "기본시급": emp.base_hourly if emp.base_hourly > 0 else 0,
        "통상시급": emp.ordinary_hourly if emp.ordinary_hourly > 0 else emp.base_hourly,
        "수당": fixed_allowance,
        "입사일": emp.hire_date,
    }
    health = seq_health if seq_health > 0 else emp.seq_health_insurance
    pension = seq_pension if seq_pension > 0 else emp.seq_national_pension
    if emp.preset_income_tax_seq > 0:
        row["소득세"] = int(emp.preset_income_tax_seq)
    if health > 0:
        row["건강보험"] = int(health)
    if pension > 0:
        row["국민연금"] = int(pension)
    if emp.seq_long_term_care > 0:
        row["장기요양"] = int(emp.seq_long_term_care)
    if emp.seq_employment > 0:
        row["고용보험"] = int(emp.seq_employment)
    if emp.local_tax > 0:
        row["지방소득세"] = int(emp.local_tax)
    exec_titles = ("회장", "부회장", "대표", "사장", "부사장", "전무", "상무", "이사")
    if any(k in (emp.title or "") for k in exec_titles):
        row["임원"] = "Y"
    return row


def reference_to_invoice_row(emp: BestecLedgerEmployee) -> dict[str, Any]:
    """payroll_builder 가 소비하는 invoice_row."""
    subtotal = (
        emp.base_salary
        + emp.weekly_pay
        + emp.tech_allowance
        + emp.meal
        + emp.ot_pay
        + emp.night_pay
        + emp.special_pay
        + emp.special_night_pay
        + emp.special_ext_pay
        + emp.early_leave_ded
        + emp.incentive
    )
    if subtotal <= 0 and emp.gross > 0:
        subtotal = max(0, emp.gross - emp.transport)
    gross = emp.gross if emp.gross > 0 else subtotal + emp.transport
    wh = emp.work_hours if emp.work_hours > 0 else 209.0
    return {
        "name": emp.name,
        "dept": emp.dept,
        "hire_date": emp.hire_date,
        "base_hourly": emp.base_hourly,
        "ordinary_hourly": emp.ordinary_hourly,
        "base_days": wh,
        "work_days": wh,
        "unpaid_days": 0,
        "leave_days": 0,
        "ot_hours": emp.ot_hours,
        "shift_hours": 0,
        "night_hours": emp.night_hours,
        "special_hours": emp.special_hours,
        "special_ext_hours": emp.special_ext_hours + emp.special_night_hours,
        "early_leave_hours": emp.early_leave_hours,
        "base_salary": int(emp.base_salary),
        "base_deduction": 0,
        "ot_pay": int(emp.ot_pay),
        "night_pay": int(emp.night_pay),
        "special_pay": int(emp.special_pay),
        "special_ext_pay": int(emp.special_ext_pay + emp.special_night_pay),
        "position_pay": int(emp.mgmt_allowance),
        "shift_pay": 0,
        "workers_day_pay": 0,
        "annual_pay": 0,
        "transport": int(emp.transport),
        "subtotal": int(subtotal),
        "gross_pay": int(gross),
        "health_insurance": int(emp.health),
        "long_term_care": 0,
        "national_pension": int(emp.pension),
        "employment_insurance": int(emp.employment),
        "insurance_total": int(emp.health + emp.pension + emp.employment),
        "_payroll_source": "bestec_reference",
    }


def compare_records(
    generated: list[dict[str, Any]],
    reference: dict[str, BestecLedgerEmployee],
    *,
    tolerance: int = 1,
) -> dict[str, Any]:
    """이름 기준 비교."""
    gen_by = {norm_name_key(r["name"]): r for r in generated}
    ref_keys = set(reference.keys())
    gen_keys = set(gen_by.keys())
    matched = ref_keys & gen_keys
    only_ref = sorted(ref_keys - gen_keys)
    only_gen = sorted(gen_keys - ref_keys)

    mismatches: list[dict[str, Any]] = []

    def diff_field(name: str, field: str, ref_v: float, gen_v: float, category: str) -> None:
        if abs(ref_v - gen_v) > tolerance:
            mismatches.append(
                {
                    "name": name,
                    "field": field,
                    "category": category,
                    "reference": ref_v,
                    "generated": gen_v,
                    "delta": gen_v - ref_v,
                }
            )

    for key in sorted(matched):
        ref = reference[key]
        gen = gen_by[key]
        name = ref.name
        diff_field(name, "gross_pay", ref.gross, safe_number(gen.get("gross_pay")), "gross")
        diff_field(
            name,
            "total_deduction",
            ref.deduction_total,
            safe_number(gen.get("total_deduction")),
            "deductions",
        )
        diff_field(name, "net_pay", ref.net, safe_number(gen.get("net_pay")), "net")
        ref_h = ref.work_hours if ref.work_hours > 0 else 209.0
        gen_h = safe_number(
            gen.get("_attendance_work_hours")
            or gen.get("_monthly_work_hours")
            or gen.get("work_days"),
            ref_h,
        )
        diff_field(name, "work_hours", ref_h, gen_h, "hours")

    match_ok = len(matched) - len({m["name"] for m in mismatches})
    return {
        "reference_count": len(ref_keys),
        "generated_count": len(gen_keys),
        "matched_names": len(matched),
        "only_in_reference": [reference[k].name for k in only_ref],
        "only_in_generated": [gen_by[k]["name"] for k in only_gen],
        "mismatches": mismatches,
        "match_rate": (
            round(100.0 * match_ok / len(matched), 1) if matched else 0.0
        ),
        "fully_matched_employees": match_ok,
    }
