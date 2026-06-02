"""
ui/platform_launcher.py - Bitween 플랫폼 홈 (런처)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from core.brand_display import company_name_line, launcher_tagline, product_name_line
from core.config import APP_CONFIG
from core.platforms import PLATFORMS, PlatformDef, PlatformOpenHandler
from core.i18n import tf, t
from core.session_service import is_logged_in
from ui.appearance_settings_panel import AppearanceSettingsPanel
from ui.theme import COLORS, FONT, FONT_BODY, get_current_theme_id
from ui.wheel_scroll import bind_local_wheel
from ui.workspace_hub import WorkspaceHub


class PlatformLauncherPanel(tk.Frame):
    """플랫폼 선택 홈."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_open: PlatformOpenHandler,
        host: tk.Misc | None = None,
        on_login: Callable[[], None] | None = None,
        on_logout: Callable[[], None] | None = None,
        on_theme_select: Callable[[str], None] | None = None,
        on_open_compliance_docs: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_open = on_open
        self._on_login = on_login
        self._on_logout = on_logout
        self._on_theme_select = on_theme_select
        self._on_open_compliance_docs = on_open_compliance_docs
        self.appearance_panel: AppearanceSettingsPanel | None = None
        self._photo_refs: list[tk.PhotoImage] = []
        self._tk_master = host if host is not None else parent

        root_col = tk.Frame(self, bg=COLORS["bg"])
        root_col.pack(fill=tk.BOTH, expand=True)
        root_col.grid_rowconfigure(0, weight=1)
        root_col.grid_columnconfigure(0, weight=1)

        scroll_host = tk.Frame(root_col, bg=COLORS["bg"])
        scroll_host.grid(row=0, column=0, sticky="nsew")
        scroll_host.grid_rowconfigure(0, weight=1)
        scroll_host.grid_columnconfigure(0, weight=1)

        self._scroll_canvas = tk.Canvas(
            scroll_host,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        yscroll = ttk.Scrollbar(scroll_host, orient=tk.VERTICAL, command=self._scroll_canvas.yview)
        self._yscroll = yscroll
        self._scroll_canvas.configure(yscrollcommand=self._on_yscroll)
        self._scroll_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self._scroll_body = tk.Frame(self._scroll_canvas, bg=COLORS["bg"])
        self._scroll_win = self._scroll_canvas.create_window((0, 0), window=self._scroll_body, anchor="nw")
        self._appearance_visible = False

        def _on_configure(_event: tk.Event | None = None) -> None:
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))
            cw = self._scroll_canvas.winfo_width()
            if cw > 1:
                self._scroll_canvas.itemconfigure(self._scroll_win, width=cw)
            self._update_appearance_visibility()

        self._scroll_body.bind("<Configure>", _on_configure)
        self._scroll_canvas.bind("<Configure>", _on_configure)

        # 드래그로 스크롤 (클릭 후 끌기)
        # 입력 위젯(엔트리/버튼)에서는 드래그 스크롤이 개입하지 않도록,
        # 기본은 캔버스에만 바인딩하고, "배경 프레임"에 한해 선택적으로 추가 바인딩합니다.
        def _drag_start(event) -> None:
            self._scroll_canvas.scan_mark(event.x, event.y)

        def _drag_move(event) -> None:
            self._scroll_canvas.scan_dragto(event.x, event.y, gain=1)

        self._drag_start = _drag_start
        self._drag_move = _drag_move
        self._scroll_canvas.bind("<ButtonPress-1>", self._drag_start, add="+")
        self._scroll_canvas.bind("<B1-Motion>", self._drag_move, add="+")

        # 휠 스크롤은 바디 어디서나 캔버스로 전달
        bind_local_wheel(self._scroll_body, self._scroll_canvas)
        bind_local_wheel(self._scroll_canvas, self._scroll_canvas)

        outer = self._scroll_body
        outer.grid_columnconfigure(0, weight=1)

        self._build_hero(outer)
        if is_logged_in():
            self._build_gw_status_widgets(outer)
            self._build_workspace_or_login(outer)
            self._build_bulletin_section(outer)
            self._build_section_header(outer)
            self._build_card_area(outer)
            self._build_appearance_section(outer)

    def _on_yscroll(self, first: str, last: str) -> None:
        self._yscroll.set(first, last)
        self._update_appearance_visibility(float(last))

    def _update_appearance_visibility(self, bottom_frac: float | None = None) -> None:
        if not hasattr(self, "_appearance_wrap"):
            return
        if bottom_frac is None:
            try:
                bottom_frac = float(self._scroll_canvas.yview()[1])
            except (tk.TclError, IndexError, ValueError):
                return
        at_bottom = bottom_frac >= 0.985
        if at_bottom and not self._appearance_visible:
            self._appearance_anchor.grid()
            self._appearance_visible = True
        elif not at_bottom and self._appearance_visible:
            self._appearance_anchor.grid_remove()
            self._appearance_visible = False

    def _bind_drag_scroll_bg(self, widget: tk.Misc) -> None:
        """배경 프레임에만 드래그-스크롤을 허용합니다."""
        widget.bind("<ButtonPress-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")

    def _hero_colors(self) -> dict[str, str]:
        return {
            "top": COLORS["hero_bg"],
            "bottom": COLORS["hero_bg_bottom"],
            "fg": COLORS["hero_fg"],
            "muted": COLORS["hero_muted"],
            "accent": COLORS["hero_accent"],
            "accent_soft": COLORS["hero_accent_soft"],
        }

    def _build_hero(self, outer: tk.Frame) -> None:
        """풀폭 히어로 — 테마 accent 연동 + 로고."""
        hero = self._hero_colors()
        banner = tk.Frame(outer, bg=hero["top"], highlightthickness=0)
        banner.grid(row=0, column=0, sticky="ew")

        grad_strip = tk.Frame(banner, bg=hero["bottom"], height=6, highlightthickness=0)
        grad_strip.pack(fill=tk.X, side=tk.BOTTOM)

        inner = tk.Frame(banner, bg=hero["top"])
        inner.pack(fill=tk.X, padx=36, pady=32)

        top_row = tk.Frame(inner, bg=hero["top"])
        top_row.pack(fill=tk.X)

        left = tk.Frame(top_row, bg=hero["top"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            left,
            text=product_name_line(),
            bg=hero["top"],
            fg=hero["fg"],
            font=(FONT, 36, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)

        tk.Label(
            left,
            text=launcher_tagline(),
            bg=hero["top"],
            fg=hero["accent_soft"],
            font=(FONT, 11, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(6, 0))

        tk.Label(
            left,
            text="사용할 업무 플랫폼을 선택하세요. 메뉴는 왼쪽 사이드바에서 이동할 수 있습니다.",
            bg=hero["top"],
            fg=hero["muted"],
            font=(FONT, 10),
            anchor=tk.W,
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 0))

        if is_logged_in():
            right = tk.Frame(top_row, bg=hero["top"])
            right.pack(side=tk.RIGHT, padx=(24, 0))
            tk.Label(
                right,
                text=company_name_line(),
                bg=hero["top"],
                fg=hero["fg"],
                font=(FONT, 13, "bold"),
                anchor=tk.E,
            ).pack(anchor=tk.E)

        tk.Frame(inner, bg=hero["accent"], height=2).pack(fill=tk.X, pady=(24, 0))

    def _build_appearance_section(self, parent: tk.Frame) -> None:
        """스크롤 맨 아래 — 테마·언어 컴팩트 바 (하단 도달 시에만 표시)."""
        self._appearance_anchor = tk.Frame(parent, bg=COLORS["bg"])
        self._appearance_anchor.grid(row=6, column=0, sticky="ew")
        self._appearance_anchor.grid_remove()
        self._bind_drag_scroll_bg(self._appearance_anchor)

        self._appearance_wrap = tk.Frame(self._appearance_anchor, bg=COLORS["bg"])
        self._appearance_wrap.pack(fill=tk.X, padx=16, pady=(1, 2))
        tk.Frame(self._appearance_wrap, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 2))

        self.appearance_panel = AppearanceSettingsPanel(
            self._appearance_wrap,
            on_theme_select=self._on_theme_select,
            inline=True,
        )
        self.appearance_panel.pack(fill=tk.X)
        self.appearance_panel.set_theme_selection(get_current_theme_id())

        self._appearance_visible = False
        self.after_idle(self._update_appearance_visibility)

    def _build_gw_status_widgets(self, outer: tk.Frame) -> None:
        """COSS GW 홈형 — 결재·공람·메일 건수 바로가기."""
        wrap = tk.Frame(outer, bg=COLORS["bg"])
        self._gw_widgets_wrap = wrap
        wrap.grid(row=1, column=0, sticky="ew", padx=32, pady=(4, 0))
        wrap.grid_columnconfigure(0, weight=1)

        counts = self._fetch_gw_widget_counts()
        items = (
            ("결재 대기", counts.get("to_approve", 0), "#2563EB", "workflow"),
            ("진행", counts.get("in_progress", 0), "#0284C7", "workflow"),
            ("공람", counts.get("circulate", 0), "#7C3AED", "workflow"),
            ("안읽은 메일", counts.get("unread_mail", 0), "#0D9488", "mail"),
        )
        for col in range(len(items)):
            wrap.grid_columnconfigure(col, weight=1, uniform="gw")

        for col, (title, n, color, target) in enumerate(items):
            card = tk.Frame(wrap, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
            card.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)
            inner = tk.Frame(card, bg=COLORS["card"], padx=14, pady=12, cursor="hand2")
            inner.pack(fill=tk.BOTH, expand=True)
            tk.Label(inner, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(anchor=tk.W)
            tk.Label(inner, text=str(n), bg=COLORS["card"], fg=color, font=(FONT, 22, "bold")).pack(anchor=tk.W)
            tk.Label(inner, text="건", bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(anchor=tk.W)
            cmd = (
                (lambda: self._on_open("workflow"))
                if target == "workflow"
                else (lambda: self._open_mail_from_launcher())
            )
            for w in (card, inner, *inner.winfo_children()):
                w.bind("<Button-1>", lambda _e, c=cmd: c())

    def _fetch_gw_widget_counts(self) -> dict[str, int]:
        out: dict[str, int] = {"to_approve": 0, "in_progress": 0, "circulate": 0, "unread_mail": 0}
        try:
            from core.group_store import get_workflow_tenant_id
            from core.session_service import get_session, session_tenant_id
            from core.workflow import service as wf_svc
            from services import workspace_store as ws

            tid = session_tenant_id()
            sess = get_session()
            if tid and sess:
                wf_tid = get_workflow_tenant_id(tid)
                c = wf_svc.inbox_counts(wf_tid, session=sess)
                out["to_approve"] = c.get("to_approve", 0)
                out["in_progress"] = c.get("in_progress", 0)
                out["circulate"] = c.get("circulate", 0)
            out["unread_mail"] = ws.unread_mail_count(sess)
        except Exception:
            pass
        return out

    def _open_mail_from_launcher(self) -> None:
        from ui.workspace_dialogs import MailDialog

        root = self.winfo_toplevel()
        MailDialog(root, on_changed=self._refresh_workspace)

    def _build_workspace_or_login(self, outer: tk.Frame) -> None:
        wrap = tk.Frame(outer, bg=COLORS["bg"])
        wrap.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        wrap.grid_columnconfigure(0, weight=1)

        if not is_logged_in():
            return

        self.workspace_hub = WorkspaceHub(
            wrap,
            on_login_request=self._on_login,
            on_logout_request=self._on_logout,
            on_session_changed=self._refresh_workspace,
            on_open_compliance_docs=self._on_open_compliance_docs,
        )
        self.workspace_hub.pack(fill=tk.X, padx=32)

    def _refresh_workspace(self) -> None:
        if hasattr(self, "workspace_hub"):
            self.workspace_hub.refresh()

    def _after_inline_login(self) -> None:
        # (레거시) 인라인 로그인 제거됨. 호출부 호환을 위해 남겨둡니다.
        if self._on_login:
            self._on_login()

    def refresh_session_ui(self) -> None:
        """로그인·로그아웃·고객사 전환 후 호출."""
        self._refresh_workspace()
        if hasattr(self, "bulletin_section"):
            self.bulletin_section.refresh()

    def _build_bulletin_section(self, outer: tk.Frame) -> None:
        """그룹 공유게시판 — 플랫폼 카드 위."""
        from ui.bulletin_panel import BulletinSection

        wrap = tk.Frame(outer, bg=COLORS["bg"])
        wrap.grid(row=3, column=0, sticky="ew", padx=32, pady=(12, 0))
        wrap.grid_columnconfigure(0, weight=1)
        self.bulletin_section = BulletinSection(wrap, on_drag_bind=self._bind_drag_scroll_bg)
        self.bulletin_section.pack(fill=tk.X)

    def _build_section_header(self, outer: tk.Frame) -> None:
        row = tk.Frame(outer, bg=COLORS["bg"])
        row.grid(row=4, column=0, sticky="ew", padx=36, pady=(20, 8))
        tk.Label(
            row,
            text=t("launcher.platform_section.title", default="업무 플랫폼"),
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
            anchor=tk.W,
        ).pack(side=tk.LEFT)
        tk.Label(
            row,
            text=t("launcher.platform_section.hint", default="카드를 클릭하거나 「플랫폼 열기」로 진입"),
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.E,
        ).pack(side=tk.RIGHT)

    def _build_card_area(self, outer: tk.Frame) -> None:
        grid_wrap = tk.Frame(outer, bg=COLORS["bg"])
        grid_wrap.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 20))
        grid_wrap.grid_columnconfigure(0, weight=1)

        grid = tk.Frame(grid_wrap, bg=COLORS["bg"])
        grid.grid(row=0, column=0, sticky="ew")

        for col in range(2):
            grid.grid_columnconfigure(col, weight=1, uniform="plat")

        for idx, plat in enumerate(PLATFORMS):
            r, c = divmod(idx, 2)
            self._build_card(grid, plat).grid(row=r, column=c, sticky="nsew", padx=8, pady=8)

    def _build_card(self, parent: tk.Misc, plat: PlatformDef) -> tk.Frame:
        from core.config import APP_CONFIG

        enabled = plat.enabled and (
            not APP_CONFIG.require_login or is_logged_in()
        )

        shell = tk.Frame(parent, bg=COLORS["bg"])
        shadow = tk.Frame(shell, bg=COLORS["card_shadow"])
        shadow.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(
            shadow,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"] if not enabled else plat.accent,
            highlightthickness=1 if not enabled else 0,
            cursor="hand2" if enabled else "arrow",
        )
        card.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 3))

        accent = tk.Frame(card, bg=plat.accent if enabled else "#CBD5E1", height=4)
        accent.pack(fill=tk.X)

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill=tk.BOTH, expand=True, padx=26, pady=22)

        head = tk.Frame(inner, bg=COLORS["card"])
        head.pack(fill=tk.X)

        icon_bg = plat.accent if enabled else "#94A3B8"
        icon_wrap = tk.Frame(head, bg=icon_bg, width=52, height=52)
        icon_wrap.pack(side=tk.LEFT)
        icon_wrap.pack_propagate(False)
        tk.Label(
            icon_wrap,
            text=plat.icon_glyph,
            bg=icon_bg,
            fg="#FFFFFF",
            font=(FONT, 20, "bold"),
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        txt = tk.Frame(head, bg=COLORS["card"])
        txt.pack(side=tk.LEFT, padx=(16, 0), fill=tk.X, expand=True)
        tk.Label(
            txt,
            text=tf(plat.id, "title", plat.title),
            bg=COLORS["card"],
            fg=COLORS["text"] if enabled else COLORS["muted"],
            font=(FONT, 17, "bold"),
            anchor=tk.W,
        ).pack(anchor=tk.W)
        tk.Label(
            txt,
            text=tf(plat.id, "subtitle", plat.subtitle),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(3, 0))

        badge_bg = "#DCFCE7" if enabled else "#FEF3C7"
        badge_fg = "#166534" if enabled else "#92400E"
        tk.Label(
            head,
            text=tf(plat.id, "status", plat.status_label),
            bg=badge_bg,
            fg=badge_fg,
            font=(FONT, 8, "bold"),
            padx=10,
            pady=5,
        ).pack(side=tk.RIGHT)

        desc = tf(plat.id, "description", plat.description)
        if plat.enabled and APP_CONFIG.require_login and not is_logged_in():
            desc = tf(plat.id, "login_required", "로그인 후 이용할 수 있습니다.")
        tk.Label(
            inner,
            text=desc,
            bg=COLORS["card"],
            fg=COLORS["text"] if enabled else COLORS["muted"],
            font=FONT_BODY,
            wraplength=400,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(18, 14))

        chips = tk.Frame(inner, bg=COLORS["card"])
        chips.pack(anchor=tk.W, fill=tk.X)
        for feat in plat.features:
            tk.Label(
                chips,
                text=feat,
                bg=COLORS["chip_bg"],
                fg=COLORS["nav_text"],
                font=(FONT, 8),
                padx=10,
                pady=5,
            ).pack(side=tk.LEFT, padx=(0, 6), pady=(0, 4))

        needs_login = (
            plat.enabled
            and APP_CONFIG.require_login
            and not is_logged_in()
        )

        if enabled:
            tk.Button(
                inner,
                text=tf(plat.id, "open", "플랫폼 열기  →"),
                bg=plat.accent,
                fg="#FFFFFF",
                activebackground=COLORS["accent_hover"],
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                font=(FONT, 11, "bold"),
                padx=18,
                pady=11,
                cursor="hand2",
                command=lambda pid=plat.id: self._on_open(pid),
            ).pack(anchor=tk.W, pady=(16, 0))

            def _bind_open(widget: tk.Misc, pid: str = plat.id) -> None:
                widget.bind("<Button-1>", lambda _e, p=pid: self._on_open(p))

            def _hover_on(_e: tk.Event) -> None:
                card.configure(highlightbackground=plat.accent, highlightthickness=2)
                shadow.configure(bg=plat.accent)

            def _hover_off(_e: tk.Event) -> None:
                card.configure(highlightthickness=0)
                shadow.configure(bg=COLORS["card_shadow"])

            for w in (shell, shadow, card, inner, head, txt, chips):
                _bind_open(w)
                w.bind("<Enter>", _hover_on)
                w.bind("<Leave>", _hover_off)
        elif needs_login:
            tk.Label(
                inner,
                text="로그인 필요",
                bg=COLORS["card"],
                fg="#B45309",
                font=(FONT, 10, "bold"),
            ).pack(anchor=tk.W, pady=(16, 0))
        else:
            tk.Label(
                inner,
                text="준비 중",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 10, "italic"),
            ).pack(anchor=tk.W, pady=(16, 0))

        return shell

    def keep_photos_on(self, host: Any) -> None:
        if not hasattr(host, "_brand_photo_refs"):
            host._brand_photo_refs = []
        host._brand_photo_refs.extend(self._photo_refs)
