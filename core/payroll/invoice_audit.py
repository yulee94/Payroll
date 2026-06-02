"""
invoice_audit.py - 청구서 기반 급여 산출 자동검열

근로시간·휴계·사업장 월 기본근로시간 정책 대비 청구서·산출 결과를 대조합니다.
"""

from __future__ import annotations

from typing import Any, Literal

from services.workplace_hours import (
    MODE_BASE_OR_FIXED,
    MODE_FIXED,
    MODE_INVOICE_BASE,
    MODE_INVOICE_WORK,
    MODE_WORK_OR_FIXED,
    apply_monthly_hours_to_invoice,
    policy_for_workplace,
    resolve_monthly_work_hours,
)
from core.payroll.fixed_hours import (
    FIXED_HOURS_SOURCE_CONTRACT,
    resolve_employee_fixed_hours,
    fixed_hours_audit_flags,
    apply_fixed_hours_to_invoice,
)
from utils import round_won, safe_number

AuditStatus = Literal["pass", "warn"]

_STATUS_LABEL = {"pass": "정상", "warn": "확인"}


def _status_label(status: AuditStatus) -> str:
    return _STATUS_LABEL.get(status, status)


def _estimate_break_hours(inv: dict[str, Any], policy: dict[str, Any]) -> float | None:
    """
    휴계시간 추정.

    - 사업장 break_minutes 설정: 근무일수(추정) × 휴계
    - 미설정: I·J열이 모두 시간 단위(≥24)일 때 기준-근무-휴가 차이를 참고 휴계로 표시
    """
    break_min = safe_number(policy.get("break_minutes"), 0.0)
    daily_h = safe_number(policy.get("daily_hours"), 8.0) or 8.0
    work = safe_number(inv.get("work_days"), 0.0)
    base = safe_number(inv.get("base_days"), 0.0)
    leave = safe_number(inv.get("leave_days"), 0.0)

    if break_min > 0 and work > 0:
        if work <= 31:
            work_days_count = work
        else:
            work_days_count = work / daily_h
        return round((break_min / 60.0) * work_days_count, 4)

    if base > work > 0 and base >= 24 and work >= 1:
        gap = base - work - leave
        if gap > 0:
            return round(gap, 4)
    return None


