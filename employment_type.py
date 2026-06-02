"""
employment_type.py - 근로자 명부 고용형태(일용직·정규직 시급/연봉)
"""

from __future__ import annotations

from typing import Any

TYPE_DAILY = "일용직"
TYPE_REGULAR_HOURLY = "정규직(시급)"
TYPE_REGULAR_SALARY = "정규직(연봉)"

EMPLOYMENT_TYPE_CHOICES: tuple[str, ...] = (
    "",
    TYPE_DAILY,
    TYPE_REGULAR_HOURLY,
    TYPE_REGULAR_SALARY,
)

FILTER_ALL = "전체"
FILTER_REGULAR = "정규직"
FILTER_UNSET = "미분류"

EMPLOYMENT_FILTER_CHOICES: tuple[str, ...] = (
    FILTER_ALL,
    TYPE_DAILY,
    FILTER_REGULAR,
    TYPE_REGULAR_HOURLY,
    TYPE_REGULAR_SALARY,
    FILTER_UNSET,
)


def normalize_employment_type(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    compact = text.replace(" ", "")
    if compact in ("일용", "일용직", "일용근로", "일용근로자"):
        return TYPE_DAILY
    if "연봉" in compact or compact in ("연봉직", "정규직연봉", "정규연봉"):
        return TYPE_REGULAR_SALARY
    if "시급" in compact or compact in ("시급직", "정규직시급", "정규시급"):
        return TYPE_REGULAR_HOURLY
    if compact in ("정규", "정규직", "상용", "상용직"):
        return TYPE_REGULAR_HOURLY
    if text in EMPLOYMENT_TYPE_CHOICES:
        return text
    return text


def apply_employment_type_to_record(rec: dict[str, Any]) -> None:
    raw = rec.get("고용형태")
    if raw is not None and str(raw).strip():
        rec["고용형태"] = normalize_employment_type(raw)


def is_regular_employment(emp_type: str) -> bool:
    return emp_type in (TYPE_REGULAR_HOURLY, TYPE_REGULAR_SALARY)


def record_matches_employment_filter(rec: dict[str, Any], employment_filter: str) -> bool:
    filt = str(employment_filter or FILTER_ALL).strip()
    if filt == FILTER_ALL:
        return True
    emp = normalize_employment_type(rec.get("고용형태"))
    if filt == FILTER_UNSET:
        return not emp
    if filt == FILTER_REGULAR:
        return is_regular_employment(emp)
    return emp == normalize_employment_type(filt)


def record_matches_affiliate_filter(rec: dict[str, Any], affiliate_filter: str) -> bool:
    filt = str(affiliate_filter or FILTER_ALL).strip()
    if filt == FILTER_ALL:
        return True
    aff = str(rec.get("계열사") or "").strip()
    return aff == filt


def record_matches_name_filter(rec: dict[str, Any], name_query: str) -> bool:
    q = str(name_query or "").strip().replace(" ", "")
    if not q:
        return True
    name = str(rec.get("성명") or "").strip().replace(" ", "")
    return q in name


def record_matches_roster_filters(
    rec: dict[str, Any],
    *,
    employment_filter: str = FILTER_ALL,
    affiliate_filter: str = FILTER_ALL,
    name_query: str = "",
    senior_filter: str = "전체",
    disability_filter: str = "전체",
) -> bool:
    from disability_employment import FILTER_DISABILITY_ALL, record_matches_disability_filter
    from senior_internship import FILTER_SENIOR_ALL, record_matches_senior_filter

    apply_employment_type_to_record(rec)
    return (
        record_matches_employment_filter(rec, employment_filter)
        and record_matches_affiliate_filter(rec, affiliate_filter)
        and record_matches_name_filter(rec, name_query)
        and record_matches_senior_filter(rec, senior_filter or FILTER_SENIOR_ALL)
        and record_matches_disability_filter(rec, disability_filter or FILTER_DISABILITY_ALL)
    )


def count_employment_stats(rows: list[dict[str, Any]]) -> dict[str, int]:
    stats = {
        "total": len(rows),
        TYPE_DAILY: 0,
        TYPE_REGULAR_HOURLY: 0,
        TYPE_REGULAR_SALARY: 0,
        FILTER_UNSET: 0,
    }
    for rec in rows:
        emp = normalize_employment_type(rec.get("고용형태"))
        if not emp:
            stats[FILTER_UNSET] += 1
        elif emp in stats:
            stats[emp] += 1
    stats[FILTER_REGULAR] = stats[TYPE_REGULAR_HOURLY] + stats[TYPE_REGULAR_SALARY]
    return stats


def distinct_affiliates(rows: list[dict[str, Any]]) -> list[str]:
    names = {str(r.get("계열사") or "").strip() for r in rows}
    return sorted(n for n in names if n)
