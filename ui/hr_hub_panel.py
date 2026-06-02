"""
ui/hr_hub_panel.py - 인사 · 노무 통합 허브 (명부 + HR 레코드)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

from core.hr import service as hr_svc
from core.hr.service import ALL_TAB_IDS, RECORD_TAB_IDS, TAB_LABELS
from ui.compliance_docs_panel import ComplianceDocsPanel
from ui.employee_roster_panel import EmployeeRosterPanel
from ui.health_checkup_panel import HealthCheckupPanel
from ui.hr_onboarding_panel import HrOnboardingPanel
from ui.hr_recruitment_panel import HrRecruitmentPanel
from ui.hr_signal_panel import HrSignalPanel
from ui.severance_panel import SeverancePanel
from ui.module_hub_panel import ModuleHubPanel, ModuleHubSpec
from ui.theme import COLORS, FONT


class HrHubPanel(tk.Frame):
    """인사 플랫폼: 직원 명부 + 연차·근태·계약·증명서·노무·입퇴사."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_roster_saved: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_roster_saved = on_roster_saved
        self._active_tab = "roster"
        self._tab_btns: dict[str, tk.Button] = {}
        self._build()
        self.select_tab("roster")

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        head = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        inner = tk.Frame(head, bg=COLORS["card"], padx=18, pady=14)
        inner.pack(fill=tk.X)
        bar = tk.Frame(inner, bg="#0D9488", width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        txt = tk.Frame(inner, bg=COLORS["card"])
        txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            txt,
            text="인사 · 노무",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            txt,
            text=(
                "근로자 명부, 연차·휴가, 근태, 근로계약, 증명서, 노무·징계, 입·퇴사 절차·알림, "
                "정관·인사규정·법정 의무 문서함, 건강검진 대상 조회·결과지 제출, "
                "그룹 공유 채용공고·인재풀, Bitween 신호등(법인 간 채용 참고) "
                "(4대보험 취득/상실·퇴직금 등 법정 체크리스트)"
            ),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
            wraplength=720,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        actions = tk.Frame(inner, bg=COLORS["card"])
        actions.pack(side=tk.RIGHT)
        tk.Button(
            actions,
            text="＋ 등록",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._on_add,
        ).pack(side=tk.RIGHT)
        tk.Button(
            actions,
            text="새로고침",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 10),
            padx=10,
            pady=8,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        tab_bar = tk.Frame(self, bg=COLORS["bg"])
        tab_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for tid in ALL_TAB_IDS:
            btn = tk.Button(
                tab_bar,
                text=TAB_LABELS.get(tid, tid),
                relief=tk.FLAT,
                font=(FONT, 10),
                padx=12,
                pady=8,
                cursor="hand2",
                command=lambda t=tid: self.select_tab(t),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self._tab_btns[tid] = btn

        self._content = tk.Frame(self, bg=COLORS["bg"])
        self._content.grid(row=2, column=0, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._roster_host = tk.Frame(self._content, bg=COLORS["bg"])
        self.roster_panel = EmployeeRosterPanel(
            self._roster_host,
            on_saved=self._on_roster_saved,
        )
        self.roster_panel.pack(fill=tk.BOTH, expand=True)

        spec = ModuleHubSpec(
            platform_id="hr",
            title="인사 · 노무",
            accent="#0D9488",
            reference="",
            tab_ids=tuple(t for t in RECORD_TAB_IDS if t != "onboarding"),
            tab_labels={k: v for k, v in TAB_LABELS.items() if k in RECORD_TAB_IDS and k != "onboarding"},
            kpi_fn=hr_svc.dashboard_kpis,
            list_fn=hr_svc.list_records,
            columns_fn=hr_svc.tab_columns,
            form_fn=hr_svc.form_fields,
            add_fn=hr_svc.add_record,
            hide_header=True,
            hide_tabs=True,
        )
        self._records_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._records_hub = ModuleHubPanel(self._records_host, spec)
        self._records_hub.grid(row=0, column=0, sticky="nsew")
        self._records_host.grid_rowconfigure(0, weight=1)
        self._records_host.grid_columnconfigure(0, weight=1)

        self._onboarding_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._onboarding_host.grid_rowconfigure(0, weight=1)
        self._onboarding_host.grid_columnconfigure(0, weight=1)
        self.onboarding_panel = HrOnboardingPanel(
            self._onboarding_host,
            on_roster_synced=self._on_roster_synced,
        )
        self.onboarding_panel.grid(row=0, column=0, sticky="nsew")

        self._recruitment_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._recruitment_host.grid_rowconfigure(0, weight=1)
        self._recruitment_host.grid_columnconfigure(0, weight=1)
        self.recruitment_panel = HrRecruitmentPanel(self._recruitment_host)
        self.recruitment_panel.grid(row=0, column=0, sticky="nsew")

        self._signal_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._signal_host.grid_rowconfigure(0, weight=1)
        self._signal_host.grid_columnconfigure(0, weight=1)
        self.signal_panel = HrSignalPanel(self._signal_host)
        self.signal_panel.grid(row=0, column=0, sticky="nsew")

        self._severance_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._severance_host.grid_rowconfigure(0, weight=1)
        self._severance_host.grid_columnconfigure(0, weight=1)
        self.severance_panel = SeverancePanel(self._severance_host)
        self.severance_panel.grid(row=0, column=0, sticky="nsew")

        self._compliance_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._compliance_host.grid_rowconfigure(0, weight=1)
        self._compliance_host.grid_columnconfigure(0, weight=1)
        self.compliance_panel = ComplianceDocsPanel(self._compliance_host)
        self.compliance_panel.grid(row=0, column=0, sticky="nsew")

        self._health_checkup_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._health_checkup_host.grid_rowconfigure(0, weight=1)
        self._health_checkup_host.grid_columnconfigure(0, weight=1)
        self.health_checkup_panel = HealthCheckupPanel(self._health_checkup_host)
        self.health_checkup_panel.grid(row=0, column=0, sticky="nsew")

    def select_tab(self, tab_id: str) -> None:
        if tab_id not in ALL_TAB_IDS:
            return
        self._active_tab = tab_id
        accent = "#0D9488"
        for tid, btn in self._tab_btns.items():
            if tid == tab_id:
                btn.configure(bg=accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10))

        self._roster_host.grid_remove()
        self._records_host.grid_remove()
        self._onboarding_host.grid_remove()
        self._recruitment_host.grid_remove()
        self._signal_host.grid_remove()
        self._severance_host.grid_remove()
        self._compliance_host.grid_remove()
        self._health_checkup_host.grid_remove()

        if tab_id == "roster":
            self._roster_host.grid(row=0, column=0, sticky="nsew")
        elif tab_id == "onboarding":
            self._onboarding_host.grid(row=0, column=0, sticky="nsew")
            self.onboarding_panel.refresh()
        elif tab_id == "recruitment":
            self._recruitment_host.grid(row=0, column=0, sticky="nsew")
            self.recruitment_panel.refresh()
        elif tab_id == "signal":
            self._signal_host.grid(row=0, column=0, sticky="nsew")
        elif tab_id == "severance":
            self._severance_host.grid(row=0, column=0, sticky="nsew")
            self.severance_panel.refresh()
        elif tab_id == "compliance_docs":
            self._compliance_host.grid(row=0, column=0, sticky="nsew")
            self.compliance_panel.refresh()
        elif tab_id == "health_checkup":
            self._health_checkup_host.grid(row=0, column=0, sticky="nsew")
            self.health_checkup_panel.refresh()
        else:
            self._records_host.grid(row=0, column=0, sticky="nsew")
            self._records_hub.select_tab(tab_id)
            self._records_hub.refresh()

    def _on_roster_synced(self) -> None:
        self.roster_panel.reload(force=True)
        if self._on_roster_saved:
            self._on_roster_saved()

    def refresh(self) -> None:
        hr_svc.ensure_seed()
        if self._active_tab == "roster":
            self.roster_panel.reload(force=False)
        elif self._active_tab == "onboarding":
            self.onboarding_panel.refresh()
        elif self._active_tab == "recruitment":
            self.recruitment_panel.refresh()
        elif self._active_tab == "signal":
            pass
        elif self._active_tab == "severance":
            self.severance_panel.refresh()
        elif self._active_tab == "compliance_docs":
            self.compliance_panel.refresh()
        elif self._active_tab == "health_checkup":
            self.health_checkup_panel.refresh()
        else:
            self._records_hub.refresh()

    def _on_add(self) -> None:
        if self._active_tab == "roster":
            return
        if self._active_tab == "onboarding":
            self.onboarding_panel.add_case_dialog()
            return
        if self._active_tab == "recruitment":
            self.recruitment_panel._on_add()
            return
        if self._active_tab == "signal":
            messagebox.showinfo(
                "신호등",
                "주민등록번호를 입력하고 「신호등 조회」를 사용하세요.\n"
                "퇴사 신호등 등록은 「입 · 퇴사」 탭에서 퇴사 절차를 진행하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        if self._active_tab == "severance":
            self.severance_panel._add_interim()
            return
        if self._active_tab == "compliance_docs":
            self.compliance_panel._upload_dialog()
            return
        if self._active_tab == "health_checkup":
            messagebox.showinfo(
                "건강검진",
                "「HR · 명단 관리」에서 CSV 가져오기 또는 수동 등록을 사용하세요.\n"
                "직원은 「내 검진 대상」에서 사번·주민번호로 조회 후 결과지를 업로드할 수 있습니다.",
                parent=self.winfo_toplevel(),
            )
            return
        self._records_hub._on_add()


def build_hr_hub(parent: tk.Misc, *, on_roster_saved: Callable[[], None] | None = None) -> HrHubPanel:
    return HrHubPanel(parent, on_roster_saved=on_roster_saved)
