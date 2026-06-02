"""
core/hr/recruitment.py - 그룹 공유 채용공고 · 인재풀

법인(테넌트)별 채용공고·지원자를 관리하고, 동일 그룹 내 계열사에 공유합니다.
주민등록번호 또는 성명+연락처로 지원자 중복을 식별합니다.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from core.group_store import get_group_for_tenant
from core.hr.traffic_signal import mask_rrn, normalize_rrn
from core.paths import app_data_dir
from core.session_service import session_tenant_id
from core.tenant_store import get_tenant

PostingStatus = Literal["open", "closed"]
ApplicantStatus = Literal[
    "applied", "interviewing", "offered", "hired", "rejected", "talent_pool"
]

_RECRUITMENT_ROOT = app_data_dir() / "hr_recruitment"
_TENANT_DIR = _RECRUITMENT_ROOT / "tenants"
_GROUP_DIR = _RECRUITMENT_ROOT / "groups"
_lock = threading.Lock()

POSTING_STATUS_OPEN: PostingStatus = "open"
POSTING_STATUS_CLOSED: PostingStatus = "closed"

POSTING_STATUS_LABELS: dict[str, str] = {
    "open": "모집중",
    "closed": "마감",
}

APPLICANT_STATUS_LABELS: dict[str, str] = {
    "applied": "지원",
    "interviewing": "면접",
    "offered": "합격제안",
    "hired": "채용",
    "rejected": "불합격",
    "talent_pool": "인재풀",
}

SHAREABLE_APPLICANT_STATUSES = frozenset({"talent_pool"})


@dataclass
class JobPosting:
    id: str
    tenant_id: str
    tenant_name: str
    department: str
    site: str
    title: str
    description: str
    status: PostingStatus
    created_at: str
    updated_at: str
    shared: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "department": self.department,
            "site": self.site,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "status_label": POSTING_STATUS_LABELS.get(self.status, self.status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shared": self.shared,
        }


@dataclass
class Applicant:
    id: str
    tenant_id: str
    tenant_name: str
    posting_id: str
    posting_title: str
    name: str
    contact: str
    resume_notes: str
    status: ApplicantStatus
    rrn_key: str = ""
    rrn_masked: str = ""
    dedupe_key: str = ""
    recommended: bool = False
    ref_tenant_id: str = ""
    ref_applicant_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "posting_id": self.posting_id,
            "posting_title": self.posting_title,
            "name": self.name,
            "contact": self.contact,
            "resume_notes": self.resume_notes,
            "status": self.status,
            "status_label": APPLICANT_STATUS_LABELS.get(self.status, self.status),
            "rrn_key": self.rrn_key,
            "rrn_masked": self.rrn_masked,
            "dedupe_key": self.dedupe_key,
            "recommended": self.recommended,
            "ref_tenant_id": self.ref_tenant_id,
            "ref_applicant_id": self.ref_applicant_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class TalentPoolEntry:
    dedupe_key: str
    name: str
    contact: str
    rrn_masked: str
    resume_notes: str
    source_tenant_id: str
    source_tenant_name: str
    source_applicant_id: str
    source_posting_id: str
    source_posting_title: str
    recommended: bool
    shared_at: str
    names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dedupe_key": self.dedupe_key,
            "name": self.name,
            "contact": self.contact,
            "rrn_masked": self.rrn_masked,
            "resume_notes": self.resume_notes,
            "source_tenant_id": self.source_tenant_id,
            "source_tenant_name": self.source_tenant_name,
            "source_applicant_id": self.source_applicant_id,
            "source_posting_id": self.source_posting_id,
            "source_posting_title": self.source_posting_title,
            "recommended": self.recommended,
            "shared_at": self.shared_at,
            "names": self.names,
        }


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tid(tenant_id: str | None = None) -> str:
    return str(tenant_id or session_tenant_id() or "default").strip()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _tenant_display(tenant_id: str) -> str:
    t = get_tenant(tenant_id)
    if t:
        return t.display_name_ko or t.display_name or tenant_id
    return tenant_id


def _group_id_for(tenant_id: str) -> str | None:
    grp = get_group_for_tenant(tenant_id)
    return grp.group_id if grp else None


def normalize_contact(value: Any) -> str:
    return re.sub(r"[^\d]", "", str(value or "").strip())


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def applicant_dedupe_key(*, rrn: Any = "", name: str = "", contact: str = "") -> str:
    rrn_key = normalize_rrn(rrn)
    if rrn_key:
        return f"rrn:{rrn_key}"
    n = normalize_name(name)
    c = normalize_contact(contact)
    if n and c:
        return f"np:{n}:{c}"
    if n:
        return f"n:{n}"
    return f"anon:{uuid.uuid4().hex[:8]}"


def _empty_tenant() -> dict[str, Any]:
    return {"postings": [], "applicants": []}


def _empty_group() -> dict[str, Any]:
    return {"shared_postings": [], "talent_pool": {}}


def _tenant_path(tenant_id: str) -> Path:
    return _TENANT_DIR / f"{tenant_id}.json"


def _group_path(group_id: str) -> Path:
    return _GROUP_DIR / f"{group_id}.json"


def _load_tenant(tenant_id: str) -> dict[str, Any]:
    path = _tenant_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        return _empty_tenant()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw.setdefault("postings", [])
            raw.setdefault("applicants", [])
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_tenant()


def _save_tenant(tenant_id: str, data: dict[str, Any]) -> None:
    path = _tenant_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_group(group_id: str) -> dict[str, Any]:
    path = _group_path(group_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        return _empty_group()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw.setdefault("shared_postings", [])
            raw.setdefault("talent_pool", {})
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_group()


def _save_group(group_id: str, data: dict[str, Any]) -> None:
    path = _group_path(group_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_posting(raw: dict[str, Any]) -> JobPosting:
    status = str(raw.get("status") or POSTING_STATUS_OPEN)
    if status not in POSTING_STATUS_LABELS:
        status = POSTING_STATUS_OPEN
    return JobPosting(
        id=str(raw.get("id") or ""),
        tenant_id=str(raw.get("tenant_id") or ""),
        tenant_name=str(raw.get("tenant_name") or ""),
        department=str(raw.get("department") or ""),
        site=str(raw.get("site") or ""),
        title=str(raw.get("title") or ""),
        description=str(raw.get("description") or ""),
        status=status,  # type: ignore[arg-type]
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
        shared=bool(raw.get("shared", True)),
    )


def _parse_applicant(raw: dict[str, Any]) -> Applicant:
    status = str(raw.get("status") or "applied")
    if status not in APPLICANT_STATUS_LABELS:
        status = "applied"
    return Applicant(
        id=str(raw.get("id") or ""),
        tenant_id=str(raw.get("tenant_id") or ""),
        tenant_name=str(raw.get("tenant_name") or ""),
        posting_id=str(raw.get("posting_id") or ""),
        posting_title=str(raw.get("posting_title") or ""),
        name=str(raw.get("name") or ""),
        contact=str(raw.get("contact") or ""),
        resume_notes=str(raw.get("resume_notes") or ""),
        status=status,  # type: ignore[arg-type]
        rrn_key=str(raw.get("rrn_key") or ""),
        rrn_masked=str(raw.get("rrn_masked") or ""),
        dedupe_key=str(raw.get("dedupe_key") or ""),
        recommended=bool(raw.get("recommended")),
        ref_tenant_id=str(raw.get("ref_tenant_id") or ""),
        ref_applicant_id=str(raw.get("ref_applicant_id") or ""),
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
    )


def _sync_posting_to_group(tenant_id: str, posting: dict[str, Any]) -> None:
    gid = _group_id_for(tenant_id)
    if not gid or not posting.get("shared", True):
        return
    with _lock:
        grp = _load_group(gid)
        shared = list(grp.get("shared_postings") or [])
        pid = posting["id"]
        row = deepcopy(posting)
        row["source_tenant_id"] = tenant_id
        row["source_posting_id"] = pid
        shared = [s for s in shared if not (
            s.get("source_tenant_id") == tenant_id and s.get("source_posting_id") == pid
        )]
        if row.get("status") == POSTING_STATUS_OPEN:
            shared.append(row)
        grp["shared_postings"] = shared
        _save_group(gid, grp)


def _remove_posting_from_group(tenant_id: str, posting_id: str) -> None:
    gid = _group_id_for(tenant_id)
    if not gid:
        return
    with _lock:
        grp = _load_group(gid)
        shared = [
            s for s in (grp.get("shared_postings") or [])
            if not (s.get("source_tenant_id") == tenant_id and s.get("source_posting_id") == posting_id)
        ]
        grp["shared_postings"] = shared
        _save_group(gid, grp)


def _sync_talent_to_group(tenant_id: str, applicant: dict[str, Any]) -> None:
    gid = _group_id_for(tenant_id)
    if not gid:
        return
    status = str(applicant.get("status") or "")
    recommended = bool(applicant.get("recommended"))
    if status not in SHAREABLE_APPLICANT_STATUSES and not recommended:
        _remove_talent_from_group(tenant_id, str(applicant.get("dedupe_key") or ""))
        return
    dedupe = str(applicant.get("dedupe_key") or "")
    if not dedupe:
        return
    entry = {
        "dedupe_key": dedupe,
        "name": applicant.get("name") or "",
        "contact": applicant.get("contact") or "",
        "rrn_masked": applicant.get("rrn_masked") or "",
        "resume_notes": applicant.get("resume_notes") or "",
        "source_tenant_id": tenant_id,
        "source_tenant_name": applicant.get("tenant_name") or _tenant_display(tenant_id),
        "source_applicant_id": applicant.get("id") or "",
        "source_posting_id": applicant.get("posting_id") or "",
        "source_posting_title": applicant.get("posting_title") or "",
        "recommended": recommended or status == "talent_pool",
        "shared_at": _now_iso(),
        "names": sorted(set([str(applicant.get("name") or "").strip()])),
    }
    with _lock:
        grp = _load_group(gid)
        pool = dict(grp.get("talent_pool") or {})
        existing = pool.get(dedupe)
        if isinstance(existing, dict):
            names = set(existing.get("names") or [])
            names.add(entry["name"])
            entry["names"] = sorted(n for n in names if n)
        pool[dedupe] = entry
        grp["talent_pool"] = pool
        _save_group(gid, grp)


def _remove_talent_from_group(tenant_id: str, dedupe_key: str) -> None:
    if not dedupe_key:
        return
    gid = _group_id_for(tenant_id)
    if not gid:
        return
    with _lock:
        grp = _load_group(gid)
        pool = dict(grp.get("talent_pool") or {})
        row = pool.get(dedupe_key)
        if isinstance(row, dict) and row.get("source_tenant_id") == tenant_id:
            pool.pop(dedupe_key, None)
        grp["talent_pool"] = pool
        _save_group(gid, grp)


def create_posting(
    *,
    tenant_id: str | None = None,
    department: str,
    site: str = "",
    title: str,
    description: str = "",
    status: PostingStatus = POSTING_STATUS_OPEN,
    shared: bool = True,
) -> dict[str, Any]:
    tid = _tid(tenant_id)
    now = _now_iso()
    row = {
        "id": _new_id(),
        "tenant_id": tid,
        "tenant_name": _tenant_display(tid),
        "department": str(department or "").strip(),
        "site": str(site or "").strip(),
        "title": str(title or "").strip(),
        "description": str(description or "").strip(),
        "status": status,
        "shared": bool(shared),
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        db = _load_tenant(tid)
        db.setdefault("postings", []).append(row)
        _save_tenant(tid, db)
    if shared:
        _sync_posting_to_group(tid, row)
    return _parse_posting(row).to_dict()


def update_posting(
    posting_id: str,
    *,
    tenant_id: str | None = None,
    **fields: Any,
) -> dict[str, Any] | None:
    tid = _tid(tenant_id)
    result: dict[str, Any] | None = None
    with _lock:
        db = _load_tenant(tid)
        for row in db.get("postings") or []:
            if row.get("id") != posting_id:
                continue
            for k, v in fields.items():
                if k in ("department", "site", "title", "description", "status", "shared"):
                    row[k] = v
            row["updated_at"] = _now_iso()
            _save_tenant(tid, db)
            result = deepcopy(row)
            break
    if not result:
        return None
    parsed = _parse_posting(result).to_dict()
    if result.get("shared", True) and result.get("status") == POSTING_STATUS_OPEN:
        _sync_posting_to_group(tid, result)
    else:
        _remove_posting_from_group(tid, posting_id)
    return parsed


def list_my_postings(tenant_id: str | None = None) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    db = _load_tenant(tid)
    return [_parse_posting(p).to_dict() for p in db.get("postings") or [] if isinstance(p, dict)]


def list_group_postings(tenant_id: str | None = None, *, include_own: bool = True) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    gid = _group_id_for(tid)
    if not gid:
        return list_my_postings(tid) if include_own else []
    grp = _load_group(gid)
    out: list[dict[str, Any]] = []
    for raw in grp.get("shared_postings") or []:
        if not isinstance(raw, dict):
            continue
        src = str(raw.get("source_tenant_id") or raw.get("tenant_id") or "")
        if not include_own and src == tid:
            continue
        posting = _parse_posting(raw)
        d = posting.to_dict()
        d["source_tenant_id"] = src
        d["source_posting_id"] = str(raw.get("source_posting_id") or raw.get("id") or "")
        d["is_own"] = src == tid
        out.append(d)
    out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return out


def add_applicant(
    posting_id: str,
    *,
    tenant_id: str | None = None,
    name: str,
    contact: str = "",
    resume_notes: str = "",
    rrn: str = "",
    status: ApplicantStatus = "applied",
    recommended: bool = False,
    ref_tenant_id: str = "",
    ref_applicant_id: str = "",
) -> dict[str, Any]:
    tid = _tid(tenant_id)
    db = _load_tenant(tid)
    posting = next((p for p in db.get("postings") or [] if p.get("id") == posting_id), None)
    if not isinstance(posting, dict):
        raise ValueError("채용공고를 찾을 수 없습니다.")
    rrn_key = normalize_rrn(rrn) or ""
    dedupe = applicant_dedupe_key(rrn=rrn, name=name, contact=contact)
    now = _now_iso()
    row = {
        "id": _new_id(),
        "tenant_id": tid,
        "tenant_name": _tenant_display(tid),
        "posting_id": posting_id,
        "posting_title": posting.get("title") or "",
        "name": str(name or "").strip(),
        "contact": str(contact or "").strip(),
        "resume_notes": str(resume_notes or "").strip(),
        "status": status,
        "rrn_key": rrn_key,
        "rrn_masked": mask_rrn(rrn_key) if rrn_key else "",
        "dedupe_key": dedupe,
        "recommended": bool(recommended),
        "ref_tenant_id": str(ref_tenant_id or "").strip(),
        "ref_applicant_id": str(ref_applicant_id or "").strip(),
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        db = _load_tenant(tid)
        db.setdefault("applicants", []).append(row)
        _save_tenant(tid, db)
    if row["status"] in SHAREABLE_APPLICANT_STATUSES or row["recommended"]:
        _sync_talent_to_group(tid, row)
    return _parse_applicant(row).to_dict()


def update_applicant(
    applicant_id: str,
    *,
    tenant_id: str | None = None,
    **fields: Any,
) -> dict[str, Any] | None:
    tid = _tid(tenant_id)
    result: dict[str, Any] | None = None
    old_dedupe = ""
    with _lock:
        db = _load_tenant(tid)
        for row in db.get("applicants") or []:
            if row.get("id") != applicant_id:
                continue
            old_dedupe = str(row.get("dedupe_key") or "")
            for k, v in fields.items():
                if k in (
                    "name", "contact", "resume_notes", "status", "recommended",
                    "posting_id", "posting_title",
                ):
                    row[k] = v
            if "rrn" in fields:
                rrn_key = normalize_rrn(fields["rrn"]) or ""
                row["rrn_key"] = rrn_key
                row["rrn_masked"] = mask_rrn(rrn_key) if rrn_key else ""
                row["dedupe_key"] = applicant_dedupe_key(
                    rrn=rrn_key, name=row.get("name"), contact=row.get("contact")
                )
            row["updated_at"] = _now_iso()
            _save_tenant(tid, db)
            result = deepcopy(row)
            break
    if not result:
        return None
    new_dedupe = str(result.get("dedupe_key") or "")
    if old_dedupe and old_dedupe != new_dedupe:
        _remove_talent_from_group(tid, old_dedupe)
    if result.get("status") in SHAREABLE_APPLICANT_STATUSES or result.get("recommended"):
        _sync_talent_to_group(tid, result)
    elif old_dedupe:
        _remove_talent_from_group(tid, new_dedupe or old_dedupe)
    return _parse_applicant(result).to_dict()


def list_applicants(
    tenant_id: str | None = None,
    *,
    posting_id: str | None = None,
) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    db = _load_tenant(tid)
    out: list[dict[str, Any]] = []
    for raw in db.get("applicants") or []:
        if not isinstance(raw, dict):
            continue
        if posting_id and raw.get("posting_id") != posting_id:
            continue
        out.append(_parse_applicant(raw).to_dict())
    return out


def list_talent_pool(tenant_id: str | None = None) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    gid = _group_id_for(tid)
    if not gid:
        db = _load_tenant(tid)
        return [
            _parse_applicant(a).to_dict()
            for a in db.get("applicants") or []
            if isinstance(a, dict)
            and (a.get("status") == "talent_pool" or a.get("recommended"))
        ]
    grp = _load_group(gid)
    pool = grp.get("talent_pool") or {}
    out: list[dict[str, Any]] = []
    for key, raw in pool.items():
        if not isinstance(raw, dict):
            continue
        entry = TalentPoolEntry(
            dedupe_key=str(key),
            name=str(raw.get("name") or ""),
            contact=str(raw.get("contact") or ""),
            rrn_masked=str(raw.get("rrn_masked") or ""),
            resume_notes=str(raw.get("resume_notes") or ""),
            source_tenant_id=str(raw.get("source_tenant_id") or ""),
            source_tenant_name=str(raw.get("source_tenant_name") or ""),
            source_applicant_id=str(raw.get("source_applicant_id") or ""),
            source_posting_id=str(raw.get("source_posting_id") or ""),
            source_posting_title=str(raw.get("source_posting_title") or ""),
            recommended=bool(raw.get("recommended")),
            shared_at=str(raw.get("shared_at") or ""),
            names=list(raw.get("names") or []),
        )
        d = entry.to_dict()
        d["is_own"] = d["source_tenant_id"] == tid
        out.append(d)
    out.sort(key=lambda x: x.get("shared_at") or "", reverse=True)
    return out


def link_talent_to_posting(
    dedupe_key: str,
    target_posting_id: str,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """타 법인 인재풀 지원자를 우리 채용공고에 참조 연결."""
    tid = _tid(tenant_id)
    gid = _group_id_for(tid)
    if not gid:
        raise ValueError("그룹에 속하지 않은 법인입니다.")
    grp = _load_group(gid)
    pool = grp.get("talent_pool") or {}
    raw = pool.get(dedupe_key)
    if not isinstance(raw, dict):
        raise ValueError("인재풀 항목을 찾을 수 없습니다.")
    src_tid = str(raw.get("source_tenant_id") or "")
    if src_tid == tid:
        raise ValueError("자사 인재는 「지원자 관리」에서 등록하세요.")
    return add_applicant(
        target_posting_id,
        tenant_id=tid,
        name=str(raw.get("name") or ""),
        contact=str(raw.get("contact") or ""),
        resume_notes=(
            f"[그룹 인재풀 참조 · {raw.get('source_tenant_name') or src_tid} · "
            f"{raw.get('source_posting_title') or ''}]\n"
            f"{raw.get('resume_notes') or ''}"
        ).strip(),
        status="applied",
        ref_tenant_id=src_tid,
        ref_applicant_id=str(raw.get("source_applicant_id") or ""),
    )


def find_duplicate_applicant(
    *,
    tenant_id: str | None = None,
    rrn: str = "",
    name: str = "",
    contact: str = "",
) -> dict[str, Any] | None:
    """동일 테넌트 내 중복 지원자 조회."""
    tid = _tid(tenant_id)
    key = applicant_dedupe_key(rrn=rrn, name=name, contact=contact)
    for row in list_applicants(tid):
        if row.get("dedupe_key") == key:
            return row
    return None


def dashboard_kpis(tenant_id: str | None = None) -> list[tuple[str, str, str]]:
    tid = _tid(tenant_id)
    posts = list_my_postings(tid)
    open_n = sum(1 for p in posts if p.get("status") == POSTING_STATUS_OPEN)
    apps = list_applicants(tid)
    pool = list_talent_pool(tid)
    group_posts = list_group_postings(tid, include_own=False)
    return [
        ("내 공고", str(len(posts)), f"모집중 {open_n}"),
        ("그룹 공고", str(len(group_posts)), "타 법인 공유"),
        ("지원자", str(len(apps)), "전체 등록"),
        ("인재풀", str(len(pool)), "그룹 공유"),
    ]
