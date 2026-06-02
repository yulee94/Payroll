"""
core/executive_policy.py - 임원(경영진) 식별 — 명부·급여 레코드
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from core.config import BASE_DIR
from roster_constants import norm_name_key

POLICY_PATH = BASE_DIR / "config" / "access_policy.json"

_EXECUTIVE_FIELDS = ("임원", "임원여부", "임원구분", "임원 해당")
_POSITIVE_VALUES = frozenset({"Y", "YES", "O", "1", "TRUE", "예", "임원", "해당"})


@lru_cache(maxsize=1)
def _policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    try:
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def executive_title_keywords() -> tuple[str, ...]:
    raw = _policy().get("executive_title_keywords") or []
    if isinstance(raw, list) and raw:
        return tuple(str(k).strip() for k in raw if str(k).strip())
    return (
        "대표",
        "부사장",
        "사장",
        "회장",
        "전무",
        "상무",
        "이사",
        "본부장",
    )


def _field_marks_executive(value: Any) -> bool:
    v = str(value or "").strip().upper()
    if not v:
        return False
    return v in _POSITIVE_VALUES or v == "임원"


def _title_marks_executive(title: str) -> bool:
    t = str(title or "").strip()
    if not t:
        return False
    upper = t.upper()
    for kw in executive_title_keywords():
        if kw.upper() in upper or kw in t:
            return True
    return False


def is_executive_roster_row(row: dict[str, Any]) -> bool:
    """명부 행이 임원인지 (임원 열 또는 직책 키워드)."""
    for field in _EXECUTIVE_FIELDS:
        if field in row and _field_marks_executive(row.get(field)):
            return True
    if _title_marks_executive(str(row.get("직책") or "")):
        return True
    return False


def is_executive_payroll_record(rec: dict[str, Any]) -> bool:
    """급여 스냅샷 레코드가 임원인지."""
    if rec.get("is_executive") is True:
        return True
    if rec.get("is_executive") is False:
        return False
    if _title_marks_executive(str(rec.get("직책") or rec.get("position") or "")):
        return True
    return False


def refresh_executive_name_index(rows: list[dict[str, Any]]) -> frozenset[str]:
    keys = {norm_name_key(r.get("성명") or r.get("name") or "") for r in rows if is_executive_roster_row(r)}
    keys.discard("")
    return frozenset(keys)


def is_executive_by_name(name: str, executive_keys: frozenset[str]) -> bool:
    k = norm_name_key(name)
    return bool(k) and k in executive_keys
