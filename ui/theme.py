"""
ui/theme.py - COSS Group UI 테마 (프리셋·개인 설정)
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from ui.theme_presets import DEFAULT_THEME_ID, PRESET_ORDER, THEME_PRESETS

# 전역 팔레트 — apply_theme()로 내용이 바뀌며, from ui.theme import COLORS 참조는 동일 dict 유지
COLORS: dict[str, str] = deepcopy(THEME_PRESETS[DEFAULT_THEME_ID]["colors"])

FONT = "맑은 고딕"
FONT_TITLE = (FONT, 20, "bold")
FONT_SUBTITLE = (FONT, 10)
FONT_NAV = (FONT, 11)
FONT_BODY = (FONT, 10)
FONT_STAT = (FONT, 18, "bold")

SIDEBAR_WIDTH = 264
WINDOW_DEFAULT = "1320x860"
WINDOW_MIN = (1120, 720)

_theme_listeners: list[Callable[[str], None]] = []
_current_theme_id: str = DEFAULT_THEME_ID


def get_current_theme_id() -> str:
    return _current_theme_id


def list_theme_options() -> list[tuple[str, str, str]]:
    """(id, label, swatch_hex)"""
    return [(tid, THEME_PRESETS[tid]["label"], THEME_PRESETS[tid]["swatch"]) for tid in PRESET_ORDER]


def apply_theme(theme_id: str) -> dict[str, str]:
    """프리셋 적용 후 리스너 호출."""
    global _current_theme_id
    if theme_id not in THEME_PRESETS:
        theme_id = DEFAULT_THEME_ID
    _current_theme_id = theme_id
    COLORS.clear()
    COLORS.update(deepcopy(THEME_PRESETS[theme_id]["colors"]))
    _merge_shell_color_defaults()
    try:
        from ui.workflow_theme import sync_workflow_theme

        sync_workflow_theme()
    except Exception:
        pass
    for fn in list(_theme_listeners):
        try:
            fn(theme_id)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("theme listener failed")
    return COLORS


def _merge_shell_color_defaults() -> None:
    """프리셋에 없는 셸·내비·홈 히어로 보조 색상."""
    accent = COLORS.get("accent", "#1F3864")
    defaults = {
        "header_bg": COLORS.get("card", "#FFFFFF"),
        "header_border": COLORS.get("border", "#E2E8F0"),
        "sidebar_brand_bg": COLORS.get("card", "#FFFFFF"),
        "sidebar_surface": COLORS.get("card", "#FFFFFF"),
        "nav_icon": COLORS.get("muted", "#64748B"),
        "nav_badge_bg": COLORS.get("accent_light", "#E0F4FD"),
        "nav_badge_fg": COLORS.get("accent", accent),
        "nav_scroll_trough": COLORS.get("sidebar", COLORS.get("bg", "#F1F5F9")),
        # 플랫폼 홈 히어로 배너 — 테마 accent 계열과 연동
        "hero_bg": COLORS.get("nav_active_bg", accent),
        "hero_bg_bottom": COLORS.get("accent_hover", accent),
        "hero_fg": "#FFFFFF",
        "hero_muted": COLORS.get("accent_light", "#A8C8E0"),
        "hero_accent": COLORS.get("nav_accent", accent),
        "hero_accent_soft": COLORS.get("nav_accent", accent),
        "card_shadow": COLORS.get("border", "#E2E8F0"),
        "chip_bg": COLORS.get("accent_light", COLORS.get("bg", "#F1F5F9")),
    }
    for key, value in defaults.items():
        COLORS.setdefault(key, value)


_merge_shell_color_defaults()


def add_theme_listener(callback: Callable[[str], None]) -> None:
    if callback not in _theme_listeners:
        _theme_listeners.append(callback)


def remove_theme_listener(callback: Callable[[str], None]) -> None:
    try:
        _theme_listeners.remove(callback)
    except ValueError:
        pass
