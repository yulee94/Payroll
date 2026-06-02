"""
ui/login_dialog.py - Bitween 로그인 · 계정 등록
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from core.session_service import UserSession, login
from core.config import APP_CONFIG
from core.tenant_store import get_active_tenant
from core.user_store import (
    authenticate_credentials,
    register_user,
    tenant_has_users,
    validate_password,
    validate_username,
)
from ui.theme import COLORS, FONT, FONT_BODY

OnLoginSuccess = Callable[[UserSession], None]


class LoginDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_success: OnLoginSuccess | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_success = on_success
        self.title("Bitween 로그인")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        tenant = get_active_tenant()
        self._tenant_id = tenant.tenant_id
        self._tenant_name = tenant.display_name

        tk.Label(
            self,
            text="로그인",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
        ).pack(anchor=tk.W, padx=28, pady=(24, 4))
        tk.Label(
            self,
            text=f"고객사: {self._tenant_name}",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=FONT_BODY,
        ).pack(anchor=tk.W, padx=28, pady=(0, 16))

        form = tk.Frame(self, bg=COLORS["bg"], padx=28)
        form.pack(fill=tk.X)

        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._remember = tk.BooleanVar(value=True)

        self._row(form, "아이디", self._username)
        self._row(form, "비밀번호", self._password, show="•")

        ttk.Checkbutton(form, text="다음 실행 시 자동 로그인", variable=self._remember).pack(
            anchor=tk.W, pady=(8, 0)
        )

        btn_row = tk.Frame(self, bg=COLORS["bg"], padx=28, pady=20)
        btn_row.pack(fill=tk.X)

        has_users = tenant_has_users(self._tenant_id)
        if not has_users and not APP_CONFIG.allow_self_register:
            tk.Label(
                btn_row,
                text="이 고객사 계정이 아직 등록되지 않았습니다.\n관리자에게 계정 생성을 요청하세요.",
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=FONT_BODY,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(0, 10))
        elif not has_users:
            tk.Label(
                btn_row,
                text="이 고객사의 첫 계정을 만듭니다.",
                bg=COLORS["bg"],
                fg=COLORS["accent"],
                font=(FONT, 9),
            ).pack(anchor=tk.W, pady=(0, 8))
            tk.Button(
                btn_row,
                text="계정 만들기",
                bg=COLORS["accent"],
                fg="#FFFFFF",
                relief=tk.FLAT,
                font=(FONT, 11, "bold"),
                padx=16,
                pady=8,
                cursor="hand2",
                command=self._open_register,
            ).pack(anchor=tk.W)
        else:
            tk.Button(
                btn_row,
                text="로그인",
                bg=COLORS["accent"],
                fg="#FFFFFF",
                relief=tk.FLAT,
                font=(FONT, 11, "bold"),
                padx=20,
                pady=8,
                cursor="hand2",
                command=self._do_login,
            ).pack(side=tk.LEFT)
            if APP_CONFIG.allow_self_register:
                tk.Button(
                    btn_row,
                    text="계정 등록",
                    bg=COLORS["card"],
                    fg=COLORS["text"],
                    relief=tk.FLAT,
                    font=FONT_BODY,
                    padx=14,
                    pady=8,
                    cursor="hand2",
                    command=self._open_register,
                ).pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(
            btn_row,
            text="취소",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            relief=tk.FLAT,
            font=FONT_BODY,
            command=self.destroy,
        ).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda _e: self._do_login() if has_users else None)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        # 창 크기/위치: 작게 + 우측 상단
        self.update_idletasks()
        try:
            w = max(self.winfo_reqwidth(), 420)
            h = max(self.winfo_reqheight(), 260)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, sw - w - 24)
            y = 24
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            self.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")

    def _row(self, parent: tk.Frame, label: str, var: tk.StringVar, *, show: str = "") -> None:
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=6)
        tk.Label(row, text=label, width=10, anchor=tk.W, bg=COLORS["bg"], font=FONT_BODY).pack(
            side=tk.LEFT
        )
        entry = tk.Entry(row, textvariable=var, show=show, font=FONT_BODY, width=28)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if label == "아이디":
            entry.focus_set()

    def _do_login(self) -> None:
        try:
            rec = authenticate_credentials(
                self._username.get(),
                self._password.get(),
                preferred_tenant_id=self._tenant_id,
            )
            sess = login(rec, remember=self._remember.get())
            if self._on_success:
                self._on_success(sess)
            self.destroy()
        except ValueError as exc:
            messagebox.showerror("로그인 실패", str(exc), parent=self)

    def _open_register(self) -> None:
        RegisterDialog(self, tenant_id=self._tenant_id, tenant_name=self._tenant_name)


class RegisterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, tenant_id: str, tenant_name: str) -> None:
        super().__init__(parent)
        self._tenant_id = tenant_id
        self.title("계정 등록")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self,
            text="새 계정",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        ).pack(anchor=tk.W, padx=24, pady=(20, 4))
        tk.Label(
            self,
            text=f"{tenant_name} · 다른 계정의 메일·메신저는 볼 수 없습니다.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=340,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=24, pady=(0, 12))

        form = tk.Frame(self, bg=COLORS["bg"], padx=24)
        form.pack(fill=tk.X)

        self._display = tk.StringVar()
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._password2 = tk.StringVar()

        for label, var, show in (
            ("표시 이름", self._display, ""),
            ("아이디", self._username, ""),
            ("비밀번호", self._password, "•"),
            ("비밀번호 확인", self._password2, "•"),
        ):
            row = tk.Frame(form, bg=COLORS["bg"])
            row.pack(fill=tk.X, pady=5)
            tk.Label(row, text=label, width=12, anchor=tk.W, bg=COLORS["bg"], font=FONT_BODY).pack(
                side=tk.LEFT
            )
            tk.Entry(row, textvariable=var, show=show, font=FONT_BODY, width=26).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        btn_row = tk.Frame(self, bg=COLORS["bg"], padx=24, pady=16)
        btn_row.pack(fill=tk.X)
        tk.Button(
            btn_row,
            text="등록",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            command=self._register,
        ).pack(side=tk.LEFT)
        tk.Button(
            btn_row,
            text="취소",
            relief=tk.FLAT,
            font=FONT_BODY,
            command=self.destroy,
        ).pack(side=tk.LEFT, padx=8)

        # 등록 창도 우측 상단에 작게
        self.update_idletasks()
        try:
            w = max(self.winfo_reqwidth(), 420)
            h = max(self.winfo_reqheight(), 320)
            sw = self.winfo_screenwidth()
            x = max(0, sw - w - 24)
            y = 24
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _register(self) -> None:
        err = validate_username(self._username.get())
        if err:
            messagebox.showerror("등록", err, parent=self)
            return
        err = validate_password(self._password.get())
        if err:
            messagebox.showerror("등록", err, parent=self)
            return
        if self._password.get() != self._password2.get():
            messagebox.showerror("등록", "비밀번호가 일치하지 않습니다.", parent=self)
            return
        try:
            register_user(
                tenant_id=self._tenant_id,
                username=self._username.get(),
                password=self._password.get(),
                display_name=self._display.get(),
            )
            messagebox.showinfo(
                "등록 완료",
                "계정이 생성되었습니다. 로그인해 주세요.",
                parent=self,
            )
            self.destroy()
        except ValueError as exc:
            messagebox.showerror("등록", str(exc), parent=self)
