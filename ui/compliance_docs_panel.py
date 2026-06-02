"""
ui/compliance_docs_panel.py - 법정·규정 문서함 (정관·인사규정·법정 의무)
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from core.compliance_docs import (
    acknowledge_document,
    can_manage_compliance_docs,
    category_label,
    delete_document,
    get_document,
    has_acknowledged,
    list_documents,
    requires_acknowledgment,
    upload_document,
)
from core.compliance_docs.categories import (
    ALL_CATEGORIES,
    CATEGORY_LABELS,
    REGULATIONS_CATEGORIES,
    STATUTORY_CATEGORIES,
    TAB_GROUP_LABELS,
    TAB_GROUP_REGULATIONS,
    TAB_GROUP_STATUTORY,
)
from core.compliance_docs.store import resolve_file_path
from core.user_store import get_user
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


class ComplianceDocsPanel(tk.Frame):
    """법인별 정관·인사규정·법정 의무 문서함."""

    _TAB_GROUPS = (TAB_GROUP_REGULATIONS, TAB_GROUP_STATUTORY)

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._group = TAB_GROUP_REGULATIONS
        self._group_btns: dict[str, tk.Button] = {}
        self._rows: list[dict[str, Any]] = []
        self._selected_id: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        notice = tk.Frame(self, bg="#ECFDF5", highlightbackground="#A7F3D0", highlightthickness=1)
        notice.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            notice,
            text="근로기준법 등 관련 법령에 따라 열람 가능한 자료입니다. "
            "본 문서함의 자료는 소속 법인(고객사) 구성원에게만 제공됩니다.",
            bg="#ECFDF5",
            fg="#065F46",
            font=(FONT, 9),
            wraplength=860,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        bar = tk.Frame(self, bg=COLORS["bg"])
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for gid in self._TAB_GROUPS:
            btn = tk.Button(
                bar,
                text=TAB_GROUP_LABELS.get(gid, gid),
                relief=tk.FLAT,
                font=(FONT, 10),
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda g=gid: self._select_group(g),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self._group_btns[gid] = btn

        self._upload_btn = tk.Button(
            bar,
            text="＋ 문서 업로드",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._upload_dialog,
        )
        self._upload_btn.pack(side=tk.RIGHT)

        tk.Button(
            bar,
            text="새로고침",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 10),
            padx=10,
            pady=8,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        body = tk.Frame(self, bg=COLORS["bg"])
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        left = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        tk.Label(
            left,
            text="문서 목록",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        list_wrap = tk.Frame(left, bg=COLORS["card"])
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_wrap,
            font=(FONT, 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            selectmode=tk.SINGLE,
            activestyle="none",
        )
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scroll.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        right = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._detail_title = tk.Label(
            right,
            text="문서를 선택하세요",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 12, "bold"),
            anchor=tk.W,
        )
        self._detail_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))

        self._detail_body = tk.Frame(right, bg=COLORS["card"])
        self._detail_body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self._detail_body.grid_columnconfigure(0, weight=1)

        self._meta_label = tk.Label(
            self._detail_body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=480,
        )
        self._meta_label.pack(anchor=tk.W, fill=tk.X)

        self._desc_label = tk.Label(
            self._detail_body,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=FONT_BODY,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=480,
        )
        self._desc_label.pack(anchor=tk.W, fill=tk.X, pady=(8, 0))

        self._ack_status = tk.Label(
            self._detail_body,
            text="",
            bg=COLORS["card"],
            fg="#B45309",
            font=(FONT, 9, "bold"),
            anchor=tk.W,
        )
        self._ack_status.pack(anchor=tk.W, pady=(10, 0))

        actions = tk.Frame(self._detail_body, bg=COLORS["card"])
        actions.pack(anchor=tk.W, pady=(14, 0))

        self._open_btn = tk.Button(
            actions,
            text="문서 열기",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._open_selected,
            state=tk.DISABLED,
        )
        self._open_btn.pack(side=tk.LEFT)

        self._ack_btn = tk.Button(
            actions,
            text="열람 확인",
            bg="#F59E0B",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._acknowledge_selected,
            state=tk.DISABLED,
        )
        self._ack_btn.pack(side=tk.LEFT, padx=(8, 0))

        self._delete_btn = tk.Button(
            actions,
            text="비활성화",
            bg=COLORS["card"],
            fg="#DC2626",
            relief=tk.FLAT,
            font=(FONT, 10),
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._deactivate_selected,
            state=tk.DISABLED,
        )
        self._delete_btn.pack(side=tk.LEFT, padx=(8, 0))

        bind_local_wheel(self._listbox, self._listbox)

    def _categories_for_group(self) -> frozenset[str]:
        if self._group == TAB_GROUP_STATUTORY:
            return STATUTORY_CATEGORIES
        return REGULATIONS_CATEGORIES

    def _sync_group_buttons(self) -> None:
        accent = "#0D9488"
        for gid, btn in self._group_btns.items():
            if gid == self._group:
                btn.configure(bg=accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10))

    def _select_group(self, group_id: str) -> None:
        if self._group == group_id:
            return
        self._group = group_id
        self.refresh()

    def refresh(self) -> None:
        can_manage = can_manage_compliance_docs()
        if can_manage:
            self._upload_btn.configure(state=tk.NORMAL)
        else:
            self._upload_btn.configure(state=tk.DISABLED)

        try:
            self._rows = list_documents(categories=self._categories_for_group())
        except PermissionError as exc:
            messagebox.showwarning("접근 제한", str(exc), parent=self.winfo_toplevel())
            self._rows = []

        self._listbox.delete(0, tk.END)
        self._selected_id = None
        for row in self._rows:
            badge = category_label(str(row.get("category")))
            eff = str(row.get("effective_date") or "")[:10]
            eff_part = f" · 시행 {eff}" if eff else ""
            ack_mark = ""
            if requires_acknowledgment(str(row.get("category"))):
                if has_acknowledged(str(row.get("id"))):
                    ack_mark = " ✓열람"
                else:
                    ack_mark = " · 미확인"
            line = f"[{badge}] {row.get('title', '')}{eff_part}{ack_mark}"
            self._listbox.insert(tk.END, line)

        if self._rows:
            self._listbox.selection_set(0)
            self._selected_id = str(self._rows[0].get("id"))
            self._show_detail(self._rows[0])
        else:
            self._show_empty()

        self._sync_group_buttons()

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._rows):
            row = self._rows[idx]
            self._selected_id = str(row.get("id"))
            self._show_detail(row)

    def _show_empty(self) -> None:
        self._detail_title.configure(text="등록된 문서가 없습니다")
        self._meta_label.configure(text="관리자가 업로드한 자료가 여기에 표시됩니다.")
        self._desc_label.configure(text="")
        self._ack_status.configure(text="")
        self._open_btn.configure(state=tk.DISABLED)
        self._ack_btn.configure(state=tk.DISABLED)
        self._delete_btn.configure(state=tk.DISABLED)

    def _show_detail(self, row: dict[str, Any]) -> None:
        doc_id = str(row.get("id") or "")
        self._detail_title.configure(text=str(row.get("title") or ""))
        uploader = ""
        urec = get_user(str(row.get("uploaded_by") or ""))
        if urec:
            uploader = urec.display_name
        meta_lines = [
            f"분류: {category_label(str(row.get('category')))}",
            f"업로드: {(str(row.get('uploaded_at') or ''))[:10]}",
        ]
        if uploader:
            meta_lines.append(f"등록: {uploader}")
        eff = str(row.get("effective_date") or "")[:10]
        if eff:
            meta_lines.append(f"시행일: {eff}")
        ver = str(row.get("version") or "").strip()
        if ver:
            meta_lines.append(f"버전: {ver}")
        self._meta_label.configure(text="\n".join(meta_lines))
        desc = str(row.get("description") or "").strip()
        self._desc_label.configure(text=desc if desc else "(설명 없음)")

        needs_ack = requires_acknowledgment(str(row.get("category")))
        if needs_ack:
            if has_acknowledged(doc_id):
                self._ack_status.configure(text="열람 확인 완료", fg="#059669")
                self._ack_btn.configure(state=tk.DISABLED)
            else:
                self._ack_status.configure(
                    text="법정 교육·공지 자료 — 열람 후 「열람 확인」을 눌러 주세요.",
                    fg="#B45309",
                )
                self._ack_btn.configure(state=tk.NORMAL)
        else:
            self._ack_status.configure(text="")
            self._ack_btn.configure(state=tk.DISABLED)

        self._open_btn.configure(state=tk.NORMAL)
        if can_manage_compliance_docs():
            self._delete_btn.configure(state=tk.NORMAL)
        else:
            self._delete_btn.configure(state=tk.DISABLED)

    def _selected_row(self) -> dict[str, Any] | None:
        if not self._selected_id:
            return None
        return get_document(self._selected_id)

    def _open_file(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except OSError as exc:
            messagebox.showerror("열기 실패", str(exc), parent=self.winfo_toplevel())

    def _open_selected(self) -> None:
        row = self._selected_row()
        if not row:
            return
        path = resolve_file_path(row)
        if path is None:
            messagebox.showwarning(
                "파일 없음",
                "저장된 파일을 찾을 수 없습니다.\n관리자에게 문의하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        self._open_file(path)

    def _acknowledge_selected(self) -> None:
        row = self._selected_row()
        if not row:
            return
        doc_id = str(row.get("id"))
        if not messagebox.askyesno(
            "열람 확인",
            f"「{row.get('title')}」 자료를 열람하였음을 확인합니다.\n"
            "계속하시겠습니까?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            acknowledge_document(doc_id)
            messagebox.showinfo("완료", "열람 확인이 기록되었습니다.", parent=self.winfo_toplevel())
            self.refresh()
            if self._selected_id:
                for r in self._rows:
                    if str(r.get("id")) == self._selected_id:
                        self._show_detail(r)
                        break
        except (PermissionError, ValueError) as exc:
            messagebox.showwarning("오류", str(exc), parent=self.winfo_toplevel())

    def _deactivate_selected(self) -> None:
        row = self._selected_row()
        if not row:
            return
        if not messagebox.askyesno(
            "비활성화",
            f"「{row.get('title')}」 문서를 목록에서 숨깁니다.\n계속하시겠습니까?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            delete_document(str(row.get("id")))
            self.refresh()
        except PermissionError as exc:
            messagebox.showwarning("접근 제한", str(exc), parent=self.winfo_toplevel())

    def _upload_dialog(self) -> None:
        if not can_manage_compliance_docs():
            messagebox.showwarning(
                "접근 제한",
                "문서 업로드는 HR 담당자 또는 관리자만 가능합니다.",
                parent=self.winfo_toplevel(),
            )
            return

        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("문서 업로드")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        dlg.configure(bg=COLORS["bg"])

        frm = tk.Frame(dlg, bg=COLORS["bg"], padx=20, pady=16)
        frm.pack(fill=tk.BOTH, expand=True)

        fields: dict[str, tk.Variable] = {
            "title": tk.StringVar(),
            "description": tk.StringVar(),
            "effective_date": tk.StringVar(),
            "version": tk.StringVar(),
        }
        file_path = tk.StringVar()

        cats = sorted(
            (c for c in ALL_CATEGORIES if c in self._categories_for_group()),
            key=lambda c: list(ALL_CATEGORIES).index(c),
        )
        cat_var = tk.StringVar(value=cats[0] if cats else ALL_CATEGORIES[0])

        row_i = 0

        def add_row(label: str, widget: tk.Widget) -> None:
            nonlocal row_i
            tk.Label(frm, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 10)).grid(
                row=row_i, column=0, sticky="w", pady=4
            )
            widget.grid(row=row_i, column=1, sticky="ew", pady=4, padx=(8, 0))
            row_i += 1

        frm.grid_columnconfigure(1, weight=1)

        cat_combo = ttk.Combobox(
            frm,
            textvariable=cat_var,
            values=[f"{c}|{CATEGORY_LABELS[c]}" for c in cats],
            state="readonly",
            width=40,
        )
        if cats:
            cat_combo.set(f"{cats[0]}|{CATEGORY_LABELS[cats[0]]}")
        add_row("분류", cat_combo)

        add_row("제목", tk.Entry(frm, textvariable=fields["title"], width=42))
        add_row("설명", tk.Entry(frm, textvariable=fields["description"], width=42))
        add_row("시행일", tk.Entry(frm, textvariable=fields["effective_date"], width=20))
        tk.Label(
            frm,
            text="(YYYY-MM-DD, 선택)",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).grid(row=row_i, column=1, sticky="w", padx=(8, 0))
        row_i += 1
        add_row("버전", tk.Entry(frm, textvariable=fields["version"], width=20))

        fp_row = tk.Frame(frm, bg=COLORS["bg"])
        tk.Entry(fp_row, textvariable=file_path, width=30, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

        def pick_file() -> None:
            path = filedialog.askopenfilename(
                parent=dlg,
                title="문서 파일 선택",
                filetypes=[
                    ("문서", "*.pdf *.doc *.docx *.hwp *.hwpx *.xls *.xlsx *.ppt *.pptx"),
                    ("이미지", "*.png *.jpg *.jpeg *.gif *.webp"),
                    ("모든 파일", "*.*"),
                ],
            )
            if path:
                file_path.set(path)

        tk.Button(fp_row, text="찾아보기…", command=pick_file).pack(side=tk.LEFT, padx=(6, 0))
        add_row("파일", fp_row)

        def submit() -> None:
            raw_cat = cat_var.get().split("|")[0]
            src = file_path.get().strip()
            if not src:
                messagebox.showwarning("입력", "파일을 선택하세요.", parent=dlg)
                return
            try:
                upload_document(
                    category=raw_cat,
                    title=fields["title"].get(),
                    description=fields["description"].get(),
                    effective_date=fields["effective_date"].get(),
                    version=fields["version"].get(),
                    source_path=Path(src),
                )
                dlg.destroy()
                self.refresh()
                messagebox.showinfo("완료", "문서가 등록되었습니다.", parent=self.winfo_toplevel())
            except (PermissionError, ValueError) as exc:
                messagebox.showwarning("오류", str(exc), parent=dlg)

        btn_row = tk.Frame(frm, bg=COLORS["bg"])
        btn_row.grid(row=row_i, column=0, columnspan=2, pady=(12, 0))
        tk.Button(
            btn_row,
            text="업로드",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            command=submit,
        ).pack(side=tk.LEFT)
        tk.Button(btn_row, text="취소", command=dlg.destroy).pack(side=tk.LEFT, padx=(8, 0))


def build_compliance_docs_panel(parent: tk.Misc) -> ComplianceDocsPanel:
    return ComplianceDocsPanel(parent)
