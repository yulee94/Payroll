"""
ui/theme_settings_panel.py - 설정 화면 테마 선택 (연한 색 클릭)
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from core.i18n import t
from ui.theme import COLORS, FONT, get_current_theme_id
from ui.theme_presets import PRESET_ORDER, THEME_PRESETS


class ThemeSettingsPanel(tk.Frame):
    """연한 색 스와치를 클릭해 개인 테마를 적용합니다."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_select: Callable[[str], None] | None = None,
        compact: bool = False,
        inline: bool = False,
        **kwargs,
    ) -> None:
        bg = COLORS["bg"] if inline else COLORS["card"]
        frame_kwargs: dict = {"bg": bg}
        if not compact and not inline:
            frame_kwargs["highlightbackground"] = COLORS["border"]
            frame_kwargs["highlightthickness"] = 1
        frame_kwargs.update(kwargs)
        super().__init__(parent, **frame_kwargs)
        self._on_select = on_select
        self._compact = compact
        self._inline = inline
        self._selected = tk.StringVar(value=get_current_theme_id())
        self._swatch_frames: dict[str, tk.Frame] = {}
        self._swatch_labels: dict[str, tk.Label] = {}

        pad_x = 0 if compact or inline else 14
        pad_y = 0 if compact or inline else 12
        self._inner = tk.Frame(self, bg=bg, padx=pad_x, pady=pad_y)
        self._inner.pack(fill=tk.X)
        inner = self._inner

        self._title_label: tk.Label | None = None
        self._hint_label: tk.Label | None = None
        self._status: tk.Label | None = None

        if not inline:
            self._title_label = tk.Label(
                inner,
                text="",
                bg=bg,
                fg=COLORS["text"],
                font=(FONT, 10, "bold"),
            )
            self._title_label.pack(anchor=tk.W)
            self._hint_label = tk.Label(
                inner,
                text="",
                bg=bg,
                fg=COLORS["muted"],
                font=(FONT, 9),
                wraplength=720,
                justify=tk.LEFT,
            )
            self._hint_label.pack(anchor=tk.W, pady=(4, 10))

        self._swatch_grid = tk.Frame(inner, bg=bg)
        grid = self._swatch_grid
        grid.pack(anchor=tk.W if not inline else tk.CENTER, side=tk.LEFT if inline else tk.TOP)

        sw_w, sw_h = (28, 18) if inline else (76, 52)
        accent_h = 3 if inline else 6
        cell_pad = 1 if inline else 4

        for col, theme_id in enumerate(PRESET_ORDER):
            meta = THEME_PRESETS[theme_id]
            cell = tk.Frame(grid, bg=bg, padx=cell_pad, pady=cell_pad)
            cell.grid(row=0, column=col, padx=1 if inline else 2)

            swatch_bg = meta["swatch"]
            accent = meta["colors"]["accent"]
            box = tk.Frame(
                cell,
                bg=swatch_bg,
                highlightbackground=COLORS["border"],
                highlightthickness=1 if inline else 2,
                cursor="hand2",
                width=sw_w,
                height=sw_h,
            )
            box.pack()
            box.pack_propagate(False)
            accent_bar = tk.Frame(box, bg=accent, height=accent_h)
            accent_bar.pack(side=tk.BOTTOM, fill=tk.X)

            name_lbl: tk.Label | None = None
            if not inline:
                name_lbl = tk.Label(
                    cell,
                    text=meta["label"],
                    bg=bg,
                    fg=COLORS["text"],
                    font=(FONT, 8),
                    cursor="hand2",
                )
                name_lbl.pack(pady=(4, 0))
                self._swatch_labels[theme_id] = name_lbl

            self._swatch_frames[theme_id] = box

            def _click(_e=None, tid: str = theme_id) -> None:
                self._pick(tid)

            bind_targets = [box, accent_bar, cell]
            if name_lbl is not None:
                bind_targets.append(name_lbl)
            for w in bind_targets:
                w.bind("<Button-1>", _click)

        if not inline:
            self._status = tk.Label(
                inner,
                text="",
                bg=bg,
                fg=COLORS["accent"],
                font=(FONT, 9),
            )
            self._status.pack(anchor=tk.W, pady=(10, 0))
        self.refresh_i18n()
        self._refresh_selection()

    def _pick(self, theme_id: str) -> None:
        self._selected.set(theme_id)
        self._refresh_selection()
        if self._on_select:
            self._on_select(theme_id)
        meta = THEME_PRESETS.get(theme_id, {})
        label = meta.get("label", theme_id)
        if self._status is not None:
            self._status.configure(
                text=t(
                    "settings.appearance.applied_theme",
                    default="테마 적용됨: {label}",
                    label=label,
                )
            )

    def set_selection(self, theme_id: str) -> None:
        self._selected.set(theme_id)
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        current = self._selected.get()
        active_w = 2 if self._inline else 3
        idle_w = 1 if self._inline else 2
        for tid, box in self._swatch_frames.items():
            if tid == current:
                box.configure(highlightbackground=COLORS["accent"], highlightthickness=active_w)
            else:
                box.configure(highlightbackground=COLORS["border"], highlightthickness=idle_w)

    def refresh_i18n(self) -> None:
        if self._title_label is not None:
            self._title_label.configure(
                text=t("settings.appearance.theme_title", default="화면 테마"),
            )
        if self._hint_label is not None:
            self._hint_label.configure(
                text=t(
                    "settings.appearance.theme_hint",
                    default="색상을 클릭하면 플랫폼 홈 배너·사이드바·버튼·표 헤더 색이 바로 바뀝니다.",
                ),
            )

    def refresh_card_style(self) -> None:
        """테마 변경 후 패널 자체 배경 갱신."""
        bg = COLORS["bg"] if self._inline else COLORS["card"]
        if not self._compact and not self._inline:
            self.configure(
                bg=bg,
                highlightbackground=COLORS["border"],
            )
        else:
            self.configure(bg=bg)
        if hasattr(self, "_inner"):
            self._inner.configure(bg=bg)
        if self._title_label is not None:
            self._title_label.configure(bg=bg, fg=COLORS["text"])
        if self._hint_label is not None:
            self._hint_label.configure(bg=bg, fg=COLORS["muted"])
        if hasattr(self, "_swatch_grid"):
            for cell in self._swatch_grid.winfo_children():
                cell.configure(bg=bg)
                for w in cell.winfo_children():
                    if isinstance(w, tk.Label):
                        w.configure(bg=bg, fg=COLORS["text"])
        if self._status is not None:
            self._status.configure(bg=bg, fg=COLORS["accent"])
        self._refresh_selection()
