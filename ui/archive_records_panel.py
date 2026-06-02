"""
ui/archive_records_panel.py - 월별 자료함 · 사업장별 급여 내역
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from services.org_registry import ALL_LABEL, OrgSelection, filter_records, group_by_workplace, summarize_records
from ui.theme import COLORS, FONT, FONT_STAT


class ArchiveRecordsPanel(ttk.Frame):
    """선택 월·조직 필터 기준 인원별·사업장별 내역."""

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._records: list = []
        self._selection = OrgSelection()
        self._group_mode = tk.StringVar(value="사업장별")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(toolbar, text="보기", font=(FONT, 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        for text, val in (("사업장별", "사업장별"), ("인원별", "인원별")):
            ttk.Radiobutton(
                toolbar,
                text=text,
                value=val,
                variable=self._group_mode,
                command=self._redraw,
            ).pack(side=tk.LEFT, padx=(0, 6))

        self._summary = tk.Label(
            self,
            text="급여월과 조직 필터를 선택하세요.",
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=12,
            pady=8,
        )
        self._summary.pack(fill=tk.X, pady=(0, 8))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = ("label", "affiliate", "workplace", "count", "gross", "net", "leave", "absence")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings")
        headings = {
            "label": ("구분 / 성명", 120),
            "affiliate": ("계열사", 100),
            "workplace": ("사업장", 110),
            "count": ("인원", 56),
            "gross": ("총지급", 100),
            "net": ("실수령", 100),
            "leave": ("연차", 52),
            "absence": ("무급", 52),
        }
        for key, (title, width) in headings.items():
            self.tree.heading(key, text=title)
            anchor = tk.E if key not in ("label", "affiliate", "workplace") else tk.W
            self.tree.column(key, width=width, minwidth=48, anchor=anchor)

        scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def load(self, period: str, records: list, selection: OrgSelection | None = None) -> None:
        self._records = records or []
        self._selection = selection or OrgSelection()
        self._redraw()

    def _filtered(self) -> list:
        return filter_records(self._records, self._selection)

    def _fmt_won(self, n: int) -> str:
        return f"{n:,}"

    def _redraw(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered = self._filtered()
        sm = summarize_records(filtered)
        sel = self._selection
        scope_parts = []
        if sel.affiliate != ALL_LABEL:
            scope_parts.append(sel.affiliate)
        if sel.workplace != ALL_LABEL:
            scope_parts.append(sel.workplace)
        scope = " · ".join(scope_parts) if scope_parts else "전체"
        self._summary.configure(
            text=(
                f"{scope} — {sm.employee_count}명 · 총지급 {self._fmt_won(sm.total_gross)} · "
                f"실수령 {self._fmt_won(sm.total_net)} · 연차 {sm.leave_users}명 · 무급 {sm.absence_users}명"
            )
        )

        if not filtered:
            return

        if self._group_mode.get() == "사업장별":
            for wp, rows in group_by_workplace(filtered):
                sm_wp = summarize_records(rows)
                aff = rows[0].get("affiliate", "") if rows else ""
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        wp,
                        aff,
                        wp,
                        f"{sm_wp.employee_count}명",
                        self._fmt_won(sm_wp.total_gross),
                        self._fmt_won(sm_wp.total_net),
                        f"{sm_wp.leave_users}명",
                        f"{sm_wp.absence_users}명",
                    ),
                )
        else:
            for r in sorted(filtered, key=lambda x: (str(x.get("workplace") or ""), str(x.get("name") or ""))):
                leave = r.get("leave_days", 0)
                unpaid = r.get("unpaid_days", 0)
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("name", ""),
                        r.get("affiliate", ""),
                        r.get("workplace", ""),
                        "1명",
                        self._fmt_won(int(r.get("gross_pay") or 0)),
                        self._fmt_won(int(r.get("net_pay") or 0)),
                        leave if float(leave or 0) > 0 else "-",
                        unpaid if float(unpaid or 0) > 0 else "-",
                    ),
                )
