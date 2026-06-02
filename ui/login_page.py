"""
ui/login_page.py - Bitween 플랫폼 로그인 화면 (테넌트 중립)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.brand_display import launcher_tagline, product_name_line
from core.config import APP_CONFIG
from core.version_display import app_version_label
from core.i18n import t
from core.session_service import login
from core.user_store import authenticate_credentials
from ui.brand_assets import attach_bitween_logo_label
from ui.theme import COLORS, FONT, FONT_BODY

OnAction = Callable[[], None]


class LoginPagePanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_success: OnAction,
        on_back: OnAction | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_success = on_success
        self._on_back = on_back
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._remember = tk.BooleanVar(value=True)
        self._status = tk.StringVar(value="")
        self._photo_refs: list[tk.PhotoImage] = []

        wrap = tk.Frame(self, bg=COLORS["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(
            wrap,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        shell.grid(row=0, column=0)
        shell.grid_columnconfigure(0, weight=1)

        hero = tk.Frame(shell, bg=COLORS["hero_bg"])
        hero.grid(row=0, column=0, sticky="ew")
        hero_inner = tk.Frame(hero, bg=COLORS["hero_bg"])
        hero_inner.pack(fill=tk.X, padx=32, pady=28)
        hero_inner.grid_columnconfigure(0, weight=1)

        brand_row = tk.Frame(hero_inner, bg=COLORS["hero_bg"])
        brand_row.pack(fill=tk.X)
        brand_row.grid_columnconfigure(0, weight=1)

        left = tk.Frame(brand_row, bg=COLORS["hero_bg"])
        left.grid(row=0, column=0, sticky="w")

        tk.Label(
            left,
            text=product_name_line(),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_fg"],
            font=(FONT, 26, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            left,
            text=launcher_tagline(),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_muted"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(4, 0))

        logo_host = tk.Frame(brand_row, bg=COLORS["hero_bg"])
        logo_host.grid(row=0, column=1, sticky="e", padx=(16, 0))
        attach_bitween_logo_label(
            logo_host,
            self._photo_refs,
            self.winfo_toplevel(),
            max_width=148,
            variant="dark",
            bg=COLORS["hero_bg"],
            blend_bg=COLORS["hero_bg"],
            anchor=tk.E,
        )

        tk.Frame(hero, bg=COLORS["hero_accent"], height=2).pack(fill=tk.X)

        body = tk.Frame(shell, bg=COLORS["card"])
        body.grid(row=1, column=0, sticky="nsew", padx=32, pady=(22, 26))
        body.grid_columnconfigure(1, weight=1)

        tk.Label(
            body,
            text=t("login.title", default="로그인"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(
            body,
            text=t(
                "login.subtitle",
                default="소속 법인 계정으로 로그인하면 해당 법인 플랫폼 홈으로 이동합니다.",
            ),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
            wraplength=380,
            justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        tk.Label(
            body,
            text=t("login.username", default="아이디"),
            bg=COLORS["card"],
            font=FONT_BODY,
            width=10,
            anchor=tk.W,
        ).grid(row=2, column=0, sticky="w", pady=6)
        user_ent = tk.Entry(body, textvariable=self._username, font=FONT_BODY, width=30)
        user_ent.grid(row=2, column=1, sticky="ew", pady=6)

        tk.Label(
            body,
            text=t("login.password", default="비밀번호"),
            bg=COLORS["card"],
            font=FONT_BODY,
            width=10,
            anchor=tk.W,
        ).grid(row=3, column=0, sticky="w", pady=6)
        pass_ent = tk.Entry(body, textvariable=self._password, show="•", font=FONT_BODY, width=30)
        pass_ent.grid(row=3, column=1, sticky="ew", pady=6)

        ttk.Checkbutton(
            body,
            text=t("login.remember", default="다음 실행 시 자동 로그인"),
            variable=self._remember,
        ).grid(row=4, column=1, sticky="w", pady=(10, 0))

        if not APP_CONFIG.allow_self_register:
            tk.Label(
                body,
                text=t("login.no_account", default="계정이 없으면 관리자에게 발급을 요청하세요."),
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                anchor=tk.W,
            ).grid(row=5, column=1, sticky="w", pady=(6, 0))

        tk.Label(
            body,
            textvariable=self._status,
            bg=COLORS["card"],
            fg="#B91C1C",
            font=(FONT, 9),
        ).grid(row=6, column=1, sticky="w", pady=(10, 0))

        btn_row = tk.Frame(body, bg=COLORS["card"])
        btn_row.grid(row=7, column=1, sticky="ew", pady=(16, 0))

        if self._on_back is not None:
            tk.Button(
                btn_row,
                text=t("common.back", default="뒤로"),
                bg=COLORS["chip_bg"],
                fg=COLORS["nav_text"],
                relief=tk.FLAT,
                font=(FONT, 10, "bold"),
                padx=14,
                pady=8,
                cursor="hand2",
                command=self._on_back,
            ).pack(side=tk.LEFT)

        tk.Button(
            btn_row,
            text=t("login.submit", default="로그인"),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._do_login,
        ).pack(side=tk.LEFT, padx=(10, 0))

        for w in (self, shell, hero, body, user_ent, pass_ent):
            w.bind("<Return>", lambda _e: self._do_login(), add="+")

        tk.Label(
            wrap,
            text=app_version_label(),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).grid(row=1, column=0, pady=(8, 12))

        user_ent.focus_set()

    def _do_login(self) -> None:
        self._status.set("")
        try:
            rec = authenticate_credentials(
                self._username.get(),
                self._password.get(),
                preferred_tenant_id=None,
            )
            login(rec, remember=self._remember.get())
            self._on_success()
        except Exception as exc:
            self._status.set(str(exc))
