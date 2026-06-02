"""
ui/file_replace_dialog.py - Excel 수정본 업로드·대체 확인
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from core.labels import label_for_filename
from services.file_revision import FileRevision, is_replaceable_file, replace_file_with_revision
from services.payroll_scope import PayrollScope
from ui.theme import COLORS, FONT, FONT_BODY


class FileReplaceDialog(tk.Toplevel):
    """수정본 업로드 + 수정 사유 입력."""

    def __init__(self, parent, scope: PayrollScope, target_path: Path) -> None:
        super().__init__(parent)
        self.title("수정본 업로드")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self._scope = scope
        self._target_path = target_path
        self._result: FileRevision | None = None
        self._upload_path: Path | None = None

        pad = ttk.Frame(self, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        ttk.Label(pad, text="Excel 수정본으로 파일 대체", font=(FONT, 11, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=f"대상: {label_for_filename(target_path.name)}  ·  {scope.display_label()}",
            font=(FONT, 9),
            foreground=COLORS["muted"],
        ).pack(anchor=tk.W, pady=(4, 10))

        warn = tk.Label(
            pad,
            text=(
                "기존 파일은 수정 이력에 자동 보관됩니다.\n"
                "임원 보고용으로 수정 사유와 변경 내용이 기록됩니다."
            ),
            anchor=tk.W,
            justify=tk.LEFT,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=10,
            pady=8,
            wraplength=440,
        )
        warn.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pad, text="수정 사유 (필수)", font=(FONT, 9, "bold")).pack(anchor=tk.W)
        reason_wrap = tk.Frame(pad)
        reason_wrap.pack(fill=tk.X, pady=(4, 10))
        scroll = ttk.Scrollbar(reason_wrap, orient=tk.VERTICAL)
        self._reason = tk.Text(
            reason_wrap,
            height=4,
            width=52,
            font=FONT_BODY,
            wrap=tk.WORD,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self._reason.yview)
        self._reason.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._reason.insert("1.0", "예: OT 시간 오입력 수정, 직책수당 반영 등")

        file_row = ttk.Frame(pad)
        file_row.pack(fill=tk.X, pady=(0, 10))
        self._file_label = ttk.Label(file_row, text="수정본 파일: 선택되지 않음", font=(FONT, 9))
        self._file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_row, text="파일 선택…", command=self._pick_file).pack(side=tk.RIGHT)

        btn_row = ttk.Frame(pad)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="취소", command=self._cancel).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="업로드하여 대체", command=self._submit).pack(side=tk.RIGHT)

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        self.wait_window()

    @property
    def revision(self) -> FileRevision | None:
        return self._result

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="수정본 Excel 선택",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")],
            parent=self,
        )
        if not path:
            return
        self._upload_path = Path(path)
        self._file_label.configure(text=f"수정본 파일: {self._upload_path.name}")

    def _submit(self) -> None:
        reason = self._reason.get("1.0", tk.END).strip()
        if len(reason) < 2 or reason.startswith("예:"):
            messagebox.showwarning("수정 사유", "수정 사유를 구체적으로 입력해 주세요.", parent=self)
            return
        if not self._upload_path or not self._upload_path.is_file():
            messagebox.showwarning("파일 선택", "수정본 Excel 파일을 선택해 주세요.", parent=self)
            return
        if not is_replaceable_file(self._target_path):
            messagebox.showwarning("안내", "이 파일은 수정 업로드를 지원하지 않습니다.", parent=self)
            return
        if not messagebox.askyesno(
            "대체 확인",
            f"「{label_for_filename(self._target_path.name)}」을(를) 수정본으로 대체합니다.\n\n"
            f"사유: {reason[:120]}{'…' if len(reason) > 120 else ''}\n\n"
            "기존 파일은 수정 이력에 보관됩니다. 계속하시겠습니까?",
            parent=self,
        ):
            return
        try:
            self._result = replace_file_with_revision(
                self._scope,
                self._target_path,
                self._upload_path,
                reason,
            )
            self.destroy()
        except (OSError, ValueError) as exc:
            messagebox.showerror("업로드 실패", str(exc), parent=self)

    def _cancel(self) -> None:
        self.destroy()
