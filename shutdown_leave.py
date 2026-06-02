"""
shutdown_leave.py - 회사 사정 휴업(단체 연차) 시 총급여 비율 지급 계산
"""

from __future__ import annotations

from typing import Any

from services.payroll_settings_store import get_shutdown_pay_percent
from utils import round_won, safe_number


def ensure_reference_gross_pay(inv: dict[str, Any]) -> int:
    """청구서 원본 총급여(휴업수당 산정 기준) — 산출 전 한 번 고정."""
    if inv.get("_reference_gross_pay") is not None:
        return int(safe_number(inv["_reference_gross_pay"], 0))
    ref = int(safe_number(inv.get("gross_pay"), 0))
    inv["_reference_gross_pay"] = ref
    return ref


def calc_shutdown_gross_adjustments(
    inv: dict[str, Any],
    shutdown_days: float,
    *,
    pay_percent: float | None = None,
) -> tuple[int, int]:
    """
    휴업 일수에 대한 지급·공제(기본공제 항목에 합산).

    Returns:
        (shutdown_allowance 양수, shutdown_base_deduction 음수 또는 0)
        — shutdown_base_deduction = -총급여일할×일수 + allowance
    """
    days = max(0.0, float(shutdown_days))
    if days <= 0:
        return 0, 0

    base_days = safe_number(inv.get("_monthly_work_hours"), 0.0)
    if base_days <= 0:
        base_days = safe_number(inv.get("base_days"), 0.0)
    ref_gross = ensure_reference_gross_pay(inv)
    if base_days <= 0 or ref_gross <= 0:
        return 0, 0

    if pay_percent is not None:
        rate = pay_percent
    else:
        workplace = str(inv.get("workplace") or "").strip()
        rate = get_shutdown_pay_percent(workplace or None)
    rate = max(0.0, min(100.0, float(rate)))
    share = days / base_days
    gross_slice = ref_gross * share
    allowance = round_won(gross_slice * rate / 100.0)
    full_deduction = -round_won(gross_slice)
    net_deduction = full_deduction + allowance
    return allowance, net_deduction


def pure_unpaid_days(inv: dict[str, Any]) -> float:
    """무급/결근만(휴업 일수 제외)."""
    unpaid = max(0.0, safe_number(inv.get("unpaid_days"), 0.0))
    shutdown = max(0.0, safe_number(inv.get("shutdown_leave_days"), 0.0))
    return max(0.0, unpaid - shutdown) if shutdown > 0 else unpaid
