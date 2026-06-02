"""
ui/disability_summary_dialog.py - 계열사(법인)별 장애인 고용 현황
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from disability_employment import (
    AFFILIATE_UNSET_LABEL,
    count_disability_by_affiliate,
    count_disability_totals,
    format_affiliate_disability_summary,
)
from ui.theme import COLORS, FONT


def show_disability_summary_dialog(
    parent: tk.Misc,
    rows: list[dict[str, Any]],
) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("장애인 고용 현황 (계열사별)")
    dlg.transient(parent)
    dlg.geometry("640x360")
    dlg.minsize(520, 280)

    totals = count_disability_totals(rows)
    summary = format_affiliate_disability_summary(rows)

    hdr = tk.Label(
        dlg,
        text=summary,
        anchor=tk.W,
        bg=COLORS["accent_light"],
        fg=COLORS["accent"],
        font=(FONT, 9),
        padx=12,
        pady=10,
        wraplength=600,
        justify=tk.LEFT,
    )
    hdr.pack(fill=tk.X)

    ttk.Label(
        dlg,
        text="계열사(법인) = 명부 「계열사」 열 · 장애인 = 「예」 표기 인원",
        font=(FONT, 8),
        padding=(12, 4),
    ).pack(anchor=tk.W)

    frame = ttk.Frame(dlg, padding=(12, 8))
    frame.pack(fill=tk.BOTH, expand=True)

    cols = ("affiliate", "total", "disabled", "not_disabled", "unset", "rate")
    tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
    for cid, title, width in (
        ("affiliate", "계열사(법인)", 160),
        ("total", "재직", 56),
        ("disabled", "장애인", 56),
        ("not_disabled", "비장애인", 72),
        ("unset", "미입력", 56),
        ("rate", "장애인 비율", 88),
    ):
        tree.heading(cid, text=title)
        tree.column(cid, width=width, anchor=tk.CENTER if cid != "affiliate" else tk.W)

    yscroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)

    for st in count_disability_by_affiliate(rows):
        rate = f"{st.rate_pct:.1f}%" if st.total else "—"
        tree.insert(
            "",
            tk.END,
            values=(
                st.affiliate,
                st.total,
                st.disabled,
                st.not_disabled,
                st.unset,
                rate,
            ),
        )

    tree.insert(
        "",
        tk.END,
        values=(
            "합계",
            totals["total"],
            totals["disabled"],
            totals["not_disabled"],
            totals["unset"],
            f"{100.0 * totals['disabled'] / totals['total']:.1f}%"
            if totals["total"]
            else "—",
        ),
        tags=("total",),
    )
    tree.tag_configure("total", font=(FONT, 9, "bold"))

    foot = ttk.Frame(dlg, padding=12)
    foot.pack(fill=tk.X)
    if totals["unset"]:
        ttk.Label(
            foot,
            text=f"※ 미입력 {totals['unset']}명 — 명부에서 장애인 유무를 입력하면 집계가 정확해집니다.",
            font=(FONT, 8),
        ).pack(side=tk.LEFT)
    if AFFILIATE_UNSET_LABEL in {st.affiliate for st in count_disability_by_affiliate(rows)}:
        ttk.Label(
            foot,
            text="※ 계열사 미기재 인원은 (미지정)으로 묶입니다.",
            font=(FONT, 8),
        ).pack(side=tk.LEFT, padx=(8, 0))

    ttk.Button(foot, text="닫기", command=dlg.destroy).pack(side=tk.RIGHT)
