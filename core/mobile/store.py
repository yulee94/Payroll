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
    BiometricEnrollmentRef,
    EmployeeDevice,
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
    "seeded": False,
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return date.today().isoformat()


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
    db["attendance_events"] = [in_ev.to_dict(), out_ev.to_dict()]
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
        db.setdefault("attendance_events", []).append(event.to_dict())
        return event

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
