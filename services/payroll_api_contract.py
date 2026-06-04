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
PAYROLL_API_ENTRYPOINT = "services.payroll_api_adapter.run_payroll_api(payload)"
PAYROLL_API_INPUT_TYPES: tuple[str, ...] = ("auto", "invoice", "attendance", "mixed")


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
        "operation_policy": {
            "input_basis": "hybrid",
            "payday": "25일",
            "attendance": {
                "enabled": True,
                "rounding_minutes": 1,
                "late_grace_minutes": 0,
                "early_leave_grace_minutes": 0,
                "missing_clock_policy": "warn",
            },
        },
        "operation_policy_source": "tenant",
        "error": "",
    }


def payroll_api_error_example() -> dict[str, Any]:
    """Return a representative validation/error response shape."""
    return {
        "ok": False,
        "status": "error",
        "request_id": "payroll-run-2026-05-coss-site-a",
        "error": "period는 YYYY-MM 형식이어야 합니다.",
        "warnings": ["period는 YYYY-MM 형식이어야 합니다."],
    }


def payroll_api_contract() -> dict[str, Any]:
    """Return the versioned contract used by docs and tests."""
    return {
        "version": PAYROLL_API_VERSION,
        "entrypoint": PAYROLL_API_ENTRYPOINT,
        "http": {
            "method": "POST",
            "path": PAYROLL_API_ENDPOINT,
            "content_type": "application/json",
            "implemented": False,
            "notes": "HTTP wrapper is planned; the framework-neutral service entrypoint is implemented now.",
        },
        "input_types": list(PAYROLL_API_INPUT_TYPES),
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
                    "required_when": ["input_type=invoice", "input_type=mixed"],
                },
                {
                    "name": "attendance_path",
                    "aliases": ["attendancePath"],
                    "type": "string path",
                    "required_when": ["input_type=attendance", "input_type=mixed"],
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
            ],
            "examples": {
                "invoice": payroll_api_request_example(input_type="invoice"),
                "attendance": payroll_api_request_example(input_type="attendance"),
                "mixed": payroll_api_request_example(input_type="mixed"),
            },
        },
        "response": {
            "success": payroll_api_success_example(),
            "error": payroll_api_error_example(),
            "stable_fields": [
                "ok",
                "status",
                "request_id",
                "scope",
                "scope_key",
                "affiliate",
                "workplace",
                "period",
                "input_type",
                "count",
                "warnings",
                "paths",
                "payroll_audit",
                "roster",
                "operation_policy",
                "operation_policy_source",
                "error",
            ],
            "never_include": ["exception"],
        },
    }


def payroll_api_contract_copy() -> dict[str, Any]:
    """Return a defensive copy for UI/API callers that may mutate data."""
    return deepcopy(payroll_api_contract())
