"""
ui/workflow_hub_panel.py - 업무·전자결재 허브 (사원용 메인 화면)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from core.paths import app_data_dir

from core.session_service import get_session, require_session, session_tenant_id
from core.user_store import list_users_for_tenant
from core.workflow.constants import (
    DOC_STATUS_LABELS,
    DOC_TEMPLATES,
    DOC_TYPE_LABELS,
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_NOT_APPLICABLE,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    TASK_STATUS_LABELS,
    TRIP_STATUS_LABELS,
)
from core.workflow.inbox import GW_INBOX_QUICK_TABS, INBOX_DEFINITIONS, INBOX_LABELS
from core.workflow import service as wf_svc
from core.workflow.form_templates import ensure_form_templates, list_templates
from core.workflow.permissions import can_approve_document
from services.workflow_ai import draft_assist, executive_summary_ai
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel
from ui.workflow_compose_dialog import open_compose_dialog
from ui.workflow_theme import (
    INBOX_UI,
    STATUS_UI,
    TAB_ITEMS,
    TEMPLATE_UI,
    WF,
    flat_button,
    setup_workflow_ttk_style,
)

KPI_REFLECTION_LABELS = {
    KPI_REFLECTION_BLOCKED: "대기",
    KPI_REFLECTION_READY: "반영 가능",
    KPI_REFLECTION_REFLECTED: "반영 완료",
    KPI_REFLECTION_NOT_APPLICABLE: "대상 아님",
}


def format_business_trip_dashboard_lines(dashboard: dict[str, Any]) -> list[str]:
    """Format manager-scoped business-trip dashboard rows for Tk text panes."""
    counts = dashboard.get("counts") or {}
    kpi_summary = dashboard.get("kpi_summary") or {}
    lines = [
        "출장 lifecycle 현황",
        "=" * 40,
        (
            f"진행 {counts.get('ongoing', 0)}건 · 완료 {counts.get('completed', 0)}건 · "
            f"지연 {counts.get('overdue', 0)}건"
        ),
        (
            "실적반영: "
            f"대기 {kpi_summary.get(KPI_REFLECTION_BLOCKED, 0)} · "
            f"가능 {kpi_summary.get(KPI_REFLECTION_READY, 0)} · "
            f"완료 {kpi_summary.get(KPI_REFLECTION_REFLECTED, 0)}"
        ),
    ]
    sections = dashboard.get("sections") or {}
    for key, label in (("overdue", "지연"), ("ongoing", "진행"), ("completed", "완료")):
        rows = list(sections.get(key) or [])
        lines.append(f"\n[{label}] {len(rows)}건")
        if not rows:
            lines.append("  · 없음")
            continue
        for row in rows[:12]:
            status = TRIP_STATUS_LABELS.get(str(row.get("status") or ""), row.get("status") or "")
            kpi = KPI_REFLECTION_LABELS.get(str(row.get("kpi_reflection_status") or ""), "")
            lines.append(
                "  · "
                f"{row.get('title') or row.get('trip_id')} "
                f"({status} / 실적 {kpi}) "
                f"{row.get('period_start') or ''}~{row.get('period_end') or ''}"
            )
        if len(rows) > 12:
            lines.append(f"  · 외 {len(rows) - 12}건")
    return lines


class WorkflowHubPanel(tk.Frame):
    """그룹웨어형 전자결재 — 홈·결재함·작성·실행·보고."""

    def __init__(self, parent, colors: dict[str, str] | None = None, **kwargs) -> None:
        super().__init__(parent, bg=WF["page_bg"], **kwargs)
        self._colors = colors or COLORS
        self._inbox_id = tk.StringVar(value="to_approve")
        self._new_doc_type = tk.StringVar(value="GENERAL_DRAFT")
        self._inbox_counts: dict[str, int] = {}
        self._active_tab = "home"
        self._tab_frames: dict[str, tk.Frame] = {}
        self._tab_btns: dict[str, tk.Button] = {}
        self._inbox_nav_btns: dict[str, tk.Frame] = {}
        self._gw_inbox_tab_btns: dict[str, tk.Button] = {}
        self._ai_structured: dict[str, Any] | None = None
        self._inbox_search_var = tk.StringVar(value="")
        self._inbox_search_debounce_job: str | None = None
        self._inbox_search_debounce_ms = 300

        setup_workflow_ttk_style(self.winfo_toplevel())

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tab_bar()
        self._build_content_stack()
        self._select_tab("home")

    def _setup_content_scroll(self, parent: tk.Frame) -> None:
        """탭 본문 — 세로 스크롤(휠·드래그)로 하단 UI까지 볼 수 있게."""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        self._scroll_host = tk.Frame(parent, bg=WF["page_bg"])
        self._scroll_host.grid(row=0, column=0, sticky="nsew")
        self._scroll_host.grid_rowconfigure(0, weight=1)
        self._scroll_host.grid_columnconfigure(0, weight=1)

        self._scroll_canvas = tk.Canvas(
            self._scroll_host,
            bg=WF["page_bg"],
            highlightthickness=0,
            bd=0,
        )
        yscroll = ttk.Scrollbar(self._scroll_host, orient=tk.VERTICAL, command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=yscroll.set)
        self._scroll_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self._scroll_body = tk.Frame(self._scroll_canvas, bg=WF["page_bg"])
        self._scroll_win = self._scroll_canvas.create_window((0, 0), window=self._scroll_body, anchor=tk.NW)

        def _on_scroll_configure(_event: tk.Event | None = None) -> None:
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))
            cw = self._scroll_canvas.winfo_width()
            if cw > 1:
                self._scroll_canvas.itemconfig(self._scroll_win, width=cw)

        self._scroll_body.bind("<Configure>", _on_scroll_configure)
        self._scroll_canvas.bind("<Configure>", _on_scroll_configure)

        def _drag_start(event: tk.Event) -> None:
            self._scroll_canvas.scan_mark(event.x, event.y)

        def _drag_move(event: tk.Event) -> None:
            self._scroll_canvas.scan_dragto(event.x, event.y, gain=1)

        self._scroll_drag_start = _drag_start
        self._scroll_drag_move = _drag_move
        self._scroll_canvas.bind("<ButtonPress-1>", _drag_start, add="+")
        self._scroll_canvas.bind("<B1-Motion>", _drag_move, add="+")

        bind_local_wheel(self._scroll_canvas, self._scroll_canvas)
        bind_local_wheel(self._scroll_body, self._scroll_canvas)

        self._content = tk.Frame(self._scroll_body, bg=WF["page_bg"])
        self._content.pack(fill=tk.X, anchor=tk.NW)

    def _bind_page_scroll_wheel(self, widget: tk.Misc | None = None) -> None:
        """배경·라벨 위에서도 페이지 스크롤 (Treeview/Text는 제외)."""
        root = widget or self._scroll_body
        if root is self._scroll_body:
            bind_local_wheel(root, self._scroll_canvas)
        for child in root.winfo_children():
            if isinstance(child, (ttk.Treeview, tk.Text, ttk.Combobox)):
                continue
            bind_local_wheel(child, self._scroll_canvas)
            self._bind_page_scroll_wheel(child)

    def _scroll_content_top(self) -> None:
        if hasattr(self, "_scroll_canvas"):
            self._scroll_canvas.yview_moveto(0)

    def refresh(self, *, full: bool = False) -> None:
        tid = session_tenant_id()
        if not tid:
            return
        try:
            wf_svc.ensure_tenant_seeded(tid)
            ensure_form_templates(tid)
        except Exception:
            pass
        self._update_header_stats()
        if full:
            self._reload_gw_form_library()
            self._reload_home()
            self._reload_inbox()
            self._reload_tasks()
            self._reload_trip_dashboard()
            self._reload_site_dashboard()
            self._reload_exec_dashboard()
            self._reload_closing()
        else:
            self._refresh_active_tab()
        self.after_idle(self._on_tab_scrolled)

    def _refresh_active_tab(self) -> None:
        tab = self._active_tab
        if tab == "home":
            self._reload_home()
        elif tab == "inbox":
            self._reload_inbox()
        elif tab == "tasks":
            self._reload_tasks()
        elif tab == "reports":
            self._reload_trip_dashboard()
            self._reload_site_dashboard()
            self._reload_exec_dashboard()
        elif tab == "new":
            self._reload_gw_form_library()
        elif tab == "closing":
            self._reload_closing()

    def _tenant(self) -> str:
        from core.group_store import get_workflow_tenant_id

        tid = session_tenant_id()
        if not tid:
            raise PermissionError("로그인이 필요합니다.")
        return get_workflow_tenant_id(tid)

  # ── 레이아웃 ─────────────────────────────────────────────

    def _build_header(self) -> None:
        self._header = tk.Frame(self, bg=WF["header_bg"], padx=20, pady=14)
        self._header.grid(row=0, column=0, sticky="ew")

        left = tk.Frame(self._header, bg=WF["header_bg"])
        left.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            left,
            text="업무 · 전자결재",
            bg=WF["header_bg"],
            fg=WF["header_fg"],
            font=(FONT, 18, "bold"),
        ).pack(anchor=tk.W)
        self._header_sub = tk.Label(
            left,
            text="결재·기안·실행업무를 한곳에서",
            bg=WF["header_bg"],
            fg=WF["header_sub"],
            font=(FONT, 10),
        )
        self._header_sub.pack(anchor=tk.W, pady=(2, 0))

        right = tk.Frame(self._header, bg=WF["header_bg"])
        right.pack(side=tk.RIGHT)
        self._header_stats = tk.Label(
            right,
            text="",
            bg=WF["header_bg"],
            fg="#E0F4FD",
            font=(FONT, 10),
            justify=tk.RIGHT,
        )
        self._header_stats.pack(side=tk.RIGHT, padx=(0, 12))
        flat_button(
            right,
            "전체 새로고침",
            command=lambda: self.refresh(full=True),
            bg=COLORS["nav_accent"],
            fg="#FFFFFF",
            font=(FONT, 9, "bold"),
            padx=12,
            pady=6,
            active_bg="#0096D1",
        ).pack(side=tk.RIGHT)

    def _update_header_stats(self) -> None:
        try:
            c = wf_svc.inbox_counts(self._tenant())
            pending = c.get("to_approve", 0)
            prog = c.get("in_progress", 0)
            trip_counts = wf_svc.business_trip_manager_dashboard(
                self._tenant(),
                session=require_session(),
            ).get("counts", {})
            self._header_stats.configure(
                text=(
                    f"결재 대기 {pending}건  ·  진행 {prog}건\n"
                    f"출장 진행 {trip_counts.get('ongoing', 0)}건  ·  지연 {trip_counts.get('overdue', 0)}건"
                )
            )
        except Exception:
            self._header_stats.configure(text="")

    def _build_tab_bar(self) -> None:
        wrap = tk.Frame(self, bg=WF["page_bg"])
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self._tab_bar = tk.Frame(wrap, bg=WF["tab_bar_bg"], padx=8, pady=10)
        self._tab_bar.grid(row=0, column=0, sticky="ew")

        for tab_id, label in TAB_ITEMS:
            btn = tk.Button(
                self._tab_bar,
                text=f"  {label}  ",
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                font=(FONT, 10, "bold"),
                padx=16,
                pady=8,
                command=lambda t=tab_id: self._select_tab(t),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self._tab_btns[tab_id] = btn

        scroll_wrap = tk.Frame(wrap, bg=WF["page_bg"])
        scroll_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._setup_content_scroll(scroll_wrap)

    def _build_content_stack(self) -> None:
        for tab_id, _ in TAB_ITEMS:
            frame = tk.Frame(self._content, bg=WF["page_bg"])
            self._tab_frames[tab_id] = frame

        self._build_home_tab(self._tab_frames["home"])
        self._build_inbox_tab(self._tab_frames["inbox"])
        self._build_new_tab(self._tab_frames["new"])
        self._build_tasks_tab(self._tab_frames["tasks"])
        self._build_reports_tab(self._tab_frames["reports"])
        self._build_closing_tab(self._tab_frames["closing"])

    def _select_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        for tid, frame in self._tab_frames.items():
            if tid == tab_id:
                frame.pack(fill=tk.X, anchor=tk.NW)
            else:
                frame.pack_forget()
        for tid, btn in self._tab_btns.items():
            if tid == tab_id:
                btn.configure(bg=WF["tab_active"], fg=WF["tab_active_fg"])
            else:
                btn.configure(bg=WF["tab_inactive"], fg=WF["tab_inactive_fg"])
        self._scroll_content_top()
        self.after_idle(self._on_tab_scrolled)
        if tab_id == "inbox":
            self._reload_inbox()
        elif tab_id == "new":
            self.after_idle(self._reload_gw_form_library)

    def _on_tab_scrolled(self) -> None:
        self._bind_page_scroll_wheel()
        if hasattr(self, "_scroll_canvas"):
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _card(self, parent: tk.Misc, **pad) -> tk.Frame:
        f = tk.Frame(
            parent,
            bg=WF["card"],
            highlightbackground=WF["card_border"],
            highlightthickness=1,
            **pad,
        )
        return f

  # ── 홈 ─────────────────────────────────────────────────

    def _build_home_tab(self, parent: tk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        quick = self._card(parent, padx=16, pady=16)
        quick.pack(fill=tk.X, pady=(0, 12))
        inner = tk.Frame(quick, bg=WF["card"], padx=16, pady=14)
        inner.pack(fill=tk.X)
        tk.Label(
            inner,
            text="빠른 작성",
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 12, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))
        row = tk.Frame(inner, bg=WF["card"])
        row.pack(fill=tk.X)
        for dtype, title, _desc in DOC_TEMPLATES:
            meta = TEMPLATE_UI.get(dtype, (title, "📄", COLORS["accent"]))
            label, icon, color = meta
            cell = tk.Frame(row, bg=WF["card"], padx=4)
            cell.pack(side=tk.LEFT, padx=(0, 8))
            btn = tk.Frame(cell, bg=color, cursor="hand2")
            btn.pack()
            btn.bind("<Button-1>", lambda _e, d=dtype: self._start_template(d))
            tk.Label(btn, text=icon, bg=color, fg="#FFFFFF", font=(FONT, 16)).pack(padx=20, pady=(10, 0))
            tk.Label(btn, text=label, bg=color, fg="#FFFFFF", font=(FONT, 10, "bold")).pack(padx=12, pady=(4, 10))
            for w in (btn, *btn.winfo_children()):
                if isinstance(w, tk.Label):
                    w.bind("<Button-1>", lambda _e, d=dtype: self._start_template(d))

        self._home_cards = tk.Frame(parent, bg=WF["page_bg"])
        self._home_cards.pack(fill=tk.X)
        for c in range(3):
            self._home_cards.grid_columnconfigure(c, weight=1, uniform="hc")

    def _reload_home(self) -> None:
        for w in self._home_cards.winfo_children():
            w.destroy()
        try:
            self._inbox_counts = wf_svc.inbox_counts(self._tenant())
        except Exception:
            self._inbox_counts = {}

        col = 0
        row = 0
        for iid, label, desc, _ref in INBOX_DEFINITIONS:
            if iid == "all":
                continue
            ui = INBOX_UI.get(iid, {})
            color = ui.get("color", COLORS["accent"])
            light = ui.get("light", WF["card"])
            icon = ui.get("icon", "•")
            cnt = self._inbox_counts.get(iid, 0)

            card = self._card(self._home_cards, padx=0, pady=0)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            accent = tk.Frame(card, bg=color, width=5)
            accent.pack(side=tk.LEFT, fill=tk.Y)
            body = tk.Frame(card, bg=WF["card"], padx=14, pady=12)
            body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            top = tk.Frame(body, bg=WF["card"])
            top.pack(fill=tk.X)
            tk.Label(top, text=icon, bg=light, fg=color, font=(FONT, 12), padx=6, pady=2).pack(side=tk.LEFT)
            tk.Label(top, text=label, bg=WF["card"], fg=COLORS["text"], font=(FONT, 11, "bold")).pack(
                side=tk.LEFT, padx=(8, 0)
            )
            tk.Label(
                body,
                text=f"{cnt}",
                bg=WF["card"],
                fg=color,
                font=(FONT, 28, "bold"),
            ).pack(anchor=tk.W, pady=(8, 2))
            tk.Label(
                body,
                text="건",
                bg=WF["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(anchor=tk.W)
            tk.Label(
                body,
                text=desc,
                bg=WF["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                wraplength=200,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(6, 10))

            flat_button(
                body,
                "함 열기 →",
                command=lambda x=iid: self._open_inbox(x),
                bg=light,
                fg=color,
                font=(FONT, 9, "bold"),
                padx=10,
                pady=5,
                active_bg=color,
            ).pack(anchor=tk.W)

            col += 1
            if col >= 3:
                col = 0
                row += 1
        self.after_idle(self._on_tab_scrolled)

    def _open_inbox(self, inbox_id: str) -> None:
        self._inbox_id.set(inbox_id)
        self._highlight_inbox_nav(inbox_id)
        self._select_tab("inbox")
        self._reload_inbox()

    def _start_template(self, document_type: str, *, template_id: str = "") -> None:
        open_compose_dialog(
            self,
            document_type=document_type,
            template_id=template_id or None,
            on_saved=self.refresh,
        )

    def _start_gw_template(self, template_id: str) -> None:
        open_compose_dialog(self, template_id=template_id, on_saved=self.refresh)

  # ── 결재함 ─────────────────────────────────────────────

    def _build_inbox_tab(self, parent: tk.Frame) -> None:
        parent.grid_columnconfigure(1, weight=1)

        # 왼쪽 결재함 목록
        nav_card = self._card(parent)
        nav_card.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        nav_inner = tk.Frame(nav_card, bg=WF["sidebar_bg"], padx=4, pady=8)
        nav_inner.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            nav_inner,
            text="결재함",
            bg=WF["sidebar_bg"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
            padx=8,
        ).pack(anchor=tk.W, pady=(4, 8))

        self._inbox_nav_host = tk.Frame(nav_inner, bg=WF["sidebar_bg"])
        self._inbox_nav_host.pack(fill=tk.BOTH, expand=True)
        for iid, label, _desc, _ref in INBOX_DEFINITIONS:
            self._make_inbox_nav_btn(iid, label)

        # 오른쪽 문서 목록
        main = self._card(parent)
        main.grid(row=0, column=1, sticky="new")
        main.grid_columnconfigure(0, weight=1)

        quick_tabs = tk.Frame(main, bg=WF["card"])
        quick_tabs.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        for iid, label in GW_INBOX_QUICK_TABS:
            btn = tk.Button(
                quick_tabs,
                text=f"  {label}  ",
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                font=(FONT, 10, "bold"),
                padx=12,
                pady=6,
                command=lambda x=iid: self._select_gw_inbox_tab(x),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self._gw_inbox_tab_btns[iid] = btn

        top = tk.Frame(main, bg=WF["card"], padx=16, pady=12)
        top.grid(row=1, column=0, sticky="ew")
        self._inbox_title = tk.Label(
            top,
            text="결재할 문서",
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        )
        self._inbox_title.pack(side=tk.LEFT)
        self._inbox_count_lbl = tk.Label(
            top,
            text="",
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9, "bold"),
            padx=8,
            pady=2,
        )
        self._inbox_count_lbl.pack(side=tk.LEFT, padx=(10, 0))
        flat_button(
            top,
            "새로고침",
            command=self._reload_inbox,
            bg=WF["tab_inactive"],
            fg=COLORS["text"],
            font=(FONT, 9),
            padx=10,
            pady=5,
        ).pack(side=tk.RIGHT)

        search_row = tk.Frame(main, bg=WF["card"], padx=16)
        search_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        tk.Label(search_row, text="검색", bg=WF["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(side=tk.LEFT)
        search_entry = tk.Entry(
            search_row,
            textvariable=self._inbox_search_var,
            font=(FONT, 10),
            width=36,
        )
        search_entry.pack(side=tk.LEFT, padx=(8, 8))
        search_entry.bind("<KeyRelease>", lambda _e: self._schedule_inbox_reload())
        flat_button(
            search_row,
            "지우기",
            command=lambda: (self._inbox_search_var.set(""), self._reload_inbox()),
            bg=WF["tab_inactive"],
            fg=COLORS["text"],
            font=(FONT, 8),
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT)

        tree_wrap = tk.Frame(main, bg=WF["card"], padx=12)
        tree_wrap.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        tree_wrap.grid_columnconfigure(0, weight=1)

        cols = ("type", "title", "requester", "updated", "status", "no", "amount")
        self._doc_tree = ttk.Treeview(
            tree_wrap,
            columns=cols,
            show="headings",
            style="Workflow.Treeview",
            height=12,
        )
        for c, t, w in [
            ("type", "유형", 88),
            ("title", "제목", 300),
            ("requester", "기안자", 88),
            ("updated", "일자", 100),
            ("status", "상태", 80),
            ("no", "문서번호", 100),
            ("amount", "금액", 88),
        ]:
            self._doc_tree.heading(c, text=t)
            self._doc_tree.column(c, width=w, anchor=tk.W if c in ("title", "no") else tk.CENTER)
        self._doc_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self._doc_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self._doc_tree.configure(yscrollcommand=scroll.set)
        self._doc_tree.bind("<Double-1>", lambda _e: self._open_selected_document())
        self._doc_tree.bind("<<TreeviewSelect>>", lambda _e: self._update_inbox_action_buttons())

        for st, (fg, bg) in STATUS_UI.items():
            self._doc_tree.tag_configure(st, foreground=fg)

        btn_row = tk.Frame(main, bg=WF["card"], padx=16)
        btn_row.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        flat_button(
            btn_row,
            "상세 보기",
            command=self._open_selected_document,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            padx=12,
            pady=7,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._btn_quick_approve = flat_button(
            btn_row,
            "승인",
            command=self._quick_approve,
            bg=COLORS["success"],
            fg="#FFFFFF",
            padx=14,
            pady=7,
        )
        self._btn_quick_approve.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_quick_reject = flat_button(
            btn_row,
            "반려",
            command=self._quick_reject,
            bg="#DC2626",
            fg="#FFFFFF",
            padx=14,
            pady=7,
        )
        self._btn_quick_reject.pack(side=tk.LEFT, padx=(0, 6))
        flat_button(
            btn_row,
            "+ 새 문서 작성",
            command=lambda: self._select_tab("new"),
            bg=COLORS["nav_accent"],
            fg="#FFFFFF",
            padx=12,
            pady=7,
        ).pack(side=tk.RIGHT)

        self._highlight_inbox_nav(self._inbox_id.get())
        self._highlight_gw_inbox_tabs(self._inbox_id.get())

    def _select_gw_inbox_tab(self, inbox_id: str) -> None:
        self._inbox_id.set(inbox_id)
        self._highlight_inbox_nav(inbox_id)
        self._highlight_gw_inbox_tabs(inbox_id)
        self._inbox_title.configure(text=INBOX_LABELS.get(inbox_id, inbox_id))
        self._reload_inbox()

    def _highlight_gw_inbox_tabs(self, iid: str) -> None:
        for kid, btn in self._gw_inbox_tab_btns.items():
            if kid == iid:
                btn.configure(bg=WF["tab_active"], fg=WF["tab_active_fg"])
            else:
                btn.configure(bg=WF["tab_inactive"], fg=WF["tab_inactive_fg"])

    def _make_inbox_nav_btn(self, iid: str, label: str) -> None:
        ui = INBOX_UI.get(iid, {})
        color = ui.get("color", COLORS["accent"])

        row = tk.Frame(self._inbox_nav_host, bg=WF["sidebar_bg"], cursor="hand2")
        row.pack(fill=tk.X, pady=2, padx=4)
        bar = tk.Frame(row, bg=WF["sidebar_bg"], width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        inner = tk.Frame(row, bg=WF["sidebar_bg"], padx=8, pady=8)
        inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl = tk.Label(
            inner,
            text=label,
            bg=WF["sidebar_bg"],
            fg=COLORS["text"],
            font=(FONT, 10),
            anchor=tk.W,
        )
        lbl.pack(side=tk.LEFT)
        cnt_lbl = tk.Label(
            inner,
            text="0",
            bg=color,
            fg="#FFFFFF",
            font=(FONT, 8, "bold"),
            padx=6,
            pady=1,
        )
        cnt_lbl.pack(side=tk.RIGHT)

        def _click(_e=None, x: str = iid) -> None:
            self._inbox_id.set(x)
            self._inbox_title.configure(text=INBOX_LABELS.get(x, x))
            self._highlight_inbox_nav(x)
            self._highlight_gw_inbox_tabs(x)
            self._reload_inbox()

        for w in (row, inner, lbl, bar):
            w.bind("<Button-1>", _click)
        self._inbox_nav_btns[iid] = {"row": row, "bar": bar, "inner": inner, "lbl": lbl, "cnt": cnt_lbl, "color": color}

    def _highlight_inbox_nav(self, iid: str) -> None:
        for kid, parts in self._inbox_nav_btns.items():
            active = kid == iid
            bg = WF["sidebar_active"] if active else WF["sidebar_bg"]
            bar_c = parts["color"] if active else WF["sidebar_bg"]
            for key in ("row", "inner", "lbl"):
                parts[key].configure(bg=bg)
            parts["bar"].configure(bg=bar_c)
            parts["lbl"].configure(font=(FONT, 10, "bold") if active else (FONT, 10))

    def _refresh_inbox_nav_counts(self) -> None:
        for iid, parts in self._inbox_nav_btns.items():
            n = self._inbox_counts.get(iid, 0)
            parts["cnt"].configure(text=str(n) if n else "·")

    def _schedule_inbox_reload(self) -> None:
        if self._inbox_search_debounce_job is not None:
            try:
                self.after_cancel(self._inbox_search_debounce_job)
            except Exception:
                pass
        self._inbox_search_debounce_job = self.after(
            self._inbox_search_debounce_ms, self._run_debounced_inbox_reload
        )

    def _run_debounced_inbox_reload(self) -> None:
        self._inbox_search_debounce_job = None
        self._reload_inbox()

    def _reload_inbox(self) -> None:
        try:
            tid = self._tenant()
            sess = require_session()
            inbox = self._inbox_id.get() or "to_approve"
            docs = wf_svc.list_documents(tid, inbox=inbox, session=sess)
            self._inbox_counts = wf_svc.inbox_counts(tid, session=sess)
            self._refresh_inbox_nav_counts()
            self._update_header_stats()
        except PermissionError as exc:
            messagebox.showwarning("안내", str(exc), parent=self.winfo_toplevel())
            return
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())
            return

        q = self._inbox_search_var.get().strip().lower()
        if q:
            docs = [
                d
                for d in docs
                if q in str(d.get("title") or "").lower()
                or q in str(d.get("document_type") or "").lower()
                or q in str(d.get("requested_date") or "").lower()
                or q in str(d.get("created_at") or "").lower()
                or q in str((d.get("content_json") or {}).get("gw_form_name") or "").lower()
            ]

        user_names = {u.user_id: u.display_name for u in list_users_for_tenant(tid)}
        self._inbox_count_lbl.configure(text=f"  {len(docs)}건  ")
        ui = INBOX_UI.get(inbox, {})
        if ui:
            self._inbox_count_lbl.configure(bg=ui.get("light", "#E0F4FD"), fg=ui.get("color", COLORS["accent"]))

        for i in self._doc_tree.get_children():
            self._doc_tree.delete(i)
        for d in docs:
            st = d.get("status", "")
            self._doc_tree.insert(
                "",
                tk.END,
                iid=d["id"],
                tags=(st,) if st in STATUS_UI else (),
                values=(
                    DOC_TYPE_LABELS.get(d.get("document_type", ""), ""),
                    d.get("title", ""),
                    user_names.get(d.get("requester_id", ""), ""),
                    (d.get("updated_at") or d.get("created_at") or "")[:16],
                    DOC_STATUS_LABELS.get(st, st),
                    d.get("document_no", ""),
                    f"{int(d.get('total_amount') or 0):,}" if d.get("total_amount") else "",
                ),
            )

        self._update_inbox_action_buttons()

    def _update_inbox_action_buttons(self) -> None:
        """선택 문서·결재 권한에 따라 승인/반려 버튼 활성화."""
        can_act = False
        doc_id = self._selected_doc_id()
        if doc_id:
            try:
                doc = wf_svc.get_document(self._tenant(), doc_id, session=require_session())
                can_act = can_approve_document(require_session(), doc, tenant_id=self._tenant())
            except Exception:
                can_act = False
        state = tk.NORMAL if can_act else tk.DISABLED
        self._btn_quick_approve.configure(state=state)
        self._btn_quick_reject.configure(state=state)

    def _reload_gw_form_library(self) -> None:
        if not hasattr(self, "_gw_form_buttons_host"):
            return
        for w in self._gw_form_buttons_host.winfo_children():
            w.destroy()
        try:
            templates = list_templates(self._tenant())
        except Exception:
            templates = []
        if not templates:
            tk.Label(
                self._gw_form_buttons_host,
                text="양식함이 비어 있습니다. tools/gw_import/sync_gw_extended.py 를 실행하세요.",
                bg=WF["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W)
            return
        row = tk.Frame(self._gw_form_buttons_host, bg=WF["card"])
        row.pack(fill=tk.X)
        col = 0
        for tpl in templates[:36]:
            tid = str(tpl.get("id") or "")
            name = str(tpl.get("name") or tid)[:22]
            cat = str(tpl.get("category") or "")
            b = flat_button(
                row,
                f"{name}\n({cat})",
                command=lambda t=tid: self._start_gw_template(t),
                bg="#1F3864",
                fg="#FFFFFF",
                font=(FONT, 8),
                padx=6,
                pady=4,
            )
            b.pack(side=tk.LEFT, padx=(0, 4), pady=2)
            col += 1
            if col >= 4:
                row = tk.Frame(self._gw_form_buttons_host, bg=WF["card"])
                row.pack(fill=tk.X)
                col = 0
        if len(templates) > 36:
            tk.Label(
                self._gw_form_buttons_host,
                text=f"외 {len(templates) - 36}개 양식 — 검색·추가 수집은 GW 동기화 스크립트 사용",
                bg=WF["card"],
                fg=COLORS["muted"],
                font=(FONT, 8),
            ).pack(anchor=tk.W, pady=(4, 0))

  # ── 작성 ─────────────────────────────────────────────

    def _build_new_tab(self, parent: tk.Frame) -> None:
        card = self._card(parent, padx=4, pady=4)
        card.pack(fill=tk.X, anchor=tk.NW)
        form = tk.Frame(card, bg=WF["card"], padx=20, pady=16)
        form.pack(fill=tk.X, anchor=tk.NW)

        tk.Label(
            form,
            text="새 문서 작성",
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            form,
            text="양식을 선택하면 필수 항목·결재선·참조를 포함한 작성 창이 열립니다.",
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor=tk.W, pady=(4, 12))

        flat_button(
            form,
            "양식 작성 열기 (결재선·필수항목)",
            command=lambda: open_compose_dialog(self, on_saved=self.refresh),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            font=(FONT, 11, "bold"),
            padx=16,
            pady=10,
        ).pack(anchor=tk.W, pady=(0, 12))

        tk.Label(form, text="빠른 양식 선택", bg=WF["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            anchor=tk.W, pady=(0, 8)
        )

        tpl = tk.Frame(form, bg=WF["card"])
        tpl.pack(fill=tk.X, pady=(0, 16))
        for dtype, title, _desc in DOC_TEMPLATES:
            meta = TEMPLATE_UI.get(dtype, (title, "📄", COLORS["accent"]))
            _, icon, color = meta
            b = flat_button(
                tpl,
                f"{icon} {title}",
                command=lambda d=dtype: self._start_template(d),
                bg=color,
                fg="#FFFFFF",
                font=(FONT, 9, "bold"),
                padx=10,
                pady=6,
            )
            b.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(form, text="COSS 양식함 (그룹웨어)", bg=WF["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            anchor=tk.W, pady=(8, 6)
        )
        gw_box = tk.Frame(form, bg=WF["card"])
        gw_box.pack(fill=tk.X, pady=(0, 8))
        self._gw_form_buttons_host = gw_box

        def _field_label(text: str) -> None:
            tk.Label(form, text=text, bg=WF["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(
                anchor=tk.W, pady=(10, 2)
            )

        _field_label("문서 유형")
        type_combo = ttk.Combobox(
            form,
            textvariable=self._new_doc_type,
            values=list(DOC_TYPE_LABELS.keys()),
            state="readonly",
            width=36,
            font=FONT_BODY,
        )
        type_combo.pack(anchor=tk.W, fill=tk.X)
        type_combo.bind("<<ComboboxSelected>>", self._on_doc_type_changed)

        _field_label("제목")
        self._new_title = tk.Text(
            form,
            height=2,
            font=FONT_BODY,
            wrap=tk.WORD,
            relief=tk.FLAT,
            highlightbackground=WF["card_border"],
            highlightthickness=1,
            padx=8,
            pady=6,
        )
        self._new_title.pack(fill=tk.X)

        _field_label("요약 / 본문")
        self._new_summary = tk.Text(
            form,
            height=5,
            font=FONT_BODY,
            wrap=tk.WORD,
            relief=tk.FLAT,
            highlightbackground=WF["card_border"],
            highlightthickness=1,
            padx=8,
            pady=6,
        )
        self._new_summary.pack(fill=tk.X)

        _field_label("금액 (원)")
        self._new_amount = tk.Entry(
            form,
            font=FONT_BODY,
            relief=tk.FLAT,
            highlightbackground=WF["card_border"],
            highlightthickness=1,
        )
        self._new_amount.pack(anchor=tk.W, fill=tk.X, ipady=4)

        btn_row = tk.Frame(form, bg=WF["card"])
        btn_row.pack(fill=tk.X, pady=(16, 0))
        flat_button(
            btn_row,
            "AI 작성 도우미",
            command=self._ai_draft,
            bg="#7C3AED",
            fg="#FFFFFF",
            padx=12,
            pady=8,
        ).pack(side=tk.LEFT, padx=(0, 8))
        flat_button(
            btn_row,
            "임시저장",
            command=lambda: self._save_new(submit=False),
            bg=WF["tab_inactive"],
            fg=COLORS["text"],
            padx=12,
            pady=8,
        ).pack(side=tk.LEFT, padx=(0, 8))
        flat_button(
            btn_row,
            "상신",
            command=lambda: self._save_new(submit=True),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            padx=20,
            pady=8,
        ).pack(side=tk.LEFT)

        self._ai_preview = tk.Label(
            form,
            text="",
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            justify=tk.LEFT,
            wraplength=720,
            anchor=tk.W,
            padx=10,
            pady=8,
        )
        self._ai_preview.pack(fill=tk.X, pady=(12, 0))
        self._on_doc_type_changed()

    def _on_doc_type_changed(self, _e=None) -> None:
        dtype = self._new_doc_type.get()
        label = DOC_TYPE_LABELS.get(dtype, dtype)
        if not self._new_title.get("1.0", tk.END).strip():
            self._new_title.delete("1.0", tk.END)
            self._new_title.insert("1.0", f"{label} — ")

  # ── 실행업무 · 보고 · 마감 ───────────────────────────

    def _build_tasks_tab(self, parent: tk.Frame) -> None:
        card = self._card(parent)
        card.pack(fill=tk.X, anchor=tk.NW)
        inner = tk.Frame(card, bg=WF["card"], padx=16, pady=12)
        inner.pack(fill=tk.X, anchor=tk.NW)
        inner.grid_columnconfigure(0, weight=1)

        top = tk.Frame(inner, bg=WF["card"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            top,
            text="실행업무",
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            top,
            text="승인 완료 후 자동 생성된 후속 업무",
            bg=WF["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(side=tk.LEFT, padx=(10, 0))
        flat_button(top, "새로고침", command=self._reload_tasks, bg=WF["tab_inactive"], fg=COLORS["text"], padx=10, pady=5).pack(
            side=tk.RIGHT
        )

        cols = ("title", "status", "due", "site")
        self._task_tree = ttk.Treeview(inner, columns=cols, show="headings", style="Workflow.Treeview", height=10)
        for c, t, w in [("title", "업무명", 360), ("status", "상태", 88), ("due", "마감", 100), ("site", "사업장", 120)]:
            self._task_tree.heading(c, text=t)
            self._task_tree.column(c, width=w)
        self._task_tree.grid(row=1, column=0, sticky="ew")
        flat_button(
            inner,
            "선택 업무 완료 처리",
            command=self._complete_selected_task,
            bg=COLORS["success"],
            fg="#FFFFFF",
            padx=12,
            pady=7,
        ).grid(row=2, column=0, sticky=tk.W, pady=(10, 0))

    def _build_reports_tab(self, parent: tk.Frame) -> None:
        sub_bar = tk.Frame(parent, bg=WF["page_bg"])
        sub_bar.pack(fill=tk.X, pady=(0, 8))
        self._report_tab = tk.StringVar(value="trip")
        for val, label in (("trip", "출장 현황"), ("site", "사업장 현황"), ("exec", "임원 통합")):
            flat_button(
                sub_bar,
                label,
                command=lambda v=val: self._show_report_pane(v),
                bg=COLORS["accent"] if val == "trip" else WF["tab_inactive"],
                fg="#FFFFFF" if val == "trip" else COLORS["text"],
                padx=14,
                pady=6,
            ).pack(side=tk.LEFT, padx=(0, 6))

        self._report_stack = tk.Frame(parent, bg=WF["page_bg"])
        self._report_stack.pack(fill=tk.X, anchor=tk.NW)
        self._report_trip = self._card(self._report_stack)
        self._report_site = self._card(self._report_stack)
        self._report_exec = self._card(self._report_stack)
        trip_top = tk.Frame(self._report_trip, bg=WF["card"], padx=12, pady=8)
        trip_top.pack(fill=tk.X)
        flat_button(
            trip_top,
            "지연 평가 · 새로고침",
            command=self._reload_trip_dashboard,
            bg="#0F766E",
            fg="#FFFFFF",
            padx=10,
            pady=5,
        ).pack(side=tk.RIGHT)
        self._trip_text = tk.Text(
            self._report_trip,
            font=FONT_BODY,
            wrap=tk.WORD,
            bg=WF["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=16,
            pady=12,
            height=18,
            state=tk.DISABLED,
        )
        self._trip_text.pack(fill=tk.X, anchor=tk.NW)
        self._site_text = tk.Text(
            self._report_site,
            font=FONT_BODY,
            wrap=tk.WORD,
            bg=WF["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=16,
            pady=12,
            height=18,
            state=tk.DISABLED,
        )
        self._site_text.pack(fill=tk.X, anchor=tk.NW)
        exec_top = tk.Frame(self._report_exec, bg=WF["card"], padx=12, pady=8)
        exec_top.pack(fill=tk.X)
        flat_button(exec_top, "AI 요약 생성", command=self._exec_ai_summary, bg="#7C3AED", fg="#FFFFFF", padx=10, pady=5).pack(
            side=tk.RIGHT
        )
        self._exec_text = tk.Text(
            self._report_exec,
            font=FONT_BODY,
            wrap=tk.WORD,
            bg=WF["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=16,
            pady=12,
            height=18,
            state=tk.DISABLED,
        )
        self._exec_text.pack(fill=tk.X, anchor=tk.NW)
        self._show_report_pane("trip")

    def _show_report_pane(self, pane: str) -> None:
        self._report_tab.set(pane)
        for frame in (self._report_trip, self._report_site, self._report_exec):
            frame.pack_forget()
        if pane == "exec":
            self._report_exec.pack(fill=tk.X, anchor=tk.NW)
        elif pane == "site":
            self._report_site.pack(fill=tk.X, anchor=tk.NW)
        else:
            self._report_trip.pack(fill=tk.X, anchor=tk.NW)
        self.after_idle(self._on_tab_scrolled)

    def _build_closing_tab(self, parent: tk.Frame) -> None:
        card = self._card(parent)
        card.pack(fill=tk.X, anchor=tk.NW)
        tk.Label(
            card,
            text="월마감 현황",
            bg=WF["card"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
            padx=16,
        ).pack(anchor=tk.W, pady=(12, 0))
        self._closing_text = tk.Text(
            card,
            font=FONT_BODY,
            wrap=tk.WORD,
            bg=WF["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=16,
            pady=12,
            height=16,
            state=tk.DISABLED,
        )
        self._closing_text.pack(fill=tk.X, anchor=tk.NW, padx=0, pady=(0, 12))

  # ── 비즈니스 로직 (기존과 동일) ─────────────────────────

    def _selected_doc_id(self) -> str | None:
        sel = self._doc_tree.selection()
        return sel[0] if sel else None

    def _open_selected_document(self) -> None:
        doc_id = self._selected_doc_id()
        if not doc_id:
            messagebox.showinfo("안내", "문서를 선택하세요.", parent=self.winfo_toplevel())
            return
        try:
            doc = wf_svc.get_document(self._tenant(), doc_id)
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())
            return
        WorkflowDocumentDialog(
            self.winfo_toplevel(),
            doc,
            workflow_tenant_id=self._tenant(),
            on_changed=self.refresh,
        )

    def _quick_approve(self) -> None:
        doc_id = self._selected_doc_id()
        if not doc_id:
            messagebox.showinfo("안내", "문서를 선택하세요.", parent=self.winfo_toplevel())
            return
        comment = simpledialog.askstring("승인", "코멘트 (선택)", parent=self.winfo_toplevel()) or ""
        try:
            wf_svc.approve_document(self._tenant(), doc_id, comment=comment, session=require_session())
            messagebox.showinfo("완료", "승인되었습니다.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _quick_reject(self) -> None:
        doc_id = self._selected_doc_id()
        if not doc_id:
            messagebox.showinfo("안내", "문서를 선택하세요.", parent=self.winfo_toplevel())
            return
        comment = simpledialog.askstring("반려", "사유", parent=self.winfo_toplevel()) or ""
        try:
            wf_svc.reject_document(self._tenant(), doc_id, comment=comment, session=require_session())
            messagebox.showinfo("완료", "반려되었습니다.", parent=self.winfo_toplevel())
            self.refresh()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _ai_draft(self) -> None:
        raw = self._new_summary.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showinfo("안내", "요약 또는 간단한 내용을 입력하세요.", parent=self.winfo_toplevel())
            return
        try:
            amount = int(self._new_amount.get().replace(",", "") or 0)
        except ValueError:
            amount = 0
        result = draft_assist(document_type=self._new_doc_type.get(), raw_text=raw, amount=amount)
        self._ai_structured = result
        self._new_title.delete("1.0", tk.END)
        self._new_title.insert("1.0", result.get("title", ""))
        sc = result.get("structured_content") or {}
        body = "\n".join(f"{k}: {v}" for k, v in sc.items() if v)
        self._new_summary.delete("1.0", tk.END)
        self._new_summary.insert("1.0", body or result.get("summary", ""))
        self._ai_preview.configure(
            text="AI 추천이 적용되었습니다. 확인 후 임시저장 또는 상신하세요.\n" + (result.get("ai_note") or "")
        )

    def _save_new(self, *, submit: bool) -> None:
        title = self._new_title.get("1.0", tk.END).strip()
        summary = self._new_summary.get("1.0", tk.END).strip()
        if not title:
            messagebox.showwarning("안내", "제목을 입력하세요.", parent=self.winfo_toplevel())
            return
        try:
            amount = int(self._new_amount.get().replace(",", "") or 0)
        except ValueError:
            amount = 0
        tid = self._tenant()
        sess = require_session()
        from core.workflow.store import list_departments, list_sites

        sites = list_sites(tid)
        site_id = sites[0]["id"] if sites else ""
        dept_id = ""
        if sites:
            deps = list_departments(tid, site_id)
            dept_id = deps[0]["id"] if deps else ""

        try:
            doc = wf_svc.create_document(
                tid,
                document_type=self._new_doc_type.get(),
                title=title,
                summary=summary,
                content=summary,
                site_id=site_id,
                department_id=dept_id,
                total_amount=amount,
                session=sess,
            )
            if submit:
                users = list_users_for_tenant(tid)
                approver = users[1].user_id if len(users) > 1 else users[0].user_id
                line = [
                    {"approver_id": approver, "approver_role": "department_manager"},
                    {"approver_id": approver, "approver_role": "executive"},
                ]
                if self._ai_structured:
                    for step in self._ai_structured.get("recommended_approval_line") or []:
                        if step.get("approver_id"):
                            line = self._ai_structured["recommended_approval_line"]
                            break
                wf_svc.submit_document(tid, doc["id"], line, session=sess)
                messagebox.showinfo("완료", "문서가 상신되었습니다.", parent=self.winfo_toplevel())
            else:
                messagebox.showinfo("완료", "임시저장되었습니다.", parent=self.winfo_toplevel())
            self.refresh()
            self._open_inbox("in_progress" if submit else "my_draft")
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _reload_tasks(self) -> None:
        try:
            wf_svc.evaluate_business_trip_overdues(self._tenant(), session=require_session())
            tasks = wf_svc.list_execution_tasks(self._tenant(), mine_only=True)
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())
            return
        for i in self._task_tree.get_children():
            self._task_tree.delete(i)
        from core.workflow.store import list_sites

        sites = {s["id"]: s.get("name", "") for s in list_sites(self._tenant())}
        for t in tasks:
            self._task_tree.insert(
                "",
                tk.END,
                iid=t["id"],
                values=(
                    t.get("title", ""),
                    TASK_STATUS_LABELS.get(t.get("status", ""), t.get("status", "")),
                    t.get("due_date", ""),
                    sites.get(t.get("site_id", ""), ""),
                ),
            )

    def _complete_selected_task(self) -> None:
        sel = self._task_tree.selection()
        if not sel:
            return
        try:
            wf_svc.complete_execution_task(self._tenant(), sel[0])
            messagebox.showinfo("완료", "실행업무를 완료 처리했습니다.", parent=self.winfo_toplevel())
            self._reload_tasks()
            self._reload_trip_dashboard()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _reload_trip_dashboard(self) -> None:
        if not hasattr(self, "_trip_text"):
            return
        try:
            wf_svc.evaluate_business_trip_overdues(self._tenant(), session=require_session())
            dashboard = wf_svc.business_trip_manager_dashboard(self._tenant(), session=require_session())
        except Exception as exc:
            self._set_text(self._trip_text, str(exc))
            return
        self._set_text(self._trip_text, "\n".join(format_business_trip_dashboard_lines(dashboard)))

    def _reload_site_dashboard(self) -> None:
        month = date.today().strftime("%Y-%m")
        try:
            data = wf_svc.site_summary(self._tenant(), month)
        except Exception as exc:
            self._set_text(self._site_text, str(exc))
            return
        lines = [f"사업장별 현황  ·  {month}\n", "=" * 40]
        for s in data.get("sites", []):
            lines.append(
                f"\n▸ {s.get('site_name', '')}\n"
                f"   결재 대기     {s.get('pending_approvals', 0):>4}건\n"
                f"   승인 완료     {s.get('approved_count', 0):>4}건\n"
                f"   반려          {s.get('rejected_count', 0):>4}건\n"
                f"   구매(승인)    {s.get('purchase_amount', 0):>12,}원\n"
                f"   지출(승인)    {s.get('expense_amount', 0):>12,}원\n"
                f"   지연 실행업무 {s.get('delayed_tasks', 0):>4}건"
            )
        self._set_text(self._site_text, "\n".join(lines))

    def _reload_exec_dashboard(self) -> None:
        month = date.today().strftime("%Y-%m")
        try:
            data = wf_svc.executive_summary(self._tenant(), month)
        except Exception as exc:
            self._set_text(self._exec_text, str(exc))
            return
        self._last_exec_summary = data
        lines = [
            f"임원 통합 보고  ·  {month}\n",
            "=" * 40,
            f"\n총 지출(승인)   {data.get('total_expense', 0):>14,}원",
            f"총 구매(승인)   {data.get('total_purchase', 0):>14,}원",
            f"결재 대기       {data.get('pending_approvals', 0):>14}건",
            f"지연 업무       {data.get('delayed_tasks', 0):>14}건\n",
        ]
        for s in data.get("sites", []):
            lines.append(
                f"  · {s.get('site_name')}: 지출 {s.get('expense_amount', 0):,} / 구매 {s.get('purchase_amount', 0):,}"
            )
        if data.get("ai_summary"):
            lines.append(f"\n[ AI 요약 ]\n{data['ai_summary']}")
        if data.get("risks"):
            lines.append(f"\n[ 리스크 ]\n{data['risks']}")
        self._set_text(self._exec_text, "\n".join(lines))

    def _exec_ai_summary(self) -> None:
        data = getattr(self, "_last_exec_summary", None)
        if not data:
            self._reload_exec_dashboard()
            data = getattr(self, "_last_exec_summary", {})
        ai = executive_summary_ai(data)
        data = {**data, **ai}
        self._reload_exec_dashboard()

    def _reload_closing(self) -> None:
        from core.workflow.store import _load_raw

        db = _load_raw(self._tenant())
        closings = db.get("monthly_closings") or []
        lines = ["월마감 현황\n", "=" * 40]
        for c in closings:
            lines.append(
                f"\n· {c.get('month')} / {c.get('site_id')}\n"
                f"  상태: {c.get('status')}\n"
                f"  체크: {c.get('checklist', {})}"
            )
        if not closings:
            lines.append("\n(마감 데이터 없음)")
        self._set_text(self._closing_text, "\n".join(lines))

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)


class WorkflowDocumentDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        doc: dict[str, Any],
        *,
        workflow_tenant_id: str | None = None,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._doc = doc
        self._workflow_tenant_id = workflow_tenant_id or ""
        self._on_changed = on_changed
        self.title(doc.get("title", "문서 상세"))
        self.geometry("760x600")
        self.minsize(560, 440)
        self.configure(bg=WF["page_bg"])

        st = doc.get("status", "")
        st_fg, st_bg = STATUS_UI.get(st, (COLORS["text"], WF["card"]))
        st_label = DOC_STATUS_LABELS.get(st, st)
        cj = doc.get("content_json") or {}
        self._gw_readonly = isinstance(cj, dict) and bool(cj.get("gw_readonly") or cj.get("imported_from"))

        outer = tk.Frame(self, bg=WF["page_bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        head = tk.Frame(outer, bg=COLORS["accent"], padx=20, pady=14)
        head.pack(fill=tk.X, side=tk.TOP)
        tk.Label(
            head,
            text=doc.get("title", "문서"),
            bg=COLORS["accent"],
            fg="#FFFFFF",
            font=(FONT, 14, "bold"),
            wraplength=680,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)
        meta = tk.Frame(head, bg=COLORS["accent"])
        meta.pack(anchor=tk.W, pady=(6, 0))
        tk.Label(
            meta,
            text=st_label,
            bg=st_bg,
            fg=st_fg,
            font=(FONT, 9, "bold"),
            padx=8,
            pady=2,
        ).pack(side=tk.LEFT, padx=(0, 8))
        gw_no = ""
        if isinstance(cj, dict):
            gw_no = str(cj.get("gw_doc_number") or cj.get("gw_doc_id") or "")
        meta_txt = doc.get("document_no", "")
        if gw_no:
            meta_txt = f"{meta_txt}  ·  GW {gw_no}"
        if int(doc.get("total_amount") or 0):
            meta_txt += f"  ·  {int(doc.get('total_amount') or 0):,}원"
        tk.Label(
            meta,
            text=meta_txt,
            bg=COLORS["accent"],
            fg="#E0F4FD",
            font=(FONT, 9),
        ).pack(side=tk.LEFT)
        if self._gw_readonly:
            tk.Label(
                meta,
                text="COSS 가져오기 (읽기 전용)",
                bg="#1E3A5F",
                fg="#FCD34D",
                font=(FONT, 8, "bold"),
                padx=6,
                pady=2,
            ).pack(side=tk.LEFT, padx=(8, 0))

        btn = tk.Frame(outer, bg=WF["page_bg"], padx=16, pady=10)
        btn.pack(fill=tk.X, side=tk.BOTTOM)
        sess = get_session()
        tid = self._workflow_tenant_id or session_tenant_id() or ""
        if (
            not self._gw_readonly
            and sess
            and tid
            and can_approve_document(sess, doc, tenant_id=tid)
        ):
            flat_button(btn, "승인", command=self._approve, bg=COLORS["success"], fg="#FFFFFF", padx=16, pady=8).pack(
                side=tk.LEFT, padx=(0, 6)
            )
            flat_button(btn, "반려", command=self._reject, bg="#DC2626", fg="#FFFFFF", padx=16, pady=8).pack(
                side=tk.LEFT, padx=(0, 6)
            )
            flat_button(
                btn,
                "보완요청",
                command=self._request_changes,
                bg=COLORS["warn"],
                fg="#FFFFFF",
                padx=12,
                pady=8,
            ).pack(side=tk.LEFT, padx=(0, 6))
        flat_button(btn, "닫기", command=self.destroy, bg=WF["tab_inactive"], fg=COLORS["text"], padx=14, pady=8).pack(
            side=tk.RIGHT
        )

        mid = tk.Frame(outer, bg=WF["page_bg"])
        mid.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(mid, bg=WF["card"], highlightthickness=0, bd=0)
        yscroll = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=yscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        body_card = tk.Frame(canvas, bg=WF["card"], highlightbackground=WF["card_border"], highlightthickness=1)
        win_id = canvas.create_window((0, 0), window=body_card, anchor=tk.NW)
        body = tk.Text(
            body_card,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg=WF["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=14,
            pady=12,
            height=20,
        )
        body.pack(fill=tk.BOTH, expand=True)
        lines = self._build_document_body_lines(doc)
        body.insert("1.0", "\n".join(lines))
        body.configure(state=tk.DISABLED)

        att_list = self._gw_attachment_paths(doc)
        if att_list:
            att_frame = tk.Frame(body_card, bg=WF["card"], padx=14)
            att_frame.pack(fill=tk.X, before=body, pady=(0, 10))
            tk.Label(
                att_frame,
                text="첨부파일",
                bg=WF["card"],
                fg=COLORS["text"],
                font=(FONT, 10, "bold"),
            ).pack(anchor=tk.W)
            for name, path in att_list:
                row = tk.Frame(att_frame, bg=WF["card"])
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text=name, bg=WF["card"], fg=COLORS["text"], font=(FONT, 9)).pack(
                    side=tk.LEFT, fill=tk.X, expand=True
                )
                flat_button(
                    row,
                    "열기",
                    command=lambda p=path: self._open_attachment(p),
                    bg=COLORS["accent"],
                    fg="#FFFFFF",
                    font=(FONT, 8),
                    padx=8,
                    pady=3,
                ).pack(side=tk.RIGHT)

        def _on_body_configure(_event: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            cw = canvas.winfo_width()
            if cw > 1:
                canvas.itemconfig(win_id, width=cw)

        body_card.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_body_configure)
        bind_local_wheel(canvas, canvas)
        bind_local_wheel(body_card, canvas)
        bind_local_wheel(body, canvas)

    @staticmethod
    def _html_to_display_text(html: str) -> str:
        import html as html_mod
        import re

        text = str(html or "")
        text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", text, flags=re.I)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</p>", "\n", text, flags=re.I)
        text = re.sub(r"</tr>", "\n", text, flags=re.I)
        text = re.sub(r"</td>", "\t", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html_mod.unescape(text)
        lines = [ln.strip() for ln in text.splitlines()]
        return "\n".join(ln for ln in lines if ln)

    @staticmethod
    def _build_document_body_lines(doc: dict[str, Any]) -> list[str]:
        cj = doc.get("content_json") or {}
        html_src = ""
        if isinstance(cj, dict):
            html_src = str(cj.get("content_html") or "").strip()
        if not html_src:
            html_src = str(doc.get("content_html") or "").strip()

        if html_src and len(html_src) > 40:
            main_text = WorkflowHubPanel._html_to_display_text(html_src)
        else:
            main_text = (
                str(doc.get("content") or "").strip()
                or (str(cj.get("content_text") or "").strip() if isinstance(cj, dict) else "")
            )
            if main_text and "<" in main_text and ">" in main_text:
                main_text = WorkflowHubPanel._html_to_display_text(main_text)

        lines: list[str] = []
        if main_text:
            lines.append(main_text)
            lines.append("")
        else:
            lines.append(doc.get("summary", ""))
            lines.append("")

        if isinstance(cj, dict):
            if cj.get("gw_drafter"):
                lines.append(f"— 기안자 —  {cj.get('gw_drafter')}")
            if cj.get("gw_form_name"):
                lines.append(f"— 양식 —  {cj.get('gw_form_name')}")
            if doc.get("requested_date"):
                lines.append(f"— 기안일 —  {doc.get('requested_date')}")
            lines.append("")

        lines.extend(
            [
                f"— 업무 기간 —  {doc.get('period_start', '')} ~ {doc.get('period_end', '')}",
                f"— 마감/완료 —  {doc.get('due_date', '')}",
                "",
                "— 양식 상세 —",
            ]
        )
        payload = doc.get("payload") or cj or {}
        if isinstance(payload, dict):
            skip = {
                "document_id",
                "document_type",
                "id",
                "title",
                "summary",
                "content",
                "content_text",
                "content_html",
                "attachments",
                "approval_workflow_json",
                "gw_readonly",
            }
            for k, v in payload.items():
                if k in skip or v in (None, ""):
                    continue
                if isinstance(v, (dict, list)):
                    continue
                lines.append(f"  · {k}: {v}")

        aw = cj.get("approval_workflow_json") if isinstance(cj, dict) else {}
        gw_steps = aw.get("steps") if isinstance(aw, dict) else None
        lines.extend(["", "— 결재라인 —"])
        if isinstance(gw_steps, list) and gw_steps:
            for i, s in enumerate(gw_steps, 1):
                if isinstance(s, dict):
                    lines.append(f"  {i}. {s.get('name', '')} ({s.get('role', '')})  {s.get('status', '')}")
        else:
            user_names = {}
            try:
                tid = session_tenant_id() or ""
                if tid:
                    user_names = {u.user_id: u.display_name for u in list_users_for_tenant(tid)}
            except Exception:
                pass
            from core.workflow.forms import APPROVER_ROLES

            for s in doc.get("approval_steps") or []:
                step_st = s.get("status", "")
                mark = "●" if step_st == "pending" else "✓" if step_st == "approved" else "·"
                role = APPROVER_ROLES.get(s.get("approver_role", ""), s.get("approver_role", ""))
                approver = user_names.get(s.get("approver_id", ""), s.get("approver_id", ""))
                lines.append(
                    f"  {mark} {s.get('step_order')}. {approver} ({role})  {step_st}  {s.get('comment', '')}"
                )
        return lines

    @staticmethod
    def _gw_attachment_paths(doc: dict[str, Any]) -> list[tuple[str, Path]]:
        root = app_data_dir() / "gw_import"
        out: list[tuple[str, Path]] = []
        cj = doc.get("content_json") or {}
        for att in (cj.get("attachments") if isinstance(cj, dict) else []) or []:
            if not isinstance(att, dict):
                continue
            name = str(att.get("name") or "file")
            rel = str(att.get("path") or "")
            if rel:
                p = root / rel.replace("/", os.sep)
                if p.is_file():
                    out.append((name, p))
                    continue
            gid = str(cj.get("gw_doc_id") or "")
            if gid:
                p = root / "attachments" / gid / name
                if p.is_file():
                    out.append((name, p))
        return out

    @staticmethod
    def _open_attachment(path: Path) -> None:
        if not path.is_file():
            messagebox.showwarning("안내", "파일을 찾을 수 없습니다.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except OSError as exc:
            messagebox.showerror("오류", str(exc))

    def _approve(self) -> None:
        comment = simpledialog.askstring("승인", "코멘트 (선택)", parent=self) or ""
        try:
            tid = self._workflow_tenant_id or session_tenant_id() or ""
            wf_svc.approve_document(tid, self._doc["id"], comment=comment, session=require_session())
            messagebox.showinfo("완료", "승인되었습니다.", parent=self)
            if self._on_changed:
                self._on_changed()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self)

    def _reject(self) -> None:
        comment = simpledialog.askstring("반려", "사유", parent=self) or ""
        try:
            tid = self._workflow_tenant_id or session_tenant_id() or ""
            wf_svc.reject_document(tid, self._doc["id"], comment=comment, session=require_session())
            messagebox.showinfo("완료", "반려되었습니다.", parent=self)
            if self._on_changed:
                self._on_changed()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self)

    def _request_changes(self) -> None:
        comment = simpledialog.askstring("보완요청", "요청 내용", parent=self) or ""
        try:
            wf_svc.request_changes(session_tenant_id() or "", self._doc["id"], comment=comment, session=require_session())
            messagebox.showinfo("완료", "보완요청되었습니다.", parent=self)
            if self._on_changed:
                self._on_changed()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self)
