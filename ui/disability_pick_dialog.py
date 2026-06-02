"""
ui/disability_pick_dialog.py - 장애인 유무 선택
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from disability_employment import DISABILITY_NO, DISABILITY_YES
from ui.theme import FONT


def pick_disability_flag(
    parent: tk.Misc,
    *,
    initial: str = "",
    employee_name: str = "",
) -> str | None:
    """장애인 유무 선택. 취소 시 None, 미입력은 ''."""
    result: list[str | None] = [None]

    dlg = tk.Toplevel(parent)
    title_name = employee_name or "직원"
    dlg.title(f"장애인 유무 — {title_name}")
    dlg.transient(parent)
    dlg.grab_set()
    dlg.resizable(False, False)

    ttk.Label(
        dlg,
        text=(
            f"{title_name}\n"
            "장애인 고용(의무고용) 신고·분담금 산정용입니다.\n"
            "법인(계열사)별 장애인 보유 인원 집계에 반영됩니다."
        ),
        padding=12,
        justify=tk.LEFT,
    ).pack(anchor=tk.W)

    var = tk.StringVar(value=initial or DISABILITY_NO)
    for label, val in (
        ("장애인 (예)", DISABILITY_YES),
        ("비장애인 (아니오)", DISABILITY_NO),
    ):
        ttk.Radiobutton(dlg, text=label, variable=var, value=val).pack(anchor=tk.W, padx=20, pady=2)

    ttk.Label(dlg, text="미입력", font=(FONT, 8)).pack(anchor=tk.W, padx=12, pady=(8, 0))
    ttk.Radiobutton(dlg, text="(미입력)", variable=var, value="").pack(anchor=tk.W, padx=20, pady=2)

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
