"""
services/file_revision.py - Excel 수정본 업로드·이력 보관
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.labels import label_for_filename
from services.archive_storage import INVOICE_STORED_NAME, PAYROLL_OUTPUT_NAMES
from services.excel_diff import summarize_excel_diff
from services.payroll_scope import PayrollScope, resolve_output_dir

REVISIONS_DIRNAME = ".revisions"
INDEX_FILENAME = "index.json"
BEFORE_NAME = "before.xlsx"
AFTER_NAME = "after.xlsx"
META_NAME = "meta.json"

REPLACEABLE_EXACT = set(PAYROLL_OUTPUT_NAMES) | {INVOICE_STORED_NAME}


@dataclass
class FileRevision:
    revision_id: str
    scope: PayrollScope
    file_name: str
    file_label: str
    reason: str
    replaced_at: str
    replaced_at_display: str
    change_summary: str
    change_details: list[str]
    before_path: Path
    after_path: Path
    live_path: Path


def can_replace_at_scope(scope: PayrollScope, path: Path) -> bool:
    """현재 급여월 폴더에 있는 대체 가능 파일인지 확인."""
    if not path.is_file() or not is_replaceable_file(path):
        return False
    try:
        return path.resolve().parent == resolve_output_dir(scope).resolve()
    except OSError:
        return False


def is_replaceable_file(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".xlsx":
        return False
    name = path.name
    if name in REPLACEABLE_EXACT:
        return True
    if name.startswith("급여대장_추가"):
        return True
    if "전월대비" in name and name.endswith(".xlsx"):
        return True
    if "월별요약" in name or "월별요약보고" in name:
        return True
    return False


def _revisions_root(scope: PayrollScope) -> Path:
    return resolve_output_dir(scope) / REVISIONS_DIRNAME


def _index_path(scope: PayrollScope) -> Path:
    return _revisions_root(scope) / INDEX_FILENAME


def _load_index(scope: PayrollScope) -> list[dict[str, Any]]:
    path = _index_path(scope)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("revisions") if isinstance(data, dict) else data
        return items if isinstance(items, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(scope: PayrollScope, items: list[dict[str, Any]]) -> None:
    root = _revisions_root(scope)
    root.mkdir(parents=True, exist_ok=True)
    payload = {"scope": {"affiliate": scope.affiliate, "workplace": scope.workplace, "period": scope.period}, "revisions": items}
    _index_path(scope).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_revisions(scope: PayrollScope, file_name: str = "") -> list[FileRevision]:
    items = _load_index(scope)
    out: list[FileRevision] = []
    for raw in items:
        rev = _revision_from_raw(scope, raw)
        if not rev:
            continue
        if file_name and rev.file_name != file_name:
            continue
        out.append(rev)
    out.sort(key=lambda r: r.replaced_at, reverse=True)
    return out


def list_all_revisions_for_scope(scope: PayrollScope) -> list[FileRevision]:
    return list_revisions(scope)


def _revision_from_raw(scope: PayrollScope, raw: dict[str, Any]) -> FileRevision | None:
    rev_id = str(raw.get("id") or "").strip()
    file_name = str(raw.get("file_name") or "").strip()
    if not rev_id or not file_name:
        return None
    folder = _revisions_root(scope) / rev_id
    before = folder / BEFORE_NAME
    after = folder / AFTER_NAME
    if not before.is_file() or not after.is_file():
        return None
    live = resolve_output_dir(scope) / file_name
    details = raw.get("change_details") or []
    if not isinstance(details, list):
        details = []
    return FileRevision(
        revision_id=rev_id,
        scope=scope,
        file_name=file_name,
        file_label=str(raw.get("file_label") or label_for_filename(file_name)),
        reason=str(raw.get("reason") or ""),
        replaced_at=str(raw.get("replaced_at") or ""),
        replaced_at_display=str(raw.get("replaced_at_display") or ""),
        change_summary=str(raw.get("change_summary") or ""),
        change_details=[str(d) for d in details],
        before_path=before,
        after_path=after,
        live_path=live,
    )


def replace_file_with_revision(
    scope: PayrollScope,
    target_path: Path,
    uploaded_path: Path,
    reason: str,
    *,
    editor: str = "",
) -> FileRevision:
    """수정본으로 파일을 대체하고 수정 전·후본을 보관합니다."""
    reason = (reason or "").strip()
    if len(reason) < 2:
        raise ValueError("수정 사유를 입력해 주세요.")

    target_path = target_path.resolve()
    uploaded_path = uploaded_path.resolve()
    live_dir = resolve_output_dir(scope)

    if not target_path.is_file():
        raise FileNotFoundError("대체할 원본 파일을 찾을 수 없습니다.")
    if not is_replaceable_file(target_path):
        raise ValueError("이 파일 형식은 수정 업로드 대체를 지원하지 않습니다.")
    if uploaded_path.suffix.lower() != ".xlsx":
        raise ValueError("수정본은 Excel(.xlsx) 파일이어야 합니다.")

    if target_path.parent.resolve() != live_dir.resolve():
        raise ValueError("선택한 파일은 현재 급여월 폴더에 있는 파일만 대체할 수 있습니다.")

    now = datetime.now()
    rev_id = now.strftime("%Y%m%d_%H%M%S") + f"_{target_path.stem[:20]}"
    folder = _revisions_root(scope) / rev_id
    folder.mkdir(parents=True, exist_ok=True)

    before_copy = folder / BEFORE_NAME
    after_copy = folder / AFTER_NAME
    shutil.copy2(target_path, before_copy)
    shutil.copy2(uploaded_path, after_copy)
    shutil.copy2(uploaded_path, target_path)

    diff = summarize_excel_diff(before_copy, after_copy)

    meta = {
        "id": rev_id,
        "file_name": target_path.name,
        "file_label": label_for_filename(target_path.name),
        "reason": reason,
        "editor": editor.strip(),
        "replaced_at": now.isoformat(timespec="seconds"),
        "replaced_at_display": now.strftime("%Y-%m-%d %H:%M"),
        "change_summary": diff.get("summary_text") or "",
        "change_details": diff.get("details") or [],
        "cells_changed": diff.get("cells_changed") or 0,
    }
    (folder / META_NAME).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    items = _load_index(scope)
    items.insert(0, meta)
    _save_index(scope, items)

    rev = _revision_from_raw(scope, meta)
    if not rev:
        raise RuntimeError("수정 이력 저장에 실패했습니다.")
    return rev
