"""Lightweight KPI index for imported GW documents (count by type/month)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.gw_import.paths import gw_kpi_index_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict[str, Any]:
    path = gw_kpi_index_path()
    if not path.is_file():
        return {"updated_at": "", "by_month": {}, "by_type": {}, "documents": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("by_month", {})
            data.setdefault("by_type", {})
            data.setdefault("documents", {})
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"updated_at": "", "by_month": {}, "by_type": {}, "documents": {}}


def _save(data: dict[str, Any]) -> None:
    path = gw_kpi_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _utc_now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_document(
    *,
    gw_doc_id: str,
    document_type: str,
    title: str,
    drafted_at: str = "",
    gw_list: str = "",
) -> None:
    data = _load()
    month = (drafted_at or datetime.now().strftime("%Y-%m-%d"))[:7]
    dtype = document_type or "GENERAL"
    data["documents"][gw_doc_id] = {
        "title": title[:200],
        "document_type": dtype,
        "month": month,
        "gw_list": gw_list,
        "indexed_at": _utc_now(),
    }
    by_month: dict[str, int] = defaultdict(int, data.get("by_month") or {})
    by_type: dict[str, int] = defaultdict(int, data.get("by_type") or {})
    by_month[month] = int(by_month.get(month, 0)) + 1
    by_type[dtype] = int(by_type.get(dtype, 0)) + 1
    data["by_month"] = dict(by_month)
    data["by_type"] = dict(by_type)
    _save(data)


def query_counts() -> dict[str, Any]:
    return _load()
