"""
ui/workspace_hub.py - 플랫폼 홈 업무 도구 (로그인 후)
"""

from __future__ import annotations

import calendar as cal_mod
import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog
from typing import Callable

from core.session_service import get_session, is_logged_in
from core.tenant_store import get_active_tenant
from services import workspace_store as ws
from ui.login_dialog import LoginDialog
from ui.theme import COLORS, FONT, FONT_BODY
from services.ai_assistant import load_chat_history
from services.openai_settings_store import has_api_key
from ui.ai_assistant_dialog import AiAssistantDialog
from ui.workspace_dialogs import CalendarDialog, MailDialog, MessengerDialog

OnSessionAction = Callable[[], None]


class WorkspaceHub(tk.Frame):
    """캘린더 · 할 일 · 메신저 · 메일 미리보기."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_session_changed: OnSessionAction | None = None,
        on_login_request: OnSessionAction | None = None,
        on_logout_request: OnSessionAction | None = None,
        on_open_compliance_docs: OnSessionAction | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_session_changed = on_session_changed
        self._on_login_request = on_login_request
        self._on_logout_request = on_logout_request
        self._on_open_compliance_docs = on_open_compliance_docs
        self._today = date.today()

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=4, pady=(0, 10))
        tk.Label(
            header,
            text="오늘의 업무",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
        ).pack(side=tk.LEFT)
        self._session_chip = tk.Label(
            header,
            text="",
            bg=COLORS["nav_badge_bg"],
            fg=COLORS["nav_badge_fg"],
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
        )
        self._session_chip.pack(side=tk.LEFT, padx=(12, 0))
        self._auth_btn = tk.Button(
            header,
            text="로그인",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            font=(FONT, 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_auth_click,
        )
        self._auth_btn.pack(side=tk.RIGHT)

        self._compliance_link = tk.Button(
            header,
            text="📋  법정·규정 문서함",
            relief=tk.FLAT,
            bg=COLORS["card"],
            fg="#0D9488",
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._open_compliance_docs,
        )
        self._compliance_link.pack(side=tk.RIGHT, padx=(0, 8))

        self._content = tk.Frame(self, bg=COLORS["bg"])
        self._content.pack(fill=tk.BOTH, expand=True)

        self._locked = tk.Frame(self._content, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        self._locked.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        inner_lock = tk.Frame(self._locked, bg=COLORS["card"], padx=40, pady=36)
        inner_lock.pack(expand=True)
        tk.Label(
            inner_lock,
            text="🔒",
            bg=COLORS["card"],
            font=(FONT, 28),
        ).pack()
        tk.Label(
            inner_lock,
            text="로그인 후 이용 가능합니다",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        ).pack(pady=(8, 6))
        tk.Label(
            inner_lock,
            text="메신저·메일·할 일·캘린더·AI는 본인 계정에서만 사용됩니다.\n"
            "다른 사용자 계정의 데이터는 볼 수 없습니다.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            justify=tk.CENTER,
        ).pack()
        tk.Button(
            inner_lock,
            text="로그인 / 계정 만들기",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._open_login,
        ).pack(pady=(16, 0))

        self._grid = tk.Frame(self._content, bg=COLORS["bg"])
        for c in range(3):
            self._grid.grid_columnconfigure(c, weight=1, uniform="ws")
        self._grid.grid_rowconfigure(0, weight=1)
        self._grid.grid_rowconfigure(1, weight=1)

        self._card_calendar = self._make_card(
            self._grid, "📅  캘린더", 0, 0, self._open_calendar
        )
        self._card_todo = self._make_card(self._grid, "✓  Daily To-Do", 0, 1, None)
        self._card_ai = self._make_card(
            self._grid, "✨  Personal AI", 0, 2, self._open_ai, rowspan=2
        )
        self._card_msg = self._make_card(self._grid, "💬  사내 메신저", 1, 0, self._open_messenger)
        self._card_mail = self._make_card(self._grid, "✉  내 메일함", 1, 1, self._open_mail)

        self._build_todo_body(self._card_todo)
        self._build_calendar_mini(self._card_calendar)
        self._build_ai_preview(self._card_ai)
        self._build_msg_preview(self._card_msg)
        self._build_mail_preview(self._card_mail)

        self.refresh()

    def _make_card(
        self,
        parent: tk.Misc,
        title: str,
        row: int,
        col: int,
        open_cmd: Callable[[], None] | None,
        rowspan: int = 1,
    ) -> tk.Frame:
        shell = tk.Frame(parent, bg="#E2E8F0", padx=1, pady=1)
        shell.grid(row=row, column=col, rowspan=rowspan, sticky="nsew", padx=6, pady=6)
        card = tk.Frame(shell, bg=COLORS["card"], padx=14, pady=12)
        card.pack(fill=tk.BOTH, expand=True)
        head = tk.Frame(card, bg=COLORS["card"])
        head.pack(fill=tk.X)
        tk.Label(head, text=title, bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 11, "bold")).pack(
            side=tk.LEFT
        )
        if open_cmd:
            tk.Button(
                head,
                text="열기",
                relief=tk.FLAT,
                bg="#F1F5F9",
                fg=COLORS["nav_text"],
                font=(FONT, 8),
                padx=8,
                pady=2,
                cursor="hand2",
                command=open_cmd,
            ).pack(side=tk.RIGHT)
        body = tk.Frame(card, bg=COLORS["card"])
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        body._is_body = True  # type: ignore[attr-defined]
        return body

    def _card_body(self, card_frame: tk.Frame) -> tk.Frame:
        for c in card_frame.winfo_children():
            if getattr(c, "_is_body", False):
                return c
        return card_frame

    def _build_calendar_mini(self, card: tk.Frame) -> None:
        body = self._card_body(card)
        self._cal_month_lbl = tk.Label(body, text="", bg=COLORS["card"], font=(FONT, 10, "bold"))
        self._cal_month_lbl.pack(anchor=tk.W)
        self._cal_grid = tk.Frame(body, bg=COLORS["card"])
        self._cal_grid.pack(anchor=tk.W, pady=4)
        self._cal_events_lbl = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=220,
            justify=tk.LEFT,
        )
        self._cal_events_lbl.pack(anchor=tk.W)

    def _build_todo_body(self, card: tk.Frame) -> None:
        body = self._card_body(card)
        add_row = tk.Frame(body, bg=COLORS["card"])
        add_row.pack(fill=tk.X)
        self._todo_entry = tk.Entry(add_row, font=FONT_BODY)
        self._todo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._todo_entry.bind("<Return>", lambda _e: self._add_todo())
        tk.Button(
            add_row,
            text="+",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            width=3,
            command=self._add_todo,
        ).pack(side=tk.LEFT, padx=(4, 0))
        self._todo_list = tk.Frame(body, bg=COLORS["card"])
        self._todo_list.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_msg_preview(self, card: tk.Frame) -> None:
        body = self._card_body(card)
        self._msg_preview = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=FONT_BODY,
            anchor=tk.NW,
            justify=tk.LEFT,
            wraplength=240,
        )
        self._msg_preview.pack(anchor=tk.NW, fill=tk.BOTH, expand=True)

    def _build_ai_preview(self, card: tk.Frame) -> None:
        body = self._card_body(card)
        self._ai_status = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["accent"],
            font=(FONT, 9, "bold"),
            anchor=tk.NW,
        )
        self._ai_status.pack(anchor=tk.NW)
        self._ai_preview = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            anchor=tk.NW,
            justify=tk.LEFT,
            wraplength=220,
        )
        self._ai_preview.pack(anchor=tk.NW, pady=(6, 0), fill=tk.BOTH, expand=True)
        tk.Button(
            body,
            text="질문하기 →",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            font=(FONT, 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._open_ai,
        ).pack(anchor=tk.W, pady=(8, 0))

    def _build_mail_preview(self, card: tk.Frame) -> None:
        body = self._card_body(card)
        self._mail_badge = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["accent"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        )
        self._mail_badge.pack(anchor=tk.W)
        self._mail_preview = tk.Label(
            body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            anchor=tk.NW,
            justify=tk.LEFT,
            wraplength=240,
        )
        self._mail_preview.pack(anchor=tk.NW, pady=(4, 0))

    def refresh(self) -> None:
        logged = is_logged_in()
        sess = get_session()
        tenant = get_active_tenant()

        if logged and sess:
            self._session_chip.configure(
                text=f"  {sess.display_name} · {tenant.display_name}  ",
            )
            self._auth_btn.configure(text="로그아웃", bg="#64748B")
            self._locked.pack_forget()
            self._grid.pack(fill=tk.BOTH, expand=True)
            try:
                ws.seed_demo_mail_if_empty(sess)
                self._refresh_widgets(sess)
            except PermissionError:
                pass
        else:
            self._session_chip.configure(text="  로그인 필요  ")
            self._auth_btn.configure(text="로그인", bg=COLORS["accent"])
            self._grid.pack_forget()
            self._locked.pack(fill=tk.BOTH, expand=True)

    def _refresh_widgets(self, sess) -> None:
        y, m = self._today.year, self._today.month
        self._cal_month_lbl.configure(text=f"{y}년 {m}월")
        for w in self._cal_grid.winfo_children():
            w.destroy()
        events = ws.list_calendar_events(y, m, sess)
        by_day: dict[int, int] = {}
        for ev in events:
            try:
                d = int(str(ev.get("date", ""))[8:10])
                by_day[d] = by_day.get(d, 0) + 1
            except ValueError:
                pass
        for i, wd in enumerate("월화수목금토일"):
            tk.Label(self._cal_grid, text=wd, width=3, font=(FONT, 7), bg=COLORS["card"], fg=COLORS["muted"]).grid(
                row=0, column=i
            )
        weeks = cal_mod.Calendar(firstweekday=0).monthdayscalendar(y, m)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if not day:
                    tk.Label(self._cal_grid, text="", width=3, bg=COLORS["card"]).grid(row=r, column=c)
                    continue
                is_today = day == self._today.day
                bg = COLORS["accent"] if is_today else COLORS["card"]
                fg = "#FFFFFF" if is_today else (COLORS["accent"] if by_day.get(day) else COLORS["text"])
                tk.Label(
                    self._cal_grid,
                    text=str(day),
                    width=3,
                    bg=bg,
                    fg=fg,
                    font=(FONT, 8, "bold" if is_today else "normal"),
                ).grid(row=r, column=c)
        upcoming = [e for e in events if str(e.get("date", "")) >= self._today.isoformat()][:3]
        if upcoming:
            lines = [f"· {e.get('date', '')} {e.get('title', '')}" for e in upcoming]
            self._cal_events_lbl.configure(text="\n".join(lines))
        else:
            self._cal_events_lbl.configure(text="이번 달 등록된 일정 없음")

        for w in self._todo_list.winfo_children():
            w.destroy()
        todos = [t for t in ws.list_todos(sess) if not t.get("done")][:6]
        if not todos:
            tk.Label(
                self._todo_list,
                text="오늘 할 일을 추가해 보세요.",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(anchor=tk.W)
        for t in todos:
            row = tk.Frame(self._todo_list, bg=COLORS["card"])
            row.pack(fill=tk.X, pady=2)
            tid = t.get("id", "")
            tk.Button(
                row,
                text="☐",
                relief=tk.FLAT,
                bg=COLORS["card"],
                fg=COLORS["accent"],
                command=lambda i=tid: self._toggle_todo(i),
            ).pack(side=tk.LEFT)
            due = f" ({t.get('due_date')})" if t.get("due_date") else ""
            tk.Label(
                row,
                text=f"{t.get('title', '')}{due}",
                bg=COLORS["card"],
                font=FONT_BODY,
                anchor=tk.W,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        threads = ws.list_message_threads(sess)[:3]
        if threads:
            lines = []
            for t in threads:
                u = f" ({t['unread']})" if t.get("unread") else ""
                lines.append(f"· {t.get('other_label', '')}{u}: {t.get('last_text', '')[:40]}")
            self._msg_preview.configure(text="\n".join(lines))
        else:
            self._msg_preview.configure(text="동료와 대화를 시작해 보세요.\n(같은 고객사 계정만 선택 가능)")

        unread = ws.unread_mail_count(sess)
        self._mail_badge.configure(text=f"읽지 않음 {unread}건")
        mails = ws.list_mail(sess, limit=2)
        if mails:
            self._mail_preview.configure(
                text="\n".join(f"· {m.get('subject', '')}" for m in mails),
            )
        else:
            self._mail_preview.configure(text="개인 메일함이 비어 있습니다.")

        api_ok = has_api_key(sess)
        self._ai_status.configure(
            text="ChatGPT 연동됨" if api_ok else "로컬 급여 조회 (API 키 미등록)",
        )
        hist = load_chat_history(sess, limit=4)
        last = next((m for m in reversed(hist) if m.get("role") == "assistant"), None)
        if last:
            snippet = str(last.get("content") or "")[:160]
            if len(str(last.get("content") or "")) > 160:
                snippet += "…"
            self._ai_preview.configure(text=snippet)
        else:
            self._ai_preview.configure(
                text='예: "5월 이정옥 급여" · "오늘 할 일" · "메일 초안"\n급여·명부·일정·메일·사용법',
            )

    def _add_todo(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        title = self._todo_entry.get().strip()
        if not title:
            return
        due = simpledialog.askstring(
            "마감일",
            "마감일 (YYYY-MM-DD, 비우면 없음)",
            parent=self.winfo_toplevel(),
        )
        try:
            ws.add_todo(title, due_date=due or "")
            self._todo_entry.delete(0, tk.END)
            self.refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("할 일", str(exc), parent=self)

    def _toggle_todo(self, todo_id: str) -> None:
        try:
            ws.toggle_todo(todo_id)
            self.refresh()
        except PermissionError:
            pass

    def _open_compliance_docs(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        if self._on_open_compliance_docs:
            self._on_open_compliance_docs()

    def _on_auth_click(self) -> None:
        if is_logged_in():
            if self._on_logout_request:
                self._on_logout_request()
        else:
            self._open_login()

    def _open_login(self) -> None:
        # 앱에서 별도 로그인 페이지를 제공하면 그쪽으로 라우팅합니다.
        if self._on_login_request:
            self._on_login_request()
            return
        root = self.winfo_toplevel()
        LoginDialog(root, on_success=lambda _s: self._after_login())

    def _after_login(self) -> None:
        self.refresh()
        if self._on_session_changed:
            self._on_session_changed()

    def _open_messenger(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        MessengerDialog(self.winfo_toplevel(), on_changed=self.refresh)

    def _open_mail(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        MailDialog(self.winfo_toplevel(), on_changed=self.refresh)

    def _open_calendar(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        CalendarDialog(self.winfo_toplevel(), on_changed=self.refresh)

    def _open_ai(self) -> None:
        if not is_logged_in():
            self._open_login()
            return
        AiAssistantDialog(self.winfo_toplevel(), on_changed=self.refresh)
