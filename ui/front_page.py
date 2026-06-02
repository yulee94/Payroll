"""
ui/front_page.py - Bitween 앱 시작 화면(랜딩)
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from core.brand_display import launcher_tagline, product_name_line
from core.i18n import t
from ui.brand_assets import attach_bitween_logo_label
from ui.theme import COLORS, FONT, FONT_BODY

OnAction = Callable[[], None]


class FrontPagePanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_login: OnAction,
        on_continue: OnAction | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_login = on_login
        self._on_continue = on_continue
        self._photo_refs: list[tk.PhotoImage] = []

        wrap = tk.Frame(self, bg=COLORS["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        card_shadow = tk.Frame(wrap, bg=COLORS["card_shadow"])
        card_shadow.grid(row=0, column=0, sticky="nsew", padx=36, pady=36)
        card_shadow.grid_columnconfigure(0, weight=1)
        card_shadow.grid_rowconfigure(0, weight=1)

        card = tk.Frame(
            card_shadow,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 3))
        card.grid_columnconfigure(0, weight=1)

        top = tk.Frame(card, bg=COLORS["hero_bg"], height=6)
        top.grid(row=0, column=0, sticky="ew")

        body = tk.Frame(card, bg=COLORS["card"])
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=26)
        body.grid_columnconfigure(0, weight=1)

        head = tk.Frame(body, bg=COLORS["card"])
        head.grid(row=0, column=0, sticky="ew")
        head.grid_columnconfigure(0, weight=1)

        left = tk.Frame(head, bg=COLORS["card"])
        left.grid(row=0, column=0, sticky="w")

        tk.Label(
            left,
            text=product_name_line(),
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 28, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            left,
            text=launcher_tagline(),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(6, 0))

        right = tk.Frame(head, bg=COLORS["card"])
        right.grid(row=0, column=1, sticky="e")
        attach_bitween_logo_label(
            right,
            self._photo_refs,
            self.winfo_toplevel(),
            max_width=140,
            variant="light",
            bg=COLORS["card"],
            blend_bg=COLORS["card"],
            anchor=tk.E,
        )

        tk.Label(
            body,
            text=t(
                "front.subtitle",
                default="업무 플랫폼(급여·인사·전자결재 등)을 사용하려면 로그인하세요.",
            ),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            justify=tk.LEFT,
            wraplength=720,
        ).grid(row=1, column=0, sticky="w", pady=(18, 0))

        btn_row = tk.Frame(body, bg=COLORS["card"])
        btn_row.grid(row=2, column=0, sticky="ew", pady=(22, 0))

        tk.Button(
            btn_row,
            text=t("front.login", default="로그인"),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 11, "bold"),
            padx=20,
            pady=10,
            cursor="hand2",
            command=self._on_login,
        ).pack(side=tk.LEFT)

        if self._on_continue is not None:
            tk.Button(
                btn_row,
                text=t("front.continue", default="바로 시작"),
                bg=COLORS["chip_bg"],
                fg=COLORS["nav_text"],
                relief=tk.FLAT,
                font=(FONT, 10, "bold"),
                padx=16,
                pady=10,
                cursor="hand2",
                command=self._on_continue,
            ).pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(
            body,
            text=t("front.hint", default="계정이 없으면 관리자에게 발급을 요청하세요."),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).grid(row=3, column=0, sticky="w", pady=(18, 0))

