"""
ui/module_hub_panel.py - 사업부 플랫폼 공통 허브 (탭·KPI·목록·등록)

정비·입찰·회계 등 ERP형 모듈의 MVP UI.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from core.session_service import get_session
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


@dataclass(frozen=True)
class ModuleHubSpec:
    platform_id: str
    title: str
    accent: str
    reference: str
    tab_ids: tuple[str, ...]
    tab_labels: dict[str, str]
    kpi_fn: Callable[[], list[tuple[str, str, str]]]
    list_fn: Callable[[str], list[dict[str, Any]]]
    columns_fn: Callable[[str], tuple[tuple[str, str, int], ...]]
    form_fn: Callable[[str], tuple[tuple[str, str, bool], ...]]
    add_fn: Callable[[str, dict[str, str]], dict[str, Any]]
    hide_header: bool = False
    hide_tabs: bool = False


class ModuleHubPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, spec: ModuleHubSpec, **kwargs) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._spec = spec
        self._active_tab = spec.tab_ids[0] if spec.tab_ids else "home"
        self._tab_btns: dict[str, tk.Button] = {}
        self._tree: ttk.Treeview | None = None
        self._kpi_labels: list[tk.Label] = []
        self._list_row = 0

        self.grid_columnconfigure(0, weight=1)

        row = 0
        if not spec.hide_header:
            self._build_header(row)
            row += 1
        self._build_kpi_row(row)
        row += 1
        if not spec.hide_tabs:
            self._build_tab_bar(row)
            row += 1
        self._list_row = row
        self._build_list_area(row)
        self.grid_rowconfigure(self._list_row, weight=1)
        self._select_tab(self._active_tab)

    def select_tab(self, tab_id: str) -> None:
        if tab_id in self._spec.tab_ids:
            self._select_tab(tab_id)

    def refresh(self) -> None:
        self._refresh_kpis()
        self._reload_tree()

    def _build_header(self, row: int = 0) -> None:
        head = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        head.grid(row=row, column=0, sticky="ew", padx=0, pady=(0, 10))
        inner = tk.Frame(head, bg=COLORS["card"])
        inner.pack(fill=tk.X, padx=18, pady=14)

        bar = tk.Frame(inner, bg=self._spec.accent, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        txt = tk.Frame(inner, bg=COLORS["card"])
        txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            txt,
            text=self._spec.title,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            txt,
            text=self._spec.reference,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
            wraplength=720,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        tk.Button(
            inner,
            text="＋ 등록",
            bg=self._spec.accent,
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._on_add,
        ).pack(side=tk.RIGHT)
        tk.Button(
            inner,
            text="새로고침",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=FONT_BODY,
            padx=10,
            pady=8,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _build_kpi_row(self, row: int = 0) -> None:
        wrap = tk.Frame(self, bg=COLORS["bg"])
        wrap.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        for col in range(4):
            wrap.grid_columnconfigure(col, weight=1, uniform="kpi")

        self._kpi_frames: list[tk.Frame] = []
        for i in range(4):
            card = tk.Frame(wrap, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0), pady=0)
            card.grid_columnconfigure(0, weight=1)
            val = tk.Label(card, text="—", bg=COLORS["card"], fg=self._spec.accent, font=(FONT, 18, "bold"))
            val.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
            lbl = tk.Label(card, text="", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold"))
            lbl.grid(row=1, column=0, sticky="w", padx=14)
            hint = tk.Label(card, text="", bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 8))
            hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))
            self._kpi_frames.append(card)
            self._kpi_labels.extend([val, lbl, hint])

    def _build_tab_bar(self, row: int = 0) -> None:
        bar = tk.Frame(self, bg=COLORS["bg"])
        bar.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        for tid in self._spec.tab_ids:
            label = self._spec.tab_labels.get(tid, tid)
            btn = tk.Button(
                bar,
                text=f"  {label}  ",
                relief=tk.FLAT,
                bd=0,
                bg=COLORS["card"],
                fg=COLORS["muted"],
                activebackground=COLORS["nav_hover"],
                font=(FONT, 10),
                padx=12,
                pady=8,
                cursor="hand2",
                command=lambda t=tid: self._select_tab(t),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self._tab_btns[tid] = btn

    def _build_list_area(self, row: int = 0) -> None:
        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.grid(row=row, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(outer, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._tree, self._tree)

    def _select_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        for tid, btn in self._tab_btns.items():
            if tid == tab_id:
                btn.configure(bg=self._spec.accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 10))
        self._reload_tree()

    def _refresh_kpis(self) -> None:
        try:
            kpis = self._spec.kpi_fn()
        except Exception:
            kpis = []
        for i in range(4):
            idx = i * 3
            if i < len(kpis):
                label, value, hint = kpis[i]
                self._kpi_labels[idx].configure(text=value)
                self._kpi_labels[idx + 1].configure(text=label)
                self._kpi_labels[idx + 2].configure(text=hint)
            else:
                self._kpi_labels[idx].configure(text="—")
                self._kpi_labels[idx + 1].configure(text="")
                self._kpi_labels[idx + 2].configure(text="")

    def _reload_tree(self) -> None:
        if self._tree is None:
            return
        self._refresh_kpis()
        cols = self._spec.columns_fn(self._active_tab)
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = [c[0] for c in cols]
        for key, header, width in cols:
            self._tree.heading(key, text=header)
            self._tree.column(key, width=width, minwidth=40, stretch=key in ("title", "memo", "note", "name", "plan"))
        try:
            rows = self._spec.list_fn(self._active_tab)
        except Exception as exc:
            messagebox.showerror("조회 오류", str(exc), parent=self.winfo_toplevel())
            rows = []
        for row in rows:
            values = []
            for key, _h, _w in cols:
                val = row.get(key, "")
                values.append("" if val is None else val)
            self._tree.insert("", tk.END, values=values)

    def _on_add(self) -> None:
        if get_session() is None:
            messagebox.showinfo("로그인 필요", "등록하려면 로그인해 주세요.", parent=self.winfo_toplevel())
            return
        fields = self._spec.form_fn(self._active_tab)
        values: dict[str, str] = {}
        for key, label, required in fields:
            val = simpledialog.askstring(
                f"{self._spec.tab_labels.get(self._active_tab, '')} 등록",
                f"{label}{' *' if required else ''}:",
                parent=self.winfo_toplevel(),
            )
            if val is None:
                return
            if required and not str(val).strip():
                messagebox.showwarning("입력", f"{label}을(를) 입력해 주세요.", parent=self.winfo_toplevel())
                return
            values[key] = str(val).strip()
        try:
            self._spec.add_fn(self._active_tab, values)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc), parent=self.winfo_toplevel())


def build_maintenance_hub(parent: tk.Misc) -> ModuleHubPanel:
    from core.maintenance import service as svc

    spec = ModuleHubSpec(
        platform_id="maintenance",
        title="정비 사업부",
        accent="#0F766E",
        reference="참고: Fiix·UpKeep·SAP PM·IBM Maximo — 작업지시(WO), 설비자산, 예방정비, 부품재고",
        tab_ids=svc.TAB_IDS,
        tab_labels=svc.TAB_LABELS,
        kpi_fn=svc.dashboard_kpis,
        list_fn=svc.list_records,
        columns_fn=svc.tab_columns,
        form_fn=svc.form_fields,
        add_fn=svc.add_record,
    )
    return ModuleHubPanel(parent, spec)


def build_bidding_hub(parent: tk.Misc) -> ModuleHubPanel:
    from core.bidding import service as svc

    spec = ModuleHubSpec(
        platform_id="bidding",
        title="입찰",
        accent="#7C3AED",
        reference="참고: 나라장터·Procore·BidNet — 공고수집, 원가·견적, 제출일정, 낙찰·패찰 이력",
        tab_ids=svc.TAB_IDS,
        tab_labels=svc.TAB_LABELS,
        kpi_fn=svc.dashboard_kpis,
        list_fn=svc.list_records,
        columns_fn=svc.tab_columns,
        form_fn=svc.form_fields,
        add_fn=svc.add_record,
    )
    return ModuleHubPanel(parent, spec)


def build_accounting_hub(parent: tk.Misc) -> ModuleHubPanel:
    from core.accounting import service as svc

    spec = ModuleHubSpec(
        platform_id="accounting",
        title="회계 · 경리",
        accent="#B45309",
        reference="참고: 더존 SmartA·SAP FI·Peachtree — 전표, 세무일정, 자금계획, 결산·재무보고",
        tab_ids=svc.TAB_IDS,
        tab_labels=svc.TAB_LABELS,
        kpi_fn=svc.dashboard_kpis,
        list_fn=svc.list_records,
        columns_fn=svc.tab_columns,
        form_fn=svc.form_fields,
        add_fn=svc.add_record,
    )
    return ModuleHubPanel(parent, spec)


def build_recruitment_hub(parent: tk.Misc) -> ModuleHubPanel:
    from core.recruitment import service as svc

    spec = ModuleHubSpec(
        platform_id="recruitment",
        title="채용 · 마당",
        accent="#DB2777",
        reference=(
            "법인별 채용공고 작성·승인, 플랫폼 내 채용마당 게시, 지원 접수·채널(고용24·SNS) 상태 관리. "
            "외부 API 연동은 「채널 · 홍보」 탭에서 순차 적용 예정."
        ),
        tab_ids=svc.TAB_IDS,
        tab_labels=svc.TAB_LABELS,
        kpi_fn=svc.dashboard_kpis,
        list_fn=svc.list_records,
        columns_fn=svc.tab_columns,
        form_fn=svc.form_fields,
        add_fn=svc.add_record,
    )
    return ModuleHubPanel(parent, spec)
