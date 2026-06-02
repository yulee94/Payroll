"""
ui/employment_type_pick_dialog.py - 고용형태 선택
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from employment_type import TYPE_DAILY, TYPE_REGULAR_HOURLY, TYPE_REGULAR_SALARY
from ui.theme import FONT


def pick_employment_type(parent: tk.Misc, *, initial: str = "", employee_name: str = "") -> str | None:
    """고용형태 선택 대화상자. 취소 시 None."""
    result: list[str | None] = [None]

    dlg = tk.Toplevel(parent)
    title_name = employee_name or "직원"
    dlg.title(f"고용형태 — {title_name}")
    dlg.transient(parent)
    dlg.grab_set()
    dlg.resizable(False, False)

    ttk.Label(
        dlg,
        text=f"{title_name}\n고용형태를 선택하세요.",
        padding=12,
        justify=tk.LEFT,
    ).pack(anchor=tk.W)

    var = tk.StringVar(value=initial or TYPE_REGULAR_HOURLY)
    choices = [TYPE_DAILY, TYPE_REGULAR_HOURLY, TYPE_REGULAR_SALARY]
    for label, val in (
        ("일용직", TYPE_DAILY),
        ("정규직 (시급직)", TYPE_REGULAR_HOURLY),
        ("정규직 (연봉직)", TYPE_REGULAR_SALARY),
    ):
        ttk.Radiobutton(dlg, text=label, variable=var, value=val).pack(anchor=tk.W, padx=20, pady=2)

    ttk.Label(dlg, text="미지정(비움)", font=(FONT, 8)).pack(anchor=tk.W, padx=12, pady=(8, 0))
    ttk.Radiobutton(dlg, text="(미분류)", variable=var, value="").pack(anchor=tk.W, padx=20, pady=2)

    foot = ttk.Frame(dlg, padding=12)
    foot.pack(fill=tk.X)

    def ok() -> None:
        result[0] = var.get()
        dlg.destroy()

    def cancel() -> None:
        dlg.destroy()

    ttk.Button(foot, text="취소", command=cancel).pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(foot, text="확인", command=ok).pack(side=tk.RIGHT)
    dlg.wait_window()
    return result[0]
