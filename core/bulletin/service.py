"""
core/bulletin/service.py - 그룹 공유 게시판 (공지)

본사·관리자가 법인/사업장 범위를 지정해 그룹 전체에 공지를 게시합니다.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.group_store import get_group_for_tenant, list_legal_entities
from core.org_access import can_manage_org, can_manage_tenant_settings, has_permission
from core.org_positions import PERM_ORG_MANAGE, PERM_TENANT_ADMIN
from core.paths import app_data_dir
from core.session_service import UserSession, get_session, require_session
from core.tenant_store import get_tenant, list_tenants

_STORE_PATH = app_data_dir() / "bulletin" / "announcements.json"
_lock = threading.Lock()


@dataclass
class SiteRef:
    tenant_id: str
    site_id: str
    site_name: str
    tenant_name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tenant_id": self.tenant_id,
            "site_id": self.site_id,
            "site_name": self.site_name,
            "tenant_name": self.tenant_name,
        }


@dataclass
class BulletinVisibility:
    all_group: bool = False
    tenants: list[str] = field(default_factory=list)
    sites: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_group": self.all_group,
            "tenants": list(self.tenants),
            "sites": [dict(s) for s in self.sites],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> BulletinVisibility:
        if not isinstance(raw, dict):
            return cls()
        sites: list[dict[str, str]] = []
        for row in raw.get("sites") or []:
            if not isinstance(row, dict):
                continue
            tid = str(row.get("tenant_id") or "").strip()
            sid = str(row.get("site_id") or "").strip()
            if tid and sid:
                sites.append({"tenant_id": tid, "site_id": sid})
        tenants = [str(t).strip() for t in (raw.get("tenants") or []) if str(t).strip()]
        return cls(
            all_group=bool(raw.get("all_group")),
            tenants=tenants,
            sites=sites,
        )


@dataclass
class Announcement:
    id: str
    title: str
    body: str
    author_user_id: str
    author_name: str
    author_tenant_id: str
    author_org: str
    created_at: str
    updated_at: str
    pinned: bool
    visibility: BulletinVisibility

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "author_user_id": self.author_user_id,
            "author_name": self.author_name,
            "author_tenant_id": self.author_tenant_id,
            "author_org": self.author_org,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "pinned": self.pinned,
            "visibility": self.visibility.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Announcement:
        return cls(
            id=str(raw.get("id") or ""),
            title=str(raw.get("title") or ""),
            body=str(raw.get("body") or ""),
            author_user_id=str(raw.get("author_user_id") or ""),
            author_name=str(raw.get("author_name") or ""),
            author_tenant_id=str(raw.get("author_tenant_id") or ""),
            author_org=str(raw.get("author_org") or ""),
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            pinned=bool(raw.get("pinned")),
            visibility=BulletinVisibility.from_dict(raw.get("visibility")),
        )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "announcements": []}


def _load_store() -> dict[str, Any]:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.is_file():
        return _empty_store()
    try:
        raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw.setdefault("announcements", [])
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_store()


def _save_store(data: dict[str, Any]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _tenant_display(tenant_id: str) -> str:
    rec = get_tenant(tenant_id)
    if rec:
        return rec.display_name_ko or rec.display_name or tenant_id
    return tenant_id


def _is_group_hq_tenant(tenant_id: str) -> bool:
    grp = get_group_for_tenant(tenant_id)
    if not grp:
        return False
    for ent in list_legal_entities(grp.group_id):
        if ent.tenant_id == tenant_id and ent.is_group_hq:
            return True
    return False


def can_post_bulletin(session: UserSession | None = None) -> bool:
    """그룹 본사 관리자 또는 법인(테넌트) 관리자."""
    sess = session or get_session()
    if sess is None:
        return False
    if can_manage_org(sess) or can_manage_tenant_settings(sess):
        return True
    return has_permission(PERM_ORG_MANAGE, session=sess) or has_permission(
        PERM_TENANT_ADMIN, session=sess
    )


def can_post_group_wide(session: UserSession | None = None) -> bool:
    """전체 그룹·타 법인 대상 공지 — 그룹 본사 관리자."""
    sess = session or get_session()
    if sess is None:
        return False
    if not _is_group_hq_tenant(sess.tenant_id):
        return False
    return can_manage_org(sess) or can_manage_tenant_settings(sess) or has_permission(
        PERM_ORG_MANAGE, session=sess
    )


def list_group_tenants(tenant_id: str) -> list[tuple[str, str]]:
    """(tenant_id, display_name) — 그룹 소속 법인."""
    grp = get_group_for_tenant(tenant_id)
    if grp:
        ids = list(grp.tenant_ids)
    else:
        ids = [tenant_id]
    out: list[tuple[str, str]] = []
    for tid in ids:
        out.append((tid, _tenant_display(tid)))
    return sorted(out, key=lambda x: x[1])


def _workflow_sites(tenant_id: str) -> list[dict[str, str]]:
    try:
        from core.workflow.store import list_sites

        rows = list_sites(tenant_id)
    except Exception:
        rows = []
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("site_id") or "").strip()
        name = str(row.get("name") or sid).strip()
        if sid:
            out.append({"site_id": sid, "site_name": name})
    return out


def _org_config_sites(tenant_id: str) -> list[dict[str, str]]:
    """organizations.json 사업장 — workflow sites 보완."""
    rec = get_tenant(tenant_id)
    affiliates = set(rec.data_affiliates if rec else ())
    if not affiliates:
        affiliates = {_tenant_display(tenant_id)}
    try:
        from core.org_config import list_config_workplaces

        out: list[dict[str, str]] = []
        seen: set[str] = set()
        for aff in affiliates:
            for wp in list_config_workplaces(aff):
                sid = f"wp:{wp}"
                if sid in seen:
                    continue
                seen.add(sid)
                out.append({"site_id": sid, "site_name": wp})
        return out
    except Exception:
        return []


def list_group_sites(tenant_id: str) -> list[SiteRef]:
    """그룹 내 모든 법인·사업장."""
    out: list[SiteRef] = []
    for tid, tname in list_group_tenants(tenant_id):
        seen: set[str] = set()
        for row in _workflow_sites(tid) + _org_config_sites(tid):
            sid = row["site_id"]
            if sid in seen:
                continue
            seen.add(sid)
            out.append(
                SiteRef(
                    tenant_id=tid,
                    site_id=sid,
                    site_name=row["site_name"],
                    tenant_name=tname,
                )
            )
    return out


def resolve_viewer_context(
    *,
    tenant_id: str,
    user_id: str = "",
) -> tuple[str, list[str]]:
    """시청자 tenant + site_ids (workflow 프로필)."""
    site_ids: list[str] = []
    if user_id:
        try:
            from core.workflow.store import get_user_profile

            prof = get_user_profile(tenant_id, user_id)
            if prof:
                site_ids = [str(s).strip() for s in (prof.get("site_ids") or []) if str(s).strip()]
        except Exception:
            pass
    return tenant_id, site_ids


def _site_name_lookup() -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for t in list_tenants():
        for row in _workflow_sites(t.tenant_id) + _org_config_sites(t.tenant_id):
            lookup[(t.tenant_id, row["site_id"])] = row["site_name"]
    return lookup


def format_scope_preview(visibility: BulletinVisibility) -> str:
    if visibility.all_group:
        return "노출: 전체 그룹"
    parts: list[str] = []
    if visibility.tenants:
        names = [_tenant_display(t) for t in visibility.tenants]
        parts.append("법인: " + ", ".join(names))
    if visibility.sites:
        lookup = _site_name_lookup()
        site_labels: list[str] = []
        for s in visibility.sites:
            tid = s.get("tenant_id", "")
            sid = s.get("site_id", "")
            label = lookup.get((tid, sid), sid)
            tname = _tenant_display(tid)
            site_labels.append(f"{label}({tname})")
        parts.append("사업장: " + ", ".join(site_labels))
    return "노출: " + (" / ".join(parts) if parts else "미지정")


def format_scope_badge(visibility: BulletinVisibility) -> str:
    if visibility.all_group:
        return "전체"
    tags: list[str] = []
    if visibility.tenants:
        tags.append(f"법인 {len(visibility.tenants)}")
    if visibility.sites:
        tags.append(f"사업장 {len(visibility.sites)}")
    return " · ".join(tags) if tags else "지정"


def is_visible_to(
    announcement: Announcement,
    *,
    tenant_id: str,
    site_ids: list[str] | None = None,
) -> bool:
    vis = announcement.visibility
    if vis.all_group:
        return True
    sites = site_ids or []
    if tenant_id in vis.tenants:
        return True
    for ref in vis.sites:
        if ref.get("tenant_id") != tenant_id:
            continue
        sid = ref.get("site_id", "")
        if not sites:
            continue
        if sid in sites:
            return True
    return False


def _validate_visibility(
    visibility: BulletinVisibility,
    *,
    author_tenant_id: str,
    group_wide: bool,
) -> None:
    if visibility.all_group and not group_wide:
        raise ValueError("전체 그룹 공지는 그룹 본사 관리자만 작성할 수 있습니다.")
    grp = get_group_for_tenant(author_tenant_id)
    allowed_tenants = set(grp.tenant_ids if grp else (author_tenant_id,))
    for tid in visibility.tenants:
        if tid not in allowed_tenants:
            raise ValueError(f"선택할 수 없는 법인입니다: {tid}")
    for ref in visibility.sites:
        tid = ref.get("tenant_id", "")
        if tid not in allowed_tenants:
            raise ValueError(f"선택할 수 없는 사업장 법인입니다: {tid}")
    if not group_wide:
        if visibility.all_group:
            raise ValueError("전체 그룹 공지 권한이 없습니다.")
        extra_tenants = [t for t in visibility.tenants if t != author_tenant_id]
        if extra_tenants:
            raise ValueError("다른 법인 대상 공지는 그룹 본사 관리자만 작성할 수 있습니다.")
        for ref in visibility.sites:
            if ref.get("tenant_id") != author_tenant_id:
                raise ValueError("다른 법인 사업장은 그룹 본사 관리자만 지정할 수 있습니다.")
    if not visibility.all_group and not visibility.tenants and not visibility.sites:
        raise ValueError("노출 범위(전체 그룹·법인·사업장)를 하나 이상 선택하세요.")


def list_announcements_for_viewer(
    *,
    tenant_id: str,
    user_id: str = "",
    limit: int = 50,
) -> list[Announcement]:
    _, site_ids = resolve_viewer_context(tenant_id=tenant_id, user_id=user_id)
    with _lock:
        store = _load_store()
        rows = store.get("announcements") or []
    items = [Announcement.from_dict(r) for r in rows if isinstance(r, dict)]
    visible = [a for a in items if is_visible_to(a, tenant_id=tenant_id, site_ids=site_ids)]
    visible.sort(key=lambda a: (not a.pinned, a.created_at), reverse=True)
    return visible[:limit]


def get_announcement(announcement_id: str) -> Announcement | None:
    aid = str(announcement_id).strip()
    with _lock:
        store = _load_store()
        for row in store.get("announcements") or []:
            if isinstance(row, dict) and str(row.get("id")) == aid:
                return Announcement.from_dict(row)
    return None


def create_announcement(
    *,
    title: str,
    body: str,
    visibility: BulletinVisibility,
    pinned: bool = False,
    session: UserSession | None = None,
) -> Announcement:
    sess = require_session() if session is None else session
    if not can_post_bulletin(sess):
        raise PermissionError("공지 작성 권한이 없습니다.")
    title_s = str(title or "").strip()
    body_s = str(body or "").strip()
    if not title_s:
        raise ValueError("제목을 입력하세요.")
    if not body_s:
        raise ValueError("내용을 입력하세요.")
    group_wide = can_post_group_wide(sess)
    _validate_visibility(visibility, author_tenant_id=sess.tenant_id, group_wide=group_wide)
    now = _now_iso()
    grp = get_group_for_tenant(sess.tenant_id)
    author_org = _tenant_display(sess.tenant_id)
    if grp:
        for ent in list_legal_entities(grp.group_id):
            if ent.tenant_id == sess.tenant_id:
                author_org = ent.name_ko or ent.code or author_org
                break
    ann = Announcement(
        id=uuid.uuid4().hex[:12],
        title=title_s,
        body=body_s,
        author_user_id=sess.user_id,
        author_name=sess.display_name,
        author_tenant_id=sess.tenant_id,
        author_org=author_org,
        created_at=now,
        updated_at=now,
        pinned=bool(pinned),
        visibility=visibility,
    )
    with _lock:
        store = _load_store()
        rows: list[dict[str, Any]] = list(store.get("announcements") or [])
        rows.append(ann.to_dict())
        store["announcements"] = rows
        _save_store(store)
    return ann


def update_announcement(
    announcement_id: str,
    *,
    title: str | None = None,
    body: str | None = None,
    visibility: BulletinVisibility | None = None,
    pinned: bool | None = None,
    session: UserSession | None = None,
) -> Announcement:
    sess = require_session() if session is None else session
    if not can_post_bulletin(sess):
        raise PermissionError("공지 수정 권한이 없습니다.")
    group_wide = can_post_group_wide(sess)
    with _lock:
        store = _load_store()
        rows: list[dict[str, Any]] = list(store.get("announcements") or [])
        idx = next(
            (i for i, r in enumerate(rows) if isinstance(r, dict) and r.get("id") == announcement_id),
            None,
        )
        if idx is None:
            raise ValueError("공지를 찾을 수 없습니다.")
        ann = Announcement.from_dict(rows[idx])
        if title is not None:
            t = str(title).strip()
            if not t:
                raise ValueError("제목을 입력하세요.")
            ann.title = t
        if body is not None:
            b = str(body).strip()
            if not b:
                raise ValueError("내용을 입력하세요.")
            ann.body = b
        if visibility is not None:
            _validate_visibility(visibility, author_tenant_id=sess.tenant_id, group_wide=group_wide)
            ann.visibility = visibility
        if pinned is not None:
            ann.pinned = bool(pinned)
        ann.updated_at = _now_iso()
        rows[idx] = ann.to_dict()
        store["announcements"] = rows
        _save_store(store)
    return ann


def delete_announcement(announcement_id: str, *, session: UserSession | None = None) -> None:
    sess = require_session() if session is None else session
    if not can_post_bulletin(sess):
        raise PermissionError("공지 삭제 권한이 없습니다.")
    with _lock:
        store = _load_store()
        rows: list[dict[str, Any]] = list(store.get("announcements") or [])
        new_rows = [r for r in rows if not (isinstance(r, dict) and r.get("id") == announcement_id)]
        if len(new_rows) == len(rows):
            raise ValueError("공지를 찾을 수 없습니다.")
        store["announcements"] = new_rows
        _save_store(store)


def reset_store_for_tests(path: Path | None = None) -> None:
    """테스트용 — 저장소 초기화."""
    global _STORE_PATH
    if path is not None:
        _STORE_PATH = path
    p = _STORE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    _save_store(_empty_store())
