"""
ui/workspace_dialogs.py - 메신저·메일·캘린더 상세 창
"""

from __future__ import annotations

import calendar as cal_mod
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from core.session_service import UserSession, require_session
from services import workspace_store as ws
from services.workspace_store import MAIL_FOLDERS
from ui.theme import COLORS, FONT, FONT_BODY

OnDataChanged = Callable[[], None]


class MessengerDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_changed: OnDataChanged | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self.title("사내 메신저")
        self.geometry("720x520")
        self.minsize(560, 400)
        self.configure(bg=COLORS["bg"])

        sess = require_session()
        self._sess = sess

        body = tk.Frame(self, bg=COLORS["bg"], padx=12, pady=12)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=COLORS["card"], width=200)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        tk.Label(left, text="대화", bg=COLORS["card"], font=(FONT, 11, "bold")).pack(
            anchor=tk.W, padx=10, pady=8
        )
        self._thread_list = tk.Listbox(left, font=FONT_BODY, height=20, activestyle="none")
        self._thread_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._thread_list.bind("<<ListboxSelect>>", self._on_thread_select)

        new_row = tk.Frame(left, bg=COLORS["card"])
        new_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._peer_var = tk.StringVar()
        peers = ws.colleagues_except_self(sess)
        names = [f"{p['display_name']} ({p['username']})" for p in peers]
        self._peer_ids = [p["user_id"] for p in peers]
        combo = ttk.Combobox(new_row, textvariable=self._peer_var, values=names, state="readonly", width=18)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if names:
            combo.current(0)
        tk.Button(
            new_row,
            text="새 대화",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            command=self._start_peer_chat,
        ).pack(side=tk.LEFT, padx=(4, 0))

        right = tk.Frame(body, bg=COLORS["card"])
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._chat_title = tk.Label(right, text="대화를 선택하세요", bg=COLORS["card"], font=(FONT, 11, "bold"))
        self._chat_title.pack(anchor=tk.W, padx=12, pady=(8, 4))

        chat_toolbar = tk.Frame(right, bg=COLORS["card"])
        chat_toolbar.pack(fill=tk.X, padx=12, pady=(0, 4))
        tk.Button(
            chat_toolbar,
            text="선택 메시지 삭제",
            relief=tk.FLAT,
            bg=COLORS["border"],
            command=self._delete_selected_message,
        ).pack(side=tk.LEFT)
        tk.Button(
            chat_toolbar,
            text="대화 기록 모두 삭제",
            relief=tk.FLAT,
            bg=COLORS["border"],
            command=self._clear_conversation,
        ).pack(side=tk.LEFT, padx=(6, 0))

        chat_frame = tk.Frame(right, bg=COLORS["card"])
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        self._msg_list = tk.Listbox(chat_frame, font=FONT_BODY, height=10, activestyle="none")
        msg_scroll = ttk.Scrollbar(chat_frame, command=self._msg_list.yview)
        self._msg_list.configure(yscrollcommand=msg_scroll.set)
        self._msg_list.grid(row=0, column=0, sticky="nsew")
        msg_scroll.grid(row=0, column=1, sticky="ns")
        self._msg_list.bind("<<ListboxSelect>>", self._on_message_select)
        self._msg_list.bind("<Button-3>", self._show_message_menu)

        self._msg_detail = tk.Text(chat_frame, wrap=tk.WORD, font=FONT_BODY, state=tk.DISABLED, height=6)
        detail_scroll = ttk.Scrollbar(chat_frame, command=self._msg_detail.yview)
        self._msg_detail.configure(yscrollcommand=detail_scroll.set)
        self._msg_detail.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        detail_scroll.grid(row=1, column=1, sticky="ns", pady=(6, 0))
        chat_frame.grid_rowconfigure(1, weight=1)

        self._msg_menu = tk.Menu(self, tearoff=0)
        self._msg_menu.add_command(label="이 메시지 삭제", command=self._delete_selected_message)

        send_row = tk.Frame(right, bg=COLORS["card"], padx=8, pady=8)
        send_row.pack(fill=tk.X)
        self._msg_var = tk.StringVar()
        entry = tk.Entry(send_row, textvariable=self._msg_var, font=FONT_BODY)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda _e: self._send())
        tk.Button(send_row, text="전송", relief=tk.FLAT, bg=COLORS["accent"], fg="#FFFFFF", command=self._send).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self._threads: list[dict] = []
        self._active_other_id: str | None = None
        self._active_label: str = ""
        self._visible_msgs: list[dict] = []
        self._reload_threads()

    def _reload_threads(self) -> None:
        self._threads = ws.list_message_threads(self._sess)
        self._thread_list.delete(0, tk.END)
        for t in self._threads:
            unread = f" ({t['unread']})" if t.get("unread") else ""
            self._thread_list.insert(tk.END, f"{t['other_label']}{unread}")

    def _on_thread_select(self, _event: tk.Event | None = None) -> None:
        sel = self._thread_list.curselection()
        if not sel:
            return
        t = self._threads[sel[0]]
        parts = t.get("participants") or []
        other = next((p for p in parts if p != self._sess.user_id), None)
        if other:
            self._open_chat(other, t.get("other_label") or "")

    def _start_peer_chat(self) -> None:
        idx = 0
        name = self._peer_var.get()
        for i, n in enumerate(
            [f"{p['display_name']} ({p['username']})" for p in ws.colleagues_except_self(self._sess)]
        ):
            if n == name:
                idx = i
                break
        if idx < len(self._peer_ids):
            uid = self._peer_ids[idx]
            label = name.split(" (")[0] if name else uid
            self._open_chat(uid, label)

    def _open_chat(self, other_id: str, label: str) -> None:
        self._active_other_id = other_id
        self._active_label = label
        self._chat_title.configure(text=label)
        self._visible_msgs = ws.get_thread_messages(other_id, self._sess)
        self._msg_list.delete(0, tk.END)
        for m in self._visible_msgs:
            who = "나" if m.get("sender_id") == self._sess.user_id else label
            ts = (m.get("sent_at") or "")[:16]
            preview = (m.get("text") or "")[:80].replace("\n", " ")
            self._msg_list.insert(tk.END, f"[{ts}] {who}: {preview}")
        self._msg_detail.configure(state=tk.NORMAL)
        self._msg_detail.delete("1.0", tk.END)
        self._msg_detail.configure(state=tk.DISABLED)
        ws.mark_thread_read(other_id, self._sess)
        self._reload_threads()

    def _on_message_select(self, _event: tk.Event | None = None) -> None:
        sel = self._msg_list.curselection()
        if not sel or sel[0] >= len(self._visible_msgs):
            return
        m = self._visible_msgs[sel[0]]
        self._msg_detail.configure(state=tk.NORMAL)
        self._msg_detail.delete("1.0", tk.END)
        self._msg_detail.insert(tk.END, m.get("text", ""))
        self._msg_detail.configure(state=tk.DISABLED)

    def _show_message_menu(self, event: tk.Event) -> None:
        idx = self._msg_list.nearest(event.y)
        if idx < 0 or idx >= len(self._visible_msgs):
            return
        self._msg_list.selection_clear(0, tk.END)
        self._msg_list.selection_set(idx)
        self._on_message_select()
        try:
            self._msg_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._msg_menu.grab_release()

    def _delete_selected_message(self) -> None:
        if not self._active_other_id:
            messagebox.showinfo("메신저", "대화 상대를 선택하세요.", parent=self)
            return
        sel = self._msg_list.curselection()
        if not sel or sel[0] >= len(self._visible_msgs):
            messagebox.showinfo("메신저", "삭제할 메시지를 선택하세요.", parent=self)
            return
        msg = self._visible_msgs[sel[0]]
        if not messagebox.askyesno(
            "메시지 삭제",
            "선택한 메시지를 내 채팅함에서 삭제할까요?\n(서버에는 감사용으로 보관됩니다.)",
            parent=self,
        ):
            return
        try:
            ws.delete_message_for_user(msg.get("id", ""), self._active_other_id, self._sess)
            self._open_chat(self._active_other_id, self._active_label)
            if self._on_changed:
                self._on_changed()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("메신저", str(exc), parent=self)

    def _clear_conversation(self) -> None:
        if not self._active_other_id:
            messagebox.showinfo("메신저", "대화 상대를 선택하세요.", parent=self)
            return
        if not self._visible_msgs:
            messagebox.showinfo("메신저", "삭제할 대화 기록이 없습니다.", parent=self)
            return
        if not messagebox.askyesno(
            "대화 기록 삭제",
            "이 대화의 모든 메시지를 내 채팅함에서 삭제할까요?\n(서버에는 감사용으로 보관됩니다.)",
            parent=self,
        ):
            return
        try:
            ws.clear_thread_for_user(self._active_other_id, self._sess)
            self._open_chat(self._active_other_id, self._active_label)
            if self._on_changed:
                self._on_changed()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("메신저", str(exc), parent=self)

    def _send(self) -> None:
        if not self._active_other_id:
            messagebox.showinfo("메신저", "대화 상대를 선택하세요.", parent=self)
            return
        try:
            ws.send_message(self._active_other_id, self._msg_var.get(), self._sess)
            self._msg_var.set("")
            self._open_chat(self._active_other_id, self._active_label)
            if self._on_changed:
                self._on_changed()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("메신저", str(exc), parent=self)


