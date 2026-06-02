"""
ui/payroll_audit_dialog.py - 청구서 급여 산출 자동검열 결과
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ui.theme import COLORS, FONT, FONT_BODY


class PayrollAuditDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, audit: dict[str, Any]) -> None:
        super().__init__(master)
        self.title("자동검열 — 청구서 급여 산출")
        self.geometry("920x520")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        summary = audit.get("summary") or {}
        header = ttk.Frame(self, padding=12)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text=(
                f"총 {summary.get('total', 0)}명 · "
                f"정상 {summary.get('pass', 0)}명 · "
                f"확인 {summary.get('warn', 0)}명"
            ),
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W)
        wp = audit.get("workplace")
        if wp:
            ttk.Label(header, text=f"사업장: {wp}", foreground="#555").pack(anchor=tk.W)

        table_wrap = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_wrap.pack(fill=tk.BOTH, expand=True)
        cols = (
            "status",
            "name",
            "base_days",
            "work_days",
            "break_hours",
            "applied_h",
            "calc_base",
            "flags",
        )
        tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=16)
        tree.heading("status", text="결과")
        tree.heading("name", text="성명")
        tree.heading("base_days", text="I 기준")
        tree.heading("work_days", text="J 근무")
        tree.heading("break_hours", text="휴계(h)")
        tree.heading("applied_h", text="적용(h)")
        tree.heading("calc_base", text="산출 기본급")
        tree.heading("flags", text="비고")
        tree.column("status", width=52, anchor=tk.CENTER)
        tree.column("name", width=88)
        tree.column("base_days", width=64, anchor=tk.E)
        tree.column("work_days", width=64, anchor=tk.E)
        tree.column("break_hours", width=64, anchor=tk.E)
        tree.column("applied_h", width=64, anchor=tk.E)
        tree.column("calc_base", width=96, anchor=tk.E)
        tree.column("flags", width=280)
        ysb = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        for row in audit.get("rows") or []:
            br = row.get("break_hours")
            br_txt = f"{br:g}" if br is not None else "-"
            calc = row.get("calc_base_salary") or 0
            flags = "; ".join(row.get("flags") or [])
            iid = tree.insert(
                "",
                tk.END,
                values=(
                    row.get("status_label", ""),
                    row.get("name", ""),
                    f"{row.get('base_days', 0):g}",
                    f"{row.get('work_days', 0):g}",
                    br_txt,
                    f"{row.get('applied_monthly_hours', 0):g}",
                    f"{calc:,}" if calc else "-",
                    flags,
                ),
            )
            if row.get("status") == "warn":
                tree.item(iid, tags=("warn",))
        tree.tag_configure("warn", foreground="#B45309")

        detail = tk.Text(
            self,
            height=5,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg="#FAFBFC",
            relief=tk.FLAT,
            padx=10,
            pady=8,
        )
        detail.pack(fill=tk.X, padx=12, pady=(0, 8))

        def on_select(_event=None) -> None:
            sel = tree.selection()
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if not sel:
                detail.configure(state=tk.DISABLED)
                return
            idx = tree.index(sel[0])
            rows = audit.get("rows") or []
            if idx < len(rows):
                r = rows[idx]
                lines = [
                    r.get("formula", ""),
                    r.get("hours_source", ""),
                ]
                detail.insert("1.0", "\n".join(x for x in lines if x))
            detail.configure(state=tk.DISABLED)

        tree.bind("<<TreeviewSelect>>", on_select)
        if audit.get("rows"):
            first = tree.get_children()
            if first:
                tree.selection_set(first[0])
                on_select()

        ttk.Button(self, text="닫기", command=self.destroy).pack(pady=(0, 12))
