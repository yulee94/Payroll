"""
ui/edi_insurance_panel.py - 사대보험 EDI 4대보험료 조회 UI
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from core.payroll import edi_insurance as edi
from core.tenant_store import get_active_tenant_id
from services.payroll_settings_store import get_edi_insurance_config, save_edi_insurance_config
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


class EdiInsurancePanel(tk.Frame):
    """EDI 보험료 조회 — 급여 설정 · 회계/경리 연동용."""

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, bg=COLORS["bg"], **kwargs)
        self._period_var = tk.StringVar()
        self._use_edi_var = tk.BooleanVar(value=False)
        self._cert_var = tk.StringVar()
        self._biz_var = tk.StringVar()
        self._endpoint_var = tk.StringVar()
        self._status_var = tk.StringVar()
        self._roster: dict[str, dict[str, Any]] = {}
        self._rows: list[dict[str, Any]] = []
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#EFF6FF", highlightbackground="#93C5FD", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=edi.help_text_ko().replace("\n", "  "),
            bg="#EFF6FF",
            fg="#1E40AF",
            font=(FONT, 9),
            wraplength=920,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        cert_box = ttk.LabelFrame(self, text="EDI 연동 설정 (Phase 2 · 선택)", padding=8)
        cert_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        row1 = ttk.Frame(cert_box)
        row1.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(
            row1,
            text="EDI 보험료로 급여 반영 (use_edi_premiums)",
            variable=self._use_edi_var,
            command=self._save_config,
        ).pack(side=tk.LEFT)
        tk.Button(
            row1,
            text="설정 저장",
            bg=COLORS["card"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._save_config,
        ).pack(side=tk.RIGHT)

        for label, var, width in (
            ("인증서 경로", self._cert_var, 48),
            ("사업자등록번호", self._biz_var, 24),
            ("API 엔드포인트 URL", self._endpoint_var, 48),
        ):
            r = ttk.Frame(cert_box)
            r.pack(fill=tk.X, pady=2)
            ttk.Label(r, text=label, width=16).pack(side=tk.LEFT)
            ttk.Entry(r, textvariable=var, width=width, font=FONT_BODY).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
            )

        ttk.Label(
            cert_box,
            text=(
                "※ 공인인증서·공동인증서 또는 EDI 전용 인증서, 사업장 EDI 가입, "
                "공단별 웹서비스 이용계약이 필요합니다. 임의 앱용 공개 REST API는 제공되지 않습니다."
            ),
            foreground="#666",
            wraplength=880,
        ).pack(anchor=tk.W, pady=(6, 0))

        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        tk.Label(toolbar, text="급여월", bg=COLORS["bg"], font=(FONT, 9, "bold")).pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self._period_var, width=10, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(6, 12)
        )
        for text, cmd in (
            ("새로고침", self.refresh),
            ("수동 등록", self._manual_entry),
            ("CSV 가져오기", self._import_csv),
            ("월별 일괄 조회", self._batch_fetch),
        ):
            tk.Button(
                toolbar,
                text=text,
                bg=COLORS["card"] if text != "수동 등록" else "#2563EB",
                fg="#FFFFFF" if text == "수동 등록" else COLORS.get("text", "#111"),
                relief=tk.FLAT,
                font=(FONT, 9, "bold" if text == "수동 등록" else "normal"),
                padx=10,
                pady=4,
                cursor="hand2",
                command=cmd,
            ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            toolbar,
            text="EDI API 연동 (준비중)",
            bg="#E5E7EB",
            fg="#6B7280",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            state=tk.DISABLED,
        ).pack(side=tk.LEFT, padx=(0, 6))

        portal = tk.Menubutton(
            toolbar,
            text="공단 포털 ▾",
            bg=COLORS["card"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=8,
            pady=4,
        )
        portal_menu = tk.Menu(portal, tearoff=0)
        portal_menu.add_command(
            label="국민연금 (NPS)",
            command=lambda: webbrowser.open(edi.NPS_EDI_URL),
        )
        portal_menu.add_command(
            label="국민건강보험 (NHIS)",
            command=lambda: webbrowser.open(edi.NHIS_EDI_URL),
        )
        portal_menu.add_command(
            label="근로복지공단 (고용·산재)",
            command=lambda: webbrowser.open(edi.KCOMWEL_EDI_URL),
        )
        portal["menu"] = portal_menu
        portal.pack(side=tk.LEFT)

        body = tk.Frame(
            self,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        body.grid(row=3, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        cols = (
            "employee_name",
            "employee_id",
            "workplace",
            "source_label",
            "national_pension",
            "health_insurance",
            "employment_insurance",
            "fetched_at",
        )
        self._tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse", height=10)
        headings = (
            ("employee_name", "성명", 80),
            ("employee_id", "사번", 72),
            ("workplace", "근무지", 96),
            ("source_label", "출처", 88),
            ("national_pension", "국민연금", 80),
            ("health_insurance", "건강보험", 80),
            ("employment_insurance", "고용보험", 80),
            ("fetched_at", "조회일시", 120),
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
        ).grid(row=4, column=0, sticky="ew", pady=(6, 0))

    def set_roster(self, roster: dict[str, dict[str, Any]] | None) -> None:
        self._roster = roster or {}

    def set_payroll_period(self, period: str) -> None:
        self._period_var.set(period)

    def _load_config_form(self) -> None:
        cfg = get_edi_insurance_config(tenant_id=get_active_tenant_id())
        self._use_edi_var.set(bool(cfg.get("use_edi_premiums")))
        self._cert_var.set(str(cfg.get("certificate_path") or ""))
        self._biz_var.set(str(cfg.get("business_registration_no") or ""))
        self._endpoint_var.set(str(cfg.get("api_endpoint_url") or ""))

    def _save_config(self) -> None:
        save_edi_insurance_config(
            use_edi_premiums=self._use_edi_var.get(),
            certificate_path=self._cert_var.get(),
            business_registration_no=self._biz_var.get(),
            api_endpoint_url=self._endpoint_var.get(),
            tenant_id=get_active_tenant_id(),
        )
        self._status_var.set("EDI 설정이 저장되었습니다.")

    def refresh(self) -> None:
        from datetime import datetime

        period = self._period_var.get().strip()
        if not period:
            period = datetime.now().strftime("%Y-%m")
            self._period_var.set(period)

        self._load_config_form()
        tenant_id = get_active_tenant_id()

        if not self._roster:
            try:
                from roster_workbook import load_employee_roster

                self._roster = load_employee_roster() or {}
            except Exception:
                self._roster = {}

        for item in self._tree.get_children():
            self._tree.delete(item)

        self._rows = edi.list_roster_edi_status(
            self._roster,
            payroll_period=period,
            tenant_id=tenant_id,
        )

        for row in self._rows:
            def _amt(v: Any) -> str:
                return f"{int(v):,}" if v is not None else "—"

            tag = "edi" if row.get("has_edi") else "calc"
            self._tree.insert(
                "",
                tk.END,
                values=(
                    row.get("employee_name", ""),
                    row.get("employee_id", ""),
                    row.get("workplace", ""),
                    row.get("source_label", ""),
                    _amt(row.get("national_pension")),
                    _amt(row.get("health_insurance")),
                    _amt(row.get("employment_insurance")),
                    row.get("fetched_at", "") or "—",
                ),
                tags=(tag,),
            )

        self._tree.tag_configure("edi", foreground="#059669")
        self._tree.tag_configure("calc", foreground="#6B7280")

        edi_count = sum(1 for r in self._rows if r.get("has_edi"))
        use = "ON" if self._use_edi_var.get() else "OFF"
        self._status_var.set(
            f"급여월 {period} · EDI 조회 {edi_count}/{len(self._rows)}명 · 급여 반영 {use}"
        )

    def _selected_row(self) -> dict[str, Any] | None:
        sel = self._tree.selection()
        if not sel:
            return None
        idx = self._tree.index(sel[0])
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def _manual_entry(self) -> None:
        row = self._selected_row()
        period = self._period_var.get().strip()
        emp_id = simpledialog.askstring(
            "수동 등록",
            "사번:",
            initialvalue=(row or {}).get("employee_id", ""),
            parent=self.winfo_toplevel(),
        )
        if emp_id is None:
            return
        name = simpledialog.askstring(
            "수동 등록",
            "성명:",
            initialvalue=(row or {}).get("employee_name", ""),
            parent=self.winfo_toplevel(),
        )
        if not name:
            return
        np_amt = simpledialog.askstring("수동 등록", "국민연금(원):", initialvalue="0", parent=self.winfo_toplevel())
        if np_amt is None:
            return
        hi_amt = simpledialog.askstring("수동 등록", "건강보험(원):", initialvalue="0", parent=self.winfo_toplevel())
        if hi_amt is None:
            return
        ei_amt = simpledialog.askstring("수동 등록", "고용보험(원):", initialvalue="0", parent=self.winfo_toplevel())
        if ei_amt is None:
            return
        try:
            edi.add_premium_manual(
                tenant_id=get_active_tenant_id(),
                employee_id=emp_id.strip(),
                employee_name=name.strip(),
                period=period,
                national_pension=np_amt,
                health_insurance=hi_amt,
                employment_insurance=ei_amt,
            )
        except Exception as exc:
            messagebox.showerror("등록 실패", str(exc), parent=self.winfo_toplevel())
            return
        messagebox.showinfo("완료", "보험료가 등록되었습니다.", parent=self.winfo_toplevel())
        self.refresh()

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="EDI 보험료 CSV",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        period = self._period_var.get().strip() or None
        try:
            summary = edi.import_premiums_csv(
                path,
                default_period=period,
                tenant_id=get_active_tenant_id(),
            )
        except Exception as exc:
            messagebox.showerror("가져오기 실패", str(exc), parent=self.winfo_toplevel())
            return
        messagebox.showinfo(
            "완료",
            f"{summary.get('imported_count', 0)}건 · 기간 {', '.join(summary.get('periods') or [])}",
            parent=self.winfo_toplevel(),
        )
        self.refresh()

    def _batch_fetch(self) -> None:
        period = self._period_var.get().strip()
        if not self._roster:
            messagebox.showwarning("명부 없음", "직원 명부를 불러올 수 없습니다.", parent=self.winfo_toplevel())
            return
        summary = edi.batch_fetch_for_payroll(
            self._roster,
            payroll_period=period,
            tenant_id=get_active_tenant_id(),
        )
        msg = (
            f"EDI 저장/조회 {summary.get('fetched_count', 0)}명 · "
            f"미조회 {summary.get('missing_count', 0)}명"
        )
        if summary.get("errors"):
            msg += f"\n(오류 {len(summary['errors'])}건)"
        messagebox.showinfo("일괄 조회", msg, parent=self.winfo_toplevel())
        self.refresh()
