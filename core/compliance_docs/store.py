"""법정·규정 문서 저장·조회 (테넌트별)."""

from __future__ import annotations

import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.compliance_docs.categories import (
    ACKNOWLEDGMENT_CATEGORIES,
    ALL_CATEGORIES,
    CATEGORY_LABELS,
)
from core.compliance_docs.permissions import (
    require_manage_compliance_docs,
    require_view_compliance_docs,
)
from core.paths import app_data_dir
from core.session_service import UserSession, get_session

MODULE = "compliance_docs"

_EMPTY: dict[str, Any] = {
    "documents": [],
    "acknowledgments": [],
}


def _tenant_id(session: UserSession | None = None) -> str:
    sess = require_view_compliance_docs(session)
    return sess.tenant_id


def _files_dir(tenant_id: str) -> Path:
    return app_data_dir() / MODULE / tenant_id / "files"


def _db_path(tenant_id: str) -> Path:
    return app_data_dir() / MODULE / tenant_id / "database.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _load_db(tenant_id: str) -> dict[str, Any]:
    path = _db_path(tenant_id)
    if not path.is_file():
        return {"documents": [], "acknowledgments": []}
    import json

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {"documents": [], "acknowledgments": []}
        docs = raw.get("documents")
        acks = raw.get("acknowledgments")
        return {
            "documents": list(docs) if isinstance(docs, list) else [],
            "acknowledgments": list(acks) if isinstance(acks, list) else [],
        }
    except (OSError, json.JSONDecodeError):
        return {"documents": [], "acknowledgments": []}


def _save_db(tenant_id: str, data: dict[str, Any]) -> None:
    import json

    path = _db_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(str(category), str(category))


def requires_acknowledgment(category: str) -> bool:
    return str(category) in ACKNOWLEDGMENT_CATEGORIES


def _normalize_category(category: str) -> str:
    cat = str(category or "").strip()
    if cat not in ALL_CATEGORIES:
        raise ValueError(f"알 수 없는 카테고리: {cat}")
    return cat


def list_documents(
    *,
    category: str | None = None,
    categories: frozenset[str] | set[str] | None = None,
    active_only: bool = True,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    tid = _tenant_id(session)
    db = _load_db(tid)
    rows = list(db.get("documents") or [])
    if active_only:
        rows = [r for r in rows if r.get("is_active", True)]
    if category:
        rows = [r for r in rows if str(r.get("category")) == category]
    elif categories:
        cat_set = frozenset(categories)
        rows = [r for r in rows if str(r.get("category")) in cat_set]
    rows.sort(key=lambda r: (r.get("effective_date") or "", r.get("uploaded_at") or ""), reverse=True)
    return rows


def get_document(doc_id: str, *, session: UserSession | None = None) -> dict[str, Any] | None:
    tid = _tenant_id(session)
    for doc in _load_db(tid).get("documents") or []:
        if str(doc.get("id")) == str(doc_id):
            return dict(doc)
    return None


def resolve_file_path(doc: dict[str, Any], *, tenant_id: str | None = None) -> Path | None:
    tid = tenant_id or str(doc.get("tenant_id") or "")
    rel = str(doc.get("file_path") or "")
    if not rel or not tid:
        return None
    path = app_data_dir() / MODULE / tid / rel
    return path if path.is_file() else None


def upload_document(
    *,
    category: str,
    title: str,
    source_path: Path,
    description: str = "",
    effective_date: str = "",
    version: str = "",
    session: UserSession | None = None,
) -> dict[str, Any]:
    from core.compliance_docs.categories import ALLOWED_EXTENSIONS

    sess = require_manage_compliance_docs(session)
    tid = sess.tenant_id
    cat = _normalize_category(category)
    src = Path(source_path)
    if not src.is_file():
        raise ValueError("파일을 찾을 수 없습니다.")
    suffix = src.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("지원하지 않는 파일 형식입니다.")

    title_clean = str(title or "").strip()
    if not title_clean:
        raise ValueError("제목을 입력하세요.")

    eff = str(effective_date or "").strip()[:10]
    if eff:
        try:
            date.fromisoformat(eff)
        except ValueError as exc:
            raise ValueError("시행일 형식이 올바르지 않습니다 (YYYY-MM-DD).") from exc

    doc_id = _new_id()
    files_dir = _files_dir(tid)
    files_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{doc_id}{suffix}"
    dest = files_dir / stored_name
    shutil.copy2(src, dest)

    rel_path = f"files/{stored_name}"
    row: dict[str, Any] = {
        "id": doc_id,
        "tenant_id": tid,
        "category": cat,
        "title": title_clean,
        "description": str(description or "").strip(),
        "file_path": rel_path,
        "uploaded_by": sess.user_id,
        "uploaded_at": _now_iso(),
        "effective_date": eff,
        "version": str(version or "").strip(),
        "is_active": True,
    }

    db = _load_db(tid)
    db.setdefault("documents", []).append(row)
    _save_db(tid, db)
    return row


def delete_document(doc_id: str, *, session: UserSession | None = None) -> bool:
    sess = require_manage_compliance_docs(session)
    tid = sess.tenant_id
    db = _load_db(tid)
    found = False
    for doc in db.get("documents") or []:
        if str(doc.get("id")) != str(doc_id):
            continue
        doc["is_active"] = False
        found = True
        break
    if found:
        _save_db(tid, db)
    return found


def has_acknowledged(doc_id: str, *, session: UserSession | None = None) -> bool:
    sess = require_view_compliance_docs(session)
    tid = sess.tenant_id
    uid = sess.user_id
    for ack in _load_db(tid).get("acknowledgments") or []:
        if str(ack.get("doc_id")) == str(doc_id) and str(ack.get("user_id")) == uid:
            return True
    return False


def acknowledge_document(doc_id: str, *, session: UserSession | None = None) -> dict[str, Any]:
    sess = require_view_compliance_docs(session)
    tid = sess.tenant_id
    doc = get_document(doc_id, session=sess)
    if doc is None:
        raise ValueError("문서를 찾을 수 없습니다.")
    if not requires_acknowledgment(str(doc.get("category"))):
        raise ValueError("이 문서는 열람 확인 대상이 아닙니다.")

    db = _load_db(tid)
    for ack in db.get("acknowledgments") or []:
        if str(ack.get("doc_id")) == str(doc_id) and str(ack.get("user_id")) == sess.user_id:
            return dict(ack)

    row = {
        "doc_id": str(doc_id),
        "user_id": sess.user_id,
        "acknowledged_at": _now_iso(),
    }
    db.setdefault("acknowledgments", []).append(row)
    _save_db(tid, db)
    return row


def list_acknowledgments(doc_id: str, *, tenant_id: str) -> list[dict[str, Any]]:
    """관리자용 — 특정 문서의 열람 확인 목록."""
    db = _load_db(tenant_id)
    return [
        dict(a)
        for a in db.get("acknowledgments") or []
        if str(a.get("doc_id")) == str(doc_id)
    ]
