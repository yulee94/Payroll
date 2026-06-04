"""
core/workflow/store.py - 테넌트별 워크플로우 JSON 저장소
"""

from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import app_data_dir

WORKFLOW_ROOT = app_data_dir() / "workflow"
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex


def tenant_db_path(tenant_id: str) -> Path:
    return WORKFLOW_ROOT / tenant_id / "database.json"


def _empty_db() -> dict[str, Any]:
    return {
        "version": 1,
        "sites": [],
        "departments": [],
        "user_profiles": [],
        "documents": [],
        "approval_steps": [],
        "attendance_requests": [],
        "purchase_requests": [],
        "purchase_request_items": [],
        "expense_reports": [],
        "execution_tasks": [],
        "business_trips": [],
        "notifications": [],
        "audit_logs": [],
        "attachments": [],
        "monthly_closings": [],
        "profit_loss": [],
        "comments": [],
        "document_seq": 0,
        "business_trip_seq": 0,
    }


def _load_raw(tenant_id: str) -> dict[str, Any]:
    path = tenant_db_path(tenant_id)
    if not path.is_file():
        return _empty_db()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            original = deepcopy(data)
            empty = _empty_db()
            for key in empty:
                data.setdefault(key, deepcopy(empty[key]) if isinstance(empty[key], list) else empty[key])
            from core.workflow.business_trip import migrate_business_trips

            migrate_business_trips(data, tenant_id)
            if data != original:
                _save_raw(tenant_id, data)
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_db()


def _save_raw(tenant_id: str, data: dict[str, Any]) -> None:
    path = tenant_db_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def with_db(tenant_id: str):
    """Context manager style via function — load, mutate callback, save."""

    def _run(mutator: Any) -> Any:
        with _lock:
            db = _load_raw(tenant_id)
            result = mutator(db)
            _save_raw(tenant_id, db)
            return result

    return _run


def get_user_profile(tenant_id: str, user_id: str) -> dict[str, Any] | None:
    db = _load_raw(tenant_id)
    for p in db.get("user_profiles") or []:
        if p.get("user_id") == user_id:
            return p
    return None


def list_sites(tenant_id: str) -> list[dict[str, Any]]:
    return list(_load_raw(tenant_id).get("sites") or [])


def list_departments(tenant_id: str, site_id: str | None = None) -> list[dict[str, Any]]:
    deps = _load_raw(tenant_id).get("departments") or []
    if not site_id:
        return list(deps)
    return [d for d in deps if d.get("site_id") == site_id]


def next_document_no(db: dict[str, Any]) -> str:
    seq = int(db.get("document_seq") or 0) + 1
    db["document_seq"] = seq
    year = datetime.now().year
    return f"BW-{year}-{seq:05d}"


def append_audit(
    db: dict[str, Any],
    *,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: Any = None,
    after: Any = None,
) -> None:
    logs: list[dict[str, Any]] = db.setdefault("audit_logs", [])
    logs.append(
        {
            "id": _new_id(),
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "before_json": deepcopy(before),
            "after_json": deepcopy(after),
            "ip_address": "",
            "user_agent": "desktop",
            "created_at": _now_iso(),
        }
    )


def add_notification(
    db: dict[str, Any],
    *,
    user_id: str,
    ntype: str,
    title: str,
    message: str,
    related_document_id: str = "",
    related_task_id: str = "",
) -> None:
    notes: list[dict[str, Any]] = db.setdefault("notifications", [])
    notes.append(
        {
            "id": _new_id(),
            "user_id": user_id,
            "type": ntype,
            "title": title,
            "message": message,
            "related_document_id": related_document_id,
            "related_task_id": related_task_id,
            "read_at": "",
            "created_at": _now_iso(),
        }
    )
