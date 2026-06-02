"""
급여 계산 엔진 (실무형 ERP 급여 모듈 핵심).

기본급, 각종 수당(연장·야간·휴일·주휴·식대·교통비),
4대보험·세금 공제를 반영하여 총지급액·실수령액을 산출합니다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from insurance import calculate_insurance
from tax import calculate_tax
from utils import (
    MEAL_ALLOWANCE_PER_DAY,
    STANDARD_MONTHLY_HOURS,
    is_likely_hours,
    round_won,
    safe_number,
)

# 가산임금 배율 (통상시급 대비)
OVERTIME_PREMIUM = 1.5   # 연장근로
NIGHT_PREMIUM = 0.5      # 야간근로 (통상임금의 50% 가산)
HOLIDAY_PREMIUM = 1.5    # 휴일근로
OVERLAP_PREMIUM = 0.5    # 중복가산 (야간+연장 겹치는 시간)


def calc_ordinary_hourly(base_salary: float, fixed_allowance: float, preset: float) -> float:
    """
    통상시급을 계산합니다.

    우선순위: ① 청구서/마스터 preset ② (기본급+고정수당)÷209
    """
    if preset > 0:
        return preset
    total = base_salary + fixed_allowance
    if total <= 0:
        return 0.0
    return total / STANDARD_MONTHLY_HOURS


def calc_weekly_holiday_pay(
    ordinary_hourly: float,
    weekly_work_hours: float = 40.0,
) -> int:
    """
    주휴수당을 계산합니다.

    주 40시간 이상 근무 시: 1일(8시간)분 × 통상시급
    40시간 미만: (주간근로시간 / 40) × 8 × 통상시급 (비례)
    """
    if ordinary_hourly <= 0:
        return 0
    ratio = min(weekly_work_hours, 40.0) / 40.0
    hours = 8.0 * ratio
    return round_won(ordinary_hourly * hours)


def calc_overlap_premium(overtime_hours: float, night_hours: float, ordinary_hourly: float) -> int:
    """
    중복가산(야간+연장 동시 해당 시간)을 계산합니다.

    겹치는 시간 = min(연장시간, 야간시간)
    가산분 = 겹침시간 × 통상시급 × 0.5 (야간 0.5 + 연장 0.5 중복분)
    """
    overlap = min(max(overtime_hours, 0), max(night_hours, 0))
    return round_won(overlap * ordinary_hourly * OVERLAP_PREMIUM)


def calculate_salary(employee_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    한 직원의 급여를 전 항목 계산하여 구조화된 dict로 반환합니다.

    Parameters
    ----------
    employee_data : dict
        invoice_parser + employee_manager 병합 결과

    Returns
    -------
    dict
        earnings, deductions, gross_pay, net_pay 등 상세 내역
    """
    name = employee_data.get("name", "")
    emp_no = employee_data.get("emp_no", "")
    department = employee_data.get("department", "")

    base_salary = safe_number(employee_data.get("base_salary", 0))
    fixed_allowance = safe_number(employee_data.get("fixed_allowance", 0))
    preset_oh = safe_number(employee_data.get("ordinary_hourly", 0))
    ordinary_hourly = calc_ordinary_hourly(base_salary, fixed_allowance, preset_oh)

    # --- 시간·수당 ---
    ot_hours = safe_number(employee_data.get("overtime_hours", 0))
    night_hours = safe_number(employee_data.get("night_hours", 0))
    holiday_hours = safe_number(employee_data.get("holiday_hours", 0))

    # 금액이 직접 들어온 경우 재계산
    ot_amount = round_won(ot_hours * ordinary_hourly * OVERTIME_PREMIUM)
    if ot_amount <= 0:
        raw = safe_number(employee_data.get("overtime_amount_raw", 0))
        if raw > 0 and not is_likely_hours(raw, ordinary_hourly):
            ot_amount = round_won(raw)
            if ordinary_hourly > 0:
                ot_hours = raw / (ordinary_hourly * OVERTIME_PREMIUM)

    night_amount = round_won(night_hours * ordinary_hourly * NIGHT_PREMIUM)
    if night_amount <= 0:
        raw = safe_number(employee_data.get("night_amount_raw", 0))
        if raw > 0 and not is_likely_hours(raw, ordinary_hourly):
            night_amount = round_won(raw)

    holiday_amount = round_won(holiday_hours * ordinary_hourly * HOLIDAY_PREMIUM)
    if holiday_amount <= 0:
        raw = safe_number(employee_data.get("holiday_amount_raw", 0))
        if raw > 0 and not is_likely_hours(raw, ordinary_hourly):
            holiday_amount = round_won(raw)

    overlap_amount = calc_overlap_premium(ot_hours, night_hours, ordinary_hourly)

    meal_days = safe_number(employee_data.get("meal_days", 0))
    meal_allowance = round_won(meal_days * MEAL_ALLOWANCE_PER_DAY)

    transport = round_won(safe_number(employee_data.get("transport_allowance", 0)))
    other_pay = round_won(safe_number(employee_data.get("other_pay", 0)))
    additional_pay = round_won(safe_number(employee_data.get("additional_pay", 0)))

    # 주휴수당 (주 40h 기준, 근태시간 없으면 기본 40h 가정)
    weekly_hours = safe_number(employee_data.get("weekly_work_hours", 40))
    weekly_holiday_pay = calc_weekly_holiday_pay(ordinary_hourly, weekly_hours)

    # 기본급이 없고 시급만 있는 경우: 209h × 통상시급
    if base_salary <= 0 and ordinary_hourly > 0:
        base_salary = round_won(ordinary_hourly * STANDARD_MONTHLY_HOURS)

    earnings = {
        "base_salary": round_won(base_salary),
        "fixed_allowance": round_won(fixed_allowance),
        "overtime": ot_amount,
        "night": night_amount,
        "holiday": holiday_amount,
        "overlap_premium": overlap_amount,
        "weekly_holiday": weekly_holiday_pay,
        "meal": meal_allowance,
        "transport": transport,
        "other": other_pay,
        "additional": additional_pay,
    }

    gross_pay = sum(earnings.values())

    # 비과세: 식대(월 20만 이하) — 단순화하여 전액 비과세 처리
    non_taxable = min(meal_allowance, 200_000)
    taxable_pay = gross_pay - non_taxable

    # --- 공제 ---
    ins = calculate_insurance(
        taxable_pay,
        preset_national_pension=employee_data.get("preset_national_pension"),
        preset_health=employee_data.get("preset_health"),
    )
    tax = calculate_tax(taxable_pay, preset_income_tax=employee_data.get("preset_income_tax"))

    deductions = {
        "national_pension": ins.national_pension,
        "health_insurance": ins.health_insurance,
        "long_term_care": ins.long_term_care,
        "employment_insurance": ins.employment_insurance,
        "income_tax": tax.income_tax,
        "local_income_tax": tax.local_income_tax,
    }

    total_deductions = sum(deductions.values())
    net_pay = gross_pay - total_deductions

    return {
        "name": name,
        "emp_no": emp_no,
        "department": department,
        "account_no": employee_data.get("account_no", ""),
        "ordinary_hourly": round(ordinary_hourly, 2),
        "hours": {
            "overtime": ot_hours,
            "night": night_hours,
            "holiday": holiday_hours,
        },
        "earnings": earnings,
        "deductions": deductions,
        "gross_pay": gross_pay,
        "taxable_pay": round_won(taxable_pay),
        "non_taxable_pay": round_won(non_taxable),
        "total_deductions": total_deductions,
        "net_pay": net_pay,
        "tax_method": tax.method,
    }


def calculate_all(merged_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """여러 직원 데이터에 대해 calculate_salary를 일괄 실행합니다."""
    return [calculate_salary(row) for row in merged_rows]
