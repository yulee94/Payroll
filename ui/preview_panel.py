"""
ui/preview_panel.py - 파일 미리보기 + Excel 내려받기 패널
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk

from services.file_revision import can_replace_at_scope
from services.payroll_scope import PayrollScope
from services.preview_export import PreviewData, copy_file_to, preview_file
from ui.file_replace_dialog import FileReplaceDialog
from ui.spreadsheet_grid import SpreadsheetGrid
from ui.theme import COLORS, FONT, FONT_BODY
from ui.user_display import (
    format_save_success,
    friendly_document_title,
    friendly_error,
    preview_status_line,
)


class FilePreviewPanel(ttk.LabelFrame):
    """선택 파일 미리보기 및 저장."""

    def __init__(self, parent, colors: dict[str, str] | None = None, **kwargs) -> None:
        kwargs.setdefault("text", "  미리보기  ")
        kwargs.setdefault("padding", 8)
        super().__init__(parent, **kwargs)
        self._colors = colors or COLORS
        self._current_path: Path | None = None
        self._current_period: str = ""
        self._scope: PayrollScope | None = None
        self._on_replaced = None
        self._sheet_names: list[str] = []
        self._load_token = 0
        self._pending_load_job: str | None = None
        self._preview_delay_ms = 200
        self._preview_base_info = ""
        self._filter_hint = ""

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        self.path_label = ttk.Label(
            toolbar,
            text="파일을 선택하면 표 형태로 표시됩니다.",
            font=(FONT, 10, "bold"),
            foreground=self._colors["text"],
        )
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toolbar, text="Excel 내려받기", command=self._download).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(toolbar, text="다른 이름 저장", command=self._save_as).pack(side=tk.RIGHT, padx=(6, 0))
        self._clear_filter_btn = ttk.Button(toolbar, text="필터 초기화", command=self._clear_grid_filters)
        self._clear_filter_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self._clear_filter_btn.pack_forget()
        # 수정본 업로드는 “해당 폴더(scope) 안의 현재 파일”일 때만 노출됩니다.
        self._replace_btn = ttk.Button(toolbar, text="수정본 업로드", command=self._replace_upload)
        self._replace_btn.pack_forget()

        meta = ttk.Frame(self)
        meta.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(meta, text="시트", font=(FONT, 9)).pack(side=tk.LEFT, padx=(0, 6))
        self._sheet_var = tk.StringVar()
        self._sheet_combo = ttk.Combobox(
            meta,
            textvariable=self._sheet_var,
            state="disabled",
            width=18,
            font=(FONT, 9),
        )
        self._sheet_combo.pack(side=tk.LEFT)
        self._sheet_combo.bind("<<ComboboxSelected>>", lambda _e: self._reload_sheet())

        self.info_label = tk.Label(
            self,
            text="",
            anchor=tk.W,
            bg=self._colors["accent_light"],
            fg=self._colors["accent"],
            font=(FONT, 9),
            padx=10,
            pady=5,
        )
        self.info_label.pack(fill=tk.X, pady=(0, 6))

        self._grid = SpreadsheetGrid(self, self._colors, on_filter_changed=self._on_grid_filter_changed)
        self._grid.pack(fill=tk.BOTH, expand=True)

        self._text_frame = ttk.Frame(self)
        text_wrap = tk.Frame(self._text_frame)
        text_wrap.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(text_wrap, orient=tk.VERTICAL)
        self.text = tk.Text(
            text_wrap,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg="#FAFBFC",
            fg=self._colors["text"],
            relief=tk.FLAT,
            padx=12,
            pady=10,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self.text.yview)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        for w in (text_wrap, self.text):
            w.bind("<MouseWheel>", self._on_text_mousewheel)

    def _on_text_mousewheel(self, event) -> None:
        self.text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def set_period(self, period: str) -> None:
        self._current_period = period or ""

    def set_scope(self, scope: PayrollScope | None) -> None:
        self._scope = scope
        self._update_replace_button()

    def set_on_replaced(self, callback) -> None:
        self._on_replaced = callback

    def _show_grid(self) -> None:
        self._text_frame.pack_forget()
        self._grid.pack(fill=tk.BOTH, expand=True)

    def _show_text(self) -> None:
        self._grid.pack_forget()
        self._text_frame.pack(fill=tk.BOTH, expand=True)

    def show_file(self, path: Path | None) -> None:
        self._cancel_pending_load()
        self._load_file_sync(path)

    def schedule_show_file(self, path: Path | None, delay_ms: int | None = None) -> None:
        """파일 선택 후 잠시 대기 → 로딩 표시 → 백그라운드에서 Excel 파싱."""
        self._cancel_pending_load()
        delay = self._preview_delay_ms if delay_ms is None else delay_ms

        if path is None or not path.exists():
            self._load_file_sync(None)
            return

        self._load_token += 1
        token = self._load_token
        self._show_loading(path)

        def _start() -> None:
            if token != self._load_token:
                return
            self._load_file_async(path, token)

        self._pending_load_job = self.after(delay, _start)

    def _cancel_pending_load(self) -> None:
        if self._pending_load_job is not None:
            try:
                self.after_cancel(self._pending_load_job)
            except Exception:
                pass
            self._pending_load_job = None
        self._load_token += 1

    def _show_loading(self, path: Path) -> None:
        self._current_path = path
        self._sheet_combo.configure(values=[], state="disabled")
        self._sheet_var.set("")
        self._grid.clear()
        self._show_grid()
        title = friendly_document_title(path, period=self._current_period)
        self.path_label.configure(text=f"{title} — 미리보기 준비 중…")
        self.info_label.configure(text="Excel 파일을 읽는 중입니다. 잠시만 기다려 주세요.")
        self._update_replace_button()

    def _load_file_sync(self, path: Path | None) -> None:
        self._current_path = path
        self._sheet_names = []
        self._sheet_combo.configure(values=[], state="disabled")
        self._sheet_var.set("")
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.info_label.configure(text="")
        self._grid.clear()

        if path is None or not path.exists():
            self.path_label.configure(text="파일을 선택하면 표 형태로 표시됩니다.")
            self._show_grid()
            self._update_replace_button()
            return

        self.path_label.configure(
            text=friendly_document_title(path, period=self._current_period)
        )
        data = preview_file(path)
        self._apply_preview(data)
        self._update_replace_button()

    def _load_file_async(self, path: Path, token: int) -> None:
        self._pending_load_job = None

        def worker() -> None:
            try:
                data = preview_file(path)
                err: str | None = None
            except Exception as exc:
                data = None
                err = str(exc)

            def apply() -> None:
                if token != self._load_token:
                    return
                if data is None:
                    self._current_path = path
                    self.path_label.configure(
                        text=friendly_document_title(path, period=self._current_period)
                    )
                    self._show_text()
                    self.text.configure(state=tk.NORMAL)
                    self.text.delete("1.0", tk.END)
                    msg = err or "미리보기를 불러오지 못했습니다."
                    self.text.insert("1.0", msg)
                    self.text.configure(state=tk.DISABLED)
                    self.info_label.configure(text="")
                    self._update_replace_button()
                    return
                self._current_path = path
                self.path_label.configure(
                    text=friendly_document_title(path, period=self._current_period)
                )
                self._apply_preview(data)
                self._update_replace_button()

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _update_replace_button(self) -> None:
        show = bool(
            self._scope
            and self._current_path
            and can_replace_at_scope(self._scope, self._current_path)
        )
        if show:
            self._replace_btn.pack(side=tk.RIGHT, padx=(6, 0))
        else:
            self._replace_btn.pack_forget()

    def _replace_upload(self) -> None:
        if not self._scope or not self._current_path:
            messagebox.showinfo("안내", "대체할 파일을 먼저 선택하세요.")
            return
        dialog = FileReplaceDialog(self.winfo_toplevel(), self._scope, self._current_path)
        if not dialog.revision:
            return
        self.show_file(self._current_path)
        if self._on_replaced:
            self._on_replaced(dialog.revision)

    def _reload_sheet(self) -> None:
        if not self._current_path:
            return
        sheet = self._sheet_var.get().strip()
        if not sheet:
            return
        self._load_token += 1
        token = self._load_token
        path = self._current_path
        prev_info = self._preview_base_info
        self.info_label.configure(text="시트를 불러오는 중입니다. 잠시만 기다려 주세요.")
        if self._sheet_names:
            self._sheet_combo.configure(state="disabled")

        def worker() -> None:
            try:
                data = preview_file(path, sheet_name=sheet)
                err: str | None = None
            except Exception as exc:
                data = None
                err = str(exc)

            def apply() -> None:
                if token != self._load_token:
                    return
                if data is None:
                    self.info_label.configure(text=err or "시트를 불러오지 못했습니다.")
                    if self._sheet_names:
                        self._sheet_combo.configure(state="readonly")
                    return
                self._apply_preview(data, keep_sheet=True)
                if self._sheet_names:
                    self._sheet_combo.configure(state="readonly")

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _on_grid_filter_changed(self, summary: str) -> None:
        self._filter_hint = summary
        if self._grid.has_active_filters:
            self._clear_filter_btn.pack(side=tk.RIGHT, padx=(6, 0))
        else:
            self._clear_filter_btn.pack_forget()
        self._refresh_info_label()

    def _clear_grid_filters(self) -> None:
        self._grid.clear_filters()

    def _refresh_info_label(self) -> None:
        if self._filter_hint:
            text = f"{self._preview_base_info}  ·  {self._filter_hint}" if self._preview_base_info else self._filter_hint
        else:
            text = self._preview_base_info
        self.info_label.configure(text=text)

    def _update_preview_info(self, data: PreviewData) -> None:
        row_count = len([r for r in data.grid_rows if r.role not in ("empty",)])
        self._preview_base_info = preview_status_line(
            sheet=data.active_sheet,
            truncated=data.truncated,
            truncated_cols=getattr(data, "truncated_cols", False),
            row_count=row_count,
        )
        if self._grid.has_filterable_columns(data):
            hint = "열 헤더(▼) 클릭 → 체크박스로 계열사·사업장 등 필터"
            self._preview_base_info = f"{self._preview_base_info}  ·  {hint}" if self._preview_base_info else hint
        self._filter_hint = ""
        self._refresh_info_label()
        self._clear_filter_btn.pack_forget()

    def _apply_preview(self, data: PreviewData, keep_sheet: bool = False) -> None:
        if data.kind in ("excel", "csv") and data.grid_rows:
            self._show_grid()
            self._grid.load(data)

            if data.sheet_names and len(data.sheet_names) > 1:
                self._sheet_names = data.sheet_names
                self._sheet_combo.configure(values=data.sheet_names, state="readonly")
                if not keep_sheet:
                    self._sheet_var.set(data.active_sheet or data.sheet_names[0])
            else:
                self._sheet_combo.configure(values=[], state="disabled")
                self._sheet_var.set("")

            self._update_preview_info(data)
            return

        self._show_text()
        self._sheet_combo.configure(values=[], state="disabled")
        if data.kind == "unsupported":
            self.text.insert("1.0", data.text or "이 형식은 미리보기를 지원하지 않습니다.\nExcel에서 열어 확인해 주세요.")
        else:
            self.text.insert("1.0", data.text or "표시할 내용이 없습니다.")
        self.text.configure(state=tk.DISABLED)
        self.info_label.configure(text="")

    def _download(self) -> None:
        if not self._current_path or not self._current_path.exists():
            messagebox.showinfo("안내", "내려받을 파일을 먼저 선택하세요.")
            return
        dest = filedialog.asksaveasfilename(
            title="Excel 내려받기",
            defaultextension=self._current_path.suffix,
            initialfile=self._current_path.name,
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("All", "*.*")],
        )
        if not dest:
            return
        try:
            copy_file_to(Path(dest), self._current_path)
            messagebox.showinfo("완료", format_save_success(dest))
        except OSError as exc:
            messagebox.showerror("저장 실패", friendly_error(exc))

    def _save_as(self) -> None:
        self._download()
