"""
ui/executive_dashboard.py - 임원용 월별 경영 보고 (한 화면 · 한눈에 보기)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from core.brand_display import company_name_line
from core.config import APP_CONFIG
from payroll_archive import format_executive_report_title
from services.executive_analytics import ExecutiveAnalytics
from ui.theme import COLORS, FONT
from ui.wheel_scroll import _scroll_widget, wheel_delta

_brand = APP_CONFIG.brand
_NAVY = _brand.primary_navy
_CYAN = "#00A8E8"
_MUTED = COLORS["muted"]
_SUCCESS = COLORS["success"]
_WARN = COLORS["warn"]


def _setup_matplotlib_fonts() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def _fmt_man(won: int) -> str:
    if won >= 100_000_000:
        return f"{won / 100_000_000:.1f}억원"
    if won >= 10_000:
        return f"{won / 10_000:,.0f}만원"
    return f"{won:,}원"


def _fmt_delta_short(value: int, *, unit: str = "", is_money: bool = False) -> str:
    if value == 0:
        return "전월과 동일"
    sign = "+" if value > 0 else ""
    if is_money:
        body = _fmt_man(abs(value))
        if value < 0:
            body = f"-{body}"
        else:
            body = f"+{body}"
    else:
        body = f"{sign}{value}{unit}"
    return f"전월 대비 {body}"


def _delta_color(value: int) -> str:
    if value > 0:
        return _WARN
    if value < 0:
        return _SUCCESS
    return _MUTED


class ExecutiveDashboardPanel(ttk.Frame):
    """임원 보고: 제목·핵심 수치·차트·상세 표.

    page_scroll=True 이면 내부 스크롤 없이 전체 높이로 펼치고, 부모 페이지에서 스크롤합니다.
    """

    def __init__(
        self,
        parent,
        colors: dict[str, str] | None = None,
        *,
        page_scroll: bool = False,
        wheel_scroll_target: tk.Misc | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._colors = colors or COLORS
        self._page_scroll = page_scroll
        self._wheel_scroll_target = wheel_scroll_target
        self._analytics: ExecutiveAnalytics | None = None
        self._empty_message: str | None = None
        self._kpi_value_labels: dict[str, tk.Label] = {}
        self._kpi_delta_labels: dict[str, tk.Label] = {}
        self._last_draw_key: tuple | None = None
        self._wheel_bound = False
        self._scroll_canvas: tk.Canvas | None = None
        self._canvas_win: int | None = None

        _setup_matplotlib_fonts()

        outer = ttk.Frame(self)
        if page_scroll:
            outer.pack(fill=tk.X, anchor=tk.NW)
        else:
            outer.pack(fill=tk.BOTH, expand=True)
            outer.grid_rowconfigure(0, weight=1)
            outer.grid_columnconfigure(0, weight=1)

        if page_scroll:
            self._body = tk.Frame(outer, bg=COLORS["bg"])
            self._body.pack(fill=tk.X, anchor=tk.NW)
        else:
            self._scroll_canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
            scroll = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self._scroll_canvas.yview)
            self._scroll_canvas.configure(yscrollcommand=scroll.set)
            self._scroll_canvas.grid(row=0, column=0, sticky="nsew")
            scroll.grid(row=0, column=1, sticky="ns")

            self._body = tk.Frame(self._scroll_canvas, bg=COLORS["bg"])
            self._canvas_win = self._scroll_canvas.create_window((0, 0), window=self._body, anchor=tk.NW)
            self._body.bind("<Configure>", self._on_body_configure)
            self._scroll_canvas.bind("<Configure>", self._on_canvas_configure)
            self.bind("<Enter>", self._bind_scroll_wheel)
            self.bind("<Leave>", self._unbind_scroll_wheel)

        # —— 보고 헤더 ——
        header = tk.Frame(self._body, bg=_NAVY, padx=20, pady=16)
        header.pack(fill=tk.X, padx=0, pady=(0, 12))

        top_row = tk.Frame(header, bg=_NAVY)
        top_row.pack(fill=tk.X)
        self._title_label = tk.Label(
            top_row,
            text="급여 경영 보고",
            bg=_NAVY,
            fg="#FFFFFF",
            font=(FONT, 16, "bold"),
            anchor=tk.W,
        )
        self._title_label.pack(side=tk.LEFT)
        self._brand_label = tk.Label(
            top_row,
            text=company_name_line(),
            bg=_NAVY,
            fg="#94A3B8",
            font=(FONT, 10),
            anchor=tk.E,
        )
        self._brand_label.pack(side=tk.RIGHT)

        self._headline_label = tk.Label(
            header,
            text="",
            bg=_NAVY,
            fg="#E2E8F0",
            font=(FONT, 11),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=900,
        )
        self._headline_label.pack(fill=tk.X, pady=(10, 0))

        self._metrics_strip = tk.Label(
            header,
            text="",
            bg=_NAVY,
            fg="#94A3B8",
            font=(FONT, 9),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=900,
        )
        self._metrics_strip.pack(fill=tk.X, pady=(4, 0))

        self._takeaway_frame = tk.Frame(header, bg=_NAVY)
        self._takeaway_frame.pack(fill=tk.X, pady=(8, 0))
        self._takeaway_labels: list[tk.Label] = []
        for _ in range(3):
            lbl = tk.Label(
                self._takeaway_frame,
                text="",
                bg=_NAVY,
                fg="#FFFFFF",
                font=(FONT, 10),
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=880,
            )
            lbl.pack(fill=tk.X, pady=2)
            self._takeaway_labels.append(lbl)

        # —— 핵심 KPI (2×2, 잘림 방지) ——
        self._kpi_wrap = tk.Frame(self._body, bg=COLORS["bg"])
        self._kpi_wrap.pack(fill=tk.X, padx=4, pady=(0, 12))
        kpi_wrap = self._kpi_wrap
        for c in range(2):
            kpi_wrap.grid_columnconfigure(c, weight=1, uniform="kpi")

        kpi_defs = [
            ("count", "인원", "명"),
            ("gross", "총 인건비", ""),
            ("ot", "연장 수당", ""),
            ("special", "특근 수당", ""),
        ]
        for idx, (key, title, unit_hint) in enumerate(kpi_defs):
            row, col = divmod(idx, 2)
            card = tk.Frame(
                kpi_wrap,
                bg=COLORS["card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
            )
            card.grid(row=row, column=col, padx=(0 if col == 0 else 6, 6), pady=(0 if row == 0 else 6, 0), sticky="nsew")
            inner = tk.Frame(card, bg=COLORS["card"], padx=18, pady=14)
            inner.pack(fill=tk.BOTH, expand=True)
            tk.Label(inner, text=title, bg=COLORS["card"], fg=_MUTED, font=(FONT, 10)).pack(anchor=tk.W)
            val = tk.Label(
                inner,
                text="-",
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=(FONT, 22, "bold"),
                anchor=tk.W,
                wraplength=320,
            )
            val.pack(anchor=tk.W, pady=(6, 2))
            delta = tk.Label(
                inner,
                text="",
                bg=COLORS["card"],
                fg=_MUTED,
                font=(FONT, 9),
                anchor=tk.W,
                wraplength=320,
            )
            delta.pack(anchor=tk.W)
            self._kpi_value_labels[key] = val
            self._kpi_delta_labels[key] = delta
            _ = unit_hint

        # —— 연간 요약 (1~당월) ——
        self._ytd_frame = tk.Frame(
            self._body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        ytd_inner = tk.Frame(self._ytd_frame, bg=COLORS["card"], padx=16, pady=12)
        ytd_inner.pack(fill=tk.X)
        self._ytd_title = tk.Label(
            ytd_inner,
            text="연간 보고",
            bg=COLORS["card"],
            fg=_NAVY,
            font=(FONT, 11, "bold"),
            anchor=tk.W,
        )
        self._ytd_title.pack(anchor=tk.W)
        self._ytd_summary = tk.Label(
            ytd_inner,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=920,
        )
        self._ytd_summary.pack(anchor=tk.W, pady=(6, 0))
        self._ytd_frame.pack_forget()

        # —— 차트 + 상세 표 (단일 패널) ——
        self._board_frame = tk.Frame(
            self._body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        if page_scroll:
            self._board_frame.pack(fill=tk.X, padx=4, pady=(0, 8))
        else:
            self._board_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 8))
        board = self._board_frame
        board_inner = tk.Frame(board, bg=COLORS["card"], padx=12, pady=12)
        if page_scroll:
            board_inner.pack(fill=tk.X)
        else:
            board_inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            board_inner,
            text="시각 요약",
            bg=COLORS["card"],
            fg=_NAVY,
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W, pady=(0, 6))

        chart_box = tk.Frame(board_inner, bg=COLORS["card"])
        chart_box.pack(fill=tk.X)
        self._figure = Figure(figsize=(10.2, 6.4), dpi=96, facecolor=COLORS["card"])
        self._mpl_canvas = FigureCanvasTkAgg(self._figure, master=chart_box)
        self._mpl_canvas.get_tk_widget().pack(fill=tk.X)

        tk.Label(
            board_inner,
            text="상세 집계",
            bg=COLORS["card"],
            fg=_NAVY,
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W, pady=(12, 6))

        tables = tk.Frame(board_inner, bg=COLORS["card"])
        if page_scroll:
            tables.pack(fill=tk.X)
        else:
            tables.pack(fill=tk.BOTH, expand=True)
        tables.grid_columnconfigure(0, weight=1)
        tables.grid_columnconfigure(1, weight=1)
        if not page_scroll:
            tables.grid_rowconfigure(0, weight=1)

        site_lf = ttk.LabelFrame(tables, text="  사업장·소속별  ", padding=4)
        site_lf.grid(row=0, column=0, sticky="nsew" if not page_scroll else "new", padx=(0, 6))
        if not page_scroll:
            site_lf.grid_rowconfigure(0, weight=1)
        site_lf.grid_columnconfigure(0, weight=1)

        self._site_table = ttk.Treeview(
            site_lf,
            columns=("site", "headcount", "gross", "share"),
            show="headings",
            height=8,
        )
        for key, title, w, anchor in [
            ("site", "사업장·소속", 200, tk.W),
            ("headcount", "인원", 48, tk.E),
            ("gross", "총 급여", 100, tk.E),
            ("share", "비중", 52, tk.E),
        ]:
            self._site_table.heading(key, text=title)
            self._site_table.column(key, width=w, minwidth=40, anchor=anchor)
        if page_scroll:
            self._site_table.grid(row=0, column=0, sticky="ew")
        else:
            site_scroll = ttk.Scrollbar(site_lf, orient=tk.VERTICAL, command=self._site_table.yview)
            self._site_table.configure(yscrollcommand=site_scroll.set)
            self._site_table.grid(row=0, column=0, sticky="nsew")
            site_scroll.grid(row=0, column=1, sticky="ns")
            self._site_table.bind("<MouseWheel>", self._on_table_wheel)

        emp_lf = ttk.LabelFrame(tables, text="  총지급 상위 인원  ", padding=4)
        emp_lf.grid(row=0, column=1, sticky="nsew" if not page_scroll else "new")
        if not page_scroll:
            emp_lf.grid_rowconfigure(0, weight=1)
        emp_lf.grid_columnconfigure(0, weight=1)

        self._emp_table = ttk.Treeview(
            emp_lf,
            columns=("rank", "name", "site", "gross"),
            show="headings",
            height=8,
        )
        for key, title, w, anchor in [
            ("rank", "순위", 40, tk.E),
            ("name", "성명", 88, tk.W),
            ("site", "소속", 140, tk.W),
            ("gross", "총지급", 96, tk.E),
        ]:
            self._emp_table.heading(key, text=title)
            self._emp_table.column(key, width=w, minwidth=36, anchor=anchor)
        if page_scroll:
            self._emp_table.grid(row=0, column=0, sticky="ew")
        else:
            emp_scroll = ttk.Scrollbar(emp_lf, orient=tk.VERTICAL, command=self._emp_table.yview)
            self._emp_table.configure(yscrollcommand=emp_scroll.set)
            self._emp_table.grid(row=0, column=0, sticky="nsew")
            emp_scroll.grid(row=0, column=1, sticky="ns")
            self._emp_table.bind("<MouseWheel>", self._on_table_wheel)

        if page_scroll and wheel_scroll_target is not None:
            self._bind_page_wheel(wheel_scroll_target)

    def _bind_page_wheel(self, target: tk.Misc) -> None:
        def _wheel(event, t=target) -> str | None:
            delta = wheel_delta(event)
            if delta and _scroll_widget(t, delta, event):
                return "break"
            return None

        for w in (self, self._body, self._site_table, self._emp_table, self._board_frame):
            w.bind("<MouseWheel>", _wheel, add="+")
            w.bind("<Button-4>", _wheel, add="+")
            w.bind("<Button-5>", _wheel, add="+")

    def _notify_layout_refresh(self) -> None:
        if self._page_scroll:
            self._fit_table_heights()
            self._body.update_idletasks()
            self.event_generate("<<ExecutiveDashboardLayout>>", when="tail")
        elif self._scroll_canvas is not None:
            self._on_body_configure()

    def _fit_table_heights(self) -> None:
        if not self._page_scroll:
            return
        n_site = len(self._site_table.get_children())
        n_emp = len(self._emp_table.get_children())
        self._site_table.configure(height=max(1, n_site))
        self._emp_table.configure(height=max(1, n_emp))

    def _on_body_configure(self, _event=None) -> None:
        if self._scroll_canvas is None:
            return
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        if self._scroll_canvas is None or self._canvas_win is None:
            return
        self._scroll_canvas.itemconfig(self._canvas_win, width=event.width)

    def _bind_scroll_wheel(self, _event=None) -> None:
        if self._page_scroll or self._scroll_canvas is None:
            return
        if self._wheel_bound:
            return
        self._wheel_bound = True
        for w in (self._scroll_canvas, self._body):
            w.bind("<MouseWheel>", self._on_panel_wheel)

    def _unbind_scroll_wheel(self, _event=None) -> None:
        if not self._wheel_bound:
            return
        self._wheel_bound = False
        for w in (self._scroll_canvas, self._body):
            w.unbind("<MouseWheel>")

    def _on_panel_wheel(self, event) -> None:
        if isinstance(event.widget, (ttk.Treeview, tk.Text)):
            return
        if self._scroll_canvas is None:
            return
        self._scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_table_wheel(self, event) -> str:
        tree = event.widget
        tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _analytics_draw_key(self, a: ExecutiveAnalytics) -> tuple:
        return (
            a.period,
            len(a.records),
            a.summary.total_gross,
            len(a.sites),
            len(a.ytd_months),
            a.ytd_total_gross,
        )

    def load(
        self,
        analytics: ExecutiveAnalytics | None,
        *,
        empty_message: str | None = None,
    ) -> None:
        self._analytics = analytics
        self._empty_message = (empty_message or "").strip() or None
        if not analytics or not analytics.records:
            self._last_draw_key = None
            self._set_empty_state()
            self._notify_layout_refresh()
            return
        self._fill_header(analytics)
        self._fill_kpis(analytics)
        self._fill_ytd_section(analytics)
        self._load_tables(analytics)
        draw_key = self._analytics_draw_key(analytics)
        if draw_key != self._last_draw_key:
            self._schedule_draw_charts(draw_key)
        self._notify_layout_refresh()

    def summary_headline(self) -> str:
        """상단 고정 요약 표시용 한 줄 헤드라인."""
        try:
            return str(self._headline_label.cget("text") or "")
        except Exception:
            return ""

    def summary_bullets(self) -> list[str]:
        """상단 고정 요약 표시용 핵심 bullet(최대 3개)."""
        out: list[str] = []
        for lbl in getattr(self, "_takeaway_labels", []) or []:
            try:
                t = str(lbl.cget("text") or "").strip()
            except Exception:
                t = ""
            if t:
                out.append(t)
        return out[:3]

    def _set_empty_state(self) -> None:
        hint = self._empty_message or "급여 산출 후 이 화면에 임원용 요약이 표시됩니다."
        self._title_label.configure(text="인도급 급여 요약")
        self._ytd_frame.pack_forget()
        self._headline_label.configure(text=hint)
        self._metrics_strip.configure(text="")
        for lbl in self._takeaway_labels:
            lbl.configure(text="")
        for key in self._kpi_value_labels:
            self._kpi_value_labels[key].configure(text="-")
            self._kpi_delta_labels[key].configure(text="")
        for t in self._site_table.get_children():
            self._site_table.delete(t)
        for t in self._emp_table.get_children():
            self._emp_table.delete(t)
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.axis("off")
        chart_msg = "표시할 급여 데이터가 없습니다"
        if self._empty_message:
            chart_msg = self._empty_message[:80]
        ax.text(0.5, 0.5, chart_msg, ha="center", va="center", fontsize=11, color=_MUTED, wrap=True)
        self._mpl_canvas.draw_idle()
        self._notify_layout_refresh()

    def _fill_header(self, a: ExecutiveAnalytics) -> None:
        ms = a.summary
        self._title_label.configure(text=format_executive_report_title(a.period))
        self._headline_label.configure(
            text=(
                f"당월 인원 {ms.employee_count}명 · 총 인건비 {_fmt_man(ms.total_gross)} · "
                f"연장 {_fmt_man(getattr(a, 'ot_total', 0))} · 특근 {_fmt_man(getattr(a, 'special_total', 0))}"
            )
        )
        self._metrics_strip.configure(
            text=(
                f"실수령 {_fmt_man(ms.total_net)} · 공제 {_fmt_man(ms.total_deduction)} · "
                f"연차 사용 {ms.leave_users}명 · 무급/결근 {ms.absence_users}명"
            )
        )
        bullets = self._executive_bullets(a)
        for lbl, text in zip(self._takeaway_labels, bullets):
            lbl.configure(text=text if text else "")

    def _executive_bullets(self, a: ExecutiveAnalytics) -> list[str]:
        ms = a.summary
        lines: list[str] = []
        hd = getattr(a, "headcount_delta", 0)
        gd = getattr(a, "gross_delta", 0)
        lines.append(
            f"① 인원 {ms.employee_count}명 — {_fmt_delta_short(hd, unit='명')}"
        )
        lines.append(
            f"② 총 인건비 {_fmt_man(ms.total_gross)} — {_fmt_delta_short(gd, is_money=True)}"
        )
        if a.sites:
            top = a.sites[0]
            share = (top.gross / ms.total_gross * 100) if ms.total_gross else 0
            lines.append(
                f"③ 최대 부담 「{top.name}」 {top.headcount}명 · {_fmt_man(top.gross)} (약 {share:.0f}%)"
            )
        else:
            ot_d = getattr(a, "ot_delta", 0)
            lines.append(
                f"③ 연장·특근 — 연장 {_fmt_delta_short(ot_d, is_money=True)} · "
                f"특근 {_fmt_delta_short(getattr(a, 'special_delta', 0), is_money=True)}"
            )
        return lines[:3]

    def _fill_ytd_section(self, a: ExecutiveAnalytics) -> None:
        if not a.ytd_label or len(a.ytd_months) < 1:
            self._ytd_frame.pack_forget()
            return
        self._ytd_frame.pack(fill=tk.X, padx=4, pady=(0, 12), before=self._board_frame)
        self._ytd_title.configure(text=f"연간 보고 · {a.ytd_label}")
        parts = [f"누적 총급여 {_fmt_man(a.ytd_total_gross)}"]
        if a.ytd_gross_deltas:
            trend_bits: list[str] = []
            for d in a.ytd_gross_deltas:
                if d.delta == 0 and d is a.ytd_gross_deltas[0]:
                    trend_bits.append(f"{d.label} {_fmt_man(d.gross)}")
                else:
                    trend_bits.append(
                        f"{d.label} {_fmt_delta_short(d.delta, is_money=True)}"
                    )
            parts.append("전월 대비 증감: " + " → ".join(trend_bits))
        self._ytd_summary.configure(text="\n".join(parts))

    def _fill_kpis(self, a: ExecutiveAnalytics) -> None:
        ms = a.summary
        mapping = {
            "count": (
                f"{ms.employee_count}명",
                _fmt_delta_short(getattr(a, "headcount_delta", 0), unit="명"),
                getattr(a, "headcount_delta", 0),
            ),
            "gross": (
                _fmt_man(ms.total_gross),
                _fmt_delta_short(getattr(a, "gross_delta", 0), is_money=True),
                getattr(a, "gross_delta", 0),
            ),
            "ot": (
                _fmt_man(getattr(a, "ot_total", 0)),
                _fmt_delta_short(getattr(a, "ot_delta", 0), is_money=True),
                getattr(a, "ot_delta", 0),
            ),
            "special": (
                _fmt_man(getattr(a, "special_total", 0)),
                _fmt_delta_short(getattr(a, "special_delta", 0), is_money=True),
                getattr(a, "special_delta", 0),
            ),
        }
        for key, (val, delta, dnum) in mapping.items():
            self._kpi_value_labels[key].configure(text=val)
            self._kpi_delta_labels[key].configure(text=delta, fg=_delta_color(dnum))

    def _load_tables(self, a: ExecutiveAnalytics) -> None:
        for item in self._site_table.get_children():
            self._site_table.delete(item)
        for item in self._emp_table.get_children():
            self._emp_table.delete(item)

        total_gross = a.summary.total_gross or 1
        for s in a.sites[:15]:
            share = s.gross / total_gross * 100
            self._site_table.insert(
                "",
                tk.END,
                values=(s.name, f"{s.headcount}명", _fmt_man(s.gross), f"{share:.0f}%"),
            )

        emp_count = len(a.top_employees[:12])
        for i, r in enumerate(a.top_employees[:12], start=1):
            self._emp_table.insert(
                "",
                tk.END,
                values=(
                    i,
                    r.get("name", ""),
                    r.get("workplace", "") or r.get("dept", "") or "-",
                    _fmt_man(int(r.get("gross_pay") or 0)),
                ),
            )
        if self._page_scroll:
            site_count = min(len(a.sites), 15)
            self._site_table.configure(height=max(1, site_count))
            self._emp_table.configure(height=max(1, emp_count))

    def _schedule_draw_charts(self, draw_key: tuple) -> None:
        """KPI·표를 먼저 그린 뒤 차트만 idle 시점에 그려 UI 멈춤을 줄입니다."""

        def _run() -> None:
            a = self._analytics
            if not a or not a.records:
                return
            if self._analytics_draw_key(a) != draw_key:
                return
            self._draw_charts()

        self.after_idle(_run)

    def _draw_charts(self) -> None:
        if not self._analytics or not self._analytics.records:
            return
        a = self._analytics
        draw_key = self._analytics_draw_key(a)
        if self._last_draw_key == draw_key:
            return
        self._last_draw_key = draw_key
        self._figure.clear()
        try:
            self._draw_executive_charts()
            self._figure.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.14, hspace=0.55, wspace=0.32)
        except Exception as exc:
            self._figure.clear()
            ax = self._figure.add_subplot(111)
            ax.axis("off")
            ax.text(0.5, 0.55, "차트를 표시할 수 없습니다", ha="center", va="center", color=_MUTED)
            ax.text(0.5, 0.4, str(exc), ha="center", va="center", fontsize=8, color=_MUTED)
        self._mpl_canvas.draw_idle()
        self._notify_layout_refresh()

    def _draw_executive_charts(self) -> None:
        a = self._analytics
        assert a is not None
        ms = a.summary

        gs = self._figure.add_gridspec(2, 2, height_ratios=[1.05, 0.95], hspace=0.55, wspace=0.32)
        gs_top = gs[0, :].subgridspec(1, 3, width_ratios=[1.4, 1, 1])

        # 사업장별 총급여
        ax1 = self._figure.add_subplot(gs_top[0, 0])
        sites = a.sites[:8]
        if sites:
            names = [self._short(s.name, 14) for s in sites]
            grosses = [s.gross / 1_000_000 for s in sites]
            bars = ax1.barh(names[::-1], grosses[::-1], color=_NAVY, height=0.62)
            ax1.set_xlabel("백만원", fontsize=9)
            for bar, s in zip(bars, sites[::-1]):
                ax1.text(
                    bar.get_width() + 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    f"{s.headcount}명",
                    va="center",
                    fontsize=8,
                    color=_MUTED,
                )
        else:
            ax1.axis("off")
            ax1.text(0.5, 0.5, "사업장 데이터 없음", ha="center", va="center", color=_MUTED)
        ax1.set_title("사업장·소속별 총 인건비", fontsize=10, fontweight="bold", color=_NAVY, pad=8)

        # 전월 대비 총급여
        ax2 = self._figure.add_subplot(gs_top[0, 1])
        if a.prior_summary:
            labels = ["전월", "당월"]
            gross = [a.prior_summary.total_gross / 1_000_000, ms.total_gross / 1_000_000]
            colors = ["#94A3B8", _CYAN]
            bars = ax2.bar(labels, gross, color=colors, width=0.5)
            ax2.set_ylabel("백만원", fontsize=9)
            for bar, val in zip(bars, gross):
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    f"{val:.1f}",
                    ha="center",
                    fontsize=8,
                )
            gd = getattr(a, "gross_delta", 0)
            ax2.text(
                0.5,
                0.92,
                _fmt_delta_short(gd, is_money=True),
                transform=ax2.transAxes,
                ha="center",
                fontsize=8,
                color=_NAVY,
            )
        else:
            ax2.axis("off")
            ax2.text(0.5, 0.5, "전월\n데이터 없음", ha="center", va="center", color=_MUTED, fontsize=9)
        ax2.set_title("총 인건비 전월 대비", fontsize=10, fontweight="bold", color=_NAVY, pad=8)

        # 인원 전월 대비 + 연장/특근(백만원) 소형 막대
        ax3 = self._figure.add_subplot(gs_top[0, 2])
        prior_h = a.prior_summary.employee_count if a.prior_summary else 0
        x = [0, 1]
        bars = ax3.bar(x, [prior_h, ms.employee_count], color=["#94A3B8", _CYAN], width=0.5)
        ax3.set_xticks(x, ["전월", "당월"], fontsize=9)
        ax3.set_ylabel("인원", fontsize=9)
        for bar, v in zip(bars, [prior_h, ms.employee_count]):
            ax3.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{int(v)}명",
                ha="center",
                fontsize=9,
                fontweight="bold",
            )
        hd = getattr(a, "headcount_delta", 0)
        ax3.text(
            0.5,
            0.9,
            _fmt_delta_short(hd, unit="명"),
            transform=ax3.transAxes,
            ha="center",
            fontsize=8,
            color=_NAVY,
        )
        ot_m = getattr(a, "ot_total", 0) / 1_000_000
        sp_m = getattr(a, "special_total", 0) / 1_000_000
        ax3.text(
            0.5,
            0.02,
            f"연장 {ot_m:.1f}백만 · 특근 {sp_m:.1f}백만",
            transform=ax3.transAxes,
            ha="center",
            fontsize=8,
            color=_MUTED,
        )
        ax3.set_title("인원·수당 요약", fontsize=10, fontweight="bold", color=_NAVY, pad=8)

        self._draw_ytd_charts(gs, a)

    def _draw_ytd_charts(self, gs, a: ExecutiveAnalytics) -> None:
        ax_g = self._figure.add_subplot(gs[1, 0])
        ax_d = self._figure.add_subplot(gs[1, 1])
        months = a.ytd_months
        if not months:
            for ax in (ax_g, ax_d):
                ax.axis("off")
                ax.text(0.5, 0.5, "연간 데이터 없음", ha="center", va="center", color=_MUTED)
            return

        labels = [pt.label for pt in months]
        gross_m = [pt.gross / 1_000_000 for pt in months]
        bars = ax_g.bar(labels, gross_m, color=_NAVY, width=0.55)
        ax_g.set_ylabel("백만원", fontsize=9)
        ytd_title = a.ytd_label or "연간"
        ax_g.set_title(f"{ytd_title} 총급여 추이", fontsize=10, fontweight="bold", color=_NAVY, pad=8)
        for bar, val in zip(bars, gross_m):
            ax_g.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.04,
                f"{val:.1f}",
                ha="center",
                fontsize=8,
            )

        deltas = a.ytd_gross_deltas
        if len(deltas) > 1:
            d_labels = [d.label for d in deltas[1:]]
            d_vals = [d.delta / 1_000_000 for d in deltas[1:]]
            colors = [_CYAN if v >= 0 else "#F59E0B" for v in d_vals]
            bars_d = ax_d.bar(d_labels, d_vals, color=colors, width=0.55)
            ax_d.axhline(0, color="#CBD5E1", linewidth=0.8)
            ax_d.set_ylabel("백만원", fontsize=9)
            ax_d.set_title(
                f"{ytd_title} 전월 대비 총급여 차이",
                fontsize=10,
                fontweight="bold",
                color=_NAVY,
                pad=8,
            )
            for bar, val in zip(bars_d, d_vals):
                ypos = bar.get_height()
                va = "bottom" if ypos >= 0 else "top"
                offset = 0.03 if ypos >= 0 else -0.03
                ax_d.text(
                    bar.get_x() + bar.get_width() / 2,
                    ypos + offset,
                    f"{ypos:+.1f}",
                    ha="center",
                    va=va,
                    fontsize=8,
                )
        else:
            ax_d.axis("off")
            ax_d.text(
                0.5,
                0.5,
                "2개월 이상\n데이터 필요",
                ha="center",
                va="center",
                color=_MUTED,
                fontsize=9,
            )

    @staticmethod
    def _short(name: str, n: int) -> str:
        return name if len(name) <= n else name[: n - 1] + "…"
