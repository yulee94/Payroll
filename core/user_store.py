"""
core/user_store.py - Bitween 사용자 계정 (고객사·개인 격리)
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.roles import ROLE_ADMIN, ROLE_STAFF, normalize_role
from core.org_positions import normalize_position

USERS_FILE = app_data_dir() / "users" / "registry.json"
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
_PBKDF2_ITERS = 120_000


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    tenant_id: str
    username: str
    display_name: str
    role: str = ROLE_STAFF
    org_unit_id: str = ""
    position: str = ""
    manager_user_id: str = ""
    created_at: str = ""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_users_dir() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERS,
    )
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, check = _hash_password(password, salt)
    return secrets.compare_digest(check, hash_hex)


def _load_raw() -> dict[str, Any]:
    _ensure_users_dir()
    if not USERS_FILE.is_file():
        data: dict[str, Any] = {"users": {}, "by_tenant": {}}
        _save_raw(data)
        return data
    try:
        raw = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {"users": {}, "by_tenant": {}}
        raw.setdefault("users", {})
        raw.setdefault("by_tenant", {})
        return raw
    except (OSError, json.JSONDecodeError):
        return {"users": {}, "by_tenant": {}}


def _save_raw(data: dict[str, Any]) -> None:
    _ensure_users_dir()
    USERS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_record(raw: dict[str, Any]) -> UserRecord:
    return UserRecord(
        user_id=str(raw.get("user_id") or ""),
        tenant_id=str(raw.get("tenant_id") or ""),
        username=str(raw.get("username") or ""),
        display_name=str(raw.get("display_name") or ""),
        role=normalize_role(str(raw.get("role") or ROLE_STAFF)),
        org_unit_id=str(raw.get("org_unit_id") or ""),
        position=normalize_position(str(raw.get("position") or "")),
        manager_user_id=str(raw.get("manager_user_id") or ""),
        created_at=str(raw.get("created_at") or ""),
    )


def validate_username(username: str) -> str | None:
    u = str(username or "").strip().lower()
    if not u:
        return "아이디를 입력하세요."
    if not _USERNAME_RE.match(u):
        return "아이디는 영문·숫자·._- 만 3~32자입니다."
    return None


def validate_password(password: str) -> str | None:
    p = str(password or "")
    if len(p) < 6:
        return "비밀번호는 6자 이상입니다."
    if len(p) > 128:
        return "비밀번호가 너무 깁니다."
    return None


def list_users_for_tenant(tenant_id: str) -> list[UserRecord]:
    """동일 고객사 사용자 목록 (메신저 수신자 선택용, 비밀번호 미포함)."""
    raw = _load_raw()
    ids = (raw.get("by_tenant") or {}).get(str(tenant_id).strip(), [])
    users = raw.get("users") or {}
    out: list[UserRecord] = []
    for uid in ids:
        row = users.get(uid)
        if isinstance(row, dict):
            out.append(_to_record(row))
    return sorted(out, key=lambda u: u.display_name.lower())


def find_user_by_username(tenant_id: str, username: str) -> UserRecord | None:
    tid = str(tenant_id).strip()
    uname = str(username or "").strip().lower()
    for rec in list_users_for_tenant(tid):
        if rec.username == uname:
            return rec
    return None


def get_user(user_id: str) -> UserRecord | None:
    raw = _load_raw()
    row = (raw.get("users") or {}).get(str(user_id).strip())
    if isinstance(row, dict):
        return _to_record(row)
    return None


def tenant_has_users(tenant_id: str) -> bool:
    return bool(list_users_for_tenant(tenant_id))


def register_user(
    *,
    tenant_id: str,
    username: str,
    password: str,
    display_name: str,
    org_unit_id: str = "",
    position: str = "",
    manager_user_id: str = "",
    role: str | None = None,
) -> UserRecord:
    tid = str(tenant_id).strip()
    err = validate_username(username)
    if err:
        raise ValueError(err)
    err = validate_password(password)
    if err:
        raise ValueError(err)
    uname = str(username).strip().lower()
    if find_user_by_username(tid, uname):
        raise ValueError("이미 사용 중인 아이디입니다.")
    name = str(display_name or "").strip()
    if not name:
        raise ValueError("표시 이름을 입력하세요.")

    raw = _load_raw()
    users: dict[str, Any] = raw.setdefault("users", {})
    by_tenant: dict[str, list[str]] = raw.setdefault("by_tenant", {})
    uid = uuid.uuid4().hex
    salt_hex, hash_hex = _hash_password(password)
    now = _now_iso()
    initial_role = role if role else (ROLE_ADMIN if not tenant_has_users(tid) else ROLE_STAFF)
    users[uid] = {
        "user_id": uid,
        "tenant_id": tid,
        "username": uname,
        "display_name": name,
        "role": normalize_role(initial_role),
        "org_unit_id": str(org_unit_id or "").strip(),
        "position": normalize_position(position),
        "manager_user_id": str(manager_user_id or "").strip(),
        "password_salt": salt_hex,
        "password_hash": hash_hex,
        "created_at": now,
    }
    by_tenant.setdefault(tid, []).append(uid)
    _save_raw(raw)
    return _to_record(users[uid])


def authenticate(tenant_id: str, username: str, password: str) -> UserRecord:
    tid = str(tenant_id).strip()
    uname = str(username or "").strip().lower()
    raw = _load_raw()
    users = raw.get("users") or {}
    for uid in (raw.get("by_tenant") or {}).get(tid, []):
        row = users.get(uid)
        if not isinstance(row, dict):
            continue
        if str(row.get("username") or "").lower() != uname:
            continue
        salt = str(row.get("password_salt") or "")
        phash = str(row.get("password_hash") or "")
        if _verify_password(password, salt, phash):
            return _to_record(row)
    raise ValueError("아이디 또는 비밀번호가 올바르지 않습니다.")


def authenticate_credentials(
    username: str,
    password: str,
    *,
    preferred_tenant_id: str | None = None,
) -> UserRecord:
    """
    로그인: 우선 preferred_tenant_id에서 확인 후, 없으면 전체 고객사에서 동일 아이디·비밀번호 검색.
    (홈 화면 active 고객사와 계정 소속이 달라도 로그인 가능)
    """
    uname = str(username or "").strip().lower()
    if not uname:
        raise ValueError("아이디를 입력하세요.")
    if not str(password or ""):
        raise ValueError("비밀번호를 입력하세요.")

    if preferred_tenant_id:
        try:
            return authenticate(preferred_tenant_id, uname, password)
        except ValueError:
            pass

    raw = _load_raw()
    by_tenant: dict[str, list[str]] = raw.get("by_tenant") or {}
    users = raw.get("users") or {}
    matched: list[UserRecord] = []

    for tid in by_tenant:
        for uid in by_tenant.get(tid, []):
            row = users.get(uid)
            if not isinstance(row, dict):
                continue
            if str(row.get("username") or "").lower() != uname:
                continue
            salt = str(row.get("password_salt") or "")
            phash = str(row.get("password_hash") or "")
            if _verify_password(password, salt, phash):
                matched.append(_to_record(row))

    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        names = ", ".join({m.tenant_id for m in matched})
        raise ValueError(
            f"동일 아이디가 여러 고객사({names})에 있습니다. 관리자에게 문의하세요."
        )
    raise ValueError("아이디 또는 비밀번호가 올바르지 않습니다.")


def update_user_role(user_id: str, role: str) -> UserRecord:
    uid = str(user_id).strip()
    r = normalize_role(role)
    raw = _load_raw()
    users = raw.get("users") or {}
    row = users.get(uid)
    if not isinstance(row, dict):
        raise ValueError("사용자를 찾을 수 없습니다.")
    row["role"] = r
    _save_raw(raw)
    return _to_record(row)


def update_user_org(
    user_id: str,
    *,
    org_unit_id: str | None = None,
    position: str | None = None,
    manager_user_id: str | None = None,
    display_name: str | None = None,
) -> UserRecord:
    uid = str(user_id).strip()
    raw = _load_raw()
    users = raw.get("users") or {}
    row = users.get(uid)
    if not isinstance(row, dict):
        raise ValueError("사용자를 찾을 수 없습니다.")
    if org_unit_id is not None:
        row["org_unit_id"] = str(org_unit_id or "").strip()
    if position is not None:
        row["position"] = normalize_position(position)
    if manager_user_id is not None:
        row["manager_user_id"] = str(manager_user_id or "").strip()
    if display_name is not None:
        name = str(display_name).strip()
        if not name:
            raise ValueError("표시 이름을 입력하세요.")
        row["display_name"] = name
    _save_raw(raw)
    return _to_record(row)


def list_users_in_org_unit(tenant_id: str, unit_id: str, *, include_subtree: bool = False) -> list[UserRecord]:
    from core.org_store import descendant_unit_ids

    tid = str(tenant_id).strip()
    uid_set = {str(unit_id).strip()}
    if include_subtree:
        uid_set = descendant_unit_ids(tid, str(unit_id).strip(), include_self=True)
    return [u for u in list_users_for_tenant(tid) if u.org_unit_id in uid_set]


def admin_create_user(
    *,
    tenant_id: str,
    username: str,
    password: str,
    display_name: str,
    org_unit_id: str,
    position: str,
    manager_user_id: str = "",
    role: str | None = None,
    creator_user_id: str,
) -> UserRecord:
    """조직 관리자가 하위 팀에 계정 생성."""
    from core.org_access import can_create_subordinate_in_unit, can_manage_org
    from core.session_service import UserSession

    creator = get_user(creator_user_id)
    if creator is None or creator.tenant_id != str(tenant_id).strip():
        raise PermissionError("계정을 생성할 권한이 없습니다.")
    if not can_manage_org(UserSession.from_record(creator)) and not can_create_subordinate_in_unit(
        creator_user_id, org_unit_id
    ):
        raise PermissionError("해당 팀에 계정을 생성할 권한이 없습니다.")
    return register_user(
        tenant_id=tenant_id,
        username=username,
        password=password,
        display_name=display_name,
        org_unit_id=org_unit_id,
        position=position,
        manager_user_id=manager_user_id or creator_user_id,
        role=role,
    )
