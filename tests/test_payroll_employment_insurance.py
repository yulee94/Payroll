"""고용보험·만65세 4대보험 면제·급여대장 수식."""

from __future__ import annotations

from datetime import date

from core.payroll_calc_rules import (
    PAYROLL_OUTPUT_ENGINE_VERSION,
    resolve_social_insurance,
    sync_employment_insurance_from_gross,
)
from insurance import is_insurance_exempt
from utils import calc_employment_insurance


def test_sync_employment_from_gross():
    inv = {
        "gross_pay": 4_640_000,
        "health_insurance": 100_000,
        "long_term_care": 10_000,
        "national_pension": 200_000,
        "employment_insurance": 999,
        "insurance_total": 999_999,
    }
    sync_employment_insurance_from_gross(inv)
    expected = calc_employment_insurance(4_640_000)
    assert inv["employment_insurance"] == expected
    assert inv["insurance_total"] == 100_000 + 10_000 + 200_000 + expected


def test_insurance_exempt_age_65():
    # 1950-06-15 → 2026-05-31 기준 만 75세
    assert is_insurance_exempt("500615-1", as_of=date(2026, 5, 31))
    # 1965-06-01 → 2026-05-31 기준 만 60세 (미만 65)
    assert not is_insurance_exempt("650601-1", as_of=date(2026, 5, 31))
    # 1960-05-01 → 2026-05-31 기준 만 66세
    assert is_insurance_exempt("600501-1", as_of=date(2026, 5, 31))


def test_resolve_social_insurance_exempt_zeros():
    inv = {
        "gross_pay": 3_000_000,
        "health_insurance": 150_000,
        "long_term_care": 19_000,
        "national_pension": 200_000,
        "employment_insurance": 27_000,
        "insurance_total": 396_000,
    }
    exempt = resolve_social_insurance(
        inv,
        identity="500615-1",
        payroll_period="2026-05",
    )
    assert exempt is True
    assert inv["insurance_total"] == 0
    assert inv["employment_insurance"] == 0


def test_ledger_formula_helpers():
    from excel_writer import (
        _ledger_employment_insurance_formula,
        _ledger_net_pay_formula,
    )

    assert "0.009" in _ledger_employment_insurance_formula(5)
    assert _ledger_net_pay_formula(5) == '=IF(S6="",0,MAX(0,S6-W5))'


def test_engine_version_defined():
    assert PAYROLL_OUTPUT_ENGINE_VERSION == "4"
