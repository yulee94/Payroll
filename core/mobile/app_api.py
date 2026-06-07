"""Framework-neutral Bitween worker mobile API.

These functions are deliberately plain Python so a future FastAPI/Flask/Rust
HTTP layer can wrap the same contracts without coupling mobile behavior to a
desktop UI runtime.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

from core.mobile import store, sync, workflow_bridge
from core.mobile.models import (
    AttendanceEvent,
    EmployeeDevice,
    GeofenceAlert,
    MobileConsentRecord,
)
from core.roles import ROLE_ADMIN, ROLE_FINANCE, normalize_role
from core.session_service import UserSession
from core.user_store import authenticate_credentials, get_user
from core.workflow.constants import DOC_TYPE_ATTENDANCE

MOBILE_API_VERSION = "v1"
REQUIRED_ATTENDANCE_CONSENTS = ("privacy", "location", "biometric", "notifications")
REQUIRED_PAYROLL_CONSENTS = REQUIRED_ATTENDANCE_CONSENTS + ("payroll",)
DEVICE_BIOMETRIC_REF_PREFIX = "device://local-auth/"


def mobile_api_contract() -> dict[str, Any]:
    """Stable contract metadata for future HTTP/Rust wrappers."""
    return {
        "version": MOBILE_API_VERSION,
        "auth": {
            "type": "Bearer",
            "tenant_header": "X-Bitween-Tenant",
            "token_storage": "mobile_sessions.token_hash",
        },
        "privacy_defaults": {
            "biometric_storage": "device_only_pass_fail",
            "location_collection": "check_in_out_plus_shift_geofence",
            "payroll_visibility": "own_employee_only",
            "required_consents": list(REQUIRED_PAYROLL_CONSENTS),
        },
        "endpoints": [
            {"method": "POST", "path": "/mobile/v1/auth/login", "handler": "mobile_login"},
            {"method": "POST", "path": "/mobile/v1/devices/register", "handler": "register_mobile_device"},
            {"method": "POST", "path": "/mobile/v1/consents", "handler": "record_mobile_consents"},
            {"method": "GET", "path": "/mobile/v1/me", "handler": "get_mobile_me"},
            {"method": "GET", "path": "/mobile/v1/geofence/current", "handler": "get_current_geofence"},
            {"method": "POST", "path": "/mobile/v1/attendance/check", "handler": "mobile_check_attendance"},
            {"method": "POST", "path": "/mobile/v1/location/geofence-event", "handler": "mobile_geofence_event"},
            {"method": "GET", "path": "/mobile/v1/payroll/{period}", "handler": "get_mobile_payroll_summary"},
            {"method": "GET", "path": "/mobile/v1/hr/documents", "handler": "list_mobile_hr_documents"},
            {"method": "POST", "path": "/mobile/v1/hr/documents", "handler": "upload_mobile_hr_document"},
            {"method": "POST", "path": "/mobile/v1/hr/documents/{id}/permission-requests", "handler": "request_mobile_hr_document_permission"},
            {"method": "POST", "path": "/mobile/v1/hr/documents/{id}/delete-requests", "handler": "request_mobile_hr_document_delete"},
            {"method": "POST", "path": "/mobile/v1/hr/notifications/{id}/ack", "handler": "ack_mobile_hr_document_notification"},
            {"method": "POST", "path": "/mobile/v1/requests", "handler": "create_mobile_attendance_request"},
            {"method": "POST", "path": "/mobile/v1/absence-windows/sync", "handler": "sync_mobile_absence_windows"},
            {"method": "GET", "path": "/mobile/v1/manager/alerts", "handler": "list_mobile_manager_alerts"},
            {"method": "POST", "path": "/mobile/v1/manager/alerts/{id}/ack", "handler": "ack_mobile_alert"},
        ],
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _employee_name_for_session(sess: UserSession) -> str:
    rec = get_user(sess.user_id)
    return (rec.display_name if rec else sess.display_name).strip()


def _session_payload(sess: UserSession) -> dict[str, Any]:
    return {
        "user_id": sess.user_id,
        "tenant_id": sess.tenant_id,
        "username": sess.username,
        "display_name": sess.display_name,
        "role": normalize_role(sess.role),
        "employee_name": _employee_name_for_session(sess),
    }


def mobile_login(payload: dict[str, Any]) -> dict[str, Any]:
    """Authenticate a Bitween account and issue a mobile bearer token."""
    rec = authenticate_credentials(
        str(payload.get("username") or ""),
        str(payload.get("password") or ""),
        preferred_tenant_id=str(payload.get("tenant_id") or payload.get("tenantId") or "") or None,
    )
    sess = UserSession.from_record(rec)
    token = secrets.token_urlsafe(32)
    store.save_mobile_session(
        {
            "token_hash": _token_hash(token),
            "user_id": rec.user_id,
            "username": rec.username,
            "employee_name": rec.display_name,
            "tenant_id": rec.tenant_id,
            "device_uid": str(payload.get("device_uid") or payload.get("deviceUid") or ""),
            "created_at": _now_iso(),
            "revoked_at": "",
        },
        rec.tenant_id,
    )
    return {
        "version": MOBILE_API_VERSION,
        "token": token,
        "token_type": "Bearer",
        "user": _session_payload(sess),
        "required_consents": list(REQUIRED_PAYROLL_CONSENTS),
    }


def require_mobile_session(
    *,
    tenant_id: str,
    token: str,
) -> UserSession:
    """Validate a mobile bearer token and return a Bitween session object."""
    tid = str(tenant_id or "").strip()
    thash = _token_hash(token)
    for row in store.list_mobile_sessions(tid):
        if row.get("token_hash") != thash:
            continue
        if row.get("revoked_at"):
            break
        rec = get_user(str(row.get("user_id") or ""))
        if rec is None or rec.tenant_id != tid:
            break
        return UserSession.from_record(rec)
    raise PermissionError("모바일 로그인이 필요합니다.")


def mobile_logout(*, tenant_id: str, token: str) -> dict[str, Any]:
    changed = store.revoke_mobile_session(_token_hash(token), tenant_id)
    return {"ok": bool(changed)}


def _require_consents(
    sess: UserSession,
    *,
    tenant_id: str,
    required: tuple[str, ...],
) -> None:
    latest = store.latest_consents_for_user(sess.user_id, tenant_id)
    missing = [
        kind
        for kind in required
        if kind not in latest or not latest[kind].granted or latest[kind].revoked_at
    ]
    if missing:
        raise PermissionError("필수 동의가 필요합니다: " + ", ".join(missing))


def record_mobile_consents(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    employee_name = _employee_name_for_session(sess)
    device_uid = str(payload.get("device_uid") or payload.get("deviceUid") or "")
    device = store.find_device(device_uid, tenant_id=tenant_id, employee_name=employee_name)
    rows = payload.get("consents") or payload.get("items") or []
    if not isinstance(rows, list):
        raise ValueError("consents must be a list")
    saved: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        consent = MobileConsentRecord(
            id="",
            user_id=sess.user_id,
            employee_name=employee_name,
            consent_kind=str(raw.get("kind") or raw.get("consent_kind") or "privacy"),  # type: ignore[arg-type]
            granted=bool(raw.get("granted", True)),
            granted_at=str(raw.get("granted_at") or _now_iso()),
            locale=str(raw.get("locale") or payload.get("locale") or "ko-KR"),
            policy_version=str(raw.get("policy_version") or payload.get("policy_version") or "2026-06-04"),
            device_id=device.id if device else device_uid,
        )
        saved.append(store.record_consent(consent, tenant_id).to_dict())
    return {"ok": True, "consents": saved}


def register_mobile_device(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    employee_name = _employee_name_for_session(sess)
    device_uid = str(payload.get("device_uid") or payload.get("deviceUid") or "").strip()
    if not device_uid:
        raise ValueError("device_uid is required")
    platform = str(payload.get("platform") or "").strip().lower()
    if platform not in ("android", "ios"):
        raise ValueError("platform must be android or ios")
    device = EmployeeDevice(
        id="",
        user_id=sess.user_id,
        employee_name=employee_name,
        device_uid=device_uid,
        platform=platform,
        push_token=str(payload.get("push_token") or payload.get("pushToken") or ""),
        app_version=str(payload.get("app_version") or payload.get("appVersion") or ""),
        os_version=str(payload.get("os_version") or payload.get("osVersion") or ""),
        registered_at=_now_iso(),
        last_seen_at=_now_iso(),
        active=True,
    )
    saved = store.upsert_device(device, tenant_id)
    return {"ok": True, "device": saved.to_dict()}


def get_mobile_me(*, tenant_id: str, token: str) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    latest = store.latest_consents_for_user(sess.user_id, tenant_id)
    return {
        "version": MOBILE_API_VERSION,
        "user": _session_payload(sess),
        "consents": {k: v.to_dict() for k, v in latest.items()},
    }


def _require_document_consents(sess: UserSession, *, tenant_id: str) -> None:
    _require_consents(sess, tenant_id=tenant_id, required=("privacy", "notifications"))


def list_mobile_hr_documents(
    *,
    tenant_id: str,
    token: str,
    current_only: bool = True,
) -> dict[str, Any]:
    """List HR documents visible to the logged-in mobile user."""

    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_document_consents(sess, tenant_id=tenant_id)
    from core.hr.employee_documents import service as doc_svc

    docs = doc_svc.list_employee_documents(tenant_id=tenant_id, session=sess, current_only=current_only)
    notices = [
        n
        for n in doc_svc.list_notifications(tenant_id=tenant_id, unread_only=True)
        if not n.get("employee_user_id") or n.get("employee_user_id") == sess.user_id or "employee" in set(n.get("target_roles") or [])
    ]
    return {"documents": docs, "notifications": notices}


def _payload_file_bytes(payload: dict[str, Any]) -> bytes:
    raw = payload.get("file_bytes")
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    b64 = payload.get("file_base64") or payload.get("fileBase64")
    if b64:
        return base64.b64decode(str(b64))
    raise ValueError("file_bytes 또는 file_base64가 필요합니다.")


def upload_mobile_hr_document(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    """Upload an employee HR document from mobile; HR approval is still required."""

    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_document_consents(sess, tenant_id=tenant_id)
    from core.hr.employee_documents import service as doc_svc

    employee_name = _employee_name_for_session(sess)
    row = doc_svc.upload_document(
        tenant_id=tenant_id,
        session=sess,
        employee_id=str(payload.get("employee_id") or payload.get("employeeId") or sess.user_id),
        employee_user_id=sess.user_id,
        employee_name=str(payload.get("employee_name") or payload.get("employeeName") or employee_name),
        department=str(payload.get("department") or ""),
        position=str(payload.get("position") or ""),
        employment_type=str(payload.get("employment_type") or payload.get("employmentType") or ""),
        document_type=str(payload.get("document_type") or payload.get("documentType") or ""),
        document_name=str(payload.get("document_name") or payload.get("documentName") or ""),
        file_bytes=_payload_file_bytes(payload),
        file_name=str(payload.get("file_name") or payload.get("fileName") or "mobile-upload.pdf"),
        issued_date=str(payload.get("issued_date") or payload.get("issuedDate") or ""),
        start_date=str(payload.get("start_date") or payload.get("startDate") or ""),
        expiry_date=str(payload.get("expiry_date") or payload.get("expiryDate") or ""),
        memo=str(payload.get("memo") or "mobile upload"),
    )
    return {"ok": True, "document": row, "requires_approval": row.get("status") == doc_svc.STATUS_REVIEW_REQUIRED}


def request_mobile_hr_document_permission(
    document_id: str,
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_document_consents(sess, tenant_id=tenant_id)
    from core.hr.employee_documents import service as doc_svc

    row = doc_svc.request_document_permission(
        document_id,
        tenant_id=tenant_id,
        session=sess,
        reason=str(payload.get("reason") or ""),
        scopes=payload.get("scopes") or ("unmasked_view",),
        duration_hours=int(payload.get("duration_hours") or payload.get("durationHours") or 24),
    )
    return {"ok": True, "request": row}


def request_mobile_hr_document_delete(
    document_id: str,
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_document_consents(sess, tenant_id=tenant_id)
    from core.hr.employee_documents import service as doc_svc

    row = doc_svc.request_delete_document(
        document_id,
        tenant_id=tenant_id,
        session=sess,
        reason=str(payload.get("reason") or ""),
    )
    return {"ok": True, "request": row}


def ack_mobile_hr_document_notification(
    notification_id: str,
    *,
    tenant_id: str,
    token: str,
    action_note: str = "",
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_document_consents(sess, tenant_id=tenant_id)
    from core.hr.employee_documents import service as doc_svc

    row = doc_svc.acknowledge_notification(
        notification_id,
        tenant_id=tenant_id,
        session=sess,
        action_note=action_note,
    )
    return {"ok": True, "notification": row}


def get_current_geofence(
    *,
    tenant_id: str,
    token: str,
    site_name: str = "",
) -> dict[str, Any]:
    require_mobile_session(tenant_id=tenant_id, token=token)
    geofence = store.find_geofence(site_name, tenant_id) if site_name else None
    if geofence is None:
        fences = store.list_geofences(tenant_id)
        geofence = fences[0] if fences else None
    return {"geofence": geofence.to_dict() if geofence else None}


def _require_registered_device(
    *,
    tenant_id: str,
    sess: UserSession,
    device_uid: str,
) -> EmployeeDevice:
    employee_name = _employee_name_for_session(sess)
    device = store.find_device(device_uid, tenant_id=tenant_id, employee_name=employee_name)
    if device is None:
        raise PermissionError("등록된 모바일 기기에서만 사용할 수 있습니다.")
    return device


def mobile_check_attendance(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    """Check in/out with registered device, geofence, and OS biometric attestation."""
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_consents(sess, tenant_id=tenant_id, required=REQUIRED_ATTENDANCE_CONSENTS)
    device_uid = str(payload.get("device_uid") or payload.get("deviceUid") or "")
    device = _require_registered_device(tenant_id=tenant_id, sess=sess, device_uid=device_uid)
    event_type = str(payload.get("event_type") or payload.get("eventType") or "")
    if event_type not in ("clock_in", "clock_out"):
        raise ValueError("event_type must be clock_in or clock_out")
    biometric_ok = bool(payload.get("biometric_ok") or payload.get("biometricOk"))
    biometric_kind = str(payload.get("biometric_kind") or payload.get("biometricKind") or "none")
    if biometric_kind not in ("fingerprint", "face"):
        raise PermissionError("출퇴근에는 지문 또는 Face ID/Touch ID 인증이 필요합니다.")
    if not biometric_ok:
        raise PermissionError("생체인증에 실패했습니다.")
    biometric_ref = str(payload.get("biometric_ref") or payload.get("biometricRef") or "")
    if not biometric_ref:
        biometric_ref = f"{DEVICE_BIOMETRIC_REF_PREFIX}{device.platform}/{device.id}"
    event = AttendanceEvent.from_dict(
        {
            **payload,
            "employee_name": _employee_name_for_session(sess),
            "user_id": sess.user_id,
            "device_id": device.id,
            "device_uid": device.device_uid,
            "event_type": event_type,
            "event_at": str(payload.get("event_at") or payload.get("eventAt") or _now_iso()),
            "biometric_kind": biometric_kind,
            "biometric_ref": biometric_ref,
            "biometric_ok": True,
        }
    )
    saved = sync.ingest_attendance_event(event.to_dict(), tenant_id=tenant_id)
    return {"ok": saved.status == "verified", "event": saved.to_dict()}


def _is_checked_in(*, tenant_id: str, employee_name: str, user_id: str = "") -> bool:
    events = store.list_events(tenant_id=tenant_id, employee_name=employee_name, status="verified")
    if user_id and any(e.user_id == user_id for e in events):
        events = [e for e in events if e.user_id == user_id]
    if not events:
        return False
    last = sorted(events, key=lambda e: e.event_at)[-1]
    return last.event_type == "clock_in"


def mobile_geofence_event(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_consents(sess, tenant_id=tenant_id, required=REQUIRED_ATTENDANCE_CONSENTS)
    device_uid = str(payload.get("device_uid") or payload.get("deviceUid") or "")
    device = _require_registered_device(tenant_id=tenant_id, sess=sess, device_uid=device_uid)
    employee_name = _employee_name_for_session(sess)
    transition = str(payload.get("transition") or "heartbeat")
    if transition not in ("enter", "exit", "heartbeat"):
        raise ValueError("transition must be enter, exit, or heartbeat")
    site_name = str(payload.get("site_name") or payload.get("siteName") or "")
    detected_at = str(payload.get("detected_at") or payload.get("detectedAt") or _now_iso())
    active_window = workflow_bridge.find_active_absence_window(
        tenant_id=tenant_id,
        employee_name=employee_name,
        at=detected_at,
        site_name=site_name,
    )
    if transition == "enter":
        resolved: list[dict[str, Any]] = []
        for alert in store.list_geofence_alerts(
            tenant_id=tenant_id,
            employee_name=employee_name,
            status="open",
        ):
            if site_name and alert.site_name != site_name:
                continue
            resolved.append(
                store.update_geofence_alert(
                    alert.id,
                    {"status": "resolved", "resolved_at": detected_at},
                    tenant_id=tenant_id,
                ).to_dict()
            )
        return {"ok": True, "authorized": True, "resolved_alerts": resolved}
    if transition != "exit" or not _is_checked_in(tenant_id=tenant_id, employee_name=employee_name, user_id=sess.user_id):
        return {"ok": True, "authorized": True, "alert": None, "reason": "not_checked_in"}
    if active_window is not None:
        return {
            "ok": True,
            "authorized": True,
            "alert": None,
            "absence_window": active_window.to_dict(),
        }
    rec = get_user(sess.user_id)
    alert = GeofenceAlert(
        id="",
        employee_name=employee_name,
        user_id=sess.user_id,
        device_id=device.id,
        site_name=site_name,
        transition="exit",
        detected_at=detected_at,
        latitude=float(payload.get("latitude") or 0),
        longitude=float(payload.get("longitude") or 0),
        manager_user_id=rec.manager_user_id if rec else "",
        department_id=rec.org_unit_id if rec else "",
        worker_warning_sent=True,
        manager_alert_sent=True,
        note="근무시간 중 승인 없는 근무지 이탈",
    )
    saved = store.append_geofence_alert(alert, tenant_id)
    return {"ok": True, "authorized": False, "alert": saved.to_dict()}


def create_mobile_attendance_request(
    payload: dict[str, Any],
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    """Create and submit a Bitween attendance workflow request from mobile."""
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    from core.workflow import service as wf_svc

    employee_name = _employee_name_for_session(sess)
    values = dict(payload)
    values.setdefault("employee_name", employee_name)
    title = str(values.get("title") or values.get("request_type") or values.get("attendance_type") or "근태신청")
    summary = str(values.get("reason") or values.get("summary") or title)
    doc = wf_svc.create_document(
        tenant_id,
        document_type=DOC_TYPE_ATTENDANCE,
        title=title,
        summary=summary,
        content=summary,
        period_start=str(values.get("start_at") or values.get("period_start") or ""),
        period_end=str(values.get("end_at") or values.get("period_end") or ""),
        payload=values,
        session=sess,
    )
    requester = get_user(sess.user_id)
    manager_id = str(values.get("approver_id") or values.get("manager_user_id") or (requester.manager_user_id if requester else ""))
    submitted = doc
    if manager_id:
        submitted = wf_svc.submit_document(
            tenant_id,
            doc["id"],
            [{"approver_id": manager_id, "approver_role": "department_manager"}],
            session=sess,
        )
    return {
        "ok": True,
        "document": submitted,
        "submitted": bool(manager_id),
        "requires_approval": True,
    }


def sync_mobile_absence_windows(*, tenant_id: str, token: str) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    windows = workflow_bridge.sync_approved_attendance_windows(tenant_id, session=sess)
    return {"ok": True, "windows": [w.to_dict() for w in windows]}


def list_mobile_manager_alerts(
    *,
    tenant_id: str,
    token: str,
    status: str = "open",
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    role = normalize_role(sess.role)
    manager_filter = "" if role in (ROLE_ADMIN, ROLE_FINANCE) else sess.user_id
    alerts = store.list_geofence_alerts(
        tenant_id=tenant_id,
        status=status,
        manager_user_id=manager_filter,
    )
    return {"alerts": [a.to_dict() for a in alerts]}


def ack_mobile_alert(
    alert_id: str,
    *,
    tenant_id: str,
    token: str,
    comment: str = "",
) -> dict[str, Any]:
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    alert = store.update_geofence_alert(
        alert_id,
        {
            "status": "acknowledged",
            "acknowledged_by": sess.user_id,
            "acknowledged_at": _now_iso(),
            "note": comment or "관리자 확인",
        },
        tenant_id=tenant_id,
    )
    return {"ok": True, "alert": alert.to_dict()}


def _load_payroll_records_for_mobile(
    period: str,
    tenant_id: str,
    *,
    session: UserSession,
) -> list[dict[str, Any]]:
    """Optional payroll snapshot dependency seam for mobile self-service."""

    try:
        from core.access_control import load_payroll_records_secured

        return list(load_payroll_records_secured(period, tenant_id, session=session))
    except Exception:
        return []


def get_mobile_payroll_summary(
    period: str,
    *,
    tenant_id: str,
    token: str,
) -> dict[str, Any]:
    """Return only the logged-in worker's finalized or current estimate payroll."""
    sess = require_mobile_session(tenant_id=tenant_id, token=token)
    _require_consents(sess, tenant_id=tenant_id, required=REQUIRED_PAYROLL_CONSENTS)
    employee_name = _employee_name_for_session(sess)
    records: list[dict[str, Any]] = []
    try:
        from roster_constants import norm_name_key

        key = norm_name_key(employee_name)
        records = [
            r for r in _load_payroll_records_for_mobile(period, tenant_id, session=sess)
            if norm_name_key(r.get("name")) == key
        ]
    except Exception:
        records = []
    if records:
        rec = records[0]
        income_tax = int(rec.get("income_tax") or rec.get("tax") or 0)
        local_tax = int(rec.get("local_income_tax") or rec.get("local_tax") or 0)
        return {
            "period": period,
            "status": "finalized",
            "employee_name": employee_name,
            "gross_pay": int(rec.get("gross_pay") or 0),
            "net_pay": int(rec.get("net_pay") or 0),
            "total_deduction": int(rec.get("total_deduction") or 0),
            "tax": income_tax + local_tax,
            "remaining_leave": float(rec.get("remaining_annual_leave") or 0),
            "work_hours": float(rec.get("work_hours") or 0),
            "source": "payroll_snapshot",
        }

    from core.mobile import payroll_source

    summaries = [
        s
        for s in payroll_source.aggregate_period_hours(period, tenant_id=tenant_id)
        if s.employee_name == employee_name
    ]
    work_hours = sum(float(s.work_hours or 0) for s in summaries)
    work_days = sum(float(s.work_days or 0) for s in summaries)
    leave_days = sum(float(s.leave_days or 0) for s in summaries)
    return {
        "period": period,
        "status": "estimate",
        "employee_name": employee_name,
        "gross_pay": 0,
        "net_pay": 0,
        "total_deduction": 0,
        "tax": 0,
        "remaining_leave": 0,
        "work_hours": work_hours,
        "work_days": work_days,
        "leave_days": leave_days,
        "source": "attendance_mobile",
        "estimate_notice": "현재월 추정치이며 EDI 보험료·세금·관리자 검토 후 확정 급여와 달라질 수 있습니다.",
    }
