"""
ui/health_checkup_panel.py - 건강검진 대상 조회 · 검사기록지 업로드 UI
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from core.hr import health_checkup as hc
from ui.theme import COLORS, FONT, FONT_BODY
from ui.wheel_scroll import bind_local_wheel


def _status_fg(status: str) -> str:
    if status == "completed":
        return "#059669"
    if status == "waived":
        return COLORS["muted"]
    return "#D97706"


class HealthCheckupPanel(tk.Frame):
    """직원 self-check + HR 명단 관리."""

    _SUB_TABS = (
        ("employee", "내 검진 대상"),
        ("hr", "HR · 명단 관리"),
    )

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._sub_tab = "employee"
        self._sub_btns: dict[str, tk.Button] = {}
        self._ident_var = tk.StringVar()
        self._result_var = tk.StringVar(value="사번 또는 주민등록번호를 입력하고 조회하세요.")
        self._lookup_records: list[dict[str, Any]] = []
        self._selected_elig_id: str | None = None
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#ECFEFF", highlightbackground="#A5F3FC", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=hc.help_text_ko().replace("\n", " "),
            bg="#ECFEFF",
            fg="#0E7490",
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

        self._employee_host = tk.Frame(self, bg=COLORS["bg"])
        self._hr_host = tk.Frame(self, bg=COLORS["bg"])
        self._build_employee_view(self._employee_host)
        self._build_hr_view(self._hr_host)
        self._select_sub("employee")

    def _select_sub(self, tab_id: str) -> None:
        self._sub_tab = tab_id
        accent = "#0D9488"
        for tid, btn in self._sub_btns.items():
            if tid == tab_id:
                btn.configure(bg=accent, fg="#FFFFFF", font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10))
        self._employee_host.grid_remove()
        self._hr_host.grid_remove()
        if tab_id == "employee":
            self._employee_host.grid(row=2, column=0, sticky="nsew")
        else:
            self._hr_host.grid(row=2, column=0, sticky="nsew")
            self._reload_hr_list()

    def _build_employee_view(self, parent: tk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        search_card = tk.Frame(
            parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1
        )
        search_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_inner = tk.Frame(search_card, bg=COLORS["card"], padx=16, pady=14)
        search_inner.pack(fill=tk.X)

        tk.Label(
            search_inner,
            text="내 검진 대상 여부",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
        ).pack(anchor=tk.W)

        row = tk.Frame(search_inner, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(row, text="사번 / 주민번호", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10)).pack(
            side=tk.LEFT
        )
        ttk.Entry(row, textvariable=self._ident_var, width=28, font=FONT_BODY).pack(side=tk.LEFT, padx=(8, 8))
        tk.Button(
            row,
            text="조회",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._lookup,
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            row,
            text="NHIS 공식 사이트",
            bg=COLORS["card"],
            fg="#0369A1",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open(hc.NHIS_PUBLIC_URL),
        ).pack(side=tk.LEFT)

        tk.Label(
            search_inner,
            textvariable=self._result_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10),
            wraplength=760,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 0))

        body = tk.Frame(parent, bg=COLORS["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        left = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        tk.Label(left, text="검진 정보", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        wrap = tk.Frame(left, bg=COLORS["card"])
        wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        cols = ("checkup_type_label", "period_start", "period_end", "status_label")
        self._emp_tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse", height=8)
        for col, label, w in (
            ("checkup_type_label", "유형", 120),
            ("period_start", "시작", 88),
            ("period_end", "마감", 88),
            ("status_label", "상태", 72),
        ):
            self._emp_tree.heading(col, text=label)
            self._emp_tree.column(col, width=w, minwidth=40)
        sv = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self._emp_tree.yview)
        self._emp_tree.configure(yscrollcommand=sv.set)
        self._emp_tree.grid(row=0, column=0, sticky="nsew")
        sv.grid(row=0, column=1, sticky="ns")
        self._emp_tree.bind("<<TreeviewSelect>>", self._on_emp_select)
        bind_local_wheel(self._emp_tree)

        self._detail_lbl = tk.Label(
            left,
            text="",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=340,
            justify=tk.LEFT,
            anchor=tk.W,
        )
        self._detail_lbl.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        right = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        head = tk.Frame(right, bg=COLORS["card"])
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        tk.Label(head, text="검사기록지 업로드", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            side=tk.LEFT
        )
        tk.Button(
            head,
            text="📎 결과지 업로드",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._upload_result,
        ).pack(side=tk.RIGHT)

        tk.Label(
            right,
            text="수검 완료 후 PDF 또는 이미지 파일을 업로드하세요. (기간 내 제출)",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).grid(row=1, column=0, sticky="w", padx=12)

        up_wrap = tk.Frame(right, bg=COLORS["card"])
        up_wrap.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 10))
        up_wrap.grid_rowconfigure(0, weight=1)
        up_wrap.grid_columnconfigure(0, weight=1)

        ucols = ("checkup_date", "original_filename", "uploaded_at")
        self._upload_tree = ttk.Treeview(up_wrap, columns=ucols, show="headings", selectmode="browse", height=8)
        for col, label, w in (
            ("checkup_date", "수검일", 88),
            ("original_filename", "파일", 160),
            ("uploaded_at", "업로드", 120),
        ):
            self._upload_tree.heading(col, text=label)
            self._upload_tree.column(col, width=w, minwidth=40)
        usv = ttk.Scrollbar(up_wrap, orient=tk.VERTICAL, command=self._upload_tree.yview)
        self._upload_tree.configure(yscrollcommand=usv.set)
        self._upload_tree.grid(row=0, column=0, sticky="nsew")
        usv.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._upload_tree)

    def _build_hr_view(self, parent: tk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=0)
        parent.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        inner = tk.Frame(toolbar, bg=COLORS["card"], padx=14, pady=10)
        inner.pack(fill=tk.X)

        tk.Label(
            inner,
            text="HR · 검진 대상 명단 (NHIS CSV 가져오기 / 수동 등록)",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).pack(side=tk.LEFT)

        tk.Button(
            inner,
            text="CSV 가져오기",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._import_csv,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(
            inner,
            text="＋ 수동 등록",
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._manual_add,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(
            inner,
            text="선택 삭제",
            bg=COLORS["card"],
            fg="#DC2626",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._delete_selected,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        self._meta_var = tk.StringVar(value="")
        tk.Label(
            inner,
            textvariable=self._meta_var,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).pack(side=tk.LEFT, padx=(16, 0))

        list_card = tk.Frame(
            parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1
        )
        list_card.grid(row=1, column=0, sticky="nsew")
        list_card.grid_rowconfigure(1, weight=1)
        list_card.grid_columnconfigure(0, weight=1)

        tk.Label(
            list_card,
            text="등록된 대상자",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        wrap = tk.Frame(list_card, bg=COLORS["card"])
        wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        hcols = (
            "employee_no",
            "employee_name",
            "checkup_type_label",
            "period_end",
            "special_exam_types",
            "status_label",
        )
        self._hr_tree = ttk.Treeview(wrap, columns=hcols, show="headings", selectmode="browse", height=14)
        for col, label, w in (
            ("employee_no", "사번", 72),
            ("employee_name", "성명", 72),
            ("checkup_type_label", "유형", 100),
            ("period_end", "마감", 88),
            ("special_exam_types", "특수검사", 140),
            ("status_label", "상태", 64),
        ):
            self._hr_tree.heading(col, text=label)
            self._hr_tree.column(col, width=w, minwidth=36)
        hsv = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self._hr_tree.yview)
        self._hr_tree.configure(yscrollcommand=hsv.set)
        self._hr_tree.grid(row=0, column=0, sticky="nsew")
        hsv.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._hr_tree)

        upload_card = tk.Frame(
            parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1
        )
        upload_card.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        upload_card.grid_rowconfigure(1, weight=1)
        upload_card.grid_columnconfigure(0, weight=1)

        tk.Label(
            upload_card,
            text="제출된 검사기록지",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        uwrap = tk.Frame(upload_card, bg=COLORS["card"])
        uwrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        uwrap.grid_rowconfigure(0, weight=1)
        uwrap.grid_columnconfigure(0, weight=1)

        ucols = ("employee_name", "checkup_date", "original_filename", "uploaded_at")
        self._hr_upload_tree = ttk.Treeview(uwrap, columns=ucols, show="headings", selectmode="browse", height=5)
        for col, label, w in (
            ("employee_name", "성명", 72),
            ("checkup_date", "수검일", 88),
            ("original_filename", "파일", 180),
            ("uploaded_at", "업로드", 120),
        ):
            self._hr_upload_tree.heading(col, text=label)
            self._hr_upload_tree.column(col, width=w, minwidth=36)
        uhsv = ttk.Scrollbar(uwrap, orient=tk.VERTICAL, command=self._hr_upload_tree.yview)
        self._hr_upload_tree.configure(yscrollcommand=uhsv.set)
        self._hr_upload_tree.grid(row=0, column=0, sticky="nsew")
        uhsv.grid(row=0, column=1, sticky="ns")
        bind_local_wheel(self._hr_upload_tree)

    def refresh(self) -> None:
        if self._sub_tab == "hr":
            self._reload_hr_list()
        elif self._ident_var.get().strip():
            self._lookup()

    def _lookup(self) -> None:
        ident = self._ident_var.get().strip()
        if not ident:
            messagebox.showwarning("조회", "사번 또는 주민등록번호를 입력하세요.", parent=self.winfo_toplevel())
            return
        result = hc.lookup_eligibility(None, ident)
        self._lookup_records = list(result.records)
        self._result_var.set(result.message)
        self._emp_tree.delete(*self._emp_tree.get_children())
        self._upload_tree.delete(*self._upload_tree.get_children())
        self._selected_elig_id = None
        self._detail_lbl.configure(text="")

        for rec in self._lookup_records:
            iid = str(rec.get("id"))
            self._emp_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    rec.get("checkup_type_label", ""),
                    rec.get("period_start", ""),
                    rec.get("period_end", ""),
                    rec.get("status_label", ""),
                ),
            )
        for up in result.uploads:
            self._upload_tree.insert(
                "",
                tk.END,
                values=(
                    up.get("checkup_date", ""),
                    up.get("original_filename", ""),
                    (up.get("uploaded_at") or "")[:16],
                ),
            )
        if result.eligible and self._lookup_records:
            self._emp_tree.selection_set(str(self._lookup_records[0].get("id")))
            self._on_emp_select()

    def _on_emp_select(self, _event: Any = None) -> None:
        sel = self._emp_tree.selection()
        if not sel:
            return
        eid = sel[0]
        self._selected_elig_id = eid
        rec = next((r for r in self._lookup_records if str(r.get("id")) == eid), None)
        if not rec:
            return
        exams = rec.get("special_exam_types") or []
        exam_txt = ", ".join(exams) if exams else "(없음)"
        lines = [
            f"성명: {rec.get('employee_name', '')}  사번: {rec.get('employee_no', '')}",
            f"검진 유형: {rec.get('checkup_type_label', '')}",
            f"기간: {rec.get('period_start', '')} ~ {rec.get('period_end', '')}",
            f"특수검사(특별검사): {exam_txt}",
            f"상태: {rec.get('status_label', '')}",
        ]
        if rec.get("note"):
            lines.append(f"비고: {rec.get('note')}")
        self._detail_lbl.configure(text="\n".join(lines), fg=_status_fg(str(rec.get("status", ""))))

    def _upload_result(self) -> None:
        if not self._selected_elig_id:
            messagebox.showwarning(
                "업로드",
                "먼저 검진 대상을 조회하고 항목을 선택하세요.",
                parent=self.winfo_toplevel(),
            )
            return
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="검사기록지 선택",
            filetypes=[
                ("문서·이미지", "*.pdf *.png *.jpg *.jpeg *.gif *.webp *.tif *.tiff"),
                ("모든 파일", "*.*"),
            ],
        )
        if not path:
            return
        from datetime import date

        checkup_date = simpledialog.askstring(
            "수검일",
            "수검일 (YYYY-MM-DD):",
            parent=self.winfo_toplevel(),
            initialvalue=date.today().isoformat(),
        )
        if checkup_date is None:
            return
        if not checkup_date.strip():
            checkup_date = date.today().isoformat()
        try:
            hc.save_upload(
                source_file=path,
                eligibility_id=self._selected_elig_id,
                checkup_date=checkup_date.strip(),
            )
            messagebox.showinfo("업로드", "검사기록지가 저장되었습니다.", parent=self.winfo_toplevel())
            self._lookup()
        except (OSError, ValueError) as exc:
            messagebox.showerror("업로드 실패", str(exc), parent=self.winfo_toplevel())

    def _reload_hr_list(self) -> None:
        meta = hc.import_meta()
        parts = []
        if meta.get("last_import_at"):
            parts.append(f"마지막 import: {meta['last_import_at'][:16]} ({meta.get('last_import_source', '')})")
        if hc.is_api_connected():
            parts.append("API 연동: ON")
        else:
            parts.append("API 연동: OFF (import/수동)")
        self._meta_var.set(" · ".join(parts))

        self._hr_tree.delete(*self._hr_tree.get_children())
        for row in hc.list_eligibility():
            exams = row.get("special_exam_types") or []
            exam_str = ", ".join(exams) if exams else ""
            self._hr_tree.insert(
                "",
                tk.END,
                iid=str(row.get("id")),
                values=(
                    row.get("employee_no", ""),
                    row.get("employee_name", ""),
                    row.get("checkup_type_label", ""),
                    row.get("period_end", ""),
                    exam_str,
                    row.get("status_label", ""),
                ),
            )

        self._hr_upload_tree.delete(*self._hr_upload_tree.get_children())
        for up in hc.list_uploads():
            self._hr_upload_tree.insert(
                "",
                tk.END,
                values=(
                    up.get("employee_name", ""),
                    up.get("checkup_date", ""),
                    up.get("original_filename", ""),
                    (up.get("uploaded_at") or "")[:16],
                ),
            )

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="NHIS 검진 대상 CSV",
            filetypes=[("CSV", "*.csv"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        replace = messagebox.askyesno(
            "가져오기 방식",
            "기존 명단을 모두 교체하시겠습니까?\n\n"
            "「예」= 전체 교체  ·  「아니오」= 기존 명단에 추가",
            parent=self.winfo_toplevel(),
        )
        try:
            summary = hc.import_eligibility_csv(path, replace=replace)
            messagebox.showinfo(
                "가져오기 완료",
                f"{summary.get('imported_count', 0)}명의 검진 대상을 등록했습니다.",
                parent=self.winfo_toplevel(),
            )
            self._reload_hr_list()
        except (OSError, ValueError) as exc:
            messagebox.showerror("가져오기 실패", str(exc), parent=self.winfo_toplevel())

    def _manual_add(self) -> None:
        name = simpledialog.askstring("수동 등록", "성명:", parent=self.winfo_toplevel())
        if not name:
            return
        emp_no = simpledialog.askstring("수동 등록", "사번 (선택):", parent=self.winfo_toplevel()) or ""
        rrn = simpledialog.askstring("수동 등록", "주민번호 (선택):", parent=self.winfo_toplevel()) or ""
        ctype = simpledialog.askstring(
            "수동 등록",
            "검진 유형 (general/special 또는 일반/특수):",
            parent=self.winfo_toplevel(),
            initialvalue="general",
        ) or "general"
        start = simpledialog.askstring(
            "수동 등록", "기간 시작 (YYYY-MM-DD):", parent=self.winfo_toplevel()
        ) or ""
        end = simpledialog.askstring(
            "수동 등록", "기간 종료 (YYYY-MM-DD):", parent=self.winfo_toplevel()
        ) or ""
        exams_raw = simpledialog.askstring(
            "수동 등록",
            "특수검사 항목 (쉼표 구분, 없으면 비움):",
            parent=self.winfo_toplevel(),
        ) or ""
        exams = [x.strip() for x in exams_raw.split(",") if x.strip()]
        try:
            hc.add_eligibility_manual(
                employee_no=emp_no,
                employee_name=name,
                rrn=rrn,
                checkup_type=ctype,
                period_start=start,
                period_end=end,
                special_exam_types=exams,
            )
            self._reload_hr_list()
        except ValueError as exc:
            messagebox.showerror("등록 실패", str(exc), parent=self.winfo_toplevel())

    def _delete_selected(self) -> None:
        sel = self._hr_tree.selection()
        if not sel:
            messagebox.showwarning("삭제", "삭제할 대상을 선택하세요.", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno("삭제 확인", "선택한 검진 대상을 삭제하시겠습니까?", parent=self.winfo_toplevel()):
            return
        for eid in sel:
            hc.delete_eligibility(eid)
        self._reload_hr_list()


def build_health_checkup_panel(parent: tk.Misc) -> HealthCheckupPanel:
    return HealthCheckupPanel(parent)
