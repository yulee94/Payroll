"""
ui/spreadsheet_filter_popup.py - 열 헤더 클릭 시 체크박스 필터 팝업
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ui.theme import COLORS, FONT


class ColumnFilterPopup(tk.Toplevel):
    """Excel 유사 열 필터 — 체크박스로 값 선택."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        column_label: str,
        values: list[str],
        selected: set[str],
        on_apply: Callable[[set[str] | None], None],
    ) -> None:
        root = parent.winfo_toplevel()
        super().__init__(root)
        self._values = list(values)
        self._on_apply = on_apply
        self._vars: dict[str, tk.BooleanVar] = {}

        self.title(f"{column_label} 필터")
        self.configure(bg=COLORS["bg"])
        self.transient(root)
        self.resizable(False, True)
        self.geometry("320x420")
        try:
            px = parent.winfo_rootx() + 24
            py = parent.winfo_rooty() + parent.winfo_height() + 8
            self.geometry(f"+{px}+{py}")
        except tk.TclError:
            pass

        head = tk.Frame(self, bg=COLORS["bg"], padx=14, pady=10)
        head.pack(fill=tk.X)
        tk.Label(
            head,
            text=column_label,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            head,
            text="표시할 항목을 선택하세요.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor=tk.W, pady=(4, 0))

        tool = tk.Frame(self, bg=COLORS["bg"], padx=14)
        tool.pack(fill=tk.X)
        tk.Button(
            tool,
            text="전체 선택",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 8),
            command=self._select_all,
        ).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(
            tool,
            text="전체 해제",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 8),
            command=self._clear_all,
        ).pack(side=tk.LEFT)

        search_row = tk.Frame(self, bg=COLORS["bg"], padx=14)
        search_row.pack(fill=tk.X, pady=(8, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_search())
        ttk.Entry(search_row, textvariable=self._search_var, font=(FONT, 9)).pack(fill=tk.X)

        list_wrap = tk.Frame(self, bg=COLORS["bg"], padx=14)
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        canvas = tk.Canvas(list_wrap, bg="#FFFFFF", highlightthickness=1, highlightbackground=COLORS["border"])
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=canvas.yview)
        self._inner = tk.Frame(canvas, bg="#FFFFFF")
        self._inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._inner, anchor=tk.NW, width=288)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = canvas
        self._checkbox_rows: list[tuple[tk.Checkbutton, str]] = []

        init = set(selected) if selected else set(values)
        for val in values:
            var = tk.BooleanVar(value=val in init)
            self._vars[val] = var
            cb = tk.Checkbutton(
                self._inner,
                text=val,
                variable=var,
                bg="#FFFFFF",
                anchor=tk.W,
                font=(FONT, 9),
                padx=8,
                pady=2,
            )
            cb.pack(fill=tk.X)
            self._checkbox_rows.append((cb, val))

        foot = tk.Frame(self, bg=COLORS["bg"], padx=14, pady=10)
        foot.pack(fill=tk.X)
        tk.Button(
            foot,
            text="필터 해제",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 9),
            command=self._clear_filter,
        ).pack(side=tk.LEFT)
        tk.Button(
            foot,
            text="취소",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 9),
            padx=12,
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(
            foot,
            text="적용",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            font=(FONT, 9, "bold"),
            padx=14,
            command=self._apply,
        ).pack(side=tk.RIGHT)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.lift()
        self.focus_force()
        self.after(50, self.lift)

    def _select_all(self) -> None:
        for var in self._vars.values():
            var.set(True)

    def _clear_all(self) -> None:
        for var in self._vars.values():
            var.set(False)

    def _apply_search(self) -> None:
        q = self._search_var.get().strip().lower()
        for cb, val in self._checkbox_rows:
            if not q or q in val.lower():
                cb.pack(fill=tk.X)
            else:
                cb.pack_forget()

    def _apply(self) -> None:
        chosen = {val for val, var in self._vars.items() if var.get()}
        if not chosen or len(chosen) == len(self._values):
            self._on_apply(None)
        else:
            self._on_apply(chosen)
        self.destroy()

    def _clear_filter(self) -> None:
        self._on_apply(None)
        self.destroy()