def audit_invoice_row(
    inv: dict[str, Any],
    *,
    workplace: str,
    policy: dict[str, Any] | None = None,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """청구서 1인분 자동검열."""
    wp = str(
        workplace
        or (record or {}).get("workplace")
        or inv.get("workplace")
        or ""
    ).strip()
    pol = policy if policy else policy_for_workplace(wp)
    inv_copy = dict(inv)
    emp_name = str(inv.get("name") or (record or {}).get("name") or "")
    fixed_profile = resolve_employee_fixed_hours(
        employee_name=emp_name,
        workplace=wp,
    )
    if fixed_profile and fixed_profile.get("fixed_hours_mode"):
        apply_fixed_hours_to_invoice(inv_copy, fixed_profile, workplace=wp)
        applied_h = safe_number(inv_copy.get("_monthly_work_hours"), 0.0)
        source = str(inv_copy.get("_monthly_hours_source") or FIXED_HOURS_SOURCE_CONTRACT)
    else:
        applied_h = apply_monthly_hours_to_invoice(inv_copy, wp, policy=pol)
        source = str(inv_copy.get("_monthly_hours_source") or "")
    fixed_h = float(pol.get("hours") or 209)

    base_i = safe_number(inv.get("base_days"))
    work_j = safe_number(inv.get("work_days"))
    break_h = _estimate_break_hours(inv, pol)

    base_hourly = safe_number(
        (record or {}).get("base_hourly") or inv.get("base_hourly"),
        0.0,
    )
    invoice_base = int(safe_number(inv.get("base_salary"), 0))
    calc_base = round_won(base_hourly * applied_h) if base_hourly > 0 else 0

    flags: list[str] = []
    status: AuditStatus = "pass"

    mode = pol.get("mode", MODE_FIXED)
    if mode in (MODE_INVOICE_WORK, MODE_WORK_OR_FIXED) and work_j <= 0:
        flags.append("청구서 근무시간(J) 없음 — 고정값 대체")
        status = "warn"
    if mode in (MODE_INVOICE_BASE, MODE_BASE_OR_FIXED) and base_i <= 0:
        flags.append("청구서 기준시간(I) 없음 — 고정값 대체")
        status = "warn"
    if mode == MODE_FIXED and work_j > fixed_h * 1.05 and work_j >= 24:
        flags.append(f"청구서 근무시간({work_j:g}h)이 사업장 고정({fixed_h:g}h) 초과")
        status = "warn"
    if applied_h > fixed_h * 1.1 and mode == MODE_FIXED:
        flags.append(f"적용 시간({applied_h:g}h)이 고정 기준({fixed_h:g}h)보다 큼")
        status = "warn"
    if base_hourly > 0 and invoice_base > 0 and abs(calc_base - invoice_base) > 1:
        flags.append(
            f"기본급 불일치: 산출 {calc_base:,}원 vs 청구서 {invoice_base:,}원"
        )
        status = "warn"
    elif base_hourly <= 0 and invoice_base > 0:
        flags.append("명부 기본시급 없음 — 기본급 검증 생략")
    if break_h is None and base_i > work_j > 0:
        flags.append("휴계 미설정 — I·J열 차이는 휴가·무급 포함 가능")

    fixed_flags = fixed_hours_audit_flags(inv_copy, fixed_profile)
    if fixed_flags:
        flags = fixed_flags + flags
        if any("≠" in f for f in fixed_flags):
            status = "warn"

    rec_h = safe_number((record or {}).get("_monthly_work_hours"), 0.0)
    if record and rec_h > 0 and abs(rec_h - applied_h) > 0.01:
        flags.append(f"대장 적용시간({rec_h:g}h)과 재검열({applied_h:g}h) 상이")
        status = "warn"

    formula_parts = [f"기본시급 {base_hourly:,.0f}원 × {applied_h:g}시간"]
    if calc_base > 0:
        formula_parts.append(f"= {calc_base:,}원")

    return {
        "name": str(inv.get("name") or ""),
        "workplace": wp,
        "status": status,
        "status_label": _status_label(status),
        "flags": flags,
        "base_days": base_i,
        "work_days": work_j,
        "break_hours": break_h,
        "applied_monthly_hours": applied_h,
        "hours_source": source,
        "policy_mode": mode,
        "policy_fixed_hours": fixed_h,
        "base_hourly": base_hourly,
        "invoice_base_salary": invoice_base,
        "calc_base_salary": calc_base,
        "formula": " ".join(formula_parts),
        "fixed_hours_mode": bool(fixed_profile and fixed_profile.get("fixed_hours_mode")),
        "fixed_hours_source": (fixed_profile or {}).get("source_label", ""),
    }


def audit_invoice_payroll(
    invoice_rows: list[dict[str, Any]],
    records: list[dict[str, Any]] | None = None,
    *,
    workplace: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """
    청구서 전체 자동검열.

    Returns:
        summary, rows, pass_count, warn_count, workplace
    """
    record_by_name: dict[str, dict[str, Any]] = {}
    for rec in records or []:
        key = str(rec.get("name") or "").strip()
        if key:
            record_by_name[key] = rec

    default_wp = str(workplace or "").strip()
    pol = policy_for_workplace(default_wp, tenant_id=tenant_id) if default_wp else None

    rows: list[dict[str, Any]] = []
    pass_count = 0
    warn_count = 0

    for inv in invoice_rows:
        name = str(inv.get("name") or "").strip()
        rec = record_by_name.get(name)
        wp = default_wp
        if rec:
            wp = str(rec.get("workplace") or rec.get("dept") or wp).strip() or wp
        if not wp and isinstance(inv.get("workplace"), str):
            wp = inv["workplace"]
        row_pol = policy_for_workplace(wp, tenant_id=tenant_id) if wp else pol
        audited = audit_invoice_row(
            inv,
            workplace=wp,
            policy=row_pol,
            record=rec,
        )
        rows.append(audited)
        if audited["status"] == "pass":
            pass_count += 1
        else:
            warn_count += 1

    return {
        "workplace": default_wp,
        "summary": {
            "total": len(rows),
            "pass": pass_count,
            "warn": warn_count,
        },
        "rows": rows,
        "pass_count": pass_count,
        "warn_count": warn_count,
    }


def format_audit_summary_text(audit: dict[str, Any]) -> str:
    s = audit.get("summary") or {}
    lines = [
        f"자동검열 — {s.get('total', 0)}명",
        f"  · 정상 {s.get('pass', 0)}명 / 확인 필요 {s.get('warn', 0)}명",
    ]
    wp = audit.get("workplace")
    if wp:
        lines.insert(1, f"  · 사업장: {wp}")
    warns = [r for r in audit.get("rows") or [] if r.get("status") == "warn"][:5]
    if warns:
        lines.append("")
        lines.append("확인 필요 (일부)")
        for r in warns:
            flags = "; ".join(r.get("flags") or []) or "-"
            lines.append(f"  · {r.get('name')}: {flags}")
        extra = int(s.get("warn", 0)) - len(warns)
        if extra > 0:
            lines.append(f"  · 외 {extra}명")
    return "\n".join(lines)
