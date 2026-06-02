"""
fixed_hours.py - 근로계약서·사업장 직군별 고정 근로시간 (경비·미화 등)

우선순위: 근로계약 개별 설정 → 사업장 직군 템플릿(경비·미화) → 청구서/사업장 정책
"""

from __future__ import annotations

from typing import Any

from utils import STANDARD_MONTHLY_HOURS, safe_number

PAY_TYPE_HOURLY = "hourly"
PAY_TYPE_MONTHLY_SALARY = "monthly_salary"

PAY_TYPE_LABELS: dict[str, str] = {
    PAY_TYPE_HOURLY: "시급",
    PAY_TYPE_MONTHLY_SALARY: "연봉직",
}

PAY_TYPE_CHOICES: tuple[str, ...] = (PAY_TYPE_HOURLY, PAY_TYPE_MONTHLY_SALARY)

# 경비·미화 사업장 기본 직군 템플릿
DEFAULT_JOB_GROUP_TEMPLATES: dict[str, dict[str, Any]] = {
    "경비": {
        "fixed_hours_mode": True,
        "monthly_fixed_hours": 209,
        "fixed_overtime_hours": 0,
        "fixed_extension_hours": 0,
        "pay_type": PAY_TYPE_HOURLY,
    },
    "미화": {
        "fixed_hours_mode": True,
        "monthly_fixed_hours": 209,
        "fixed_overtime_hours": 0,
        "fixed_extension_hours": 0,
        "pay_type": PAY_TYPE_HOURLY,
    },
    "관리": {
        "fixed_hours_mode": True,
        "monthly_fixed_hours": 209,
        "fixed_overtime_hours": 0,
        "fixed_extension_hours": 0,
        "pay_type": PAY_TYPE_MONTHLY_SALARY,
    },
}

FIXED_HOURS_SOURCE_CONTRACT = "근로계약서 기준 고정"
FIXED_HOURS_SOURCE_TEMPLATE = "사업장 직군 템플릿"


def normalize_pay_type(value: Any) -> str:
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return PAY_TYPE_HOURLY
    if "연봉" in text or text in ("monthly_salary", "monthly", "salary"):
        return PAY_TYPE_MONTHLY_SALARY
    if text in PAY_TYPE_CHOICES:
        return text
    return PAY_TYPE_HOURLY


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in ("1", "true", "yes", "y", "예", "사용", "on")


def normalize_fixed_hours_profile(raw: dict[str, Any] | None) -> dict[str, Any]:
    """고정 근로시간 프로필 정규화."""
    if not isinstance(raw, dict):
        raw = {}
    monthly = safe_number(raw.get("monthly_fixed_hours"), 0.0)
    daily = safe_number(raw.get("daily_fixed_hours"), 0.0)
    if monthly <= 0 and daily > 0:
        monthly = daily * 26
    if monthly <= 0:
        monthly = float(STANDARD_MONTHLY_HOURS)
    return {
        "fixed_hours_mode": _as_bool(raw.get("fixed_hours_mode")),
        "monthly_fixed_hours": round(monthly, 4),
        "daily_fixed_hours": round(daily, 4) if daily > 0 else 0.0,
        "fixed_overtime_hours": max(0.0, safe_number(raw.get("fixed_overtime_hours"), 0.0)),
        "fixed_extension_hours": max(0.0, safe_number(raw.get("fixed_extension_hours"), 0.0)),
        "pay_type": normalize_pay_type(raw.get("pay_type")),
        "job_group": str(raw.get("job_group") or "").strip(),
    }


def infer_job_group_from_roster(emp_roster: dict[str, Any] | None) -> str:
    """명부 업무·직책 등에서 직군 추정."""
    if not isinstance(emp_roster, dict):
        return ""
    for field in ("직군", "업무", "직책", "직무"):
        text = str(emp_roster.get(field) or "").strip()
        if not text:
            continue
        compact = text.replace(" ", "")
        for key in DEFAULT_JOB_GROUP_TEMPLATES:
            if key in compact:
                return key
        if "경비" in compact or "보안" in compact:
            return "경비"
        if "미화" in compact or "청소" in compact:
            return "미화"
        if "관리" in compact or "소장" in compact:
            return "관리"
    emp_type = str(emp_roster.get("고용형태") or "")
    if "연봉" in emp_type.replace(" ", ""):
        return "관리"
    return ""


def contract_to_fixed_hours_profile(contract: dict[str, Any]) -> dict[str, Any]:
    """HR 근로계약 레코드 → 고정시간 프로필."""
    return normalize_fixed_hours_profile(
        {
            "fixed_hours_mode": contract.get("fixed_hours_mode"),
            "monthly_fixed_hours": contract.get("monthly_fixed_hours"),
            "daily_fixed_hours": contract.get("daily_fixed_hours"),
            "fixed_overtime_hours": contract.get("fixed_overtime_hours"),
            "fixed_extension_hours": contract.get("fixed_extension_hours"),
            "pay_type": contract.get("pay_type"),
            "job_group": contract.get("job_group"),
        }
    )


