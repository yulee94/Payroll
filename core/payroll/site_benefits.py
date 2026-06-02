"""
core/payroll/site_benefits.py - 사업장별 특수 급여 항목

· 근로자의 날 수당 — 청구서 연동 또는 고정 금액
· 신원보증보험료 — 연 1회 공제 (설정 월)
"""

from __future__ import annotations

import re
from typing import Any, Literal

from core.org_config import canonical_scope_workplace
from roster_constants import norm_name_key
from utils import safe_number

BenefitSource = Literal["site", "tenant", "global"]

WORKERS_DAY_DEFAULT = {
    "enabled": False,
    "default_amount": 0,
    "auto_from_invoice": True,
}

IDENTITY_INSURANCE_DEFAULT = {
    "enabled": False,
    "annual_amount": 0,
    "billing_month": 1,
}

DEFAULT_SITE_BENEFITS = {
    "workers_day_allowance": dict(WORKERS_DAY_DEFAULT),
    "identity_guarantee_insurance": dict(IDENTITY_INSURANCE_DEFAULT),
}

WORKERS_DAY_HEADER_RE = re.compile(r"근로자\s*의\s*날")


def _header_matches_workers_day(header: str) -> bool:
    compact = str(header or "").replace(" ", "").replace("\n", "")
    if not compact:
        return False
    if WORKERS_DAY_HEADER_RE.search(str(header or "")):
        return True
    if "근로자의날" in compact:
        return True
    if compact in ("근로자의날수당", "근로자의날지급"):
        return True
    return False


def find_workers_day_column(ws) -> int | None:
    """청구내역 시트 헤더에서 근로자의 날 수당 열(1-based)을 찾습니다."""
    for r in range(1, min(12, ws.max_row + 1)):
        for c in range(1, ws.max_column + 1):
            raw = ws.cell(r, c).value
            if raw is None:
                continue
            if _header_matches_workers_day(str(raw).strip()):
                return c
    return None


def normalize_workers_day_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(WORKERS_DAY_DEFAULT)
    if not isinstance(raw, dict):
        return base
    base["enabled"] = bool(raw.get("enabled"))
    try:
        base["default_amount"] = max(0, int(safe_number(raw.get("default_amount"), 0)))
    except (TypeError, ValueError):
        base["default_amount"] = 0
    if "auto_from_invoice" in raw:
        base["auto_from_invoice"] = bool(raw.get("auto_from_invoice"))
    return base


def normalize_identity_insurance_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(IDENTITY_INSURANCE_DEFAULT)
    if not isinstance(raw, dict):
        return base
    base["enabled"] = bool(raw.get("enabled"))
    try:
        base["annual_amount"] = max(0, int(safe_number(raw.get("annual_amount"), 0)))
    except (TypeError, ValueError):
        base["annual_amount"] = 0
    try:
        month = int(safe_number(raw.get("billing_month"), 1))
    except (TypeError, ValueError):
        month = 1
    base["billing_month"] = min(12, max(1, month))
    return base


def normalize_site_benefits(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "workers_day_allowance": normalize_workers_day_config(
            raw.get("workers_day_allowance")
        ),
        "identity_guarantee_insurance": normalize_identity_insurance_config(
            raw.get("identity_guarantee_insurance")
        ),
    }


def _merge_benefit_field(
    field: str,
    *,
    site_raw: dict[str, Any],
    tenant_defaults: dict[str, Any],
    global_defaults: dict[str, Any],
    normalizer,
) -> tuple[dict[str, Any], BenefitSource]:
    site_benefits = site_raw.get("site_benefits") if isinstance(site_raw, dict) else None
    if isinstance(site_benefits, dict) and field in site_benefits:
        return normalizer(site_benefits.get(field)), "site"
    if isinstance(tenant_defaults, dict) and field in tenant_defaults:
        return normalizer(tenant_defaults.get(field)), "tenant"
    if isinstance(global_defaults, dict) and field in global_defaults:
        return normalizer(global_defaults.get(field)), "global"
    return normalizer(None), "global"


