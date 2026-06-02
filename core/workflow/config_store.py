"""
core/workflow/config_store.py - 그룹별 전자결재 설정 (법인·결재선·양식·연동체인)
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.group_store import DEFAULT_GROUP_ID, get_group
from core.paths import app_data_dir
from core.workflow.constants import DOC_TYPE_GENERAL
from core.workflow.forms import FORM_SCHEMAS, FormFieldDef

CONFIG_ROOT = app_data_dir() / "groups"


def config_path(group_id: str) -> Path:
    return CONFIG_ROOT / str(group_id).strip() / "workflow_config.json"


def load_workflow_config(group_id: str) -> dict[str, Any]:
    path = config_path(group_id)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_workflow_config(group_id: str, data: dict[str, Any]) -> None:
    path = config_path(group_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_workflow_config(group_id: str, *, factory: Any | None = None) -> dict[str, Any]:
    existing = load_workflow_config(group_id)
    if existing.get("legal_entities"):
        return existing
    if factory is None:
        from core.workflow.group_defaults import coss_workflow_config

        factory = coss_workflow_config
    data = factory() if callable(factory) else deepcopy(factory)
    data["group_id"] = group_id
    grp = get_group(group_id)
    if grp and grp.name:
        data["group_name"] = grp.name
    save_workflow_config(group_id, data)
    return data


def load_config_for_tenant(tenant_id: str) -> dict[str, Any]:
    from core.group_store import get_group_for_tenant

    grp = get_group_for_tenant(tenant_id)
    if not grp:
        return {}
    return ensure_workflow_config(grp.group_id)


def list_approval_templates(group_id: str, document_type: str | None = None) -> list[dict[str, Any]]:
    cfg = ensure_workflow_config(group_id)
    rows = cfg.get("approval_templates") or []
    if not document_type:
        return [r for r in rows if isinstance(r, dict)]
    return [r for r in rows if isinstance(r, dict) and r.get("document_type") == document_type]


def pick_approval_template(
    group_id: str,
    document_type: str,
    *,
    amount: int = 0,
) -> dict[str, Any] | None:
    """금액 구간에 맞는 결재 템플릿 선택."""
    candidates = list_approval_templates(group_id, document_type)
    if not candidates:
        return None
    amt = int(amount or 0)
    matched = [
        t
        for t in candidates
        if int(t.get("amount_min") or 0) <= amt <= int(t.get("amount_max") or 999_999_999_999)
    ]
    if matched:
        return matched[0]
    return candidates[0]


def get_form_schema_from_config(group_id: str, document_type: str) -> tuple[FormFieldDef, ...] | None:
    cfg = ensure_workflow_config(group_id)
    for row in cfg.get("document_types") or []:
        if not isinstance(row, dict):
            continue
        if row.get("document_type") != document_type or not row.get("enabled", True):
            continue
        fields = []
        for f in row.get("fields") or []:
            if not isinstance(f, dict):
                continue
            fields.append(
                FormFieldDef(
                    key=str(f.get("key") or ""),
                    label=str(f.get("label") or ""),
                    field_type=str(f.get("field_type") or "text"),
                    required=bool(f.get("required")),
                    options=tuple(f.get("options") or ()),
                    placeholder=str(f.get("placeholder") or ""),
                    maps_to=str(f.get("maps_to") or ""),
                )
            )
        if fields:
            return tuple(fields)
    return None


def resolve_form_schema(tenant_id: str, document_type: str) -> tuple[FormFieldDef, ...]:
    from core.group_store import get_group_for_tenant

    grp = get_group_for_tenant(tenant_id)
    if grp:
        custom = get_form_schema_from_config(grp.group_id, document_type)
        if custom:
            return custom
    return FORM_SCHEMAS.get(document_type, FORM_SCHEMAS[DOC_TYPE_GENERAL])


def update_approval_templates(group_id: str, templates: list[dict[str, Any]]) -> None:
    cfg = ensure_workflow_config(group_id)
    cfg["approval_templates"] = templates
    save_workflow_config(group_id, cfg)


def update_legal_entities(group_id: str, entities: list[dict[str, Any]]) -> None:
    cfg = ensure_workflow_config(group_id)
    cfg["legal_entities"] = entities
    save_workflow_config(group_id, cfg)


def update_procurement_chain(group_id: str, chain: list[dict[str, Any]]) -> None:
    cfg = ensure_workflow_config(group_id)
    cfg["procurement_chain"] = chain
    save_workflow_config(group_id, cfg)


def get_entity_for_tenant(group_id: str, tenant_id: str) -> dict[str, Any] | None:
    for row in load_workflow_config(group_id).get("legal_entities") or []:
        if isinstance(row, dict) and str(row.get("tenant_id") or "") == str(tenant_id).strip():
            return row
    return None
