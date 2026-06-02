"""
calc_breakdown.py - 사업장별 급여 산출내역(적용 근로시간·산식 설명)
"""

from __future__ import annotations

from typing import Any

from services.payroll_settings_store import resolve_payroll_calc_settings, settings_source_label
from services.payroll_settings_store import get_site_extra_settings
from core.payroll.site_benefits import benefit_source_label, resolve_site_benefits
from services.workplace_hours import MODE_LABELS, resolve_monthly_work_hours
from core.payroll.fixed_hours import DEFAULT_JOB_GROUP_TEMPLATES, PAY_TYPE_LABELS
from utils import STANDARD_MONTHLY_HOURS, round_won, safe_number


def _sample_invoice_for_preview() -> dict[str, Any]:
    """설정 화면 미리보기용 — 청구서 I·J열 예시."""
    return {"base_days": 209.0, "work_days": 200.0, "leave_days": 0.0}


def build_site_calc_breakdown(
    workplace: str,
    *,
    tenant_id: str | None = None,
    sample_invoice: dict[str, Any] | None = None,
    roster_base_hourly: float = 0.0,
) -> dict[str, Any]:
    """
    사업장 급여 산출 설정과 예시 산식을 구조화해 반환합니다.

    Returns:
        workplace, policy, resolved sources, lines (표시용 문자열 목록),
        preview_hours, preview_source, preview_base_salary
    """
    wp = str(workplace or "").strip()
    if not wp:
        return {
            "workplace": "",
            "lines": ["사업장을 선택하면 적용 근로시간과 산출내역을 확인할 수 있습니다."],
            "preview_hours": STANDARD_MONTHLY_HOURS,
            "preview_source": "",
            "preview_base_salary": 0,
        }

    resolved = resolve_payroll_calc_settings(wp, tenant_id=tenant_id)
    pol = resolved["workplace_hours_policy"]
    inv = sample_invoice if isinstance(sample_invoice, dict) else _sample_invoice_for_preview()
    preview_h, preview_src = resolve_monthly_work_hours(inv, wp, policy=pol)

    mode_label = MODE_LABELS.get(pol["mode"], pol["mode"])
    fixed_h = float(pol.get("hours") or STANDARD_MONTHLY_HOURS)
    daily_h = pol.get("daily_hours")
    break_m = pol.get("break_minutes")

    lines: list[str] = [
        f"【{wp}】 적용 설정",
        f"  · 휴업수당: {resolved['shutdown_pay_percent']:g}% ({settings_source_label(resolved['shutdown_source'])})",
        f"  · 월 기본근로시간 산출: {mode_label}",
        f"  · 고정/대체 시간: {fixed_h:g}시간 ({settings_source_label(resolved['hours_source'])})",
    ]
    if daily_h:
        lines.append(f"  · 1일 소정근로: {float(daily_h):g}시간")
    if break_m:
        lines.append(f"  · 1일 휴계(기본): {float(break_m):g}분")

    site_extra = get_site_extra_settings(wp, tenant_id=tenant_id)
    if site_extra.get("security_cleaning"):
        lines.extend(["", "경비·미화 유형 사업장 — 직군별 고정 근로시간"])
        templates = site_extra.get("job_group_templates") or {}
        if templates:
            for jg, tpl in sorted(templates.items()):
                pay_l = PAY_TYPE_LABELS.get(tpl.get("pay_type", ""), tpl.get("pay_type", ""))
                lines.append(
                    f"  · {jg}: 월 {float(tpl.get('monthly_fixed_hours', 209)):g}h"
                    f" · 특근 {float(tpl.get('fixed_overtime_hours', 0)):g}h"
                    f" · 연장 {float(tpl.get('fixed_extension_hours', 0)):g}h"
                    f" ({pay_l})"
                )
        else:
            for jg, tpl in DEFAULT_JOB_GROUP_TEMPLATES.items():
                pay_l = PAY_TYPE_LABELS.get(tpl.get("pay_type", ""), "")
                lines.append(
                    f"  · {jg}(기본): 월 {float(tpl.get('monthly_fixed_hours', 209)):g}h ({pay_l})"
                )
        lines.append("  · 근로계약서 개별 설정이 있으면 템플릿보다 우선합니다.")

    benefits = resolve_site_benefits(wp, tenant_id=tenant_id)
    wd = benefits["workers_day_allowance"]
    ig = benefits["identity_guarantee_insurance"]
    lines.extend(
        [
            "",
            "사업장별 특수 항목",
            f"  · 근로자의 날 수당: {'사용' if wd.get('enabled') else '미사용'}"
            f" ({benefit_source_label(benefits['workers_day_source'])})",
        ]
    )
    if wd.get("enabled"):
        if wd.get("auto_from_invoice", True):
            lines.append("    └ 청구서 금액 자동 반영")
        else:
            lines.append(
                f"    └ 5월 고정 {int(wd.get('default_amount', 0)):,}원"
            )
    lines.append(
        f"  · 신원보증보험료: {'사용' if ig.get('enabled') else '미사용'}"
        f" ({benefit_source_label(benefits['identity_insurance_source'])})"
    )
    if ig.get("enabled"):
        lines.append(
            f"    └ 연 {int(ig.get('annual_amount', 0)):,}원 · "
            f"{int(ig.get('billing_month', 1))}월 1회 공제"
        )

    base_i = safe_number(inv.get("base_days"))
    work_j = safe_number(inv.get("work_days"))
    lines.extend(
        [
            "",
            "청구서 참고 열 (예시·실제 청구서 값)",
            f"  · I열 기준시간(base_days): {base_i:g}",
            f"  · J열 근무시간(work_days): {work_j:g}",
            "",
            "기본급 산식",
            f"  · 적용 월 근로시간 = {preview_h:g}시간",
            f"    └ {preview_src}",
            "  · 기본급 = 기본시급 × 적용 월 근로시간",
        ]
    )
    if roster_base_hourly > 0:
        calc_base = round_won(roster_base_hourly * preview_h)
        lines.append(
            f"  · 예: 기본시급 {roster_base_hourly:,.0f}원 × {preview_h:g}h = {calc_base:,}원"
        )
    else:
        lines.append("  · (명부 기본시급 입력 시 예상 기본급 금액 표시)")

    lines.extend(
        [
            "",
            "기본공제",
            "  · 기본공제 = -(기본시급 × 공제일수 × 8) + 휴업 조정",
            "",
            "시간수당 (명부 통상시급 있을 때)",
            "  · 연장 = 통상시급 × 연장시간 × 1.5",
            "  · 심야 = 통상시급 × 심야시간 × 0.5",
        ]
    )

    return {
        "workplace": wp,
        "policy": pol,
        "resolved": resolved,
        "lines": lines,
        "preview_hours": preview_h,
        "preview_source": preview_src,
        "preview_base_salary": (
            int(roster_base_hourly * preview_h) if roster_base_hourly > 0 else 0
        ),
    }


def format_site_calc_breakdown_text(
    workplace: str,
    *,
    tenant_id: str | None = None,
    roster_base_hourly: float = 0.0,
) -> str:
    data = build_site_calc_breakdown(
        workplace,
        tenant_id=tenant_id,
        roster_base_hourly=roster_base_hourly,
    )
    return "\n".join(data["lines"])
