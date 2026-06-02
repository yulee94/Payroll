"""
payroll_settings_store.py - 급여 산출 설정 (법인 기본 · 사업장별)

적용 우선순위: 사업장 개별 → 법인(테넌트) 기본 → 전역 기본(config)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from core.config import BASE_DIR
from core.org_config import canonical_scope_workplace, list_config_workplaces
from core.paths import app_data_dir
from core.tenant_store import get_active_tenant_id

GLOBAL_SETTINGS_PATH = BASE_DIR / "config" / "payroll_settings.json"

# 근로기준법 제46조: 사업주 귀책 휴업 시 평균임금의 100분의 70 이상 지급
LEGAL_MIN_SHUTDOWN_PAY_PERCENT = 70.0
DEFAULT_SHUTDOWN_PAY_PERCENT = 70.0

SettingsSource = Literal["site", "tenant", "global"]


def _tenant_settings_dir() -> Path:
    return app_data_dir() / "payroll_settings"


def _tenant_settings_path(tenant_id: str) -> Path:
    return _tenant_settings_dir() / f"{tenant_id}.json"


def _resolve_tenant_id(tenant_id: str | None) -> str:
    if tenant_id:
        return str(tenant_id).strip()
    try:
        from core.session_service import session_tenant_id

        tid = session_tenant_id()
        if tid:
            return tid
    except Exception:
        pass
    return get_active_tenant_id()


def _default_global_settings() -> dict[str, Any]:
    from core.payroll.site_benefits import DEFAULT_SITE_BENEFITS

    return {
        "shutdown_pay_percent": DEFAULT_SHUTDOWN_PAY_PERCENT,
        "updated_at": "",
        "default_workplace_hours_policy": {
            "mode": "fixed",
            "hours": 209,
        },
        "workplace_hours_policies": {},
        "site_benefits_defaults": dict(DEFAULT_SITE_BENEFITS),
    }


def _load_global_settings() -> dict[str, Any]:
    if not GLOBAL_SETTINGS_PATH.is_file():
        return _default_global_settings()
    try:
        data = json.loads(GLOBAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_global_settings()
        out = _default_global_settings()
        out.update(data)
        return out
    except (OSError, json.JSONDecodeError):
        return _default_global_settings()


def _default_tenant_settings(*, from_global: dict[str, Any] | None = None) -> dict[str, Any]:
    from core.payroll.site_benefits import DEFAULT_SITE_BENEFITS, normalize_site_benefits

    global_data = from_global or _load_global_settings()
    site_settings: dict[str, Any] = {}
    per_wp = global_data.get("workplace_hours_policies") or {}
    if isinstance(per_wp, dict):
        for wp, pol in per_wp.items():
            canon = canonical_scope_workplace(str(wp or "").strip())
            if not canon or not isinstance(pol, dict):
                continue
            site_settings[canon] = {"workplace_hours_policy": dict(pol)}
    global_benefits = global_data.get("site_benefits_defaults")
    return {
        "shutdown_pay_percent": global_data.get("shutdown_pay_percent", DEFAULT_SHUTDOWN_PAY_PERCENT),
        "default_workplace_hours_policy": dict(
            global_data.get("default_workplace_hours_policy")
            or _default_global_settings()["default_workplace_hours_policy"]
        ),
        "site_benefits_defaults": normalize_site_benefits(
            global_benefits if isinstance(global_benefits, dict) else DEFAULT_SITE_BENEFITS
        ),
        "site_settings": site_settings,
        "identity_insurance_ledger": {},
        "edi_insurance": _default_edi_insurance_config(),
        "updated_at": "",
    }


def _default_edi_insurance_config() -> dict[str, Any]:
    return {
        "use_edi_premiums": False,
        "certificate_path": "",
        "business_registration_no": "",
        "api_endpoint_url": "",
        "api_connected": False,
    }


def get_edi_insurance_config(*, tenant_id: str | None = None) -> dict[str, Any]:
    """법인 EDI 보험료 연동 설정."""
    tenant = load_tenant_payroll_settings(tenant_id)
    raw = tenant.get("edi_insurance")
    out = _default_edi_insurance_config()
    if isinstance(raw, dict):
        out.update(raw)
    return out


def save_edi_insurance_config(
    *,
    use_edi_premiums: bool | None = None,
    certificate_path: str | None = None,
    business_registration_no: str | None = None,
    api_endpoint_url: str | None = None,
    api_connected: bool | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    tenant = load_tenant_payroll_settings(tenant_id)
    cfg = get_edi_insurance_config(tenant_id=tenant_id)
    if use_edi_premiums is not None:
        cfg["use_edi_premiums"] = bool(use_edi_premiums)
    if certificate_path is not None:
        cfg["certificate_path"] = str(certificate_path).strip()
    if business_registration_no is not None:
        cfg["business_registration_no"] = str(business_registration_no).strip()
    if api_endpoint_url is not None:
        cfg["api_endpoint_url"] = str(api_endpoint_url).strip()
    if api_connected is not None:
        cfg["api_connected"] = bool(api_connected)
    tenant["edi_insurance"] = cfg
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return cfg


def _read_tenant_settings_file(path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_tenant_settings()
        out = _default_tenant_settings()
        out.update(data)
        if not isinstance(out.get("site_settings"), dict):
            out["site_settings"] = {}
        return out
    except (OSError, json.JSONDecodeError):
        return _default_tenant_settings()


def _write_tenant_settings(tenant_id: str, data: dict[str, Any]) -> None:
    path = _tenant_settings_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_tenant_payroll_settings(tenant_id: str | None = None) -> dict[str, Any]:
    """법인(테넌트) 급여 산출 설정 — 없으면 전역 기본에서 시드."""
    tid = _resolve_tenant_id(tenant_id)
    path = _tenant_settings_path(tid)
    if path.is_file():
        return _read_tenant_settings_file(path)
    seeded = _default_tenant_settings()
    _write_tenant_settings(tid, seeded)
    return seeded


def load_payroll_settings(tenant_id: str | None = None) -> dict[str, Any]:
    """UI·하위 호환 — 법인 설정을 기존 키 형태로 반환."""
    tenant = load_tenant_payroll_settings(tenant_id)
    global_data = _load_global_settings()
    site_settings = tenant.get("site_settings") or {}
    workplace_hours_policies: dict[str, Any] = {}
    if isinstance(site_settings, dict):
        for wp, raw in site_settings.items():
            if isinstance(raw, dict) and isinstance(raw.get("workplace_hours_policy"), dict):
                workplace_hours_policies[str(wp)] = dict(raw["workplace_hours_policy"])
    tenant_shutdown = tenant.get("shutdown_pay_percent")
    tenant_hours = tenant.get("default_workplace_hours_policy")
    return {
        "shutdown_pay_percent": (
            tenant_shutdown
            if tenant_shutdown is not None
            else global_data.get("shutdown_pay_percent", DEFAULT_SHUTDOWN_PAY_PERCENT)
        ),
        "default_workplace_hours_policy": (
            tenant_hours
            if isinstance(tenant_hours, dict)
            else global_data.get("default_workplace_hours_policy")
        ),
        "workplace_hours_policies": workplace_hours_policies,
        "site_settings": site_settings,
        "updated_at": tenant.get("updated_at", ""),
    }


def clamp_shutdown_pay_percent(value: float) -> float:
    """법정 최저(70%) 미만은 허용하지 않음."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = DEFAULT_SHUTDOWN_PAY_PERCENT
    if v < LEGAL_MIN_SHUTDOWN_PAY_PERCENT:
        v = LEGAL_MIN_SHUTDOWN_PAY_PERCENT
    if v > 100.0:
        v = 100.0
    return round(v, 2)


