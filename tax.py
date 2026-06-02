"""
근로소득세·지방소득세 계산 모듈.

직원 마스터에 소득세가 있으면 우선 사용하고,
없으면 간이세액표(월급여 구간별)로 추정합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from utils import round_won, safe_number

# 간이 월급여 구간별 근로소득세 (2024 간이세액표 단순화 버전, 부양가족 1인 기준)
# 실무에서는 국세청 간이세액표 Excel/PDF를 매년 갱신해야 합니다.
SIMPLIFIED_TAX_TABLE = [
    (1_060_000, 0),
    (1_500_000, 8_000),
    (2_000_000, 42_000),
    (2_500_000, 120_000),
    (3_000_000, 210_000),
    (3_500_000, 310_000),
    (4_000_000, 420_000),
    (5_000_000, 650_000),
    (6_000_000, 920_000),
    (8_000_000, 1_450_000),
    (10_000_000, 2_100_000),
    (float("inf"), 0),  # 상한 초과 시 별도 계산
]


@dataclass
class TaxResult:
    """소득세 계산 결과."""

    income_tax: int
    local_income_tax: int
    total: int
    method: str  # "PRESET" | "SIMPLIFIED_TABLE" | "ESTIMATE"


def lookup_simplified_tax(monthly_taxable: float) -> int:
    """
    간이세액표 구간에서 해당 월급여에 맞는 소득세를 찾습니다.

    표는 부양가족 1명 기준 단순화본입니다.
    """
    amount = safe_number(monthly_taxable)
    for upper_bound, tax in SIMPLIFIED_TAX_TABLE:
        if amount <= upper_bound:
            if tax == 0 and upper_bound == float("inf"):
                # 1000만원 초과: (과세급여 - 150만) × 3% 단순 추정
                return round_won(max(0, (amount - 1_500_000) * 0.03))
            return tax
    return 0


def calculate_tax(
    taxable_pay: float,
    preset_income_tax: Optional[float] = None,
) -> TaxResult:
    """
    근로소득세와 지방소득세(소득세의 10%)를 계산합니다.

    Parameters
    ----------
    taxable_pay : float
        과세 대상 급여
    preset_income_tax : float, optional
        직원정보.xlsx에 입력된 월 소득세 (원천징수 확정액)
    """
    if preset_income_tax is not None and preset_income_tax > 0:
        income_tax = round_won(preset_income_tax)
        method = "PRESET"
    else:
        income_tax = lookup_simplified_tax(taxable_pay)
        method = "SIMPLIFIED_TABLE"

    local_tax = round_won(income_tax * 0.10)
    return TaxResult(
        income_tax=income_tax,
        local_income_tax=local_tax,
        total=income_tax + local_tax,
        method=method,
    )


def calculate_tax_deductions(
    salary_result: dict,
    employee_master: dict | None = None,
) -> dict:
    """
    calculator + insurance 결과에 소득세·지방소득세·실수령액을 반영합니다.
    """
    master = employee_master or {}
    gross = safe_number(salary_result.get("총지급액"))

    insurance_total = (
        safe_number(salary_result.get("국민연금"))
        + safe_number(salary_result.get("건강보험"))
        + safe_number(salary_result.get("장기요양보험"))
        + safe_number(salary_result.get("고용보험"))
    )

    preset_tax = salary_result.get("preset_income_tax")
    if preset_tax is None:
        preset_tax = master.get("소득세")

    taxable = gross - insurance_total
    tax = calculate_tax(taxable, preset_income_tax=preset_tax)

    total_deduction = insurance_total + tax.total
    net_pay = gross - total_deduction

    salary_result["소득세"] = tax.income_tax
    salary_result["지방소득세"] = tax.local_income_tax
    salary_result["공제합계"] = round(total_deduction)
    salary_result["실수령액"] = round(net_pay)
    return salary_result
