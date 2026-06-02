"""
core/theme_store.py - 사용자별 UI 테마 저장
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.session_service import UserSession, get_session

THEME_FILE = app_data_dir() / "theme.json"
DEFAULT_THEME_ID = "navy"


def _load() -> dict[str, Any]:
    if not THEME_FILE.is_file():
        return {}
    try:
        data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, Any]) -> None:
    THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    THEME_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_saved_theme_id(session: UserSession | None = None) -> str:
    from ui.theme_presets import PRESET_ORDER

    data = _load()
    sess = session or get_session()
    theme_id = DEFAULT_THEME_ID
    if sess:
        users = data.get("users") or {}
        if isinstance(users, dict) and sess.user_id in users:
            theme_id = str(users[sess.user_id] or DEFAULT_THEME_ID)
    else:
        theme_id = str(data.get("default") or DEFAULT_THEME_ID)
    if theme_id not in PRESET_ORDER:
        return DEFAULT_THEME_ID
    return theme_id


def set_saved_theme_id(theme_id: str, session: UserSession | None = None) -> None:
    from ui.theme_presets import PRESET_ORDER

    theme_id = (theme_id or DEFAULT_THEME_ID).strip()
    if theme_id not in PRESET_ORDER:
        theme_id = DEFAULT_THEME_ID
    data = _load()
    sess = session or get_session()
    if sess:
        users = dict(data.get("users") or {})
        users[sess.user_id] = theme_id
        data["users"] = users
    data["default"] = theme_id
    _save(data)


def load_user_theme(session: UserSession | None = None) -> str:
    """저장된 테마를 불러와 전역 COLORS에 적용."""
    from ui.theme import apply_theme

    theme_id = get_saved_theme_id(session)
    apply_theme(theme_id)
    return theme_id
