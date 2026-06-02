"""Collect GW document list rows from browser scrape JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from core.gw_import.detail_parser import parse_inbox_sample_line, stable_gw_doc_id
from core.gw_import.paths import dev_gw_import_dir, gw_import_root


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def iter_list_sources() -> Iterator[tuple[str, Path]]:
    for root in (gw_import_root(), dev_gw_import_dir()):
        lists_dir = root / "lists"
        if lists_dir.is_dir():
            for p in sorted(lists_dir.glob("*.json")):
                yield f"lists/{p.name}", p
        for name in (
            "_drafts_parsed.json",
            "browser_min_screen.json",
            "gw_scrape_extended.json",
        ):
            p = root / name
            if p.is_file():
                yield name, p


def collect_list_rows(
    *,
    lists: tuple[str, ...] = ("pending", "in_progress", "completed", "circulate", "draft"),
) -> list[dict[str, Any]]:
    """
    Merge document references from known scrape files.
    lists: which GW list kinds to include (mapped to gw_list field).
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(row: dict[str, Any], list_kind: str) -> None:
        gid = str(row.get("gw_doc_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not title:
            return
        if not gid:
            gid = stable_gw_doc_id(f"{list_kind}|{title}")
            row = {**row, "gw_doc_id": gid}
        key = f"id:{gid}"
        if key in seen:
            return
        seen.add(key)
        rows.append({**row, "gw_list": list_kind})

    list_set = set(lists)
    for _fname, path in iter_list_sources():
        if _fname.startswith("lists/") or path.parent.name == "lists":
            data = _read_json(path)
            if not isinstance(data, dict):
                continue
            kind = str(data.get("list_kind") or path.stem).strip() or path.stem
            if list_set and kind not in list_set:
                continue
            for row in data.get("rows") or []:
                if isinstance(row, dict):
                    _add(dict(row), str(row.get("gw_list") or kind))
            continue

        if path.name == "_drafts_parsed.json":
            if "draft" not in list_set:
                continue
            data = _read_json(path)
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        _add(dict(row), "draft")

        elif path.name == "browser_min_screen.json":
            data = _read_json(path)
            if not isinstance(data, dict):
                continue
            approval = data.get("approval") or {}
            if "circulate" in list_set:
                for row in approval.get("circulate_home_widget") or []:
                    if isinstance(row, dict):
                        _add(dict(row), "circulate")

        elif path.name == "gw_scrape_extended.json":
            data = _read_json(path)
            if not isinstance(data, dict):
                continue
            hints = data.get("inbox_counts_hint") or {}
            for line in data.get("document_samples") or []:
                if not isinstance(line, dict):
                    continue
                parsed = parse_inbox_sample_line(str(line.get("line") or ""))
                if hints.get("pending_approval") and "pending" in list_set:
                    parsed["gw_list"] = "pending"
                    _add(parsed, "pending")
                elif "pending" in list_set:
                    _add(parsed, "pending")
            if "in_progress" in list_set and hints.get("in_progress"):
                pass  # samples are mostly pending inbox

    return rows


def default_batch_lists() -> tuple[str, ...]:
    return ("pending", "in_progress", "completed", "circulate", "draft")
