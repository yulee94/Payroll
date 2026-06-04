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
    payload["error_code"] = "" if result.ok else "payroll_run_failed"
    payload["details"] = {}
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
        "error_code": _api_error_code(exc),
        "error": message,
        "warnings": [message],
        "details": _api_error_details(exc),
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def run_payroll_api(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Framework-neutral API entrypoint for payroll automation."""
    request_id = _request_id(payload)
    try:
        request = build_payroll_api_request(payload)
    except ValueError as exc:
        return payroll_api_error_response(exc, request_id=request_id)
    return payroll_api_response(run_payroll_automation(request), request_id=request_id)
