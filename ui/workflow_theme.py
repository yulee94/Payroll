"""
ui/workflow_theme.py - 업무·전자결재 화면 전용 색·스타일
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ui.theme import COLORS, FONT, FONT_BODY

# 페이지 배경·헤더·카드 (apply_theme 시 sync_workflow_theme()로 갱신)
WF: dict[str, str] = {}


def sync_workflow_theme() -> None:
    """전역 COLORS 변경 후 WF 팔레트를 맞춥니다."""
    WF.clear()
    WF.update(
        {
            "page_bg": COLORS.get("bg", "#F1F5F9"),
            "header_bg": COLORS["accent"],
            "header_fg": "#FFFFFF",
            "header_sub": COLORS.get("accent_light", "#E0F4FD"),
            "card": COLORS["card"],
            "card_border": COLORS["border"],
            "tab_bar_bg": COLORS["card"],
            "tab_inactive": COLORS.get("nav_hover", "#F8FAFC"),
            "tab_inactive_fg": COLORS["muted"],
            "tab_active": COLORS["accent"],
            "tab_active_fg": "#FFFFFF",
            "sidebar_bg": COLORS.get("nav_hover", "#F8FAFC"),
            "sidebar_active": COLORS.get("accent_light", "#E0F4FD"),
            "sidebar_active_border": COLORS["nav_accent"],
            "row_alt": COLORS.get("nav_hover", "#F8FAFC"),
            "row_hover": COLORS.get("accent_light", "#E0F4FD"),
        }
    )


sync_workflow_theme()

# 결재함별 색 (한눈에 구분)
INBOX_UI: dict[str, dict[str, str]] = {
    "to_approve": {"label": "결재할 문서", "color": "#2563EB", "light": "#DBEAFE", "icon": "●"},
    "my_draft": {"label": "기안함", "color": "#64748B", "light": "#F1F5F9", "icon": "✎"},
    "circulate": {"label": "공람", "color": "#7C3AED", "light": "#EDE9FE", "icon": "◎"},
    "in_progress": {"label": "진행함", "color": "#0284C7", "light": "#E0F2FE", "icon": "◐"},
    "completed": {"label": "완료함", "color": "#059669", "light": "#D1FAE5", "icon": "✓"},
    "rejected": {"label": "반려함", "color": "#DC2626", "light": "#FEE2E2", "icon": "✗"},
    "reference": {"label": "참조함", "color": "#6366F1", "light": "#EEF2FF", "icon": "◇"},
    "all": {"label": "전체", "color": "#475569", "light": "#E2E8F0", "icon": "≡"},
}

# 문서 상태 → 표시 색
STATUS_UI: dict[str, tuple[str, str]] = {
    "draft": ("#64748B", "#F1F5F9"),
    "submitted": ("#2563EB", "#DBEAFE"),
    "in_review": ("#D97706", "#FEF3C7"),
    "approved": ("#059669", "#D1FAE5"),
    "rejected": ("#DC2626", "#FEE2E2"),
    "requested_changes": ("#7C3AED", "#EDE9FE"),
    "cancelled": ("#94A3B8", "#F1F5F9"),
    "completed": ("#059669", "#D1FAE5"),
    "closed": ("#1F3864", "#E0F4FD"),
}

# 양식 템플릿 카드 색
TEMPLATE_UI: dict[str, tuple[str, str, str]] = {
    "GENERAL_DRAFT": ("일반 기안", "📋", "#1F3864"),
    "ATTENDANCE_REQUEST": ("근태 신청", "🗓", "#0284C7"),
    "EXPENSE_REPORT": ("지출 결의", "💳", "#059669"),
    "PURCHASE_REQUEST": ("구매 요청", "📦", "#D97706"),
    "CLOSING_REPORT": ("마감 보고", "📊", "#7C3AED"),
}

TAB_ITEMS: tuple[tuple[str, str], ...] = (
    ("home", "홈"),
    ("inbox", "결재함"),
    ("new", "양식함"),
    ("tasks", "실행업무"),
    ("reports", "보고"),
    ("closing", "월마감"),
)


def setup_workflow_ttk_style(root: tk.Misc) -> None:
    if getattr(root, "_workflow_ttk_ready", False):
        return
    root._workflow_ttk_ready = True  # type: ignore[attr-defined]
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Workflow.Treeview",
        background=WF["card"],
        fieldbackground=WF["card"],
        foreground=COLORS["text"],
        rowheight=34,
        font=FONT_BODY,
        borderwidth=0,
    )
    style.configure(
        "Workflow.Treeview.Heading",
        background=COLORS["table_head"],
        foreground=COLORS["table_head_fg"],
        font=(FONT, 10, "bold"),
        padding=(8, 10),
    )
    style.map(
        "Workflow.Treeview.Heading",
        background=[("active", COLORS["accent_hover"])],
    )
    style.configure("Workflow.TNotebook", background=WF["page_bg"], borderwidth=0)
    style.configure("Workflow.TNotebook.Tab", padding=(14, 8), font=(FONT, 10))


def flat_button(
    parent: tk.Misc,
    text: str,
    *,
    command: Callable[[], None] | None = None,
    bg: str,
    fg: str = "#FFFFFF",
    font: tuple = (FONT, 10, "bold"),
    padx: int = 14,
    pady: int = 8,
    active_bg: str | None = None,
) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=active_bg or bg,
        activeforeground=fg,
        relief=tk.FLAT,
        bd=0,
        cursor="hand2",
        font=font,
        padx=padx,
        pady=pady,
    )
