"""
core/tenant_store.py - Bitween 멀티 테넌트(고객사) · 화이트라벨 설정

법인 A가 사용 시 화면의 회사명·로고를 A 기준으로 표시합니다.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import LOGO_PATH
from core.paths import app_data_dir

DEFAULT_TENANT_ID = "coss"
TENANTS_FILE = app_data_dir() / "tenants.json"
TENANT_LOGOS_DIR = app_data_dir() / "tenant_logos"

_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,31}$")


@dataclass
class TenantRecord:
    tenant_id: str
    display_name: str
    login_id: str
    display_name_ko: str = ""
    notes: str = ""
    logo_filename: str = ""
    contact: str = ""
    default_site: str = ""
    onboarding_completed: bool = True
    data_affiliates: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""

    @property
    def logo_path(self) -> Path | None:
        if not self.logo_filename:
            return None
        p = TENANT_LOGOS_DIR / self.tenant_id / self.logo_filename
        return p if p.is_file() else None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_registry() -> dict[str, Any]:
    return {
        "active_tenant_id": DEFAULT_TENANT_ID,
        "tenants": {
            DEFAULT_TENANT_ID: {
                "tenant_id": DEFAULT_TENANT_ID,
                "display_name": "COSS Group",
                "display_name_ko": "(주)코스",
                "login_id": "coss",
                "notes": "Bitween 기본 운영사 (COSS)",
                "logo_filename": "",
                "contact": "",
                "default_site": "",
                "onboarding_completed": True,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        },
    }


def _ensure_dirs() -> None:
    TENANT_LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    TENANTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_registry() -> dict[str, Any]:
    _ensure_dirs()
    if not TENANTS_FILE.is_file():
        data = _default_registry()
        save_registry(data)
        return data
    try:
        raw = json.loads(TENANTS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default_registry()
        if "tenants" not in raw or not isinstance(raw["tenants"], dict):
            raw["tenants"] = {}
        if DEFAULT_TENANT_ID not in raw["tenants"]:
            raw["tenants"][DEFAULT_TENANT_ID] = _default_registry()["tenants"][DEFAULT_TENANT_ID]
        active = str(raw.get("active_tenant_id") or DEFAULT_TENANT_ID).strip()
        if active not in raw["tenants"]:
            raw["active_tenant_id"] = DEFAULT_TENANT_ID
        return raw
    except (OSError, json.JSONDecodeError):
        return _default_registry()


def save_registry(data: dict[str, Any]) -> None:
    _ensure_dirs()
    TENANTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_data_affiliates(raw: dict[str, Any]) -> tuple[str, ...]:
    explicit = raw.get("data_affiliates")
    if isinstance(explicit, list) and explicit:
        return tuple(str(a).strip() for a in explicit if str(a).strip())
    ko = str(raw.get("display_name_ko") or "").strip()
    if ko:
        return (ko,)
    name = str(raw.get("display_name") or "").strip()
    if name:
        return (name,)
    return ()


def _to_record(raw: dict[str, Any]) -> TenantRecord:
    oc = raw.get("onboarding_completed")
    if oc is None:
        onboarding_completed = True
    else:
        onboarding_completed = bool(oc)
    return TenantRecord(
        tenant_id=str(raw.get("tenant_id") or "").strip(),
        display_name=str(raw.get("display_name") or "").strip(),
        login_id=str(raw.get("login_id") or "").strip(),
        display_name_ko=str(raw.get("display_name_ko") or "").strip(),
        notes=str(raw.get("notes") or "").strip(),
        logo_filename=str(raw.get("logo_filename") or "").strip(),
        contact=str(raw.get("contact") or "").strip(),
        default_site=str(raw.get("default_site") or "").strip(),
        onboarding_completed=onboarding_completed,
        data_affiliates=_parse_data_affiliates(raw),
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
    )


def list_tenants() -> list[TenantRecord]:
    reg = load_registry()
    tenants = reg.get("tenants") or {}
    rows = [_to_record(v) for v in tenants.values() if isinstance(v, dict)]
    return sorted(rows, key=lambda t: t.tenant_id)


def get_active_tenant_id() -> str:
    return str(load_registry().get("active_tenant_id") or DEFAULT_TENANT_ID)


def get_active_tenant() -> TenantRecord:
    reg = load_registry()
    tid = str(reg.get("active_tenant_id") or DEFAULT_TENANT_ID)
    tenants = reg.get("tenants") or {}
    raw = tenants.get(tid)
    if isinstance(raw, dict):
        return _to_record(raw)
    return _to_record(_default_registry()["tenants"][DEFAULT_TENANT_ID])


def get_tenant(tenant_id: str) -> TenantRecord | None:
    reg = load_registry()
    raw = (reg.get("tenants") or {}).get(str(tenant_id).strip())
    if isinstance(raw, dict):
        return _to_record(raw)
    return None


def set_active_tenant(tenant_id: str) -> TenantRecord:
    tid = str(tenant_id).strip()
    reg = load_registry()
    if tid not in (reg.get("tenants") or {}):
        raise ValueError(f"고객사 ID '{tid}' 를 찾을 수 없습니다.")
    reg["active_tenant_id"] = tid
    save_registry(reg)
    return get_active_tenant()


def normalize_tenant_id(text: str) -> str:
    return str(text or "").strip().lower()


def validate_tenant_id(tenant_id: str) -> str | None:
    tid = normalize_tenant_id(tenant_id)
    if not tid:
        return "고객사 ID를 입력하세요."
    if not _TENANT_ID_RE.match(tid):
        return "ID는 영문·숫자·_·- 만 2~32자 (첫 글자는 영숫자)입니다."
    return None


def validate_login_id(login_id: str) -> str | None:
    lid = str(login_id or "").strip()
    if not lid:
        return "로그인 아이디를 입력하세요."
    if len(lid) < 3 or len(lid) > 40:
        return "아이디는 3~40자입니다."
    if not re.match(r"^[a-zA-Z0-9_.@-]+$", lid):
        return "아이디는 영문·숫자·._@- 만 사용할 수 있습니다."
    return None


def create_tenant(
    *,
    tenant_id: str,
    display_name: str,
    login_id: str,
    display_name_ko: str = "",
    notes: str = "",
    set_active: bool = False,
) -> TenantRecord:
    tid = normalize_tenant_id(tenant_id)
    err = validate_tenant_id(tid)
    if err:
        raise ValueError(err)
    err = validate_login_id(login_id)
    if err:
        raise ValueError(err)
    name = str(display_name or "").strip()
    if not name:
        raise ValueError("고객사 표시명을 입력하세요.")

    reg = load_registry()
    tenants: dict[str, Any] = reg.setdefault("tenants", {})
    if tid in tenants:
        raise ValueError(f"이미 등록된 고객사 ID입니다: {tid}")

    now = _now_iso()
    ko = str(display_name_ko or "").strip()
    tenants[tid] = {
        "tenant_id": tid,
        "display_name": name,
        "display_name_ko": ko,
        "login_id": str(login_id).strip(),
        "notes": str(notes or "").strip(),
        "logo_filename": "",
        "contact": "",
        "default_site": "",
        "onboarding_completed": False,
        "data_affiliates": [ko] if ko else [name],
        "created_at": now,
        "updated_at": now,
    }
    if set_active:
        reg["active_tenant_id"] = tid
    save_registry(reg)
    (TENANT_LOGOS_DIR / tid).mkdir(parents=True, exist_ok=True)
    return get_tenant(tid) or get_active_tenant()


def update_tenant(
    tenant_id: str,
    *,
    display_name: str | None = None,
    login_id: str | None = None,
    display_name_ko: str | None = None,
    notes: str | None = None,
    contact: str | None = None,
    default_site: str | None = None,
    onboarding_completed: bool | None = None,
) -> TenantRecord:
    tid = normalize_tenant_id(tenant_id)
    reg = load_registry()
    tenants: dict[str, Any] = reg.get("tenants") or {}
    raw = tenants.get(tid)
    if not isinstance(raw, dict):
        raise ValueError(f"고객사를 찾을 수 없습니다: {tid}")

    if display_name is not None:
        name = str(display_name).strip()
        if not name:
            raise ValueError("고객사 표시명을 입력하세요.")
        raw["display_name"] = name
    if login_id is not None:
        err = validate_login_id(login_id)
        if err:
            raise ValueError(err)
        raw["login_id"] = str(login_id).strip()
    if display_name_ko is not None:
        raw["display_name_ko"] = str(display_name_ko).strip()
    if notes is not None:
        raw["notes"] = str(notes).strip()
    if contact is not None:
        raw["contact"] = str(contact).strip()
    if default_site is not None:
        raw["default_site"] = str(default_site).strip()
    if onboarding_completed is not None:
        raw["onboarding_completed"] = bool(onboarding_completed)
    raw["updated_at"] = _now_iso()
    save_registry(reg)
    return _to_record(raw)


def tenant_needs_onboarding(tenant_id: str) -> bool:
    """첫 로그인 설정: 로고·기본 정보 미완료 테넌트."""
    rec = get_tenant(tenant_id)
    if rec is None or rec.onboarding_completed:
        return False
    missing_logo = not tenant_has_custom_logo(tenant_id)
    missing_ko = not rec.display_name_ko.strip()
    missing_contact = not rec.contact.strip()
    return missing_logo or missing_ko or missing_contact


def mark_onboarding_completed(tenant_id: str) -> TenantRecord:
    return update_tenant(tenant_id, onboarding_completed=True)


def delete_tenant(tenant_id: str) -> None:
    tid = normalize_tenant_id(tenant_id)
    if tid == DEFAULT_TENANT_ID:
        raise ValueError("기본 운영사(COSS)는 삭제할 수 없습니다.")
    reg = load_registry()
    tenants: dict[str, Any] = reg.get("tenants") or {}
    if tid not in tenants:
        raise ValueError(f"고객사를 찾을 수 없습니다: {tid}")
    if reg.get("active_tenant_id") == tid:
        raise ValueError("현재 사용 중인 고객사는 삭제할 수 없습니다. 다른 고객사를 활성화한 뒤 삭제하세요.")
    del tenants[tid]
    save_registry(reg)
    logo_dir = TENANT_LOGOS_DIR / tid
    if logo_dir.is_dir():
        shutil.rmtree(logo_dir, ignore_errors=True)


def resolve_company_logo_path() -> Path:
    """활성 테넌트 로고 → 없으면 기본 COSS 로고."""
    return resolve_tenant_logo_path(get_active_tenant_id())


def resolve_tenant_logo_path(tenant_id: str) -> Path:
    """지정 법인(테넌트) 로고 → 없으면 기본 COSS 로고."""
    rec = get_tenant(tenant_id)
    if rec and rec.logo_path is not None:
        return rec.logo_path
    return LOGO_PATH


def tenant_has_custom_logo(tenant_id: str) -> bool:
    rec = get_tenant(tenant_id)
    return rec is not None and rec.logo_path is not None


def save_tenant_logo(tenant_id: str, source_path: Path) -> TenantRecord:
    tid = normalize_tenant_id(tenant_id)
    src = Path(source_path)
    if not src.is_file():
        raise ValueError("로고 파일을 찾을 수 없습니다.")

    suffix = src.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise ValueError("로고는 PNG·JPG·GIF·WEBP 형식만 지원합니다.")

    reg = load_registry()
    tenants: dict[str, Any] = reg.get("tenants") or {}
    raw = tenants.get(tid)
    if not isinstance(raw, dict):
        raise ValueError(f"고객사를 찾을 수 없습니다: {tid}")

    dest_dir = TENANT_LOGOS_DIR / tid
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob("logo.*"):
        try:
            old.unlink()
        except OSError:
            pass

    dest_name = f"logo{suffix}"
    dest = dest_dir / dest_name
    shutil.copy2(src, dest)

    raw["logo_filename"] = dest_name
    raw["updated_at"] = _now_iso()
    save_registry(reg)
    return _to_record(raw)


def clear_tenant_logo(tenant_id: str) -> TenantRecord:
    tid = normalize_tenant_id(tenant_id)
    reg = load_registry()
    tenants: dict[str, Any] = reg.get("tenants") or {}
    raw = tenants.get(tid)
    if not isinstance(raw, dict):
        raise ValueError(f"고객사를 찾을 수 없습니다: {tid}")
    logo_dir = TENANT_LOGOS_DIR / tid
    if logo_dir.is_dir():
        shutil.rmtree(logo_dir, ignore_errors=True)
    logo_dir.mkdir(parents=True, exist_ok=True)
    raw["logo_filename"] = ""
    raw["updated_at"] = _now_iso()
    save_registry(reg)
    return _to_record(raw)
