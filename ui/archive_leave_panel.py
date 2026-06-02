"""
ui/archive_leave_panel.py - 월별 자료함 · 연차 소진·결근 관리
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from leave_calendar_marks import build_marks_from_row, format_legend_text, format_usage_dates_summary
from services.monthly_leave_manager import filtered_leave_rows, sync_monthly_leave_to_ledger
from services.org_registry import ALL_LABEL, OrgSelection, filter_records, summarize_records
from services.payroll_scope import discover_scopes
from payroll_archive import format_period_display
from ui.leave_ledger_panel import show_leave_ledger_viewer
from ui.theme import COLORS, FONT


class ArchiveLeavePanel(ttk.Frame):
    """선택 급여월의 연차 소진·결근 내역 표시 및 연차대장 반영."""

    def __init__(self, parent, on_synced=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._on_synced = on_synced
        self._period = ""
        self._records: list = []
        self._selection = OrgSelection()
        self._only_usage = tk.BooleanVar(value=False)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Checkbutton(
            toolbar,
            text="연차·결근 있는 인원만",
            variable=self._only_usage,
            command=self._redraw,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(toolbar, text="청구서 연차시트 → 대장 반영", command=self._sync_ledger).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(toolbar, text="사용내역 보기", command=self._open_usage_viewer).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="연차대장 Excel", command=self._open_ledger).pack(side=tk.LEFT)

        self._summary = tk.Label(
            self,
            text="급여월을 선택하면 당월 연차 소진·결근 내역이 표시됩니다.",
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=12,
            pady=8,
            wraplength=720,
            justify=tk.LEFT,
        )
        self._summary.pack(fill=tk.X, pady=(0, 8))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = (
            "name",
            "workplace",
            "month_leave",
            "dates_summary",
            "absence_days",
            "remaining",
        )
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings")
        headings = {
            "name": ("성명", 88),
            "workplace": ("사업장·소속", 120),
            "month_leave": ("당월 연차", 72),
            "dates_summary": ("사용일자", 260),
            "absence_days": ("무급/결근", 72),
            "remaining": ("잔여 연차", 72),
        }
        for key, (title, width) in headings.items():
            self.tree.heading(key, text=title)
            anchor = tk.W if key in ("name", "workplace", "dates_summary") else tk.E
            self.tree.column(key, width=width, minwidth=48, anchor=anchor, stretch=(key == "dates_summary"))
        self.tree.tag_configure("dates", font=(FONT, 9))

        scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<MouseWheel>", self._on_wheel)

        note = tk.Label(
            self,
            text=(
                f"{format_legend_text()}  ·  "
                "「청구서 연차시트 → 대장 반영」: 저장된 도급비 청구서의 연차 시트를 읽어 "
                "연차사용대장(월별현황 양식)과 사업장별 Excel을 갱신합니다."
            ),
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=720,
            justify=tk.LEFT,
        )
        note.pack(fill=tk.X, pady=(8, 0))

    def _on_wheel(self, event) -> str:
        self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def load(self, period: str, records: list, selection: OrgSelection | None = None) -> None:
        self._period = period or ""
        self._records = records or []
        self._selection = selection or OrgSelection()
        self._redraw()

    def _redraw(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self._period:
            self._summary.configure(text="급여월을 선택하면 당월 연차 소진·결근 내역이 표시됩니다.")
            return

        rows = filtered_leave_rows(
            self._period,
            self._records,
            self._selection,
            only_with_usage=self._only_usage.get(),
        )
        filtered = filter_records(self._records, self._selection)
        sm = summarize_records(filtered)
        scope_parts = []
        if self._selection.affiliate != ALL_LABEL:
            scope_parts.append(self._selection.affiliate)
        if self._selection.workplace != ALL_LABEL:
            scope_parts.append(self._selection.workplace)
        scope = " · ".join(scope_parts) if scope_parts else "전체"

        self._summary.configure(
            text=(
                f"{format_period_display(self._period)} · {scope} — "
                f"표시 {len(rows)}명 / 전체 {sm.employee_count}명 · "
                f"연차 사용 {sm.leave_users}명 · 무급/결근 {sm.absence_users}명"
            )
        )

        for r in rows:
            ml = float(r.get("month_leave") or 0)
            ad = float(r.get("absence_days") or 0)
            rem = r.get("remaining")
            rem_txt = f"{float(rem):g}" if rem not in (None, "", 0, 0.0) else "-"
            marks = build_marks_from_row(r, self._period)
            dates_txt = r.get("dates_summary") or format_usage_dates_summary(self._period, marks)
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r.get("name", ""),
                    r.get("workplace", ""),
                    f"{ml:g}일" if ml > 0 else "-",
                    dates_txt or "-",
                    f"{ad:g}일" if ad > 0 else "-",
                    rem_txt if rem_txt != "-" else "-",
                ),
                tags=("dates",),
            )

    def _sync_ledger(self) -> None:
        if not self._period:
            messagebox.showinfo("안내", "급여월을 먼저 선택하세요.")
            return
        filtered = filter_records(self._records, self._selection)
        if not filtered:
            messagebox.showinfo("안내", "반영할 급여 데이터가 없습니다.")
            return
        try:
            from services.archive_storage import invoice_file_path
            from services.payroll_scope import discover_scopes

            scopes = [s for s in discover_scopes() if s.period == self._period]
            invoice_path = None
            if scopes:
                invoice_path = invoice_file_path(scopes[0])
            info = sync_monthly_leave_to_ledger(
                self._period,
                filtered,
                scopes=scopes,
                invoice_path=invoice_path,
            )
            n = int(info.get("summaries") or 0)
            exported = info.get("exported") or []
            msg = f"연차대장 월별현황 {n}명 반영 완료."
            if exported:
                msg += f"\n\n사업장별 파일 {len(exported)}건 저장."
            messagebox.showinfo("완료", msg)
            self._redraw()
            if self._on_synced:
                self._on_synced()
        except OSError as exc:
            messagebox.showerror("저장 실패", str(exc))

    def _open_usage_viewer(self) -> None:
        if not self._period:
            messagebox.showinfo("안내", "급여월을 먼저 선택하세요.")
            return
        show_leave_ledger_viewer(
            self.winfo_toplevel(),
            period=self._period,
            records=self._records,
            selection=self._selection,
        )

    def _open_ledger(self) -> None:
        from leave_usage_ledger import get_leave_usage_ledger_path
        import os

        path = get_leave_usage_ledger_path()
        if not path.is_file():
            messagebox.showinfo("안내", "연차사용대장 파일이 아직 없습니다.\n「연차대장 반영」을 실행해 주세요.")
            return
        os.startfile(str(path))  # type: ignore[attr-defined]
