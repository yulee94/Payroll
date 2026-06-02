"""
ui/org_admin_panel.py - 조직도·팀별 계정 생성·직위 권한 관리
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from core.bootstrap_org import COSS_CEO_DEFAULT_PASSWORD, COSS_CEO_USERNAME
from core.org_access import org_summary_for_user, require_org_management
from core.org_positions import (
    ORG_PLATFORM_IDS,
    ORG_PLATFORM_LABELS,
    POSITION_LABELS,
    POSITION_ORDER,
    position_label,
)
from core.org_store import create_unit, get_unit, list_units, update_unit
from core.roles import ROLE_CHOICES, ROLE_LABELS, normalize_role
from core.session_service import get_session, is_logged_in
from core.tenant_store import get_active_tenant
from core.user_store import (
    admin_create_user,
    list_users_in_org_unit,
    update_user_org,
    validate_password,
    validate_username,
)
from ui.theme import COLORS, FONT, FONT_BODY

OnChanged = Callable[[], None]


class OrgAdminPanel(ttk.Frame):
    """대표·조직 관리자: 팀 트리, 계정 생성, 직위·플랫폼 접근."""

    def __init__(self, master: tk.Misc, *, on_changed: OnChanged | None = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._on_changed = on_changed
        self._selected_unit_id: str = ""
        self._platform_vars: dict[str, tk.BooleanVar] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        pad = ttk.Frame(self, padding=24)
        pad.pack(fill=tk.BOTH, expand=True)

        ttk.Label(pad, text="조직 · 계정 관리", font=(FONT, 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=(
                "대표이사 계정에서 조직도를 구성하고, 팀·직위별로 하위 계정을 생성합니다. "
                "각 팀에 사용할 플랫폼(급여·전자결재·정비·입찰·회계)을 지정하면 "
                "해당 팀 소속은 지정된 메뉴만 이용할 수 있습니다."
            ),
            wraplength=900,
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(8, 12))

        self._status = tk.StringVar(value="")
        ttk.Label(pad, textvariable=self._status, font=(FONT, 9), foreground=COLORS["muted"]).pack(
            anchor=tk.W, pady=(0, 8)
        )

        body = ttk.Panedwindow(pad, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        body.add(left, weight=1)
        ttk.Label(left, text="조직도", font=(FONT, 11, "bold")).pack(anchor=tk.W)
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self._org_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._org_tree.yview)
        self._org_tree.configure(yscrollcommand=scroll.set)
        self._org_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._org_tree.bind("<<TreeviewSelect>>", self._on_unit_selected)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="＋ 하위 팀", command=self._add_child_unit).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="새로고침", command=self.refresh).pack(side=tk.RIGHT)

        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        body.add(right, weight=2)

        ttk.Label(right, text="팀 설정 · 소속 인원", font=(FONT, 11, "bold")).pack(anchor=tk.W)
        detail = ttk.LabelFrame(right, text="선택 팀", padding=12)
        detail.pack(fill=tk.X, pady=(6, 8))

        self._unit_name_var = tk.StringVar()
        name_row = ttk.Frame(detail)
        name_row.pack(fill=tk.X)
        ttk.Label(name_row, text="팀명").pack(side=tk.LEFT)
        ttk.Entry(name_row, textvariable=self._unit_name_var, width=28).pack(side=tk.LEFT, padx=(8, 8))
        ttk.Button(name_row, text="저장", command=self._save_unit).pack(side=tk.LEFT)

        plat_frame = ttk.Frame(detail)
        plat_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(plat_frame, text="사용 플랫폼").pack(anchor=tk.W)
        checks = ttk.Frame(plat_frame)
        checks.pack(anchor=tk.W, pady=(4, 0))
        for pid in ORG_PLATFORM_IDS:
            var = tk.BooleanVar(value=False)
            self._platform_vars[pid] = var
            ttk.Checkbutton(checks, text=ORG_PLATFORM_LABELS[pid], variable=var).pack(side=tk.LEFT, padx=(0, 12))

        members_frame = ttk.LabelFrame(right, text="소속 계정", padding=12)
        members_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        cols = ("display_name", "username", "position", "role", "platforms")
        self._member_tree = ttk.Treeview(members_frame, columns=cols, show="headings", height=8)
        for col, title, w in (
            ("display_name", "이름", 100),
            ("username", "아이디", 90),
            ("position", "직위", 90),
            ("role", "시스템권한", 80),
            ("platforms", "접근 플랫폼", 180),
        ):
            self._member_tree.heading(col, text=title)
            self._member_tree.column(col, width=w)
        mscroll = ttk.Scrollbar(members_frame, orient=tk.VERTICAL, command=self._member_tree.yview)
        self._member_tree.configure(yscrollcommand=mscroll.set)
        self._member_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mscroll.pack(side=tk.RIGHT, fill=tk.Y)

        action = ttk.Frame(right)
        action.pack(fill=tk.X)
        ttk.Button(action, text="＋ 팀원 계정 생성", command=self._create_member).pack(side=tk.LEFT)
        ttk.Button(action, text="직위 변경", command=self._change_position).pack(side=tk.LEFT, padx=(8, 0))

        info = ttk.LabelFrame(pad, text="대표 계정 안내", padding=10)
        info.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(
            info,
            text=(
                f"COSS 대표 계정: 아이디 「{COSS_CEO_USERNAME}」 / "
                f"초기 비밀번호 「{COSS_CEO_DEFAULT_PASSWORD}」 (최초 로그인 후 변경 권장)"
            ),
            font=(FONT, 9),
            foreground=COLORS["muted"],
        ).pack(anchor=tk.W)

    def refresh(self) -> None:
        tenant = get_active_tenant()
        self._org_tree.delete(*self._org_tree.get_children())
        self._member_tree.delete(*self._member_tree.get_children())
        self._selected_unit_id = ""

        if not is_logged_in():
            self._status.set("로그인 후 조직·계정 관리를 이용할 수 있습니다.")
            return
        try:
            require_org_management()
        except PermissionError as exc:
            self._status.set(str(exc))
            return

        units = list_units(tenant.tenant_id)
        by_parent: dict[str, list] = {}
        for u in units:
            by_parent.setdefault(u.parent_id or "", []).append(u)

        def _insert(parent_iid: str, parent_id: str) -> None:
            for u in sorted(by_parent.get(parent_id, []), key=lambda x: (x.sort_order, x.name)):
                label = f"{u.name}  ({len(list_users_in_org_unit(tenant.tenant_id, u.unit_id))}명)"
                self._org_tree.insert(parent_iid, tk.END, iid=u.unit_id, text=label, open=True)
                _insert(u.unit_id, u.unit_id)

        _insert("", "")
        self._status.set(f"{tenant.display_name} — 조직 {len(units)}개 · 관리자: {get_session().display_name}")

        children = self._org_tree.get_children("")
        if children:
            first = children[0]
            self._org_tree.selection_set(first)
            self._org_tree.focus(first)
            self._load_unit(first)

    def _on_unit_selected(self, _event: tk.Event | None = None) -> None:
        sel = self._org_tree.selection()
        if sel:
            self._load_unit(sel[0])

    def _load_unit(self, unit_id: str) -> None:
        tenant = get_active_tenant()
        unit = get_unit(tenant.tenant_id, unit_id)
        if unit is None:
            return
        self._selected_unit_id = unit_id
        self._unit_name_var.set(unit.name)
        plat_set = set(unit.platform_ids)
        for pid, var in self._platform_vars.items():
            var.set(pid in plat_set)

        self._member_tree.delete(*self._member_tree.get_children())
        for user in list_users_in_org_unit(tenant.tenant_id, unit_id, include_subtree=False):
            summary = org_summary_for_user(user.user_id)
            self._member_tree.insert(
                "",
                tk.END,
                iid=user.user_id,
                values=(
                    user.display_name,
                    user.username,
                    summary.get("position", ""),
                    ROLE_LABELS.get(normalize_role(user.role), user.role),
                    summary.get("platforms", ""),
                ),
            )

    def _save_unit(self) -> None:
        if not self._selected_unit_id:
            return
        tenant = get_active_tenant()
        try:
            require_org_management()
            platforms = tuple(pid for pid, var in self._platform_vars.items() if var.get())
            update_unit(
                tenant.tenant_id,
                self._selected_unit_id,
                name=self._unit_name_var.get().strip(),
                platform_ids=platforms,
            )
            self.refresh()
            if self._on_changed:
                self._on_changed()
            messagebox.showinfo("저장됨", "팀 설정이 저장되었습니다.", parent=self.winfo_toplevel())
        except (PermissionError, ValueError) as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _add_child_unit(self) -> None:
        if not is_logged_in():
            return
        tenant = get_active_tenant()
        parent_id = self._selected_unit_id or ""
        name = simpledialog.askstring("하위 팀 추가", "새 팀·부서 이름:", parent=self.winfo_toplevel())
        if not name or not name.strip():
            return
        try:
            require_org_management()
            unit = create_unit(tenant.tenant_id, name=name.strip(), parent_id=parent_id)
            self.refresh()
            self._org_tree.selection_set(unit.unit_id)
            self._load_unit(unit.unit_id)
        except (PermissionError, ValueError) as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _create_member(self) -> None:
        if not self._selected_unit_id:
            messagebox.showinfo("계정", "팀을 선택하세요.", parent=self.winfo_toplevel())
            return
        sess = get_session()
        if sess is None:
            return
        dlg = _CreateMemberDialog(self, unit_id=self._selected_unit_id, creator_id=sess.user_id)
        if dlg.result:
            self._load_unit(self._selected_unit_id)
            if self._on_changed:
                self._on_changed()

    def _change_position(self) -> None:
        sel = self._member_tree.selection()
        if not sel:
            messagebox.showinfo("직위", "구성원을 선택하세요.", parent=self.winfo_toplevel())
            return
        uid = sel[0]
        labels = [POSITION_LABELS[p] for p in POSITION_ORDER]
        choice = simpledialog.askstring(
            "직위 변경",
            "새 직위:\n" + " / ".join(labels),
            parent=self.winfo_toplevel(),
        )
        if not choice:
            return
        pos = next((p for p in POSITION_ORDER if POSITION_LABELS[p] == choice.strip()), "")
        if not pos:
            for p in POSITION_ORDER:
                if POSITION_LABELS[p] in choice:
                    pos = p
                    break
        if not pos:
            messagebox.showwarning("직위", "목록에서 직위를 선택하세요.", parent=self.winfo_toplevel())
            return
        try:
            require_org_management()
            update_user_org(uid, position=pos)
            self._load_unit(self._selected_unit_id)
            messagebox.showinfo("저장됨", f"직위가 「{position_label(pos)}」(으)로 변경되었습니다.", parent=self.winfo_toplevel())
        except (PermissionError, ValueError) as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())


class _CreateMemberDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, unit_id: str, creator_id: str) -> None:
        super().__init__(parent)
        self.result = False
        self._unit_id = unit_id
        self._creator_id = creator_id
        self.title("팀원 계정 생성")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.resizable(False, False)

        pad = ttk.Frame(self, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._name = tk.StringVar()
        self._position = tk.StringVar(value=POSITION_LABELS[POSITION_ORDER[-2]])
        self._role = tk.StringVar(value=ROLE_LABELS["staff"])

        fields = (
            ("아이디", self._username),
            ("초기 비밀번호", self._password),
            ("표시 이름", self._name),
        )
        for label, var in fields:
            row = ttk.Frame(pad)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=28, show="*" if label == "초기 비밀번호" else "").pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        row = ttk.Frame(pad)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="직위", width=14).pack(side=tk.LEFT)
        ttk.Combobox(
            row,
            textvariable=self._position,
            values=[POSITION_LABELS[p] for p in POSITION_ORDER],
            state="readonly",
            width=26,
        ).pack(side=tk.LEFT)

        row = ttk.Frame(pad)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="시스템 권한", width=14).pack(side=tk.LEFT)
        ttk.Combobox(
            row,
            textvariable=self._role,
            values=[ROLE_LABELS[r] for r in ROLE_CHOICES],
            state="readonly",
            width=26,
        ).pack(side=tk.LEFT)

        btns = ttk.Frame(pad)
        btns.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(btns, text="생성", command=self._submit).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text="취소", command=self.destroy).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda _e: self._submit())
        self.wait_window()

    def _submit(self) -> None:
        tenant = get_active_tenant()
        uname = self._username.get().strip()
        pwd = self._password.get()
        name = self._name.get().strip()
        err = validate_username(uname) or validate_password(pwd)
        if err:
            messagebox.showerror("입력", err, parent=self)
            return
        if not name:
            messagebox.showerror("입력", "표시 이름을 입력하세요.", parent=self)
            return
        pos_label = self._position.get().strip()
        pos = next((p for p in POSITION_ORDER if POSITION_LABELS[p] == pos_label), POSITION_ORDER[-2])
        role_label = self._role.get().strip()
        role = next((r for r in ROLE_CHOICES if ROLE_LABELS[r] == role_label), "staff")
        try:
            admin_create_user(
                tenant_id=tenant.tenant_id,
                username=uname,
                password=pwd,
                display_name=name,
                org_unit_id=self._unit_id,
                position=pos,
                manager_user_id=self._creator_id,
                role=role,
                creator_user_id=self._creator_id,
            )
            self.result = True
            messagebox.showinfo("생성됨", f"「{name}」 계정이 생성되었습니다.", parent=self)
            self.destroy()
        except (PermissionError, ValueError) as exc:
            messagebox.showerror("오류", str(exc), parent=self)
