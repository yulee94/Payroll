"""Immutable compliance archive copy after GW document import."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.gw_import.paths import gw_archive_dir


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def archive_immutable_copy(
    detail: dict[str, Any],
    *,
    attachment_paths: list[Path],
) -> Path:
    """
    Write immutable snapshot: detail.json + files/ under archive/{gw_doc_id}/.
    Existing archive is never overwritten (append-only new version folder).
    """
    gid = str(detail.get("gw_doc_id") or "").strip()
    if not gid:
        raise ValueError("gw_doc_id required for archive")

    base = gw_archive_dir(gid)
    version_dir = base / f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if version_dir.exists():
        version_dir = base / f"v_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    files_dir = version_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    archived_atts: list[dict[str, Any]] = []
    for src in attachment_paths:
        if not src.is_file():
            continue
        dest = files_dir / src.name
        if dest.exists():
            dest = files_dir / f"{src.stem}_{hash(str(src)) & 0xFFFF:04x}{src.suffix}"
        shutil.copy2(src, dest)
        archived_atts.append(
            {
                "name": src.name,
                "path": str(dest.relative_to(version_dir)).replace("\\", "/"),
                "size": dest.stat().st_size,
            }
        )

    payload = {
        **detail,
        "attachments": archived_atts,
        "archived_at": _utc_now(),
        "immutable": True,
    }
    (version_dir / "detail.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    latest = base / "latest.json"
    if not latest.is_file():
        latest.write_text(
            json.dumps({"version_dir": version_dir.name, "archived_at": payload["archived_at"]}, ensure_ascii=False),
            encoding="utf-8",
        )
    return version_dir
