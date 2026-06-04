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
_INPUT_TYPES = {"auto", "invoice", "attendance", "mixed"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _payload_mapping(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise TypeError("급여 자동화 요청은 dict 형태여야 합니다.")
    return payload


def _scope_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    raw_scope = payload.get("scope")
    if isinstance(raw_scope, Mapping):
        return raw_scope
    return payload


def _request_id(payload: Mapping[str, Any] | None) -> str:
    try:
        data = _payload_mapping(payload)
    except TypeError:
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
        raise ValueError("period는 YYYY-MM 형식이어야 합니다.")
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
            raise ValueError("scope 키 형식이 올바르지 않습니다.")
        return scope

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
        raise ValueError(f"scope 필드가 부족합니다: {', '.join(missing)}")
    if not _PERIOD_RE.match(period):
        raise ValueError("period는 YYYY-MM 형식이어야 합니다.")
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
        raise ValueError(f"지원하지 않는 급여 입력 방식입니다: {value}")
    return value  # type: ignore[return-value]


def build_payroll_api_request(payload: Mapping[str, Any] | None) -> PayrollAutomationRequest:
    """Convert a JSON-like payload into the internal automation request."""
    data = _payload_mapping(payload)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    return PayrollAutomationRequest(
        scope=scope_from_api_payload(data),
        invoice_path=_path_from_payload(data, "invoice_path", "invoicePath"),
        attendance_path=_path_from_payload(data, "attendance_path", "attendancePath"),
        input_type=_input_type_from_payload(data),
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
    if request_id:
        payload["request_id"] = request_id
    return payload


def payroll_api_error_response(
    exc: Exception,
    *,
    request_id: str = "",
) -> dict[str, Any]:
    message = str(exc) or "급여 자동화 요청을 처리할 수 없습니다."
    payload: dict[str, Any] = {
        "ok": False,
        "status": "error",
        "error": message,
        "warnings": [message],
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def run_payroll_api(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Framework-neutral API entrypoint for payroll automation."""
    request_id = _request_id(payload)
    try:
        request = build_payroll_api_request(payload)
    except (TypeError, ValueError) as exc:
        return payroll_api_error_response(exc, request_id=request_id)
    return payroll_api_response(run_payroll_automation(request), request_id=request_id)
