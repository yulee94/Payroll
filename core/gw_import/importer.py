"""
Import full GW document (body + attachments) into workflow database.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.gw_import.archive import archive_immutable_copy
from core.gw_import.detail_parser import parse_detail_payload
from core.gw_import.kpi import record_document
from core.gw_import.paths import gw_attachments_dir, gw_details_dir
from core.gw_import.store import save_detail_cache
from core.workflow.constants import DOC_STATUS_APPROVED, DOC_STATUS_IN_REVIEW
from core.workflow.store import _load_raw, _new_id, _now_iso, _save_raw, next_document_no
from core.gw_import.classify import DEFAULT_REQUESTER, infer_document_type
from core.gw_import.gw_document_api import is_synthetic_body

TENANT_DEFAULT = "coss"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_by_gw_id(db: dict[str, Any], gw_doc_id: str) -> dict[str, Any] | None:
    for doc in db.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        cj = doc.get("content_json") or {}
        if isinstance(cj, dict) and str(cj.get("gw_doc_id") or "").strip() == gw_doc_id:
            return doc
    return None


def _has_full_body(doc: dict[str, Any]) -> bool:
    ch = str(doc.get("content_html") or "").strip()
    if len(ch) > 80:
        return True
    cj = doc.get("content_json") or {}
    if isinstance(cj, dict):
        cjh = str(cj.get("content_html") or "").strip()
        if len(cjh) > 80:
            return True
        ct = str(cj.get("content_text") or doc.get("content") or "").strip()
        if ct and not is_synthetic_body({"content_text": ct, "content_html": cjh}):
            if len(ct) > 120:
                return True
        atts = cj.get("attachments") or []
        if isinstance(atts, list) and any(
            isinstance(a, dict) and str(a.get("name") or "").strip() for a in atts
        ):
            return True
    content = str(doc.get("content") or "").strip()
    if content and not content.startswith("(COSS 그룹웨어") and len(content) > 120:
        return True
    return False


def _resolve_attachment_files(
    detail: dict[str, Any],
    *,
    source_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], list[Path]]:
    gid = str(detail.get("gw_doc_id") or "").strip()
    dest_dir = gw_attachments_dir(gid)
    resolved: list[dict[str, Any]] = []
    paths: list[Path] = []
    for att in detail.get("attachments") or []:
        if not isinstance(att, dict):
            continue
        name = str(att.get("name") or "attachment").strip()
        if not name:
            continue
        src_path = Path(str(att.get("path") or ""))
        if not src_path.is_file() and source_dir:
            cand = source_dir / name
            if cand.is_file():
                src_path = cand
        dest = dest_dir / name
        if src_path.is_file():
            if not dest.is_file() or src_path.stat().st_mtime > dest.stat().st_mtime:
                shutil.copy2(src_path, dest)
            paths.append(dest)
            resolved.append(
                {
                    "name": name,
                    "path": f"attachments/{gid}/{name}",
                    "size": dest.stat().st_size,
                }
            )
        elif att.get("url"):
            resolved.append({"name": name, "path": "", "size": 0, "url": str(att.get("url"))})
        elif name:
            resolved.append(
                {
                    "name": name,
                    "path": "",
                    "size": int(att.get("size") or 0),
                    "pending_download": True,
                }
            )
    return resolved, paths


def _gw_status_for_list(gw_list: str) -> str:
    if gw_list in ("pending", "to_approve", "in_progress"):
        return DOC_STATUS_IN_REVIEW
    return DOC_STATUS_APPROVED


def upsert_gw_document(
    tenant_id: str,
    detail: dict[str, Any],
    *,
    skip_if_complete: bool = True,
    source_attachment_dir: Path | None = None,
) -> tuple[str, bool, bool]:
    """
    Returns (document_id, created, skipped).
    """
    detail = parse_detail_payload(detail)
    gid = detail["gw_doc_id"]
    if not gid:
        raise ValueError("gw_doc_id is required")

    db = _load_raw(tenant_id)
    existing = _find_by_gw_id(db, gid)
    if existing and skip_if_complete and _has_full_body(existing):
        return str(existing["id"]), False, True

    attachments, att_paths = _resolve_attachment_files(detail, source_dir=source_attachment_dir)
    detail["attachments"] = attachments
    save_detail_cache(detail)

    content_text = detail.get("content_text") or ""
    content_html = detail.get("content_html") or ""
    gw_list = detail.get("gw_list") or "imported"
    doc_type = infer_document_type(detail.get("title") or "")
    if detail.get("form_name"):
        doc_type = infer_document_type(str(detail.get("form_name")) + " " + doc_type)

    content_json: dict[str, Any] = {
        "gw_doc_id": gid,
        "gw_doc_number": detail.get("doc_number") or "",
        "gw_drafter": detail.get("drafter") or "",
        "gw_list": gw_list,
        "gw_form_name": detail.get("form_name") or "",
        "gw_url": detail.get("gw_url") or "",
        "imported_from": "gw.cossok.com",
        "imported_at": _utc_now(),
        "gw_readonly": True,
        "content_text": content_text,
        "content_html": content_html[:500_000] if content_html else "",
        "attachments": attachments,
        "approval_workflow_json": detail.get("approval_workflow_json") or {},
    }

    if existing:
        doc_id = str(existing["id"])
        existing["title"] = detail.get("title") or existing.get("title")
        existing["summary"] = (content_text[:500] or existing.get("summary") or detail.get("title") or "")
        existing["content"] = content_text[:100_000]
        existing["content_html"] = content_html[:500_000] if content_html else existing.get("content_html", "")
        existing["content_json"] = {**(existing.get("content_json") or {}), **content_json}
        existing["updated_at"] = _now_iso()
        if detail.get("drafted_at"):
            existing["requested_date"] = detail["drafted_at"][:10]
        created = False
    else:
        doc_id = _new_id()
        db.setdefault("documents", []).append(
            {
                "id": doc_id,
                "document_no": detail.get("doc_number") or next_document_no(db),
                "document_type": doc_type,
                "title": detail.get("title") or "(제목 없음)",
                "summary": content_text[:500] or detail.get("title") or "",
                "content": content_text[:100_000],
                "content_html": content_html[:500_000] if content_html else "",
                "status": _gw_status_for_list(gw_list),
                "site_id": "site_hq",
                "department_id": "dept_mgmt",
                "requester_id": DEFAULT_REQUESTER,
                "total_amount": 0,
                "currency": "KRW",
                "category": detail.get("form_name") or "",
                "requested_date": (detail.get("drafted_at") or "")[:10],
                "due_date": "",
                "approved_at": _now_iso() if _gw_status_for_list(gw_list) == DOC_STATUS_APPROVED else "",
                "rejected_at": "",
                "completed_at": (detail.get("completed_at") or "")[:10],
                "closed_at": "",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "content_json": content_json,
            }
        )
        created = True

    for att in attachments:
        if not att.get("path"):
            continue
        db.setdefault("attachments", []).append(
            {
                "id": uuid.uuid4().hex[:12],
                "document_id": doc_id,
                "file_name": att["name"],
                "file_path": att["path"],
                "file_size": att.get("size", 0),
                "uploaded_at": _now_iso(),
                "gw_import": True,
            }
        )

    _save_raw(tenant_id, db)

    if att_paths or content_text or content_html:
        try:
            archive_immutable_copy(detail, attachment_paths=att_paths)
        except OSError:
            pass

    record_document(
        gw_doc_id=gid,
        document_type=doc_type,
        title=detail.get("title") or "",
        drafted_at=detail.get("drafted_at") or "",
        gw_list=gw_list,
    )
    return doc_id, created, False


def import_detail_file(
    tenant_id: str,
    path: Path,
    *,
    skip_if_complete: bool = True,
) -> tuple[str, bool, bool]:
    from core.gw_import.detail_parser import load_detail_file

    detail = load_detail_file(path)
    att_dir = path.parent / "attachments" / detail.get("gw_doc_id", "")
    if not att_dir.is_dir():
        att_dir = path.parent
    return upsert_gw_document(
        tenant_id,
        detail,
        skip_if_complete=skip_if_complete,
        source_attachment_dir=att_dir,
    )


def count_fully_imported(tenant_id: str) -> dict[str, int]:
    db = _load_raw(tenant_id)
    total_gw = 0
    full = 0
    for doc in db.get("documents") or []:
        cj = doc.get("content_json") or {}
        if not isinstance(cj, dict) or not cj.get("imported_from"):
            continue
        total_gw += 1
        if _has_full_body(doc):
            full += 1
    return {"gw_documents": total_gw, "with_body_or_attachments": full}