def resolve_site_benefits(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """사업장 특수 항목 — site → tenant → global."""
    from services.payroll_settings_store import (
        _load_global_settings,
        _site_entry,
        load_tenant_payroll_settings,
    )

    wp = canonical_scope_workplace(str(workplace or "").strip())
    tenant = load_tenant_payroll_settings(tenant_id)
    global_data = _load_global_settings()
    site_raw = _site_entry(tenant_id, wp) if wp else {}

    tenant_defaults = tenant.get("site_benefits_defaults") or {}
    global_defaults = global_data.get("site_benefits_defaults") or DEFAULT_SITE_BENEFITS

    workers, workers_src = _merge_benefit_field(
        "workers_day_allowance",
        site_raw=site_raw,
        tenant_defaults=tenant_defaults,
        global_defaults=global_defaults,
        normalizer=normalize_workers_day_config,
    )
    insurance, insurance_src = _merge_benefit_field(
        "identity_guarantee_insurance",
        site_raw=site_raw,
        tenant_defaults=tenant_defaults,
        global_defaults=global_defaults,
        normalizer=normalize_identity_insurance_config,
    )

    return {
        "workplace": wp,
        "workers_day_allowance": workers,
        "workers_day_source": workers_src,
        "identity_guarantee_insurance": insurance,
        "identity_insurance_source": insurance_src,
    }


def _ledger_key(workplace: str, employee_name: str) -> str:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    key = norm_name_key(employee_name)
    return f"{wp}|{key}"


def _parse_period_month(payroll_period: str) -> int | None:
    raw = str(payroll_period or "").strip()
    if len(raw) >= 7 and raw[4] == "-":
        try:
            return int(raw[5:7])
        except ValueError:
            return None
    return None


def _parse_period_year(payroll_period: str) -> str:
    raw = str(payroll_period or "").strip()
    if len(raw) >= 4:
        return raw[:4]
    return ""


def identity_insurance_already_applied(
    workplace: str,
    employee_name: str,
    payroll_period: str,
    *,
    tenant_id: str | None = None,
    prior_records: list[dict[str, Any]] | None = None,
) -> bool:
    """해당 연도·사업장·직원에 신원보증보험료가 이미 공제됐는지 확인."""
    year = _parse_period_year(payroll_period)
    if not year:
        return False
    ledger_key = _ledger_key(workplace, employee_name)

    from services.payroll_settings_store import load_tenant_payroll_settings

    tenant = load_tenant_payroll_settings(tenant_id)
    ledger = tenant.get("identity_insurance_ledger") or {}
    year_entry = ledger.get(year) if isinstance(ledger, dict) else None
    if isinstance(year_entry, dict) and ledger_key in year_entry:
        return True

    if prior_records:
        wp = canonical_scope_workplace(str(workplace or "").strip())
        name_key = norm_name_key(employee_name)
        for rec in prior_records:
            if not isinstance(rec, dict):
                continue
            if norm_name_key(rec.get("name")) != name_key:
                continue
            rec_wp = canonical_scope_workplace(str(rec.get("workplace") or ""))
            if rec_wp != wp:
                continue
            if int(safe_number(rec.get("identity_guarantee_insurance_deduction"), 0)) < 0:
                return True
    return False


def mark_identity_insurance_applied(
    workplace: str,
    employee_name: str,
    payroll_period: str,
    *,
    tenant_id: str | None = None,
) -> None:
    """신원보증보험료 공제 이력 기록."""
    year = _parse_period_year(payroll_period)
    if not year:
        return
    from services.payroll_settings_store import (
        _resolve_tenant_id,
        _write_tenant_settings,
        load_tenant_payroll_settings,
    )

    tenant = load_tenant_payroll_settings(tenant_id)
    ledger = tenant.setdefault("identity_insurance_ledger", {})
    if not isinstance(ledger, dict):
        ledger = {}
        tenant["identity_insurance_ledger"] = ledger
    year_entry = ledger.setdefault(year, {})
    if not isinstance(year_entry, dict):
        year_entry = {}
        ledger[year] = year_entry
    year_entry[_ledger_key(workplace, employee_name)] = str(payroll_period)
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


def calc_workers_day_allowance(
    inv: dict[str, Any],
    config: dict[str, Any],
    *,
    payroll_period: str = "",
) -> int:
    """근로자의 날 수당 금액 산출."""
    if not config.get("enabled"):
        return 0
    if config.get("auto_from_invoice", True):
        amount = int(safe_number(inv.get("workers_day_pay"), 0))
        if amount > 0:
            return amount
        return 0
    default_amt = int(safe_number(config.get("default_amount"), 0))
    if default_amt <= 0:
        return 0
    month = _parse_period_month(payroll_period)
    if month == 5:
        return default_amt
    return 0


def calc_identity_guarantee_insurance_deduction(
    config: dict[str, Any],
    *,
    payroll_period: str,
    workplace: str,
    employee_name: str,
    tenant_id: str | None = None,
    prior_records: list[dict[str, Any]] | None = None,
) -> int:
    """신원보증보험료 공제(음수) — 설정 월·연 1회."""
    if not config.get("enabled"):
        return 0
    annual = int(safe_number(config.get("annual_amount"), 0))
    if annual <= 0:
        return 0
    billing_month = int(safe_number(config.get("billing_month"), 1))
    month = _parse_period_month(payroll_period)
    if month != billing_month:
        return 0
    if identity_insurance_already_applied(
        workplace,
        employee_name,
        payroll_period,
        tenant_id=tenant_id,
        prior_records=prior_records,
    ):
        return 0
    return -annual


def apply_site_benefits_to_invoice(
    inv: dict[str, Any],
    *,
    workplace: str,
    payroll_period: str = "",
    tenant_id: str | None = None,
    prior_records: list[dict[str, Any]] | None = None,
    persist_ledger: bool = True,
) -> dict[str, Any]:
    """
    사업장 특수 항목을 청구서/급여 dict에 반영합니다.

    Returns:
        적용 내역 {workers_day_allowance, identity_guarantee_insurance_deduction, ...}
    """
    wp = str(workplace or inv.get("workplace") or "").strip()
    name = str(inv.get("name") or "").strip()
    benefits = resolve_site_benefits(wp, tenant_id=tenant_id)

    workers_amt = calc_workers_day_allowance(
        inv,
        benefits["workers_day_allowance"],
        payroll_period=payroll_period,
    )
    insurance_ded = calc_identity_guarantee_insurance_deduction(
        benefits["identity_guarantee_insurance"],
        payroll_period=payroll_period,
        workplace=wp,
        employee_name=name,
        tenant_id=tenant_id,
        prior_records=prior_records,
    )

    inv["workers_day_allowance"] = workers_amt
    inv["identity_guarantee_insurance_deduction"] = insurance_ded
    inv["_workers_day_source"] = benefits["workers_day_source"]
    inv["_identity_insurance_source"] = benefits["identity_insurance_source"]

    if insurance_ded < 0 and persist_ledger and name:
        mark_identity_insurance_applied(
            wp, name, payroll_period, tenant_id=tenant_id
        )

    return {
        "workers_day_allowance": workers_amt,
        "identity_guarantee_insurance_deduction": insurance_ded,
        "workers_day_source": benefits["workers_day_source"],
        "identity_insurance_source": benefits["identity_insurance_source"],
    }


def benefit_source_label(source: BenefitSource) -> str:
    return {"site": "사업장 개별", "tenant": "법인 기본", "global": "전역 기본"}.get(
        source, source
    )
