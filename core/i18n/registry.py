"""
core/i18n/registry.py - 다국어 카탈로그 및 t() 번역 함수
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from core.i18n.locale_store import DEFAULT_LOCALE, get_saved_locale

LOCALES_DIR = Path(__file__).resolve().parent.parent.parent / "locales"

SUPPORTED_LOCALES: dict[str, dict[str, str]] = {
    "ko": {"name": "한국어", "native": "한국어"},
    "en": {"name": "English", "native": "English"},
    "zh-Hans": {"name": "Chinese (Simplified)", "native": "简体中文"},
    "zh-Hant": {"name": "Chinese (Traditional)", "native": "繁體中文"},
    "ja": {"name": "Japanese", "native": "日本語"},
}

_listeners: list[Callable[[str], None]] = []
_current_locale: str = DEFAULT_LOCALE
_catalogs: dict[str, dict[str, str]] = {}
_fallback_catalog: dict[str, str] = {}


def _flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("locale", "_meta"):
                continue
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, key))
    elif isinstance(obj, str):
        if prefix:
            out[prefix] = obj
    return out


def _load_catalog(locale: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.is_file():
        return {}
    try:
        # locale JSON은 Windows 편집기 등에서 UTF-8 BOM으로 저장되는 경우가 많음
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        return _flatten(raw)
    except (OSError, json.JSONDecodeError):
        return {}


def init_i18n(locale: str | None = None) -> str:
    """앱 시작 시 호출. 저장된 locale 또는 인자 사용."""
    global _current_locale, _fallback_catalog, _catalogs
    _fallback_catalog = _load_catalog(DEFAULT_LOCALE)
    _catalogs = {}
    for code in SUPPORTED_LOCALES:
        _catalogs[code] = _load_catalog(code)
    loc = (locale or get_saved_locale() or DEFAULT_LOCALE).strip()
    if loc not in SUPPORTED_LOCALES:
        loc = DEFAULT_LOCALE
    _current_locale = loc
    return loc


def get_locale() -> str:
    return _current_locale


def set_locale(locale: str) -> None:
    global _current_locale
    loc = (locale or DEFAULT_LOCALE).strip()
    if loc not in SUPPORTED_LOCALES:
        loc = DEFAULT_LOCALE
    if loc == _current_locale:
        return
    _current_locale = loc
    for cb in list(_listeners):
        try:
            cb(loc)
        except Exception:
            pass


def add_locale_listener(cb: Callable[[str], None]) -> None:
    if cb not in _listeners:
        _listeners.append(cb)


def remove_locale_listener(cb: Callable[[str], None]) -> None:
    if cb in _listeners:
        _listeners.remove(cb)


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """
    번역 키 조회. 없으면 default → ko 카탈로그 → key 순 fallback.
    {name} 형식 치환 지원.
    """
    text = _catalogs.get(_current_locale, {}).get(key)
    if not text and _current_locale != DEFAULT_LOCALE:
        text = _catalogs.get(DEFAULT_LOCALE, {}).get(key)
    if not text:
        text = _fallback_catalog.get(key)
    if not text:
        text = default if default is not None else key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def tf(platform_id: str, field: str, fallback: str = "") -> str:
    """platform.{id}.{field} 단축."""
    return t(f"platform.{platform_id}.{field}", default=fallback)


def locale_display_name(code: str) -> str:
    meta = SUPPORTED_LOCALES.get(code, {})
    return meta.get("native") or meta.get("name") or code


_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def extract_placeholders(text: str) -> list[str]:
    return _PLACEHOLDER_RE.findall(text)