def normalize_contract_fixed_hours_fields(contract: dict[str, Any]) -> None:
    """근로계약 저장 시 고정시간 필드 정규화 (in-place)."""
    prof = normalize_fixed_hours_profile(contract)
    contract["fixed_hours_mode"] = prof["fixed_hours_mode"]
    contract["monthly_fixed_hours"] = prof["monthly_fixed_hours"]
    if prof["daily_fixed_hours"] > 0:
        contract["daily_fixed_hours"] = prof["daily_fixed_hours"]
    contract["fixed_overtime_hours"] = prof["fixed_overtime_hours"]
    contract["fixed_extension_hours"] = prof["fixed_extension_hours"]
    contract["pay_type"] = prof["pay_type"]
    if prof["job_group"]:
        contract["job_group"] = prof["job_group"]


def find_active_contract(
    employee_name: str,
    contracts: list[dict[str, Any]] | None,
    *,
    workplace: str = "",
) -> dict[str, Any] | None:
    """유효 근로계약 1건 (이름 일치, fixed_hours_mode 우선)."""
    if not contracts:
        return None
    name_key = str(employee_name or "").strip().replace(" ", "")
    if not name_key:
        return None
    wp = str(workplace or "").strip()
    candidates: list[dict[str, Any]] = []
    for c in contracts:
        if not isinstance(c, dict):
            continue
        if str(c.get("status") or "유효").strip() not in ("유효", "active", ""):
            continue
        cname = str(c.get("employee_name") or "").strip().replace(" ", "")
        if cname != name_key:
            continue
        site = str(c.get("site_name") or c.get("department") or "").strip()
        if wp and site and wp not in site and site not in wp:
            continue
        candidates.append(c)
    if not candidates:
        return None
    fixed = [c for c in candidates if _as_bool(c.get("fixed_hours_mode"))]
    return fixed[0] if fixed else candidates[0]


def load_hr_contracts(*, tenant_id: str | None = None) -> list[dict[str, Any]]:
    """HR 모듈에서 근로계약 목록 로드."""
    try:
        from core.module_store import load_module_db
        from core.tenant_store import get_active_tenant_id

        tid = str(tenant_id or get_active_tenant_id() or "default").strip()
        db = load_module_db("hr", tid, {"contracts": []})
        rows = db.get("contracts") or []
        return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []


