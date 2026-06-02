"""

core/payroll_calc_rules.py - 급여 산출·Excel 출력 기준 (요율·버전)



요율 변경 시 PAYROLL_OUTPUT_ENGINE_VERSION 을 올리면

저장된 청구서 기준으로 급여대장·명세서·지급내역이 자동 재생성됩니다.

"""



from __future__ import annotations



from typing import Any



from annual_leave_accrual import period_end_date

from insurance import EMPLOYMENT_INSURANCE_WORKER_RATE, is_insurance_exempt

from utils import calc_employment_insurance, round_won, safe_number



# 산출 엔진/Excel 수식 기준 버전 (변경 시 기존 output 자동 갱신 대상)

# v3: 만 65세 이상 국민·건강·장기요양 면제 (급여월 말일 기준)
# v4: 만 65세 이상 고용보험 — KCOMWEL 부과고지보험료 확인 후 공제 여부 결정
# v5: 사대보험 EDI 조회 보험료(use_edi_premiums) 급여 반영
PAYROLL_OUTPUT_ENGINE_VERSION = "5"





def sync_employment_insurance_from_gross(inv: dict[str, Any]) -> int:

    """청구서/명부 반영 후 총지급액 기준으로 고용보험·4대보험 합계를 맞춥니다."""

    if inv.get("insurance_exempt") and not inv.get("ei_65_liable"):

        inv["employment_insurance"] = 0

        inv["insurance_total"] = (

            int(safe_number(inv.get("health_insurance"), 0))

            + int(safe_number(inv.get("long_term_care"), 0))

            + int(safe_number(inv.get("national_pension"), 0))

        )

        return 0



    gross = int(safe_number(inv.get("gross_pay"), 0.0))

    employment = calc_employment_insurance(gross)

    inv["employment_insurance"] = employment

    inv["insurance_total"] = (

        int(safe_number(inv.get("health_insurance"), 0))

        + int(safe_number(inv.get("long_term_care"), 0))

        + int(safe_number(inv.get("national_pension"), 0))

        + employment

    )

    return employment





def resolve_social_insurance(

    inv: dict[str, Any],

    *,

    identity: Any,

    payroll_period: str,

    emp_roster: dict[str, Any] | None = None,

    tenant_id: str | None = None,

) -> bool:

    """

    국민·건강·장기·고용보험 산출.



    만 65세 이상(해당 급여월 말일): 국민·건강·장기요양 면제.

    고용보험은 KCOMWEL 부과고지보험료 확인 결과에 따라 공제 여부 결정.

    Returns True if pension/health/ltc exempt (age 65+).

    """

    from core.payroll.employment_insurance_65 import resolve_ei_65_for_payroll

    as_of = period_end_date(payroll_period)

    age_65_plus = is_insurance_exempt(identity, as_of=as_of)

    inv["insurance_exempt"] = age_65_plus

    inv.pop("ei_65_liable", None)

    inv.pop("ei_65_status", None)

    inv.pop("ei_65_premium", None)

    inv.pop("ei_65_management_no", None)

    inv.pop("ei_65_warning", None)



    if age_65_plus:

        inv["national_pension"] = 0

        inv["health_insurance"] = 0

        inv["long_term_care"] = 0

        ei_result = resolve_ei_65_for_payroll(

            identity=identity,

            payroll_period=payroll_period,

            employee_id=str((emp_roster or {}).get("사번") or ""),

            employee_name=str(inv.get("name") or (emp_roster or {}).get("성명") or ""),

            workplace=str((emp_roster or {}).get("근무지") or inv.get("workplace") or ""),

            tenant_id=tenant_id,

        )

        inv["ei_65_status"] = ei_result.status

        inv["ei_65_premium"] = ei_result.premium_amount

        inv["ei_65_management_no"] = ei_result.management_no

        if ei_result.warning:

            inv["ei_65_warning"] = ei_result.warning

        if ei_result.deduct_employment_insurance:

            inv["ei_65_liable"] = True

            sync_employment_insurance_from_gross(inv)

        else:

            inv["employment_insurance"] = 0

            inv["insurance_total"] = 0

        _apply_edi_if_enabled(

            inv,

            payroll_period=payroll_period,

            emp_roster=emp_roster,

            tenant_id=tenant_id,

        )

        return True



    if emp_roster:

        national_pension_master = safe_number(emp_roster.get("국민연금"), 0.0)

        health_insurance_master = safe_number(emp_roster.get("건강보험"), 0.0)

        ltc_master = safe_number(emp_roster.get("장기요양"), 0.0)

        ei_master = safe_number(emp_roster.get("고용보험"), 0.0)

        if national_pension_master > 0:

            inv["national_pension"] = int(national_pension_master)

        if health_insurance_master > 0:

            inv["health_insurance"] = int(health_insurance_master)

            if ltc_master > 0:

                inv["long_term_care"] = int(ltc_master)

            else:

                inv["long_term_care"] = round_won(inv["health_insurance"] * 0.1295)

        elif ltc_master > 0:

            inv["long_term_care"] = int(ltc_master)

        if ei_master > 0:

            inv["employment_insurance"] = int(ei_master)

            inv["insurance_total"] = (

                int(safe_number(inv.get("health_insurance"), 0))

                + int(safe_number(inv.get("long_term_care"), 0))

                + int(safe_number(inv.get("national_pension"), 0))

                + int(ei_master)

            )

            _apply_edi_if_enabled(

                inv,

                payroll_period=payroll_period,

                emp_roster=emp_roster,

                tenant_id=tenant_id,

            )

            return False



    sync_employment_insurance_from_gross(inv)

    _apply_edi_if_enabled(

        inv,

        payroll_period=payroll_period,

        emp_roster=emp_roster,

        tenant_id=tenant_id,

    )

    return False





def _apply_edi_if_enabled(

    inv: dict[str, Any],

    *,

    payroll_period: str,

    emp_roster: dict[str, Any] | None,

    tenant_id: str | None,

) -> None:

    from core.payroll.edi_insurance import apply_edi_premiums_to_inv

    result = apply_edi_premiums_to_inv(

        inv,

        payroll_period=payroll_period,

        emp_roster=emp_roster,

        tenant_id=tenant_id,

        respect_age_exempt=True,

    )

    if result.applied and inv.get("insurance_exempt") and not inv.get("ei_65_liable"):

        inv["employment_insurance"] = 0

        inv["insurance_total"] = 0





def employment_insurance_rate_label() -> str:

    return f"{EMPLOYMENT_INSURANCE_WORKER_RATE * 100:.2f}%".rstrip("0").rstrip(".")


