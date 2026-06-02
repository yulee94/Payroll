"""
core/mobile/profile.py - 직원 모바일 셀프서비스 프로필 (계좌·이메일)

명부(bank_account·roster_constants)와 병행; 모바일 앱에서 수정 가능한 필드.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from bank_account import enrich_roster_bank_info
from core.mobile import store
from roster_constants import norm_name_key

# 모바일 프로필 필드 — roster_constants 확장과 동기
MOBILE_PROFILE_FIELDS = (
    "email",
    "payslip_email",
    "phone",
    "bank_holder",
    "bank_name",
    "bank_account",
)


def _today() -> str:
    return date.today().isoformat()


def _find_profile_row(db: dict[str, Any], employee_name: str) -> dict[str, Any] | None:
    key = norm_name_key(employee_name)
    for raw in db.get("employee_profiles") or []:
        if norm_name_key(raw.get("employee_name")) == key:
            return raw
    return None


def get_employee_mobile_profile(
    employee_name: str,
    *,
    tenant_id: str | None = None,
    roster_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    모바일 프로필 + 명부 계좌 정보 병합.

    roster_row 가 있으면 bank_account.enrich_roster_bank_info 결과를 기본값으로 사용.
    """
    store.ensure_seed(tenant_id)
    db = store.load_db(tenant_id)
    prof = _find_profile_row(db, employee_name) or {"employee_name": employee_name}

    out: dict[str, Any] = {
        "employee_name": employee_name,
        "email": prof.get("email") or "",
        "payslip_email": prof.get("payslip_email") or prof.get("email") or "",
        "phone": prof.get("phone") or "",
        "bank_holder": prof.get("bank_holder") or "",
        "bank_name": prof.get("bank_name") or "",
        "bank_account": prof.get("bank_account") or "",
        "updated_at": prof.get("updated_at") or "",
    }

    if roster_row:
        enriched = enrich_roster_bank_info(dict(roster_row))
        out["bank_holder"] = out["bank_holder"] or enriched.get("예금주") or employee_name
        out["bank_name"] = out["bank_name"] or enriched.get("은행명") or ""
        out["bank_account"] = out["bank_account"] or enriched.get("계좌번호") or ""
        out["phone"] = out["phone"] or str(enriched.get("휴대폰") or "")
        out["workplace"] = str(enriched.get("근무지") or "")
        out["leave_balance"] = enriched.get("잔여연차")
    return out


def update_employee_mobile_profile(
    employee_name: str,
    values: dict[str, str],
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """모바일 앱에서 수정한 프로필 저장."""

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        existing = _find_profile_row(db, employee_name)
        row = dict(existing) if existing else {"employee_name": employee_name}
        for field in MOBILE_PROFILE_FIELDS:
            if field in values:
                row[field] = str(values[field] or "").strip()
        row["updated_at"] = _today()
        profiles = list(db.get("employee_profiles") or [])
        key = norm_name_key(employee_name)
        replaced = False
        for i, raw in enumerate(profiles):
            if norm_name_key(raw.get("employee_name")) == key:
                profiles[i] = row
                replaced = True
                break
        if not replaced:
            profiles.append(row)
        db["employee_profiles"] = profiles
        return row

    return store.mutate_db(mut, tenant_id)


def apply_profile_to_roster_row(
    profile: dict[str, Any],
    roster_row: dict[str, Any],
) -> dict[str, Any]:
    """모바일 프로필 → 명부 행 반영 (선택적 동기화)."""
    out = dict(roster_row)
    mapping = {
        "email": "이메일",
        "payslip_email": "급여명세서이메일",
        "phone": "휴대폰",
        "bank_holder": "예금주",
        "bank_name": "은행명",
        "bank_account": "계좌번호",
    }
    for src, dst in mapping.items():
        val = str(profile.get(src) or "").strip()
        if val:
            out[dst] = val
    return out
