"""
payroll_automation.py - backend/API friendly payroll automation entrypoint.

This service keeps invoice, attendance, and mixed uploads behind one request
shape. The desktop UI can call it today, and a future API can call the same
function without knowing the Tkinter details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from services.attendance_import import extract_attendance_invoice_rows
from services.attendance_invoice_bridge import (
    attach_attendance_sheet,
    build_attendance_invoice_workbook,
)
from services.payroll_policy_store import INPUT_ATTENDANCE, INPUT_HYBRID, INPUT_INVOICE
from services.payroll_scope import PayrollScope

PayrollInputType = Literal["invoice", "attendance", "mixed", "auto"]


@dataclass(frozen=True)
class PayrollAutomationRequest:
    scope: PayrollScope
    invoice_path: Path | None = None
    attendance_path: Path | None = None
    input_type: PayrollInputType = "auto"
    tenant_id: str | None = None
    interactive_parent: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PayrollAutomationResult:
    ok: bool
    scope: PayrollScope
    input_type: str
    count: int = 0
    warnings: list[str] = field(default_factory=list)
    paths: dict[str, str] = field(default_factory=dict)
    payroll_audit: dict[str, Any] = field(default_factory=dict)
    roster: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    exception: Exception | None = field(default=None, repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "scope": self.scope.key,
            "affiliate": self.scope.affiliate,
            "workplace": self.scope.workplace,
            "period": self.scope.period,
            "input_type": self.input_type,
            "count": self.count,
            "warnings": list(self.warnings),
            "paths": dict(self.paths),
            "payroll_audit": dict(self.payroll_audit),
            "roster": dict(self.roster),
            "error": self.error,
        }


def _determine_input_type(request: PayrollAutomationRequest) -> str:
    if request.input_type != "auto":
        return request.input_type
    if request.invoice_path and request.attendance_path:
        return "mixed"
    if request.attendance_path:
        return "attendance"
    return "invoice"


def _policy_input_type(request: PayrollAutomationRequest) -> str:
    # Explicit callers, including the current desktop upload button, should keep
    # their requested path. Tenant/site policy only decides ambiguous API calls.
    if request.input_type != "auto":
        return request.input_type
    try:
        from services.payroll_policy_store import resolve_payroll_operation_policy

        policy = resolve_payroll_operation_policy(
            request.scope.workplace,
            tenant_id=request.tenant_id,
        )["policy"]
        basis = policy.get("input_basis")
        if basis == INPUT_ATTENDANCE:
            return "attendance"
        if basis == INPUT_HYBRID:
            return "mixed" if request.invoice_path and request.attendance_path else _determine_input_type(request)
        if basis == INPUT_INVOICE:
            return "invoice"
    except Exception:
        pass
    return _determine_input_type(request)


def _stringify_paths(paths: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (paths or {}).items():
        if isinstance(value, list):
            out[key] = ";".join(str(v) for v in value)
        elif value is not None:
            out[key] = str(value)
    return out


def _process_invoice_path(
    invoice_path: Path,
    request: PayrollAutomationRequest,
    *,
    input_type: str,
    extra_warnings: list[str] | None = None,
) -> PayrollAutomationResult:
    from main import process_invoice

    raw = process_invoice(
        invoice_path,
        request.scope,
        interactive_parent=request.interactive_parent,
    )
    warnings = list(raw.get("warnings") or [])
    if extra_warnings:
        warnings = list(extra_warnings) + warnings
    return PayrollAutomationResult(
        ok=True,
        scope=request.scope,
        input_type=input_type,
        count=int(raw.get("count") or 0),
        warnings=warnings,
        paths=_stringify_paths(raw.get("paths") or {}),
        payroll_audit=raw.get("payroll_audit") or {},
        roster=raw.get("roster") or {},
        raw=raw,
    )


def run_payroll_automation(request: PayrollAutomationRequest) -> PayrollAutomationResult:
    """Run payroll automation from invoice, attendance, or mixed inputs."""
    input_type = request.input_type
    try:
        input_type = _policy_input_type(request)
        invoice_path = Path(request.invoice_path) if request.invoice_path else None
        attendance_path = Path(request.attendance_path) if request.attendance_path else None

        if input_type == "invoice":
            if not invoice_path:
                raise ValueError("청구서 파일이 필요합니다.")
            return _process_invoice_path(invoice_path, request, input_type=input_type)

        if input_type == "attendance":
            if not attendance_path:
                raise ValueError("근태 파일이 필요합니다.")
            attendance = extract_attendance_invoice_rows(
                attendance_path,
                workplace=request.scope.workplace,
                tenant_id=request.tenant_id,
            )
            with TemporaryDirectory(prefix="bitween_attendance_payroll_") as tmp:
                generated = Path(tmp) / f"attendance_invoice_{request.scope.period}.xlsx"
                build_attendance_invoice_workbook(
                    attendance,
                    generated,
                    period=request.scope.period,
                    workplace=request.scope.workplace,
                )
                return _process_invoice_path(
                    generated,
                    request,
                    input_type=input_type,
                    extra_warnings=attendance.warnings,
                )

        if input_type == "mixed":
            if not invoice_path:
                if attendance_path:
                    fallback = PayrollAutomationRequest(
                        scope=request.scope,
                        attendance_path=attendance_path,
                        input_type="attendance",
                        tenant_id=request.tenant_id,
                        interactive_parent=request.interactive_parent,
                        metadata=dict(request.metadata),
                    )
                    return run_payroll_automation(fallback)
                raise ValueError("청구서 또는 근태 파일이 필요합니다.")
            if not attendance_path:
                return _process_invoice_path(invoice_path, request, input_type="invoice")
            attendance = extract_attendance_invoice_rows(
                attendance_path,
                workplace=request.scope.workplace,
                tenant_id=request.tenant_id,
            )
            with TemporaryDirectory(prefix="bitween_mixed_payroll_") as tmp:
                merged = Path(tmp) / f"mixed_invoice_{request.scope.period}.xlsx"
                attach_attendance_sheet(invoice_path, attendance, merged)
                return _process_invoice_path(
                    merged,
                    request,
                    input_type=input_type,
                    extra_warnings=attendance.warnings,
                )

        raise ValueError(f"지원하지 않는 급여 입력 방식입니다: {input_type}")
    except Exception as exc:
        return PayrollAutomationResult(
            ok=False,
            scope=request.scope,
            input_type=input_type,
            error=str(exc),
            warnings=[str(exc)],
            exception=exc,
        )


def run_invoice_payroll(
    invoice_path: Path | str,
    scope: PayrollScope,
    *,
    interactive_parent: Any = None,
    tenant_id: str | None = None,
) -> PayrollAutomationResult:
    return run_payroll_automation(
        PayrollAutomationRequest(
            scope=scope,
            invoice_path=Path(invoice_path),
            input_type="invoice",
            tenant_id=tenant_id,
            interactive_parent=interactive_parent,
        )
    )


def run_attendance_payroll(
    attendance_path: Path | str,
    scope: PayrollScope,
    *,
    tenant_id: str | None = None,
    interactive_parent: Any = None,
) -> PayrollAutomationResult:
    return run_payroll_automation(
        PayrollAutomationRequest(
            scope=scope,
            attendance_path=Path(attendance_path),
            input_type="attendance",
            tenant_id=tenant_id,
            interactive_parent=interactive_parent,
        )
    )


def run_mixed_payroll(
    invoice_path: Path | str,
    attendance_path: Path | str,
    scope: PayrollScope,
    *,
    tenant_id: str | None = None,
    interactive_parent: Any = None,
) -> PayrollAutomationResult:
    return run_payroll_automation(
        PayrollAutomationRequest(
            scope=scope,
            invoice_path=Path(invoice_path),
            attendance_path=Path(attendance_path),
            input_type="mixed",
            tenant_id=tenant_id,
            interactive_parent=interactive_parent,
        )
    )
