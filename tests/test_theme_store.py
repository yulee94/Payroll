"""사용자별 테마 저장·적용."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from core.theme_store import (
    DEFAULT_THEME_ID,
    THEME_FILE,
    get_saved_theme_id,
    load_user_theme,
    set_saved_theme_id,
)
from ui.theme import COLORS, apply_theme, get_current_theme_id


@pytest.fixture
def theme_file(tmp_path, monkeypatch):
    path = tmp_path / "theme.json"
    monkeypatch.setattr("core.theme_store.THEME_FILE", path)
    return path


def test_default_theme_when_no_file(theme_file):
    assert get_saved_theme_id() == DEFAULT_THEME_ID


def test_per_user_persistence(theme_file):
    class S:
        user_id = "user-a"

    set_saved_theme_id("mint", session=S())
    assert get_saved_theme_id(session=S()) == "mint"
    data = json.loads(theme_file.read_text(encoding="utf-8"))
    assert data["users"]["user-a"] == "mint"


def test_load_user_theme_updates_colors(theme_file):
    set_saved_theme_id("sky")
    tid = load_user_theme()
    assert tid == "sky"
    assert get_current_theme_id() == "sky"
    assert COLORS["accent"] == apply_theme("sky")["accent"]
