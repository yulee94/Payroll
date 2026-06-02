"""
ui/tenant_admin_panel.py - Bitween 법인(테넌트) · 화이트라벨 관리
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from core.brand_display import active_tenant_login_id, company_name_line
from core.tenant_store import (
    clear_tenant_logo,
    create_tenant,
    delete_tenant,
    get_active_tenant_id,
    get_tenant,
    list_tenants,
    resolve_tenant_logo_path,
    save_tenant_logo,
    set_active_tenant,
    tenant_has_custom_logo,
    update_tenant,
    validate_tenant_id,
)
from ui.brand_assets import logo_photoimage
from ui.theme import COLORS, FONT, FONT_BODY

OnTenantChanged = Callable[[], None]


class TenantAdminPanel(ttk.Frame):
    """법인 등록·활성화·법인별 로고 업로드."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_tenant_changed: OnTenantChanged | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_tenant_changed = on_tenant_changed
        self._selected_id: str | None = None
        self._photo_refs: list[Any] = []

        self._id_var = tk.StringVar()
        self._name_var = tk.StringVar()
        self._name_ko_var = tk.StringVar()
        self._login_var = tk.StringVar()
        self._notes_var = tk.StringVar()
        self._status_var = tk.StringVar()

        self._build()
        self.refresh()

    def _build(self) -> None:
        pad = ttk.Frame(self, padding=24)
        pad.pack(fill=tk.BOTH, expand=True, anchor=tk.NW)

        ttk.Label(pad, text="법인 관리", font=(FONT, 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=(
                "Bitween을 이용하는 법인마다 표시명·로그인 아이디·로고를 따로 등록합니다. "
                "목록에서 법인을 선택한 뒤 로고를 업로드하면 해당 법인에만 저장됩니다. "
                "「이 법인 사용」으로 전환하면 사이드바·플랫폼 홈·보고서에 그 법인 이름·로고가 표시됩니다."
            ),
            wraplength=820,
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(8, 16))

        body = ttk.Frame(pad)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="등록된 법인", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_rowconfigure(0, weight=1)

        list_frame = ttk.Frame(left)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(list_frame, height=14, font=FONT_BODY, activestyle="none")
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scroll.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)

        list_btn = ttk.Frame(left)
        list_btn.grid(row=1, column=0, sticky=tk.EW, pady=(8, 0))
        ttk.Button(list_btn, text="새로고침", command=self.refresh).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(list_btn, text="이 법인 사용", command=self._activate_selected).pack(side=tk.LEFT)

        right = ttk.LabelFrame(body, text="법인 정보", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(1, weight=1)

        fields = (
            ("법인 ID", self._id_var, "영문·숫자 (예: elso) — 저장 후 변경 불가"),
            ("표시명", self._name_var, "화면에 보이는 회사명 (예: ELSO)"),
            ("표시명(한글)", self._name_ko_var, "예: (주)엘소"),
            ("로그인 아이디", self._login_var, "해당 법인 관리용 ID"),
        )
        for row, (label, var, hint) in enumerate(fields):
            ttk.Label(right, text=label, font=(FONT, 9, "bold")).grid(
                row=row * 2, column=0, sticky=tk.W, pady=(0 if row == 0 else 10, 2)
            )
            ttk.Entry(right, textvariable=var, width=36).grid(
                row=row * 2, column=1, sticky=tk.EW, pady=(0 if row == 0 else 10, 2)
            )
            ttk.Label(right, text=hint, foreground=COLORS["muted"], font=(FONT, 8)).grid(
                row=row * 2 + 1, column=1, sticky=tk.W
            )

        ttk.Label(right, text="메모", font=(FONT, 9, "bold")).grid(
            row=8, column=0, sticky=tk.NW, pady=(10, 2)
        )
        self._notes_entry = ttk.Entry(right, textvariable=self._notes_var, width=36)
        self._notes_entry.grid(row=8, column=1, sticky=tk.EW, pady=(10, 2))

        logo_box = ttk.LabelFrame(right, text="법인별 로고", padding=10)
        logo_box.grid(row=9, column=0, columnspan=2, sticky=tk.EW, pady=(16, 0))
        logo_box.grid_columnconfigure(1, weight=1)

        self._logo_preview_host = tk.Frame(logo_box, bg=COLORS["card"], width=120, height=72)
        self._logo_preview_host.grid(row=0, column=0, rowspan=2, sticky=tk.NW, padx=(0, 12))
        self._logo_preview_host.grid_propagate(False)
        self._logo_preview_label = tk.Label(
            self._logo_preview_host,
            text="미리보기",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        )
        self._logo_preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        logo_btn_col = ttk.Frame(logo_box)
        logo_btn_col.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(logo_btn_col, text="로고 업로드…", command=self._upload_logo).pack(anchor=tk.W)
        ttk.Button(logo_btn_col, text="로고 제거", command=self._clear_logo).pack(anchor=tk.W, pady=(6, 0))

        self._logo_status = ttk.Label(logo_box, text="", font=(FONT, 8), foreground=COLORS["muted"])
        self._logo_status.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))

        action = ttk.Frame(right)
        action.grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(18, 0))
        ttk.Button(action, text="신규 등록", command=self._create_new).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action, text="저장", command=self._save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action, text="삭제", command=self._delete).pack(side=tk.LEFT)

        ttk.Label(pad, textvariable=self._status_var, foreground=COLORS["accent"], font=FONT_BODY).pack(
            anchor=tk.W, pady=(16, 0)
        )

    def refresh(self) -> None:
        active = get_active_tenant_id()
        self._listbox.delete(0, tk.END)
        for rec in list_tenants():
            marks: list[str] = []
            if rec.tenant_id == active:
                marks.append("★")
            if tenant_has_custom_logo(rec.tenant_id):
                marks.append("로고")
            suffix = f"  [{' · '.join(marks)}]" if marks else ""
            self._listbox.insert(tk.END, f"{rec.display_name}  ({rec.tenant_id}){suffix}")
        self._status_var.set(
            f"현재 사용 중: {company_name_line()} · 아이디 {active_tenant_login_id()}"
        )
        if self._selected_id:
            self._load_form(self._selected_id)

    def _on_list_select(self, _event: tk.Event | None = None) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        text = self._listbox.get(sel[0])
        if "(" in text and ")" in text:
            tid = text.rsplit("(", 1)[-1].split(")")[0].strip()
            self._load_form(tid)

    def _refresh_logo_preview(self, tenant_id: str | None) -> None:
        for child in self._logo_preview_host.winfo_children():
            child.destroy()
        self._logo_preview_label = tk.Label(
            self._logo_preview_host,
            text="미리보기",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        )
        if not tenant_id:
            self._logo_preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            return
        path = resolve_tenant_logo_path(tenant_id)
        photo = logo_photoimage(
            self._logo_preview_host,
            self._photo_refs,
            max_width=110,
            variant="light",
            logo_path=path,
            blend_bg=COLORS["card"],
        )
        if photo:
            self._logo_preview_label = tk.Label(
                self._logo_preview_host,
                image=photo,
                bg=COLORS["card"],
                bd=0,
                highlightthickness=0,
            )
            self._logo_preview_label.image = photo
            self._logo_preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self._logo_preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _load_form(self, tenant_id: str) -> None:
        rec = get_tenant(tenant_id)
        if not rec:
            return
        self._selected_id = rec.tenant_id
        self._id_var.set(rec.tenant_id)
        self._name_var.set(rec.display_name)
        self._name_ko_var.set(rec.display_name_ko)
        self._login_var.set(rec.login_id)
        self._notes_var.set(rec.notes)
        if rec.logo_path:
            self._logo_status.configure(
                text=f"「{rec.display_name}」 전용 로고: {rec.logo_path.name}"
            )
        else:
            self._logo_status.configure(
                text=f"「{rec.display_name}」 로고 미등록 — 업로드 시 이 법인에만 저장됩니다."
            )
        self._refresh_logo_preview(rec.tenant_id)

    def _create_new(self) -> None:
        self._selected_id = None
        self._id_var.set("")
        self._name_var.set("")
        self._name_ko_var.set("")
        self._login_var.set("")
        self._notes_var.set("")
        self._logo_status.configure(text="신규 법인을 저장한 뒤 법인별 로고를 업로드할 수 있습니다.")
        self._refresh_logo_preview(None)

    def _create_new_save(self) -> None:
        try:
            rec = create_tenant(
                tenant_id=self._id_var.get(),
                display_name=self._name_var.get(),
                login_id=self._login_var.get(),
                display_name_ko=self._name_ko_var.get(),
                notes=self._notes_var.get(),
            )
        except ValueError as exc:
            messagebox.showwarning("입력 오류", str(exc), parent=self.winfo_toplevel())
            return
        self._selected_id = rec.tenant_id
        self.refresh()
        self._status_var.set(f"등록됨: {rec.display_name}")

    def _save(self) -> None:
        if not self._selected_id:
            err = validate_tenant_id(self._id_var.get())
            if err:
                messagebox.showwarning("입력 오류", err, parent=self.winfo_toplevel())
                return
            self._create_new_save()
            return
        try:
            update_tenant(
                self._selected_id,
                display_name=self._name_var.get(),
                login_id=self._login_var.get(),
                display_name_ko=self._name_ko_var.get(),
                notes=self._notes_var.get(),
            )
        except ValueError as exc:
            messagebox.showwarning("입력 오류", str(exc), parent=self.winfo_toplevel())
            return
        self.refresh()
        self._status_var.set("저장되었습니다.")
        self._notify_changed()

    def _activate_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo("선택 없음", "목록에서 법인을 선택하세요.", parent=self.winfo_toplevel())
            return
        try:
            rec = set_active_tenant(self._selected_id)
        except ValueError as exc:
            messagebox.showwarning("안내", str(exc), parent=self.winfo_toplevel())
            return
        self.refresh()
        self._status_var.set(f"「{rec.display_name}」(으)로 화면이 전환되었습니다.")
        self._notify_changed()

    def _upload_logo(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(
                "법인 선택",
                "먼저 법인을 선택하거나 신규 등록·저장하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        rec = get_tenant(self._selected_id)
        entity_name = rec.display_name if rec else self._selected_id
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title=f"「{entity_name}」 법인 로고 선택",
            filetypes=[
                ("이미지", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("모든 파일", "*.*"),
            ],
        )
        if not path:
            return
        try:
            saved = save_tenant_logo(self._selected_id, Path(path))
        except (ValueError, OSError) as exc:
            messagebox.showerror("업로드 실패", str(exc), parent=self.winfo_toplevel())
            return
        self._logo_status.configure(
            text=f"「{saved.display_name}」 전용 로고 저장됨: {saved.logo_filename}"
        )
        self._refresh_logo_preview(self._selected_id)
        if self._selected_id == get_active_tenant_id():
            self._notify_changed()
        self.refresh()

    def _clear_logo(self) -> None:
        if not self._selected_id:
            return
        rec = get_tenant(self._selected_id)
        name = rec.display_name if rec else self._selected_id
        if not messagebox.askyesno(
            "로고 제거",
            f"「{name}」 법인의 로고를 제거할까요?\n(다른 법인 로고에는 영향 없습니다.)",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            clear_tenant_logo(self._selected_id)
        except ValueError as exc:
            messagebox.showwarning("안내", str(exc), parent=self.winfo_toplevel())
            return
        self._logo_status.configure(text=f"「{name}」 로고 제거됨 (기본 COSS 로고 사용)")
        self._refresh_logo_preview(self._selected_id)
        if self._selected_id == get_active_tenant_id():
            self._notify_changed()
        self.refresh()

    def _delete(self) -> None:
        if not self._selected_id:
            return
        if not messagebox.askyesno(
            "법인 삭제",
            f"「{self._name_var.get()}」 법인을 삭제할까요?\n로고·설정이 함께 삭제됩니다.",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            delete_tenant(self._selected_id)
        except ValueError as exc:
            messagebox.showwarning("안내", str(exc), parent=self.winfo_toplevel())
            return
        self._selected_id = None
        self._create_new()
        self.refresh()
        self._notify_changed()

    def _notify_changed(self) -> None:
        if self._on_tenant_changed:
            self._on_tenant_changed()

