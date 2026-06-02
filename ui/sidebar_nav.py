"""
ui/sidebar_nav.py - 접이식 사이드바 내비게이션 (섹션 강조·활성 표시)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from tkinter import messagebox
import tkinter as tk

from ui.nav_icons import nav_item_icon, section_accent, section_icon
from ui.theme import COLORS, FONT, FONT_NAV


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = str(hex_color or "#64748B").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return 100, 116, 139


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def _blend_hex(base: str, overlay: str, alpha: float) -> str:
    br, bg, bb = _hex_to_rgb(base)
    or_, og, ob = _hex_to_rgb(overlay)
    a = max(0.0, min(1.0, alpha))
    return _rgb_to_hex(
        int(br + (or_ - br) * a),
        int(bg + (og - bg) * a),
        int(bb + (ob - bb) * a),
    )


def _surface() -> str:
    return COLORS.get("sidebar_surface", COLORS.get("card", "#FFFFFF"))


def create_scrollable_nav_area(
    parent: tk.Misc,
    *,
    width: int | None = None,
) -> tuple[tk.Frame, tk.Canvas]:
    """사이드바용 세로 스크롤 영역. Returns (inner_frame_for_nav_items, canvas)."""
    sb = COLORS["sidebar"]
    outer = tk.Frame(parent, bg=sb)
    canvas = tk.Canvas(outer, bg=sb, highlightthickness=0, bd=0, width=width)
    scrollbar = tk.Scrollbar(
        outer,
        orient=tk.VERTICAL,
        command=canvas.yview,
        width=6,
        bg=sb,
        troughcolor=COLORS.get("nav_scroll_trough", sb),
        activebackground=COLORS.get("nav_accent", COLORS["muted"]),
    )
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4))
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

    inner = tk.Frame(canvas, bg=sb)
    win_id = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

    def _on_inner_configure(_event: tk.Event) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=event.width)

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _wheel(event: tk.Event) -> str:
        from ui.wheel_scroll import wheel_delta

        delta = wheel_delta(event)
        if delta:
            canvas.yview_scroll(delta, "units")
            return "break"
        return ""

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        canvas.bind(seq, _wheel, add="+")
        inner.bind(seq, _wheel, add="+")
        outer.bind(seq, _wheel, add="+")

    outer._nav_canvas = canvas  # type: ignore[attr-defined]
    outer.pack(fill=tk.BOTH, expand=True, padx=(0, 4), pady=(0, 4))
    return inner, canvas


@dataclass
class NavItemDef:
    key: str
    label: str
    command: Callable[[], None] | None = None
    enabled: bool = True
    icon: str = ""


@dataclass
class NavSectionDef:
    section_id: str
    title: str
    items: tuple[NavItemDef, ...] = field(default_factory=tuple)
    default_expanded: bool = False
    status_label: str = ""
    icon: str = ""
    accent: str = ""


class NavItemRow:
    """좌측 활성 막대 + 아이콘 + 라벨 내비 행."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        key: str,
        label: str,
        icon: str,
        command: Callable[[], None],
        is_preview: bool,
        section_accent: str = "",
    ) -> None:
        self.key = key
        self._command = command
        self._is_preview = is_preview
        self._enabled = True
        self._active = False
        self._section_accent = section_accent or COLORS.get("nav_accent", COLORS["accent"])

        try:
            panel_bg = str(parent.cget("bg"))
        except tk.TclError:
            panel_bg = _surface()

        self._wrap = tk.Frame(parent, bg=panel_bg, cursor="hand2")
        self._wrap.pack(fill=tk.X, pady=2, padx=4)

        self._indicator = tk.Frame(self._wrap, width=3, bg=panel_bg)
        self._indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(2, 0))

        self._inner = tk.Frame(self._wrap, bg=panel_bg)
        self._inner.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))

        icon_fg = COLORS["muted"] if is_preview else self._section_accent
        self._icon_lbl = tk.Label(
            self._inner,
            text=icon,
            bg=panel_bg,
            fg=icon_fg,
            font=(FONT, 11),
            width=2,
            anchor=tk.W,
        )
        self._icon_lbl.pack(side=tk.LEFT, padx=(6, 6))

        text_fg = COLORS["muted"] if is_preview else COLORS["text"]
        self._text_lbl = tk.Label(
            self._inner,
            text=label,
            bg=panel_bg,
            fg=text_fg,
            font=FONT_NAV,
            anchor=tk.W,
        )
        self._text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=8, padx=(0, 6))

        for widget in (self._wrap, self._inner, self._icon_lbl, self._text_lbl):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        self._apply_visual()

    def _panel_bg(self) -> str:
        try:
            return str(self._wrap.master.cget("bg"))
        except (tk.TclError, AttributeError):
            return _surface()

    def refresh_section_style(self) -> None:
        self._apply_visual()

    def _on_click(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._command()

    def _on_enter(self, _event: tk.Event) -> None:
        if not self._enabled or self._active:
            return
        bg = _blend_hex(self._panel_bg(), self._section_accent, 0.09)
        self._set_bg(bg)
        self._indicator.configure(bg=bg)

    def _on_leave(self, _event: tk.Event) -> None:
        self._apply_visual()

    def _set_bg(self, bg: str) -> None:
        for w in (self._wrap, self._inner, self._icon_lbl, self._text_lbl):
            w.configure(bg=bg)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_visual()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        cursor = "hand2" if enabled else "arrow"
        self._wrap.configure(cursor=cursor)
        self._apply_visual()

    def _apply_visual(self) -> None:
        base_bg = self._panel_bg()
        if self._active:
            bg = _blend_hex(base_bg, self._section_accent, 0.16)
            fg = self._section_accent
            self._indicator.configure(bg=self._section_accent)
            self._set_bg(bg)
            self._icon_lbl.configure(fg=fg)
            self._text_lbl.configure(fg=fg, font=(FONT, 11, "bold"))
            return

        self._indicator.configure(bg=base_bg)
        self._set_bg(base_bg)
        if not self._enabled:
            fg = COLORS["muted"]
            icon_fg = COLORS["muted"]
            font = FONT_NAV
        elif self._is_preview:
            fg = COLORS["muted"]
            icon_fg = COLORS["muted"]
            font = FONT_NAV
        else:
            fg = COLORS["text"]
            icon_fg = self._section_accent
            font = FONT_NAV
        self._icon_lbl.configure(fg=icon_fg)
        self._text_lbl.configure(fg=fg, font=font)

    def configure(self, **kwargs: object) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.set_enabled(str(state) != str(tk.DISABLED))
        fg = kwargs.get("fg")
        if fg is not None and not self._active:
            self._text_lbl.configure(fg=str(fg))
        cursor = kwargs.get("cursor")
        if cursor is not None:
            self._wrap.configure(cursor=str(cursor))


class CollapsibleNavSection:
    """섹션 헤더(강조색·아이콘·배지) + 접이식 하위 메뉴."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        section_id: str,
        title: str,
        status_label: str = "",
        icon: str = "",
        accent: str = "",
        default_expanded: bool = False,
        on_toggle: Callable[[str, bool], None] | None = None,
    ) -> None:
        self.section_id = section_id
        self.title = title
        self.status_label = status_label.strip()
        self._icon = icon or section_icon(section_id)
        self._accent = accent or section_accent(section_id)
        self._expanded = default_expanded
        self._on_toggle = on_toggle
        self._header_widgets: list[tk.Misc] = []
        self._item_rows: list[NavItemRow] = []

        surface = _surface()
        border_idle = COLORS.get("border", "#E2E8F0")

        self._wrap = tk.Frame(
            parent,
            bg=surface,
            highlightthickness=1,
            highlightbackground=border_idle,
        )
        self._wrap.pack(fill=tk.X, padx=10, pady=(5, 0))

        self._header = tk.Frame(self._wrap, bg=surface, cursor="hand2")
        self._header.pack(fill=tk.X)

        self._accent_bar = tk.Frame(self._header, width=4, bg=self._accent)
        self._accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        header_body = tk.Frame(self._header, bg=surface)
        header_body.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._header_body = header_body

        top_row = tk.Frame(header_body, bg=surface)
        top_row.pack(fill=tk.X, padx=(10, 10), pady=(10, 8))
        self._top_row = top_row

        chip_bg = _blend_hex(surface, self._accent, 0.14)
        self._icon_chip = tk.Frame(top_row, bg=chip_bg)
        self._icon_chip.pack(side=tk.LEFT, padx=(0, 10))
        self._icon_lbl = tk.Label(
            self._icon_chip,
            text=self._icon,
            bg=chip_bg,
            fg=self._accent,
            font=(FONT, 11),
            padx=7,
            pady=5,
        )
        self._icon_lbl.pack()

        self._title_lbl = tk.Label(
            top_row,
            text=title,
            bg=surface,
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        )
        self._title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if self.status_label:
            badge_bg = _blend_hex(surface, self._accent, 0.16)
            self._badge = tk.Label(
                top_row,
                text=self.status_label,
                bg=badge_bg,
                fg=self._accent,
                font=(FONT, 7, "bold"),
                padx=7,
                pady=2,
            )
            self._badge.pack(side=tk.RIGHT, padx=(6, 6))
        else:
            self._badge = None

        self._chevron = tk.Label(
            top_row,
            text="▾" if self._expanded else "▸",
            bg=surface,
            fg=self._accent,
            font=(FONT, 12),
            width=2,
            anchor=tk.E,
        )
        self._chevron.pack(side=tk.RIGHT, padx=(0, 0))

        self._divider = tk.Frame(header_body, bg=border_idle, height=1)
        self._divider.pack(fill=tk.X, padx=(10, 10))

        self._header_widgets = [
            self._header,
            header_body,
            top_row,
            self._accent_bar,
            self._icon_chip,
            self._icon_lbl,
            self._title_lbl,
            self._chevron,
            self._divider,
        ]
        if self._badge is not None:
            self._header_widgets.append(self._badge)

        for widget in self._header_widgets:
            widget.bind("<Button-1>", lambda _e: self.toggle())
            widget.bind("<Enter>", self._on_header_enter)
            widget.bind("<Leave>", self._on_header_leave)

        self._body = tk.Frame(self._wrap, bg=surface)
        self._body_accent = tk.Frame(self._body, width=3, bg=self._accent)
        self._body_accent.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0), pady=(0, 10))
        self._items_frame = tk.Frame(self._body, bg=surface, highlightthickness=0)
        self._items_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8), pady=(2, 10))

        self._apply_visibility()
        self._apply_section_style()

    def _header_bg(self, *, hover: bool = False) -> str:
        surface = _surface()
        if self._expanded:
            return _blend_hex(surface, self._accent, 0.20 if hover else 0.11)
        return _blend_hex(surface, self._accent, 0.08 if hover else 0.0) or surface

    def _chip_bg(self, header_bg: str) -> str:
        return _blend_hex(header_bg, self._accent, 0.22)

    def _apply_section_style(self) -> None:
        surface = _surface()
        header_bg = self._header_bg()
        chip_bg = self._chip_bg(header_bg)
        wrap_border = self._accent if self._expanded else COLORS.get("border", "#E2E8F0")

        self._wrap.configure(bg=header_bg if self._expanded else surface, highlightbackground=wrap_border)
        self._header.configure(bg=header_bg)
        self._header_body.configure(bg=header_bg)
        self._top_row.configure(bg=header_bg)
        self._accent_bar.configure(bg=self._accent, width=5 if self._expanded else 4)
        self._icon_chip.configure(bg=chip_bg)
        self._icon_lbl.configure(bg=chip_bg, fg=self._accent)
        self._title_lbl.configure(
            bg=header_bg,
            fg=self._accent if self._expanded else COLORS["text"],
            font=(FONT, 10, "bold"),
        )
        self._chevron.configure(
            bg=header_bg,
            fg=self._accent,
            text="▾" if self._expanded else "▸",
        )
        self._divider.configure(
            bg=_blend_hex(COLORS["border"], self._accent, 0.45) if self._expanded else COLORS["border"]
        )
        if self._badge is not None:
            self._badge.configure(
                bg=_blend_hex(header_bg, self._accent, 0.24),
                fg=self._accent,
            )

        body_bg = surface
        self._body.configure(bg=body_bg)
        self._body_accent.configure(bg=self._accent if self._expanded else body_bg)
        self._items_frame.configure(bg=body_bg)
        for row in self._item_rows:
            row.refresh_section_style()

    def _set_header_bg(self, bg: str) -> None:
        chip_bg = self._chip_bg(bg)
        self._header.configure(bg=bg)
        self._header_body.configure(bg=bg)
        self._top_row.configure(bg=bg)
        self._icon_chip.configure(bg=chip_bg)
        self._icon_lbl.configure(bg=chip_bg)
        self._title_lbl.configure(bg=bg)
        self._chevron.configure(bg=bg)
        if self._badge is not None:
            self._badge.configure(bg=_blend_hex(bg, self._accent, 0.24))

    def register_item_row(self, row: NavItemRow) -> None:
        self._item_rows.append(row)

    def _on_header_enter(self, _event: tk.Event) -> None:
        self._set_header_bg(self._header_bg(hover=True))

    def _on_header_leave(self, _event: tk.Event) -> None:
        self._apply_section_style()

    def _apply_visibility(self) -> None:
        if self._expanded:
            self._body.pack(fill=tk.X)
        else:
            self._body.pack_forget()
        self._apply_section_style()

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._apply_visibility()
        if self._on_toggle:
            self._on_toggle(self.section_id, self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._apply_visibility()

    @property
    def expanded(self) -> bool:
        return self._expanded

    @property
    def items_parent(self) -> tk.Frame:
        return self._items_frame


class SidebarNavigator:
    """플랫폼·사업부별 접이식 사이드바."""

    def __init__(self, parent: tk.Misc) -> None:
        self._parent = parent
        self.nav_buttons: dict[str, NavItemRow] = {}
        self._sections: dict[str, CollapsibleNavSection] = {}
        self._active_key: str | None = None
        self._coming_soon_keys: set[str] = set()

    @property
    def coming_soon_keys(self) -> frozenset[str]:
        return frozenset(self._coming_soon_keys)

    @property
    def sections(self) -> dict[str, CollapsibleNavSection]:
        return dict(self._sections)

    def build_sections(self, sections: tuple[NavSectionDef, ...]) -> None:
        for spec in sections:
            self._add_section(spec)

    def _add_section(self, spec: NavSectionDef) -> None:
        section = CollapsibleNavSection(
            self._parent,
            section_id=spec.section_id,
            title=spec.title,
            status_label=spec.status_label,
            icon=spec.icon,
            accent=spec.accent,
            default_expanded=spec.default_expanded,
        )
        self._sections[spec.section_id] = section

        for item in spec.items:
            self._add_item(section, item)

    def _add_item(self, section: CollapsibleNavSection, item: NavItemDef) -> None:
        parent = section.items_parent

        def _invoke() -> None:
            if item.command is None:
                messagebox.showinfo(
                    "준비 중",
                    f"「{item.label}」 기능은 현재 준비 중입니다.\n오픈 후 이용하실 수 있습니다.",
                    parent=self._parent.winfo_toplevel(),
                )
                return
            item.command()

        is_preview = item.command is None
        icon = item.icon or nav_item_icon(item.key)
        row = NavItemRow(
            parent,
            key=item.key,
            label=item.label,
            icon=icon,
            command=_invoke,
            is_preview=is_preview,
            section_accent=section._accent,
        )
        section.register_item_row(row)
        if is_preview:
            self._coming_soon_keys.add(item.key)
        if not item.enabled:
            row.set_enabled(False)

        self.nav_buttons[item.key] = row

    def set_active(self, key: str | None) -> None:
        self._active_key = key
        for nav_key, row in self.nav_buttons.items():
            row.set_active(nav_key == key)

    def set_item_state(self, key: str, *, enabled: bool) -> None:
        row = self.nav_buttons.get(key)
        if not row:
            return
        row.set_enabled(enabled)
        if enabled:
            self._coming_soon_keys.discard(key)
        if self._active_key == key:
            self.set_active(key)

    def expand_for_page(self, page_key: str, section_map: dict[str, str]) -> None:
        section_id = section_map.get(page_key)
        if section_id:
            section = self._sections.get(section_id)
            if section:
                section.set_expanded(True)

    def expand_section(self, section_id: str) -> None:
        section = self._sections.get(section_id)
        if section:
            section.set_expanded(True)
