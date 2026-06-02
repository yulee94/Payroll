"""
ui/upload_confirm_dialog.py - 청구서 업로드 전 계열사·사업장·월 확인
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from core.org_config import (
    canonical_scope_workplace,
    get_default_affiliate,
    list_config_affiliates,
    list_config_workplaces,
)
from payroll_archive import format_period_display
from services.payroll_scope import PayrollScope
from ui.theme import COLORS, FONT, FONT_BODY

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


class UploadConfirmDialog(tk.Toplevel):
    """업로드 전 법인(계열사)·사업장·급여월 확인."""

    def __init__(
        self,
        parent,
        invoice_name: str,
        suggested: PayrollScope,
        on_workplaces: Callable[[str], list[str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("청구서 업로드 확인")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self._result: PayrollScope | None = None
        self._on_workplaces = on_workplaces or list_config_workplaces

        pad = ttk.Frame(self, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            pad,
            text="아래 법인·사업장·급여월이 맞는지 확인해 주세요.",
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=f"파일: {invoice_name}",
            font=(FONT, 9),
            foreground=COLORS["muted"],
        ).pack(anchor=tk.W, pady=(4, 12))

        form = ttk.Frame(pad)
        form.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(form, text="계열사 (법인)", width=14).grid(row=0, column=0, sticky=tk.W, pady=4)
        self._aff_var = tk.StringVar(value=suggested.affiliate or get_default_affiliate())
        affs = list_config_affiliates() or [get_default_affiliate()]
        self._aff_combo = ttk.Combobox(form, textvariable=self._aff_var, values=affs, state="readonly", width=28)
        self._aff_combo.grid(row=0, column=1, sticky=tk.W, pady=4)
        self._aff_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_workplaces())

        ttk.Label(form, text="사업장", width=14).grid(row=1, column=0, sticky=tk.W, pady=4)
        self._wp_var = tk.StringVar(value=suggested.workplace)
        self._wp_combo = ttk.Combobox(form, textvariable=self._wp_var, width=28)
        self._wp_combo.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(form, text="급여월", width=14).grid(row=2, column=0, sticky=tk.W, pady=4)
        self._period_var = tk.StringVar(value=suggested.period)
        self._period_entry = ttk.Entry(form, textvariable=self._period_var, width=12)
        self._period_entry.grid(row=2, column=1, sticky=tk.W, pady=4)
        ttk.Label(form, text="예: 2026-05", foreground=COLORS["muted"]).grid(row=2, column=2, sticky=tk.W, padx=(8, 0))

        self._path_label = tk.Label(
            pad,
            text="",
            anchor=tk.W,
            justify=tk.LEFT,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=10,
            pady=8,
            wraplength=420,
        )
        self._path_label.pack(fill=tk.X, pady=(8, 8))

        self._confirm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pad,
            text="위 계열사·사업장·급여월의 청구서가 맞습니다.",
            variable=self._confirm_var,
            command=self._update_buttons,
        ).pack(anchor=tk.W, pady=(0, 12))

        btn_row = ttk.Frame(pad)
        btn_row.pack(fill=tk.X)
        self._ok_btn = ttk.Button(btn_row, text="급여 산출 시작", command=self._on_ok, state=tk.DISABLED)
        self._ok_btn.pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="취소", command=self._on_cancel).pack(side=tk.RIGHT)

        for var in (self._aff_var, self._wp_var, self._period_var):
            var.trace_add("write", lambda *_a: self._update_preview())
        self._refresh_workplaces()
        self._update_preview()
        self._update_buttons()

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    @property
    def scope(self) -> PayrollScope | None:
        return self._result

    def _refresh_workplaces(self) -> None:
        aff = self._aff_var.get().strip()
        wps = self._on_workplaces(aff)
        if not wps:
            wps = list_config_workplaces(aff)
        self._wp_combo.configure(values=wps)
        if self._wp_var.get() not in wps and wps:
            self._wp_var.set(wps[0])

    def _update_preview(self) -> None:
        scope = self._current_scope()
        self._path_label.configure(
            text=f"저장 위치\n{scope.breadcrumb()}\n\n산출 파일: 급여대장 · 급여명세서 · 지급내역 · 청구서 원본"
        )

    def _current_scope(self) -> PayrollScope:
        return PayrollScope(
            self._aff_var.get().strip() or get_default_affiliate(),
            self._wp_var.get().strip() or "미분류",
            self._period_var.get().strip(),
        )

    def _update_buttons(self) -> None:
        ok = self._confirm_var.get() and self._validate_period(silent=True)
        self._ok_btn.configure(state=tk.NORMAL if ok else tk.DISABLED)

    def _validate_period(self, silent: bool = False) -> bool:
        p = self._period_var.get().strip()
        if not _PERIOD_RE.match(p):
            if not silent:
                messagebox.showwarning(
                    "급여월",
                    "급여월은 YYYY-MM 형식이어야 합니다. (예: 2026-05)",
                    parent=self,
                )
            return False
        return True

    def _on_ok(self) -> None:
        if not self._confirm_var.get():
            messagebox.showinfo("확인 필요", "체크박스에 동의해 주세요.", parent=self)
            return
        if not self._validate_period():
            return
        wp = self._wp_var.get().strip()
        if not wp:
            messagebox.showwarning("사업장", "사업장을 선택하거나 입력해 주세요.", parent=self)
            return
        self._result = self._current_scope()
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()


def suggest_upload_scope(
    invoice_path,
    default_affiliate: str = "",
    default_workplace: str = "",
) -> PayrollScope:
    """파일명·명부 기준 업로드 위치 추정."""
    from datetime import datetime
    from main import _period_from_filename
    from payroll_builder import load_employee_roster, resolve_roster_path
    from invoice_parser import extract_invoice_data
    from services.org_registry import resolve_affiliate, resolve_workplace
    from collections import Counter

    period = _period_from_filename(invoice_path) or datetime.now().strftime("%Y-%m")
    affiliate = default_affiliate or get_default_affiliate()
    workplace = default_workplace

    cfg_wps = list_config_workplaces(affiliate)
    if not workplace and len(cfg_wps) == 1:
        workplace = cfg_wps[0]

    try:
        rows = extract_invoice_data(invoice_path)
        roster_path, _src = resolve_roster_path(invoice_path, period=period)
        if roster_path:
            roster = load_employee_roster(roster_path, period_hint=period)
            wps: list[str] = []
            for row in rows:
                key = str(row.get("name") or "").strip().replace(" ", "")
                emp = roster.get(key)
                if emp:
                    wps.append(str(emp.get("근무지") or resolve_workplace({"workplace": "", "dept": ""})))
            if wps:
                workplace = Counter(wps).most_common(1)[0][0]
            affs = [resolve_affiliate({"affiliate": emp.get("계열사"), "workplace": emp.get("근무지")}) for emp in roster.values() if isinstance(emp, dict)]
            if affs:
                affiliate = Counter(affs).most_common(1)[0][0]
    except Exception:
        pass

    if not workplace:
        workplace = cfg_wps[0] if len(cfg_wps) == 1 else "미분류"

    workplace = canonical_scope_workplace(workplace)

    return PayrollScope(affiliate, workplace, period)
