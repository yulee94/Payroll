"""
core/mobile/store.py - 모바일 출퇴근 테넌트별 JSON 저장소

경로: {app_data_dir}/mobile/{tenant_id}/database.json
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Callable

from core.mobile.models import (
    AttendanceEvent,
    AuthorizedAbsenceWindow,
    BiometricEnrollmentRef,
    EmployeeDevice,
    GeofenceAlert,
    MobileConsentRecord,
    PeriodWorkSummary,
    SiteGeofence,
)
from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "mobile"

_EMPTY: dict[str, Any] = {
    "site_geofences": [],
    "employee_devices": [],
    "biometric_enrollments": [],
    "attendance_events": [],
    "period_summaries": [],
    "employee_profiles": [],
    "mobile_sessions": [],
    "consents": [],
    "authorized_absence_windows": [],
    "geofence_alerts": [],
    "seeded": False,
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return date.today().isoformat()


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_db(tenant_id: str | None = None) -> dict[str, Any]:
    return load_module_db(MODULE, tenant_id or _tid(), _EMPTY)


def save_db(data: dict[str, Any], tenant_id: str | None = None) -> None:
    save_module_db(MODULE, tenant_id or _tid(), data)


def mutate_db(
    mutator: Callable[[dict[str, Any]], Any],
    tenant_id: str | None = None,
) -> Any:
    return mutate_module_db(MODULE, tenant_id or _tid(), _EMPTY, mutator)


def ensure_seed(tenant_id: str | None = None) -> None:
    """데모용 지오펜스·기기·출퇴근 샘플."""
    tid = tenant_id or _tid()
    db = load_db(tid)
    if db.get("seeded"):
        return
    d = date.today()
    db.setdefault("site_geofences", [])
    if not db["site_geofences"]:
        db["site_geofences"] = [
            SiteGeofence(
                id=_new_id(),
                site_name="화성 정비사업장",
                latitude=37.1995,
                longitude=126.8312,
                radius_m=200,
                legal_entity="(주)코스",
                note="KPI sites 연동 예정",
            ).to_dict(),
            SiteGeofence(
                id=_new_id(),
                site_name="부산 현장 01",
                latitude=35.1796,
                longitude=129.0756,
                radius_m=180,
                legal_entity="(주)코스",
            ).to_dict(),
        ]
    dev_id = _new_id()
    db.setdefault("employee_devices", [])
    if not db["employee_devices"]:
        db["employee_devices"] = [
            EmployeeDevice(
                id=dev_id,
                employee_name="박철수",
                device_uid="demo-android-001",
                platform="android",
                registered_at=_today(),
                last_seen_at=_today(),
            ).to_dict(),
        ]
    else:
        first = EmployeeDevice.from_dict(db["employee_devices"][0])
        dev_id = first.id
    db.setdefault("biometric_enrollments", [])
    if not db["biometric_enrollments"]:
        db["biometric_enrollments"] = [
            BiometricEnrollmentRef(
                id=_new_id(),
                employee_name="박철수",
                kind="fingerprint",
                external_ref="vault://bio/demo/park001",
                enrolled_at=_today(),
            ).to_dict(),
        ]
    in_ev = AttendanceEvent(
        id=_new_id(),
        employee_name="박철수",
        site_name="화성 정비사업장",
        event_type="clock_in",
        event_at=f"{(d - timedelta(days=1)).isoformat()}T08:02:00",
        latitude=37.1996,
        longitude=126.8310,
        device_id=dev_id,
        biometric_kind="fingerprint",
        biometric_ref="vault://bio/demo/park001",
        geofence_ok=True,
        biometric_ok=True,
        status="verified",
    )
    out_ev = AttendanceEvent(
        id=_new_id(),
        employee_name="박철수",
        site_name="화성 정비사업장",
        event_type="clock_out",
        event_at=f"{(d - timedelta(days=1)).isoformat()}T17:05:00",
        latitude=37.1994,
        longitude=126.8313,
        device_id=dev_id,
        biometric_kind="fingerprint",
        biometric_ref="vault://bio/demo/park001",
        geofence_ok=True,
        biometric_ok=True,
        status="verified",
        work_minutes=483,
    )
    db.setdefault("attendance_events", [])
    if not db["attendance_events"]:
        db["attendance_events"] = [in_ev.to_dict(), out_ev.to_dict()]
    db.setdefault("employee_profiles", [])
    if not db["employee_profiles"]:
        db["employee_profiles"] = [
            {
                "employee_name": "박철수",
                "email": "park@example.com",
                "payslip_email": "park@example.com",
                "phone": "010-1234-5678",
                "bank_holder": "박철수",
                "bank_name": "국민은행",
                "bank_account": "123456-01-123456",
                "updated_at": _today(),
            }
        ]
    db["seeded"] = True
    save_db(db, tid)


def list_geofences(tenant_id: str | None = None) -> list[SiteGeofence]:
    ensure_seed(tenant_id)
    return [SiteGeofence.from_dict(r) for r in load_db(tenant_id).get("site_geofences") or []]


def find_geofence(site_name: str, tenant_id: str | None = None) -> SiteGeofence | None:
    key = site_name.strip()
    for g in list_geofences(tenant_id):
        if g.site_name == key and g.active:
            return g
    return None


def list_events(
    *,
    tenant_id: str | None = None,
    employee_name: str = "",
    period: str = "",
    status: str = "",
) -> list[AttendanceEvent]:
    ensure_seed(tenant_id)
    rows = load_db(tenant_id).get("attendance_events") or []
    out: list[AttendanceEvent] = []
    for raw in rows:
        ev = AttendanceEvent.from_dict(raw)
        if employee_name and ev.employee_name != employee_name:
            continue
        if period and not ev.event_at.startswith(period):
            continue
        if status and ev.status != status:
            continue
        out.append(ev)
    return out


def append_event(event: AttendanceEvent, tenant_id: str | None = None) -> AttendanceEvent:
    def mut(db: dict[str, Any]) -> AttendanceEvent:
        if not event.id:
            event.id = _new_id()
        if not event.created_at:
            event.created_at = _now_iso()
        db.setdefault("attendance_events", []).append(event.to_dict())
        return event

    return mutate_db(mut, tenant_id)


def upsert_device(device: EmployeeDevice, tenant_id: str | None = None) -> EmployeeDevice:
    """Register or refresh one Android/iOS worker device."""

    def mut(db: dict[str, Any]) -> EmployeeDevice:
        rows = list(db.get("employee_devices") or [])
        if not device.id:
            device.id = _new_id()
        if not device.registered_at:
            device.registered_at = _now_iso()
        device.last_seen_at = _now_iso()
        replaced = False
        for i, raw in enumerate(rows):
            existing = EmployeeDevice.from_dict(raw)
            if existing.device_uid == device.device_uid and existing.employee_name == device.employee_name:
                device.id = existing.id
                if not device.registered_at:
                    device.registered_at = existing.registered_at
                rows[i] = device.to_dict()
                replaced = True
                break
        if not replaced:
            rows.append(device.to_dict())
        db["employee_devices"] = rows
        return device

    return mutate_db(mut, tenant_id)


def find_device(
    device_uid: str,
    *,
    tenant_id: str | None = None,
    employee_name: str = "",
) -> EmployeeDevice | None:
    key = str(device_uid or "").strip()
    emp = str(employee_name or "").strip()
    if not key:
        return None
    for raw in load_db(tenant_id).get("employee_devices") or []:
        dev = EmployeeDevice.from_dict(raw)
        if dev.device_uid != key or not dev.active:
            continue
        if emp and dev.employee_name != emp:
            continue
        return dev
    return None


def save_mobile_session(session_row: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
    """Persist a hashed mobile bearer token row."""

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = dict(session_row)
        row.setdefault("id", _new_id())
        row.setdefault("created_at", _now_iso())
        db.setdefault("mobile_sessions", []).append(row)
        return row

    return mutate_db(mut, tenant_id)


def list_mobile_sessions(tenant_id: str | None = None) -> list[dict[str, Any]]:
    return [dict(r) for r in load_db(tenant_id).get("mobile_sessions") or [] if isinstance(r, dict)]


def revoke_mobile_session(token_hash: str, tenant_id: str | None = None) -> bool:
    key = str(token_hash or "")

    def mut(db: dict[str, Any]) -> bool:
        changed = False
        for row in db.get("mobile_sessions") or []:
            if row.get("token_hash") == key and not row.get("revoked_at"):
                row["revoked_at"] = _now_iso()
                changed = True
        return changed

    return mutate_db(mut, tenant_id)


def record_consent(consent: MobileConsentRecord, tenant_id: str | None = None) -> MobileConsentRecord:
    def mut(db: dict[str, Any]) -> MobileConsentRecord:
        if not consent.id:
            consent.id = _new_id()
        if not consent.granted_at:
            consent.granted_at = _now_iso()
        db.setdefault("consents", []).append(consent.to_dict())
        return consent

    return mutate_db(mut, tenant_id)


def latest_consents_for_user(user_id: str, tenant_id: str | None = None) -> dict[str, MobileConsentRecord]:
    out: dict[str, MobileConsentRecord] = {}
    for raw in load_db(tenant_id).get("consents") or []:
        consent = MobileConsentRecord.from_dict(raw)
        if consent.user_id != user_id:
            continue
        current = out.get(consent.consent_kind)
        if current is None or consent.granted_at >= current.granted_at:
            out[consent.consent_kind] = consent
    return out


def upsert_absence_window(
    window: AuthorizedAbsenceWindow,
    tenant_id: str | None = None,
) -> AuthorizedAbsenceWindow:
    def mut(db: dict[str, Any]) -> AuthorizedAbsenceWindow:
        rows = list(db.get("authorized_absence_windows") or [])
        if not window.id:
            window.id = window.document_id or _new_id()
        replaced = False
        for i, raw in enumerate(rows):
            existing = AuthorizedAbsenceWindow.from_dict(raw)
            if existing.id == window.id or (
                window.document_id and existing.document_id == window.document_id
            ):
                rows[i] = window.to_dict()
                replaced = True
                break
        if not replaced:
            rows.append(window.to_dict())
        db["authorized_absence_windows"] = rows
        return window

    return mutate_db(mut, tenant_id)


def list_absence_windows(
    *,
    tenant_id: str | None = None,
    employee_name: str = "",
    active_only: bool = True,
) -> list[AuthorizedAbsenceWindow]:
    out: list[AuthorizedAbsenceWindow] = []
    emp = str(employee_name or "").strip()
    for raw in load_db(tenant_id).get("authorized_absence_windows") or []:
        win = AuthorizedAbsenceWindow.from_dict(raw)
        if emp and win.employee_name != emp:
            continue
        if active_only and not win.active:
            continue
        out.append(win)
    return out


def append_geofence_alert(alert: GeofenceAlert, tenant_id: str | None = None) -> GeofenceAlert:
    def mut(db: dict[str, Any]) -> GeofenceAlert:
        if not alert.id:
            alert.id = _new_id()
        db.setdefault("geofence_alerts", []).append(alert.to_dict())
        return alert

    return mutate_db(mut, tenant_id)


def list_geofence_alerts(
    *,
    tenant_id: str | None = None,
    status: str = "",
    manager_user_id: str = "",
    employee_name: str = "",
) -> list[GeofenceAlert]:
    out: list[GeofenceAlert] = []
    for raw in load_db(tenant_id).get("geofence_alerts") or []:
        alert = GeofenceAlert.from_dict(raw)
        if status and alert.status != status:
            continue
        if manager_user_id and alert.manager_user_id != manager_user_id:
            continue
        if employee_name and alert.employee_name != employee_name:
            continue
        out.append(alert)
    return sorted(out, key=lambda a: a.detected_at, reverse=True)


def update_geofence_alert(
    alert_id: str,
    updates: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> GeofenceAlert:
    aid = str(alert_id or "").strip()

    def mut(db: dict[str, Any]) -> GeofenceAlert:
        for raw in db.get("geofence_alerts") or []:
            if raw.get("id") != aid:
                continue
            raw.update(updates)
            return GeofenceAlert.from_dict(raw)
        raise LookupError("지오펜스 알림을 찾을 수 없습니다.")

    return mutate_db(mut, tenant_id)


def upsert_period_summary(summary: PeriodWorkSummary, tenant_id: str | None = None) -> PeriodWorkSummary:
    def mut(db: dict[str, Any]) -> PeriodWorkSummary:
        rows = list(db.get("period_summaries") or [])
        key = (summary.employee_name, summary.period, summary.site_name)
        replaced = False
        for i, raw in enumerate(rows):
            s = PeriodWorkSummary.from_dict(raw)
            if (s.employee_name, s.period, s.site_name) == key:
                rows[i] = summary.to_dict()
                replaced = True
                break
        if not replaced:
            rows.append(summary.to_dict())
        db["period_summaries"] = rows
        return summary

    return mutate_db(mut, tenant_id)


def list_period_summaries(
    period: str,
    *,
    tenant_id: str | None = None,
    site_name: str = "",
) -> list[PeriodWorkSummary]:
    ensure_seed(tenant_id)
    out: list[PeriodWorkSummary] = []
    for raw in load_db(tenant_id).get("period_summaries") or []:
        s = PeriodWorkSummary.from_dict(raw)
        if s.period != period:
            continue
        if site_name and s.site_name != site_name:
            continue
        out.append(s)
    return out
