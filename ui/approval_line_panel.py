"""
ui/approval_line_panel.py - 결재선 시각 편집 (순서·역할·결재자 한눈에)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from core.workflow.forms import APPROVER_ROLES
from core.workflow.group_directory import GroupUser, group_user_department_label
from core.user_store import UserRecord
from ui.approver_picker_dialog import pick_single_group_user
from ui.theme import COLORS, FONT, FONT_BODY
from ui.workflow_theme import WF, flat_button
from ui.wheel_scroll import wheel_delta


OnChange = Callable[[], None]

_ROLE_OPTIONS = [(k, v) for k, v in APPROVER_ROLES.items()]
_STEP_COLORS = ("#2563EB", "#0284C7", "#059669", "#D97706", "#7C3AED", "#DC2626")


class ApprovalLinePanel(tk.Frame):
    """결재선을 카드형 흐름(1 → 2 → 3)으로 표시·편집."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        group_users: list[GroupUser],
        users: list[UserRecord],
        on_change: OnChange | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, bg=WF["card"], **kwargs)
        self._group_users = group_users
        self._users = users
        self._on_change = on_change
        self._rows: list[dict[str, Any]] = []
        self._card_frames: list[tk.Frame] = []
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        head = tk.Frame(self, bg=WF["card"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(head, text="결재선", bg=WF["card"], fg=COLORS["text"], font=(FONT, 11, "bold")).pack(
            side=tk.LEFT
        )
        self._summary_lbl = tk.Label(
            head,
            text="",
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        )
        self._summary_lbl.pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True)

        scroll_wrap = tk.Frame(self, bg=WF["card"])
        scroll_wrap.grid(row=1, column=0, sticky="nsew")
        scroll_wrap.grid_rowconfigure(0, weight=1)
        scroll_wrap.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            scroll_wrap,
            bg=WF["card"],
            highlightthickness=0,
            bd=0,
            height=148,
        )
        hsb = ttk.Scrollbar(scroll_wrap, orient=tk.HORIZONTAL, command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=hsb.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        hsb.grid(row=1, column=0, sticky="ew")

        self._flow_host = tk.Frame(self._canvas, bg=WF["card"])
        self._flow_win = self._canvas.create_window((0, 0), window=self._flow_host, anchor=tk.NW)
        self._flow_host.bind("<Configure>", self._on_flow_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_horizontal_wheel(self._canvas)

        foot = tk.Frame(self, bg=WF["card"])
        foot.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        flat_button(
            foot,
            "＋ 결재자 추가",
            command=self._add_approver,
            bg=COLORS["accent"],
            fg="#FFF",
            padx=10,
            pady=5,
            font=(FONT, 9, "bold"),
        ).pack(side=tk.LEFT)

    def _on_flow_configure(self, _event: tk.Event | None = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._flow_win, height=event.height)

    def _bind_horizontal_wheel(self, widget: tk.Misc) -> None:
        def _handler(event: tk.Event) -> str:
            delta = wheel_delta(event)
            if delta:
                self._canvas.xview_scroll(delta, "units")
            return "break"

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(seq, _handler, add="+")

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self._rows = [dict(r) for r in rows]
        self.refresh()

    def get_rows(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def refresh(self) -> None:
        for w in self._flow_host.winfo_children():
            w.destroy()
        self._card_frames.clear()

        if not self._rows:
            empty = tk.Frame(self._flow_host, bg=WF["card"])
            empty.pack(side=tk.LEFT, padx=4, pady=8)
            tk.Label(
                empty,
                text="결재자가 없습니다.\n「＋ 결재자 추가」로 지정하세요.",
                bg=WF["tab_inactive"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                padx=24,
                pady=20,
                justify=tk.CENTER,
            ).pack()
            self._update_summary()
            self._on_flow_configure()
            return

        gu_map = {gu.user.user_id: gu for gu in self._group_users}
        name_lookup = {u.user_id: u.display_name for u in self._users}

        for i, row in enumerate(self._rows):
            if i > 0:
                self._add_arrow(i)
            card = self._build_step_card(i, row, gu_map, name_lookup)
            card.pack(side=tk.LEFT, padx=(0 if i == 0 else 2, 2), pady=4)
            self._card_frames.append(card)

        self._update_summary()
        self._on_flow_configure()

    def _add_arrow(self, step_index: int) -> None:
        arrow = tk.Frame(self._flow_host, bg=WF["card"])
        arrow.pack(side=tk.LEFT, padx=0, pady=4)
        tk.Label(
            arrow,
            text="→",
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 16, "bold"),
        ).pack(expand=True, pady=36)

    def _build_step_card(
        self,
        index: int,
        row: dict[str, Any],
        gu_map: dict[str, GroupUser],
        name_lookup: dict[str, str],
    ) -> tk.Frame:
        uid = row.get("approver_id", "")
        gu = gu_map.get(uid)
        name = gu.user.display_name if gu else name_lookup.get(uid, "미지정")
        entity = gu.entity_name if gu else ""
        dept = group_user_department_label(gu) if gu else ""
        role_key = row.get("approver_role", "department_manager")
        accent = _STEP_COLORS[index % len(_STEP_COLORS)]

        card = tk.Frame(
            self._flow_host,
            bg=WF["card"],
            highlightbackground=WF["card_border"],
            highlightthickness=1,
        )
        inner = tk.Frame(card, bg=WF["card"], padx=10, pady=8)
        inner.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(inner, bg=WF["card"])
        top.pack(fill=tk.X)

        badge = tk.Label(
            top,
            text=str(index + 1),
            bg=accent,
            fg="#FFFFFF",
            font=(FONT, 11, "bold"),
            width=2,
            height=1,
        )
        badge.pack(side=tk.LEFT)

        info = tk.Frame(top, bg=WF["card"])
        info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 4))

        name_lbl = tk.Label(
            info,
            text=name,
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
            cursor="hand2",
        )
        name_lbl.pack(anchor=tk.W)
        name_lbl.bind("<Button-1>", lambda _e, idx=index: self._change_approver(idx))
        name_lbl.bind("<Double-Button-1>", lambda _e, idx=index: self._change_approver(idx))

        meta_parts = [p for p in (entity, dept) if p]
        meta = " · ".join(meta_parts) if meta_parts else "법인·부서 미지정"
        tk.Label(
            info,
            text=meta,
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            anchor=tk.W,
        ).pack(anchor=tk.W)

        actions = tk.Frame(top, bg=WF["card"])
        actions.pack(side=tk.RIGHT)
        for sym, cmd in (
            ("▲", lambda idx=index: self._move(idx, -1)),
            ("▼", lambda idx=index: self._move(idx, 1)),
            ("✕", lambda idx=index: self._remove(idx)),
        ):
            btn = tk.Button(
                actions,
                text=sym,
                command=cmd,
                bg=WF["tab_inactive"],
                fg=COLORS["text"],
                activebackground=WF["row_hover"],
                relief=tk.FLAT,
                bd=0,
                font=(FONT, 8),
                width=2,
                cursor="hand2",
                padx=0,
                pady=0,
            )
            btn.pack(side=tk.LEFT, padx=1)
            if sym == "✕":
                btn.configure(fg="#B91C1C", activebackground="#FEE2E2")

        role_row = tk.Frame(inner, bg=WF["card"])
        role_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(role_row, text="역할", bg=WF["card"], fg=COLORS["muted"], font=(FONT, 8)).pack(side=tk.LEFT)
        role_var = tk.StringVar(value=APPROVER_ROLES.get(role_key, role_key))
        role_cb = ttk.Combobox(
            role_row,
            textvariable=role_var,
            state="readonly",
            width=12,
            values=[v for _, v in _ROLE_OPTIONS],
            font=FONT_BODY,
        )
        role_cb.pack(side=tk.LEFT, padx=(6, 0))
        role_cb.bind("<<ComboboxSelected>>", lambda _e, idx=index, var=role_var: self._apply_role(idx, var.get()))

        return card

    def _apply_role(self, index: int, role_label: str) -> None:
        if not (0 <= index < len(self._rows)):
            return
        role_key = next((k for k, v in APPROVER_ROLES.items() if v == role_label), "department_manager")
        self._rows[index]["approver_role"] = role_key
        self._rows[index]["role_label"] = role_label
        self._notify()

    def _change_approver(self, index: int) -> None:
        if not (0 <= index < len(self._rows)):
            return
        gu = pick_single_group_user(self.winfo_toplevel(), self._group_users, title="결재자 변경")
        if not gu:
            return
        self._rows[index]["approver_id"] = gu.user.user_id
        self._rows[index]["approver_tenant_id"] = gu.tenant_id
        self.refresh()
        self._notify()

    def _add_approver(self) -> None:
        gu = pick_single_group_user(self.winfo_toplevel(), self._group_users, title="결재자 추가")
        if not gu:
            return
        role_key = "department_manager"
        self._rows.append(
            {
                "approver_id": gu.user.user_id,
                "approver_role": role_key,
                "approver_tenant_id": gu.tenant_id,
                "role_label": APPROVER_ROLES.get(role_key, role_key),
            }
        )
        self.refresh()
        self._notify()
        self.after_idle(lambda: self._canvas.xview_moveto(1.0))

    def _remove(self, index: int) -> None:
        if 0 <= index < len(self._rows):
            self._rows.pop(index)
            self.refresh()
            self._notify()

    def _move(self, index: int, delta: int) -> None:
        new_idx = index + delta
        if 0 <= index < len(self._rows) and 0 <= new_idx < len(self._rows):
            self._rows[index], self._rows[new_idx] = self._rows[new_idx], self._rows[index]
            self.refresh()
            self._notify()

    def _update_summary(self) -> None:
        if not self._rows:
            self._summary_lbl.configure(text="")
            return
        gu_map = {gu.user.user_id: gu for gu in self._group_users}
        name_lookup = {u.user_id: u.display_name for u in self._users}
        names: list[str] = []
        for row in self._rows:
            uid = row.get("approver_id", "")
            gu = gu_map.get(uid)
            names.append(gu.user.display_name if gu else name_lookup.get(uid, "?"))
        self._summary_lbl.configure(text="  →  ".join(names))

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()
