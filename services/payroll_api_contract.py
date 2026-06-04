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
            "never_include": ["exception"],
        },
    }


def payroll_api_contract_copy() -> dict[str, Any]:
    """Return a defensive copy for UI/API callers that may mutate data."""
    return deepcopy(payroll_api_contract())
