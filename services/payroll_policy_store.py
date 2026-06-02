"""
payroll_policy_store.py - tenant/site payroll operation policy.

This module keeps payroll automation choices under the active tenant account,
so each licensed or subscription customer can manage its own payroll standards
without changing the whole platform.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from core.org_config import canonical_scope_workplace
from services.payroll_settings_store import (
    _resolve_tenant_id,
    _write_tenant_settings,
    load_tenant_payroll_settings,
)

INPUT_HYBRID = "hybrid"
INPUT_INVOICE = "invoice"
INPUT_ATTENDANCE = "attendance"
INPUT_CHOICES: tuple[str, ...] = (INPUT_HYBRID, INPUT_INVOICE, INPUT_ATTENDANCE)

INPUT_LABELS: dict[str, str] = {
    INPUT_HYBRID: "청구서+근태 혼합",
    INPUT_INVOICE: "청구서 기준",
    INPUT_ATTENDANCE: "근태/지문 기준",
}

MISSING_CLOCK_WARN = "warn"
MISSING_CLOCK_IGNORE = "ignore"
MISSING_CLOCK_DEDUCT = "deduct"
MISSING_CLOCK_POLICIES: tuple[str, ...] = (
    MISSING_CLOCK_WARN,
    MISSING_CLOCK_IGNORE,
    MISSING_CLOCK_DEDUCT,
)

MISSING_CLOCK_LABELS: dict[str, str] = {
    MISSING_CLOCK_WARN: "경고 표시",
    MISSING_CLOCK_IGNORE: "반영 안 함",
    MISSING_CLOCK_DEDUCT: "공제 후보",
}

PolicySource = Literal["site", "tenant", "global"]


def default_payroll_operation_policy() -> dict[str, Any]:
    return {
        "input_basis": INPUT_HYBRID,
        "payday": "25일",
        "show_setup_guide": True,
        "policy_note": "",
        "attendance": {
            "enabled": True,
            "source": "biometric",
            "rounding_minutes": 1,
            "late_grace_minutes": 0,
            "early_leave_grace_minutes": 0,
            "overtime_rounding_minutes": 1,
            "missing_clock_policy": MISSING_CLOCK_WARN,
            "holiday_source": "invoice",
        },
    }


def _int_between(value: Any, default: int, *, minimum: int = 0, maximum: int = 1440) -> int:
    try:
        v = int(float(value))
    except (TypeError, ValueError):
        v = default
    return max(minimum, min(maximum, v))


def normalize_payroll_operation_policy(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = default_payroll_operation_policy()
    if not isinstance(raw, dict):
        return base

    input_basis = str(raw.get("input_basis") or base["input_basis"]).strip()
    if input_basis not in INPUT_CHOICES:
        input_basis = INPUT_HYBRID

    out = deepcopy(base)
    out["input_basis"] = input_basis
    out["payday"] = str(raw.get("payday") or base["payday"]).strip() or base["payday"]
    out["show_setup_guide"] = bool(raw.get("show_setup_guide", True))
    out["policy_note"] = str(raw.get("policy_note") or "").strip()

    attendance_raw = raw.get("attendance") if isinstance(raw.get("attendance"), dict) else {}
    attendance = dict(out["attendance"])
    attendance["enabled"] = bool(attendance_raw.get("enabled", attendance["enabled"]))
    attendance["source"] = str(attendance_raw.get("source") or attendance["source"]).strip()
    attendance["rounding_minutes"] = _int_between(
        attendance_raw.get("rounding_minutes"),
        attendance["rounding_minutes"],
        minimum=1,
        maximum=60,
    )
    attendance["late_grace_minutes"] = _int_between(
        attendance_raw.get("late_grace_minutes"),
        attendance["late_grace_minutes"],
        minimum=0,
        maximum=240,
    )
    attendance["early_leave_grace_minutes"] = _int_between(
        attendance_raw.get("early_leave_grace_minutes"),
        attendance["early_leave_grace_minutes"],
        minimum=0,
        maximum=240,
    )
    attendance["overtime_rounding_minutes"] = _int_between(
        attendance_raw.get("overtime_rounding_minutes"),
        attendance["overtime_rounding_minutes"],
        minimum=1,
        maximum=60,
    )
    missing_policy = str(
        attendance_raw.get("missing_clock_policy") or attendance["missing_clock_policy"]
    ).strip()
    if missing_policy not in MISSING_CLOCK_POLICIES:
        missing_policy = MISSING_CLOCK_WARN
    attendance["missing_clock_policy"] = missing_policy
    attendance["holiday_source"] = str(
        attendance_raw.get("holiday_source") or attendance["holiday_source"]
    ).strip()
    out["attendance"] = attendance
    return out


def _site_policy_entry(tenant: dict[str, Any], workplace: str) -> dict[str, Any]:
    site_settings = tenant.get("site_settings") or {}
    if not isinstance(site_settings, dict):
        return {}
    entry = site_settings.get(workplace)
    return entry if isinstance(entry, dict) else {}


def resolve_payroll_operation_policy(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Resolve payroll operation policy by site -> tenant -> built-in default."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    tenant = load_tenant_payroll_settings(tenant_id)
    source: PolicySource = "global"
    raw: dict[str, Any] | None = None

    if wp:
        site_entry = _site_policy_entry(tenant, wp)
        site_policy = site_entry.get("payroll_operation_policy")
        if isinstance(site_policy, dict):
            raw = site_policy
            source = "site"

    if raw is None:
        tenant_policy = tenant.get("payroll_operation_policy")
        if isinstance(tenant_policy, dict):
            raw = tenant_policy
            source = "tenant"

    policy = normalize_payroll_operation_policy(raw)
    return {
        "workplace": wp,
        "policy": policy,
        "source": source,
        "has_site_override": source == "site",
    }


def save_tenant_payroll_operation_policy(
    policy: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    tenant = load_tenant_payroll_settings(tenant_id)
    applied = normalize_payroll_operation_policy(policy)
    tenant["payroll_operation_policy"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def save_site_payroll_operation_policy(
    workplace: str,
    policy: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    applied = normalize_payroll_operation_policy(policy)
    entry["payroll_operation_policy"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def clear_site_payroll_operation_policy(workplace: str, *, tenant_id: str | None = None) -> None:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings")
    if not isinstance(site_settings, dict):
        return
    entry = site_settings.get(wp)
    if isinstance(entry, dict) and "payroll_operation_policy" in entry:
        del entry["payroll_operation_policy"]
        if not entry:
            del site_settings[wp]
        _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


def operation_policy_source_label(source: PolicySource | str) -> str:
    return {"site": "사업장 개별", "tenant": "법인 기본", "global": "기본값"}.get(
        str(source), str(source)
    )


def format_payroll_operation_policy_summary(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> str:
    resolved = resolve_payroll_operation_policy(workplace, tenant_id=tenant_id)
    policy = resolved["policy"]
    attendance = policy["attendance"]
    return "\n".join(
        [
            f"급여 입력 방식: {INPUT_LABELS.get(policy['input_basis'], policy['input_basis'])} ({operation_policy_source_label(resolved['source'])})",
            f"지급일: {policy['payday']}",
            f"지문근태: {'사용' if attendance.get('enabled') else '미사용'} · 반올림 {attendance['rounding_minutes']}분 · 지각 유예 {attendance['late_grace_minutes']}분 · 조퇴 유예 {attendance['early_leave_grace_minutes']}분",
            f"누락 출퇴근: {MISSING_CLOCK_LABELS.get(attendance['missing_clock_policy'], attendance['missing_clock_policy'])}",
        ]
    )
