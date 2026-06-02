"""
4대보험(국민연금·건강·장기요양·고용) 계산 모듈.

직원 마스터에 금액이 있으면 그 값을 우선 사용하고,
없으면 과세급여 기준 요율로 자동 계산합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from utils import calc_employment_insurance, round_won, safe_number

# 2024~2026년 기준 근로자 부담 요율 (실무에서는 매년 국세청/4대보험 공고 확인)
NATIONAL_PENSION_RATE = 0.045       # 국민연금 4.5% (전체 9%의 절반)
HEALTH_INSURANCE_RATE = 0.03545     # 건강보험 3.545%
LONG_TERM_CARE_RATIO = 0.1295       # 장기요양 = 건강보험료 × 12.95%
# 고용보험 근로자 부담 실업급여 보험료 요율 (보수총액 × 0.9%, 10원 단위 반올림)
EMPLOYMENT_INSURANCE_WORKER_RATE = 0.009

# 만 65세 이상: 국민연금·건강·장기요양·고용보험 근로자 부담 면제 (급여 해당 월 말일 기준)
INSURANCE_EXEMPT_AGE_YEARS = 65

# 국민연금 기준소득월액 상·하한 (2024 기준, 원)
PENSION_FLOOR = 390_000
PENSION_CEILING = 6_170_000


@dataclass
class InsuranceResult:
    """4대보험 계산 결과를 담는 데이터 클래스."""

    national_pension: int
    health_insurance: int
    long_term_care: int
    employment_insurance: int
    total: int


def clamp(value: float, low: float, high: float) -> float:
    """값을 최소~최대 범위 안으로 제한합니다."""
    return max(low, min(high, value))


def is_insurance_exempt(identity: Any, *, as_of: date | None = None) -> bool:
    """
    만 65세 이상 여부 — 4대보험 근로자 부담 면제 대상.

    주민등록번호(또는 생년월일)와 기준일(급여월 말일)로 판단합니다.
    """
    from utils import age_years_at, parse_birth_date_from_korean_rrn

    birth = parse_birth_date_from_korean_rrn(identity, as_of=as_of)
    if birth is None:
        return False
    return age_years_at(birth, as_of) >= INSURANCE_EXEMPT_AGE_YEARS


def calculate_insurance(
    taxable_pay: float,
    preset_national_pension: Optional[float] = None,
    preset_health: Optional[float] = None,
    *,
    insurance_exempt: bool = False,
) -> InsuranceResult:
    """
    과세급여(taxable_pay)를 기준으로 4대보험을 산출합니다.

    Parameters
    ----------
    taxable_pay : float
        과세 대상 총지급액 (비과세 식대 등 제외 후)
    preset_national_pension : float, optional
        직원정보.xlsx에 미리 입력된 국민연금 공제액 (있으면 우선)
    preset_health : float, optional
        직원정보.xlsx에 미리 입력된 건강보험 공제액 (있으면 우선)

    Returns
    -------
    InsuranceResult
        각 보험료와 합계
    """
    taxable = safe_number(taxable_pay)

    if insurance_exempt:
        return InsuranceResult(0, 0, 0, 0, 0)

    # 국민연금: 기준소득월액 구간 적용 후 4.5%
    if preset_national_pension is not None and preset_national_pension > 0:
        pension = round_won(preset_national_pension)
    else:
        pension_base = clamp(taxable, PENSION_FLOOR, PENSION_CEILING)
        pension = round_won(pension_base * NATIONAL_PENSION_RATE)

    # 건강보험
    if preset_health is not None and preset_health > 0:
        health = round_won(preset_health)
    else:
        health = round_won(taxable * HEALTH_INSURANCE_RATE)

    # 장기요양: 건강보험료의 일정 비율
    ltc = round_won(health * LONG_TERM_CARE_RATIO)

    # 고용보험: 10원 미만 절사 규칙
    employment = calc_employment_insurance(taxable)

    total = pension + health + ltc + employment
    return InsuranceResult(
        national_pension=pension,
        health_insurance=health,
        long_term_care=ltc,
        employment_insurance=employment,
        total=total,
    )


def calculate_insurance_deductions(
    salary_result: dict,
    employee_master: dict | None = None,
) -> dict:
    """
    calculator 결과 dict에 4대보험 공제를 반영합니다.

    excel_writer / main 파이프라인에서 호출하는 어댑터 함수입니다.
    """
    master = employee_master or {}
    gross = safe_number(salary_result.get("총지급액"))

    identity = master.get("주민번호") or salary_result.get("birth")
    exempt = is_insurance_exempt(identity)

    preset_pension = salary_result.get("preset_national_pension")
    if preset_pension is None:
        preset_pension = master.get("국민연금")
    preset_health = salary_result.get("preset_health")
    if preset_health is None:
        preset_health = master.get("건강보험")

    ins = calculate_insurance(
        gross,
        preset_national_pension=preset_pension,
        preset_health=preset_health,
        insurance_exempt=exempt,
    )

    salary_result["국민연금"] = ins.national_pension
    salary_result["건강보험"] = ins.health_insurance
    salary_result["장기요양보험"] = ins.long_term_care
    salary_result["고용보험"] = ins.employment_insurance
    return salary_result
