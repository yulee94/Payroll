"""
ui/succession_edit_dialog.py - 고용승계 경로 편집
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from core.org_config import list_config_affiliates
from employment_succession import (
    KIND_INITIAL,
    KIND_SUCCESSION,
    SuccessionStep,
    format_succession_path,
    format_succession_date,
    parse_succession_history,
    save_succession_steps,
    serialize_succession_history,
    severance_display,
)
from senior_internship import parse_roster_date_input
from ui.theme import COLORS, FONT


class SuccessionEditDialog(tk.Toplevel):
    """고용승계 이력 편집 (계열사·일자·퇴직금 정산)."""

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
        self._steps: list[SuccessionStep] = list(parse_succession_history(rec))
        self._selected_index: int | None = None

        name = str(rec.get("성명") or "").strip() or "(이름 없음)"
        self.title(f"고용승계 — {name}")
        self.transient(parent)
        self.grab_set()
        self.geometry("640x480")
        self.minsize(560, 420)

        header = tk.Label(
            self,
            text=(
                f"{name} · 현재 계열사: {rec.get('계열사') or '—'}\n"
                "최초 입사 → 계열사 이동(승계) 순으로 등록 · 승계 시 전 법인 퇴직금 정산 여부(O/X)"
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

        body = ttk.Frame(self, padding=10)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(body, text="승계 경로", padding=6)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._listbox = tk.Listbox(list_frame, font=(FONT, 10), height=8, activestyle="dotbox")
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scroll.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ttk.Frame(list_frame)
        btn_row.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btn_row, text="추가", command=self._add_step, width=8).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="수정", command=self._edit_step, width=8).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="삭제", command=self._delete_step, width=8).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="▲", command=lambda: self._move(-1), width=4).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Button(btn_row, text="▼", command=lambda: self._move(1), width=4).pack(side=tk.LEFT)

        form = ttk.LabelFrame(body, text="단계 상세", padding=8)
        form.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="계열사").grid(row=0, column=0, sticky=tk.W, pady=4)
        self._aff_var = tk.StringVar()
        affs = list_config_affiliates()
        self._aff_combo = ttk.Combobox(form, textvariable=self._aff_var, values=affs, width=28)
        self._aff_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(form, text="일자").grid(row=1, column=0, sticky=tk.W, pady=4)
        self._date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._date_var, width=30).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="구분").grid(row=2, column=0, sticky=tk.W, pady=4)
        self._kind_var = tk.StringVar(value=KIND_INITIAL)
        kind_frame = ttk.Frame(form)
        kind_frame.grid(row=2, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        ttk.Radiobutton(
            kind_frame, text="최초입사", variable=self._kind_var, value=KIND_INITIAL, command=self._sync_sev_state
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            kind_frame, text="승계", variable=self._kind_var, value=KIND_SUCCESSION, command=self._sync_sev_state
        ).pack(side=tk.LEFT)

        ttk.Label(form, text="퇴직금정산").grid(row=3, column=0, sticky=tk.W, pady=4)
        sev_frame = ttk.Frame(form)
        sev_frame.grid(row=3, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        self._sev_var = tk.StringVar(value="—")
        self._sev_radios: list[ttk.Radiobutton] = []
        for label, val in (("O (정산)", "O"), ("X (미정산)", "X"), ("미기재", "—")):
            rb = ttk.Radiobutton(sev_frame, text=label, variable=self._sev_var, value=val)
            rb.pack(side=tk.LEFT, padx=(0, 10))
            self._sev_radios.append(rb)

        self._preview = tk.Label(
            body,
            text="",
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=580,
            justify=tk.LEFT,
        )
        self._preview.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        foot = ttk.Frame(self, padding=(10, 0, 10, 10))
        foot.pack(fill=tk.X)
        ttk.Button(foot, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(foot, text="적용", command=self._apply).pack(side=tk.RIGHT)

        self._refresh_list()
        if self._steps:
            self._listbox.selection_set(0)
            self._load_step(0)

        self.wait_window()

    def _refresh_list(self) -> None:
        self._listbox.delete(0, tk.END)
        for i, step in enumerate(self._steps):
            kind = "최초" if step.kind == KIND_INITIAL or i == 0 else "승계"
            sev = ""
            if i > 0 and step.kind == KIND_SUCCESSION:
                sev = f" · 퇴직금 {severance_display(step.severance_settled)}"
            self._listbox.insert(tk.END, f"{i + 1}. [{kind}] {step.affiliate} — {step.date}{sev}")
        preview_rec = {**self._rec}
        if self._steps:
            preview_rec["고용승계이력"] = serialize_succession_history(self._steps)
        self._preview.configure(text=format_succession_path(preview_rec) or "(경로 없음)")

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        self._load_step(int(sel[0]))

    def _load_step(self, index: int) -> None:
        if index < 0 or index >= len(self._steps):
            return
        self._selected_index = index
        step = self._steps[index]
        self._aff_var.set(step.affiliate)
        self._date_var.set(step.date)
        self._kind_var.set(KIND_INITIAL if index == 0 else step.kind)
        self._sync_sev_state()
        if index == 0:
            self._sev_var.set("—")
        elif step.severance_settled is True:
            self._sev_var.set("O")
        elif step.severance_settled is False:
            self._sev_var.set("X")
        else:
            self._sev_var.set("—")

    def _sync_sev_state(self) -> None:
        is_first = self._selected_index == 0 or self._kind_var.get() == KIND_INITIAL
        state = tk.DISABLED if is_first else tk.NORMAL
        for rb in self._sev_radios:
            rb.configure(state=state)

    def _read_form(self) -> SuccessionStep | None:
        aff = self._aff_var.get().strip()
        date_raw = self._date_var.get().strip()
        parsed = parse_roster_date_input(date_raw) if date_raw else None
        if date_raw and parsed is None:
            messagebox.showwarning("입력 오류", "일자 형식을 확인해 주세요. (예: 2015.01.01)", parent=self)
            return None
        date_s = parsed or format_succession_date(date_raw)
        idx = self._selected_index if self._selected_index is not None else len(self._steps)
        kind = KIND_INITIAL if idx == 0 else self._kind_var.get()
        sev: bool | None = None
        if idx > 0 and kind == KIND_SUCCESSION:
            v = self._sev_var.get()
            if v == "O":
                sev = True
            elif v == "X":
                sev = False
        return SuccessionStep(affiliate=aff, date=date_s, kind=kind, severance_settled=sev)

    def _add_step(self) -> None:
        new = SuccessionStep(
            affiliate=str(self._rec.get("계열사") or ""),
            date="0000.00.00",
            kind=KIND_SUCCESSION if self._steps else KIND_INITIAL,
            severance_settled=None,
        )
        self._steps.append(new)
        self._refresh_list()
        idx = len(self._steps) - 1
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(idx)
        self._load_step(idx)

    def _edit_step(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            messagebox.showinfo("선택 없음", "수정할 단계를 선택하세요.", parent=self)
            return
        idx = int(sel[0])
        self._selected_index = idx
        step = self._read_form()
        if step is None:
            return
        if not step.affiliate:
            messagebox.showwarning("입력 오류", "계열사를 입력하세요.", parent=self)
            return
        self._steps[idx] = step
        self._refresh_list()
        self._listbox.selection_set(idx)

    def _delete_step(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        del self._steps[idx]
        self._selected_index = None
        self._refresh_list()

    def _move(self, delta: int) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self._steps):
            return
        self._steps[idx], self._steps[new_idx] = self._steps[new_idx], self._steps[idx]
        if new_idx == 0:
            self._steps[0].kind = KIND_INITIAL
            self._steps[0].severance_settled = None
        self._refresh_list()
        self._listbox.selection_set(new_idx)
        self._load_step(new_idx)

    def _apply(self) -> None:
        sel = self._listbox.curselection()
        if sel:
            self._selected_index = int(sel[0])
            step = self._read_form()
            if step is None:
                return
            if not step.affiliate:
                messagebox.showwarning("입력 오류", "계열사를 입력하세요.", parent=self)
                return
            self._steps[self._selected_index] = step

        if not self._steps:
            if not messagebox.askyesno(
                "확인",
                "승계 이력을 모두 삭제할까요?",
                parent=self,
            ):
                return
        save_succession_steps(self._rec, self._steps)
        if self._on_apply:
            self._on_apply(self._rec)
        self.destroy()


def open_succession_editor(
    parent: tk.Misc,
    rec: dict[str, Any],
    *,
    on_apply: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    SuccessionEditDialog(parent, rec, on_apply=on_apply)
