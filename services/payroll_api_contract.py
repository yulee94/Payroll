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
            "batch summary aggregation, settings lookup, record matching, and workbook I/O remain Python compatibility boundaries in this slice",
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
            "fixed_hours_application_entrypoint": "PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)",
            "never_include": ["exception"],
        },
    }


def payroll_api_contract_copy() -> dict[str, Any]:
    """Return a defensive copy for UI/API callers that may mutate data."""
    return deepcopy(payroll_api_contract())
