"""
ui/leave_ledger_panel.py - 연차사용대장 일별 사용내역 뷰어
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from leave_calendar_marks import (
    build_marks_from_row,
    format_legend_text,
    format_usage_dates_summary,
    render_month_calendar_block,
    render_month_day_header,
    render_month_mark_row,
)
from leave_usage_ledger import get_leave_usage_ledger_path, normalize_period_label
from payroll_archive import format_period_display
from services.monthly_leave_manager import filtered_leave_rows
from services.org_registry import OrgSelection
from ui.theme import COLORS, FONT


class LeaveLedgerViewerDialog:
    """연차사용대장 — 월별 일자 그리드(● ◐ ✕) 표시."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        period: str = "",
        records: list[dict[str, Any]] | None = None,
        selection: OrgSelection | None = None,
    ) -> None:
        self._parent = parent
        self._period = normalize_period_label(period) or period or ""
        self._records = records or []
        self._selection = selection or OrgSelection()
        self._only_usage = tk.BooleanVar(value=True)
        self._detail_var = tk.StringVar(value="직원을 선택하면 일별 사용내역이 표시됩니다.")
        self._row_cache: dict[str, dict[str, Any]] = {}

        self.win = tk.Toplevel(parent)
        self.win.title("연차사용대장 — 사용내역")
        self.win.transient(parent)
        self.win.geometry("980x620")
        self.win.minsize(820, 480)

        self._build()
        self._redraw()

    def _build(self) -> None:
        top = ttk.Frame(self.win, padding=(12, 10, 12, 6))
        top.pack(fill=tk.X)

        period_txt = format_period_display(self._period) if self._period else "급여월 미선택"
        tk.Label(
            top,
            text=f"{period_txt} · 일별 연차·결근 표시",
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 10, "bold"),
            padx=12,
            pady=8,
        ).pack(fill=tk.X, pady=(0, 8))

        toolbar = ttk.Frame(top)
        toolbar.pack(fill=tk.X)
        ttk.Checkbutton(
            toolbar,
            text="연차·결근 있는 인원만",
            variable=self._only_usage,
            command=self._redraw,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(toolbar, text="Excel 파일 열기", command=self._open_excel).pack(side=tk.LEFT)

        tk.Label(
            top,
            text=format_legend_text(),
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Consolas", 9),
            wraplength=920,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(8, 0))

        paned = ttk.Panedwindow(self.win, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=3)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        cols = (
            "name",
            "workplace",
            "month_leave",
            "dates_summary",
            "absence_days",
            "remaining",
        )
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        headings = {
            "name": ("성명", 88),
            "workplace": ("사업장·소속", 110),
            "month_leave": ("당월 연차", 68),
            "dates_summary": ("사용일자", 280),
            "absence_days": ("무급/결근", 68),
            "remaining": ("잔여", 52),
        }
        for key, (title, width) in headings.items():
            self.tree.heading(key, text=title)
            anchor = tk.W
            if key in ("month_leave", "absence_days", "remaining"):
                anchor = tk.E
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=(key == "dates_summary"))

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.tag_configure("dates", font=(FONT, 9))

        detail_frame = ttk.LabelFrame(paned, text="  선택 직원 · 사용내역  ", padding=10)
        paned.add(detail_frame, weight=1)

        self._day_header = tk.Label(
            detail_frame,
            text="",
            anchor=tk.W,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Consolas", 9),
            justify=tk.LEFT,
        )
        self._day_header.pack(fill=tk.X, pady=(0, 4))

        self._day_marks = tk.Label(
            detail_frame,
            text="",
            anchor=tk.W,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Consolas", 11),
            justify=tk.LEFT,
        )
        self._day_marks.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            detail_frame,
            textvariable=self._detail_var,
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=900,
            justify=tk.LEFT,
        ).pack(fill=tk.X)

        btn_row = ttk.Frame(self.win, padding=(12, 0, 12, 12))
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="닫기", command=self.win.destroy).pack(side=tk.RIGHT)

    def _open_excel(self) -> None:
        import os

        path = get_leave_usage_ledger_path()
        if not path.is_file():
            messagebox.showinfo("안내", "연차사용대장 Excel 파일이 아직 없습니다.", parent=self.win)
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _rows(self) -> list[dict[str, Any]]:
        if not self._period:
            return []
        return filtered_leave_rows(
            self._period,
            self._records,
            self._selection,
            only_with_usage=self._only_usage.get(),
        )

    def _redraw(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_cache.clear()

        rows = self._rows()

        if not self._period:
            self._detail_var.set("급여월을 선택한 뒤 다시 열어 주세요.")
            return

        for r in rows:
            name = str(r.get("name") or "")
            ml = float(r.get("month_leave") or 0)
            ad = float(r.get("absence_days") or 0)
            rem = r.get("remaining")
            rem_txt = f"{float(rem):g}" if rem not in (None, "", 0, 0.0) else "-"
            marks = build_marks_from_row(r, self._period)
            dates_txt = r.get("dates_summary") or format_usage_dates_summary(self._period, marks)
            iid = self.tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    r.get("workplace", ""),
                    f"{ml:g}일" if ml > 0 else "-",
                    dates_txt or "-",
                    f"{ad:g}일" if ad > 0 else "-",
                    rem_txt,
                ),
                tags=("dates",),
            )
            self._row_cache[iid] = r

        if rows:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self._show_detail(self._row_cache[first])
        else:
            self._detail_var.set("표시할 연차·결근 내역이 없습니다.")
            self._day_header.configure(text="")
            self._day_marks.configure(text="")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        row = self._row_cache.get(sel[0])
        if row:
            self._show_detail(row)

    def _show_detail(self, row: dict[str, Any]) -> None:
        marks = build_marks_from_row(row, self._period)
        self._day_header.configure(text=render_month_day_header(self._period))
        self._day_marks.configure(text=render_month_mark_row(self._period, marks))
        block = render_month_calendar_block(self._period, marks)
        memo_parts = []
        lm = str(row.get("leave_memo") or "").strip()
        am = str(row.get("absence_memo") or "").strip()
        if lm:
            memo_parts.append(f"연차: {lm}")
        if am:
            memo_parts.append(f"결근/무급: {am}")
        memo = " · ".join(memo_parts)
        self._detail_var.set(f"{row.get('name', '')} — {memo or '메모 없음'}\n{block}")


def show_leave_ledger_viewer(
    parent: tk.Misc,
    *,
    period: str = "",
    records: list[dict[str, Any]] | None = None,
    selection: OrgSelection | None = None,
) -> LeaveLedgerViewerDialog:
    return LeaveLedgerViewerDialog(
        parent,
        period=period,
        records=records,
        selection=selection,
    )
