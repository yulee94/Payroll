"""
payroll_readiness.py - API/UI friendly payroll automation readiness snapshot.

The launcher displays this today, and a future HTTP layer can expose the same
payload as a lightweight readiness endpoint for frontend dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ReadinessStatus = Literal["ready", "attention", "pending", "error"]

_STATUS_ORDER: dict[ReadinessStatus, int] = {
    "ready": 0,
    "pending": 1,
    "attention": 2,
    "error": 3,
}


@dataclass(frozen=True)
class PayrollReadinessItem:
    id: str
    title: str
    value: str
    detail: str
    status: ReadinessStatus
    color: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "value": self.value,
            "detail": self.detail,
            "status": self.status,
            "color": self.color,
        }


def _active_tenant_id(tenant_id: str | None = None) -> str | None:
    if tenant_id:
        return str(tenant_id)
    try:
        from core.session_service import session_tenant_id

        return session_tenant_id()
    except Exception:
        return None


def _policy_item(tenant_id: str | None) -> PayrollReadinessItem:
    try:
        from services.payroll_policy_store import (
            INPUT_LABELS,
            operation_policy_source_label,
            resolve_payroll_operation_policy,
        )

        resolved = resolve_payroll_operation_policy("", tenant_id=tenant_id)
        policy = resolved.get("policy") if isinstance(resolved, dict) else {}
        source = operation_policy_source_label(str(resolved.get("source") or "global"))
        input_basis = str(policy.get("input_basis") or "")
        label = INPUT_LABELS.get(input_basis, input_basis or "청구서+근태 혼합")
        return PayrollReadinessItem(
            id="input_basis",
            title="입력 기준",
            value=label,
            detail=source,
            status="ready",
            color="#2563EB",
        )
    except Exception:
        return PayrollReadinessItem(
            id="input_basis",
            title="입력 기준",
            value="청구서+근태 혼합",
            detail="기본값",
            status="attention",
            color="#2563EB",
        )


def _roster_item() -> PayrollReadinessItem:
    try:
        from services.employee_roster_store import (
            canonical_roster_path,
            roster_exists,
            roster_updated_display,
        )

        path = canonical_roster_path()
        if roster_exists():
            return PayrollReadinessItem(
                id="roster",
                title="근로자 명부",
                value="준비됨",
                detail=roster_updated_display(),
                status="ready",
                color="#0D9488",
            )
        return PayrollReadinessItem(
            id="roster",
            title="근로자 명부",
            value="확인 필요",
            detail=str(path),
            status="attention",
            color="#B45309",
        )
    except Exception:
        return PayrollReadinessItem(
            id="roster",
            title="근로자 명부",
            value="확인 필요",
            detail="상태 조회 실패",
            status="error",
            color="#B45309",
        )


def _output_item() -> PayrollReadinessItem:
    try:
        from payroll_archive import list_payroll_periods

        periods = list_payroll_periods()
        if periods:
            return PayrollReadinessItem(
                id="payroll_outputs",
                title="산출 자료",
                value=f"{len(periods)}개 급여월",
                detail=str(periods[0]),
                status="ready",
                color="#7C3AED",
            )
        return PayrollReadinessItem(
            id="payroll_outputs",
            title="산출 자료",
            value="대기 중",
            detail="첫 청구서 업로드 필요",
            status="pending",
            color="#64748B",
        )
    except Exception:
        return PayrollReadinessItem(
            id="payroll_outputs",
            title="산출 자료",
            value="대기 중",
            detail="상태 조회 실패",
            status="error",
            color="#64748B",
        )


def _api_item() -> PayrollReadinessItem:
    try:
        from services.payroll_api_contract import PAYROLL_API_ENDPOINT, PAYROLL_API_VERSION

        detail = f"{PAYROLL_API_VERSION} · {PAYROLL_API_ENDPOINT}"
    except Exception:
        detail = "JSON 요청/응답 어댑터"
    return PayrollReadinessItem(
        id="api_contract",
        title="API 연결",
        value="준비됨",
        detail=detail,
        status="ready",
        color="#1F3864",
    )


def payroll_readiness_items(*, tenant_id: str | None = None) -> list[PayrollReadinessItem]:
    """Return stable readiness cards for payroll launcher/API surfaces."""
    tid = _active_tenant_id(tenant_id)
    return [_policy_item(tid), _roster_item(), _output_item(), _api_item()]


def payroll_readiness_cards(*, tenant_id: str | None = None) -> list[dict[str, str]]:
    return [item.as_dict() for item in payroll_readiness_items(tenant_id=tenant_id)]


def payroll_readiness_snapshot(*, tenant_id: str | None = None) -> dict[str, Any]:
    """Return a JSON-friendly summary for a future readiness API endpoint."""
    tid = _active_tenant_id(tenant_id)
    items = payroll_readiness_items(tenant_id=tid)
    worst = max((item.status for item in items), key=lambda s: _STATUS_ORDER[s])
    return {
        "ok": worst in ("ready", "pending"),
        "status": worst,
        "tenant_id": tid or "",
        "ready_count": sum(1 for item in items if item.status == "ready"),
        "attention_count": sum(1 for item in items if item.status in ("attention", "error")),
        "pending_count": sum(1 for item in items if item.status == "pending"),
        "items": [item.as_dict() for item in items],
    }
