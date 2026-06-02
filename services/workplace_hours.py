"""
workplace_hours.py - 사업장별 월 기본근로시간(기본급 산정) 정책

모드:
  fixed              — 고정 시간 (기본 209, 앰코 등)
  invoice_work_days  — 청구서 J열 근무시간 그대로
  invoice_base_days  — 청구서 I열 기준시간 그대로
  work_or_fixed      — 근무시간 > 0 이면 근무시간, 아니면 고정값
  base_or_fixed      — 기준시간 > 0 이면 기준시간, 아니면 고정값
"""

from __future__ import annotations

from typing import Any

from core.org_config import canonical_scope_workplace, list_config_workplaces
from services.payroll_settings_store import load_payroll_settings
from utils import STANDARD_MONTHLY_HOURS, safe_number

MODE_FIXED = "fixed"
MODE_INVOICE_WORK = "invoice_work_days"
MODE_INVOICE_BASE = "invoice_base_days"
MODE_WORK_OR_FIXED = "work_or_fixed"
MODE_BASE_OR_FIXED = "base_or_fixed"

MODE_LABELS: dict[str, str] = {
    MODE_FIXED: "고정 시간",
    MODE_INVOICE_WORK: "청구서 근무시간(J열)",
    MODE_INVOICE_BASE: "청구서 기준시간(I열)",
    MODE_WORK_OR_FIXED: "근무시간 우선 (없으면 고정)",
    MODE_BASE_OR_FIXED: "기준시간 우선 (없으면 고정)",
}

MODE_CHOICES: tuple[str, ...] = tuple(MODE_LABELS.keys())


def normalize_policy(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    mode = str(raw.get("mode") or MODE_FIXED).strip()
    if mode not in MODE_LABELS:
        mode = MODE_FIXED
    try:
        hours = float(raw.get("hours", STANDARD_MONTHLY_HOURS))
    except (TypeError, ValueError):
        hours = float(STANDARD_MONTHLY_HOURS)
    if hours <= 0:
        hours = float(STANDARD_MONTHLY_HOURS)
    out: dict[str, Any] = {"mode": mode, "hours": round(hours, 4)}
    for key, default in (("daily_hours", 8.0), ("break_minutes", 0.0)):
        if raw.get(key) is None:
            continue
        try:
            val = float(raw[key])
        except (TypeError, ValueError):
            continue
        if key == "daily_hours" and val > 0:
            out["daily_hours"] = round(val, 4)
        elif key == "break_minutes" and val >= 0:
            out["break_minutes"] = round(val, 2)
    return out


def policy_for_workplace(workplace: str, *, tenant_id: str | None = None) -> dict[str, Any]:
    """사업장별 정책 — site → tenant → global."""
    from services.payroll_settings_store import resolve_payroll_calc_settings

    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        settings = load_payroll_settings(tenant_id)
        return normalize_policy(settings.get("default_workplace_hours_policy"))
    return resolve_payroll_calc_settings(wp, tenant_id=tenant_id)["workplace_hours_policy"]


def _hours_from_invoice(inv: dict[str, Any], field: str) -> float:
    return max(0.0, safe_number(inv.get(field), 0.0))


def resolve_monthly_work_hours(
    inv: dict[str, Any],
    workplace: str,
    *,
    policy: dict[str, Any] | None = None,
) -> tuple[float, str]:
    """
    기본급 산정용 월 근로시간.

    Returns:
        (hours, source_label) — UI·경고용
    """
    pol = normalize_policy(policy) if policy else policy_for_workplace(workplace)
    mode = pol["mode"]
    fixed_h = float(pol["hours"])
    wp_label = canonical_scope_workplace(workplace) or "(기본)"

    work_h = _hours_from_invoice(inv, "work_days")
    base_h = _hours_from_invoice(inv, "base_days")

    if mode == MODE_FIXED:
        return fixed_h, f"{wp_label}: 고정 {fixed_h:g}시간"
    if mode == MODE_INVOICE_WORK:
        h = work_h if work_h > 0 else fixed_h
        src = "청구서 근무시간" if work_h > 0 else f"고정 {fixed_h:g}시간(근무시간 없음)"
        return h, f"{wp_label}: {src}"
    if mode == MODE_INVOICE_BASE:
        h = base_h if base_h > 0 else fixed_h
        src = "청구서 기준시간" if base_h > 0 else f"고정 {fixed_h:g}시간(기준시간 없음)"
        return h, f"{wp_label}: {src}"
    if mode == MODE_WORK_OR_FIXED:
        if work_h > 0:
            return work_h, f"{wp_label}: 청구서 근무시간 {work_h:g}"
        return fixed_h, f"{wp_label}: 고정 {fixed_h:g}시간"
    if mode == MODE_BASE_OR_FIXED:
        if base_h > 0:
            return base_h, f"{wp_label}: 청구서 기준시간 {base_h:g}"
        return fixed_h, f"{wp_label}: 고정 {fixed_h:g}시간"

    return fixed_h, f"{wp_label}: 고정 {fixed_h:g}시간"


def apply_monthly_hours_to_invoice(
    inv: dict[str, Any],
    workplace: str,
    *,
    policy: dict[str, Any] | None = None,
) -> float:
    """청구서 dict에 산정 시간·출처 기록 후 반환."""
    hours, source = resolve_monthly_work_hours(inv, workplace, policy=policy)
    inv["_monthly_work_hours"] = hours
    inv["_monthly_hours_source"] = source
    return hours


def list_all_workplace_policies(*, tenant_id: str | None = None) -> list[dict[str, Any]]:
    """설정 화면용 — 조직 사업장 + 저장된 정책 병합."""
    from services.payroll_settings_store import list_site_payroll_overview

    rows: list[dict[str, Any]] = []
    for row in list_site_payroll_overview(tenant_id=tenant_id):
        rows.append(
            {
                "workplace": row["workplace"],
                "mode": row["mode"],
                "mode_label": row["mode_label"],
                "hours": row["hours"],
                "is_custom": row["is_custom"],
                "shutdown_pay_percent": row["shutdown_pay_percent"],
            }
        )
    return rows


def workplace_hours_help_text() -> str:
    return (
        "기본급 = 기본시급 × 월 기본근로시간 입니다.\n"
        "· 고정: 법정 209시간 등 사업장별 고정값 (한국앰코 기본)\n"
        "· 청구서 근무/기준시간: 도급비 청구서 I·J열 값을 시간으로 사용\n"
        "· ○○ 우선: 해당 열이 비어 있으면 고정값으로 대체"
    )
