"""
ui/severance_panel.py - 퇴직금·중간정산 산출 UI
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from annual_leave_accrual import parse_hire_date
from core.access_control import load_roster_rows_secured
from core.hr import severance as sev
from core.hr.severance import InterimSettlement, SeveranceResult
from core.session_service import session_tenant_id
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


def _won(n: int | float) -> str:
    return f"{int(round(n)):,}원"


def _fmt_date(d: date | None) -> str:
    if d is None:
        return "-"
    return f"{d.year:04d}.{d.month:02d}.{d.day:02d}"


class SeverancePanel(tk.Frame):
    """직원 선택 + 퇴직일 → 3개월 임금·보험·퇴직금·중간정산 표시."""

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._roster: list[dict[str, Any]] = []
        self._result: SeveranceResult | None = None
        self._employee_var = tk.StringVar()
        self._resign_var = tk.StringVar()
        self._hire_var = tk.StringVar(value="-")
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=(
                "퇴직금은 근로자퇴직급여 보장법에 따라 퇴직일 이전 3개월 급여 스냅샷(총지급·세전)으로 "
                "평균임금을 산출합니다. 4대보험 근로자 부담분은 참고용으로 표시하며, "
                "퇴직금 산정 기준 임금에는 공제하지 않습니다. "
                "5년 이상 근속 시 중간정산 이력은 최종 퇴직금에서 차감됩니다."
            ),
            bg="#EFF6FF",
            fg="#1E40AF",
            font=(FONT, 9),
            wraplength=860,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        top = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        top.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        form = tk.Frame(top, bg=COLORS["card"])
        form.pack(fill=tk.X, padx=16, pady=12)

        tk.Label(form, text="직원", bg=COLORS["card"], font=(FONT, 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        self._emp_combo = ttk.Combobox(form, textvariable=self._employee_var, width=18, font=FONT_BODY, state="readonly")
        self._emp_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 16))
        self._emp_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_employee_selected())

        tk.Label(form, text="입사일", bg=COLORS["card"], font=(FONT, 10, "bold")).grid(row=0, column=2, sticky=tk.W)
        tk.Label(form, textvariable=self._hire_var, bg=COLORS["card"], font=FONT_BODY).grid(
            row=0, column=3, sticky=tk.W, padx=(8, 16)
        )

        tk.Label(form, text="퇴직일", bg=COLORS["card"], font=(FONT, 10, "bold")).grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(form, textvariable=self._resign_var, width=14, font=FONT_BODY).grid(row=0, column=5, sticky=tk.W, padx=(8, 8))

        tk.Button(
            form,
            text="퇴직금 산출",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._calculate,
        ).grid(row=0, column=6, padx=(8, 0))

        tk.Button(
            form,
            text="새로고침",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.refresh,
        ).grid(row=0, column=7, padx=(8, 0))

        body = tk.Frame(self, bg=COLORS["bg"])
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=2)
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        # --- 3개월 임금 ---
        wage_card = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        wage_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        wage_card.grid_rowconfigure(1, weight=1)
        wage_card.grid_columnconfigure(0, weight=1)
        tk.Label(wage_card, text="퇴직 전 3개월 임금·보험", bg=COLORS["card"], font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        wage_wrap = tk.Frame(wage_card, bg=COLORS["card"])
        wage_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        wage_wrap.grid_rowconfigure(0, weight=1)
        wage_wrap.grid_columnconfigure(0, weight=1)

        cols = ("month", "days", "gross", "insurance", "prorated", "note")
        self._wage_tree = ttk.Treeview(wage_wrap, columns=cols, show="headings", height=8)
        headings = {
            "month": ("급여월", 90),
            "days": ("산정일수", 70),
            "gross": ("월 총지급", 100),
            "insurance": ("4대보험(근로자)", 110),
            "prorated": ("비례 임금", 100),
            "note": ("비고", 80),
        }
        for cid, (label, width) in headings.items():
            self._wage_tree.heading(cid, text=label)
            self._wage_tree.column(cid, width=width, anchor=tk.CENTER if cid != "note" else tk.W)
        wscroll = ttk.Scrollbar(wage_wrap, orient=tk.VERTICAL, command=self._wage_tree.yview)
        self._wage_tree.configure(yscrollcommand=wscroll.set)
        self._wage_tree.grid(row=0, column=0, sticky="nsew")
        wscroll.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._wage_tree, self._wage_tree)

        self._summary_var = tk.StringVar(value="직원과 퇴직일을 선택한 뒤 「퇴직금 산출」을 누르세요.")
        tk.Label(
            wage_card,
            textvariable=self._summary_var,
            bg="#F8FAFC",
            fg=COLORS["text"],
            font=(FONT, 9),
            justify=tk.LEFT,
            anchor=tk.W,
            wraplength=520,
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        # --- 중간정산 ---
        interim_card = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        interim_card.grid(row=0, column=1, rowspan=2, sticky="nsew")
        interim_card.grid_rowconfigure(1, weight=1)
        interim_card.grid_columnconfigure(0, weight=1)

        head = tk.Frame(interim_card, bg=COLORS["card"])
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        tk.Label(head, text="중간정산 이력", bg=COLORS["card"], font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        tk.Button(
            head,
            text="＋ 추가",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 8, "bold"),
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._add_interim,
        ).pack(side=tk.RIGHT)

        interim_wrap = tk.Frame(interim_card, bg=COLORS["card"])
        interim_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        interim_wrap.grid_rowconfigure(0, weight=1)
        interim_wrap.grid_columnconfigure(0, weight=1)

        icols = ("date", "amount", "reason")
        self._interim_tree = ttk.Treeview(interim_wrap, columns=icols, show="headings", height=12)
        for cid, label, width in (("date", "정산일", 90), ("amount", "금액", 100), ("reason", "사유", 140)):
            self._interim_tree.heading(cid, text=label)
            self._interim_tree.column(cid, width=width, anchor=tk.CENTER if cid != "reason" else tk.W)
        iscroll = ttk.Scrollbar(interim_wrap, orient=tk.VERTICAL, command=self._interim_tree.yview)
        self._interim_tree.configure(yscrollcommand=iscroll.set)
        self._interim_tree.grid(row=0, column=0, sticky="nsew")
        iscroll.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._interim_tree, self._interim_tree)

        btn_row = tk.Frame(interim_card, bg=COLORS["card"])
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        tk.Button(
            btn_row,
            text="수정",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 9),
            command=self._edit_interim,
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            btn_row,
            text="삭제",
            bg=COLORS["card"],
            fg="#DC2626",
            relief=tk.FLAT,
            font=(FONT, 9),
            command=self._delete_interim,
        ).pack(side=tk.LEFT)

        self._final_var = tk.StringVar(value="")
        tk.Label(
            interim_card,
            textvariable=self._final_var,
            bg="#ECFDF5",
            fg="#065F46",
            font=(FONT, 11, "bold"),
            anchor=tk.W,
            padx=10,
            pady=8,
        ).grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

    def refresh(self) -> None:
        self._roster = load_roster_rows_secured(tenant_id=session_tenant_id())
        names = sorted({str(r.get("성명") or "").strip() for r in self._roster if str(r.get("성명") or "").strip()})
        self._emp_combo["values"] = names
        if names and not self._employee_var.get():
            self._employee_var.set(names[0])
            self._on_employee_selected()

    def _roster_row(self, name: str) -> dict[str, Any] | None:
        key = name.strip()
        for row in self._roster:
            if str(row.get("성명") or "").strip() == key:
                return row
        return None

    def _on_employee_selected(self) -> None:
        name = self._employee_var.get().strip()
        row = self._roster_row(name)
        if not row:
            self._hire_var.set("-")
            return
        hire = sev.hire_date_from_roster(row)
        resign = sev.resign_date_from_roster(row)
        self._hire_var.set(_fmt_date(hire))
        if resign:
            self._resign_var.set(_fmt_date(resign))
        self._load_interim_list(name)

    def _parse_resign_input(self) -> date | None:
        raw = self._resign_var.get().strip()
        d = parse_hire_date(raw)
        if d is None and raw:
            messagebox.showwarning("퇴직일", "퇴직일 형식을 확인하세요. (예: 2026.06.15)", parent=self.winfo_toplevel())
        return d

    def _calculate(self) -> None:
        name = self._employee_var.get().strip()
        if not name:
            messagebox.showinfo("퇴직금", "직원을 선택하세요.", parent=self.winfo_toplevel())
            return
        resign = self._parse_resign_input()
        if resign is None:
            return
        row = self._roster_row(name)
        hire = sev.hire_date_from_roster(row) if row else None

        self._result = sev.calculate_severance(name, resign, hire, tenant_id=session_tenant_id())
        self._render_result(self._result)
        self._load_interim_list(name)

    def _render_result(self, result: SeveranceResult) -> None:
        for item in self._wage_tree.get_children():
            self._wage_tree.delete(item)

        for row in result.monthly_rows:
            days_txt = f"{row.days_in_window}/{row.days_in_month}"
            gross_txt = _won(row.gross_wage) if row.found else "-"
            ins_txt = _won(row.insurance_employee) if row.found else "-"
            prorated_txt = _won(row.prorated_wage) if row.found else "-"
            self._wage_tree.insert(
                "",
                tk.END,
                values=(row.period_label, days_txt, gross_txt, ins_txt, prorated_txt, row.note),
            )

        lines = [
            f"산정 구간: {_fmt_date(result.period_start)} ~ {_fmt_date(result.period_end)} ({result.calendar_days}일)",
            f"3개월 임금 합(비례): {_won(result.total_gross_3m)}  |  4대보험(근로자) 합: {_won(result.total_insurance_3m)}",
            f"평균임금(일): {_won(result.average_daily_wage)}",
            f"근속: {result.service.display} ({result.service.days}일)",
            f"법정 퇴직금: {_won(result.statutory_severance)}  (= 평균임금 × 30 × {result.service.years:.4f}년)",
        ]
        if result.warnings:
            lines.append("⚠ " + " / ".join(result.warnings))
        self._summary_var.set("\n".join(lines))

        self._final_var.set(
            f"중간정산 차감 {_won(result.interim_total)}  →  "
            f"최종 퇴직금 {_won(result.final_severance)}"
        )

    def _interim_items(self) -> dict[str, InterimSettlement]:
        name = self._employee_var.get().strip()
        items = sev.list_interim_settlements(name, tenant_id=session_tenant_id())
        return {i.id: i for i in items}

    def _load_interim_list(self, name: str) -> None:
        for item in self._interim_tree.get_children():
            self._interim_tree.delete(item)
        for item in sev.list_interim_settlements(name, tenant_id=session_tenant_id()):
            self._interim_tree.insert("", tk.END, iid=item.id, values=(item.date, _won(item.amount), item.reason))

    def _selected_interim_id(self) -> str | None:
        sel = self._interim_tree.selection()
        return sel[0] if sel else None

    def _add_interim(self) -> None:
        name = self._employee_var.get().strip()
        if not name:
            messagebox.showinfo("중간정산", "직원을 먼저 선택하세요.", parent=self.winfo_toplevel())
            return
        date_s = simpledialog.askstring("중간정산", "정산일 (YYYY.MM.DD):", parent=self.winfo_toplevel())
        if not date_s:
            return
        amount_s = simpledialog.askstring("중간정산", "정산 금액 (원):", parent=self.winfo_toplevel())
        if amount_s is None:
            return
        try:
            amount = int(str(amount_s).replace(",", "").strip())
        except ValueError:
            messagebox.showwarning("중간정산", "금액을 숫자로 입력하세요.", parent=self.winfo_toplevel())
            return
        reason = simpledialog.askstring("중간정산", "사유 (선택):", parent=self.winfo_toplevel()) or ""
        item = InterimSettlement(id="", employee_name=name, date=date_s.strip(), amount=amount, reason=reason.strip())
        sev.save_interim_settlement(item, tenant_id=session_tenant_id())
        self._load_interim_list(name)
        if self._result:
            self._calculate()

    def _edit_interim(self) -> None:
        iid = self._selected_interim_id()
        if not iid:
            messagebox.showinfo("중간정산", "수정할 항목을 선택하세요.", parent=self.winfo_toplevel())
            return
        items = self._interim_items()
        cur = items.get(iid)
        if not cur:
            return
        amount_s = simpledialog.askstring(
            "중간정산 수정",
            f"금액 (현재 {_won(cur.amount)}):",
            initialvalue=str(cur.amount),
            parent=self.winfo_toplevel(),
        )
        if amount_s is None:
            return
        try:
            amount = int(str(amount_s).replace(",", "").strip())
        except ValueError:
            messagebox.showwarning("중간정산", "금액을 숫자로 입력하세요.", parent=self.winfo_toplevel())
            return
        reason = simpledialog.askstring(
            "중간정산 수정",
            "사유:",
            initialvalue=cur.reason,
            parent=self.winfo_toplevel(),
        )
        if reason is None:
            return
        updated = InterimSettlement(
            id=cur.id,
            employee_name=cur.employee_name,
            date=cur.date,
            amount=amount,
            reason=reason.strip(),
        )
        sev.save_interim_settlement(updated, tenant_id=session_tenant_id())
        self._load_interim_list(cur.employee_name)
        if self._result:
            self._calculate()

    def _delete_interim(self) -> None:
        iid = self._selected_interim_id()
        if not iid:
            messagebox.showinfo("중간정산", "삭제할 항목을 선택하세요.", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno("중간정산", "선택한 중간정산을 삭제할까요?", parent=self.winfo_toplevel()):
            return
        sev.delete_interim_settlement(iid, tenant_id=session_tenant_id())
        name = self._employee_var.get().strip()
        self._load_interim_list(name)
        if self._result:
            self._calculate()
