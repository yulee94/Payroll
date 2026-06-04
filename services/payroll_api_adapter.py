"""
payroll_api_adapter.py - API-friendly request/response adapter for payroll automation.

This module is intentionally framework-neutral. A future FastAPI, Flask, or
internal desktop bridge can pass a plain dict payload here and receive a
JSON-friendly response without importing Tkinter-facing code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from services.payroll_automation import (
    PayrollAutomationRequest,
    PayrollAutomationResult,
    PayrollInputType,
    run_payroll_automation,
)
from services.payroll_scope import PayrollScope

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_INPUT_TYPES = ("auto", "invoice", "attendance", "mixed")


class PayrollApiValidationError(ValueError):
    """Validation error with a stable code for frontend/API callers."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _payload_mapping(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise PayrollApiValidationError(
            "급여 자동화 요청은 dict 형태여야 합니다.",
            code="invalid_payload",
            details={"expected": "object"},
        )
    return payload


def _scope_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    raw_scope = payload.get("scope")
    if isinstance(raw_scope, Mapping):
        return raw_scope
    return payload


def _request_id(payload: Mapping[str, Any] | None) -> str:
    try:
        data = _payload_mapping(payload)
    except ValueError:
        return ""
    metadata = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    return _text(
        data.get("request_id")
        or data.get("requestId")
        or metadata.get("request_id")
        or metadata.get("requestId")
    )


def _validate_only(payload: Mapping[str, Any] | None) -> bool:
    try:
        data = _payload_mapping(payload)
    except ValueError:
        return False
    metadata = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    return _truthy(
        data.get("validate_only")
        or data.get("validateOnly")
        or data.get("dry_run")
        or data.get("dryRun")
        or metadata.get("validate_only")
        or metadata.get("validateOnly")
    )


def _scope_from_api_string(value: str) -> PayrollScope | None:
    scope = PayrollScope.from_key(value)
    if scope is not None:
        return scope
    parts = [p.strip() for p in value.split("/", 2)]
    if len(parts) != 3 or not all(parts):
        return None
    affiliate, workplace, period = parts
    if not _PERIOD_RE.match(period):
        raise PayrollApiValidationError(
            "period는 YYYY-MM 형식이어야 합니다.",
            code="invalid_period",
            details={"period": period, "period_format": "YYYY-MM"},
        )
    return PayrollScope(affiliate, workplace, period)


def _scope_display(scope: PayrollScope) -> str:
    return f"{scope.affiliate}/{scope.workplace}/{scope.period}"


def scope_from_api_payload(payload: Mapping[str, Any] | None) -> PayrollScope:
    """Build PayrollScope from scope key or affiliate/workplace/period fields."""
    data = _payload_mapping(payload)
    raw_scope = data.get("scope")
    if isinstance(raw_scope, str):
        scope = _scope_from_api_string(raw_scope)
        if scope is None:
            raise PayrollApiValidationError(
                "scope 키 형식이 올바르지 않습니다.",
                code="invalid_scope",
                details={"scope_format": "affiliate/workplace/YYYY-MM"},
            )
        return scope
    if raw_scope is not None and not isinstance(raw_scope, Mapping):
        raise PayrollApiValidationError(
            "scope는 문자열 또는 객체 형태여야 합니다.",
            code="invalid_scope",
            details={"accepted_forms": ["affiliate/workplace/YYYY-MM", "scope object"]},
        )

    scope_data = _scope_payload(data)
    affiliate = _text(scope_data.get("affiliate"))
    workplace = _text(scope_data.get("workplace"))
    period = _text(scope_data.get("period"))
    missing = [
        label
        for label, value in (
            ("affiliate", affiliate),
            ("workplace", workplace),
            ("period", period),
        )
        if not value
    ]
    if missing:
        raise PayrollApiValidationError(
            f"scope 필드가 부족합니다: {', '.join(missing)}",
            code="missing_scope_fields",
            details={"missing_fields": missing},
        )
    if not _PERIOD_RE.match(period):
        raise PayrollApiValidationError(
            "period는 YYYY-MM 형식이어야 합니다.",
            code="invalid_period",
            details={"period": period, "period_format": "YYYY-MM"},
        )
    return PayrollScope(affiliate, workplace, period)