class MailDialog(tk.Toplevel):
    """COSS GW 스타일 — 좌측 폴더, 우측 보낸사람/제목/날짜 목록."""

    def __init__(self, parent: tk.Misc, *, on_changed: OnDataChanged | None = None) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self.title("내 메일함")
        self.geometry("820x520")
        self.minsize(640, 400)
        self.configure(bg=COLORS["bg"])
        self._sess = require_session()
        self._folder = tk.StringVar(value="inbox")
        self._mails: list[dict] = []

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=16, pady=(12, 8))
        tk.Label(
            header,
            text=f"{self._sess.display_name} 님의 메일함",
            bg=COLORS["bg"],
            font=(FONT, 12, "bold"),
        ).pack(side=tk.LEFT)
        self._folder_count_lbl = tk.Label(header, text="", bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 9))
        self._folder_count_lbl.pack(side=tk.RIGHT)

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        nav = tk.Frame(body, bg=COLORS["card"], width=140)
        nav.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        tk.Label(nav, text="메일함", bg=COLORS["card"], font=(FONT, 10, "bold")).pack(anchor=tk.W, padx=10, pady=8)
        self._folder_btns: dict[str, tk.Button] = {}
        for fid, label in MAIL_FOLDERS:
            btn = tk.Button(
                nav,
                text=label,
                anchor=tk.W,
                relief=tk.FLAT,
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=FONT_BODY,
                padx=10,
                pady=6,
                cursor="hand2",
                command=lambda f=fid: self._select_folder(f),
            )
            btn.pack(fill=tk.X, padx=6, pady=2)
            self._folder_btns[fid] = btn

        right = tk.Frame(body, bg=COLORS["card"])
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        list_wrap = tk.Frame(right, bg=COLORS["card"])
        list_wrap.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        cols = ("sender", "subject", "date")
        self._tree = ttk.Treeview(list_wrap, columns=cols, show="headings", height=14)
        self._tree.heading("sender", text="보낸 사람")
        self._tree.heading("subject", text="제목")
        self._tree.heading("date", text="날짜")
        self._tree.column("sender", width=120, anchor=tk.W)
        self._tree.column("subject", width=360, anchor=tk.W)
        self._tree.column("date", width=120, anchor=tk.CENTER)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._body = tk.Text(right, wrap=tk.WORD, font=FONT_BODY, state=tk.DISABLED, height=8)
        self._body.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(fill=tk.X, padx=16, pady=(0, 12))
        tk.Button(
            btn_row,
            text="메모 작성 (받은 메일)",
            relief=tk.FLAT,
            bg=COLORS["accent"],
            fg="#FFFFFF",
            command=lambda: self._compose("inbox"),
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            btn_row,
            text="보낸 메일함에 저장",
            relief=tk.FLAT,
            bg="#64748B",
            fg="#FFFFFF",
            command=lambda: self._compose("sent"),
        ).pack(side=tk.LEFT)

        self._reload()

    def _select_folder(self, folder_id: str) -> None:
        self._folder.set(folder_id)
        for fid, btn in self._folder_btns.items():
            if fid == folder_id:
                btn.configure(bg=COLORS.get("accent_light", "#E0F4FD"), fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"])
        self._reload()

    def _reload(self) -> None:
        fid = self._folder.get()
        self._mails = ws.list_mail(self._sess, folder=fid)
        self._folder_count_lbl.configure(text=f"{len(self._mails)}건")
        for i in self._tree.get_children():
            self._tree.delete(i)
        for m in self._mails:
            mark = "● " if not m.get("read") else ""
            self._tree.insert(
                "",
                tk.END,
                iid=m["id"],
                values=(
                    m.get("sender", ""),
                    f"{mark}{m.get('subject', '')}",
                    (m.get("received_at") or "")[:16],
                ),
            )
        self._body.configure(state=tk.NORMAL)
        self._body.delete("1.0", tk.END)
        self._body.configure(state=tk.DISABLED)

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        mid = sel[0]
        m = next((x for x in self._mails if x.get("id") == mid), None)
        if not m:
            return
        ws.mark_mail_read(mid, self._sess)
        self._body.configure(state=tk.NORMAL)
        self._body.delete("1.0", tk.END)
        self._body.insert(
            tk.END,
            f"보낸 사람: {m.get('sender', '')}\n"
            f"수신: {m.get('received_at', '')}\n\n"
            f"{m.get('body', '')}",
        )
        self._body.configure(state=tk.DISABLED)
        self._reload()
        if self._on_changed:
            self._on_changed()

    def _compose(self, folder: str) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("메모 작성")
        dlg.configure(bg=COLORS["bg"])
        subj = tk.StringVar()
        body = tk.Text(dlg, height=8, width=48, font=FONT_BODY)
        tk.Label(dlg, text="제목", bg=COLORS["bg"]).pack(anchor=tk.W, padx=12, pady=(12, 0))
        tk.Entry(dlg, textvariable=subj, width=50).pack(padx=12)
        tk.Label(dlg, text="내용", bg=COLORS["bg"]).pack(anchor=tk.W, padx=12, pady=(8, 0))
        body.pack(padx=12)

        def save() -> None:
            ws.add_mail(subj.get(), body.get("1.0", tk.END), folder=folder, session=self._sess)
            dlg.destroy()
            self._select_folder(folder if folder != "sent" else "sent")
            if self._on_changed:
                self._on_changed()

        tk.Button(dlg, text="저장", command=save, bg=COLORS["accent"], fg="#FFFFFF").pack(pady=12)


class CalendarDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, on_changed: OnDataChanged | None = None) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self.title("캘린더")
        self.geometry("520x440")
        self.configure(bg=COLORS["bg"])
        today = date.today()
        self._year = today.year
        self._month = today.month

        head = tk.Frame(self, bg=COLORS["bg"])
        head.pack(fill=tk.X, padx=16, pady=12)
        tk.Button(head, text="◀", command=self._prev_month).pack(side=tk.LEFT)
        self._month_lbl = tk.Label(head, text="", bg=COLORS["bg"], font=(FONT, 12, "bold"))
        self._month_lbl.pack(side=tk.LEFT, padx=12)
        tk.Button(head, text="▶", command=self._next_month).pack(side=tk.LEFT)

        self._grid = tk.Frame(self, bg=COLORS["bg"])
        self._grid.pack(padx=16)
        self._events_list = tk.Listbox(self, font=FONT_BODY, height=8)
        self._events_list.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        add_row = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=8)
        add_row.pack(fill=tk.X)
        self._title_var = tk.StringVar()
        self._date_var = tk.StringVar(value=today.isoformat())
        tk.Entry(add_row, textvariable=self._title_var, width=24, font=FONT_BODY).pack(side=tk.LEFT)
        tk.Entry(add_row, textvariable=self._date_var, width=12, font=FONT_BODY).pack(side=tk.LEFT, padx=4)
        tk.Button(add_row, text="일정 추가", command=self._add, bg=COLORS["accent"], fg="#FFFFFF").pack(
            side=tk.LEFT
        )

        self._render()

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._render()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._render()

    def _render(self) -> None:
        from core.session_service import require_session

        sess = require_session()
        self._month_lbl.configure(text=f"{self._year}년 {self._month}월")
        for w in self._grid.winfo_children():
            w.destroy()
        for col, wd in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
            tk.Label(self._grid, text=wd, bg=COLORS["bg"], font=(FONT, 9, "bold"), width=4).grid(
                row=0, column=col
            )
        events = ws.list_calendar_events(self._year, self._month, sess)
        by_date: dict[str, list[str]] = {}
        for ev in events:
            d = ev.get("date", "")
            by_date.setdefault(d, []).append(ev.get("title", ""))
        weeks = cal_mod.Calendar(firstweekday=0).monthdayscalendar(self._year, self._month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(self._grid, text="", bg=COLORS["bg"], width=4).grid(row=r, column=c)
                    continue
                dkey = f"{self._year:04d}-{self._month:02d}-{day:02d}"
                mark = "●" if dkey in by_date else ""
                tk.Label(
                    self._grid,
                    text=f"{day}{mark}",
                    bg=COLORS["card"] if dkey in by_date else COLORS["bg"],
                    width=4,
                ).grid(row=r, column=c, padx=1, pady=1)
        self._events_list.delete(0, tk.END)
        for ev in sorted(events, key=lambda x: x.get("date", "")):
            self._events_list.insert(tk.END, f"{ev.get('date')}  {ev.get('title')}")

    def _add(self) -> None:
        from core.session_service import require_session

        try:
            ws.add_calendar_event(self._title_var.get(), self._date_var.get(), require_session())
            self._title_var.set("")
            self._render()
            if self._on_changed:
                self._on_changed()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("캘린더", str(exc), parent=self)
