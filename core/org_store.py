"""
core/org_store.py - 고객사 조직도(팀·부서) 저장
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.org_positions import ORG_PLATFORM_IDS, normalize_position, position_label
from core.paths import app_data_dir

ORG_DIR = app_data_dir() / "org"


@dataclass
class OrgUnit:
    unit_id: str
    tenant_id: str
    name: str
    parent_id: str = ""
    sort_order: int = 0
    platform_ids: tuple[str, ...] = field(default_factory=tuple)
    head_user_id: str = ""
    notes: str = ""
    created_at: str = ""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _org_file(tenant_id: str) -> Path:
    ORG_DIR.mkdir(parents=True, exist_ok=True)
    return ORG_DIR / f"{str(tenant_id).strip()}.json"


def _empty_db(tenant_id: str) -> dict[str, Any]:
    return {"tenant_id": tenant_id, "units": {}, "root_id": ""}


def _load_raw(tenant_id: str) -> dict[str, Any]:
    path = _org_file(tenant_id)
    if not path.is_file():
        return _empty_db(tenant_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty_db(tenant_id)
        raw.setdefault("units", {})
        raw.setdefault("root_id", "")
        return raw
    except (OSError, json.JSONDecodeError):
        return _empty_db(tenant_id)


def _save_raw(tenant_id: str, data: dict[str, Any]) -> None:
    path = _org_file(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_unit(raw: dict[str, Any], tenant_id: str) -> OrgUnit:
    platforms = raw.get("platform_ids") or []
    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    return OrgUnit(
        unit_id=str(raw.get("unit_id") or ""),
        tenant_id=tenant_id,
        name=str(raw.get("name") or ""),
        parent_id=str(raw.get("parent_id") or ""),
        sort_order=int(raw.get("sort_order") or 0),
        platform_ids=tuple(p for p in platforms if p in ORG_PLATFORM_IDS),
        head_user_id=str(raw.get("head_user_id") or ""),
        notes=str(raw.get("notes") or ""),
        created_at=str(raw.get("created_at") or ""),
    )


def list_units(tenant_id: str) -> list[OrgUnit]:
    raw = _load_raw(tenant_id)
    units = raw.get("units") or {}
    out = [_to_unit(row, tenant_id) for row in units.values() if isinstance(row, dict)]
    return sorted(out, key=lambda u: (u.sort_order, u.name))


def get_unit(tenant_id: str, unit_id: str) -> OrgUnit | None:
    raw = _load_raw(tenant_id)
    row = (raw.get("units") or {}).get(str(unit_id).strip())
    if isinstance(row, dict):
        return _to_unit(row, tenant_id)
    return None


def get_root_unit_id(tenant_id: str) -> str:
    return str(_load_raw(tenant_id).get("root_id") or "")


def descendant_unit_ids(tenant_id: str, unit_id: str, *, include_self: bool = True) -> set[str]:
    """하위 팀 ID (재귀)."""
    units = list_units(tenant_id)
    by_parent: dict[str, list[str]] = {}
    for u in units:
        by_parent.setdefault(u.parent_id or "", []).append(u.unit_id)

    result: set[str] = set()
    stack = [unit_id] if include_self else list(by_parent.get(unit_id, []))
    while stack:
        cur = stack.pop()
        if cur in result:
            continue
        result.add(cur)
        stack.extend(by_parent.get(cur, []))
    if not include_self:
        result.discard(unit_id)
    return result


def create_unit(
    tenant_id: str,
    *,
    name: str,
    parent_id: str = "",
    platform_ids: tuple[str, ...] = (),
    notes: str = "",
) -> OrgUnit:
    tid = str(tenant_id).strip()
    label = str(name or "").strip()
    if not label:
        raise ValueError("팀·부서 이름을 입력하세요.")
    raw = _load_raw(tid)
    units: dict[str, Any] = raw.setdefault("units", {})
    pid = str(parent_id or "").strip()
    if pid and pid not in units:
        raise ValueError("상위 조직을 찾을 수 없습니다.")
    uid = uuid.uuid4().hex[:12]
    now = _now_iso()
    row = {
        "unit_id": uid,
        "name": label,
        "parent_id": pid,
        "sort_order": len(units),
        "platform_ids": list(platform_ids),
        "head_user_id": "",
        "notes": str(notes or ""),
        "created_at": now,
    }
    units[uid] = row
    if not raw.get("root_id"):
        raw["root_id"] = uid
    _save_raw(tid, raw)
    return _to_unit(row, tid)


def update_unit(
    tenant_id: str,
    unit_id: str,
    *,
    name: str | None = None,
    platform_ids: tuple[str, ...] | None = None,
    head_user_id: str | None = None,
    notes: str | None = None,
) -> OrgUnit:
    tid = str(tenant_id).strip()
    uid = str(unit_id).strip()
    raw = _load_raw(tid)
    units = raw.get("units") or {}
    row = units.get(uid)
    if not isinstance(row, dict):
        raise ValueError("조직을 찾을 수 없습니다.")
    if name is not None:
        label = str(name).strip()
        if not label:
            raise ValueError("팀·부서 이름을 입력하세요.")
        row["name"] = label
    if platform_ids is not None:
        row["platform_ids"] = [p for p in platform_ids if p in ORG_PLATFORM_IDS]
    if head_user_id is not None:
        row["head_user_id"] = str(head_user_id or "")
    if notes is not None:
        row["notes"] = str(notes or "")
    _save_raw(tid, raw)
    return _to_unit(row, tid)


def import_org_tree(tenant_id: str, units: list[dict[str, Any]], *, root_id: str = "") -> None:
    """부트스트랩·시드용 조직 트리 일괄 등록."""
    tid = str(tenant_id).strip()
    data = _empty_db(tid)
    store: dict[str, Any] = {}
    for row in units:
        uid = str(row.get("unit_id") or uuid.uuid4().hex[:12])
        store[uid] = {
            "unit_id": uid,
            "name": str(row.get("name") or ""),
            "parent_id": str(row.get("parent_id") or ""),
            "sort_order": int(row.get("sort_order") or 0),
            "platform_ids": list(row.get("platform_ids") or []),
            "head_user_id": str(row.get("head_user_id") or ""),
            "notes": str(row.get("notes") or ""),
            "created_at": str(row.get("created_at") or _now_iso()),
        }
    data["units"] = store
    data["root_id"] = root_id or (units[0]["unit_id"] if units else "")
    _save_raw(tid, data)


def unit_platform_ids(tenant_id: str, unit_id: str) -> frozenset[str]:
    unit = get_unit(tenant_id, unit_id)
    if unit is None:
        return frozenset()
    return frozenset(unit.platform_ids)


def effective_platform_ids_for_unit(tenant_id: str, unit_id: str) -> frozenset[str]:
    """팀 + 상위 조직에 할당된 플랫폼 합집합."""
    raw = _load_raw(tenant_id)
    units = raw.get("units") or {}
    result: set[str] = set()
    cur = str(unit_id or "").strip()
    seen: set[str] = set()
    while cur and cur not in seen:
        seen.add(cur)
        row = units.get(cur)
        if not isinstance(row, dict):
            break
        for p in row.get("platform_ids") or []:
            if p in ORG_PLATFORM_IDS:
                result.add(p)
        cur = str(row.get("parent_id") or "")
    return frozenset(result)
