"""
core/org_config.py - 계열사·사업장 설정 (순환 import 방지용 경량 모듈)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.config import BASE_DIR

ORG_CONFIG_PATH = BASE_DIR / "config" / "organizations.json"


def _load_config_raw() -> dict[str, Any]:
    if not ORG_CONFIG_PATH.is_file():
        return {"default_affiliate": "COSS Group", "affiliates": []}
    try:
        return json.loads(ORG_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"default_affiliate": "COSS Group", "affiliates": []}


@lru_cache(maxsize=1)
def get_default_affiliate() -> str:
    cfg = _load_config_raw()
    return str(cfg.get("default_affiliate") or "COSS Group").strip()


@lru_cache(maxsize=1)
def workplace_to_affiliate_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in _load_config_raw().get("affiliates") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        for wp in item.get("workplaces") or []:
            wp_name = str(wp).strip()
            if wp_name:
                mapping[wp_name] = name
    return mapping


def list_config_affiliates() -> list[str]:
    names: set[str] = set()
    for item in _load_config_raw().get("affiliates") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name:
                names.add(name)
    default = get_default_affiliate()
    if default:
        names.add(default)
    return sorted(names)


def list_config_workplaces(affiliate: str = "") -> list[str]:
    """드롭다운·설정용 사업장(별칭 통합 후 대표명만)."""
    out: set[str] = set()
    for item in _load_config_raw().get("affiliates") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if affiliate and name != affiliate:
            continue
        for wp in item.get("workplaces") or []:
            wp_name = str(wp).strip()
            if wp_name:
                out.add(canonical_scope_workplace(wp_name))
    return sorted(out)


@lru_cache(maxsize=1)
def _workplace_alias_groups_uncached() -> dict[str, frozenset[str]]:
    """
    동일 사업장 별칭 — key: 대표(표시)명, value: 동일 취급할 모든 폴더·표기명.
    """
    groups: dict[str, set[str]] = {}
    raw = _load_config_raw().get("workplace_aliases") or {}
    if isinstance(raw, dict):
        for canon, aliases in raw.items():
            canon_s = str(canon).strip()
            if not canon_s:
                continue
            bucket = groups.setdefault(canon_s, set())
            bucket.add(canon_s)
            if isinstance(aliases, str):
                aliases = [aliases]
            for a in aliases or []:
                a_s = str(a).strip()
                if a_s:
                    bucket.add(a_s)
    for item in _load_config_raw().get("affiliates") or []:
        if not isinstance(item, dict):
            continue
        for wp in item.get("workplaces") or []:
            wp_name = str(wp).strip()
            if not wp_name:
                continue
            placed = False
            for canon, names in groups.items():
                if wp_name in names:
                    names.add(wp_name)
                    placed = True
                    break
            if not placed:
                groups.setdefault(wp_name, {wp_name})
    return {c: frozenset(ns) for c, ns in groups.items()}


def workplace_alias_groups() -> dict[str, frozenset[str]]:
    return _workplace_alias_groups_uncached()


def canonical_scope_workplace(name: str) -> str:
    """폴더·필터·집계용 대표 사업장명."""
    s = (name or "").strip()
    if not s:
        return s
    for canon, names in workplace_alias_groups().items():
        if s in names:
            return canon
    return s


def scope_workplaces_match(nav_workplace: str, scope_workplace: str) -> bool:
    """드롭다운 선택 사업장과 출력 폴더 사업장이 동일 그룹인지."""
    if not nav_workplace or not scope_workplace:
        return nav_workplace == scope_workplace
    return canonical_scope_workplace(nav_workplace) == canonical_scope_workplace(scope_workplace)


def all_names_for_scope_workplace(canonical: str) -> frozenset[str]:
    """대표명에 해당하는 모든 폴더·표기명."""
    c = canonical_scope_workplace(canonical)
    return workplace_alias_groups().get(c, frozenset({c}))
