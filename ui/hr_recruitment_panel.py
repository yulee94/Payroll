"""
ui/hr_recruitment_panel.py - 그룹 공유 채용공고 · 인재풀 UI
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from core.hr import recruitment as rec
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


class HrRecruitmentPanel(tk.Frame):
    """채용공고 · 지원자 · 그룹 인재풀."""

    _SUB_TABS = (
        ("my_postings", "내 공고"),
        ("group_postings", "그룹 공고"),
        ("applicants", "지원자"),
        ("talent_pool", "인재풀"),
    )

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._sub_tab = "my_postings"
        self._sub_btns: dict[str, tk.Button] = {}
        self._rows: list[dict[str, Any]] = []
        self._selected_key: str | None = None
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=(
                "채용공고는 등록 시 동일 그룹(계열사)에 자동 공유됩니다. "
                "지원자를 「인재풀」 또는 「추천 인재」로 표시하면 타 법인·부서에서 채용 시 참조할 수 있습니다. "
                "주민등록번호가 있으면 중복 식별에 사용됩니다."
            ),
            bg="#EFF6FF",
            fg="#1E40AF",
            font=(FONT, 9),
            wraplength=820,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        sub_bar = tk.Frame(self, bg=COLORS["bg"])
        sub_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for tid, label in self._SUB_TABS:
            btn = tk.Button(
                sub_bar,
                text=label,
                relief=tk.FLAT,
                font=(FONT, 10),
                padx=12,
                pady=6,
                cursor="hand2",
                command=lambda t=tid: self._select_sub(t),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self._sub_btns[tid] = btn

        body = tk.Frame(self, bg=COLORS["bg"])
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        left = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        head = tk.Frame(left, bg=COLORS["card"])
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        self._list_title = tk.Label(
            head, text="목록", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")
        )
        self._list_title.pack(side=tk.LEFT)
        tk.Button(
            head,
            text="＋ 추가",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_add,
        ).pack(side=tk.RIGHT)

        list_wrap = tk.Frame(left, bg=COLORS["card"])
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(list_wrap, columns=("c1", "c2"), show="headings", height=14)
        self._tree.heading("c1", text="항목")
        self._tree.heading("c2", text="상태")
        self._tree.column("c1", width=180, stretch=True)
        self._tree.column("c2", width=80, stretch=False)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._tree, self._tree)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        right = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        tk.Label(
            right, text="상세", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        detail_wrap = tk.Frame(right, bg=COLORS["card"])
        detail_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        detail_wrap.grid_rowconfigure(0, weight=1)
        detail_wrap.grid_columnconfigure(0, weight=1)

        self._detail = tk.Text(
            detail_wrap,
            wrap=tk.WORD,
            font=FONT_BODY,
            height=12,
            bg="#F8FAFC",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        dscroll = ttk.Scrollbar(detail_wrap, orient=tk.VERTICAL, command=self._detail.yview)
        self._detail.configure(yscrollcommand=dscroll.set)
        self._detail.grid(row=0, column=0, sticky="nsew")
        dscroll.grid(row=0, column=1, sticky="ns")
        self._detail.configure(state=tk.DISABLED)

        actions = tk.Frame(right, bg=COLORS["card"])
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        self._btn_close = tk.Button(
            actions,
            text="공고 마감",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._close_posting,
        )
        self._btn_talent = tk.Button(
            actions,
            text="인재풀 등록",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._mark_talent_pool,
        )
        self._btn_link = tk.Button(
            actions,
            text="우리 공고에 연결",
            bg="#2563EB",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._link_talent,
        )
        self._btn_close.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_talent.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_link.pack(side=tk.LEFT)

        self._select_sub("my_postings")

    def _select_sub(self, tab_id: str) -> None:
        self._sub_tab = tab_id
        accent = "#0D9488"
        for tid, btn in self._sub_btns.items():
            if tid == tab_id:
                btn.configure(bg=accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10))
        titles = {
            "my_postings": "내 채용공고",
            "group_postings": "그룹 공유 공고",
            "applicants": "지원자",
            "talent_pool": "그룹 인재풀",
        }
        self._list_title.configure(text=titles.get(tab_id, "목록"))
        self._update_action_buttons()
        self.refresh()

    def _update_action_buttons(self) -> None:
        self._btn_close.pack_forget()
        self._btn_talent.pack_forget()
        self._btn_link.pack_forget()
        if self._sub_tab == "my_postings":
            self._btn_close.pack(side=tk.LEFT, padx=(0, 6))
        elif self._sub_tab == "applicants":
            self._btn_talent.pack(side=tk.LEFT, padx=(0, 6))
        elif self._sub_tab == "talent_pool":
            self._btn_link.pack(side=tk.LEFT)

    def refresh(self) -> None:
        self._rows = self._load_rows()
        self._selected_key = None
        for item in self._tree.get_children():
            self._tree.delete(item)
        for row in self._rows:
            key = self._row_key(row)
            c1, c2 = self._row_columns(row)
            self._tree.insert("", tk.END, iid=key, values=(c1, c2))
        self._set_detail("항목을 선택하세요.")

    def _load_rows(self) -> list[dict[str, Any]]:
        if self._sub_tab == "my_postings":
            return rec.list_my_postings()
        if self._sub_tab == "group_postings":
            return rec.list_group_postings(include_own=False)
        if self._sub_tab == "applicants":
            return rec.list_applicants()
        return rec.list_talent_pool()

    def _row_key(self, row: dict[str, Any]) -> str:
        if self._sub_tab == "talent_pool":
            return str(row.get("dedupe_key") or row.get("id") or "")
        return str(row.get("id") or "")

    def _row_columns(self, row: dict[str, Any]) -> tuple[str, str]:
        if self._sub_tab in ("my_postings", "group_postings"):
            title = row.get("title") or "-"
            if self._sub_tab == "group_postings":
                title = f"[{row.get('tenant_name') or row.get('source_tenant_id')}] {title}"
            return title, row.get("status_label") or row.get("status") or ""
        if self._sub_tab == "applicants":
            return row.get("name") or "-", row.get("status_label") or row.get("status") or ""
        name = row.get("name") or "-"
        src = row.get("source_tenant_name") or row.get("source_tenant_id") or ""
        tag = "추천" if row.get("recommended") else "인재풀"
        return f"{name} ({src})", tag

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        key = sel[0]
        self._selected_key = key
        row = next((r for r in self._rows if self._row_key(r) == key), None)
        if row:
            self._show_detail(row)

    def _show_detail(self, row: dict[str, Any]) -> None:
        lines: list[str] = []
        if self._sub_tab in ("my_postings", "group_postings"):
            lines = [
                f"공고: {row.get('title')}",
                f"법인: {row.get('tenant_name') or row.get('source_tenant_id')}",
                f"부서: {row.get('department')} · 현장: {row.get('site') or '-'}",
                f"상태: {row.get('status_label')}",
                "",
                row.get("description") or "(설명 없음)",
            ]
        elif self._sub_tab == "applicants":
            lines = [
                f"성명: {row.get('name')}",
                f"연락처: {row.get('contact') or '-'}",
                f"주민번호: {row.get('rrn_masked') or '(미입력)'}",
                f"공고: {row.get('posting_title')}",
                f"상태: {row.get('status_label')}",
                f"추천 인재: {'예' if row.get('recommended') else '아니오'}",
            ]
            if row.get("ref_tenant_id"):
                lines.append(f"참조: {row.get('ref_tenant_id')} · {row.get('ref_applicant_id')}")
            lines.extend(["", row.get("resume_notes") or "(이력 메모 없음)"])
        else:
            lines = [
                f"성명: {row.get('name')}",
                f"연락처: {row.get('contact') or '-'}",
                f"주민번호: {row.get('rrn_masked') or '(미입력)'}",
                f"출처: {row.get('source_tenant_name')} · {row.get('source_posting_title')}",
                f"공유: {row.get('shared_at') or '-'}",
                "",
                row.get("resume_notes") or "(메모 없음)",
            ]
        self._set_detail("\n".join(lines))

    def _set_detail(self, text: str) -> None:
        self._detail.configure(state=tk.NORMAL)
        self._detail.delete("1.0", tk.END)
        self._detail.insert(tk.END, text)
        self._detail.configure(state=tk.DISABLED)

    def _selected_row(self) -> dict[str, Any] | None:
        if not self._selected_key:
            return None
        return next((r for r in self._rows if self._row_key(r) == self._selected_key), None)

    def _on_add(self) -> None:
        parent = self.winfo_toplevel()
        if self._sub_tab == "my_postings":
            self._add_posting_dialog(parent)
        elif self._sub_tab == "applicants":
            self._add_applicant_dialog(parent)
        elif self._sub_tab == "group_postings":
            messagebox.showinfo("그룹 공고", "타 법인 공고는 열람만 가능합니다.", parent=parent)
        else:
            messagebox.showinfo(
                "인재풀",
                "인재풀은 지원자 상태를 「인재풀」 또는 「추천 인재」로 변경하면 자동 등록됩니다.",
                parent=parent,
            )

    def _add_posting_dialog(self, parent: tk.Misc) -> None:
        title = simpledialog.askstring("채용공고", "공고명:", parent=parent)
        if not title:
            return
        dept = simpledialog.askstring("채용공고", "채용 부서:", parent=parent) or ""
        site = simpledialog.askstring("채용공고", "현장/근무지:", parent=parent) or ""
        desc = simpledialog.askstring("채용공고", "업무 설명:", parent=parent) or ""
        try:
            rec.create_posting(department=dept, site=site, title=title, description=desc)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=parent)

    def _add_applicant_dialog(self, parent: tk.Misc) -> None:
        posts = [p for p in rec.list_my_postings() if p.get("status") == rec.POSTING_STATUS_OPEN]
        if not posts:
            messagebox.showwarning("지원자", "모집중인 채용공고가 없습니다.", parent=parent)
            return
        posting = posts[0]
        if len(posts) > 1:
            titles = "\n".join(f"{i+1}. {p.get('title')}" for i, p in enumerate(posts))
            choice = simpledialog.askstring(
                "공고 선택",
                f"번호를 입력하세요:\n{titles}",
                parent=parent,
            )
            if not choice:
                return
            try:
                idx = int(choice.strip()) - 1
                posting = posts[idx]
            except (ValueError, IndexError):
                messagebox.showerror("오류", "잘못된 번호입니다.", parent=parent)
                return
        name = simpledialog.askstring("지원자", "성명:", parent=parent)
        if not name:
            return
        contact = simpledialog.askstring("지원자", "연락처:", parent=parent) or ""
        rrn = simpledialog.askstring("지원자", "주민번호(선택, 중복식별):", parent=parent) or ""
        notes = simpledialog.askstring("지원자", "이력·메모:", parent=parent) or ""
        dup = rec.find_duplicate_applicant(rrn=rrn, name=name, contact=contact)
        if dup:
            if not messagebox.askyesno(
                "중복",
                f"동일 지원자가 이미 등록되어 있습니다 ({dup.get('name')}).\n계속 등록하시겠습니까?",
                parent=parent,
            ):
                return
        try:
            rec.add_applicant(
                posting["id"],
                name=name,
                contact=contact,
                resume_notes=notes,
                rrn=rrn,
            )
            self.refresh()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=parent)

    def _close_posting(self) -> None:
        row = self._selected_row()
        if not row or self._sub_tab != "my_postings":
            messagebox.showinfo("공고", "마감할 공고를 선택하세요.", parent=self.winfo_toplevel())
            return
        if row.get("status") == rec.POSTING_STATUS_CLOSED:
            return
        rec.update_posting(row["id"], status=rec.POSTING_STATUS_CLOSED)
        self.refresh()

    def _mark_talent_pool(self) -> None:
        row = self._selected_row()
        if not row or self._sub_tab != "applicants":
            messagebox.showinfo("인재풀", "지원자를 선택하세요.", parent=self.winfo_toplevel())
            return
        parent = self.winfo_toplevel()
        recommended = messagebox.askyesno(
            "인재풀",
            "추천 인재로 표시하시겠습니까?\n(아니오 = 일반 인재풀)",
            parent=parent,
        )
        rec.update_applicant(
            row["id"],
            status="talent_pool",
            recommended=recommended,
        )
        self.refresh()
        messagebox.showinfo("인재풀", "그룹 인재풀에 공유되었습니다.", parent=parent)

    def _link_talent(self) -> None:
        row = self._selected_row()
        if not row or self._sub_tab != "talent_pool":
            messagebox.showinfo("연결", "인재풀 항목을 선택하세요.", parent=self.winfo_toplevel())
            return
        if row.get("is_own"):
            messagebox.showinfo("연결", "자사 인재는 지원자 탭에서 관리하세요.", parent=self.winfo_toplevel())
            return
        posts = [p for p in rec.list_my_postings() if p.get("status") == rec.POSTING_STATUS_OPEN]
        if not posts:
            messagebox.showwarning("연결", "모집중인 우리 공고가 없습니다.", parent=self.winfo_toplevel())
            return
        posting = posts[0]
        if len(posts) > 1:
            titles = "\n".join(f"{i+1}. {p.get('title')}" for i, p in enumerate(posts))
            choice = simpledialog.askstring(
                "공고 선택",
                f"연결할 공고 번호:\n{titles}",
                parent=self.winfo_toplevel(),
            )
            if not choice:
                return
            try:
                posting = posts[int(choice.strip()) - 1]
            except (ValueError, IndexError):
                messagebox.showerror("오류", "잘못된 번호입니다.", parent=self.winfo_toplevel())
                return
        try:
            rec.link_talent_to_posting(row["dedupe_key"], posting["id"])
            messagebox.showinfo(
                "연결 완료",
                f"「{row.get('name')}」 지원자가 「{posting.get('title')}」 공고에 연결되었습니다.",
                parent=self.winfo_toplevel(),
            )
            self._select_sub("applicants")
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())
