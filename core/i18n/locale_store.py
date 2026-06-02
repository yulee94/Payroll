"""
core/i18n/locale_store.py - 사용자/앱 언어 설정 저장
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.session_service import get_session

LOCALE_FILE = app_data_dir() / "locale.json"
DEFAULT_LOCALE = "ko"


def _load() -> dict[str, Any]:
    if not LOCALE_FILE.is_file():
        return {}
    try:
        data = json.loads(LOCALE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, Any]) -> None:
    LOCALE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCALE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_saved_locale() -> str:
    data = _load()
    sess = get_session()
    if sess:
        per_user = data.get("users") or {}
        if isinstance(per_user, dict) and sess.user_id in per_user:
            return str(per_user[sess.user_id] or DEFAULT_LOCALE)
    return str(data.get("default") or DEFAULT_LOCALE)


def set_saved_locale(locale: str) -> None:
    locale = (locale or DEFAULT_LOCALE).strip()
    data = _load()
    sess = get_session()
    if sess:
        users = dict(data.get("users") or {})
        users[sess.user_id] = locale
        data["users"] = users
    data["default"] = locale
    _save(data)
