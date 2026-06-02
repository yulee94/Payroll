"""
ui/hr_signal_panel.py - Bitween HR 신호등 조회 (법인 간 공유)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from core.hr import traffic_signal as sig
from core.hr.traffic_signal import STATUS_LABELS
from ui.theme import COLORS, FONT, FONT_BODY


class HrSignalPanel(tk.Frame):
    """주민등록번호로 타 법인 포함 신호등·재직 이력 조회."""

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._rrn_var = tk.StringVar()
        self._result_var = tk.StringVar(value="주민등록번호 13자리를 입력하고 조회하세요.")
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#FFFBEB", highlightbackground="#FDE68A", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=(
                "Bitween 신호등은 주민등록번호로 개인을 매칭합니다 (동명이인 구분). "
                "퇴사 시 등록된 판정은 퇴사 후에도 유지되며, 타 법인 채용 시 참고할 수 있습니다. "
                "개인정보 보호를 위해 화면에는 마스킹된 번호만 표시됩니다."
            ),
            bg="#FFFBEB",
            fg="#92400E",
            font=(FONT, 9),
            wraplength=820,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        card = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        search = tk.Frame(card, bg=COLORS["card"])
        search.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        tk.Label(search, text="주민등록번호", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            side=tk.LEFT
        )
        ttk.Entry(search, textvariable=self._rrn_var, width=24, font=FONT_BODY).pack(side=tk.LEFT, padx=(10, 8))
        tk.Button(
            search,
            text="신호등 조회",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._lookup,
        ).pack(side=tk.LEFT)

        self._badge = tk.Label(
            card,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
            anchor=tk.W,
        )
        self._badge.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))

        body = tk.Frame(card, bg=COLORS["card"])
        body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 14))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._text = tk.Text(
            body,
            wrap=tk.WORD,
            font=FONT_BODY,
            height=16,
            bg="#F8FAFC",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._text.configure(state=tk.DISABLED)

    def _set_text(self, content: str) -> None:
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, content)
        self._text.configure(state=tk.DISABLED)

    def _lookup(self) -> None:
        key, err = sig.validate_rrn_input(self._rrn_var.get())
        if err:
            messagebox.showwarning("신호등", err, parent=self.winfo_toplevel())
            return
        prof = sig.lookup_by_rrn(key)
        if not prof:
            messagebox.showwarning("신호등", "조회할 수 없습니다.", parent=self.winfo_toplevel())
            return
        emoji = prof.display_emoji
        self._badge.configure(
            text=f"{emoji}  {prof.status_label}",
            fg={"green": "#059669", "yellow": "#D97706", "red": "#DC2626"}.get(prof.status, COLORS["text"]),
        )
        lines = prof.summary_lines()
        lines.append("")
        if prof.employment_history:
            lines.append("[재직 이력 — Bitween 법인 간]")
            for h in prof.employment_history:
                lines.append(
                    f"  · {h.tenant_name} | {h.employee_name} | "
                    f"{h.hire_date or '?'} ~ {h.resign_date or '재직'} | {h.site_name or h.department or '-'}"
                )
            lines.append("")
        if prof.issues:
            lines.append("[신호등·판정 이력]")
            for issue in prof.issues[-15:]:
                se = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(issue.severity, "·")
                lines.append(
                    f"  {se} {issue.recorded_at} | {issue.tenant_name} | "
                    f"{issue.category}: {issue.summary}"
                )
        elif not prof.found:
            lines.append("등록된 이력이 없습니다. (최초 채용 또는 타 법인 미등록)")
        self._set_text("\n".join(lines))

    def lookup_and_show(self, rrn: str) -> None:
        self._rrn_var.set(rrn)
        self._lookup()


def ask_resign_signal_registration(parent: tk.Misc) -> tuple[str, str, str] | None:
    """퇴사 신호등 등록 입력. Returns (severity, category, summary) or None."""
    dlg = tk.Toplevel(parent)
    dlg.title("퇴사 신호등 등록")
    dlg.transient(parent.winfo_toplevel())
    dlg.grab_set()
    dlg.configure(bg=COLORS["bg"])

    severity_var = tk.StringVar(value="green")
    category_var = tk.StringVar(value="퇴사")
    summary_var = tk.StringVar()
    result: dict[str, tuple[str, str, str] | None] = {"value": None}

    tk.Label(
        dlg,
        text="퇴사자 판정을 Bitween 법인 간 공유 레지스트리에 등록합니다.\n"
        "주민등록번호로 매칭되며, 퇴사 후에도 유지됩니다.",
        bg=COLORS["bg"],
        fg=COLORS["text"],
        font=(FONT, 9),
        justify=tk.LEFT,
        wraplength=420,
    ).pack(anchor=tk.W, padx=16, pady=(14, 10))

    form = tk.Frame(dlg, bg=COLORS["bg"])
    form.pack(fill=tk.X, padx=16)

    tk.Label(form, text="신호등", bg=COLORS["bg"], font=(FONT, 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=4)
    combo = ttk.Combobox(
        form,
        textvariable=severity_var,
        values=[f"{k} ({v})" for k, v in STATUS_LABELS.items()],
        state="readonly",
        width=28,
    )
    combo.current(0)
    combo.grid(row=0, column=1, sticky=tk.W, pady=4, padx=(8, 0))

    tk.Label(form, text="분류", bg=COLORS["bg"], font=(FONT, 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=4)
    ttk.Entry(form, textvariable=category_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=4, padx=(8, 0))

    tk.Label(form, text="판정 사유", bg=COLORS["bg"], font=(FONT, 9, "bold")).grid(
        row=2, column=0, sticky=tk.NW, pady=4
    )
    summary_entry = ttk.Entry(form, textvariable=summary_var, width=30)
    summary_entry.grid(row=2, column=1, sticky=tk.W, pady=4, padx=(8, 0))

    btn_row = tk.Frame(dlg, bg=COLORS["bg"])
    btn_row.pack(fill=tk.X, padx=16, pady=14)

    def _ok() -> None:
        raw = severity_var.get().split()[0]
        if raw not in STATUS_LABELS:
            messagebox.showwarning("신호등", "신호등 색상을 선택하세요.", parent=dlg)
            return
        summary = summary_var.get().strip()
        if not summary:
            messagebox.showwarning("신호등", "판정 사유를 입력하세요.", parent=dlg)
            return
        result["value"] = (raw, category_var.get().strip() or "퇴사", summary)
        dlg.destroy()

    def _cancel() -> None:
        dlg.destroy()

    tk.Button(btn_row, text="등록", bg="#0D9488", fg="#FFFFFF", relief=tk.FLAT, command=_ok).pack(side=tk.RIGHT)
    tk.Button(btn_row, text="취소", relief=tk.FLAT, command=_cancel).pack(side=tk.RIGHT, padx=(0, 8))
    summary_entry.focus_set()
    dlg.wait_window()
    return result["value"]
