"""
ui/reports_dashboard.py - 보고·연차 화면 (조직 필터 + KPI + 연차/무급 목록)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from payroll_archive import MonthSummary, format_period_display
from services.org_registry import ALL_LABEL, OrgSelection, filter_records, summarize_records
from ui.theme import COLORS, FONT, FONT_STAT


class ReportsDashboardPanel(ttk.Frame):
    """전월 대비·연차 현황을 조직 필터 기준으로 표시."""

    def __init__(self, parent, colors: dict[str, str] | None = None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._colors = colors or COLORS
        self._summary: MonthSummary | None = None
        self._records: list = []
        self._selection = OrgSelection()
        self._comparison_status = ""
        self._kpi_labels: dict[str, tk.Label] = {}

        comp_frame = ttk.LabelFrame(self, text="  전월 대비 급여차이  ", padding=10)
        comp_frame.pack(fill=tk.X, pady=(0, 10))
        self._comp_status = tk.Label(
            comp_frame,
            text="",
            anchor=tk.W,
            justify=tk.LEFT,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 9),
            padx=4,
            pady=2,
        )
        self._comp_status.pack(fill=tk.X)

        kpi_frame = tk.Frame(self, bg=self._colors["bg"])
        kpi_frame.pack(fill=tk.X, pady=(0, 10))
        for i, (key, title) in enumerate(
            [
                ("count", "인원"),
                ("gross", "총지급"),
                ("net", "실수령"),
                ("leave", "연차"),
                ("absence", "무급/결근"),
            ]
        ):
            card = tk.Frame(
                kpi_frame,
                bg=COLORS["card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
            )
            card.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="nsew")
            kpi_frame.grid_columnconfigure(i, weight=1)
            inner = tk.Frame(card, bg=COLORS["card"], padx=12, pady=10)
            inner.pack(fill=tk.BOTH, expand=True)
            tk.Label(inner, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(anchor=tk.W)
            val = tk.Label(inner, text="-", bg=COLORS["card"], fg=COLORS["text"], font=FONT_STAT)
            val.pack(anchor=tk.W, pady=(4, 0))
            self._kpi_labels[key] = val

        leave_frame = ttk.LabelFrame(self, text="  연차 · 무급/결근  ", padding=8)
        leave_frame.pack(fill=tk.BOTH, expand=True)
        leave_frame.grid_rowconfigure(0, weight=1)
        leave_frame.grid_columnconfigure(0, weight=1)

        cols = ("name", "affiliate", "workplace", "leave", "unpaid", "memo")
        self.leave_tree = ttk.Treeview(leave_frame, columns=cols, show="headings", height=10)
        for key, title, width in [
            ("name", "성명", 90),
            ("affiliate", "계열사", 90),
            ("workplace", "사업장", 100),
            ("leave", "연차", 52),
            ("unpaid", "무급", 52),
            ("memo", "내역", 160),
        ]:
            self.leave_tree.heading(key, text=title)
            self.leave_tree.column(key, width=width, minwidth=48, anchor=tk.W)
        scroll = ttk.Scrollbar(leave_frame, orient=tk.VERTICAL, command=self.leave_tree.yview)
        self.leave_tree.configure(yscrollcommand=scroll.set)
        self.leave_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        note = tk.Label(
            self,
            text="연차사용대장은 전 계열사·사업장 통합으로 관리됩니다. 「연차대장 열기」로 전체 내역을 확인하세요.",
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=520,
            justify=tk.LEFT,
        )
        note.pack(fill=tk.X, pady=(8, 0))

    def load(
        self,
        period: str,
        summary: MonthSummary | None,
        records: list,
        selection: OrgSelection | None = None,
        comparison_status: str = "",
    ) -> None:
        self._summary = summary
        self._records = records or []
        self._selection = selection or OrgSelection()
        self._comparison_status = comparison_status
        self._redraw(period)

    def _fmt_man(self, won: int) -> str:
        if won >= 10_000:
            return f"{won / 10_000:,.0f}만"
        return f"{won:,}"

    def _redraw(self, period: str) -> None:
        filtered = filter_records(self._records, self._selection)
        sm = summarize_records(filtered)

        self._comp_status.configure(
            text=self._comparison_status or "전월 대비 급여차이 보고서 정보가 없습니다."
        )

        if not filtered:
            for lbl in self._kpi_labels.values():
                lbl.configure(text="-")
            for item in self.leave_tree.get_children():
                self.leave_tree.delete(item)
            return

        self._kpi_labels["count"].configure(text=f"{sm.employee_count}명")
        self._kpi_labels["gross"].configure(text=self._fmt_man(sm.total_gross))
        self._kpi_labels["net"].configure(text=self._fmt_man(sm.total_net))
        self._kpi_labels["leave"].configure(text=f"{sm.leave_users}명")
        self._kpi_labels["absence"].configure(text=f"{sm.absence_users}명")

        for item in self.leave_tree.get_children():
            self.leave_tree.delete(item)

        leave_rows = [
            r for r in filtered if float(r.get("leave_days") or 0) > 0 or float(r.get("unpaid_days") or 0) > 0
        ]
        for r in sorted(leave_rows, key=lambda x: str(x.get("name") or "")):
            self.leave_tree.insert(
                "",
                tk.END,
                values=(
                    r.get("name", ""),
                    r.get("affiliate", ""),
                    r.get("workplace", ""),
                    r.get("leave_days", 0) if float(r.get("leave_days") or 0) > 0 else "-",
                    r.get("unpaid_days", 0) if float(r.get("unpaid_days") or 0) > 0 else "-",
                    r.get("leave_usage_display") or "",
                ),
            )

        if not leave_rows:
            self.leave_tree.insert("", tk.END, values=("해당 없음", "-", "-", "-", "-", f"{format_period_display(period)}"))
