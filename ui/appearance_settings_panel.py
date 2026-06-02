"""
ui/appearance_settings_panel.py - 테마·언어 개인 설정 (플랫폼 홈)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.i18n import (
    SUPPORTED_LOCALES,
    get_locale,
    locale_display_name,
    set_locale,
    set_saved_locale,
    t,
)
from ui.theme import COLORS, FONT, get_current_theme_id
from ui.theme_settings_panel import ThemeSettingsPanel


class AppearanceSettingsPanel(tk.Frame):
    """화면 테마와 UI 언어를 한 카드에서 설정합니다."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_theme_select: Callable[[str], None] | None = None,
        inline: bool = False,
        **kwargs,
    ) -> None:
        bg = COLORS["bg"] if inline else COLORS["card"]
        frame_kwargs: dict = {"bg": bg}
        if not inline:
            frame_kwargs["highlightbackground"] = COLORS["border"]
            frame_kwargs["highlightthickness"] = 1
        frame_kwargs.update(kwargs)
        super().__init__(parent, **frame_kwargs)
        self._on_theme_select = on_theme_select
        self._inline = inline
        self._locale_codes = list(SUPPORTED_LOCALES.keys())
        self._build()
        self.refresh_i18n()

    def _build(self) -> None:
        if self._inline:
            self._build_inline()
            return
        self._build_card()

    def _build_inline(self) -> None:
        bg = COLORS["bg"]
        row = tk.Frame(self, bg=bg)
        row.pack(fill=tk.X, padx=4, pady=1)
        self._inner = row

        self._title_label = None
        self._subtitle_label = None
        self._lang_hint = None
        self._lang_status = None

        self._theme_label = tk.Label(
            row,
            text="",
            bg=bg,
            fg=COLORS["muted"],
            font=(FONT, 8),
        )
        self._theme_label.pack(side=tk.LEFT, padx=(0, 3))

        self._theme_panel = ThemeSettingsPanel(
            row,
            on_select=self._on_theme_select,
            inline=True,
        )
        self._theme_panel.pack(side=tk.LEFT)
        self._theme_panel.set_selection(get_current_theme_id())

        tk.Frame(row, bg=COLORS["border"], width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=1
        )

        self._lang_title = tk.Label(
            row,
            text="",
            bg=bg,
            fg=COLORS["muted"],
            font=(FONT, 8),
        )
        self._lang_title.pack(side=tk.LEFT, padx=(0, 3))

        labels = [locale_display_name(code) for code in self._locale_codes]
        self._locale_combo = ttk.Combobox(
            row,
            values=labels,
            state="readonly",
            width=10,
            font=(FONT, 8),
        )
        self._locale_combo.pack(side=tk.LEFT)
        self._locale_combo.bind("<<ComboboxSelected>>", self._on_lang_changed)
        self._sync_locale_combo()

    def _build_card(self) -> None:
        inner = tk.Frame(self, bg=COLORS["card"], padx=16, pady=14)
        inner.pack(fill=tk.X)
        self._inner = inner

        self._title_label = tk.Label(
            inner,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
        )
        self._title_label.pack(anchor=tk.W)

        self._subtitle_label = tk.Label(
            inner,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=760,
            justify=tk.LEFT,
        )
        self._subtitle_label.pack(anchor=tk.W, pady=(4, 12))

        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 12))

        self._theme_panel = ThemeSettingsPanel(
            inner,
            on_select=self._on_theme_select,
            compact=True,
        )
        self._theme_panel.pack(fill=tk.X)
        self._theme_panel.set_selection(get_current_theme_id())

        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=12)

        lang_row = tk.Frame(inner, bg=COLORS["card"])
        lang_row.pack(fill=tk.X)
        lang_row.grid_columnconfigure(1, weight=1)

        self._lang_title = tk.Label(
            lang_row,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        )
        self._lang_title.grid(row=0, column=0, sticky="w")

        combo_frame = tk.Frame(lang_row, bg=COLORS["card"])
        combo_frame.grid(row=0, column=1, sticky="e")

        labels = [locale_display_name(code) for code in self._locale_codes]
        self._locale_combo = ttk.Combobox(
            combo_frame,
            values=labels,
            state="readonly",
            width=22,
            font=(FONT, 10),
        )
        self._locale_combo.pack(side=tk.LEFT)
        self._locale_combo.bind("<<ComboboxSelected>>", self._on_lang_changed)

        self._lang_hint = tk.Label(
            lang_row,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=760,
            justify=tk.LEFT,
        )
        self._lang_hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._lang_status = tk.Label(
            lang_row,
            text="",
            bg=COLORS["card"],
            fg=COLORS["accent"],
            font=(FONT, 9),
        )
        self._lang_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._sync_locale_combo()

    def _sync_locale_combo(self) -> None:
        current = get_locale()
        try:
            self._locale_combo.current(self._locale_codes.index(current))
        except ValueError:
            self._locale_combo.current(0)

    def _on_lang_changed(self, _event: tk.Event | None = None) -> None:
        idx = self._locale_combo.current()
        if idx < 0 or idx >= len(self._locale_codes):
            return
        code = self._locale_codes[idx]
        if code == get_locale():
            return
        set_saved_locale(code)
        set_locale(code)
        if not self._inline and self._lang_status is not None:
            name = locale_display_name(code)
            self._lang_status.configure(
                text=t(
                    "settings.appearance.applied_language",
                    default="언어가 {name}(으)로 변경되었습니다.",
                    name=name,
                )
            )

    def set_theme_selection(self, theme_id: str) -> None:
        self._theme_panel.set_selection(theme_id)

    def refresh_card_style(self) -> None:
        bg = COLORS["bg"] if self._inline else COLORS["card"]
        if self._inline:
            self.configure(bg=bg)
            self._inner.configure(bg=bg)
            self._theme_label.configure(bg=bg, fg=COLORS["muted"])
            self._lang_title.configure(bg=bg, fg=COLORS["muted"])
        else:
            self.configure(bg=bg, highlightbackground=COLORS["border"])
            for widget in (self._inner, self._title_label, self._subtitle_label):
                widget.configure(bg=bg)
            self._title_label.configure(fg=COLORS["text"])
            self._subtitle_label.configure(fg=COLORS["muted"])
            for widget in self._inner.winfo_children():
                if isinstance(widget, tk.Frame) and widget is not self._theme_panel:
                    widget.configure(bg=bg)
            self._lang_title.configure(bg=bg, fg=COLORS["text"])
            self._lang_hint.configure(bg=bg, fg=COLORS["muted"])
            self._lang_status.configure(bg=bg, fg=COLORS["accent"])
        self._theme_panel.refresh_card_style()

    def refresh_i18n(self) -> None:
        if self._inline:
            self._theme_label.configure(
                text=t("settings.appearance.theme_title", default="테마"),
            )
            self._lang_title.configure(
                text=t("i18n.language", default="언어"),
            )
        else:
            self._title_label.configure(
                text=t("settings.appearance.title", default="화면 설정"),
            )
            self._subtitle_label.configure(
                text=t(
                    "settings.appearance.subtitle",
                    default="테마와 언어는 로그인 계정별로 저장되며, 홈 배너·사이드바·메뉴에 즉시 반영됩니다.",
                ),
            )
            self._lang_title.configure(
                text=t("i18n.language", default="언어"),
            )
            self._lang_hint.configure(
                text=t(
                    "i18n.restart_hint",
                    default="일부 화면은 페이지 이동 또는 재실행 후 완전히 적용됩니다.",
                ),
            )
        self._theme_panel.refresh_i18n()
        self._sync_locale_combo()