def get_site_fixed_hours_settings(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    from services.payroll_settings_store import get_site_extra_settings

    return get_site_extra_settings(workplace, tenant_id=tenant_id)


def resolve_job_group_template(
    job_group: str,
    site_settings: dict[str, Any],
) -> dict[str, Any] | None:
    """사업장 직군 템플릿 — security_cleaning 사업장만."""
    if not site_settings.get("security_cleaning"):
        return None
    jg = str(job_group or "").strip()
    if not jg:
        return None
    templates = site_settings.get("job_group_templates") or {}
    if not isinstance(templates, dict):
        templates = {}
    raw = templates.get(jg)
    if isinstance(raw, dict):
        return normalize_fixed_hours_profile({**raw, "job_group": jg, "fixed_hours_mode": True})
    default = DEFAULT_JOB_GROUP_TEMPLATES.get(jg)
    if default:
        return normalize_fixed_hours_profile({**default, "job_group": jg})
    return None


def resolve_employee_fixed_hours(
    *,
    employee_name: str,
    workplace: str = "",
    job_group: str = "",
    emp_roster: dict[str, Any] | None = None,
    contracts: list[dict[str, Any]] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any] | None:
    """
    직원별 적용 고정 근로시간 프로필.

    Returns:
        None — 고정시간 미적용
        dict — fixed_hours_mode=True 프로필 + source, source_label
    """
    jg = str(job_group or "").strip() or infer_job_group_from_roster(emp_roster)
    contract_list = contracts if contracts is not None else load_hr_contracts(tenant_id=tenant_id)
    contract = find_active_contract(employee_name, contract_list, workplace=workplace)

    if contract:
        prof = contract_to_fixed_hours_profile(contract)
        if not jg and prof["job_group"]:
            jg = prof["job_group"]
        if prof["fixed_hours_mode"]:
            return {
                **prof,
                "source": "contract",
                "source_label": FIXED_HOURS_SOURCE_CONTRACT,
                "contract_id": contract.get("id"),
            }
        if not jg:
            jg = str(contract.get("job_group") or "").strip()

    site = get_site_fixed_hours_settings(workplace, tenant_id=tenant_id)
    template = resolve_job_group_template(jg, site)
    if template:
        return {
            **template,
            "source": "template",
            "source_label": FIXED_HOURS_SOURCE_TEMPLATE,
            "job_group": jg,
        }

    if contract and not _as_bool(contract.get("fixed_hours_mode")):
        prof = contract_to_fixed_hours_profile(contract)
        if prof["pay_type"] == PAY_TYPE_MONTHLY_SALARY:
            return {
                **prof,
                "fixed_hours_mode": True,
                "source": "contract",
                "source_label": FIXED_HOURS_SOURCE_CONTRACT,
                "contract_id": contract.get("id"),
            }
    return None


def apply_fixed_hours_to_invoice(
    inv: dict[str, Any],
    profile: dict[str, Any],
    *,
    workplace: str = "",
) -> dict[str, Any]:
    """
    고정 근로시간을 청구서 dict에 반영.

    - 월 기본근로시간 → _monthly_work_hours
    - fixed_overtime_hours(특근) → special_hours
    - fixed_extension_hours(연장) → ot_hours
    - 청구서 원본은 _invoice_* 키에 보존 (검증용)
    """
    if not profile or not profile.get("fixed_hours_mode"):
        return profile or {}

    for key in ("work_days", "base_days", "ot_hours", "special_hours", "special_ext_hours"):
        if key in inv and f"_invoice_{key}" not in inv:
            inv[f"_invoice_{key}"] = inv[key]

    monthly_h = float(profile.get("monthly_fixed_hours") or STANDARD_MONTHLY_HOURS)
    invoice_h = safe_number(
        inv.get("_invoice_work_days") or inv.get("_invoice_base_days"),
        0.0,
    )
    if inv.get("_preserve_reference_hours") and invoice_h > 0:
        monthly_h = invoice_h
    elif invoice_h > 0 and invoice_h < monthly_h - 0.01:
        monthly_h = invoice_h
    inv["_monthly_work_hours"] = monthly_h
    inv["_monthly_hours_source"] = profile.get("source_label", FIXED_HOURS_SOURCE_CONTRACT)
    inv["_fixed_hours_mode"] = True
    inv["_fixed_hours_source"] = profile.get("source", "")
    inv["_fixed_hours_pay_type"] = profile.get("pay_type", PAY_TYPE_HOURLY)
    inv["_fixed_hours_job_group"] = profile.get("job_group", "")

    inv["base_days"] = monthly_h
    inv["work_days"] = monthly_h

    ot_fixed = safe_number(profile.get("fixed_extension_hours"), 0.0)
    special_fixed = safe_number(profile.get("fixed_overtime_hours"), 0.0)
    if ot_fixed > 0:
        inv["ot_hours"] = ot_fixed
    if special_fixed > 0:
        inv["special_hours"] = special_fixed

    wp = str(workplace or inv.get("workplace") or "").strip()
    if wp:
        inv["workplace"] = wp

    return profile


def fixed_hours_audit_flags(
    inv: dict[str, Any],
    profile: dict[str, Any] | None,
) -> list[str]:
    """자동검열용 — 고정시간 vs 청구서 대조."""
    if not profile or not inv.get("_fixed_hours_mode"):
        return []
    flags: list[str] = [profile.get("source_label") or FIXED_HOURS_SOURCE_CONTRACT]
    jg = profile.get("job_group") or inv.get("_fixed_hours_job_group")
    if jg:
        flags[0] = f"{flags[0]} ({jg})"
    pay_label = PAY_TYPE_LABELS.get(profile.get("pay_type", ""), "")
    if pay_label:
        flags.append(f"급여형태: {pay_label}")

    inv_ot = safe_number(inv.get("_invoice_ot_hours"), safe_number(inv.get("ot_hours"), 0))
    inv_special = safe_number(
        inv.get("_invoice_special_hours"), safe_number(inv.get("special_hours"), 0)
    )
    fixed_ot = safe_number(profile.get("fixed_extension_hours"), 0)
    fixed_special = safe_number(profile.get("fixed_overtime_hours"), 0)

    if fixed_ot > 0 and inv_ot > 0 and abs(inv_ot - fixed_ot) > 0.01:
        flags.append(f"청구서 연장({inv_ot:g}h) ≠ 계약 고정({fixed_ot:g}h)")
    if fixed_special > 0 and inv_special > 0 and abs(inv_special - fixed_special) > 0.01:
        flags.append(f"청구서 특근({inv_special:g}h) ≠ 계약 고정({fixed_special:g}h)")

    inv_work = safe_number(inv.get("_invoice_work_days"), 0)
    monthly = float(profile.get("monthly_fixed_hours") or 0)
    if inv_work > 0 and monthly > 0 and abs(inv_work - monthly) > monthly * 0.05:
        flags.append(f"청구서 근무시간({inv_work:g}h) ≠ 계약 월시간({monthly:g}h)")

    return flags
