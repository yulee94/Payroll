"""Checkpoint and per-document detail cache on disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.gw_import.paths import gw_checkpoint_path, gw_details_dir


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_checkpoint() -> dict[str, Any]:
    path = gw_checkpoint_path()
    if not path.is_file():
        return {
            "started_at": "",
            "updated_at": "",
            "completed_ids": [],
            "errors": [],
            "stats": {"imported": 0, "skipped": 0, "failed": 0},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("completed_ids", [])
            data.setdefault("errors", [])
            data.setdefault("stats", {"imported": 0, "skipped": 0, "failed": 0})
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "started_at": "",
        "updated_at": "",
        "completed_ids": [],
        "errors": [],
        "stats": {"imported": 0, "skipped": 0, "failed": 0},
    }


def save_checkpoint(data: dict[str, Any]) -> None:
    path = gw_checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not data.get("started_at"):
        data["started_at"] = _utc_now()
    data["updated_at"] = _utc_now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_completed(gw_doc_id: str, *, imported: bool = True, skipped: bool = False, error: str = "") -> None:
    cp = load_checkpoint()
    gid = str(gw_doc_id).strip()
    if gid and gid not in cp["completed_ids"]:
        cp["completed_ids"].append(gid)
    stats = cp.setdefault("stats", {})
    if error:
        stats["failed"] = int(stats.get("failed", 0)) + 1
        cp.setdefault("errors", []).append({"gw_doc_id": gid, "error": error, "at": _utc_now()})
    elif skipped:
        stats["skipped"] = int(stats.get("skipped", 0)) + 1
    elif imported:
        stats["imported"] = int(stats.get("imported", 0)) + 1
    save_checkpoint(cp)


def detail_cache_path(gw_doc_id: str) -> Path:
    return gw_details_dir() / f"{gw_doc_id}.json"


def save_detail_cache(detail: dict[str, Any]) -> Path:
    gid = str(detail.get("gw_doc_id") or "").strip()
    path = detail_cache_path(gid)
    path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_detail_cache(gw_doc_id: str) -> dict[str, Any] | None:
    path = detail_cache_path(gw_doc_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None
