"""
ui/brand_header.py - Bitween · 고객사(COSS 등) 사이드바 브랜드
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

from core.brand_display import (
    company_name_ko_line,
    company_name_line,
    product_name_line,
    sidebar_user_identity_line,
)
from core.config import APP_CONFIG
from ui.brand_assets import attach_logo_label
from ui.theme import COLORS, FONT, SIDEBAR_WIDTH

_brand = APP_CONFIG.brand
_NAVY = _brand.primary_navy


class SidebarBrandHeader(tk.Frame):
    """사이드바: Bitween → COSS 로고 → 회사명 · 로그인 사용자 (카드형)."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        host: tk.Misc | None = None,
        bg: str | None = None,
        **kwargs: Any,
    ) -> None:
        card_bg = COLORS.get("sidebar_brand_bg", COLORS.get("card", "#FFFFFF"))
        bg = bg or card_bg
        master = host if host is not None else parent
        super().__init__(
            parent,
            bg=card_bg,
            highlightthickness=1,
            highlightbackground=COLORS.get("sidebar_border", COLORS["border"]),
            **kwargs,
        )
        self._photo_refs: list[Any] = []
        self._card_bg = card_bg

        inner = tk.Frame(self, bg=card_bg, padx=14, pady=14)
        inner.pack(fill=tk.X)
        self._inner = inner

        tk.Label(
            inner,
            text=product_name_line(),
            bg=card_bg,
            fg=_NAVY,
            font=(FONT, 18, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)

        tk.Label(
            inner,
            text=_brand.product_tagline,
            bg=card_bg,
            fg=COLORS["muted"],
            font=(FONT, 8),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(2, 10))

        accent = COLORS.get("nav_accent", "#00A8E8")
        tk.Frame(inner, bg=accent, height=3).pack(fill=tk.X, pady=(0, 12))
        tk.Frame(inner, bg=COLORS.get("accent_light", "#E0F4FD"), height=1).pack(fill=tk.X, pady=(0, 12))

        logo_w = min(200, SIDEBAR_WIDTH - 48)
        attach_logo_label(
            inner,
            self._photo_refs,
            master,
            max_width=logo_w,
            variant="sidebar",
            bg=card_bg,
            anchor=tk.W,
            pady=(0, 6),
        )

        tk.Label(
            inner,
            text=company_name_line(),
            bg=card_bg,
            fg=_NAVY,
            font=(FONT, 11, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(4, 0))

        self._ko_lbl = tk.Label(
            inner,
            text="",
            bg=card_bg,
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
            wraplength=SIDEBAR_WIDTH - 48,
            justify=tk.LEFT,
        )
        self._user_lbl = tk.Label(
            inner,
            text="",
            bg=card_bg,
            fg=COLORS.get("nav_accent", _NAVY),
            font=(FONT, 9, "bold"),
            anchor=tk.W,
            wraplength=SIDEBAR_WIDTH - 48,
            justify=tk.LEFT,
        )
        self.refresh_user_context()

    def refresh_user_context(self) -> None:
        """로그인·조직 정보에 따라 (주)코스 ○○팀 홍길동 직위 표시."""
        card_bg = self._card_bg
        user_line = sidebar_user_identity_line()
        self._user_lbl.pack_forget()
        self._ko_lbl.pack_forget()

        if user_line:
            self._user_lbl.configure(text=user_line, bg=card_bg)
            self._user_lbl.pack(anchor=tk.W, pady=(6, 0))
            return

        ko = company_name_ko_line()
        if ko:
            self._ko_lbl.configure(text=ko, bg=card_bg)
            self._ko_lbl.pack(anchor=tk.W, pady=(2, 0))

    def keep_photos_on(self, host: Any) -> None:
        if not hasattr(host, "_brand_photo_refs"):
            host._brand_photo_refs = []
        host._brand_photo_refs.extend(self._photo_refs)


def build_sidebar_brand(parent: tk.Misc, host: Any) -> SidebarBrandHeader:
    tk_host = host if isinstance(host, tk.Misc) else parent
    frame = SidebarBrandHeader(parent, host=tk_host)
    frame.pack(fill=tk.X, anchor=tk.NW, padx=10, pady=(4, 0))
    frame.keep_photos_on(host)
    return frame
