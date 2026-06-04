"""
payroll_api_contract.py - stable payroll automation API contract metadata.

The desktop app does not expose HTTP yet, but this contract gives a future
FastAPI/Flask wrapper, mobile bridge, or external payroll integrator one stable
request/response shape to implement against.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.payroll_scope import PayrollScope

PAYROLL_API_VERSION = "v1"
PAYROLL_API_ENDPOINT = "/api/payroll/v1/runs"
PAYROLL_API_VALIDATE_ENDPOINT = "/api/payroll/v1/runs/validate"
PAYROLL_API_HEALTH_ENDPOINT = "/api/payroll/v1/healthz"
PAYROLL_API_READINESS_ENDPOINT = "/api/payroll/v1/readiness"
PAYROLL_API_ENTRYPOINT = "services.payroll_api_adapter.run_payroll_api(payload)"
PAYROLL_API_VALIDATE_ENTRYPOINT = "services.payroll_api_adapter.validate_payroll_api_payload(payload)"
PAYROLL_API_INPUT_TYPES: tuple[str, ...] = ("auto", "invoice", "attendance", "mixed")


def payroll_operation_policy_example() -> dict[str, Any]:
    """Return the normalized operation policy shape emitted by Rust validation."""
    return {
        "input_basis": "hybrid",
        "payday": "25일",
        "show_setup_guide": True,
        "policy_note": "",
        "attendance": {
            "enabled": True,
            "source": "biometric",
            "rounding_minutes": 1,
            "late_grace_minutes": 0,
            "early_leave_grace_minutes": 0,
            "overtime_rounding_minutes": 1,
            "missing_clock_policy": "warn",
            "holiday_source": "invoice",
        },
    }


def payroll_api_request_example(*, input_type: str = "mixed") -> dict[str, Any]:
    """Return a JSON-serializable example payload accepted by run_payroll_api."""
    if input_type not in PAYROLL_API_INPUT_TYPES:
        raise ValueError(f"지원하지 않는 급여 입력 방식입니다: {input_type}")

    payload: dict[str, Any] = {
        "request_id": "payroll-run-2026-05-coss-site-a",
        "scope": {
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
        },
        "input_type": input_type,
        "tenant_id": "coss",
        "metadata": {
            "requested_by": "api",
            "source_system": "Bitween HTTP wrapper",
        },
    }
    if input_type in ("auto", "invoice", "mixed"):
        payload["invoice_path"] = "C:/Bitween/inbox/invoice_2026-05.xlsx"
    if input_type in ("attendance", "mixed"):
        payload["attendance_path"] = "C:/Bitween/inbox/attendance_2026-05.csv"
    return payload


def payroll_api_success_example() -> dict[str, Any]:
    """Return a representative successful response shape."""
    return {
        "ok": True,
        "status": "success",
        "will_run": True,
        "can_run": True,
        "request_id": "payroll-run-2026-05-coss-site-a",
        "scope": "COSS/Site A/2026-05",
        "scope_key": PayrollScope("COSS", "Site A", "2026-05").key,
        "affiliate": "COSS",
        "workplace": "Site A",
        "period": "2026-05",
        "input_type": "mixed",
        "count": 28,
        "warnings": [],
        "paths": {
            "ledger": "C:/Bitween/output/COSS/Site A/2026-05/급여대장.xlsx",
            "payslip": "C:/Bitween/output/COSS/Site A/2026-05/급여명세서.xlsx",
            "payment": "C:/Bitween/output/COSS/Site A/2026-05/지급내역.xlsx",
        },
        "payroll_audit": {},
        "roster": {"source": "templates", "updated_at": "2026-06-01 09:47"},
        "operation_policy": payroll_operation_policy_example(),
        "operation_policy_source": "tenant",
        "error_code": "",
        "details": {},
        "error": "",
    }


def payroll_api_error_example() -> dict[str, Any]:
    """Return a representative validation/error response shape."""
    return {
        "ok": False,
        "status": "error",
        "will_run": False,
        "can_run": False,
        "request_id": "payroll-run-2026-05-coss-site-a",
        "error_code": "invalid_period",
        "error": "period는 YYYY-MM 형식이어야 합니다.",
        "warnings": ["period는 YYYY-MM 형식이어야 합니다."],
        "details": {
            "period": "202605",
            "period_format": "YYYY-MM",
        },
    }


def payroll_api_run_error_example() -> dict[str, Any]:
    """Return the Rust-owned run-result error envelope shape."""
    return {
        "ok": False,
        "status": "error",
        "will_run": True,
        "can_run": False,
        "request_id": "payroll-run-2026-05-coss-site-a",
        "scope": "COSS/Site A/2026-05",
        "scope_key": PayrollScope("COSS", "Site A", "2026-05").key,
        "affiliate": "COSS",
        "workplace": "Site A",
        "period": "2026-05",
        "input_type": "mixed",
        "count": 0,
        "warnings": ["급여 처리 실패"],
        "paths": {},
        "payroll_audit": {},
        "roster": {},
        "operation_policy": payroll_operation_policy_example(),
        "operation_policy_source": "tenant",
        "error_code": "payroll_run_failed",
        "details": {},
        "error": "급여 처리 실패",
    }


def payroll_api_validation_example() -> dict[str, Any]:
    """Return a representative validation-only response shape."""
    scope = PayrollScope("COSS", "Site A", "2026-05")
    return {
        "ok": True,
        "status": "validated",
        "will_run": False,
        "can_run": True,
        "request_id": "payroll-run-2026-05-coss-site-a",
        "scope": "COSS/Site A/2026-05",
        "scope_key": scope.key,
        "affiliate": "COSS",
        "workplace": "Site A",
        "period": "2026-05",
        "input_type": "mixed",
        "requested_input_type": "mixed",
        "tenant_id": "coss",
        "paths": {
            "invoice": "C:/Bitween/inbox/invoice_2026-05.xlsx",
            "attendance": "C:/Bitween/inbox/attendance_2026-05.csv",
        },
        "metadata_keys": ["requested_by", "source_system"],
        "operation_policy": payroll_operation_policy_example(),
        "operation_policy_source": "tenant",
        "warnings": [],
        "error_code": "",
        "details": {},
        "error": "",
    }


def payroll_attendance_aggregation_example() -> dict[str, Any]:
    """Return the Rust-owned attendance aggregation contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::aggregate_attendance_records(records, workplace, attendance_policy)",
        "aggregator_entrypoint": "aggregate_attendance_records(records, workplace, attendance_policy)",
        "python_compatibility_source": "services.attendance_import._aggregate_records",
        "parser_boundary": "Python compatibility code may still parse CSV/XLSX files before supplying normalized records to Rust.",
        "source_record_fields": [
            "name",
            "name_key",
            "dept",
            "workplace",
            "work_hours",
            "late_hours",
            "early_leave_hours",
            "overtime_hours",
            "night_hours",
            "special_hours",
            "leave_days",
            "unpaid_days",
        ],
        "invoice_row_fields": [
            "row",
            "name",
            "dept",
            "hire_date",
            "workplace",
            "base_hourly",
            "ordinary_hourly",
            "base_days",
            "work_days",
            "unpaid_days",
            "leave_days",
            "ot_hours",
            "shift_hours",
            "night_hours",
            "special_hours",
            "special_ext_hours",
            "early_leave_hours",
            "base_salary",
            "base_deduction",
            "ot_pay",
            "night_pay",
            "special_pay",
            "special_ext_pay",
            "position_pay",
            "shift_pay",
            "workers_day_pay",
            "annual_pay",
            "transport",
            "subtotal",
            "gross_pay",
            "health_insurance",
            "long_term_care",
            "national_pension",
            "employment_insurance",
            "insurance_total",
            "_attendance_days",
            "_attendance_input",
        ],
        "example_source_records": [
            {
                "name": "홍 길동",
                "dept": "Payroll",
                "workplace": "Site A",
                "work_hours": 4.0,
                "late_hours": 0.1667,
                "overtime_hours": 0.5,
                "night_hours": 1.0,
            },
            {
                "name": "홍길동",
                "name_key": "홍길동",
                "dept": "Payroll",
                "workplace": "Site A",
                "work_hours": 4.0,
                "early_leave_hours": 0.0833,
                "overtime_hours": 0.5,
                "special_hours": 2.0,
                "leave_days": 1.0,
                "unpaid_days": 0.5,
            },
        ],
        "example_policy": {
            "rounding_minutes": 15,
            "late_grace_minutes": 5,
            "early_leave_grace_minutes": 0,
        },
        "example_invoice_rows": [
            {
                "row": 0,
                "name": "홍 길동",
                "dept": "Payroll",
                "hire_date": "",
                "workplace": "Site A",
                "base_days": 8.0,
                "work_days": 8.0,
                "unpaid_days": 0.5,
                "leave_days": 1.0,
                "ot_hours": 1.0,
                "night_hours": 1.0,
                "special_hours": 2.0,
                "early_leave_hours": 0.25,
                "subtotal": 0,
                "_attendance_days": 2,
                "_attendance_input": True,
            }
        ],
        "invariants": [
            "records are grouped by supplied name_key or a whitespace-normalized name key",
            "late and early-leave grace minutes are applied per source record before totals are rounded",
            "work, late/early, overtime, night, and special hours are rounded with Python-compatible half-even rounding",
            "invoice rows are sorted by employee name and keep zero-valued payroll amount fields until the payroll calculator fills them",
        ],
    }


