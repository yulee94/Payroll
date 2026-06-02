"""
ui/inline_login_panel.py - 팝업 없이 홈 화면에서 로그인
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.config import APP_CONFIG
from core.session_service import is_logged_in, login
from core.tenant_store import get_active_tenant
from core.user_store import authenticate_credentials
from ui.theme import COLORS, FONT, FONT_BODY

OnLoggedIn = Callable[[], None]


class InlineLoginPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, *, on_logged_in: OnLoggedIn | None = None, **kwargs) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_logged_in = on_logged_in
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._remember = tk.BooleanVar(value=True)
        self._status = tk.StringVar(value="")

        shell = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        shell.pack(fill=tk.X, padx=32, pady=(8, 0))

        head = tk.Frame(shell, bg=COLORS["card"])
        head.pack(fill=tk.X, padx=18, pady=14)
        tk.Label(
            head,
            text="로그인",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
        ).pack(side=tk.LEFT)
        if not APP_CONFIG.require_login or is_logged_in():
            tenant = get_active_tenant()
            tk.Label(
                head,
                text=f"고객사: {tenant.display_name}",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(side=tk.LEFT, padx=(10, 0))

        body = tk.Frame(shell, bg=COLORS["card"])
        body.pack(fill=tk.X, padx=18, pady=(0, 16))

        grid = tk.Frame(body, bg=COLORS["card"])
        grid.pack(fill=tk.X)
        grid.grid_columnconfigure(1, weight=1)

        tk.Label(grid, text="아이디", bg=COLORS["card"], font=FONT_BODY, width=10, anchor=tk.W).grid(
            row=0, column=0, sticky="w", pady=4
        )
        user_ent = tk.Entry(grid, textvariable=self._username, font=FONT_BODY, width=28)
        user_ent.grid(row=0, column=1, sticky="ew", pady=4)

        tk.Label(grid, text="비밀번호", bg=COLORS["card"], font=FONT_BODY, width=10, anchor=tk.W).grid(
            row=1, column=0, sticky="w", pady=4
        )
        pass_ent = tk.Entry(grid, textvariable=self._password, show="•", font=FONT_BODY, width=28)
        pass_ent.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(body, text="다음 실행 시 자동 로그인", variable=self._remember).pack(
            anchor=tk.W, pady=(10, 0)
        )

        if not APP_CONFIG.allow_self_register:
            tk.Label(
                body,
                text="계정이 없으면 관리자에게 발급을 요청하세요.",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(anchor=tk.W, pady=(6, 0))

        tk.Label(body, textvariable=self._status, bg=COLORS["card"], fg="#B91C1C", font=(FONT, 9)).pack(
            anchor=tk.W, pady=(10, 0)
        )

        btn_row = tk.Frame(body, bg=COLORS["card"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        tk.Button(
            btn_row,
            text="로그인",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._do_login,
        ).pack(side=tk.LEFT)

        for w in (self, shell, head, body, grid, user_ent, pass_ent):
            w.bind("<Return>", lambda _e: self._do_login(), add="+")

        user_ent.focus_set()

    def _do_login(self) -> None:
        self._status.set("")
        tenant = get_active_tenant()
        try:
            rec = authenticate_credentials(
                self._username.get(),
                self._password.get(),
                preferred_tenant_id=tenant.tenant_id,
            )
            login(rec, remember=self._remember.get())
            if self._on_logged_in:
                self._on_logged_in()
        except Exception as exc:
            self._status.set(str(exc))

