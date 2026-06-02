"""
ui/bank_account_edit_dialog.py - 급여 지급 계좌(예금주·계좌번호) 편집
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from bank_account import apply_bank_account_to_record, is_third_party_holder, save_bank_account_fields
from ui.theme import COLORS, FONT


class BankAccountEditDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        rec: dict[str, Any],
        *,
        on_apply: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._rec = rec
        self._on_apply = on_apply
        apply_bank_account_to_record(rec)

        name = str(rec.get("성명") or "").strip() or "(이름 없음)"
        self.title(f"지급 계좌 — {name}")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        header = tk.Label(
            self,
            text=(
                f"{name}\n"
                "가족 등 타인 명의 계좌로 급여를 받는 경우 예금주에 통장 명의를 입력하세요.\n"
                "지급내역·이체 파일에는 아래 예금주·계좌번호가 사용됩니다."
            ),
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=12,
            pady=10,
            justify=tk.LEFT,
        )
        header.pack(fill=tk.X)

        form = ttk.Frame(self, padding=12)
        form.pack(fill=tk.BOTH, expand=True)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="근로자 성명").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Label(form, text=name, font=(FONT, 10, "bold")).grid(
            row=0, column=1, sticky=tk.W, pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="예금주").grid(row=1, column=0, sticky=tk.W, pady=4)
        self._holder_var = tk.StringVar(value=str(rec.get("예금주") or name))
        ttk.Entry(form, textvariable=self._holder_var, width=32).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="계좌번호").grid(row=2, column=0, sticky=tk.W, pady=4)
        self._acct_var = tk.StringVar(value=str(rec.get("계좌번호") or rec.get("계좌") or ""))
        ttk.Entry(form, textvariable=self._acct_var, width=32).grid(
            row=2, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="은행명").grid(row=3, column=0, sticky=tk.W, pady=4)
        self._bank_var = tk.StringVar(value=str(rec.get("은행명") or ""))
        ttk.Entry(form, textvariable=self._bank_var, width=32).grid(
            row=3, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="은행코드").grid(row=4, column=0, sticky=tk.W, pady=4)
        self._code_var = tk.StringVar(value=str(rec.get("은행코드") or ""))
        ttk.Entry(form, textvariable=self._code_var, width=32).grid(
            row=4, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        btn_row = ttk.Frame(form)
        btn_row.grid(row=5, column=1, sticky=tk.W, pady=(6, 0), padx=(8, 0))
        ttk.Button(btn_row, text="예금주 = 성명", command=self._use_employee_name, width=14).pack(
            side=tk.LEFT
        )

        self._hint = tk.Label(
            form,
            text="",
            anchor=tk.W,
            fg=COLORS["warn"],
            font=(FONT, 8),
            wraplength=360,
            justify=tk.LEFT,
        )
        self._hint.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        self._holder_var.trace_add("write", lambda *_: self._update_hint())
        self._update_hint()

        foot = ttk.Frame(self, padding=(10, 0, 10, 10))
        foot.pack(fill=tk.X)
        ttk.Button(foot, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(foot, text="적용", command=self._apply).pack(side=tk.RIGHT)

        self.wait_window()

    def _use_employee_name(self) -> None:
        self._holder_var.set(str(self._rec.get("성명") or "").strip())

    def _update_hint(self) -> None:
        if is_third_party_holder(self._rec.get("성명"), self._holder_var.get()):
            self._hint.configure(text="※ 예금주가 근로자 성명과 다릅니다. 지급내역에 입력한 예금주로 표시됩니다.")
        else:
            self._hint.configure(text="")

    def _apply(self) -> None:
        acct = self._acct_var.get().strip()
        if not acct:
            if not messagebox.askyesno(
                "확인",
                "계좌번호가 비어 있습니다. 그대로 저장할까요?",
                parent=self,
            ):
                return
        save_bank_account_fields(
            self._rec,
            holder=self._holder_var.get(),
            account_no=acct,
            bank_name=self._bank_var.get(),
            bank_code=self._code_var.get(),
        )
        if self._on_apply:
            self._on_apply(self._rec)
        self.destroy()


def open_bank_account_editor(
    parent: tk.Misc,
    rec: dict[str, Any],
    *,
    on_apply: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    BankAccountEditDialog(parent, rec, on_apply=on_apply)
