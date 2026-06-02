"""
ui/revision_history_panel.py - Excel 수정 이력 (임원 확인용)
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from services.file_revision import FileRevision, list_all_revisions_for_scope
from services.payroll_scope import PayrollScope
from ui.theme import COLORS, FONT, FONT_BODY


class RevisionHistoryPanel(ttk.LabelFrame):
    """수정 사유·변경 내용 이력."""

    def __init__(self, parent, **kwargs) -> None:
        kwargs.setdefault("text", "  Excel 수정 이력  ")
        kwargs.setdefault("padding", 8)
        super().__init__(parent, **kwargs)
        self._revisions: list[FileRevision] = []

        self._summary = tk.Label(
            self,
            text="수정 업로드 이력이 없습니다.",
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=520,
            justify=tk.LEFT,
        )
        self._summary.pack(fill=tk.X, pady=(0, 8))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = ("when", "file", "reason", "changes")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=5)
        for key, title, width in [
            ("when", "일시", 110),
            ("file", "파일", 88),
            ("reason", "수정 사유", 180),
            ("changes", "변경", 120),
        ]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=60, anchor=tk.W)
        scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_detail())

        detail_frame = ttk.LabelFrame(self, text="  변경 상세  ", padding=6)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        text_wrap = tk.Frame(detail_frame)
        text_wrap.pack(fill=tk.BOTH, expand=True)
        dscroll = ttk.Scrollbar(text_wrap, orient=tk.VERTICAL)
        self.detail = tk.Text(
            text_wrap,
            height=6,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg="#FAFBFC",
            fg=COLORS["text"],
            yscrollcommand=dscroll.set,
        )
        dscroll.config(command=self.detail.yview)
        self.detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail.configure(state=tk.DISABLED)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="수정 전 파일", command=lambda: self._open_selected("before")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="수정 후 파일", command=lambda: self._open_selected("after")).pack(side=tk.LEFT)

    def load(self, scope: PayrollScope | None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.detail.configure(state=tk.NORMAL)
        self.detail.delete("1.0", tk.END)
        self.detail.configure(state=tk.DISABLED)

        if not scope:
            self._summary.configure(text="급여 대상을 선택하면 수정 이력을 확인할 수 있습니다.")
            self._revisions = []
            return

        self._revisions = list_all_revisions_for_scope(scope)
        if not self._revisions:
            self._summary.configure(
                text=f"{scope.display_label()} — Excel 수정 업로드 이력이 없습니다."
            )
            return

        self._summary.configure(
            text=f"{scope.display_label()} — 수정 {len(self._revisions)}건 (사유·변경 내용은 아래에서 확인)"
        )
        for i, rev in enumerate(self._revisions):
            self.tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    rev.replaced_at_display or rev.replaced_at[:16],
                    rev.file_label,
                    rev.reason[:80] + ("…" if len(rev.reason) > 80 else ""),
                    rev.change_summary,
                ),
            )
        if self._revisions:
            self.tree.selection_set("0")
            self._show_detail()

    def _selected_revision(self) -> FileRevision | None:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        if 0 <= idx < len(self._revisions):
            return self._revisions[idx]
        return None

    def _show_detail(self) -> None:
        rev = self._selected_revision()
        self.detail.configure(state=tk.NORMAL)
        self.detail.delete("1.0", tk.END)
        if not rev:
            self.detail.configure(state=tk.DISABLED)
            return
        lines = [
            f"파일: {rev.file_label} ({rev.file_name})",
            f"일시: {rev.replaced_at_display or rev.replaced_at}",
            f"수정 사유: {rev.reason}",
            "",
            f"변경 요약: {rev.change_summary}",
            "",
            "변경 상세:",
        ]
        if rev.change_details:
            lines.extend(f"  · {d}" for d in rev.change_details)
        else:
            lines.append("  · (자동 비교 결과 없음)")
        self.detail.insert("1.0", "\n".join(lines))
        self.detail.configure(state=tk.DISABLED)

    def _open_selected(self, which: str) -> None:
        rev = self._selected_revision()
        if not rev:
            messagebox.showinfo("안내", "이력을 먼저 선택하세요.")
            return
        path = rev.before_path if which == "before" else rev.after_path
        if not path.is_file():
            messagebox.showwarning("파일 없음", "보관된 파일을 찾을 수 없습니다.")
            return
        os.startfile(str(path))  # type: ignore[attr-defined]
