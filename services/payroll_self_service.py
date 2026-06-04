"""
payroll_self_service.py - self-service guide for payroll settings.

The desktop UI and future API can use this module to show customers what is
configured, what still needs confirmation, and how the current payroll result
will be interpreted for their licensed tenant account.
"""

from __future__ import annotations

from typing import Any

from core.payroll.site_benefits import resolve_site_benefits
from services.payroll_policy_store import (
    INPUT_LABELS,
    format_payroll_operation_policy_summary,
    operation_policy_source_label,
    resolve_payroll_operation_policy,
)
from services.payroll_settings_store import (
    _resolve_tenant_id,
    get_edi_insurance_config,
    resolve_payroll_calc_settings,
    settings_source_label,
)
from services.workplace_hours import MODE_LABELS


def _done_item(title: str, detail: str, done: bool = True) -> dict[str, Any]:
    return {"title": title, "detail": detail, "done": bool(done)}


def build_payroll_setup_checklist(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return customer-facing setup checklist for one workplace."""
    wp = str(workplace or "").strip()
    tid = _resolve_tenant_id(tenant_id)
    operation = resolve_payroll_operation_policy(wp, tenant_id=tid)
    op_policy = operation["policy"]
    calc = resolve_payroll_calc_settings(wp, tenant_id=tid) if wp else None
    benefits = resolve_site_benefits(wp, tenant_id=tid) if wp else None
    edi = get_edi_insurance_config(tenant_id=tid)

    items: list[dict[str, Any]] = [
        _done_item(
            "법인/구독 계정",
            f"현재 설정은 이 계정에만 저장됩니다: {tid}",
            bool(tid),
        ),
        _done_item(
            "사업장 선택",
            wp or "사업장을 선택하면 개별 기준을 확인할 수 있습니다.",
            bool(wp),
        ),
        _done_item(
            "급여 입력 방식",
            f"{INPUT_LABELS.get(op_policy['input_basis'], op_policy['input_basis'])} · {operation_policy_source_label(operation['source'])}",
            True,
        ),
    ]

    if calc:
        hours_policy = calc["workplace_hours_policy"]
        items.extend(
            [
                _done_item(
                    "월 기본근로시간",
                    f"{MODE_LABELS.get(hours_policy['mode'], hours_policy['mode'])} · {hours_policy['hours']:g}시간 · {settings_source_label(calc['hours_source'])}",
                    True,
                ),
                _done_item(
                    "휴업수당 지급률",
                    f"{calc['shutdown_pay_percent']:g}% · {settings_source_label(calc['shutdown_source'])}",
                    True,
                ),
            ]
        )

    attendance = op_policy["attendance"]
    items.append(
        _done_item(
            "지문근태 집계 기준",
            (
                f"반올림 {attendance['rounding_minutes']}분, "
                f"지각 유예 {attendance['late_grace_minutes']}분, "
                f"조퇴 유예 {attendance['early_leave_grace_minutes']}분"
            ),
            bool(attendance.get("enabled")),
        )
    )

    if benefits:
        wd = benefits["workers_day_allowance"]
        ig = benefits["identity_guarantee_insurance"]
        items.append(
            _done_item(
                "사업장 특수 항목",
                (
                    f"근로자의 날 {'사용' if wd.get('enabled') else '미사용'} · "
                    f"신원보증보험 {'사용' if ig.get('enabled') else '미사용'}"
                ),
                True,
            )
        )

    items.append(
        _done_item(
            "보험료/외부 API 연동",
            "EDI/API 연결 준비됨" if edi.get("api_connected") else "필요 시 설정 화면에서 EDI/API 값을 연결합니다.",
            True,
        )
    )
    return items


def format_payroll_setup_guide(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> str:
    """Format setup checklist as text for the settings explanation panel."""
    resolved = resolve_payroll_operation_policy(workplace, tenant_id=tenant_id)
    if not resolved["policy"].get("show_setup_guide", True):
        return ""

    lines = [
        "초기 세팅 체크리스트",
        f"  · {format_payroll_operation_policy_summary(workplace, tenant_id=tenant_id).replace(chr(10), chr(10) + '  · ')}",
    ]
    for item in build_payroll_setup_checklist(workplace, tenant_id=tenant_id):
        marker = "완료" if item["done"] else "확인필요"
        lines.append(f"  · [{marker}] {item['title']}: {item['detail']}")

    note = str(resolved["policy"].get("policy_note") or "").strip()
    if note:
        lines.append(f"  · 메모: {note}")
    return "\n".join(lines)
