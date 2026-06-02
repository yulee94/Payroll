"""
ui/approver_picker_dialog.py - 결재선·참조 인원 검색 선택 (법인·이름)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.org_positions import position_label
from core.workflow.group_directory import (
    GroupUser,
    filter_group_users,
    format_group_user_label,
    group_user_department_label,
    list_entity_filter_options,
)
from ui.theme import COLORS, FONT, FONT_BODY
from ui.workflow_theme import WF, flat_button
from ui.wheel_scroll import bind_local_wheel


class ApproverPickerDialog(tk.Toplevel):
    """그룹 조직에서 결재자·참조인 검색·선택."""

    def __init__(
        self,
        parent: tk.Misc,
        group_users: list[GroupUser],
        *,
        title: str = "결재자 선택",
        multi: bool = False,
        on_pick: Callable[[list[GroupUser]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._all_users = list(group_users)
        self._multi = multi
        self._on_pick = on_pick
        self._result: list[GroupUser] = []
        self._gu_by_id: dict[str, GroupUser] = {gu.user.user_id: gu for gu in group_users}
        self._entity_map: dict[str, str] = {}

        self.title(title)
        self.geometry("720x520")
        self.minsize(560, 420)
        self.configure(bg=WF["page_bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._search_var = tk.StringVar()
        self._entity_var = tk.StringVar(value="전체 법인")
        self._count_var = tk.StringVar(value="")

        self._build()
        self._reload_table()
        self._search_entry.focus_set()

        self.bind("<Escape>", lambda _e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    @property
    def result(self) -> list[GroupUser]:
        return list(self._result)

    def _build(self) -> None:
        outer = tk.Frame(self, bg=WF["page_bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        outer.grid_rowconfigure(2, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        head = tk.Frame(outer, bg=WF["card"], highlightbackground=WF["card_border"], highlightthickness=1)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        inner = tk.Frame(head, bg=WF["card"], padx=14, pady=12)
        inner.pack(fill=tk.X)
        tk.Label(inner, text="조직에서 인원 검색", bg=WF["card"], fg=COLORS["text"], font=(FONT, 12, "bold")).pack(
            anchor=tk.W
        )
        tk.Label(
            inner,
            text="법인을 고른 뒤 이름·아이디·부서로 검색하세요. 더블클릭 또는 「선택」으로 확정합니다.",
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=640,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        filt = tk.Frame(outer, bg=WF["page_bg"])
        filt.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        filt.grid_columnconfigure(1, weight=1)

        tk.Label(filt, text="법인", bg=WF["page_bg"], font=(FONT, 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        entity_combo = ttk.Combobox(filt, textvariable=self._entity_var, state="readonly", width=28, font=FONT_BODY)
        entity_labels: list[str] = []
        self._entity_map.clear()
        for eid, label in list_entity_filter_options(self._all_users):
            entity_labels.append(label)
            self._entity_map[label] = eid
        entity_combo["values"] = entity_labels
        entity_combo.grid(row=0, column=1, sticky="w")
        entity_combo.bind("<<ComboboxSelected>>", lambda _e: self._reload_table())

        tk.Label(filt, text="검색", bg=WF["page_bg"], font=(FONT, 9, "bold")).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        search_row = tk.Frame(filt, bg=WF["page_bg"])
        search_row.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        search_row.grid_columnconfigure(0, weight=1)
        self._search_entry = tk.Entry(
            search_row,
            textvariable=self._search_var,
            font=FONT_BODY,
            relief=tk.FLAT,
            highlightthickness=1,
        )
        self._search_entry.grid(row=0, column=0, sticky="ew", ipady=5)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._reload_table())
        flat_button(search_row, "검색", command=self._reload_table, bg=WF["tab_inactive"], padx=10, pady=4).grid(
            row=0, column=1, padx=(8, 0)
        )

        tk.Label(filt, textvariable=self._count_var, bg=WF["page_bg"], fg=COLORS["muted"], font=(FONT, 8)).grid(
            row=2, column=1, sticky="w", pady=(6, 0)
        )

        table_wrap = tk.Frame(outer, bg=WF["card"], highlightbackground=WF["card_border"], highlightthickness=1)
        table_wrap.grid(row=2, column=0, sticky="nsew")
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = ("entity", "dept", "name", "position", "username")
        selmode = "extended" if self._multi else "browse"
        self._tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode=selmode, height=14)
        for col, label, w in (
            ("entity", "법인", 120),
            ("dept", "부서", 110),
            ("name", "이름", 90),
            ("position", "직위", 88),
            ("username", "아이디", 90),
        ):
            self._tree.heading(col, text=label)
            self._tree.column(col, width=w, minwidth=60, stretch=(col == "entity"))
        vsb = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        vsb.grid(row=0, column=1, sticky="ns", pady=8)
        self._tree.bind("<Double-1>", lambda _e: self._confirm())
        bind_local_wheel(self._tree)

        foot = tk.Frame(outer, bg=WF["page_bg"])
        foot.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        btn_label = "추가" if self._multi else "선택"
        flat_button(foot, btn_label, command=self._confirm, bg=COLORS["accent"], fg="#FFF", padx=18, pady=8).pack(
            side=tk.LEFT
        )
        flat_button(foot, "취소", command=self.destroy, bg=WF["tab_inactive"], padx=14, pady=8).pack(side=tk.RIGHT)

    def _selected_entity_id(self) -> str:
        return self._entity_map.get(self._entity_var.get(), "")

    def _reload_table(self) -> None:
        rows = filter_group_users(
            self._all_users,
            query=self._search_var.get(),
            entity_id=self._selected_entity_id(),
        )
        self._tree.delete(*self._tree.get_children())
        for gu in rows[:500]:
            uid = gu.user.user_id
            self._tree.insert(
                "",
                tk.END,
                iid=uid,
                values=(
                    gu.entity_name,
                    group_user_department_label(gu),
                    gu.user.display_name,
                    position_label(gu.user.position or ""),
                    gu.user.username,
                ),
            )
        total = len(rows)
        shown = min(total, 500)
        self._count_var.set(f"{shown}명 표시" + (f" (전체 {total}명)" if total > shown else f" · {total}명"))

    def _confirm(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        picked: list[GroupUser] = []
        for iid in sel:
            gu = self._gu_by_id.get(str(iid))
            if gu:
                picked.append(gu)
        if not picked:
            return
        self._result = picked
        if self._on_pick:
            self._on_pick(picked)
        self.destroy()


def pick_group_users(
    parent: tk.Misc,
    group_users: list[GroupUser],
    *,
    title: str = "결재자 선택",
    multi: bool = False,
) -> list[GroupUser]:
    if not group_users:
        return []
    dlg = ApproverPickerDialog(parent, group_users, title=title, multi=multi)
    parent.wait_window(dlg)
    return dlg.result


def pick_single_group_user(parent: tk.Misc, group_users: list[GroupUser], *, title: str = "결재자 선택") -> GroupUser | None:
    rows = pick_group_users(parent, group_users, title=title, multi=False)
    return rows[0] if rows else None
