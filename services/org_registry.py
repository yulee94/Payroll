"""
services/org_registry.py - 계열사·사업장 조직 구조 및 필터
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.org_config import (
    canonical_scope_workplace,
    get_default_affiliate,
    list_config_affiliates,
    list_config_workplaces,
    scope_workplaces_match,
    workplace_to_affiliate_map,
)
from payroll_archive import load_snapshot_records

ALL_LABEL = "전체"


@dataclass(frozen=True)
class OrgSelection:
    affiliate: str = ALL_LABEL
    workplace: str = ALL_LABEL


@dataclass
class RecordSummary:
    employee_count: int = 0
    total_gross: int = 0
    total_net: int = 0
    total_deduction: int = 0
    leave_users: int = 0
    absence_users: int = 0


def resolve_workplace(rec: dict[str, Any]) -> str:
    wp = str(rec.get("workplace") or "").strip()
    if wp:
        return canonical_scope_workplace(wp)
    dept = str(rec.get("dept") or "").strip()
    if dept:
        return canonical_scope_workplace(dept)
    workplaces = list(workplace_to_affiliate_map().keys())
    if len(workplaces) == 1:
        return canonical_scope_workplace(workplaces[0])
    return "미분류"


def resolve_affiliate(rec: dict[str, Any]) -> str:
    aff = str(rec.get("affiliate") or rec.get("계열사") or "").strip()
    if aff:
        return aff
    wp = str(rec.get("workplace") or "").strip()
    mapping = workplace_to_affiliate_map()
    if wp and wp in mapping:
        return mapping[wp]
    return get_default_affiliate()


def enrich_record(rec: dict[str, Any]) -> dict[str, Any]:
    out = dict(rec)
    out["affiliate"] = resolve_affiliate(rec)
    out["workplace"] = resolve_workplace(rec)
    return out


def enrich_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_record(r) for r in records]


def _is_all(value: str) -> bool:
    return not value or value == ALL_LABEL


def matches_selection(rec: dict[str, Any], selection: OrgSelection) -> bool:
    row = enrich_record(rec)
    if not _is_all(selection.affiliate) and row["affiliate"] != selection.affiliate:
        return False
    if not _is_all(selection.workplace):
        scope_wp = str(rec.get("_scope_workplace") or "").strip()
        row_wp = scope_wp or str(row.get("workplace") or "").strip()
        if not scope_workplaces_match(selection.workplace, row_wp):
            return False
    return True


def filter_records(records: list[dict[str, Any]], selection: OrgSelection) -> list[dict[str, Any]]:
    return [r for r in records if matches_selection(r, selection)]


def summarize_records(records: list[dict[str, Any]]) -> RecordSummary:
    summary = RecordSummary()
    for r in records:
        summary.employee_count += 1
        summary.total_gross += int(r.get("gross_pay") or 0)
        summary.total_net += int(r.get("net_pay") or 0)
        summary.total_deduction += int(r.get("total_deduction") or 0)
        if float(r.get("leave_days") or 0) > 0:
            summary.leave_users += 1
        if float(r.get("unpaid_days") or 0) > 0:
            summary.absence_users += 1
    return summary


def _sorted_unique(values: set[str]) -> list[str]:
    return sorted(v for v in values if v)


def list_affiliate_options(records: list[dict[str, Any]] | None = None) -> list[str]:
    discovered: set[str] = set(list_config_affiliates())
    if records:
        for r in records:
            discovered.add(resolve_affiliate(r))
    return [ALL_LABEL] + _sorted_unique(discovered)


def list_workplace_options(
    records: list[dict[str, Any]] | None = None,
    affiliate: str = ALL_LABEL,
) -> list[str]:
    aff_key = "" if _is_all(affiliate) else affiliate
    discovered: set[str] = set(list_config_workplaces(aff_key))

    from services.payroll_scope import discover_scopes

    for scope in discover_scopes():
        if not _is_all(affiliate) and scope.affiliate != affiliate:
            continue
        discovered.add(canonical_scope_workplace(scope.workplace))

    if records:
        for r in records:
            row = enrich_record(r)
            if not _is_all(affiliate) and row["affiliate"] != affiliate:
                continue
            sw = str(r.get("_scope_workplace") or "").strip()
            discovered.add(canonical_scope_workplace(sw or row["workplace"]))
    return [ALL_LABEL] + _sorted_unique(discovered)


def load_records_for_period(period_or_key: str) -> list[dict[str, Any]]:
    if not period_or_key:
        return []
    import re

    # scope.key(= \x1f 포함)가 아니고 “YYYY-MM”일 경우 해당 월의 모든 scope 스냅샷을 합산합니다.
    if "\x1f" not in str(period_or_key) and re.match(r"^\d{4}-\d{2}$", period_or_key):
        return enrich_records(load_snapshot_records(period_or_key, None))

    from services.payroll_scope import PayrollScope

    scope = PayrollScope.try_parse_key(period_or_key)
    period = scope.period if scope else period_or_key
    return enrich_records(load_snapshot_records(period, scope))


def group_by_workplace(records: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        key = resolve_workplace(r)
        buckets.setdefault(key, []).append(r)
    return sorted(buckets.items(), key=lambda x: (-len(x[1]), x[0]))
