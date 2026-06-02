"""
core/roles.py - Bitween 사용자 권한 역할
"""

from __future__ import annotations

ROLE_STAFF = "staff"
ROLE_FINANCE = "finance"
ROLE_ADMIN = "admin"

ROLE_CHOICES: tuple[str, ...] = (ROLE_STAFF, ROLE_FINANCE, ROLE_ADMIN)

ROLE_LABELS: dict[str, str] = {
    ROLE_STAFF: "일반 사용자",
    ROLE_FINANCE: "재무팀",
    ROLE_ADMIN: "관리자",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_STAFF: "임원 급여·명부·보고(개인) 조회 불가",
    ROLE_FINANCE: "임원 포함 전체 급여·명부·월별 보고 조회 가능",
    ROLE_ADMIN: "재무팀 권한 + 사용자 권한 설정",
}


def normalize_role(value: str | None) -> str:
    r = str(value or "").strip().lower()
    if r in ROLE_CHOICES:
        return r
    if r in ("user", "general", "일반"):
        return ROLE_STAFF
    if r in ("재무", "finance_team"):
        return ROLE_FINANCE
    return ROLE_STAFF


def role_label(role: str) -> str:
    return ROLE_LABELS.get(normalize_role(role), ROLE_LABELS[ROLE_STAFF])
