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
    platform: str = "android"
    registered_at: str = ""
    last_seen_at: str = ""
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EmployeeDevice:
        return cls(
            id=str(raw.get("id") or ""),
            employee_name=str(raw.get("employee_name") or ""),
            device_uid=str(raw.get("device_uid") or ""),
            platform=str(raw.get("platform") or "android"),
            registered_at=str(raw.get("registered_at") or ""),
            last_seen_at=str(raw.get("last_seen_at") or ""),
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
    device_id: str = ""
    biometric_kind: BiometricKind = "none"
    biometric_ref: str = ""
    geofence_ok: bool = False
    biometric_ok: bool = False
    status: VerificationStatus = "pending"
    work_minutes: int = 0
    note: str = ""
    synced_hr: bool = False
    synced_payroll: bool = False

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
            device_id=str(raw.get("device_id") or ""),
            biometric_kind=bk,  # type: ignore[arg-type]
            biometric_ref=str(raw.get("biometric_ref") or ""),
            geofence_ok=bool(raw.get("geofence_ok")),
            biometric_ok=bool(raw.get("biometric_ok")),
            status=st,  # type: ignore[arg-type]
            work_minutes=int(raw.get("work_minutes") or 0),
            note=str(raw.get("note") or ""),
            synced_hr=bool(raw.get("synced_hr")),
            synced_payroll=bool(raw.get("synced_payroll")),
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
