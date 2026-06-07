"""
core/mobile/sync.py - 모바일 → Bitween HR·급여 동기화 (스텁)

실제 HTTP 수신은 추후 API 레이어에서 ingest_attendance_event 를 호출합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.mobile.models import AttendanceEvent, BiometricEnrollmentRef, SiteGeofence
from core.mobile import store


def verify_geofence(event: AttendanceEvent, geofence: SiteGeofence | None) -> bool:
    if geofence is None:
        return False
    return geofence.contains(event.latitude, event.longitude)


def verify_biometric(
    event: AttendanceEvent,
    enrollments: list[BiometricEnrollmentRef],
) -> bool:
    if event.biometric_kind == "none":
        return False
    # Device-only biometric mode: mobile OS performs Face ID/Touch ID/fingerprint
    # and Bitween stores only an attestation reference, never a biometric template.
    if event.biometric_ok and str(event.biometric_ref or "").startswith("device://local-auth/"):
        return True
    for ref in enrollments:
        if not ref.active:
            continue
        if ref.employee_name != event.employee_name:
            continue
        if ref.kind != event.biometric_kind:
            continue
        if event.biometric_ref and ref.external_ref == event.biometric_ref:
            return True
    return False


def ingest_attendance_event(
    payload: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> AttendanceEvent:
    """
    모바일 앱이 전송한 출퇴근 1건 수신·검증·저장.

    location + biometric 모두 통과 시 status=verified.
    """
    store.ensure_seed(tenant_id)
    event = AttendanceEvent.from_dict(payload)
    if not event.id:
        from core.mobile.store import _new_id  # noqa: PLC0415

        event.id = _new_id()

    geofence = store.find_geofence(event.site_name, tenant_id)
    event.geofence_ok = verify_geofence(event, geofence)

    enrollments = [
        BiometricEnrollmentRef.from_dict(r)
        for r in store.load_db(tenant_id).get("biometric_enrollments") or []
    ]
    event.biometric_ok = verify_biometric(event, enrollments)

    if event.geofence_ok and event.biometric_ok:
        event.status = "verified"
    else:
        event.status = "rejected"
        parts: list[str] = []
        if not event.geofence_ok:
            parts.append("사업장 위치 불일치")
        if not event.biometric_ok:
            parts.append("생체인증 불일치")
        event.note = (event.note + " " + " · ".join(parts)).strip()

    return store.append_event(event, tenant_id)


def push_verified_to_hr(event: AttendanceEvent, *, tenant_id: str | None) -> dict[str, Any] | None:
    """검증된 이벤트를 HR 근태 탭에 미러 (수동 근태와 병행)."""
    if event.status != "verified" or event.synced_hr:
        return None
    from core.hr import service as hr_svc

    hr_type = "출근" if event.event_type == "clock_in" else "퇴근"
    day = event.event_at[:10]
    values = {
        "employee_name": event.employee_name,
        "date": day,
        "type": hr_type,
        "minutes": event.work_minutes if event.event_type == "clock_out" else 0,
        "status": "확인",
        "note": f"모바일({event.site_name})",
    }

    def mark_synced(db: dict[str, Any]) -> None:
        for raw in db.get("attendance_events") or []:
            if raw.get("id") == event.id:
                raw["synced_hr"] = True
                break

    store.mutate_db(mark_synced, tenant_id)
    return hr_svc.add_record("attendance", values)


def sync_pending_events(tenant_id: str | None = None) -> dict[str, int]:
    """verified 이벤트 중 HR 미동기화 건 일괄 반영."""
    stats = {"hr_pushed": 0, "rejected": 0, "pending": 0}
    for ev in store.list_events(tenant_id=tenant_id):
        if ev.status == "rejected":
            stats["rejected"] += 1
            continue
        if ev.status != "verified":
            stats["pending"] += 1
            continue
        if not ev.synced_hr:
            if push_verified_to_hr(ev, tenant_id=tenant_id):
                stats["hr_pushed"] += 1
    return stats


def pair_work_minutes(events: list[AttendanceEvent]) -> list[AttendanceEvent]:
    """
    동일 직원·일자 clock_in/out 쌍에서 work_minutes 계산 (퇴근 이벤트에 기록).
    """
    by_key: dict[tuple[str, str], list[AttendanceEvent]] = {}
    for ev in sorted(events, key=lambda e: e.event_at):
        day = ev.event_at[:10]
        by_key.setdefault((ev.employee_name, day), []).append(ev)

    updated: list[AttendanceEvent] = []
    for group in by_key.values():
        ins = [e for e in group if e.event_type == "clock_in" and e.status == "verified"]
        outs = [e for e in group if e.event_type == "clock_out" and e.status == "verified"]
        if ins and outs:
            try:
                t_in = datetime.fromisoformat(ins[0].event_at)
                t_out = datetime.fromisoformat(outs[-1].event_at)
                mins = max(0, int((t_out - t_in).total_seconds() / 60))
                outs[-1].work_minutes = mins
                updated.append(outs[-1])
            except ValueError:
                pass
    return updated
