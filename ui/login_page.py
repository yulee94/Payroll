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
        self._show_password = tk.BooleanVar(value=False)
        self._status = tk.StringVar(value="")
        self._photo_refs: list[tk.PhotoImage] = []
        self._password_entry: tk.Entry | None = None
        self._submit_btn: tk.Button | None = None

        wrap = tk.Frame(self, bg=COLORS["bg"])
        wrap.pack(fill=tk.BOTH, expand=True)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        shell_shadow = tk.Frame(wrap, bg=COLORS.get("card_shadow", COLORS["border"]))
        shell_shadow.grid(row=0, column=0, sticky="nsew", padx=34, pady=30)
        shell_shadow.grid_rowconfigure(0, weight=1)
        shell_shadow.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(
            shell_shadow,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        shell.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 3))
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=5, minsize=390)
        shell.grid_columnconfigure(1, weight=4, minsize=420)

        self._build_brand_panel(shell)
        self._build_form_panel(shell)

        tk.Label(
            wrap,
            text=app_version_label(),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).grid(row=1, column=0, pady=(0, 12))

        self.after_idle(lambda: self._username_entry.focus_set())

    def _build_brand_panel(self, parent: tk.Frame) -> None:
        hero = tk.Frame(parent, bg=COLORS["hero_bg"])
        hero.grid(row=0, column=0, sticky="nsew")
        hero.grid_rowconfigure(1, weight=1)
        hero.grid_columnconfigure(0, weight=1)

        brand_row = tk.Frame(hero, bg=COLORS["hero_bg"])
        brand_row.grid(row=0, column=0, sticky="ew", padx=32, pady=(30, 0))
        brand_row.grid_columnconfigure(0, weight=1)

        tk.Label(
            brand_row,
            text=product_name_line(),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_fg"],
            font=(FONT, 28, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="w")
        attach_bitween_logo_label(
            brand_row,
            self._photo_refs,
            self.winfo_toplevel(),
            max_width=132,
            variant="dark",
            bg=COLORS["hero_bg"],
            blend_bg=COLORS["hero_bg"],
            anchor=tk.E,
        )

        hero_body = tk.Frame(hero, bg=COLORS["hero_bg"])
        hero_body.grid(row=1, column=0, sticky="nsew", padx=32, pady=(42, 28))
        hero_body.grid_columnconfigure(0, weight=1)

        tk.Label(
            hero_body,
            text=launcher_tagline(),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_accent_soft"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            hero_body,
            text=t("login.hero.title", default="법인 업무를 한 화면에서 시작합니다."),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_fg"],
            font=(FONT, 23, "bold"),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=440,
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Label(
            hero_body,
            text=t(
                "login.hero.subtitle",
                default="권한에 맞는 플랫폼과 자료만 표시되도록 법인 계정으로 접속하세요.",
            ),
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_muted"],
            font=(FONT, 10),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=430,
        ).grid(row=2, column=0, sticky="w", pady=(12, 0))

        assurance = tk.Frame(hero_body, bg=COLORS["hero_bg"])
        assurance.grid(row=3, column=0, sticky="ew", pady=(34, 0))
        assurance.grid_columnconfigure(0, weight=1)
        self._build_assurance_item(assurance, 0, "01", t("login.assurance.tenant", default="법인별 권한 적용"))
        self._build_assurance_item(assurance, 1, "02", t("login.assurance.audit", default="업무 자료 접근 분리"))
        self._build_assurance_item(assurance, 2, "03", t("login.assurance.session", default="자동 로그인 선택 가능"))

        tk.Frame(hero, bg=COLORS["hero_accent"], height=5).grid(row=2, column=0, sticky="ew")

    def _build_assurance_item(self, parent: tk.Frame, row: int, number: str, text: str) -> None:
        item = tk.Frame(parent, bg=COLORS["hero_bg"])
        item.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 10, 0))
        badge = tk.Label(
            item,
            text=number,
            bg=COLORS["hero_accent"],
            fg=COLORS["hero_fg"],
            font=(FONT, 8, "bold"),
            width=4,
            pady=4,
        )
        badge.pack(side=tk.LEFT)
        tk.Label(
            item,
            text=text,
            bg=COLORS["hero_bg"],
            fg=COLORS["hero_fg"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_form_panel(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=COLORS["card"])
        body.grid(row=0, column=1, sticky="nsew", padx=34, pady=32)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(8, weight=1)

        tk.Label(
            body,
            text=t("login.title", default="로그인"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 18, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="w")
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
            wraplength=390,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 22))

        self._username_entry = self._field(body, 2, t("login.username", default="아이디"), self._username)
        self._password_entry = self._field(
            body,
            3,
            t("login.password", default="비밀번호"),
            self._password,
            show="" if self._show_password.get() else "•",
        )

        option_row = tk.Frame(body, bg=COLORS["card"])
        option_row.grid(row=4, column=0, sticky="ew", pady=(2, 0))
        ttk.Checkbutton(
            option_row,
            text=t("login.remember", default="다음 실행 시 자동 로그인"),
            variable=self._remember,
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            option_row,
            text=t("login.show_password", default="비밀번호 표시"),
            variable=self._show_password,
            command=self._toggle_password_visibility,
        ).pack(side=tk.RIGHT)

        self._status_wrap = tk.Frame(
            body,
            bg="#FEF2F2",
            highlightbackground="#FECACA",
            highlightthickness=1,
        )
        self._status_wrap.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        self._status_wrap.grid_columnconfigure(1, weight=1)
        tk.Label(
            self._status_wrap,
            text="!",
            bg="#FEE2E2",
            fg="#B91C1C",
            font=(FONT, 9, "bold"),
            width=3,
        ).grid(row=0, column=0, sticky="ns")
        tk.Label(
            self._status_wrap,
            textvariable=self._status,
            bg="#FEF2F2",
            fg="#B91C1C",
            font=(FONT, 9),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=340,
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=9)
        self._status_wrap.grid_remove()

        if not APP_CONFIG.allow_self_register:
            tk.Label(
                body,
                text=t("login.no_account", default="계정이 없으면 관리자에게 발급을 요청하세요."),
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                anchor=tk.W,
            ).grid(row=6, column=0, sticky="w", pady=(14, 0))

        btn_row = tk.Frame(body, bg=COLORS["card"])
        btn_row.grid(row=7, column=0, sticky="ew", pady=(22, 0))
        btn_row.grid_columnconfigure(1, weight=1)

        if self._on_back is not None:
            tk.Button(
                btn_row,
                text=t("common.back", default="뒤로"),
                bg=COLORS["chip_bg"],
                fg=COLORS["nav_text"],
                relief=tk.FLAT,
                font=(FONT, 10, "bold"),
                padx=16,
                pady=10,
                cursor="hand2",
                command=self._on_back,
            ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._submit_btn = tk.Button(
            btn_row,
            text=t("login.submit", default="로그인"),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 11, "bold"),
            padx=20,
            pady=11,
            cursor="hand2",
            command=self._do_login,
        )
        self._submit_btn.grid(row=0, column=1, sticky="ew")

        for widget in (self, body, self._username_entry, self._password_entry):
            widget.bind("<Return>", lambda _e: self._do_login(), add="+")

    def _field(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        show: str = "",
    ) -> tk.Entry:
        wrap = tk.Frame(parent, bg=COLORS["card"])
        wrap.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        wrap.grid_columnconfigure(0, weight=1)
        tk.Label(
            wrap,
            text=label,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 9, "bold"),
            anchor=tk.W,
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        entry = tk.Entry(
            wrap,
            textvariable=variable,
            show=show,
            font=FONT_BODY,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        entry.grid(row=1, column=0, sticky="ew", ipady=8)
        return entry

    def _toggle_password_visibility(self) -> None:
        if self._password_entry is None:
            return
        self._password_entry.configure(show="" if self._show_password.get() else "•")

    def _set_status(self, message: str) -> None:
        self._status.set(message)
        if message:
            self._status_wrap.grid()
        else:
            self._status_wrap.grid_remove()

    def _do_login(self) -> None:
        self._set_status("")
        if self._submit_btn is not None:
            self._submit_btn.configure(state=tk.DISABLED, text=t("login.submitting", default="확인 중..."))
            self.update_idletasks()
        try:
            rec = authenticate_credentials(
                self._username.get(),
                self._password.get(),
                preferred_tenant_id=None,
            )
            login(rec, remember=self._remember.get())
            self._on_success()
        except Exception as exc:
            self._set_status(str(exc))
        finally:
            if self._submit_btn is not None:
                self._submit_btn.configure(state=tk.NORMAL, text=t("login.submit", default="로그인"))
