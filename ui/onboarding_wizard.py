"""
ui/onboarding_wizard.py - 첫 로그인 법인 설정 마법사
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from core.roles import ROLE_ADMIN
from core.session_service import get_session
from core.tenant_store import (
    get_tenant,
    mark_onboarding_completed,
    save_tenant_logo,
    tenant_has_custom_logo,
    tenant_needs_onboarding,
    update_tenant,
)
from ui.brand_assets import logo_photoimage
from ui.theme import COLORS, FONT, FONT_BODY

OnComplete = Callable[[], None]


def should_show_tenant_onboarding() -> bool:
    """관리자 + 미완료 테넌트 설정 시 온보딩 표시."""
    sess = get_session()
    if sess is None or sess.role != ROLE_ADMIN:
        return False
    return tenant_needs_onboarding(sess.tenant_id)


class TenantOnboardingDialog(tk.Toplevel):
    """첫 로그인 후 법인 로고·기본 정보 설정."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_complete: OnComplete | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_complete = on_complete
        sess = get_session()
        if sess is None:
            self.destroy()
            return
        self._tenant_id = sess.tenant_id
        rec = get_tenant(self._tenant_id)
        if rec is None:
            self.destroy()
            return

        self.title("법인 초기 설정")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        self._photo_refs: list[tk.PhotoImage] = []
        self._logo_path: Path | None = None
        self._name_var = tk.StringVar(value=rec.display_name)
        self._name_ko_var = tk.StringVar(value=rec.display_name_ko)
        self._contact_var = tk.StringVar(value=rec.contact)
        self._site_var = tk.StringVar(value=rec.default_site)
        self._status_var = tk.StringVar(value="")

        tk.Label(
            self,
            text="법인 초기 설정",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
        ).pack(anchor=tk.W, padx=28, pady=(24, 4))

        tk.Label(
            self,
            text="첫 로그인입니다. 법인 로고와 기본 정보를 등록해 주세요.\n"
            "설정은 해당 법인 플랫폼 홈에 반영됩니다.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=FONT_BODY,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=28, pady=(0, 16))

        form = tk.Frame(self, bg=COLORS["bg"], padx=28)
        form.pack(fill=tk.X)
        form.grid_columnconfigure(1, weight=1)

        self._row(form, 0, "표시명", self._name_var)
        self._row(form, 1, "법인명(한글)", self._name_ko_var)
        self._row(form, 2, "담당 연락처", self._contact_var)
        self._row(form, 3, "기본 사업장", self._site_var, hint="(선택)")

        logo_frame = ttk.LabelFrame(form, text="법인 로고", padding=10)
        logo_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(14, 0))
        logo_frame.grid_columnconfigure(1, weight=1)

        self._logo_preview_host = tk.Frame(logo_frame, bg=COLORS["card"], width=120, height=72)
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

        logo_btns = ttk.Frame(logo_frame)
        logo_btns.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(logo_btns, text="로고 선택…", command=self._pick_logo).pack(anchor=tk.W)

        self._logo_hint = ttk.Label(
            logo_frame,
            text="PNG·JPG·GIF·WEBP (권장: 가로 400px 이상)",
            font=(FONT, 8),
            foreground=COLORS["muted"],
        )
        self._logo_hint.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))

        if tenant_has_custom_logo(self._tenant_id):
            self._refresh_logo_preview()

        tk.Label(
            self,
            textvariable=self._status_var,
            bg=COLORS["bg"],
            fg="#B91C1C",
            font=(FONT, 9),
        ).pack(anchor=tk.W, padx=28, pady=(10, 0))

        btn_row = tk.Frame(self, bg=COLORS["bg"], padx=28, pady=20)
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="나중에", command=self._skip).pack(side=tk.LEFT)
        tk.Button(
            btn_row,
            text="저장하고 시작",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._save,
        ).pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._skip)
        self._center_on(parent)

    def _row(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        var: tk.StringVar,
        *,
        hint: str = "",
    ) -> None:
        tk.Label(parent, text=label, bg=COLORS["bg"], font=FONT_BODY, width=12, anchor=tk.W).grid(
            row=row, column=0, sticky="w", pady=5
        )
        ttk.Entry(parent, textvariable=var, width=36).grid(row=row, column=1, sticky=tk.EW, pady=5)
        if hint:
            tk.Label(parent, text=hint, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 8)).grid(
                row=row, column=2, sticky="w", padx=(6, 0)
            )

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="법인 로고 선택",
            filetypes=[
                ("이미지", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("모든 파일", "*.*"),
            ],
        )
        if not path:
            return
        self._logo_path = Path(path)
        self._refresh_logo_preview(path=self._logo_path)

    def _refresh_logo_preview(self, *, path: Path | None = None) -> None:
        for child in self._logo_preview_host.winfo_children():
            child.destroy()
        src = path
        if src is None:
            rec = get_tenant(self._tenant_id)
            if rec and rec.logo_path:
                src = rec.logo_path
        if src is None or not src.is_file():
            self._logo_preview_label = tk.Label(
                self._logo_preview_host,
                text="미리보기",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=(FONT, 8),
            )
            self._logo_preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            return
        photo = logo_photoimage(
            self._logo_preview_host,
            self._photo_refs,
            max_width=110,
            variant="light",
            logo_path=src,
            blend_bg=COLORS["card"],
        )
        if photo:
            lbl = tk.Label(
                self._logo_preview_host,
                image=photo,
                bg=COLORS["card"],
                bd=0,
                highlightthickness=0,
            )
            lbl.image = photo
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _skip(self) -> None:
        try:
            mark_onboarding_completed(self._tenant_id)
        except ValueError:
            pass
        self._finish()

    def _save(self) -> None:
        self._status_var.set("")
        name = self._name_var.get().strip()
        if not name:
            self._status_var.set("표시명을 입력하세요.")
            return
        try:
            update_tenant(
                self._tenant_id,
                display_name=name,
                display_name_ko=self._name_ko_var.get().strip(),
                contact=self._contact_var.get().strip(),
                default_site=self._site_var.get().strip(),
            )
            if self._logo_path is not None:
                save_tenant_logo(self._tenant_id, self._logo_path)
            mark_onboarding_completed(self._tenant_id)
        except (ValueError, OSError) as exc:
            self._status_var.set(str(exc))
            return
        self._finish()

    def _finish(self) -> None:
        self.grab_release()
        self.destroy()
        if self._on_complete:
            self._on_complete()


def show_tenant_onboarding_if_needed(parent: tk.Misc, *, on_complete: OnComplete) -> bool:
    """온보딩 필요 시 다이얼로그 표시. 표시했으면 True."""
    if not should_show_tenant_onboarding():
        return False
    TenantOnboardingDialog(parent, on_complete=on_complete)
    return True
