"""GW import paths under app_data."""

from __future__ import annotations

from pathlib import Path

from core.paths import app_data_dir, dev_root


def gw_import_root() -> Path:
    root = app_data_dir() / "gw_import"
    root.mkdir(parents=True, exist_ok=True)
    return root


def gw_details_dir() -> Path:
    d = gw_import_root() / "details"
    d.mkdir(parents=True, exist_ok=True)
    return d


def gw_attachments_dir(gw_doc_id: str) -> Path:
    d = gw_import_root() / "attachments" / str(gw_doc_id).strip()
    d.mkdir(parents=True, exist_ok=True)
    return d


def gw_archive_dir(gw_doc_id: str) -> Path:
    d = gw_import_root() / "archive" / str(gw_doc_id).strip()
    d.mkdir(parents=True, exist_ok=True)
    return d


def gw_checkpoint_path() -> Path:
    return gw_import_root() / "import_checkpoint.json"


def gw_kpi_index_path() -> Path:
    return gw_import_root() / "kpi_index.json"


def dev_gw_import_dir() -> Path:
    """Project-local scrape outputs (browser_min_screen.json etc.)."""
    p = dev_root() / "gw_import"
    return p if p.is_dir() else gw_import_root()
