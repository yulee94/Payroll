"""
ui/bulletin_panel.py - 플랫폼 홈 공유게시판 + 공지 작성
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable

from core.bulletin import (
    Announcement,
    BulletinVisibility,
    can_post_bulletin,
    can_post_group_wide,
    create_announcement,
    delete_announcement,
    format_scope_badge,
    format_scope_preview,
    get_announcement,
    list_announcements_for_viewer,
    list_group_sites,
    list_group_tenants,
)
from core.session_service import get_session, is_logged_in, session_tenant_id
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


class BulletinSection(tk.Frame):
    """플랫폼 홈 — 공유게시판 카드."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_drag_bind: Callable[[tk.Misc], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_drag_bind = on_drag_bind
        self._rows_frame: tk.Frame | None = None
        self._build_shell()
        self.refresh()

    def _bind_bg(self, widget: tk.Misc) -> None:
        if self._on_drag_bind:
            self._on_drag_bind(widget)

    def _build_shell(self) -> None:
        shadow = tk.Frame(self, bg=COLORS["card_shadow"])
        shadow.pack(fill=tk.BOTH, expand=True)
        self._bind_bg(shadow)

        card = tk.Frame(
            shadow,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        card.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 3))
        self._bind_bg(card)

        accent = tk.Frame(card, bg=COLORS["hero_accent"], height=4)
        accent.pack(fill=tk.X)

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)
        self._bind_bg(inner)

        head = tk.Frame(inner, bg=COLORS["card"])
        head.pack(fill=tk.X)
        self._bind_bg(head)

        tk.Label(
            head,
            text="📢  공유게시판",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 13, "bold"),
            anchor=tk.W,
        ).pack(side=tk.LEFT)

        tk.Label(
            head,
            text="그룹 본사·법인 공지",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=(10, 0))

        btn_frame = tk.Frame(head, bg=COLORS["card"])
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(
            btn_frame,
            text="새로고침",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=FONT_BODY,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=(0, 6))

        self._compose_btn = tk.Button(
            btn_frame,
            text="공지 작성",
            bg=COLORS["hero_accent"],
            fg="#FFFFFF",
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._open_compose,
        )
        self._compose_btn.pack(side=tk.LEFT)

        tk.Label(
            inner,
            text="소속 법인·사업장에 해당하는 공지만 표시됩니다.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(8, 10))

        self._rows_frame = tk.Frame(inner, bg=COLORS["card"])
        self._rows_frame.pack(fill=tk.X)
        self._bind_bg(self._rows_frame)

    def refresh(self) -> None:
        if self._rows_frame is None:
            return
        for w in self._rows_frame.winfo_children():
            w.destroy()

        show_compose = is_logged_in() and can_post_bulletin()
        if show_compose:
            self._compose_btn.pack(side=tk.LEFT)
        else:
            self._compose_btn.pack_forget()

        if not is_logged_in():
            tk.Label(
                self._rows_frame,
                text="로그인 후 공지를 확인할 수 있습니다.",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=FONT_BODY,
                anchor=tk.W,
            ).pack(anchor=tk.W)
            return

        sess = get_session()
        tenant_id = session_tenant_id() or (sess.tenant_id if sess else "")
        user_id = sess.user_id if sess else ""
        items = list_announcements_for_viewer(tenant_id=tenant_id, user_id=user_id, limit=8)

        if not items:
            tk.Label(
                self._rows_frame,
                text="등록된 공지가 없습니다.",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=FONT_BODY,
                anchor=tk.W,
            ).pack(anchor=tk.W)
            return

        for ann in items:
            self._add_row(ann)

    def _add_row(self, ann: Announcement) -> None:
        assert self._rows_frame is not None
        row = tk.Frame(self._rows_frame, bg=COLORS["chip_bg"], cursor="hand2")
        row.pack(fill=tk.X, pady=(0, 6))
        self._bind_bg(row)

        inner = tk.Frame(row, bg=COLORS["chip_bg"])
        inner.pack(fill=tk.X, padx=12, pady=10)
        self._bind_bg(inner)

        pin = "📌 " if ann.pinned else ""
        title_lbl = tk.Label(
            inner,
            text=f"{pin}{ann.title}",
            bg=COLORS["chip_bg"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor=tk.W,
        )
        title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        meta = tk.Frame(inner, bg=COLORS["chip_bg"])
        meta.pack(side=tk.RIGHT)
        self._bind_bg(meta)

        badge = format_scope_badge(ann.visibility)
        tk.Label(
            meta,
            text=badge,
            bg="#E0E7FF",
            fg="#3730A3",
            font=(FONT, 8, "bold"),
            padx=8,
            pady=2,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        date_str = (ann.created_at or "")[:10]
        tk.Label(
            meta,
            text=date_str,
            bg=COLORS["chip_bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).pack(side=tk.RIGHT)

        sub = tk.Frame(self._rows_frame, bg=COLORS["card"])
        sub.pack(fill=tk.X, padx=12, pady=(0, 2))
        tk.Label(
            sub,
            text=f"{ann.author_org} · {ann.author_name}",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            anchor=tk.W,
        ).pack(anchor=tk.W)

        def _open(_e: tk.Event | None = None, aid: str = ann.id) -> None:
            BulletinDetailDialog(self.winfo_toplevel(), announcement_id=aid, on_changed=self.refresh)

        for w in (row, inner, title_lbl):
            w.bind("<Button-1>", _open)
            w.bind("<Enter>", lambda e, r=row: r.configure(bg="#E2E8F0"))
            w.bind("<Leave>", lambda e, r=row: r.configure(bg=COLORS["chip_bg"]))

    def _open_compose(self) -> None:
        BulletinComposeDialog(self.winfo_toplevel(), on_saved=self.refresh)


class BulletinDetailDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        announcement_id: str,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._ann_id = announcement_id
        self._on_changed = on_changed
        ann = get_announcement(announcement_id)
        if ann is None:
            messagebox.showerror("공유게시판", "공지를 찾을 수 없습니다.", parent=parent)
            self.destroy()
            return

        self.title(ann.title[:40])
        self.geometry("560x480")
        self.minsize(440, 360)
        self.configure(bg=COLORS["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        tk.Label(
            outer,
            text=ann.title,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
            anchor=tk.W,
            wraplength=500,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        meta = f"{ann.author_org} · {ann.author_name}  |  {(ann.created_at or '')[:16]}"
        tk.Label(
            outer,
            text=meta,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(6, 4))

        tk.Label(
            outer,
            text=format_scope_preview(ann.visibility),
            bg="#EEF2FF",
            fg="#4338CA",
            font=(FONT, 9),
            anchor=tk.W,
            padx=10,
            pady=6,
        ).pack(anchor=tk.W, fill=tk.X, pady=(0, 12))

        body = scrolledtext.ScrolledText(
            outer,
            wrap=tk.WORD,
            font=FONT_BODY,
            height=14,
            relief=tk.FLAT,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        body.pack(fill=tk.BOTH, expand=True)
        body.insert("1.0", ann.body)
        body.configure(state=tk.DISABLED)

        foot = tk.Frame(outer, bg=COLORS["bg"])
        foot.pack(fill=tk.X, pady=(12, 0))

        if can_post_bulletin():
            tk.Button(
                foot,
                text="삭제",
                bg=COLORS["card"],
                fg="#B91C1C",
                relief=tk.FLAT,
                font=FONT_BODY,
                padx=12,
                pady=6,
                cursor="hand2",
                command=lambda: self._delete(ann.title),
            ).pack(side=tk.LEFT)

        tk.Button(
            foot,
            text="닫기",
            bg=COLORS["hero_accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT)

    def _delete(self, title: str) -> None:
        if not messagebox.askyesno("공유게시판", f"「{title}」 공지를 삭제할까요?", parent=self):
            return
        try:
            delete_announcement(self._ann_id)
        except Exception as exc:
            messagebox.showerror("공유게시판", str(exc), parent=self)
            return
        if self._on_changed:
            self._on_changed()
        self.destroy()


class BulletinComposeDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_saved = on_saved
        sess = get_session()
        if sess is None or not can_post_bulletin():
            messagebox.showerror("공유게시판", "공지 작성 권한이 없습니다.", parent=parent)
            self.destroy()
            return

        self._tenant_id = sess.tenant_id
        self._group_wide = can_post_group_wide()
        self._tenant_vars: dict[str, tk.BooleanVar] = {}
        self._site_vars: dict[tuple[str, str], tk.BooleanVar] = {}

        self.title("공지 작성")
        self.geometry("640x720")
        self.minsize(520, 600)
        self.configure(bg=COLORS["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        yscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=yscroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        body = tk.Frame(canvas, bg=COLORS["bg"])
        win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_cfg(_e: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            cw = canvas.winfo_width()
            if cw > 1:
                canvas.itemconfigure(win, width=cw)

        body.bind("<Configure>", _on_cfg)
        canvas.bind("<Configure>", _on_cfg)
        bind_local_wheel(body, canvas)

        pad = tk.Frame(body, bg=COLORS["bg"])
        pad.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        tk.Label(pad, text="제목", bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            anchor=tk.W
        )
        self._title_var = tk.StringVar()
        tk.Entry(
            pad,
            textvariable=self._title_var,
            font=FONT_BODY,
            relief=tk.FLAT,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        ).pack(fill=tk.X, pady=(4, 12), ipady=6)

        tk.Label(pad, text="내용", bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            anchor=tk.W
        )
        self._body_text = scrolledtext.ScrolledText(
            pad,
            wrap=tk.WORD,
            font=FONT_BODY,
            height=8,
            relief=tk.FLAT,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self._body_text.pack(fill=tk.X, pady=(4, 12))

        tk.Label(
            pad,
            text="노출 범위",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).pack(anchor=tk.W)

        scope_frame = tk.Frame(pad, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        scope_frame.pack(fill=tk.X, pady=(6, 8))

        scope_inner = tk.Frame(scope_frame, bg=COLORS["card"])
        scope_inner.pack(fill=tk.X, padx=14, pady=12)

        self._all_group_var = tk.BooleanVar(value=False)
        all_cb = tk.Checkbutton(
            scope_inner,
            text="전체 그룹",
            variable=self._all_group_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=FONT_BODY,
            anchor=tk.W,
            command=self._sync_scope_mode,
        )
        all_cb.pack(anchor=tk.W)
        if not self._group_wide:
            all_cb.configure(state=tk.DISABLED)

        tk.Label(
            scope_inner,
            text="법인 선택 (복수 가능)",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9, "bold"),
        ).pack(anchor=tk.W, pady=(10, 4))

        tenant_box = tk.Frame(scope_inner, bg=COLORS["card"])
        tenant_box.pack(fill=tk.X)
        for tid, tname in list_group_tenants(self._tenant_id):
            var = tk.BooleanVar(value=False)
            self._tenant_vars[tid] = var
            state = tk.NORMAL if self._group_wide or tid == self._tenant_id else tk.DISABLED
            tk.Checkbutton(
                tenant_box,
                text=tname,
                variable=var,
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=FONT_BODY,
                anchor=tk.W,
                state=state,
            ).pack(anchor=tk.W)

        tk.Label(
            scope_inner,
            text="사업장 선택 (복수 가능)",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9, "bold"),
        ).pack(anchor=tk.W, pady=(10, 4))

        site_box = tk.Frame(scope_inner, bg=COLORS["card"])
        site_box.pack(fill=tk.X)
        for site in list_group_sites(self._tenant_id):
            key = (site.tenant_id, site.site_id)
            var = tk.BooleanVar(value=False)
            self._site_vars[key] = var
            label = f"{site.site_name}  [{site.tenant_name}]"
            state = tk.NORMAL if self._group_wide or site.tenant_id == self._tenant_id else tk.DISABLED
            tk.Checkbutton(
                site_box,
                text=label,
                variable=var,
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=FONT_BODY,
                anchor=tk.W,
                state=state,
            ).pack(anchor=tk.W)

        self._preview_lbl = tk.Label(
            pad,
            text="노출: (선택 후 미리보기)",
            bg="#EEF2FF",
            fg="#4338CA",
            font=(FONT, 9),
            anchor=tk.W,
            padx=10,
            pady=8,
            wraplength=560,
            justify=tk.LEFT,
        )
        self._preview_lbl.pack(fill=tk.X, pady=(4, 12))

        for var in list(self._tenant_vars.values()) + list(self._site_vars.values()):
            var.trace_add("write", lambda *_: self._update_preview())
        self._all_group_var.trace_add("write", lambda *_: self._update_preview())

        self._pinned_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            pad,
            text="상단 고정",
            variable=self._pinned_var,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(0, 12))

        foot = tk.Frame(pad, bg=COLORS["bg"])
        foot.pack(fill=tk.X)
        tk.Button(
            foot,
            text="취소",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=FONT_BODY,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            foot,
            text="게시",
            bg=COLORS["hero_accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._save,
        ).pack(side=tk.RIGHT)

    def _sync_scope_mode(self) -> None:
        if self._all_group_var.get():
            for var in self._tenant_vars.values():
                var.set(False)
            for var in self._site_vars.values():
                var.set(False)
        self._update_preview()

    def _collect_visibility(self) -> BulletinVisibility:
        if self._all_group_var.get():
            return BulletinVisibility(all_group=True)
        tenants = [tid for tid, var in self._tenant_vars.items() if var.get()]
        sites = [
            {"tenant_id": tid, "site_id": sid}
            for (tid, sid), var in self._site_vars.items()
            if var.get()
        ]
        return BulletinVisibility(all_group=False, tenants=tenants, sites=sites)

    def _update_preview(self) -> None:
        vis = self._collect_visibility()
        self._preview_lbl.configure(text=format_scope_preview(vis))

    def _save(self) -> None:
        title = self._title_var.get().strip()
        body = self._body_text.get("1.0", tk.END).strip()
        vis = self._collect_visibility()
        try:
            create_announcement(title=title, body=body, visibility=vis, pinned=self._pinned_var.get())
        except Exception as exc:
            messagebox.showerror("공유게시판", str(exc), parent=self)
            return
        messagebox.showinfo("공유게시판", "공지가 등록되었습니다.", parent=self)
        if self._on_saved:
            self._on_saved()
        self.destroy()
