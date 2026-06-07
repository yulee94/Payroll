"""Workflow approvals → mobile authorized absence windows."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from core.mobile.models import AuthorizedAbsenceWindow
from core.mobile import store
from core.session_service import UserSession
from core.user_store import get_user
from core.workflow.constants import DOC_STATUS_APPROVED, DOC_TYPE_ATTENDANCE


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        try:
            return datetime.fromisoformat(raw[:10])
        except ValueError:
            return None


def _day_start(value: str) -> str:
    raw = str(value or "").strip()
    if "T" in raw:
        return raw
    dt = _parse_iso(raw)
    if dt is None:
        return raw
    return datetime.combine(dt.date(), time.min).isoformat()


def _day_end(value: str) -> str:
    raw = str(value or "").strip()
    if "T" in raw:
        return raw
    dt = _parse_iso(raw)
    if dt is None:
        return raw
    return datetime.combine(dt.date(), time.max.replace(microsecond=0)).isoformat()


def _window_from_document(doc: dict[str, Any]) -> AuthorizedAbsenceWindow | None:
    payload = doc.get("payload") if isinstance(doc.get("payload"), dict) else {}
    requester = get_user(str(doc.get("requester_id") or ""))
    employee_name = str(
        payload.get("employee_name")
        or payload.get("requester_name")
        or (requester.display_name if requester else "")
    ).strip()
    if not employee_name:
        return None
    start_raw = str(
        payload.get("start_at") or payload.get("period_start") or doc.get("period_start") or ""
    )
    end_raw = str(payload.get("end_at") or payload.get("period_end") or doc.get("period_end") or start_raw)
    start_at = _day_start(start_raw)
    end_at = _day_end(end_raw)
    if not start_at or not end_at:
        return None
    request_type = str(
        payload.get("attendance_type")
        or payload.get("request_type")
        or doc.get("category")
        or "other"
    )
    return AuthorizedAbsenceWindow(
        id=str(doc.get("id") or ""),
        employee_name=employee_name,
        start_at=start_at,
        end_at=end_at,
        request_type=request_type,
        document_id=str(doc.get("id") or ""),
        site_name=str(payload.get("site_name") or doc.get("site_id") or ""),
        approved_by=str(payload.get("approved_by") or ""),
        approved_at=str(doc.get("approved_at") or ""),
        active=doc.get("status") == DOC_STATUS_APPROVED,
        note=str(doc.get("title") or ""),
    )


def sync_approved_attendance_windows(
    tenant_id: str,
    *,
    session: UserSession,
) -> list[AuthorizedAbsenceWindow]:
    """Mirror approved attendance workflow documents into mobile absence windows."""
    from core.workflow import service as wf_svc

    docs = wf_svc.list_documents(
        tenant_id,
        session=session,
        status=DOC_STATUS_APPROVED,
        document_type=DOC_TYPE_ATTENDANCE,
    )
    synced: list[AuthorizedAbsenceWindow] = []
    for doc in docs:
        detailed = wf_svc.get_document(tenant_id, doc["id"], session=session)
        window = _window_from_document(detailed)
        if window is None:
            continue
        synced.append(store.upsert_absence_window(window, tenant_id))
    return synced


def find_active_absence_window(
    *,
    tenant_id: str,
    employee_name: str,
    at: str,
    site_name: str = "",
) -> AuthorizedAbsenceWindow | None:
    """Return an approved leave/trip/outing/sick window covering `at`."""
    target = _parse_iso(at)
    if target is None:
        return None
    for window in store.list_absence_windows(
        tenant_id=tenant_id,
        employee_name=employee_name,
        active_only=True,
    ):
        start = _parse_iso(window.start_at)
        end = _parse_iso(window.end_at)
        if start is None or end is None:
            continue
        if site_name and window.site_name and window.site_name != site_name:
            continue
        if start <= target <= end:
            return window
    return None
