"""
ui/user_permissions_panel.py - 사용자 권한(재무팀·관리자) 설정
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from core.access_control import (
    list_tenant_users_with_roles,
    require_role_management,
    set_user_role_for_tenant,
)
from core.roles import ROLE_CHOICES, ROLE_DESCRIPTIONS, ROLE_LABELS, normalize_role
from core.session_service import get_session, is_logged_in
from core.tenant_store import get_active_tenant
from ui.login_dialog import LoginDialog
from ui.theme import COLORS, FONT, FONT_BODY

OnChanged = Callable[[], None]


class UserPermissionsPanel(ttk.Frame):
    """관리자: 동일 고객사 사용자 역할 변경."""

    def __init__(self, master: tk.Misc, *, on_changed: OnChanged | None = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._on_changed = on_changed
        self._rows: list[dict[str, str]] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        pad = ttk.Frame(self, padding=24)
        pad.pack(fill=tk.BOTH, expand=True)

        ttk.Label(pad, text="사용자 권한", font=(FONT, 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=(
                "임원 급여·명부·월별 경영 보고는 재무팀·관리자만 조회할 수 있습니다. "
                "명부에 「임원」 열(예/ Y) 또는 직책(이사·상무 등)으로 임원을 표시합니다."
            ),
            wraplength=820,
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(8, 12))

        for role in ROLE_CHOICES:
            ttk.Label(
                pad,
                text=f"· {ROLE_LABELS[role]}: {ROLE_DESCRIPTIONS[role]}",
                font=(FONT, 9),
                foreground=COLORS["muted"],
            ).pack(anchor=tk.W)

        self._status = tk.StringVar(value="")
        ttk.Label(pad, textvariable=self._status, font=(FONT, 9)).pack(anchor=tk.W, pady=(12, 4))

        table_frame = ttk.Frame(pad)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        cols = ("display_name", "username", "org_unit", "position", "role_label", "platforms")
        self._tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            height=10,
            selectmode="browse",
        )
        self._tree.heading("display_name", text="표시 이름")
        self._tree.heading("username", text="아이디")
        self._tree.heading("org_unit", text="소속 팀")
        self._tree.heading("position", text="직위")
        self._tree.heading("role_label", text="시스템 권한")
        self._tree.heading("platforms", text="접근 플랫폼")
        self._tree.column("display_name", width=100)
        self._tree.column("username", width=90)
        self._tree.column("org_unit", width=100)
        self._tree.column("position", width=80)
        self._tree.column("role_label", width=80)
        self._tree.column("platforms", width=160)
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        edit = ttk.Frame(pad)
        edit.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(edit, text="권한 변경", font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        self._role_var = tk.StringVar()
        self._role_combo = ttk.Combobox(
            edit,
            textvariable=self._role_var,
            values=[ROLE_LABELS[r] for r in ROLE_CHOICES],
            state="readonly",
            width=16,
        )
        self._role_combo.pack(side=tk.LEFT, padx=(12, 8))
        ttk.Button(edit, text="적용", command=self._apply_role).pack(side=tk.LEFT)
        ttk.Button(edit, text="새로고침", command=self.refresh).pack(side=tk.RIGHT)

    def refresh(self) -> None:
        tenant = get_active_tenant()
        self._tree.delete(*self._tree.get_children())
        self._rows = []

        if not is_logged_in():
            self._status.set("로그인 후 관리자만 권한을 변경할 수 있습니다.")
            return

        try:
            require_role_management()
        except PermissionError as exc:
            self._status.set(str(exc))
            return

        self._rows = list_tenant_users_with_roles(tenant.tenant_id)
        for row in self._rows:
            self._tree.insert(
                "",
                tk.END,
                iid=row["user_id"],
                values=(
                    row["display_name"],
                    row["username"],
                    row.get("org_unit", ""),
                    row.get("position", ""),
                    row["role_label"],
                    row.get("platforms", ""),
                ),
            )
        self._status.set(f"{tenant.display_name} — 사용자 {len(self._rows)}명")

    def _apply_role(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("권한", "사용자를 선택하세요.", parent=self.winfo_toplevel())
            return
        uid = sel[0]
        label = self._role_var.get().strip()
        role = next((r for r in ROLE_CHOICES if ROLE_LABELS[r] == label), "")
        if not role:
            messagebox.showwarning("권한", "역할을 선택하세요.", parent=self.winfo_toplevel())
            return
        try:
            set_user_role_for_tenant(uid, role)
            self.refresh()
            if self._on_changed:
                self._on_changed()
            messagebox.showinfo("저장됨", f"권한이 「{ROLE_LABELS[role]}」(으)로 변경되었습니다.", parent=self.winfo_toplevel())
        except (PermissionError, ValueError) as exc:
            messagebox.showerror("권한", str(exc), parent=self.winfo_toplevel())


def open_permissions_with_login(parent: tk.Misc) -> None:
    if not is_logged_in():
        LoginDialog(parent)