def _path_from_payload(payload: Mapping[str, Any], *keys: str) -> Path | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return Path(value)
    return None


def _input_type_from_payload(payload: Mapping[str, Any]) -> PayrollInputType:
    value = _text(payload.get("input_type") or payload.get("inputType") or "auto").lower()
    if value not in _INPUT_TYPES:
        raise PayrollApiValidationError(
            f"지원하지 않는 급여 입력 방식입니다: {value}",
            code="invalid_input_type",
            details={"input_type": value, "allowed_input_types": list(_INPUT_TYPES)},
        )
    return value  # type: ignore[return-value]


def _determine_request_input_type(request: PayrollAutomationRequest) -> str:
    if request.invoice_path and request.attendance_path:
        return "mixed"
    if request.attendance_path:
        return "attendance"
    return "invoice"


def _operation_policy_preview(request: PayrollAutomationRequest) -> tuple[dict[str, Any], str]:
    try:
        from services.payroll_policy_store import resolve_payroll_operation_policy

        resolved = resolve_payroll_operation_policy(
            request.scope.workplace,
            tenant_id=request.tenant_id,
        )
        policy = resolved.get("policy") if isinstance(resolved, dict) else None
        source = str(resolved.get("source") or "") if isinstance(resolved, dict) else ""
        return (dict(policy) if isinstance(policy, dict) else {}), source
    except Exception:
        return {}, ""


def _resolved_input_type_preview(
    request: PayrollAutomationRequest,
    operation_policy: Mapping[str, Any],
) -> str:
    if request.input_type != "auto":
        return request.input_type
    try:
        from services.payroll_policy_store import INPUT_ATTENDANCE, INPUT_HYBRID, INPUT_INVOICE

        basis = str(operation_policy.get("input_basis") or "")
        if basis == INPUT_ATTENDANCE:
            return "attendance"
        if basis == INPUT_HYBRID:
            if request.invoice_path and request.attendance_path:
                return "mixed"
            return _determine_request_input_type(request)
        if basis == INPUT_INVOICE:
            return "invoice"
    except Exception:
        pass
    return _determine_request_input_type(request)


def _validate_required_paths(
    input_type: PayrollInputType,
    *,
    invoice_path: Path | None,
    attendance_path: Path | None,
) -> None:
    missing: list[str] = []
    if input_type == "auto" and not invoice_path and not attendance_path:
        missing.extend(["invoice_path", "attendance_path"])
    elif input_type == "invoice" and not invoice_path:
        missing.append("invoice_path")
    elif input_type == "attendance" and not attendance_path:
        missing.append("attendance_path")
    elif input_type == "mixed":
        if not invoice_path:
            missing.append("invoice_path")
        if not attendance_path:
            missing.append("attendance_path")
    if not missing:
        return

    alias_hint = {
        "invoice_path": ["invoice_path", "invoicePath"],
        "attendance_path": ["attendance_path", "attendancePath"],
    }
    raise PayrollApiValidationError(
        "급여 입력 파일 경로가 부족합니다: " + ", ".join(missing),
        code="missing_input_path",
        details={
            "input_type": input_type,
            "missing_fields": missing,
            "accepted_aliases": {key: alias_hint[key] for key in missing},
        },
    )


