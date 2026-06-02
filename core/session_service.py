"""
core/session_service.py - 로그인 세션 (계정별 데이터 접근 키)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.paths import app_data_dir
from core.user_store import UserRecord, get_user

SESSION_FILE = app_data_dir() / "session.json"
# Dev (python main.py): <project>/session.json
# Installed EXE: %LOCALAPPDATA%\Bitween\Payroll\session.json

OnSessionChanged = Callable[[], None]


@dataclass(frozen=True)
class UserSession:
    user_id: str
    tenant_id: str
    username: str
    display_name: str
    role: str = "staff"

    @classmethod
    def from_record(cls, rec: UserRecord) -> UserSession:
        from core.roles import normalize_role

        return cls(
            user_id=rec.user_id,
            tenant_id=rec.tenant_id,
            username=rec.username,
            display_name=rec.display_name,
            role=normalize_role(rec.role),
        )


_session: UserSession | None = None
_listeners: list[OnSessionChanged] = []


def add_session_listener(cb: OnSessionChanged) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def remove_session_listener(cb: OnSessionChanged) -> None:
    if cb in _listeners:
        _listeners.remove(cb)


def _notify() -> None:
    for cb in list(_listeners):
        try:
            cb()
        except Exception:
            pass


def get_session() -> UserSession | None:
    return _session


def is_logged_in() -> bool:
    return _session is not None


def require_session() -> UserSession:
    if _session is None:
        raise PermissionError("로그인이 필요합니다.")
    return _session


def session_tenant_id() -> str | None:
    """Payroll/UI data scope: logged-in user's tenant only (never global active tenant)."""
    sess = get_session()
    return sess.tenant_id if sess else None


def login(rec: UserRecord, *, remember: bool = True) -> UserSession:
    global _session
    from core.tenant_store import set_active_tenant

    set_active_tenant(rec.tenant_id)
    sess = UserSession.from_record(rec)
    _session = sess
    if remember:
        _save_session_file(sess)
    else:
        _clear_session_file()
    _notify()
    return sess


def logout(*, clear_saved: bool = True) -> None:
    global _session
    _session = None
    if clear_saved:
        _clear_session_file()
    _notify()


def clear_session_for_tenant_change() -> None:
    """고객사 전환 시 다른 법인 데이터 접근 방지."""
    logout(clear_saved=True)


def _save_session_file(sess: UserSession) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps(
            {
                "user_id": sess.user_id,
                "tenant_id": sess.tenant_id,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _clear_session_file() -> None:
    try:
        if SESSION_FILE.is_file():
            SESSION_FILE.unlink()
    except OSError:
        pass


def try_restore_session(expected_tenant_id: str | None = None) -> UserSession | None:
    """저장된 세션 복원. 성공 시 활성 고객사를 사용자 tenant로 맞춤."""
    global _session
    if not SESSION_FILE.is_file():
        return None
    try:
        raw: dict[str, Any] = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        uid = str(raw.get("user_id") or "").strip()
        tid = str(raw.get("tenant_id") or "").strip()
        rec = get_user(uid)
        if rec is None or rec.tenant_id != tid:
            _clear_session_file()
            return None
        if expected_tenant_id and tid != str(expected_tenant_id).strip():
            # 레거시: 특정 tenant만 허용할 때만 사용 (일반 기동에서는 None 전달)
            _clear_session_file()
            return None
        from core.tenant_store import set_active_tenant

        set_active_tenant(rec.tenant_id)
        _session = UserSession.from_record(rec)
        return _session
    except (OSError, json.JSONDecodeError):
        return None