def _normalize_hours_policy(raw: dict[str, Any] | None) -> dict[str, Any]:
    from services.workplace_hours import normalize_policy

    return normalize_policy(raw)


def resolve_payroll_calc_settings(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """사업장 급여 산출 설정 — site → tenant → global."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    tenant = load_tenant_payroll_settings(tenant_id)
    global_data = _load_global_settings()
    site_raw = (tenant.get("site_settings") or {}).get(wp) or {}
    if not isinstance(site_raw, dict):
        site_raw = {}

    if site_raw.get("shutdown_pay_percent") is not None:
        shutdown = site_raw["shutdown_pay_percent"]
        shutdown_source: SettingsSource = "site"
    elif tenant.get("shutdown_pay_percent") is not None:
        shutdown = tenant["shutdown_pay_percent"]
        shutdown_source = "tenant"
    else:
        shutdown = global_data.get("shutdown_pay_percent", DEFAULT_SHUTDOWN_PAY_PERCENT)
        shutdown_source = "global"

    if isinstance(site_raw.get("workplace_hours_policy"), dict):
        hours_policy = site_raw["workplace_hours_policy"]
        hours_source: SettingsSource = "site"
    elif isinstance(tenant.get("default_workplace_hours_policy"), dict):
        hours_policy = tenant["default_workplace_hours_policy"]
        hours_source = "tenant"
    else:
        hours_policy = global_data.get("default_workplace_hours_policy")
        hours_source = "global"

    has_site_override = bool(
        site_raw.get("shutdown_pay_percent") is not None
        or isinstance(site_raw.get("workplace_hours_policy"), dict)
    )

    return {
        "workplace": wp,
        "shutdown_pay_percent": clamp_shutdown_pay_percent(float(shutdown)),
        "workplace_hours_policy": _normalize_hours_policy(hours_policy),
        "shutdown_source": shutdown_source,
        "hours_source": hours_source,
        "has_site_override": has_site_override,
    }


def settings_source_label(source: SettingsSource) -> str:
    return {"site": "사업장 개별", "tenant": "법인 기본", "global": "전역 기본"}.get(
        source, source
    )


def get_shutdown_pay_percent(
    workplace: str | None = None,
    *,
    tenant_id: str | None = None,
) -> float:
    if workplace and str(workplace).strip():
        return resolve_payroll_calc_settings(workplace, tenant_id=tenant_id)["shutdown_pay_percent"]
    tenant = load_tenant_payroll_settings(tenant_id)
    global_data = _load_global_settings()
    raw = tenant.get("shutdown_pay_percent")
    if raw is None:
        raw = global_data.get("shutdown_pay_percent", DEFAULT_SHUTDOWN_PAY_PERCENT)
    return clamp_shutdown_pay_percent(float(raw))


def save_shutdown_pay_percent(percent: float, *, tenant_id: str | None = None) -> float:
    """법인 기본 휴업수당 지급률 저장."""
    applied = clamp_shutdown_pay_percent(percent)
    tenant = load_tenant_payroll_settings(tenant_id)
    tenant["shutdown_pay_percent"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def save_site_shutdown_pay_percent(
    workplace: str,
    percent: float,
    *,
    tenant_id: str | None = None,
) -> float:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    applied = clamp_shutdown_pay_percent(percent)
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    entry["shutdown_pay_percent"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def get_workplace_hours_policy(workplace: str, *, tenant_id: str | None = None) -> dict[str, Any] | None:
    """사업장별 저장 정책. 없으면 None."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return None
    site_raw = (load_tenant_payroll_settings(tenant_id).get("site_settings") or {}).get(wp)
    if not isinstance(site_raw, dict):
        return None
    raw = site_raw.get("workplace_hours_policy")
    return raw if isinstance(raw, dict) else None


def save_workplace_hours_policy(
    workplace: str,
    *,
    mode: str,
    hours: float,
    tenant_id: str | None = None,
    daily_hours: float | None = None,
    break_minutes: float | None = None,
) -> dict[str, Any]:
    """사업장별 월 기본근로시간 정책 저장."""
    from services.workplace_hours import MODE_CHOICES, normalize_policy

    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    if mode not in MODE_CHOICES:
        raise ValueError("산출 방식이 올바르지 않습니다.")
    try:
        h = float(hours)
    except (TypeError, ValueError):
        h = 209.0
    if h <= 0:
        h = 209.0

    payload: dict[str, Any] = {"mode": mode, "hours": h}
    if daily_hours is not None:
        payload["daily_hours"] = daily_hours
    if break_minutes is not None:
        payload["break_minutes"] = break_minutes
    applied = normalize_policy(payload)
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    entry["workplace_hours_policy"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def clear_workplace_hours_policy(workplace: str, *, tenant_id: str | None = None) -> None:
    """사업장별 근로시간 개별 설정만 삭제."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings")
    if not isinstance(site_settings, dict) or wp not in site_settings:
        return
    entry = site_settings.get(wp)
    if isinstance(entry, dict) and "workplace_hours_policy" in entry:
        del entry["workplace_hours_policy"]
        if not entry:
            del site_settings[wp]
        _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


def clear_site_payroll_settings(workplace: str, *, tenant_id: str | None = None) -> None:
    """사업장 개별 설정 전체 삭제 → 법인/전역 기본 적용."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings")
    if isinstance(site_settings, dict) and wp in site_settings:
        del site_settings[wp]
        _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


def save_default_workplace_hours_policy(
    *,
    mode: str,
    hours: float,
    tenant_id: str | None = None,
    daily_hours: float | None = None,
    break_minutes: float | None = None,
) -> dict[str, Any]:
    from services.workplace_hours import MODE_CHOICES, normalize_policy

    if mode not in MODE_CHOICES:
        raise ValueError("산출 방식이 올바르지 않습니다.")
    payload: dict[str, Any] = {"mode": mode, "hours": float(hours)}
    if daily_hours is not None:
        payload["daily_hours"] = daily_hours
    if break_minutes is not None:
        payload["break_minutes"] = break_minutes
    applied = normalize_policy(payload)
    tenant = load_tenant_payroll_settings(tenant_id)
    tenant["default_workplace_hours_policy"] = applied
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def copy_site_settings_from_tenant_default(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """법인 기본값을 사업장 개별 설정으로 복사."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    tenant = load_tenant_payroll_settings(tenant_id)
    global_data = _load_global_settings()
    shutdown = tenant.get("shutdown_pay_percent")
    if shutdown is None:
        shutdown = global_data.get("shutdown_pay_percent", DEFAULT_SHUTDOWN_PAY_PERCENT)
    hours = tenant.get("default_workplace_hours_policy")
    if not isinstance(hours, dict):
        hours = global_data.get("default_workplace_hours_policy")
    site_settings = tenant.setdefault("site_settings", {})
    tenant_benefits = tenant.get("site_benefits_defaults")
    site_settings[wp] = {
        "shutdown_pay_percent": clamp_shutdown_pay_percent(float(shutdown)),
        "workplace_hours_policy": _normalize_hours_policy(hours),
    }
    if isinstance(tenant_benefits, dict):
        from core.payroll.site_benefits import normalize_site_benefits

        site_settings[wp]["site_benefits"] = normalize_site_benefits(tenant_benefits)
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return resolve_payroll_calc_settings(wp, tenant_id=tenant_id)


def apply_tenant_defaults_to_all_sites(
    *,
    workplaces: list[str] | None = None,
    tenant_id: str | None = None,
) -> int:
    """법인 기본값을 모든 사업장에 일괄 적용."""
    wps = workplaces or list_config_workplaces()
    count = 0
    for wp in wps:
        copy_site_settings_from_tenant_default(wp, tenant_id=tenant_id)
        count += 1
    return count


def list_site_payroll_overview(*, tenant_id: str | None = None) -> list[dict[str, Any]]:
    """설정 화면용 — 사업장별 적용 설정·출처."""
    from services.workplace_hours import MODE_LABELS

    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings") or {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append_row(wp: str) -> None:
        canon = canonical_scope_workplace(wp)
        if not canon or canon in seen:
            return
        seen.add(canon)
        resolved = resolve_payroll_calc_settings(canon, tenant_id=tenant_id)
        pol = resolved["workplace_hours_policy"]
        rows.append(
            {
                "workplace": canon,
                "shutdown_pay_percent": resolved["shutdown_pay_percent"],
                "shutdown_source": resolved["shutdown_source"],
                "mode": pol["mode"],
                "mode_label": MODE_LABELS.get(pol["mode"], pol["mode"]),
                "hours": pol["hours"],
                "hours_source": resolved["hours_source"],
                "is_custom": resolved["has_site_override"],
            }
        )

    for wp in list_config_workplaces():
        _append_row(wp)
    if isinstance(site_settings, dict):
        for wp in sorted(site_settings.keys()):
            _append_row(str(wp))
    return rows


def shutdown_pay_legal_notice() -> str:
    return (
        "근로기준법 제46조(휴업수당): 사업주의 귀책으로 휴업 시 "
        f"평균임금의 {LEGAL_MIN_SHUTDOWN_PAY_PERCENT:g}% 이상을 지급해야 합니다. "
        "본 프로그램은 청구서 총급여를 기준일 임금으로 보고, 휴업 일수에 대해 "
        "설정한 비율만큼 지급·나머지는 기본공제로 반영합니다."
    )


def _site_entry(tenant_id: str | None, workplace: str) -> dict[str, Any]:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return {}
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings") or {}
    if not isinstance(site_settings, dict):
        return {}
    entry = site_settings.get(wp)
    return entry if isinstance(entry, dict) else {}


def get_site_extra_settings(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """사업장 부가 설정 — 경비·미화 유형, 직군별 고정시간 템플릿."""
    from core.payroll.fixed_hours import DEFAULT_JOB_GROUP_TEMPLATES, normalize_fixed_hours_profile

    entry = _site_entry(tenant_id, workplace)
    templates_raw = entry.get("job_group_templates") or {}
    templates: dict[str, Any] = {}
    if isinstance(templates_raw, dict):
        for jg, raw in templates_raw.items():
            if isinstance(raw, dict):
                templates[str(jg).strip()] = normalize_fixed_hours_profile(
                    {**raw, "job_group": str(jg).strip(), "fixed_hours_mode": True}
                )
    return {
        "workplace": canonical_scope_workplace(str(workplace or "").strip()),
        "security_cleaning": bool(entry.get("security_cleaning")),
        "job_group_templates": templates,
        "default_templates": DEFAULT_JOB_GROUP_TEMPLATES,
    }


def save_site_security_cleaning_flag(
    workplace: str,
    enabled: bool,
    *,
    tenant_id: str | None = None,
) -> bool:
    """경비·미화 유형 사업장 플래그 저장."""
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    entry["security_cleaning"] = bool(enabled)
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return bool(enabled)


def save_job_group_fixed_hours_template(
    workplace: str,
    job_group: str,
    *,
    monthly_fixed_hours: float = 209,
    fixed_overtime_hours: float = 0,
    fixed_extension_hours: float = 0,
    pay_type: str = "hourly",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """사업장 직군별 고정 근로시간 템플릿 저장."""
    from core.payroll.fixed_hours import normalize_fixed_hours_profile, normalize_pay_type

    wp = canonical_scope_workplace(str(workplace or "").strip())
    jg = str(job_group or "").strip()
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    if not jg:
        raise ValueError("직군을 입력하세요.")
    applied = normalize_fixed_hours_profile(
        {
            "fixed_hours_mode": True,
            "job_group": jg,
            "monthly_fixed_hours": monthly_fixed_hours,
            "fixed_overtime_hours": fixed_overtime_hours,
            "fixed_extension_hours": fixed_extension_hours,
            "pay_type": normalize_pay_type(pay_type),
        }
    )
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    templates = entry.setdefault("job_group_templates", {})
    if not isinstance(templates, dict):
        templates = {}
        entry["job_group_templates"] = templates
    templates[jg] = applied
    entry["security_cleaning"] = True
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return applied


def get_tenant_site_benefits_defaults(*, tenant_id: str | None = None) -> dict[str, Any]:
    from core.payroll.site_benefits import normalize_site_benefits

    tenant = load_tenant_payroll_settings(tenant_id)
    raw = tenant.get("site_benefits_defaults")
    return normalize_site_benefits(raw if isinstance(raw, dict) else None)


def get_site_benefits_config(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    from core.payroll.site_benefits import resolve_site_benefits

    return resolve_site_benefits(workplace, tenant_id=tenant_id)


def save_tenant_site_benefits_defaults(
    *,
    workers_day: dict[str, Any] | None = None,
    identity_insurance: dict[str, Any] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    from core.payroll.site_benefits import (
        normalize_identity_insurance_config,
        normalize_site_benefits,
        normalize_workers_day_config,
    )

    tenant = load_tenant_payroll_settings(tenant_id)
    current = normalize_site_benefits(tenant.get("site_benefits_defaults"))
    if workers_day is not None:
        current["workers_day_allowance"] = normalize_workers_day_config(workers_day)
    if identity_insurance is not None:
        current["identity_guarantee_insurance"] = normalize_identity_insurance_config(
            identity_insurance
        )
    tenant["site_benefits_defaults"] = current
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return current


def save_site_benefits_config(
    workplace: str,
    *,
    workers_day: dict[str, Any] | None = None,
    identity_insurance: dict[str, Any] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    from core.payroll.site_benefits import (
        normalize_identity_insurance_config,
        normalize_site_benefits,
        normalize_workers_day_config,
        resolve_site_benefits,
    )

    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        raise ValueError("사업장명을 입력하세요.")
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.setdefault("site_settings", {})
    entry = site_settings.setdefault(wp, {})
    if not isinstance(entry, dict):
        entry = {}
        site_settings[wp] = entry
    current = normalize_site_benefits(entry.get("site_benefits"))
    if workers_day is not None:
        current["workers_day_allowance"] = normalize_workers_day_config(workers_day)
    if identity_insurance is not None:
        current["identity_guarantee_insurance"] = normalize_identity_insurance_config(
            identity_insurance
        )
    entry["site_benefits"] = current
    _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)
    return resolve_site_benefits(wp, tenant_id=tenant_id)


def clear_site_benefits_config(workplace: str, *, tenant_id: str | None = None) -> None:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings")
    if not isinstance(site_settings, dict) or wp not in site_settings:
        return
    entry = site_settings.get(wp)
    if isinstance(entry, dict) and "site_benefits" in entry:
        del entry["site_benefits"]
        if not entry:
            del site_settings[wp]
        _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


def clear_job_group_template(
    workplace: str,
    job_group: str,
    *,
    tenant_id: str | None = None,
) -> None:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    jg = str(job_group or "").strip()
    if not wp or not jg:
        return
    tenant = load_tenant_payroll_settings(tenant_id)
    site_settings = tenant.get("site_settings")
    if not isinstance(site_settings, dict):
        return
    entry = site_settings.get(wp)
    if not isinstance(entry, dict):
        return
    templates = entry.get("job_group_templates")
    if isinstance(templates, dict) and jg in templates:
        del templates[jg]
        _write_tenant_settings(_resolve_tenant_id(tenant_id), tenant)


# 하위 호환
SETTINGS_PATH = GLOBAL_SETTINGS_PATH