def build_payroll_api_request(payload: Mapping[str, Any] | None) -> PayrollAutomationRequest:
    """Convert a JSON-like payload into the internal automation request."""
    data = _payload_mapping(payload)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    scope = scope_from_api_payload(data)
    input_type = _input_type_from_payload(data)
    invoice_path = _path_from_payload(data, "invoice_path", "invoicePath")
    attendance_path = _path_from_payload(data, "attendance_path", "attendancePath")
    _validate_required_paths(
        input_type,
        invoice_path=invoice_path,
        attendance_path=attendance_path,
    )
    return PayrollAutomationRequest(
        scope=scope,
        invoice_path=invoice_path,
        attendance_path=attendance_path,
        input_type=input_type,
        tenant_id=_text(data.get("tenant_id") or data.get("tenantId")) or None,
        interactive_parent=None,
        metadata=dict(metadata),
    )


def payroll_api_response(
    result: PayrollAutomationResult,
    *,
    request_id: str = "",
) -> dict[str, Any]:
    """Return a stable JSON-friendly response shape."""
    payload = result.as_dict()
    payload["scope_key"] = payload.get("scope", "")
    payload["scope"] = _scope_display(result.scope)
    payload["status"] = "success" if result.ok else "error"
    payload["will_run"] = True
    payload["can_run"] = bool(result.ok)
    payload["error_code"] = "" if result.ok else "payroll_run_failed"
    payload["details"] = {}
    if request_id:
        payload["request_id"] = request_id
    return payload


def payroll_api_validation_response(
    request: PayrollAutomationRequest,
    *,
    request_id: str = "",
) -> dict[str, Any]:
    """Return a stable response for validation-only API calls."""
    paths: dict[str, str] = {}
    if request.invoice_path is not None:
        paths["invoice"] = str(request.invoice_path)
    if request.attendance_path is not None:
        paths["attendance"] = str(request.attendance_path)
    operation_policy, operation_policy_source = _operation_policy_preview(request)
    resolved_input_type = _resolved_input_type_preview(request, operation_policy)

    payload: dict[str, Any] = {
        "ok": True,
        "status": "validated",
        "will_run": False,
        "can_run": True,
        "scope": _scope_display(request.scope),
        "scope_key": request.scope.key,
        "affiliate": request.scope.affiliate,
        "workplace": request.scope.workplace,
        "period": request.scope.period,
        "input_type": resolved_input_type,
        "requested_input_type": request.input_type,
        "tenant_id": request.tenant_id or "",
        "paths": paths,
        "metadata_keys": sorted(str(key) for key in request.metadata.keys()),
        "operation_policy": operation_policy,
        "operation_policy_source": operation_policy_source,
        "warnings": [],
        "error_code": "",
        "details": {},
        "error": "",
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def _api_error_code(exc: Exception) -> str:
    code = getattr(exc, "code", "")
    return str(code or "validation_error")


def _api_error_details(exc: Exception) -> dict[str, Any]:
    details = getattr(exc, "details", {})
    return dict(details) if isinstance(details, Mapping) else {}


def payroll_api_error_response(
    exc: Exception,
    *,
    request_id: str = "",
) -> dict[str, Any]:
    message = str(exc) or "급여 자동화 요청을 처리할 수 없습니다."
    payload: dict[str, Any] = {
        "ok": False,
        "status": "error",
        "will_run": False,
        "can_run": False,
        "error_code": _api_error_code(exc),
        "error": message,
        "warnings": [message],
        "details": _api_error_details(exc),
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def validate_payroll_api_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate an API payload without running payroll calculation."""
    request_id = _request_id(payload)
    try:
        request = build_payroll_api_request(payload)
    except ValueError as exc:
        return payroll_api_error_response(exc, request_id=request_id)
    return payroll_api_validation_response(request, request_id=request_id)


def run_payroll_api(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Framework-neutral API entrypoint for payroll automation."""
    request_id = _request_id(payload)
    try:
        request = build_payroll_api_request(payload)
    except ValueError as exc:
        return payroll_api_error_response(exc, request_id=request_id)
    if _validate_only(payload):
        return payroll_api_validation_response(request, request_id=request_id)
    return payroll_api_response(run_payroll_automation(request), request_id=request_id)