def payroll_workplace_hours_application_example() -> dict[str, Any]:
    """Return the Rust-owned workplace monthly-hours application contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)",
        "resolver_entrypoint": "resolve_monthly_work_hours(invoice, workplace, workplace_hours_policy)",
        "calculator_entrypoint": "apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)",
        "python_compatibility_source": "services.workplace_hours.apply_monthly_hours_to_invoice",
        "settings_boundary": "Python compatibility code may still resolve tenant/site/global settings and canonical workplace aliases before supplying a policy to Rust.",
        "mode_values": [
            "fixed",
            "invoice_work_days",
            "invoice_base_days",
            "work_or_fixed",
            "base_or_fixed",
        ],
        "policy_fields": ["mode", "hours", "daily_hours", "break_minutes"],
        "invoice_fields": [
            "workplace",
            "work_days",
            "base_days",
            "_monthly_work_hours",
            "_monthly_hours_source",
        ],
        "example_policy": {
            "mode": "invoice_work_days",
            "hours": 209,
            "daily_hours": 8,
            "break_minutes": 60,
        },
        "example_invoice": {
            "workplace": "청구장",
            "work_days": 192,
            "base_days": 209,
        },
        "example_resolution": {
            "hours": 192,
            "source": "청구장: 청구서 근무시간",
            "workplace": "청구장",
            "policy": {
                "mode": "invoice_work_days",
                "hours": 209,
                "daily_hours": 8,
                "break_minutes": 60,
            },
        },
        "example_application": {
            "hours": 192,
            "source": "청구장: 청구서 근무시간",
            "invoice": {
                "workplace": "청구장",
                "work_days": 192,
                "base_days": 209,
                "_monthly_work_hours": 192,
                "_monthly_hours_source": "청구장: 청구서 근무시간",
            },
            "policy": {
                "mode": "invoice_work_days",
                "hours": 209,
                "daily_hours": 8,
                "break_minutes": 60,
            },
        },
        "invariants": [
            "invalid or missing modes fall back to fixed",
            "missing, invalid, or non-positive policy hours fall back to 209",
            "daily_hours is kept only when positive and break_minutes only when non-negative",
            "invoice work/base hours are clamped at zero before mode selection",
            "source labels preserve the Python compatibility Korean wording for all five modes",
        ],
    }



def payroll_invoice_audit_row_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input invoice audit row contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)",
        "auditor_entrypoint": "audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)",
        "python_compatibility_source": "core.payroll.invoice_audit.audit_invoice_row",
        "resolver_boundary": "Python compatibility code may still resolve settings, match ledger records, resolve fixed-hours profiles, and aggregate batch summaries before supplying row inputs to Rust.",
        "status_values": ["pass", "warn"],
        "invoice_fields": [
            "name",
            "workplace",
            "base_days",
            "work_days",
            "leave_days",
            "ot_hours",
            "special_hours",
            "special_ext_hours",
            "base_hourly",
            "base_salary",
            "_preserve_reference_hours",
        ],
        "record_fields": ["name", "workplace", "base_hourly", "_monthly_work_hours"],
        "row_fields": [
            "name",
            "workplace",
            "status",
            "status_label",
            "flags",
            "base_days",
            "work_days",
            "break_hours",
            "applied_monthly_hours",
            "hours_source",
            "policy_mode",
            "policy_fixed_hours",
            "base_hourly",
            "invoice_base_salary",
            "calc_base_salary",
            "formula",
            "fixed_hours_mode",
            "fixed_hours_source",
        ],
        "example_invoice": {
            "name": "박감사",
            "base_days": 209,
            "work_days": 200,
            "base_salary": 2_000_000,
        },
        "example_record": {
            "name": "박감사",
            "base_hourly": 10_000,
            "_monthly_work_hours": 208,
        },
        "example_row": {
            "name": "박감사",
            "workplace": "앰코",
            "status": "warn",
            "status_label": "확인",
            "flags": [
                "기본급 불일치: 산출 2,090,000원 vs 청구서 2,000,000원",
                "대장 적용시간(208h)과 재검열(209h) 상이",
            ],
            "base_days": 209,
            "work_days": 200,
            "break_hours": 9,
            "applied_monthly_hours": 209,
            "hours_source": "앰코: 고정 209시간",
            "policy_mode": "fixed",
            "policy_fixed_hours": 209,
            "base_hourly": 10_000,
            "invoice_base_salary": 2_000_000,
            "calc_base_salary": 2_090_000,
            "formula": "기본시급 10,000원 × 209시간 = 2,090,000원",
            "fixed_hours_mode": False,
            "fixed_hours_source": "",
        },
        "invariants": [
            "single-row auditing is pure once invoice, workplace policy, optional ledger record, and optional fixed-hours profile are supplied",
            "break_hours uses policy break_minutes first, then the base/work/leave gap fallback",
            "base-salary mismatches, missing invoice hours, missing base hourly, fixed-hour mismatches, and ledger monthly-hour mismatches preserve Python Korean flag wording",
            "fixed-hours profile application composes the Rust fixed-hours audit flags before row-level warnings",
            "settings lookup, record matching, fixed-profile resolution, workbook I/O, and UI text rendering remain Python compatibility boundaries in this slice",
        ],
    }


def payroll_invoice_audit_batch_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input invoice audit batch contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::audit_invoice_batch(items, workplace)",
        "auditor_entrypoint": "audit_invoice_batch(items, workplace)",
        "python_compatibility_source": "core.payroll.invoice_audit.audit_invoice_payroll",
        "resolver_boundary": (
            "Python compatibility code may still resolve settings, match ledger records, "
            "resolve fixed-hours profiles, parse workbooks, and render UI text before "
            "supplying batch items to Rust."
        ),
        "item_fields": [
            "invoice",
            "workplace",
            "policy",
            "record",
            "fixed_profile",
        ],
        "summary_fields": ["total", "pass", "warn"],
        "result_fields": [
            "workplace",
            "summary",
            "rows",
            "pass_count",
            "warn_count",
        ],
        "example_items": [
            {
                "invoice": {
                    "name": "A",
                    "base_days": 209,
                    "work_days": 209,
                    "base_hourly": 10_000,
                    "base_salary": 2_090_000,
                },
                "workplace": "앰코",
                "policy": {"mode": "fixed", "hours": 209},
                "record": {"name": "A", "workplace": "앰코", "base_hourly": 10_000},
            },
            {
                "invoice": {
                    "name": "B",
                    "base_days": 209,
                    "work_days": 209,
                    "base_hourly": 10_000,
                    "base_salary": 1_000,
                },
                "workplace": "앰코",
                "policy": {"mode": "fixed", "hours": 209},
                "record": {"name": "B", "workplace": "앰코", "base_hourly": 10_000},
            },
            {
                "invoice": {
                    "name": "C",
                    "base_days": 209,
                    "work_days": 209,
                    "base_salary": 2_090_000,
                },
                "workplace": "앰코",
                "policy": {"mode": "fixed", "hours": 209},
                "record": {"name": "C", "workplace": "앰코", "base_hourly": 0},
            },
        ],
        "example_result": {
            "workplace": "앰코",
            "summary": {"total": 3, "pass": 2, "warn": 1},
            "pass_count": 2,
            "warn_count": 1,
            "rows": [
                {"name": "A", "status": "pass"},
                {"name": "B", "status": "warn"},
                {"name": "C", "status": "pass"},
            ],
        },
        "invariants": [
            "batch auditing is pure once each item has invoice, workplace policy, optional ledger record, and optional fixed-hours profile supplied",
            "row order is preserved exactly as supplied",
            "summary.total, summary.pass, summary.warn, pass_count, and warn_count are derived from Rust row statuses",
            "empty item workplace falls back to the batch workplace before the row auditor resolves record or invoice workplace",
            "settings lookup, ledger matching, fixed-profile resolution, workbook I/O, and UI text rendering remain Python compatibility boundaries in this slice",
        ],
    }



def payroll_social_insurance_calculation_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input social-insurance calculation shape."""
    return {
        "rust_entrypoint": "PayrollApiService::calculate_social_insurance(input)",
        "calculator_entrypoint": "calculate_social_insurance(input)",
        "employment_entrypoint": "calculate_employment_insurance(taxable_total)",
        "python_compatibility_source": "insurance.calculate_insurance + utils.calc_employment_insurance",
        "resolver_boundary": (
            "Python compatibility code may still parse employee identities, determine age/KCOMWEL "
            "eligibility, read roster/master workbooks, apply EDI premium overrides, and mutate "
            "workbook/payroll rows before or after supplying pure insurance inputs to Rust."
        ),
        "rates": {
            "national_pension": 0.045,
            "health_insurance": 0.03545,
            "long_term_care_ratio": 0.1295,
            "employment_insurance_worker": 0.009,
        },
        "pension_limits": {"floor": 390_000, "ceiling": 6_170_000},
        "input_fields": [
            "taxable_pay",
            "preset_national_pension",
            "preset_health_insurance",
            "insurance_exempt",
        ],
        "result_fields": [
            "national_pension",
            "health_insurance",
            "long_term_care",
            "employment_insurance",
            "total",
            "insurance_exempt",
        ],
        "example_input": {"taxable_pay": 3_000_000, "insurance_exempt": False},
        "example_result": {
            "national_pension": 135_000,
            "health_insurance": 106_350,
            "long_term_care": 13_772,
            "employment_insurance": 27_000,
            "total": 282_122,
            "insurance_exempt": False,
        },
        "example_preset_result": {
            "national_pension": 123_456,
            "health_insurance": 76_544,
            "long_term_care": 9_912,
            "employment_insurance": 27_000,
            "total": 236_912,
            "insurance_exempt": False,
        },
        "example_exempt_result": {
            "national_pension": 0,
            "health_insurance": 0,
            "long_term_care": 0,
            "employment_insurance": 0,
            "total": 0,
            "insurance_exempt": True,
        },
        "invariants": [
            "taxable_pay is supplied after non-taxable pay has already been removed by compatibility code",
            "insurance_exempt true zeroes all worker social-insurance contributions",
            "positive preset_national_pension overrides pension-rate calculation after Python-compatible won rounding",
            "positive preset_health_insurance overrides health-rate calculation and long-term care is recalculated from the rounded health amount",
            "pension-rate calculation clamps taxable pay to 390000..6170000 before applying 4.5%",
            "employment insurance is taxable pay times 0.009 rounded to the nearest 10 won",
            "identity parsing, KCOMWEL age-65 decisions, EDI premium overrides, roster/master lookup, and workbook mutation remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_earnings_calculation_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input payroll earnings calculation shape."""
    return {
        "rust_entrypoint": "PayrollApiService::calculate_payroll_earnings(input)",
        "calculator_entrypoint": "calculate_payroll_earnings(input)",
        "python_compatibility_source": "calculator.calculate_salary earnings block + calculator.calc_ordinary_hourly/calc_weekly_holiday_pay/calc_overlap_premium",
        "resolver_boundary": (
            "Python compatibility code may still parse invoices, merge employee masters, normalize "
            "strings/cell values, calculate social insurance and taxes, finalize deductions, and assemble "
            "final payroll records before or after supplying pure numeric earnings inputs to Rust."
        ),
        "constants": {
            "standard_monthly_hours": 209,
            "meal_allowance_per_day": 5_500,
            "meal_non_taxable_cap": 200_000,
            "overtime_premium": 1.5,
            "night_premium": 0.5,
            "holiday_premium": 1.5,
            "overlap_premium": 0.5,
        },
        "input_fields": [
            "base_salary",
            "fixed_allowance",
            "ordinary_hourly",
            "overtime_hours",
            "night_hours",
            "holiday_hours",
            "overtime_amount_raw",
            "night_amount_raw",
            "holiday_amount_raw",
            "meal_days",
            "transport_allowance",
            "other_pay",
            "additional_pay",
            "weekly_work_hours",
        ],
        "hours_fields": [
            "overtime",
            "night",
            "holiday",
        ],
        "earnings_fields": [
            "base_salary",
            "fixed_allowance",
            "overtime",
            "night",
            "holiday",
            "overlap_premium",
            "weekly_holiday",
            "meal",
            "transport",
            "other",
            "additional",
        ],
        "result_fields": [
            "ordinary_hourly",
            "hours",
            "earnings",
            "gross_pay",
            "taxable_pay",
            "non_taxable_pay",
        ],
        "example_input": {
            "base_salary": 2_090_000,
            "fixed_allowance": 100_000,
            "overtime_hours": 10,
            "night_hours": 4,
            "holiday_hours": 8,
            "meal_days": 22,
            "transport_allowance": 50_000,
            "other_pay": 12_345.5,
            "additional_pay": 100_000,
            "weekly_work_hours": 35,
        },
        "example_result": {
            "ordinary_hourly": 10_478.47,
            "hours": {
                "overtime": 10.0,
                "night": 4.0,
                "holiday": 8.0,
            },
            "earnings": {
                "base_salary": 2_090_000,
                "fixed_allowance": 100_000,
                "overtime": 157_177,
                "night": 20_957,
                "holiday": 125_742,
                "overlap_premium": 20_957,
                "weekly_holiday": 73_349,
                "meal": 121_000,
                "transport": 50_000,
                "other": 12_346,
                "additional": 100_000,
            },
            "gross_pay": 2_871_528,
            "non_taxable_pay": 121_000,
            "taxable_pay": 2_750_528,
        },
        "example_raw_amount_input": {
            "ordinary_hourly": 12_000,
            "overtime_amount_raw": 300_000,
            "night_amount_raw": 50_000,
            "holiday_amount_raw": 200_000,
            "meal_days": 50,
            "weekly_work_hours": 40,
        },
        "example_raw_amount_result": {
            "ordinary_hourly": 12_000.0,
            "hours": {
                "overtime": 16.666666666666668,
                "night": 0.0,
                "holiday": 0.0,
            },
            "earnings": {
                "base_salary": 2_508_000,
                "fixed_allowance": 0,
                "overtime": 300_000,
                "night": 50_000,
                "holiday": 200_000,
                "overlap_premium": 0,
                "weekly_holiday": 96_000,
                "meal": 275_000,
                "transport": 0,
                "other": 0,
                "additional": 0,
            },
            "gross_pay": 3_429_000,
            "non_taxable_pay": 200_000,
            "taxable_pay": 3_229_000,
        },
        "invariants": [
            "preset ordinary_hourly overrides (base_salary + fixed_allowance) / 209 when positive",
            "weekly holiday pay is prorated by min(weekly_work_hours, 40) / 40 * 8 hours",
            "overtime, night, holiday, overlap, meal, transport, other, and additional pay use Python-compatible won rounding",
            "raw overtime/night/holiday amounts are used only when computed pay is non-positive and the raw value is not likely an hours value",
            "raw overtime amount updates returned overtime hours; raw night and holiday amounts do not update returned hours",
            "base_salary falls back to ordinary_hourly * 209 when supplied base_salary is non-positive",
            "non_taxable_pay is capped at the meal allowance cap while taxable_pay is gross_pay minus non_taxable_pay",
            "invoice parsing, employee master merge, social-insurance/tax/deduction orchestration, workbook I/O, and final record assembly remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_salary_calculation_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input payroll salary calculation shape."""
    earnings = payroll_earnings_calculation_example()
    return {
        "rust_entrypoint": "PayrollApiService::calculate_payroll_salary(input)",
        "calculator_entrypoint": "calculate_payroll_salary(input)",
        "python_compatibility_source": "calculator.calculate_salary",
        "resolver_boundary": (
            "Python compatibility code may still parse invoices, merge employee masters, normalize "
            "strings/cell values, determine age/KCOMWEL/EDI overrides, write workbooks, and assemble "
            "final payroll records before or after supplying pure salary inputs to Rust."
        ),
        "tax_method_values": ["PRESET", "SIMPLIFIED_TABLE"],
        "input_fields": [
            "name",
            "emp_no",
            "department",
            "account_no",
            *earnings["input_fields"],
            "preset_national_pension",
            "preset_health_insurance",
            "preset_income_tax",
            "insurance_exempt",
        ],
        "python_input_aliases": {
            "preset_health": "preset_health_insurance",
        },
        "hours_fields": earnings["hours_fields"],
        "earnings_fields": earnings["earnings_fields"],
        "deductions_fields": [
            "national_pension",
            "health_insurance",
            "long_term_care",
            "employment_insurance",
            "income_tax",
            "local_income_tax",
            "total",
        ],
        "result_fields": [
            "name",
            "emp_no",
            "department",
            "account_no",
            "ordinary_hourly",
            "hours",
            "earnings",
            "deductions",
            "gross_pay",
            "taxable_pay",
            "non_taxable_pay",
            "total_deductions",
            "net_pay",
            "tax_method",
        ],
        "example_input": {
            "name": "홍길동",
            "emp_no": "E001",
            "department": "Payroll",
            "account_no": "111-222",
            **earnings["example_input"],
        },
        "example_result": {
            "name": "홍길동",
            "emp_no": "E001",
            "department": "Payroll",
            "account_no": "111-222",
            "ordinary_hourly": 10_478.47,
            "hours": {
                "overtime": 10.0,
                "night": 4.0,
                "holiday": 8.0,
            },
            "earnings": earnings["example_result"]["earnings"],
            "deductions": {
                "national_pension": 123_774,
                "health_insurance": 97_506,
                "long_term_care": 12_627,
                "employment_insurance": 24_750,
                "income_tax": 210_000,
                "local_income_tax": 21_000,
                "total": 489_657,
            },
            "gross_pay": 2_871_528,
            "non_taxable_pay": 121_000,
            "taxable_pay": 2_750_528,
            "total_deductions": 489_657,
            "net_pay": 2_381_871,
            "tax_method": "SIMPLIFIED_TABLE",
        },
        "example_raw_amount_result": {
            "name": "김시급",
            "emp_no": "E002",
            "department": "Ops",
            "account_no": "333-444",
            "ordinary_hourly": 12_000.0,
            "hours": earnings["example_raw_amount_result"]["hours"],
            "earnings": earnings["example_raw_amount_result"]["earnings"],
            "deductions": {
                "national_pension": 145_305,
                "health_insurance": 114_468,
                "long_term_care": 14_824,
                "employment_insurance": 29_060,
                "income_tax": 310_000,
                "local_income_tax": 31_000,
                "total": 644_657,
            },
            "gross_pay": 3_429_000,
            "non_taxable_pay": 200_000,
            "taxable_pay": 3_229_000,
            "total_deductions": 644_657,
            "net_pay": 2_784_343,
            "tax_method": "SIMPLIFIED_TABLE",
        },
        "example_preset_result": {
            "name": "박프리셋",
            "emp_no": "",
            "department": "",
            "account_no": "",
            "ordinary_hourly": 19_138.76,
            "hours": {
                "overtime": 0.0,
                "night": 0.0,
                "holiday": 0.0,
            },
            "earnings": {
                "base_salary": 4_000_000,
                "fixed_allowance": 0,
                "overtime": 0,
                "night": 0,
                "holiday": 0,
                "overlap_premium": 0,
                "weekly_holiday": 153_110,
                "meal": 110_000,
                "transport": 0,
                "other": 0,
                "additional": 0,
            },
            "deductions": {
                "national_pension": 123_456,
                "health_insurance": 76_544,
                "long_term_care": 9_912,
                "employment_insurance": 37_380,
                "income_tax": 123_456,
                "local_income_tax": 12_346,
                "total": 383_094,
            },
            "gross_pay": 4_263_110,
            "non_taxable_pay": 110_000,
            "taxable_pay": 4_153_110,
            "total_deductions": 383_094,
            "net_pay": 3_880_016,
            "tax_method": "PRESET",
        },
        "invariants": [
            "salary calculation composes Rust-owned earnings and social-insurance calculations from supplied normalized inputs",
            "income tax preserves calculator.calculate_salary rounding: preset income tax is won-rounded and local tax is won-rounded at 10%",
            "tax_method uses the calculator-compatible uppercase values PRESET and SIMPLIFIED_TABLE",
            "total_deductions is social-insurance total plus income/local tax total",
            "net_pay is gross_pay minus total_deductions",
            "invoice parsing, employee master merge, age/KCOMWEL/EDI resolution, workbook I/O, and final record assembly remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_deduction_finalization_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input final deduction/net-pay shape."""
    return {
        "rust_entrypoint": "PayrollApiService::finalize_payroll_deductions(input)",
        "calculator_entrypoint": "finalize_payroll_deductions(input)",
        "tax_entrypoint": "calculate_payroll_income_tax(taxable_pay, preset_income_tax, preset_local_income_tax)",
        "python_compatibility_source": "tax.calculate_tax + payroll_builder.build_payroll_records final deduction block",
        "resolver_boundary": (
            "Python compatibility code may still parse workbooks, match employee rosters, "
            "resolve social insurance, apply EDI/site/fixed-hour rules, and assemble final payroll records "
            "before or after supplying pure deduction inputs to Rust."
        ),
        "method_values": ["preset", "simplified_table"],
        "input_fields": [
            "gross_pay",
            "insurance_total",
            "preset_income_tax",
            "preset_local_income_tax",
            "identity_guarantee_insurance_deduction",
        ],
        "tax_result_fields": [
            "income_tax",
            "local_income_tax",
            "total",
            "method",
        ],
        "result_fields": [
            "gross_pay",
            "insurance_total",
            "taxable_pay",
            "income_tax",
            "local_income_tax",
            "tax_total",
            "identity_guarantee_insurance_deduction",
            "total_deduction",
            "net_pay",
            "method",
        ],
        "simplified_tax_brackets": [
            {"upper_bound": 1_060_000, "income_tax": 0},
            {"upper_bound": 1_500_000, "income_tax": 8_000},
            {"upper_bound": 2_000_000, "income_tax": 42_000},
            {"upper_bound": 2_500_000, "income_tax": 120_000},
            {"upper_bound": 3_000_000, "income_tax": 210_000},
            {"upper_bound": 3_500_000, "income_tax": 310_000},
            {"upper_bound": 4_000_000, "income_tax": 420_000},
            {"upper_bound": 5_000_000, "income_tax": 650_000},
            {"upper_bound": 6_000_000, "income_tax": 920_000},
            {"upper_bound": 8_000_000, "income_tax": 1_450_000},
            {"upper_bound": 10_000_000, "income_tax": 2_100_000},
        ],
        "high_income_estimate_formula": "max(0, taxable_pay - 1500000) * 0.03 rounded to won",
        "example_input": {
            "gross_pay": 3_000_000,
            "insurance_total": 300_000,
            "identity_guarantee_insurance_deduction": -20_000,
        },
        "example_result": {
            "gross_pay": 3_000_000,
            "insurance_total": 300_000,
            "taxable_pay": 2_700_000,
            "income_tax": 210_000,
            "local_income_tax": 21_000,
            "tax_total": 231_000,
            "identity_guarantee_insurance_deduction": -20_000,
            "total_deduction": 551_000,
            "net_pay": 2_449_000,
            "method": "simplified_table",
        },
        "example_preset_result": {
            "gross_pay": 4_000_000,
            "insurance_total": 450_000,
            "taxable_pay": 3_550_000,
            "income_tax": 123_456,
            "local_income_tax": 12_350,
            "tax_total": 135_806,
            "identity_guarantee_insurance_deduction": 0,
            "total_deduction": 585_806,
            "net_pay": 3_414_194,
            "method": "preset",
        },
        "invariants": [
            "taxable_pay is gross_pay minus insurance_total exactly as supplied",
            "positive preset_income_tax overrides the simplified tax table",
            "positive preset_local_income_tax overrides automatic local tax only when preset income tax is used",
            "automatic local tax for preset income tax is rounded to the nearest 10 won like payroll_builder",
            "simplified-table local tax is rounded to the nearest won like tax.calculate_tax",
            "identity_guarantee_insurance_deduction contributes to total_deduction by absolute value",
            "net_pay is gross_pay minus total_deduction with Python-compatible won rounding",
            "workbook parsing, roster matching, social-insurance resolution, tax-table persistence, and record assembly remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_ei65_decision_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-input EI 65+ payroll decision shape."""
    return {
        "rust_entrypoint": "PayrollApiService::resolve_ei_65_for_payroll(input)",
        "calculator_entrypoint": "resolve_ei_65_for_payroll(input)",
        "python_compatibility_source": "core.payroll.employment_insurance_65.resolve_ei_65_for_payroll",
        "resolver_boundary": (
            "Python compatibility code may still import/persist KCOMWEL records, "
            "resolve site management numbers, match employees, call future live KCOMWEL APIs, "
            "mutate payroll invoice rows, coordinate supplied EDI premium inputs, and read/write workbooks before or after "
            "supplying pure decision inputs to Rust."
        ),
        "status_values": ["exempt", "liable", "unknown"],
        "unknown_default_values": ["skip", "deduct"],
        "source_values": ["manual", "import", "api"],
        "verification_fields": [
            "employee_id",
            "employee_name",
            "check_date",
            "premium_amount",
            "management_no",
            "source",
        ],
        "input_fields": [
            "identity",
            "payroll_period",
            "employee_id",
            "employee_name",
            "workplace",
            "site_management_no",
            "unknown_default",
            "latest_verification",
        ],
        "result_fields": [
            "status",
            "premium_amount",
            "management_no",
            "deduct_employment_insurance",
            "warning",
            "default_action",
        ],
        "example_input": {
            "identity": "500615-1",
            "payroll_period": "2026-05",
            "employee_id": "E65",
            "employee_name": "김순자",
            "workplace": "한국앰코",
            "site_management_no": "1234567890",
            "unknown_default": "skip",
            "latest_verification": {
                "employee_id": "E65",
                "employee_name": "김순자",
                "check_date": "2026-05-01",
                "premium_amount": 0,
                "management_no": "1234567890",
                "source": "manual",
            },
        },
        "example_result": {
            "status": "exempt",
            "premium_amount": 0,
            "management_no": "1234567890",
            "deduct_employment_insurance": False,
            "warning": "",
            "default_action": "skip",
        },
        "example_unknown_result": {
            "status": "unknown",
            "premium_amount": None,
            "management_no": "1234567890",
            "deduct_employment_insurance": False,
            "warning": "김순자: 만 65세 이상 고용보험 KCOMWEL 확인 미완료 → 설정 기본값(공제 생략) 적용",
            "default_action": "skip",
        },
        "invariants": [
            "valid payroll periods use the calendar month end as the age basis",
            "Korean RRN century codes and six-digit birth dates use Python-compatible age parsing",
            "workers below age 65 return liable with no KCOMWEL premium lookup requirement",
            "supplied premiums less than or equal to zero return exempt and suppress employment-insurance deduction",
            "supplied positive premiums return liable and keep employment-insurance deduction enabled",
            "missing verification records return unknown and apply the supplied unknown_default skip/deduct behavior",
            "KCOMWEL storage, site settings lookup, live API calls, payroll row mutation, EDI premium input resolution, and workbook I/O remain Python compatibility boundaries in this slice",
        ],
    }


def payroll_edi_insurance_application_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-record EDI premium application shape."""
    return {
        "rust_entrypoint": "PayrollApiService::apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)",
        "calculator_entrypoint": "apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)",
        "python_compatibility_source": "core.payroll.edi_insurance.apply_edi_premiums_to_inv",
        "resolver_boundary": (
            "Python compatibility code may still import CSV/Excel EDI files, persist premium records, "
            "call future EDI providers, resolve tenant/site settings and site management numbers, "
            "match employees, and coordinate workbook I/O before or after supplying pure inputs to Rust."
        ),
        "source_values": ["manual", "import", "api", "calculated"],
        "messages": {
            "disabled": "EDI 보험료 사용 꺼짐",
            "missing_record": "EDI 보험료 없음",
            "applied": "EDI 보험료 적용",
            "badge": "EDI 조회",
        },
        "long_term_care_ratio": 0.1295,
        "config_fields": [
            "use_edi_premiums",
            "respect_age_exempt",
        ],
        "record_fields": [
            "employee_id",
            "employee_name",
            "period",
            "national_pension",
            "health_insurance",
            "long_term_care",
            "employment_insurance",
            "industrial_accident",
            "industrial_accident_employer",
            "industrial_accident_employee",
            "management_no",
            "source",
            "fetched_at",
            "workplace",
            "note",
        ],
        "invoice_fields": [
            "name",
            "employee_id",
            "workplace",
            "national_pension",
            "health_insurance",
            "long_term_care",
            "employment_insurance",
            "industrial_accident",
            "industrial_accident_employer",
            "industrial_accident_employee",
            "insurance_total",
            "insurance_exempt",
            "edi_premium_source",
            "edi_premium_badge",
            "edi_premium_period",
            "edi_premium_fetched_at",
            "edi_premium_source_type",
        ],
        "application_fields": ["applied", "record", "message", "invoice"],
        "example_config": {
            "use_edi_premiums": True,
            "respect_age_exempt": True,
        },
        "example_invoice": {
            "name": "김철수",
            "employee_id": "E02",
            "workplace": "한국앰코",
            "national_pension": 0,
            "health_insurance": 0,
            "long_term_care": 0,
            "employment_insurance": 18_000,
            "industrial_accident": 0,
            "insurance_total": 18_000,
            "insurance_exempt": False,
        },
        "example_record": {
            "employee_id": "E02",
            "employee_name": "김철수",
            "period": "2026-06",
            "national_pension": 80_000,
            "health_insurance": 40_000,
            "long_term_care": 0,
            "employment_insurance": 20_000,
            "industrial_accident": 3_000,
            "industrial_accident_employer": 2_000,
            "industrial_accident_employee": 0,
            "management_no": "1234567890",
            "source": "manual",
            "fetched_at": "2026-06-10T09:00:00",
            "workplace": "한국앰코",
            "note": "supplied EDI record",
        },
        "example_application": {
            "applied": True,
            "message": "EDI 보험료 적용",
            "record": {
                "employee_id": "E02",
                "employee_name": "김철수",
                "period": "2026-06",
                "national_pension": 80_000,
                "health_insurance": 40_000,
                "long_term_care": 0,
                "employment_insurance": 20_000,
                "industrial_accident": 3_000,
                "industrial_accident_employer": 2_000,
                "industrial_accident_employee": 0,
                "management_no": "1234567890",
                "source": "manual",
                "fetched_at": "2026-06-10T09:00:00",
                "workplace": "한국앰코",
                "note": "supplied EDI record",
            },
            "invoice": {
                "name": "김철수",
                "employee_id": "E02",
                "workplace": "한국앰코",
                "national_pension": 80_000,
                "health_insurance": 40_000,
                "long_term_care": 5_180,
                "employment_insurance": 20_000,
                "industrial_accident": 3_000,
                "industrial_accident_employer": 2_000,
                "industrial_accident_employee": 0,
                "insurance_total": 145_180,
                "insurance_exempt": False,
                "edi_premium_source": True,
                "edi_premium_badge": "EDI 조회",
                "edi_premium_period": "2026-06",
                "edi_premium_fetched_at": "2026-06-10T09:00:00",
                "edi_premium_source_type": "manual",
            },
        },
        "invariants": [
            "disabled configs and missing records return applied=false without mutating the invoice",
            "period strings normalize to YYYY-MM for record and invoice metadata",
            "pension, health, and long-term-care override only from positive EDI values unless age-exempt handling preserves them",
            "missing long-term-care falls back to Python-compatible round(health_insurance * 0.1295)",
            "zero employment insurance clears existing non-age-exempt employment insurance while positive values apply",
            "industrial-accident employer/employee split fields preserve supplied zero values",
            "insurance_total is recalculated from pension, health, long-term-care, and employment insurance only",
            "EDI import/storage/provider/settings/roster/workbook I/O remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_site_benefits_application_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-config site-benefits application shape."""
    return {
        "rust_entrypoint": "PayrollApiService::apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)",
        "calculator_entrypoint": "apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)",
        "python_compatibility_source": "core.payroll.site_benefits.apply_site_benefits_to_invoice",
        "resolver_boundary": (
            "Python compatibility code may still resolve site/tenant/global settings, "
            "canonicalize workplace aliases, inspect and persist identity-insurance "
            "ledgers, parse workbooks, and recalculate payroll totals before or after "
            "supplying pure inputs to Rust."
        ),
        "source_values": ["site", "tenant", "global"],
        "workers_day_config_fields": [
            "enabled",
            "default_amount",
            "auto_from_invoice",
        ],
        "identity_insurance_config_fields": [
            "enabled",
            "annual_amount",
            "billing_month",
        ],
        "config_fields": [
            "workers_day_allowance",
            "workers_day_source",
            "identity_guarantee_insurance",
            "identity_insurance_source",
            "identity_insurance_already_applied",
        ],
        "invoice_fields": [
            "name",
            "workplace",
            "base_salary",
            "workers_day_pay",
            "workers_day_allowance",
            "identity_guarantee_insurance_deduction",
            "_workers_day_source",
            "_identity_insurance_source",
        ],
        "application_fields": [
            "workers_day_allowance",
            "identity_guarantee_insurance_deduction",
            "workers_day_source",
            "identity_insurance_source",
            "invoice",
        ],
        "example_config": {
            "workers_day_allowance": {
                "enabled": True,
                "default_amount": 12_000,
                "auto_from_invoice": False,
            },
            "workers_day_source": "site",
            "identity_guarantee_insurance": {
                "enabled": True,
                "annual_amount": 20_000,
                "billing_month": 5,
            },
            "identity_insurance_source": "site",
            "identity_insurance_already_applied": False,
        },
        "example_invoice": {
            "name": "박민수",
            "workplace": "한국앰코",
            "base_salary": 2_090_000,
            "workers_day_pay": 99_999,
        },
        "example_application": {
            "workers_day_allowance": 12_000,
            "identity_guarantee_insurance_deduction": -20_000,
            "workers_day_source": "site",
            "identity_insurance_source": "site",
            "invoice": {
                "name": "박민수",
                "workplace": "한국앰코",
                "base_salary": 2_090_000,
                "workers_day_pay": 99_999,
                "workers_day_allowance": 12_000,
                "identity_guarantee_insurance_deduction": -20_000,
                "_workers_day_source": "site",
                "_identity_insurance_source": "site",
            },
        },
        "invariants": [
            "Workers' Day invoice-driven mode uses a positive supplied workers_day_pay regardless of period month",
            "Workers' Day fixed default mode applies only in May when the default amount is positive",
            "identity insurance applies as a negative annual amount only in the configured billing month",
            "identity_insurance_already_applied suppresses the yearly deduction without reading or writing ledgers in Rust",
            "settings lookup, workplace canonicalization, ledger persistence, workbook I/O, and payroll total recalculation remain Python compatibility boundaries in this slice",
        ],
    }

def payroll_fixed_hours_application_example() -> dict[str, Any]:
    """Return the Rust-owned fixed-hours application contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)",
        "calculator_entrypoint": "apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)",
        "python_compatibility_source": "core.payroll.fixed_hours.apply_fixed_hours_to_invoice",
        "resolver_boundary": "Python compatibility code may still resolve HR contracts, site job-group templates, and payroll settings before supplying a fixed-hours profile to Rust.",
        "pay_type_values": ["hourly", "monthly_salary"],
        "profile_fields": [
            "fixed_hours_mode",
            "monthly_fixed_hours",
            "daily_fixed_hours",
            "fixed_overtime_hours",
            "fixed_extension_hours",
            "pay_type",
            "job_group",
            "source",
            "source_label",
            "contract_id",
        ],
        "invoice_fields": [
            "name",
            "workplace",
            "work_days",
            "base_days",
            "ot_hours",
            "special_hours",
            "special_ext_hours",
            "_invoice_work_days",
            "_invoice_base_days",
            "_invoice_ot_hours",
            "_invoice_special_hours",
            "_invoice_special_ext_hours",
            "_monthly_work_hours",
            "_monthly_hours_source",
            "_fixed_hours_mode",
            "_fixed_hours_source",
            "_fixed_hours_pay_type",
            "_fixed_hours_job_group",
            "_preserve_reference_hours",
        ],
        "example_profile": {
            "fixed_hours_mode": True,
            "monthly_fixed_hours": 209,
            "daily_fixed_hours": 0,
            "fixed_overtime_hours": 10,
            "fixed_extension_hours": 20,
            "pay_type": "monthly_salary",
            "job_group": "경비",
            "source": "contract",
            "source_label": "근로계약서 기준 고정",
            "contract_id": "c1",
        },
        "example_invoice": {
            "name": "최연봉",
            "workplace": "청구지",
            "work_days": 150,
            "base_days": 150,
            "ot_hours": 5,
            "special_hours": 3,
            "special_ext_hours": 2,
        },
        "example_application": {
            "applied": True,
            "invoice": {
                "name": "최연봉",
                "workplace": "강남경비",
                "work_days": 209,
                "base_days": 209,
                "ot_hours": 20,
                "special_hours": 10,
                "special_ext_hours": 2,
                "_invoice_work_days": 150,
                "_invoice_base_days": 150,
                "_invoice_ot_hours": 5,
                "_invoice_special_hours": 3,
                "_invoice_special_ext_hours": 2,
                "_monthly_work_hours": 209,
                "_monthly_hours_source": "근로계약서 기준 고정",
                "_fixed_hours_mode": True,
                "_fixed_hours_source": "contract",
                "_fixed_hours_pay_type": "monthly_salary",
                "_fixed_hours_job_group": "경비",
                "_preserve_reference_hours": False,
            },
            "audit_flags": [
                "근로계약서 기준 고정 (경비)",
                "급여형태: 연봉직",
                "청구서 연장(5h) ≠ 계약 고정(20h)",
                "청구서 특근(3h) ≠ 계약 고정(10h)",
                "청구서 근무시간(150h) ≠ 계약 월시간(209h)",
            ],
        },
        "invariants": [
            "resolved profiles are normalized before application",
            "original invoice work/base/overtime/special hours are preserved under _invoice_* fields before replacement",
            "fixed_extension_hours maps to invoice ot_hours and fixed_overtime_hours maps to special_hours when positive",
            "_preserve_reference_hours keeps original invoice work/base hours for application while audit flags still compare against the resolved profile",
            "audit flags preserve the Python compatibility Korean labels for source, pay type, and hour mismatches",
        ],
    }


def payroll_policy_resolution_example() -> dict[str, Any]:
    """Return the Rust operation-policy resolution contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::validate_run_payload_with_policy_settings(payload, settings)",
        "resolver_entrypoint": "resolve_operation_policy(workplace, settings)",
        "source_values": ["site", "tenant", "global"],
        "precedence": ["site", "tenant", "global"],
        "settings_snapshot_fields": [
            "tenant_policy",
            "site_policies",
            "workplace_aliases",
        ],
        "example_resolution": {
            "workplace": "Site A",
            "policy": payroll_operation_policy_example(),
            "source": "site",
            "has_site_override": True,
        },
        "invariants": [
            "site payroll_operation_policy overrides tenant payroll_operation_policy when the canonical or aliased workplace matches",
            "tenant payroll_operation_policy overrides the built-in global default when no site override matches",
            "global default is used when neither site nor tenant policy exists",
            "the selected policy is normalized in Rust before validation response serialization",
        ],
    }


def payroll_execution_plan_example() -> dict[str, Any]:
    """Return the Rust-owned payroll execution planning contract shape."""
    return {
        "rust_entrypoint": "PayrollApiService::plan_run_request(request, policy_snapshot)",
        "planner_entrypoint": "plan_payroll_execution(request, policy_snapshot)",
        "backend_values": ["python_compatibility"],
        "step_kinds": [
            "extract_attendance",
            "build_attendance_invoice",
            "attach_attendance_sheet",
            "process_invoice",
        ],
        "compatibility_executor": "services.payroll_automation.run_payroll_automation",
        "example_plan": {
            "ok": True,
            "scope": "COSS/Site A/2026-05",
            "scope_key": PayrollScope("COSS", "Site A", "2026-05").key,
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "input_type": "mixed",
            "requested_input_type": "auto",
            "backend": "python_compatibility",
            "compatibility_executor": "services.payroll_automation.run_payroll_automation",
            "source_paths": {
                "invoice": "C:/Bitween/inbox/invoice_2026-05.xlsx",
                "attendance": "C:/Bitween/inbox/attendance_2026-05.csv",
            },
            "missing_source_paths": [],
            "steps": [
                {
                    "kind": "extract_attendance",
                    "backend": "python_compatibility",
                    "input": "C:/Bitween/inbox/attendance_2026-05.csv",
                    "output": "attendance_rows",
                    "description": "Extract attendance rows before merging them into the invoice workbook.",
                },
                {
                    "kind": "attach_attendance_sheet",
                    "backend": "python_compatibility",
                    "input": "C:/Bitween/inbox/invoice_2026-05.xlsx + attendance_rows",
                    "output": "generated:mixed_invoice",
                    "description": "Attach the attendance sheet to the supplied invoice workbook.",
                },
                {
                    "kind": "process_invoice",
                    "backend": "python_compatibility",
                    "input": "generated:mixed_invoice",
                    "output": "payroll_outputs",
                    "description": "Process the merged invoice workbook through the compatibility payroll executor.",
                },
            ],
            "operation_policy": payroll_operation_policy_example(),
            "operation_policy_source": "tenant",
            "warnings": [],
        },
        "invariants": [
            "explicit invoice, attendance, and mixed requests keep the caller-requested input type whenever required source paths exist",
            "auto requests resolve the executable input type from the normalized Rust operation policy",
            "mixed requests with only an attendance source plan an attendance fallback to match Python compatibility behavior",
            "the plan names python_compatibility until Rust owns payroll output generation",
        ],
    }


def payroll_api_authorization_example(*, allowed: bool = True) -> dict[str, Any]:
    """Return the Rust payroll authorization decision shape."""
    if allowed:
        return {
            "ok": True,
            "allowed": True,
            "action": "run",
            "user_id": "user-finance",
            "tenant_id": "coss",
            "scope": "COSS/Site A/2026-05",
            "reason_code": "",
            "reason": "",
            "required_permissions": ["platform.payroll.executive"],
            "granted_permissions": [
                "platform.payroll",
                "platform.payroll.executive",
            ],
        }
    return {
        "ok": False,
        "allowed": False,
        "action": "run",
        "user_id": "user-finance",
        "tenant_id": "other",
        "scope": "COSS/Site A/2026-05",
        "reason_code": "tenant_mismatch",
        "reason": "Payroll request tenant does not match the principal tenant.",
        "required_permissions": [],
        "granted_permissions": [
            "platform.payroll",
            "platform.payroll.executive",
        ],
    }


def payroll_api_health_example() -> dict[str, Any]:
    """Return the Rust service health response shape."""
    return {
        "ok": True,
        "status": "ok",
        "service": "bitween-payroll-api",
        "version": PAYROLL_API_VERSION,
        "environment": "production",
        "build_sha": "",
        "uptime_seconds": 0,
    }


def payroll_api_readiness_example() -> dict[str, Any]:
    """Return the Rust service readiness response shape."""
    return {
        "ready": False,
        "state": "not_ready",
        "service": "bitween-payroll-api",
        "version": PAYROLL_API_VERSION,
        "checks": [
            {
                "name": "policy",
                "state": "ready",
                "required": True,
                "message": "Rust policy invariants loaded",
            },
            {
                "name": "python_execution",
                "state": "degraded",
                "required": False,
                "message": "Compatibility fallback still active",
            },
            {
                "name": "database",
                "state": "not_ready",
                "required": True,
                "message": "Rust persistence is not configured",
            },
        ],
    }


def payroll_api_contract() -> dict[str, Any]:
    """Return the versioned contract used by docs and tests."""
    return {
        "version": PAYROLL_API_VERSION,
        "entrypoint": PAYROLL_API_ENTRYPOINT,
        "validation_entrypoint": PAYROLL_API_VALIDATE_ENTRYPOINT,
        "http": {
            "method": "POST",
            "path": PAYROLL_API_ENDPOINT,
            "content_type": "application/json",
            "implemented": False,
            "notes": "HTTP wrapper is planned; the framework-neutral service entrypoint is implemented now.",
            "validation_path": PAYROLL_API_VALIDATE_ENDPOINT,
            "health_path": PAYROLL_API_HEALTH_ENDPOINT,
            "readiness_path": PAYROLL_API_READINESS_ENDPOINT,
        },
        "input_types": list(PAYROLL_API_INPUT_TYPES),
        "attendance_aggregation": payroll_attendance_aggregation_example(),
        "workplace_hours_application": payroll_workplace_hours_application_example(),
        "invoice_audit_row": payroll_invoice_audit_row_example(),
        "invoice_audit_batch": payroll_invoice_audit_batch_example(),
        "social_insurance_calculation": payroll_social_insurance_calculation_example(),
        "earnings_calculation": payroll_earnings_calculation_example(),
        "salary_calculation": payroll_salary_calculation_example(),
        "deduction_finalization": payroll_deduction_finalization_example(),
        "ei65_payroll_decision": payroll_ei65_decision_example(),
        "edi_insurance_application": payroll_edi_insurance_application_example(),
        "site_benefits_application": payroll_site_benefits_application_example(),
        "fixed_hours_application": payroll_fixed_hours_application_example(),
        "policy_resolution": payroll_policy_resolution_example(),
        "execution_plan": payroll_execution_plan_example(),
        "authorization": {
            "rust_entrypoint": "PayrollApiService::authorize_run_request(request, principal, action)",
            "actions": ["validate", "run", "settings"],
            "permissions": {
                "validate": ["platform.payroll"],
                "run": ["platform.payroll.executive"],
                "settings": ["platform.payroll.settings"],
            },
            "role_families": ["staff", "finance", "admin"],
            "position_families": [
                "ceo",
                "executive",
                "director",
                "manager",
                "team_lead",
                "senior",
                "member",
                "intern",
            ],
            "abac_attributes": [
                "tenant_id",
                "affiliate",
                "workplace",
                "period",
                "org_unit_id",
                "effective_platform_ids",
                "allowed_affiliates",
                "allowed_workplaces",
            ],
            "deny_reason_codes": [
                "missing_principal_tenant",
                "tenant_mismatch",
                "missing_permission",
                "affiliate_not_allowed",
                "workplace_not_allowed",
            ],
            "invariants": [
                "request tenant_id must match the trusted principal tenant_id when supplied",
                "payroll platform permission is evaluated after role/position and effective org-unit platform filtering",
                "CEO position bypasses team platform filtering for Python compatibility",
                "non-CEO admin and finance role grants are still filtered by effective org-unit platforms",
                "allowed affiliate/workplace lists are treated as ABAC scope limits when non-empty",
            ],
        },
        "request": {
            "scope": {
                "forms": [
                    {
                        "name": "nested scope",
                        "required_fields": ["scope.affiliate", "scope.workplace", "scope.period"],
                    },
                    {
                        "name": "flat scope",
                        "required_fields": ["affiliate", "workplace", "period"],
                    },
                    {
                        "name": "scope key",
                        "required_fields": ["scope"],
                        "format": "affiliate/workplace/YYYY-MM",
                        "description": "Human-readable API scope string. Internal PayrollScope.key is also accepted.",
                    },
                ],
                "period_format": "YYYY-MM",
            },
            "fields": [
                {
                    "name": "request_id",
                    "aliases": ["requestId", "metadata.request_id", "metadata.requestId"],
                    "type": "string",
                    "required": False,
                    "description": "Caller correlation id. Echoed on success and validation errors.",
                },
                {
                    "name": "input_type",
                    "aliases": ["inputType"],
                    "type": "enum",
                    "values": list(PAYROLL_API_INPUT_TYPES),
                    "default": "auto",
                },
                {
                    "name": "invoice_path",
                    "aliases": ["invoicePath"],
                    "type": "string path",
                    "required_when": [
                        "input_type=invoice",
                        "input_type=mixed",
                        "input_type=auto and attendance_path is missing",
                    ],
                },
                {
                    "name": "attendance_path",
                    "aliases": ["attendancePath"],
                    "type": "string path",
                    "required_when": [
                        "input_type=attendance",
                        "input_type=mixed",
                        "input_type=auto and invoice_path is missing",
                    ],
                },
                {
                    "name": "tenant_id",
                    "aliases": ["tenantId"],
                    "type": "string",
                    "required": False,
                    "description": "Tenant/account id used to resolve payroll operation policy.",
                },
                {
                    "name": "metadata",
                    "type": "object",
                    "required": False,
                    "description": "Caller-owned metadata; preserved on the internal request.",
                },
                {
                    "name": "validate_only",
                    "aliases": ["validateOnly", "dry_run", "dryRun", "metadata.validate_only"],
                    "type": "boolean",
                    "required": False,
                    "description": "Validate the payload and return a normalized request response without running payroll.",
                },
            ],
            "examples": {
                "invoice": payroll_api_request_example(input_type="invoice"),
                "attendance": payroll_api_request_example(input_type="attendance"),
                "mixed": payroll_api_request_example(input_type="mixed"),
            },
        },
        "response": {
            "success": payroll_api_success_example(),
            "validation": payroll_api_validation_example(),
            "error": payroll_api_error_example(),
            "authorization": {
                "allowed": payroll_api_authorization_example(allowed=True),
                "denied": payroll_api_authorization_example(allowed=False),
            },
            "run_error": payroll_api_run_error_example(),
            "health": payroll_api_health_example(),
            "readiness": payroll_api_readiness_example(),
            "error_codes": {
                "invalid_payload": "Request body is not a JSON object/dict.",
                "invalid_scope": "Scope is not one of the accepted forms.",
                "missing_scope_fields": "Required scope fields are missing.",
                "invalid_period": "Period is not YYYY-MM.",
                "invalid_input_type": "Input type is not one of the supported values.",
                "missing_input_path": "Required invoice/attendance path is missing for the input type.",
                "payroll_run_failed": "Request was valid, but payroll processing failed.",
                "validation_error": "Validation failed without a more specific code.",
            },
            "stable_fields": [
                "ok",
                "status",
                "will_run",
                "can_run",
                "request_id",
                "error_code",
                "scope",
                "scope_key",
                "affiliate",
                "workplace",
                "period",
                "input_type",
                "requested_input_type",
                "count",
                "warnings",
                "paths",
                "payroll_audit",
                "roster",
                "operation_policy",
                "operation_policy_source",
                "metadata_keys",
                "allowed",
                "action",
                "reason_code",
                "required_permissions",
                "granted_permissions",
                "details",
                "error",
            ],
            "run_response_entrypoint": "PayrollApiService::run_response(result, request_id)",
            "policy_resolution_entrypoint": "PayrollApiService::validate_run_payload_with_policy_settings(payload, settings)",
            "execution_plan_entrypoint": "PayrollApiService::plan_run_request(request, policy_snapshot)",
            "attendance_aggregation_entrypoint": "PayrollApiService::aggregate_attendance_records(records, workplace, attendance_policy)",
            "workplace_hours_application_entrypoint": "PayrollApiService::apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)",
            "invoice_audit_row_entrypoint": "PayrollApiService::audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)",
            "invoice_audit_batch_entrypoint": "PayrollApiService::audit_invoice_batch(items, workplace)",
            "social_insurance_calculation_entrypoint": "PayrollApiService::calculate_social_insurance(input)",
            "earnings_calculation_entrypoint": "PayrollApiService::calculate_payroll_earnings(input)",
            "salary_calculation_entrypoint": "PayrollApiService::calculate_payroll_salary(input)",
            "deduction_finalization_entrypoint": "PayrollApiService::finalize_payroll_deductions(input)",
            "ei65_payroll_decision_entrypoint": "PayrollApiService::resolve_ei_65_for_payroll(input)",
            "edi_insurance_application_entrypoint": "PayrollApiService::apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)",
            "site_benefits_application_entrypoint": "PayrollApiService::apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)",
            "fixed_hours_application_entrypoint": "PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)",
            "never_include": ["exception"],
        },
    }


def payroll_api_contract_copy() -> dict[str, Any]:
    """Return a defensive copy for UI/API callers that may mutate data."""
    return deepcopy(payroll_api_contract())
