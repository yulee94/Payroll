"""
ui/ei_65_panel.py - 만 65세 고용보험 KCOMWEL 확인 UI
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from core.payroll import employment_insurance_65 as ei65
from core.tenant_store import get_active_tenant_id
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


def _status_fg(status: str) -> str:
    if status == "liable":
        return "#059669"
    if status == "exempt":
        return COLORS["muted"]
    return "#D97706"


class EmploymentInsurance65Panel(tk.Frame):
    """만 65세 이상 고용보험 KCOMWEL 확인 — 급여 설정 하위."""

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, bg=COLORS["bg"], **kwargs)
        self._period_var = tk.StringVar()
        self._default_var = tk.StringVar(value="skip")
        self._status_var = tk.StringVar()
        self._roster: dict[str, dict[str, Any]] = {}
        self._rows: list[dict[str, Any]] = []
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#FFF7ED", highlightbackground="#FDBA74", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=ei65.help_text_ko().replace("\n", "  "),
            bg="#FFF7ED",
            fg="#9A3412",
            font=(FONT, 9),
            wraplength=900,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        tk.Label(toolbar, text="급여월", bg=COLORS["bg"], font=(FONT, 9, "bold")).pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self._period_var, width=10, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(6, 12)
        )
        tk.Button(
            toolbar,
            text="새로고침",
            bg=COLORS["card"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            toolbar,
            text="수동 확인 등록",
            bg="#EA580C",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._manual_verify,
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            toolbar,
            text="CSV 가져오기",
            bg=COLORS["card"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._import_csv,
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            toolbar,
            text="KCOMWEL 포털",
            bg=COLORS["card"],
            fg="#0369A1",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: webbrowser.open(ei65.KCOMWEL_PORTAL_URL),
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            toolbar,
            text="API 연동 준비중",
            bg="#E5E7EB",
            fg="#6B7280",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            state=tk.DISABLED,
        ).pack(side=tk.LEFT)

        default_row = tk.Frame(toolbar, bg=COLORS["bg"])
        default_row.pack(side=tk.RIGHT)
        tk.Label(
            default_row,
            text="미확인 시 기본",
            bg=COLORS["bg"],
            font=(FONT, 9),
        ).pack(side=tk.LEFT)
        ttk.Combobox(
            default_row,
            textvariable=self._default_var,
            values=("skip", "deduct"),
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT, padx=(4, 4))
        tk.Button(
            default_row,
            text="저장",
            bg=COLORS["card"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._save_default,
        ).pack(side=tk.LEFT)

        body = tk.Frame(
            self,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        cols = (
            "employee_name",
            "age",
            "workplace",
            "site_management_no",
            "management_no",
            "check_date",
            "premium_amount",
            "deduct_label",
            "status_label",
        )
        self._tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse", height=12)
        headings = (
            ("employee_name", "성명", 88),
            ("age", "나이", 44),
            ("workplace", "근무지", 100),
            ("site_management_no", "사업장 관리번호", 110),
            ("management_no", "조회 관리번호", 110),
            ("check_date", "조회일", 88),
            ("premium_amount", "부과고지보험료", 110),
            ("deduct_label", "납부", 72),
            ("status_label", "상태", 100),
        )
        for col, label, w in headings:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=w, minwidth=40)
        sv = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sv.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        sv.grid(row=0, column=1, sticky="ns", pady=10)
        bind_local_wheel(self._tree)

        tk.Label(
            self,
            textvariable=self._status_var,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        ).grid(row=3, column=0, sticky="ew", pady=(6, 0))

    def set_roster(self, roster: dict[str, dict[str, Any]] | None) -> None:
        self._roster = roster or {}

    def set_payroll_period(self, period: str) -> None:
        self._period_var.set(period)

    def refresh(self) -> None:
        period = self._period_var.get().strip()
        if not period:
            from datetime import datetime

            period = datetime.now().strftime("%Y-%m")
            self._period_var.set(period)

        tenant_id = get_active_tenant_id()
        self._default_var.set(ei65.get_unknown_default(tenant_id=tenant_id))

        for item in self._tree.get_children():
            self._tree.delete(item)

        if not self._roster:
            try:
                from roster_workbook import load_employee_roster

                self._roster = load_employee_roster() or {}
            except Exception:
                self._roster = {}

        self._rows = ei65.list_65_plus_roster_rows(
            self._roster,
            payroll_period=period,
            tenant_id=tenant_id,
        )

        for row in self._rows:
            premium = row.get("premium_amount")
            premium_text = f"{premium:,}" if premium is not None else "—"
            self._tree.insert(
                "",
                tk.END,
                values=(
                    row.get("employee_name", ""),
                    row.get("age", "—"),
                    row.get("workplace", ""),
                    row.get("site_management_no", ""),
                    row.get("management_no", ""),
                    row.get("check_date", ""),
                    premium_text,
                    row.get("deduct_label", ""),
                    row.get("status_label", ""),
                ),
            )

        pending = sum(1 for r in self._rows if r.get("status") == "unknown")
        self._status_var.set(
            f"만 65세 이상 {len(self._rows)}명 · 미확인 {pending}명 · "
            f"급여월 {period} 기준"
        )

    def _selected_row(self) -> dict[str, Any] | None:
        sel = self._tree.selection()
        if not sel:
            return None
        idx = self._tree.index(sel[0])
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def _manual_verify(self) -> None:
        row = self._selected_row()
        name = simpledialog.askstring(
            "수동 확인",
            "성명:",
            initialvalue=(row or {}).get("employee_name", ""),
            parent=self.winfo_toplevel(),
        )
        if not name:
            return
        mgmt = simpledialog.askstring(
            "수동 확인",
            "관리번호:",
            initialvalue=(row or {}).get("management_no") or (row or {}).get("site_management_no", ""),
            parent=self.winfo_toplevel(),
        )
        if mgmt is None:
            return
        premium = simpledialog.askstring(
            "수동 확인",
            "부과고지보험료 (0 = 납부 없음):",
            initialvalue="0",
            parent=self.winfo_toplevel(),
        )
        if premium is None:
            return
        try:
            ei65.add_verification_manual(
                tenant_id=get_active_tenant_id(),
                employee_id=str((row or {}).get("employee_id") or ""),
                employee_name=name.strip(),
                management_no=str(mgmt or "").strip(),
                premium_amount=premium,
            )
        except Exception as exc:
            messagebox.showerror("등록 실패", str(exc), parent=self.winfo_toplevel())
            return
        messagebox.showinfo("완료", "확인 결과가 등록되었습니다.", parent=self.winfo_toplevel())
        self.refresh()

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="KCOMWEL 조회 결과 CSV",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        try:
            summary = ei65.import_verifications_csv(path, tenant_id=get_active_tenant_id())
        except Exception as exc:
            messagebox.showerror("가져오기 실패", str(exc), parent=self.winfo_toplevel())
            return
        messagebox.showinfo(
            "완료",
            f"{summary.get('imported_count', 0)}건을 가져왔습니다.",
            parent=self.winfo_toplevel(),
        )
        self.refresh()

    def _save_default(self) -> None:
        val = self._default_var.get().strip().lower()
        action = "deduct" if val == "deduct" else "skip"
        ei65.set_unknown_default(action, tenant_id=get_active_tenant_id())
        label = "공제 적용" if action == "deduct" else "공제 생략"
        self._status_var.set(f"미확인 기본값: {label}")
        messagebox.showinfo("저장", f"미확인 시 기본 동작: {label}", parent=self.winfo_toplevel())
