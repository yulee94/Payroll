"""
ui/archive_folder_panel.py - 월별 자료함 폴더 탐색 (더블클릭 이동)
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Callable

from excel_writer import OUTPUT_DIR
from core.access_control import can_view_executive_payroll, filter_archive_entries_for_role, session_role
from core.session_service import get_session
from services.archive_browser import PARENT_ID, ArchiveBrowser, ArchiveEntry, ArchiveNavContext
from services.archive_storage import load_scope_manifest
from services.org_registry import OrgSelection
from ui.theme import COLORS, FONT


class ArchiveFolderPanel(ttk.Frame):
    """COSS → 계열사 → 사업장 → 급여월 → 파일/보고서 계층 탐색."""

    def __init__(
        self,
        parent,
        on_file_select: Callable[[ArchiveEntry | None], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._browser = ArchiveBrowser()
        self._on_file_select = on_file_select
        self._select_job: str | None = None
        self._suppress_select = False

        self._path_label = tk.Label(
            self,
            text="",
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=10,
            pady=6,
        )
        self._path_label.pack(fill=tk.X, pady=(0, 8))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = ("name", "kind", "hint")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="이름")
        self.tree.heading("kind", text="구분")
        self.tree.heading("hint", text="설명")
        self.tree.column("name", width=200, minwidth=120)
        self.tree.column("kind", width=72, minwidth=56)
        self.tree.column("hint", width=180, minwidth=100)
        scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<MouseWheel>", self._on_tree_mousewheel)

    def _on_tree_mousewheel(self, event) -> None:
        self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

        tk.Label(
            self,
            text="폴더는 더블클릭 · 「..」 로 상위 이동 · 파일은 클릭 시 미리보기",
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).pack(fill=tk.X, pady=(8, 0))

    @property
    def browser(self) -> ArchiveBrowser:
        return self._browser

    def refresh(self, selection: OrgSelection | None = None, period: str = "") -> None:
        if selection is not None:
            self._browser.reset(selection)
        if period:
            self._open_period(period)
        self._redraw()

    def _open_period(self, period_or_key: str) -> None:
        from services.payroll_scope import PayrollScope
        from services.archive_storage import load_scope_manifest

        scope = PayrollScope.try_parse_key(period_or_key)
        if not scope:
            return
        manifest = load_scope_manifest(scope)
        affiliate = str(manifest.get("affiliate") or scope.affiliate).strip()
        workplace = str(manifest.get("workplace") or scope.workplace).strip()
        if not affiliate or not workplace:
            return
        self._browser._stack = [
            ArchiveNavContext(level="group"),
            ArchiveNavContext(level="affiliate", affiliate=affiliate),
            ArchiveNavContext(level="workplace", affiliate=affiliate, workplace=workplace),
            ArchiveNavContext(
                level="period",
                affiliate=affiliate,
                workplace=workplace,
                period=scope.period,
            ),
        ]

    def _redraw(self) -> None:
        self._path_label.configure(text=self._browser.breadcrumb())
        prev_sel = self.tree.selection()
        if self._select_job is not None:
            try:
                self.after_cancel(self._select_job)
            except Exception:
                pass
            self._select_job = None

        self._suppress_select = True
        entries: list[ArchiveEntry] = []
        try:
            self.tree.unbind("<<TreeviewSelect>>")
            for item in self.tree.get_children():
                self.tree.delete(item)
            entries = filter_archive_entries_for_role(
                self._browser.list_entries(),
                session=get_session(),
            )
            if (
                self._browser.context.level == "period"
                and not can_view_executive_payroll(session_role(get_session()))
                and not any(e.kind == "payroll" for e in entries)
            ):
                entries = [
                    ArchiveEntry(
                        entry_id="__notice_exec__",
                        name="(임원 포함 급여 Excel은 재무팀·관리자만 열람)",
                        kind="folder",
                        navigable=False,
                        hint="월별·사업장 내역 탭에서 일반 직원 급여를 확인하세요",
                    ),
                    *entries,
                ]
            kind_label = {
                "parent": "상위",
                "affiliate": "계열사",
                "workplace": "사업장",
                "period": "급여월",
                "folder": "폴더",
                "payroll": "급여",
                "invoice": "청구서",
                "report": "보고",
                "leave": "연차",
            }
            rows = [
                (
                    entry.entry_id,
                    (entry.name, kind_label.get(entry.kind, entry.kind), entry.hint),
                )
                for entry in entries
            ]
            for iid, values in rows:
                self.tree.insert("", tk.END, iid=iid, values=values)
        finally:
            self.tree.bind("<<TreeviewSelect>>", self._on_select)
            self._suppress_select = False

        if not entries:
            return
        # 기존 선택 유지 (가능하면)
        if prev_sel and any(e.entry_id == prev_sel[0] for e in entries):
            self.tree.selection_set(prev_sel[0])
            return
        # 자동 미리보기로 인한 Excel 파싱(버벅임)을 줄이기 위해,
        # 첫 항목만 선택하고 미리보기는 사용자가 클릭할 때만 실행합니다.
        self.tree.selection_set(entries[0].entry_id)
        if self._on_file_select:
            self._on_file_select(None)

    def _on_select(self, _event=None) -> None:
        if self._suppress_select:
            return
        # 연속 클릭 시 미리보기(Excel 파싱)가 겹치지 않도록 디바운스
        if self._select_job is not None:
            try:
                self.after_cancel(self._select_job)
            except Exception:
                pass
        self._select_job = self.after(140, self._emit_select)

    def _emit_select(self) -> None:
        self._select_job = None
        if not self._on_file_select:
            return
        sel = self.tree.selection()
        if not sel:
            self._on_file_select(None)
            return
        entry = self._browser.get_entry(sel[0])
        if (
            entry
            and entry.kind == "payroll"
            and not can_view_executive_payroll(session_role(get_session()))
        ):
            self._on_file_select(None)
            return
        if entry and entry.path and not entry.navigable:
            self._on_file_select(entry)
        else:
            self._on_file_select(None)

    def _on_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        entry_id = sel[0]
        if entry_id == PARENT_ID:
            self._browser.go_up()
            self._redraw()
            return
        entry = self._browser.get_entry(entry_id)
        if not entry:
            return
        if entry.navigable:
            self._browser.enter(entry)
            self._redraw()
        elif entry.path:
            self._emit_select()

    def open_selected_file(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        entry = self._browser.get_entry(sel[0])
        if (
            entry
            and entry.kind == "payroll"
            and not can_view_executive_payroll(session_role(get_session()))
        ):
            from tkinter import messagebox

            messagebox.showwarning(
                "권한",
                "급여대장·명세서·지급내역에는 임원 급여가 포함되어 있습니다. "
                "재무팀 또는 관리자 권한이 필요합니다.",
            )
            return
        if entry and entry.path:
            os.startfile(str(entry.path))  # type: ignore[attr-defined]

    def open_current_folder(self) -> None:
        ctx = self._browser.context
        if ctx.period:
            path = OUTPUT_DIR / ctx.period
        else:
            path = OUTPUT_DIR
        os.startfile(str(path))  # type: ignore[attr-defined]
