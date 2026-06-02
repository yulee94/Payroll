"""
core/group_store.py - Bitween 그룹(판매 단위) · 계열사·법인 레지스트리

타사 제공 시 그룹 메인 계정이 법인·테넌트·결재 정책을 자체 설정합니다.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import app_data_dir

GROUPS_FILE = app_data_dir() / "groups" / "registry.json"
DEFAULT_GROUP_ID = "coss_group"


@dataclass
class LegalEntity:
    entity_id: str
    name_ko: str
    code: str
    tenant_id: str
    is_group_hq: bool = False
    notes: str = ""


@dataclass
class GroupRecord:
    group_id: str
    name: str
    root_tenant_id: str
    tenant_ids: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    created_at: str = ""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir() -> None:
    GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _empty_registry() -> dict[str, Any]:
    return {"groups": {}, "tenant_to_group": {}}


def load_registry() -> dict[str, Any]:
    _ensure_dir()
    if not GROUPS_FILE.is_file():
        return _empty_registry()
    try:
        raw = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty_registry()
        raw.setdefault("groups", {})
        raw.setdefault("tenant_to_group", {})
        return raw
    except (OSError, json.JSONDecodeError):
        return _empty_registry()


def save_registry(data: dict[str, Any]) -> None:
    _ensure_dir()
    GROUPS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_group(raw: dict[str, Any]) -> GroupRecord:
    tids = raw.get("tenant_ids") or []
    if isinstance(tids, str):
        tids = [t.strip() for t in tids.split(",") if t.strip()]
    return GroupRecord(
        group_id=str(raw.get("group_id") or ""),
        name=str(raw.get("name") or ""),
        root_tenant_id=str(raw.get("root_tenant_id") or ""),
        tenant_ids=tuple(str(t) for t in tids),
        notes=str(raw.get("notes") or ""),
        created_at=str(raw.get("created_at") or ""),
    )


def list_groups() -> list[GroupRecord]:
    reg = load_registry()
    return sorted(
        [_to_group(v) for v in (reg.get("groups") or {}).values() if isinstance(v, dict)],
        key=lambda g: g.group_id,
    )


def get_group(group_id: str) -> GroupRecord | None:
    raw = (load_registry().get("groups") or {}).get(str(group_id).strip())
    return _to_group(raw) if isinstance(raw, dict) else None


def get_group_for_tenant(tenant_id: str) -> GroupRecord | None:
    reg = load_registry()
    gid = (reg.get("tenant_to_group") or {}).get(str(tenant_id).strip())
    return get_group(gid) if gid else None


def get_workflow_tenant_id(tenant_id: str) -> str:
    """그룹 내 전자결재 저장·조회는 루트 테넌트 DB 사용 (교차 결재 통합)."""
    grp = get_group_for_tenant(tenant_id)
    if grp and grp.root_tenant_id:
        return grp.root_tenant_id
    return tenant_id


def create_group(
    *,
    name: str,
    root_tenant_id: str,
    tenant_ids: tuple[str, ...] | None = None,
    group_id: str = "",
    notes: str = "",
) -> GroupRecord:
    label = str(name or "").strip()
    root = str(root_tenant_id or "").strip()
    if not label or not root:
        raise ValueError("그룹명과 루트 테넌트가 필요합니다.")
    gid = str(group_id or "").strip() or uuid.uuid4().hex[:12]
    tids = tuple(dict.fromkeys([root, *(tenant_ids or ())]))
    reg = load_registry()
    groups = reg.setdefault("groups", {})
    if gid in groups:
        raise ValueError("이미 존재하는 그룹 ID입니다.")
    row = {
        "group_id": gid,
        "name": label,
        "root_tenant_id": root,
        "tenant_ids": list(tids),
        "notes": notes,
        "created_at": _now_iso(),
    }
    groups[gid] = row
    mapping = reg.setdefault("tenant_to_group", {})
    for tid in tids:
        mapping[tid] = gid
    save_registry(reg)
    return _to_group(row)


def add_tenant_to_group(group_id: str, tenant_id: str) -> GroupRecord:
    gid = str(group_id).strip()
    tid = str(tenant_id).strip()
    reg = load_registry()
    groups = reg.get("groups") or {}
    row = groups.get(gid)
    if not isinstance(row, dict):
        raise ValueError("그룹을 찾을 수 없습니다.")
    tids = list(row.get("tenant_ids") or [])
    if tid not in tids:
        tids.append(tid)
    row["tenant_ids"] = tids
    reg.setdefault("tenant_to_group", {})[tid] = gid
    save_registry(reg)
    return _to_group(row)


def list_legal_entities(group_id: str) -> list[LegalEntity]:
    from core.workflow.config_store import load_workflow_config

    cfg = load_workflow_config(group_id)
    out: list[LegalEntity] = []
    for row in cfg.get("legal_entities") or []:
        if not isinstance(row, dict):
            continue
        out.append(
            LegalEntity(
                entity_id=str(row.get("entity_id") or ""),
                name_ko=str(row.get("name_ko") or ""),
                code=str(row.get("code") or ""),
                tenant_id=str(row.get("tenant_id") or ""),
                is_group_hq=bool(row.get("is_group_hq")),
                notes=str(row.get("notes") or ""),
            )
        )
    return out
