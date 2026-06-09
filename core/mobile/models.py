"""
core/mobile/models.py - 모바일 출퇴근·지오펜스·기기·생체인증 데이터 모델

REST API 레이어는 추후 추가; 현재는 데스크톱 Bitween과 동일한 JSON 저장소 패턴.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EventType = Literal["clock_in", "clock_out"]
BiometricKind = Literal["fingerprint", "face", "none"]
VerificationStatus = Literal["pending", "verified", "rejected"]
ConsentKind = Literal["location", "biometric", "payroll", "notifications", "privacy"]
GeofenceTransition = Literal["enter", "exit", "heartbeat"]
AlertStatus = Literal["open", "acknowledged", "resolved"]
PushEventKind = Literal[
    "work_assignment",
    "approval_request",
    "announcement",
    "incident",
    "inventory_movement",
    "reservation",
    "payment_settlement",
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 GPS 좌표 간 거리(미터)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class SiteGeofence:
    """사업장 GPS 지오펜스 — KPI sites·명부 근무지와 site_name 으로 연결."""

    id: str
    site_name: str
    latitude: float
    longitude: float
    radius_m: float = 150.0
    legal_entity: str = ""
    active: bool = True
    note: str = ""

    def contains(self, lat: float, lon: float) -> bool:
        if not self.active:
            return False
        return _haversine_m(self.latitude, self.longitude, lat, lon) <= self.radius_m

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SiteGeofence:
        return cls(
            id=str(raw.get("id") or ""),
            site_name=str(raw.get("site_name") or ""),
            latitude=float(raw.get("latitude") or 0),
            longitude=float(raw.get("longitude") or 0),
            radius_m=float(raw.get("radius_m") or 150),
            legal_entity=str(raw.get("legal_entity") or ""),
            active=bool(raw.get("active", True)),
            note=str(raw.get("note") or ""),
        )


@dataclass
class EmployeeDevice:
    """직원 모바일 기기 등록 — 푸시·세션·기기 무결성 추적용."""

    id: str
    employee_name: str
    device_uid: str
    user_id: str = ""
    branch_id: str = ""
    platform: str = "android"
    push_token: str = ""
    app_version: str = ""
    os_version: str = ""
    registered_at: str = ""
    last_seen_at: str = ""
    last_active_at: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EmployeeDevice:
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            device_uid=str(raw.get("device_uid") or ""),
            user_id=str(raw.get("user_id") or ""),
            branch_id=str(raw.get("branch_id") or ""),
            platform=str(raw.get("platform") or "android"),
            push_token=str(raw.get("push_token") or ""),
            app_version=str(raw.get("app_version") or ""),
            os_version=str(raw.get("os_version") or ""),
            registered_at=str(raw.get("registered_at") or ""),
            last_seen_at=str(raw.get("last_seen_at") or ""),
            last_active_at=str(raw.get("last_active_at") or raw.get("last_seen_at") or ""),
            active=bool(raw.get("active", True)),
        )


@dataclass
class BiometricEnrollmentRef:
    """
    생체인증 등록 참조 — 실제 템플릿/얼굴 벡터는 모바일·전용 KMS에 보관.
    Bitween에는 employee_name + kind + external_ref 만 저장.
    """

    id: str
    employee_name: str
    kind: BiometricKind
    external_ref: str
    enrolled_at: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> BiometricEnrollmentRef:
        kind = raw.get("kind") or "none"
        if kind not in ("fingerprint", "face", "none"):
            kind = "none"
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            kind=kind,  # type: ignore[arg-type]
            external_ref=str(raw.get("external_ref") or ""),
            enrolled_at=str(raw.get("enrolled_at") or ""),
            active=bool(raw.get("active", True)),
        )


@dataclass
class AttendanceEvent:
    """모바일 출퇴근 이벤트 — 위치·생체 검증 후 확정."""

    id: str
    employee_name: str
    site_name: str
    event_type: EventType
    event_at: str
    latitude: float
    longitude: float
    user_id: str = ""
    device_id: str = ""
    accuracy_m: float = 0.0
    biometric_kind: BiometricKind = "none"
    biometric_ref: str = ""
    geofence_ok: bool = False
    biometric_ok: bool = False
    approved_absence_window_id: str = ""
    violation_alert_id: str = ""
    status: VerificationStatus = "pending"
    work_minutes: int = 0
    note: str = ""
    synced_hr: bool = False
    synced_payroll: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AttendanceEvent:
        et = raw.get("event_type") or "clock_in"
        if et not in ("clock_in", "clock_out"):
            et = "clock_in"
        bk = raw.get("biometric_kind") or "none"
        if bk not in ("fingerprint", "face", "none"):
            bk = "none"
        st = raw.get("status") or "pending"
        if st not in ("pending", "verified", "rejected"):
            st = "pending"
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            site_name=str(raw.get("site_name") or ""),
            event_type=et,  # type: ignore[arg-type]
            event_at=str(raw.get("event_at") or ""),
            latitude=float(raw.get("latitude") or 0),
            longitude=float(raw.get("longitude") or 0),
            user_id=str(raw.get("user_id") or ""),
            device_id=str(raw.get("device_id") or ""),
            accuracy_m=float(raw.get("accuracy_m") or 0),
            biometric_kind=bk,  # type: ignore[arg-type]
            biometric_ref=str(raw.get("biometric_ref") or ""),
            geofence_ok=bool(raw.get("geofence_ok")),
            biometric_ok=bool(raw.get("biometric_ok")),
            approved_absence_window_id=str(raw.get("approved_absence_window_id") or ""),
            violation_alert_id=str(raw.get("violation_alert_id") or ""),
            status=st,  # type: ignore[arg-type]
            work_minutes=int(raw.get("work_minutes") or 0),
            note=str(raw.get("note") or ""),
            synced_hr=bool(raw.get("synced_hr")),
            synced_payroll=bool(raw.get("synced_payroll")),
            created_at=str(raw.get("created_at") or ""),
        )


@dataclass
class MobileConsentRecord:
    """Worker consent captured before mobile attendance/payroll use."""

    id: str
    user_id: str
    employee_name: str
    consent_kind: ConsentKind
    granted: bool
    granted_at: str
    locale: str = "ko-KR"
    policy_version: str = "2026-06-04"
    device_id: str = ""
    revoked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MobileConsentRecord:
        kind = str(raw.get("consent_kind") or raw.get("kind") or "privacy")
        if kind not in ("location", "biometric", "payroll", "notifications", "privacy"):
            kind = "privacy"
        return cls(
            id=str(raw.get("id") or ""),
            user_id=str(raw.get("user_id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            consent_kind=kind,  # type: ignore[arg-type]
            granted=bool(raw.get("granted")),
            granted_at=str(raw.get("granted_at") or ""),
            locale=str(raw.get("locale") or "ko-KR"),
            policy_version=str(raw.get("policy_version") or "2026-06-04"),
            device_id=str(raw.get("device_id") or ""),
            revoked_at=str(raw.get("revoked_at") or ""),
        )


@dataclass
class AuthorizedAbsenceWindow:
    """Approved workflow window that permits leaving the geofenced work area."""

    id: str
    employee_name: str
    start_at: str
    end_at: str
    request_type: str
    document_id: str = ""
    site_name: str = ""
    approved_by: str = ""
    approved_at: str = ""
    active: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AuthorizedAbsenceWindow:
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            start_at=str(raw.get("start_at") or ""),
            end_at=str(raw.get("end_at") or ""),
            request_type=str(raw.get("request_type") or ""),
            document_id=str(raw.get("document_id") or ""),
            site_name=str(raw.get("site_name") or ""),
            approved_by=str(raw.get("approved_by") or ""),
            approved_at=str(raw.get("approved_at") or ""),
            active=bool(raw.get("active", True)),
            note=str(raw.get("note") or ""),
        )


@dataclass
class GeofenceAlert:
    """Unauthorized work-area exit warning/manager alert."""

    id: str
    employee_name: str
    site_name: str
    transition: GeofenceTransition
    detected_at: str
    latitude: float
    longitude: float
    status: AlertStatus = "open"
    user_id: str = ""
    device_id: str = ""
    manager_user_id: str = ""
    department_id: str = ""
    worker_warning_sent: bool = False
    manager_alert_sent: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""
    resolved_at: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GeofenceAlert:
        transition = str(raw.get("transition") or "exit")
        if transition not in ("enter", "exit", "heartbeat"):
            transition = "exit"
        status = str(raw.get("status") or "open")
        if status not in ("open", "acknowledged", "resolved"):
            status = "open"
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            site_name=str(raw.get("site_name") or ""),
            transition=transition,  # type: ignore[arg-type]
            detected_at=str(raw.get("detected_at") or ""),
            latitude=float(raw.get("latitude") or 0),
            longitude=float(raw.get("longitude") or 0),
            status=status,  # type: ignore[arg-type]
            user_id=str(raw.get("user_id") or ""),
            device_id=str(raw.get("device_id") or ""),
            manager_user_id=str(raw.get("manager_user_id") or ""),
            department_id=str(raw.get("department_id") or ""),
            worker_warning_sent=bool(raw.get("worker_warning_sent")),
            manager_alert_sent=bool(raw.get("manager_alert_sent")),
            acknowledged_by=str(raw.get("acknowledged_by") or ""),
            acknowledged_at=str(raw.get("acknowledged_at") or ""),
            resolved_at=str(raw.get("resolved_at") or ""),
            note=str(raw.get("note") or ""),
        )


@dataclass
class MobilePushNotification:
    """Queued mobile push notification for FCM/APNs delivery."""

    id: str
    event_kind: PushEventKind
    title: str
    body: str
    user_id: str = ""
    branch_id: str = ""
    device_id: str = ""
    push_token: str = ""
    platform: str = "android"
    app_version: str = ""
    provider: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"
    created_at: str = ""
    sent_at: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MobilePushNotification:
        kind = str(raw.get("event_kind") or "announcement")
        if kind not in (
            "work_assignment",
            "approval_request",
            "announcement",
            "incident",
            "inventory_movement",
            "reservation",
            "payment_settlement",
        ):
            kind = "announcement"
        platform = str(raw.get("platform") or "android")
        if platform not in ("ios", "android"):
            platform = "android"
        return cls(
            id=str(raw.get("id") or ""),
            event_kind=kind,  # type: ignore[arg-type]
            title=str(raw.get("title") or ""),
            body=str(raw.get("body") or ""),
            user_id=str(raw.get("user_id") or ""),
            branch_id=str(raw.get("branch_id") or ""),
            device_id=str(raw.get("device_id") or ""),
            push_token=str(raw.get("push_token") or ""),
            platform=platform,
            app_version=str(raw.get("app_version") or ""),
            provider=str(raw.get("provider") or ""),
            payload=dict(raw.get("payload") or {}),
            status=str(raw.get("status") or "queued"),
            created_at=str(raw.get("created_at") or ""),
            sent_at=str(raw.get("sent_at") or ""),
            error=str(raw.get("error") or ""),
        )


@dataclass
class MobileOfflineSyncRecord:
    """Server-side idempotency record for one offline-created mobile request."""

    id: str
    request_id: str
    sync_id: str
    created_at: str
    device_id: str
    user_id: str = ""
    branch_id: str = ""
    request_type: str = ""
    payload_hash: str = ""
    status: str = "processed"
    result: dict[str, Any] = field(default_factory=dict)
    received_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MobileOfflineSyncRecord:
        return cls(
            id=str(raw.get("id") or ""),
            request_id=str(raw.get("request_id") or raw.get("requestId") or ""),
            sync_id=str(raw.get("sync_id") or raw.get("syncId") or ""),
            created_at=str(raw.get("created_at") or raw.get("createdAt") or ""),
            device_id=str(raw.get("device_id") or raw.get("deviceId") or ""),
            user_id=str(raw.get("user_id") or ""),
            branch_id=str(raw.get("branch_id") or ""),
            request_type=str(raw.get("request_type") or raw.get("requestType") or ""),
            payload_hash=str(raw.get("payload_hash") or ""),
            status=str(raw.get("status") or "processed"),
            result=dict(raw.get("result") or {}),
            received_at=str(raw.get("received_at") or ""),
        )


@dataclass
class PeriodWorkSummary:
    """월·사업장별 근무시간 집계 — 청구서 없이 급여 산출용."""

    employee_name: str
    period: str
    site_name: str
    work_days: float = 0.0
    work_hours: float = 0.0
    overtime_hours: float = 0.0
    night_hours: float = 0.0
    leave_days: float = 0.0
    source: str = "attendance_mobile"
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PeriodWorkSummary:
        return cls(
            employee_name=str(raw.get("employee_name") or ""),
            period=str(raw.get("period") or ""),
            site_name=str(raw.get("site_name") or ""),
            work_days=float(raw.get("work_days") or 0),
            work_hours=float(raw.get("work_hours") or 0),
            overtime_hours=float(raw.get("overtime_hours") or 0),
            night_hours=float(raw.get("night_hours") or 0),
            leave_days=float(raw.get("leave_days") or 0),
            source=str(raw.get("source") or "attendance_mobile"),
            event_ids=list(raw.get("event_ids") or []),
        )
