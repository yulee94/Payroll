"""
ui/kpi_hub_panel.py - KPI · 경영 통합 허브 (지역 지도 + 하단 사업장 드릴다운)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from core.kpi import service as kpi_svc
from core.kpi.service import RECORD_TAB_IDS, STATUS_CRITICAL, STATUS_WARN, TAB_IDS, TAB_LABELS
from ui.kpi_map_view import KpiMapView
from ui.module_hub_panel import ModuleHubPanel, ModuleHubSpec
from ui.theme import COLORS, FONT


def _won(n: int) -> str:
    if abs(n) >= 100_000_000:
        return f"{n / 100_000_000:.2f}억원"
    if abs(n) >= 10_000:
        return f"{n / 10_000:,.0f}만원"
    return f"{n:,}원"


def _status_fg(status: str) -> str:
    if status == STATUS_CRITICAL:
        return "#DC2626"
    if status == STATUS_WARN:
        return "#D97706"
    return COLORS["text"]


def _safe_margin_pct(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().rstrip("%").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


class KpiHubPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._active_tab = "map"
        self._tab_btns: dict[str, tk.Button] = {}
        self._kpi_value_labels: list[tk.Label] = []
        self._selected_region: dict[str, Any] | None = None
        self._site_by_id: dict[str, dict[str, Any]] = {}
        self._region_by_id: dict[str, dict[str, Any]] = {}
        self._detail_var = tk.StringVar(value="지도에서 지역을 선택하면 사업장 목록이 표시됩니다.")
        self._region_summary_var = tk.StringVar(value="전체 현황 — 지역을 클릭하세요")
        self._build()
        self.select_tab("map")

    def _build(self) -> None:
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        accent = "#4F46E5"

        head = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        inner = tk.Frame(head, bg=COLORS["card"], padx=18, pady=14)
        inner.pack(fill=tk.X)
        bar = tk.Frame(inner, bg=accent, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        txt = tk.Frame(inner, bg=COLORS["card"])
        txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(txt, text="KPI · 경영", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 14, "bold")).pack(anchor=tk.W)
        tk.Label(
            txt,
            text="지역별 손익 한눈에 · 클릭 시 사업장 목록·상세 · 100+ 현장 대응 · 인사·급여 연동 예정",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=720,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        kpi_row = tk.Frame(self, bg=COLORS["bg"])
        kpi_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for col in range(4):
            kpi_row.grid_columnconfigure(col, weight=1, uniform="kpi")
        for i in range(4):
            card = tk.Frame(kpi_row, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            val = tk.Label(card, text="—", bg=COLORS["card"], fg=accent, font=(FONT, 16, "bold"))
            val.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))
            lbl = tk.Label(card, text="", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 9, "bold"))
            lbl.grid(row=1, column=0, sticky="w", padx=12)
            hint = tk.Label(card, text="", bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 8))
            hint.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))
            self._kpi_value_labels.extend([val, lbl, hint])

        tab_bar = tk.Frame(self, bg=COLORS["bg"])
        tab_bar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for tid in TAB_IDS:
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
        self._content.grid(row=3, column=0, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._map_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._map_host.grid_rowconfigure(2, weight=1)
        self._map_host.grid_columnconfigure(0, weight=1)

        map_row = tk.Frame(self._map_host, bg=COLORS["bg"])
        map_row.grid(row=0, column=0, sticky="nsew")
        map_row.grid_columnconfigure(0, weight=3, uniform="maprow")
        map_row.grid_columnconfigure(1, weight=2, uniform="maprow")
        map_row.grid_rowconfigure(0, weight=1)

        self.map_view = KpiMapView(map_row, on_select=self._on_region_selected)
        self.map_view.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        region_panel = tk.Frame(
            map_row,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        region_panel.grid(row=0, column=1, sticky="nsew")
        region_panel.grid_rowconfigure(1, weight=1)
        region_panel.grid_columnconfigure(0, weight=1)

        tk.Label(
            region_panel,
            text="지역 요약",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
            padx=12,
            pady=10,
        ).grid(row=0, column=0, sticky="ew")

        tree_wrap2 = tk.Frame(region_panel, bg=COLORS["card"])
        tree_wrap2.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_wrap2.grid_rowconfigure(0, weight=1)
        tree_wrap2.grid_columnconfigure(0, weight=1)

        rcols = ("region", "status", "issues", "sites", "profit")
        self._region_tree = ttk.Treeview(tree_wrap2, columns=rcols, show="headings", selectmode="browse", height=10)
        rhead = {
            "region": ("지역", 110),
            "status": ("상태", 50),
            "issues": ("이슈", 40),
            "sites": ("사업장", 50),
            "profit": ("손익", 70),
        }
        for col, (label, width) in rhead.items():
            self._region_tree.heading(col, text=label)
            self._region_tree.column(col, width=width, minwidth=40, stretch=(col == "profit"))
        vsb2 = ttk.Scrollbar(tree_wrap2, orient=tk.VERTICAL, command=self._region_tree.yview)
        self._region_tree.configure(yscrollcommand=vsb2.set)
        self._region_tree.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        self._region_tree.bind("<<TreeviewSelect>>", self._on_region_tree_select)

        summary_bar = tk.Frame(
            self._map_host,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        summary_bar.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        tk.Label(
            summary_bar,
            textvariable=self._region_summary_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
            padx=14,
            pady=10,
        ).pack(fill=tk.X)

        drill = tk.Frame(self._map_host, bg=COLORS["bg"])
        drill.grid(row=2, column=0, sticky="nsew")
        drill.grid_rowconfigure(0, weight=1)
        drill.grid_columnconfigure(0, weight=3)
        drill.grid_columnconfigure(1, weight=2)

        list_card = tk.Frame(
            drill,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_card.grid_rowconfigure(1, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        tk.Label(list_card, text="사업장 목록", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        tree_wrap = tk.Frame(list_card, bg=COLORS["card"])
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        cols = ("site_name", "legal_entity", "profit", "margin_pct", "status")
        self._site_tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", selectmode="browse", height=8)
        headings = {
            "site_name": ("사업장", 140),
            "legal_entity": ("법인", 72),
            "profit": ("이익", 72),
            "margin_pct": ("마진", 52),
            "status": ("상태", 48),
        }
        for col, (label, width) in headings.items():
            self._site_tree.heading(col, text=label)
            self._site_tree.column(col, width=width, minwidth=40, stretch=(col == "site_name"))
        vsb = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self._site_tree.yview)
        self._site_tree.configure(yscrollcommand=vsb.set)
        self._site_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._site_tree.bind("<<TreeviewSelect>>", self._on_site_tree_select)

        detail = tk.Frame(
            drill,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        detail.grid(row=0, column=1, sticky="nsew")
        detail.grid_rowconfigure(1, weight=1)
        tk.Label(detail, text="사업장 상세", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 6)
        )
        self._detail_lbl = tk.Label(
            detail,
            textvariable=self._detail_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 9),
            justify=tk.LEFT,
            wraplength=280,
            anchor=tk.NW,
        )
        self._detail_lbl.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))

        alert_box = tk.Frame(self._map_host, bg=COLORS["bg"])
        alert_box.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        tk.Label(alert_box, text="⚠ 최근 이슈", bg=COLORS["bg"], fg=COLORS["warn"], font=(FONT, 9, "bold")).pack(
            anchor=tk.W
        )
        self._alert_lbl = tk.Label(
            alert_box,
            text="",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            justify=tk.LEFT,
            wraplength=900,
            anchor=tk.W,
        )
        self._alert_lbl.pack(anchor=tk.W, pady=(4, 0))

        spec = ModuleHubSpec(
            platform_id="kpi",
            title="KPI · 경영",
            accent="#4F46E5",
            reference="",
            tab_ids=RECORD_TAB_IDS,
            tab_labels={k: v for k, v in TAB_LABELS.items() if k in RECORD_TAB_IDS},
            kpi_fn=kpi_svc.dashboard_kpis,
            list_fn=kpi_svc.list_records,
            columns_fn=kpi_svc.tab_columns,
            form_fn=kpi_svc.form_fields,
            add_fn=kpi_svc.add_record,
            hide_header=True,
            hide_tabs=True,
        )
        self._records_host = tk.Frame(self._content, bg=COLORS["bg"])
        self._records_host.grid_rowconfigure(0, weight=1)
        self._records_host.grid_columnconfigure(0, weight=1)
        self._records_hub = ModuleHubPanel(self._records_host, spec)
        self._records_hub.grid(row=0, column=0, sticky="nsew")

    def _populate_region_panel(self, regions: list[dict[str, Any]]) -> None:
        tree = self._region_tree
        tree.delete(*tree.get_children())
        self._region_by_id.clear()
        for r in regions:
            rid = str(r.get("id") or "")
            self._region_by_id[rid] = r
            label = str(r.get("label") or r.get("region") or "")
            status = str(r.get("status") or "")
            issues = int(r.get("issue_count") or 0)
            sites = int(r.get("site_count") or 0)
            profit = int(r.get("profit") or 0)
            sign = "+" if profit >= 0 else ""
            tree.insert(
                "",
                tk.END,
                iid=rid,
                values=(
                    label,
                    status,
                    str(issues),
                    f"{sites}",
                    f"{sign}{_won(profit)}",
                ),
            )

    def _on_region_tree_select(self, _event: tk.Event | None = None) -> None:
        sel = self._region_tree.selection()
        if not sel:
            return
        rid = sel[0]
        region = self._region_by_id.get(rid)
        if not region:
            return
        self.map_view.select_region(rid)
        self._on_region_selected(region)

    def _refresh_kpis(self) -> None:
        try:
            kpis = kpi_svc.dashboard_kpis()
        except Exception:
            kpis = []
        for i in range(4):
            idx = i * 3
            if i < len(kpis):
                label, value, hint = kpis[i]
                self._kpi_value_labels[idx].configure(text=value)
                self._kpi_value_labels[idx + 1].configure(text=label)
                self._kpi_value_labels[idx + 2].configure(text=hint)
            else:
                self._kpi_value_labels[idx].configure(text="—")
                self._kpi_value_labels[idx + 1].configure(text="")
                self._kpi_value_labels[idx + 2].configure(text="")

    def _refresh_alerts(self) -> None:
        alerts = kpi_svc.list_records("alerts")
        if not alerts:
            self._alert_lbl.configure(text="등록된 이슈가 없습니다.")
            return
        lines = []
        for a in alerts[:3]:
            lines.append(f"· [{a.get('severity')}] {a.get('site_name')} — {a.get('title')}")
        self._alert_lbl.configure(text="\n".join(lines))

    def _format_site_detail(self, site: dict[str, Any]) -> str:
        profit = int(site.get("profit") or 0)
        lines = [
            f"【{site.get('site_name')}】",
            f"법인: {site.get('legal_entity')}",
            f"지역: {site.get('region')}",
            f"매출: {_won(int(site.get('revenue') or 0))}",
            f"비용: {_won(int(site.get('cost') or 0))}",
            f"이익: {_won(profit)} ({_safe_margin_pct(site.get('margin_pct')):+.1f}%)",
            f"상태: {site.get('status')}",
            f"인원: {site.get('headcount')}명",
        ]
        note = str(site.get("note") or "").strip()
        if note:
            lines.append(f"비고: {note}")
        return "\n".join(lines)

    def _populate_site_list(self, sites: list[dict[str, Any]]) -> None:
        tree = self._site_tree
        tree.delete(*tree.get_children())
        self._site_by_id.clear()
        for idx, site in enumerate(sites):
            sid = str(site.get("id") or "").strip() or f"site-{idx}"
            self._site_by_id[sid] = site
            profit = int(site.get("profit") or 0)
            sign = "+" if profit >= 0 else ""
            values = (
                site.get("site_name") or "",
                site.get("legal_entity") or "",
                f"{sign}{_won(profit)}",
                f"{_safe_margin_pct(site.get('margin_pct')):+.1f}%",
                site.get("status") or "",
            )
            try:
                tree.insert("", tk.END, iid=sid, values=values)
            except tk.TclError:
                tree.insert("", tk.END, values=values)

    def _on_region_selected(self, region: dict[str, Any] | None) -> None:
        self._selected_region = region
        if not region:
            self._region_summary_var.set("전체 현황 — 지역을 클릭하세요")
            self._populate_site_list([])
            self._detail_var.set("지도에서 지역을 선택하면 사업장 목록이 표시됩니다.")
            try:
                self._region_tree.selection_remove(self._region_tree.selection())
            except Exception:
                pass
            return

        label = str(region.get("label") or region.get("region") or "")
        rid = str(region.get("id") or "")
        if rid:
            try:
                self._region_tree.selection_set(rid)
                self._region_tree.focus(rid)
            except Exception:
                pass
        count = int(region.get("site_count") or 0)
        profit = int(region.get("profit") or 0)
        margin = _safe_margin_pct(region.get("margin_pct"))
        issues = int(region.get("issue_count") or 0)
        sign = "+" if profit >= 0 else ""
        issue_txt = f" · 이슈 {issues}곳" if issues else ""
        self._region_summary_var.set(
            f"▸ {label}  ·  사업장 {count}곳  ·  손익 {sign}{_won(profit)}  ·  마진 {margin:+.1f}%{issue_txt}"
        )

        sites = list(region.get("sites") or [])
        self._populate_site_list(sites)
        if sites:
            first = sites[0]
            first_sid = str(first.get("id") or "").strip() or "site-0"
            try:
                self._site_tree.selection_set(first_sid)
                self._site_tree.focus(first_sid)
            except tk.TclError:
                children = self._site_tree.get_children()
                if children:
                    self._site_tree.selection_set(children[0])
                    self._site_tree.focus(children[0])
                    first = self._site_by_id.get(children[0], first)
            self._detail_var.set(self._format_site_detail(first))
            self._detail_lbl.configure(fg=_status_fg(str(first.get("status") or "")))
        else:
            self._detail_var.set("해당 지역에 등록된 사업장이 없습니다.")

    def _on_site_tree_select(self, _event: tk.Event | None = None) -> None:
        sel = self._site_tree.selection()
        if not sel:
            return
        site = self._site_by_id.get(sel[0])
        if not site:
            return
        self._detail_var.set(self._format_site_detail(site))
        self._detail_lbl.configure(fg=_status_fg(str(site.get("status") or "")))

    def select_tab(self, tab_id: str) -> None:
        if tab_id not in TAB_IDS:
            return
        self._active_tab = tab_id
        accent = "#4F46E5"
        for tid, btn in self._tab_btns.items():
            if tid == tab_id:
                btn.configure(bg=accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10))

        self._map_host.grid_remove()
        self._records_host.grid_remove()

        if tab_id == "map":
            self._map_host.grid(row=0, column=0, sticky="nsew")
        else:
            if hasattr(self.map_view, "_hide_tooltip"):
                self.map_view._hide_tooltip()
            self._records_host.grid(row=0, column=0, sticky="nsew")
            self._records_hub.select_tab(tab_id)
        self.refresh()

    def refresh(self) -> None:
        kpi_svc.ensure_seed()
        self._refresh_kpis()
        self._refresh_alerts()
        if self._active_tab == "map":
            regions = kpi_svc.aggregate_regions()
            self.map_view.load_regions(regions)
            self._populate_region_panel(regions)
            if self._selected_region:
                rid = str(self._selected_region.get("id") or "")
                refreshed = next((r for r in regions if str(r.get("id")) == rid), None)
                if refreshed:
                    self.map_view.select_region(rid)
                    self._on_region_selected(refreshed)
                else:
                    self._on_region_selected(None)
        elif self._active_tab in RECORD_TAB_IDS:
            self._records_hub.refresh()


def build_kpi_hub(parent: tk.Misc) -> KpiHubPanel:
    return KpiHubPanel(parent)
