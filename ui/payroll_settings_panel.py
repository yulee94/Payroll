"""
ui/payroll_settings_panel.py - 급여 산출 설정 (휴업수당·사업장별 기본근로시간)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core.org_config import list_config_workplaces
from core.session_service import session_tenant_id
from services.payroll_settings_store import (
    LEGAL_MIN_SHUTDOWN_PAY_PERCENT,
    apply_tenant_defaults_to_all_sites,
    clear_job_group_template,
    clear_site_payroll_settings,
    copy_site_settings_from_tenant_default,
    clear_site_benefits_config,
    get_shutdown_pay_percent,
    get_site_benefits_config,
    get_site_extra_settings,
    get_tenant_site_benefits_defaults,
    load_payroll_settings,
    resolve_payroll_calc_settings,
    save_default_workplace_hours_policy,
    save_job_group_fixed_hours_template,
    save_shutdown_pay_percent,
    save_site_benefits_config,
    save_site_security_cleaning_flag,
    save_site_shutdown_pay_percent,
    save_tenant_site_benefits_defaults,
    save_workplace_hours_policy,
    settings_source_label,
    shutdown_pay_legal_notice,
)
from core.payroll.fixed_hours import DEFAULT_JOB_GROUP_TEMPLATES, PAY_TYPE_LABELS
from core.payroll.calc_breakdown import format_site_calc_breakdown_text
from services.workplace_hours import (
    MODE_CHOICES,
    MODE_FIXED,
    MODE_LABELS,
    list_all_workplace_policies,
    workplace_hours_help_text,
)
from ui.ei_65_panel import EmploymentInsurance65Panel
from ui.edi_insurance_panel import EdiInsurancePanel
from ui.theme import COLORS, FONT, FONT_BODY

TENANT_DEFAULT_LABEL = "(법인 기본 — 모든 사업장)"


class PayrollSettingsPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._scope_var = tk.StringVar(value=TENANT_DEFAULT_LABEL)
        self._percent_var = tk.StringVar()
        self._status_var = tk.StringVar()
        self._scope_hint_var = tk.StringVar()
        self._wp_mode_var = tk.StringVar(value=MODE_FIXED)
        self._wp_hours_var = tk.StringVar(value="209")
        self._daily_hours_var = tk.StringVar(value="")
        self._break_minutes_var = tk.StringVar(value="")
        self._sec_clean_var = tk.BooleanVar(value=False)
        self._jg_group_var = tk.StringVar(value="경비")
        self._jg_monthly_var = tk.StringVar(value="209")
        self._jg_special_var = tk.StringVar(value="0")
        self._jg_ot_var = tk.StringVar(value="0")
        self._jg_pay_type_var = tk.StringVar(value="시급")
        self._wd_enabled_var = tk.BooleanVar(value=False)
        self._wd_auto_invoice_var = tk.BooleanVar(value=True)
        self._wd_amount_var = tk.StringVar(value="0")
        self._ig_enabled_var = tk.BooleanVar(value=False)
        self._ig_amount_var = tk.StringVar(value="0")
        self._ig_month_var = tk.StringVar(value="1")
        self._build()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill=tk.BOTH, expand=True, anchor=tk.NW)

        canvas = tk.Canvas(outer, highlightthickness=0, bg=COLORS["bg"])
        scroll = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        pad = ttk.Frame(canvas)
        pad.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=pad, anchor=tk.NW)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(pad, text="급여 산출 설정", font=(FONT, 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text="휴업수당 비율과 사업장별 월 기본근로시간(기본급 = 기본시급 × 시간)을 설정합니다.",
            foreground="#555",
        ).pack(anchor=tk.W, pady=(4, 12))

        scope_box = ttk.LabelFrame(pad, text="설정 대상", padding=12)
        scope_box.pack(fill=tk.X, anchor=tk.W, pady=(0, 12))
        scope_row = ttk.Frame(scope_box)
        scope_row.pack(fill=tk.X)
        ttk.Label(scope_row, text="사업장", font=(FONT, 9, "bold")).pack(side=tk.LEFT)
        self._scope_combo = ttk.Combobox(
            scope_row,
            textvariable=self._scope_var,
            state="readonly",
            width=32,
        )
        self._scope_combo.pack(side=tk.LEFT, padx=(8, 12))
        self._scope_combo.bind("<<ComboboxSelected>>", self._on_scope_change)
        ttk.Label(
            scope_box,
            textvariable=self._scope_hint_var,
            foreground="#666",
        ).pack(anchor=tk.W, pady=(8, 0))

        calc_box = ttk.LabelFrame(pad, text="급여산출 설정", padding=16)
        calc_box.pack(fill=tk.X, anchor=tk.W, pady=(0, 16))

        shutdown_row = ttk.Frame(calc_box)
        shutdown_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(shutdown_row, text="휴업수당 지급률", font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        ttk.Entry(shutdown_row, textvariable=self._percent_var, width=8, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(12, 4)
        )
        ttk.Label(shutdown_row, text="%", font=FONT_BODY).pack(side=tk.LEFT)
        ttk.Label(
            shutdown_row,
            text=f"(법정 최저 {LEGAL_MIN_SHUTDOWN_PAY_PERCENT:g}% 이상)",
            foreground="#666",
        ).pack(side=tk.LEFT, padx=(12, 0))

        hours_row = ttk.Frame(calc_box)
        hours_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(hours_row, text="월 기본근로시간", font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        self._mode_combo = ttk.Combobox(
            hours_row,
            textvariable=self._wp_mode_var,
            values=[MODE_LABELS[m] for m in MODE_CHOICES],
            state="readonly",
            width=28,
        )
        self._mode_combo.pack(side=tk.LEFT, padx=(8, 8))
        ttk.Entry(hours_row, textvariable=self._wp_hours_var, width=8, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Label(hours_row, text="시간").pack(side=tk.LEFT)

        opt_row = ttk.Frame(calc_box)
        opt_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(opt_row, text="1일 근로(선택)", font=(FONT, 9)).pack(side=tk.LEFT)
        ttk.Entry(opt_row, textvariable=self._daily_hours_var, width=6, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(8, 4)
        )
        ttk.Label(opt_row, text="h").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(opt_row, text="휴계(선택)", font=(FONT, 9)).pack(side=tk.LEFT)
        ttk.Entry(opt_row, textvariable=self._break_minutes_var, width=6, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(8, 4)
        )
        ttk.Label(opt_row, text="분/일").pack(side=tk.LEFT)

        ttk.Label(
            calc_box,
            text=shutdown_pay_legal_notice(),
            wraplength=640,
            justify=tk.LEFT,
            foreground="#444",
        ).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(
            calc_box,
            text=workplace_hours_help_text(),
            wraplength=640,
            justify=tk.LEFT,
            foreground="#444",
        ).pack(anchor=tk.W, pady=(8, 0))

        btn_row = ttk.Frame(calc_box)
        btn_row.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(btn_row, text="저장", command=self._on_save_scope, width=10).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="기본값에서 복사", command=self._copy_from_default).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="모든 사업장에 적용", command=self._apply_to_all).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="개별 설정 삭제", command=self._clear_site).pack(side=tk.LEFT)
        ttk.Label(btn_row, textvariable=self._status_var, foreground=COLORS["nav_accent"]).pack(
            side=tk.LEFT, padx=(16, 0)
        )

        wp_box = ttk.LabelFrame(pad, text="사업장별 적용 현황", padding=16)
        wp_box.pack(fill=tk.BOTH, expand=True, anchor=tk.NW)

        table_wrap = ttk.Frame(wp_box)
        table_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        cols = ("workplace", "shutdown", "mode", "hours", "custom")
        self._wp_tree = ttk.Treeview(
            table_wrap,
            columns=cols,
            show="headings",
            height=8,
            selectmode="browse",
        )
        self._wp_tree.heading("workplace", text="사업장")
        self._wp_tree.heading("shutdown", text="휴업수당(%)")
        self._wp_tree.heading("mode", text="근로시간 산출")
        self._wp_tree.heading("hours", text="고정/대체(h)")
        self._wp_tree.heading("custom", text="개별")
        self._wp_tree.column("workplace", width=120)
        self._wp_tree.column("shutdown", width=88, anchor=tk.E)
        self._wp_tree.column("mode", width=200)
        self._wp_tree.column("hours", width=80, anchor=tk.E)
        self._wp_tree.column("custom", width=48, anchor=tk.CENTER)
        ysb = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self._wp_tree.yview)
        self._wp_tree.configure(yscrollcommand=ysb.set)
        self._wp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self._wp_tree.bind("<<TreeviewSelect>>", self._on_wp_select)

        ttk.Button(wp_box, text="목록 새로고침", command=self.refresh).pack(anchor=tk.W)

        sc_box = ttk.LabelFrame(pad, text="경비·미화 — 직군별 고정 근로시간", padding=12)
        sc_box.pack(fill=tk.X, anchor=tk.W, pady=(12, 0))
        ttk.Label(
            sc_box,
            text="사업장을 선택한 뒤 경비·미화 유형을 켜고, 직군별 월·특근·연장 고정시간을 설정합니다. "
            "근로계약서 개별 값이 우선 적용됩니다.",
            wraplength=640,
            foreground="#555",
        ).pack(anchor=tk.W, pady=(0, 8))
        sc_row1 = ttk.Frame(sc_box)
        sc_row1.pack(fill=tk.X, pady=(0, 6))
        ttk.Checkbutton(
            sc_row1,
            text="경비·미화 유형 사업장",
            variable=self._sec_clean_var,
            command=self._on_sec_clean_toggle,
        ).pack(side=tk.LEFT)
        sc_row2 = ttk.Frame(sc_box)
        sc_row2.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(sc_row2, text="직군", font=(FONT, 9, "bold")).pack(side=tk.LEFT)
        self._jg_combo = ttk.Combobox(
            sc_row2,
            textvariable=self._jg_group_var,
            values=list(DEFAULT_JOB_GROUP_TEMPLATES.keys()),
            width=10,
            state="readonly",
        )
        self._jg_combo.pack(side=tk.LEFT, padx=(8, 12))
        self._jg_combo.bind("<<ComboboxSelected>>", self._on_jg_select)
        ttk.Label(sc_row2, text="월(h)").pack(side=tk.LEFT)
        ttk.Entry(sc_row2, textvariable=self._jg_monthly_var, width=6, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Label(sc_row2, text="특근(h)").pack(side=tk.LEFT)
        ttk.Entry(sc_row2, textvariable=self._jg_special_var, width=5, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Label(sc_row2, text="연장(h)").pack(side=tk.LEFT)
        ttk.Entry(sc_row2, textvariable=self._jg_ot_var, width=5, font=FONT_BODY).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        ttk.Label(sc_row2, text="급여").pack(side=tk.LEFT)
        self._jg_pay_combo = ttk.Combobox(
            sc_row2,
            textvariable=self._jg_pay_type_var,
            values=list(PAY_TYPE_LABELS.values()),
            width=8,
            state="readonly",
        )
        self._jg_pay_combo.pack(side=tk.LEFT, padx=(4, 8))
        sc_btn = ttk.Frame(sc_box)
        sc_btn.pack(fill=tk.X)
        ttk.Button(sc_btn, text="직군 템플릿 저장", command=self._save_jg_template).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(sc_btn, text="직군 템플릿 삭제", command=self._clear_jg_template).pack(side=tk.LEFT)

        sb_box = ttk.LabelFrame(pad, text="사업장별 특수 항목", padding=12)
        sb_box.pack(fill=tk.X, anchor=tk.W, pady=(12, 0))
        ttk.Label(
            sb_box,
            text="근로자의 날 수당(청구서 연동)과 신원보증보험료(연 1회 공제)를 사업장별로 설정합니다. "
            "상단 사업장 선택과 동일한 범위에 저장됩니다.",
            wraplength=640,
            foreground="#555",
        ).pack(anchor=tk.W, pady=(0, 8))
        wd_row = ttk.Frame(sb_box)
        wd_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Checkbutton(
            wd_row,
            text="근로자의 날 수당 사용",
            variable=self._wd_enabled_var,
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            wd_row,
            text="청구서 금액 자동 반영",
            variable=self._wd_auto_invoice_var,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(wd_row, text="고정(5월)").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(wd_row, textvariable=self._wd_amount_var, width=8, font=FONT_BODY).pack(
            side=tk.LEFT
        )
        ttk.Label(wd_row, text="원").pack(side=tk.LEFT, padx=(4, 0))
        ig_row = ttk.Frame(sb_box)
        ig_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Checkbutton(
            ig_row,
            text="신원보증보험료 공제",
            variable=self._ig_enabled_var,
        ).pack(side=tk.LEFT)
        ttk.Label(ig_row, text="연간").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(ig_row, textvariable=self._ig_amount_var, width=8, font=FONT_BODY).pack(
            side=tk.LEFT
        )
        ttk.Label(ig_row, text="원 · 공제월").pack(side=tk.LEFT, padx=(4, 8))
        self._ig_month_combo = ttk.Combobox(
            ig_row,
            textvariable=self._ig_month_var,
            values=[str(m) for m in range(1, 13)],
            width=4,
            state="readonly",
        )
        self._ig_month_combo.pack(side=tk.LEFT)
        ttk.Label(ig_row, text="월").pack(side=tk.LEFT, padx=(4, 0))
        sb_btn = ttk.Frame(sb_box)
        sb_btn.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(sb_btn, text="특수 항목 저장", command=self._save_site_benefits).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(sb_btn, text="특수 항목 초기화", command=self._clear_site_benefits).pack(
            side=tk.LEFT
        )

        breakdown_box = ttk.LabelFrame(pad, text="산출내역 (선택 사업장)", padding=12)
        breakdown_box.pack(fill=tk.BOTH, expand=True, anchor=tk.NW, pady=(12, 0))
        bd_wrap = ttk.Frame(breakdown_box)
        bd_wrap.pack(fill=tk.BOTH, expand=True)
        bd_scroll = ttk.Scrollbar(bd_wrap, orient=tk.VERTICAL)
        self._breakdown_text = tk.Text(
            bd_wrap,
            height=10,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg="#FAFBFC",
            relief=tk.FLAT,
            padx=10,
            pady=8,
            yscrollcommand=bd_scroll.set,
        )
        bd_scroll.config(command=self._breakdown_text.yview)
        self._breakdown_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bd_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._breakdown_text.insert("1.0", "사업장을 선택하면 적용 근로시간과 산출 산식을 표시합니다.")
        self._breakdown_text.configure(state=tk.DISABLED)

        edi_box = ttk.LabelFrame(pad, text="EDI 보험료 조회 (사대보험)", padding=8)
        edi_box.pack(fill=tk.BOTH, expand=True, anchor=tk.NW, pady=(12, 0))
        self.edi_insurance_panel = EdiInsurancePanel(edi_box)
        self.edi_insurance_panel.pack(fill=tk.BOTH, expand=True)

        ei_box = ttk.LabelFrame(pad, text="만 65세 고용보험", padding=8)
        ei_box.pack(fill=tk.BOTH, expand=True, anchor=tk.NW, pady=(12, 0))
        self.ei_65_panel = EmploymentInsurance65Panel(ei_box)
        self.ei_65_panel.pack(fill=tk.BOTH, expand=True)

        self._mode_label_to_key = {v: k for k, v in MODE_LABELS.items()}
        self.refresh()

    def _scope_values(self) -> list[str]:
        return [TENANT_DEFAULT_LABEL] + list_config_workplaces()

    def _is_tenant_scope(self) -> bool:
        return self._scope_var.get().strip() == TENANT_DEFAULT_LABEL

    def _selected_workplace(self) -> str:
        if self._is_tenant_scope():
            return ""
        return self._scope_var.get().strip()

    def _tenant_id(self) -> str | None:
        return session_tenant_id()

    def refresh(self) -> None:
        tid = self._tenant_id()
        values = self._scope_values()
        current = self._scope_var.get().strip()
        self._scope_combo.configure(values=values)
        if current not in values:
            self._scope_var.set(TENANT_DEFAULT_LABEL)
        self._load_scope_form()
        self._status_var.set("")

        for item in self._wp_tree.get_children():
            self._wp_tree.delete(item)
        for row in list_all_workplace_policies(tenant_id=tid):
            self._wp_tree.insert(
                "",
                tk.END,
                iid=row["workplace"],
                values=(
                    row["workplace"],
                    f"{row.get('shutdown_pay_percent', get_shutdown_pay_percent(row['workplace'])):g}",
                    row["mode_label"],
                    f"{row['hours']:g}",
                    "●" if row["is_custom"] else "",
                ),
            )
        if hasattr(self, "edi_insurance_panel"):
            self.edi_insurance_panel.refresh()
        if hasattr(self, "ei_65_panel"):
            self.ei_65_panel.refresh()

    def _load_scope_form(self) -> None:
        tid = self._tenant_id()
        if self._is_tenant_scope():
            settings = load_payroll_settings(tenant_id=tid)
            shutdown = get_shutdown_pay_percent(tenant_id=tid)
            pol = settings.get("default_workplace_hours_policy") or {}
            self._scope_hint_var.set("법인 기본 — 개별 설정이 없는 사업장에 적용됩니다.")
        else:
            wp = self._selected_workplace()
            resolved = resolve_payroll_calc_settings(wp, tenant_id=tid)
            shutdown = resolved["shutdown_pay_percent"]
            pol = resolved["workplace_hours_policy"]
            self._scope_hint_var.set(
                f"사업장: {wp}  ·  휴업수당: {settings_source_label(resolved['shutdown_source'])}"
                f"  ·  근로시간: {settings_source_label(resolved['hours_source'])}"
            )
        self._percent_var.set(f"{shutdown:g}")
        mode_label = MODE_LABELS.get(pol.get("mode", MODE_FIXED), MODE_LABELS[MODE_FIXED])
        self._wp_mode_var.set(mode_label)
        self._wp_hours_var.set(f"{float(pol.get('hours', 209)):g}")
        self._daily_hours_var.set(
            f"{float(pol['daily_hours']):g}" if pol.get("daily_hours") else ""
        )
        self._break_minutes_var.set(
            f"{float(pol['break_minutes']):g}" if pol.get("break_minutes") else ""
        )
        self._load_sec_clean_form()
        self._load_site_benefits_form()
        self._refresh_breakdown_panel()

    def _load_site_benefits_form(self) -> None:
        if self._is_tenant_scope():
            benefits = get_tenant_site_benefits_defaults()
        else:
            benefits = get_site_benefits_config(self._selected_workplace())
            benefits = {
                "workers_day_allowance": benefits["workers_day_allowance"],
                "identity_guarantee_insurance": benefits["identity_guarantee_insurance"],
            }
        wd = benefits.get("workers_day_allowance") or {}
        ig = benefits.get("identity_guarantee_insurance") or {}
        self._wd_enabled_var.set(bool(wd.get("enabled")))
        self._wd_auto_invoice_var.set(bool(wd.get("auto_from_invoice", True)))
        self._wd_amount_var.set(str(int(wd.get("default_amount") or 0)))
        self._ig_enabled_var.set(bool(ig.get("enabled")))
        self._ig_amount_var.set(str(int(ig.get("annual_amount") or 0)))
        self._ig_month_var.set(str(int(ig.get("billing_month") or 1)))

    def _parse_benefit_amount(self, text: str) -> int:
        return max(0, int(float(text.strip().replace(",", "") or 0)))

    def _save_site_benefits(self) -> None:
        try:
            wd_amount = self._parse_benefit_amount(self._wd_amount_var.get())
            ig_amount = self._parse_benefit_amount(self._ig_amount_var.get())
            ig_month = int(self._ig_month_var.get() or 1)
            if ig_month < 1 or ig_month > 12:
                raise ValueError("공제월은 1~12 사이여야 합니다.")
        except ValueError as exc:
            messagebox.showerror("입력 오류", str(exc), parent=self.winfo_toplevel())
            return
        workers_day = {
            "enabled": self._wd_enabled_var.get(),
            "default_amount": wd_amount,
            "auto_from_invoice": self._wd_auto_invoice_var.get(),
        }
        identity_insurance = {
            "enabled": self._ig_enabled_var.get(),
            "annual_amount": ig_amount,
            "billing_month": ig_month,
        }
        try:
            if self._is_tenant_scope():
                save_tenant_site_benefits_defaults(
                    workers_day=workers_day,
                    identity_insurance=identity_insurance,
                )
                self._status_var.set("법인 기본 — 특수 항목 저장됨")
            else:
                save_site_benefits_config(
                    self._selected_workplace(),
                    workers_day=workers_day,
                    identity_insurance=identity_insurance,
                )
                self._status_var.set(
                    f"사업장: {self._selected_workplace()} — 특수 항목 저장됨"
                )
        except ValueError as exc:
            messagebox.showerror("저장 실패", str(exc), parent=self.winfo_toplevel())
            return
        self._refresh_breakdown_panel()

    def _clear_site_benefits(self) -> None:
        if self._is_tenant_scope():
            save_tenant_site_benefits_defaults(
                workers_day={"enabled": False, "default_amount": 0, "auto_from_invoice": True},
                identity_insurance={"enabled": False, "annual_amount": 0, "billing_month": 1},
            )
            self._status_var.set("법인 기본 — 특수 항목 초기화됨")
        else:
            if not messagebox.askyesno(
                "확인",
                f"「{self._selected_workplace()}」 사업장 특수 항목 개별 설정을 삭제할까요?",
                parent=self.winfo_toplevel(),
            ):
                return
            clear_site_benefits_config(self._selected_workplace())
            self._status_var.set(
                f"사업장: {self._selected_workplace()} — 특수 항목 법인 기본 적용"
            )
        self._load_site_benefits_form()
        self._refresh_breakdown_panel()

    def _load_sec_clean_form(self) -> None:
        if self._is_tenant_scope():
            self._sec_clean_var.set(False)
            return
        extra = get_site_extra_settings(self._selected_workplace(), tenant_id=self._tenant_id())
        self._sec_clean_var.set(bool(extra.get("security_cleaning")))
        templates = extra.get("job_group_templates") or {}
        jg = self._jg_group_var.get().strip() or "경비"
        tpl = templates.get(jg) or DEFAULT_JOB_GROUP_TEMPLATES.get(jg, {})
        self._jg_monthly_var.set(f"{float(tpl.get('monthly_fixed_hours', 209)):g}")
        self._jg_special_var.set(f"{float(tpl.get('fixed_overtime_hours', 0)):g}")
        self._jg_ot_var.set(f"{float(tpl.get('fixed_extension_hours', 0)):g}")
        pay_key = tpl.get("pay_type", "hourly")
        self._jg_pay_type_var.set(PAY_TYPE_LABELS.get(pay_key, "시급"))

    def _on_sec_clean_toggle(self) -> None:
        if self._is_tenant_scope():
            messagebox.showinfo(
                "안내",
                "사업장을 선택한 뒤 경비·미화 설정을 변경할 수 있습니다.",
                parent=self.winfo_toplevel(),
            )
            self._sec_clean_var.set(False)
            return
        try:
            save_site_security_cleaning_flag(
                self._selected_workplace(),
                self._sec_clean_var.get(),
                tenant_id=self._tenant_id(),
            )
        except ValueError as exc:
            messagebox.showerror("저장 실패", str(exc), parent=self.winfo_toplevel())

    def _on_jg_select(self, _event=None) -> None:
        self._load_sec_clean_form()

    def _pay_type_key(self, label: str) -> str:
        for key, lbl in PAY_TYPE_LABELS.items():
            if lbl == label.strip():
                return key
        return "hourly"

    def _save_jg_template(self) -> None:
        if self._is_tenant_scope():
            messagebox.showinfo(
                "안내",
                "사업장을 선택한 뒤 직군 템플릿을 저장하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        wp = self._selected_workplace()
        jg = self._jg_group_var.get().strip()
        try:
            save_job_group_fixed_hours_template(
                wp,
                jg,
                monthly_fixed_hours=self._parse_hours(self._jg_monthly_var.get()),
                fixed_overtime_hours=float(self._jg_special_var.get() or 0),
                fixed_extension_hours=float(self._jg_ot_var.get() or 0),
                pay_type=self._pay_type_key(self._jg_pay_type_var.get()),
                tenant_id=self._tenant_id(),
            )
            self._sec_clean_var.set(True)
            self._status_var.set(f"사업장: {wp} — {jg} 직군 템플릿 저장")
            self._refresh_breakdown_panel()
        except ValueError as exc:
            messagebox.showerror("저장 실패", str(exc), parent=self.winfo_toplevel())

    def _clear_jg_template(self) -> None:
        if self._is_tenant_scope():
            return
        wp = self._selected_workplace()
        jg = self._jg_group_var.get().strip()
        clear_job_group_template(wp, jg, tenant_id=self._tenant_id())
        self._status_var.set(f"사업장: {wp} — {jg} 템플릿 삭제")
        self._load_sec_clean_form()
        self._refresh_breakdown_panel()

    def _refresh_breakdown_panel(self) -> None:
        self._breakdown_text.configure(state=tk.NORMAL)
        self._breakdown_text.delete("1.0", tk.END)
        if self._is_tenant_scope():
            self._breakdown_text.insert(
                "1.0",
                "법인 기본을 편집 중입니다.\n"
                "사업장을 선택하거나 아래 목록에서 클릭하면 해당 사업장의 산출내역을 볼 수 있습니다.",
            )
        else:
            text = format_site_calc_breakdown_text(self._selected_workplace())
            self._breakdown_text.insert("1.0", text)
        self._breakdown_text.configure(state=tk.DISABLED)

    def _on_scope_change(self, _event=None) -> None:
        self._load_scope_form()
        self._status_var.set("")

    def _on_wp_select(self, _event=None) -> None:
        sel = self._wp_tree.selection()
        if not sel:
            return
        wp = sel[0]
        self._scope_var.set(wp)
        self._load_scope_form()

    def _parse_hours(self, text: str) -> float:
        return float(text.strip().replace(",", ""))

    def _parse_optional_float(self, text: str) -> float | None:
        raw = text.strip().replace(",", "")
        if not raw:
            return None
        return float(raw)

    def _optional_hours_kwargs(self) -> dict[str, float]:
        kwargs: dict[str, float] = {}
        try:
            daily = self._parse_optional_float(self._daily_hours_var.get())
            if daily is not None and daily > 0:
                kwargs["daily_hours"] = daily
        except ValueError:
            raise ValueError("1일 근로시간을 숫자로 입력하세요.") from None
        try:
            br = self._parse_optional_float(self._break_minutes_var.get())
            if br is not None and br >= 0:
                kwargs["break_minutes"] = br
        except ValueError:
            raise ValueError("휴계 시간(분)을 숫자로 입력하세요.") from None
        return kwargs

    def _mode_key_from_label(self, label: str) -> str:
        return self._mode_label_to_key.get(label.strip(), MODE_FIXED)

    def _parse_shutdown_percent(self) -> float | None:
        raw = self._percent_var.get().strip().replace(",", "").replace("%", "")
        try:
            return float(raw)
        except ValueError:
            messagebox.showerror(
                "입력 오류",
                f"휴업수당 비율을 숫자로 입력해 주세요.\n(법정 최저 {LEGAL_MIN_SHUTDOWN_PAY_PERCENT:g}%)",
                parent=self.winfo_toplevel(),
            )
            return None

    def _on_save_scope(self) -> None:
        value = self._parse_shutdown_percent()
        if value is None:
            return
        mode = self._mode_key_from_label(self._wp_mode_var.get())
        try:
            hours = self._parse_hours(self._wp_hours_var.get())
            opt = self._optional_hours_kwargs()
        except ValueError as exc:
            messagebox.showerror("입력 오류", str(exc), parent=self.winfo_toplevel())
            return

        tid = self._tenant_id()
        if self._is_tenant_scope():
            applied_shutdown = save_shutdown_pay_percent(value, tenant_id=tid)
            applied_hours = save_default_workplace_hours_policy(
                mode=mode, hours=hours, tenant_id=tid, **opt
            )
            self._status_var.set(
                f"법인 기본 저장 — 휴업 {applied_shutdown:g}% · "
                f"{MODE_LABELS.get(applied_hours['mode'], '')} {applied_hours['hours']:g}시간"
            )
        else:
            wp = self._selected_workplace()
            try:
                applied_shutdown = save_site_shutdown_pay_percent(wp, value, tenant_id=tid)
                applied_hours = save_workplace_hours_policy(
                    wp, mode=mode, hours=hours, tenant_id=tid, **opt
                )
            except ValueError as exc:
                messagebox.showerror("저장 실패", str(exc), parent=self.winfo_toplevel())
                return
            self._status_var.set(
                f"사업장: {wp} 저장 — 휴업 {applied_shutdown:g}% · "
                f"{MODE_LABELS.get(applied_hours['mode'], '')} {applied_hours['hours']:g}시간"
            )
        self.refresh()

    def _copy_from_default(self) -> None:
        if self._is_tenant_scope():
            messagebox.showinfo(
                "안내",
                "법인 기본을 편집 중입니다. 사업장을 선택한 뒤 「기본값에서 복사」를 사용하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        wp = self._selected_workplace()
        try:
            copy_site_settings_from_tenant_default(wp, tenant_id=self._tenant_id())
        except ValueError as exc:
            messagebox.showerror("복사 실패", str(exc), parent=self.winfo_toplevel())
            return
        self._status_var.set(f"사업장: {wp} — 법인 기본값으로 복사됨")
        self.refresh()

    def _apply_to_all(self) -> None:
        if not messagebox.askyesno(
            "확인",
            "법인 기본값을 organizations.json에 등록된 모든 사업장에 일괄 적용할까요?",
            parent=self.winfo_toplevel(),
        ):
            return
        count = apply_tenant_defaults_to_all_sites(tenant_id=self._tenant_id())
        self._status_var.set(f"법인 기본값을 {count}개 사업장에 적용했습니다.")
        self.refresh()

    def _clear_site(self) -> None:
        if self._is_tenant_scope():
            messagebox.showinfo(
                "안내",
                "사업장을 선택한 뒤 개별 설정을 삭제할 수 있습니다.",
                parent=self.winfo_toplevel(),
            )
            return
        wp = self._selected_workplace()
        if not messagebox.askyesno(
            "확인",
            f"「{wp}」 사업장 개별 설정을 삭제하고 법인/전역 기본을 사용할까요?",
            parent=self.winfo_toplevel(),
        ):
            return
        clear_site_payroll_settings(wp, tenant_id=self._tenant_id())
        self._status_var.set(f"사업장: {wp} — 개별 설정 삭제됨")
        self.refresh()
