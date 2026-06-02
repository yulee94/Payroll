"""
ui/hr_onboarding_panel.py - 입·퇴사 절차·체크리스트·알림 (전용 UI)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from core.hr import service as hr_svc
from ui.theme import COLORS, FONT
from ui.wheel_scroll import bind_local_wheel


def _status_fg(status: str) -> str:
    if status in ("지연", "위험"):
        return "#DC2626"
    if status in ("주의", "대기"):
        return "#D97706"
    if status == "완료":
        return "#059669"
    return COLORS["text"]


class HrOnboardingPanel(tk.Frame):
    """입·퇴사 케이스 목록 + 단계별 체크리스트 + 담당자 알림 연동."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_roster_synced: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_roster_synced = on_roster_synced
        self._cases: list[dict[str, Any]] = []
        self._selected_case_id: str | None = None
        self._detail_var = tk.StringVar(value="케이스를 선택하세요.")
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        guide = tk.Frame(self, bg="#ECFDF5", highlightbackground="#99F6E4", highlightthickness=1)
        guide.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            guide,
            text=(
                "입·퇴사 등록 시 절차·필수서류 체크리스트가 자동 생성됩니다. "
                "4대보험 취득/상실신고 등 법정 항목은 ⚠ 표시 · 지연 시 인사·부서장에게 알림·할 일이 발송됩니다. "
                "「명부 등록」/「명부 퇴사·퇴사일 반영」 완료 시 직원 명부에 자동 반영됩니다. "
                "입사 시 Bitween 신호등(주민번호) 조회 · 퇴사 시 신호등 등록으로 타 법인 채용 참고가 가능합니다."
            ),
            bg="#ECFDF5",
            fg="#0F766E",
            font=(FONT, 9),
            wraplength=820,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12, pady=10)

        body = tk.Frame(self, bg=COLORS["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)

        # --- 케이스 목록 ---
        left = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        tk.Label(left, text="입·퇴사 케이스", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        case_wrap = tk.Frame(left, bg=COLORS["card"])
        case_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        case_wrap.grid_rowconfigure(0, weight=1)
        case_wrap.grid_columnconfigure(0, weight=1)

        case_cols = ("employee_name", "process_type", "target_date", "progress", "status")
        self._case_tree = ttk.Treeview(case_wrap, columns=case_cols, show="headings", selectmode="browse", height=10)
        for col, label, w in (
            ("employee_name", "성명", 72),
            ("process_type", "구분", 44),
            ("target_date", "예정일", 78),
            ("progress", "진행", 44),
            ("status", "상태", 52),
        ):
            self._case_tree.heading(col, text=label)
            self._case_tree.column(col, width=w, minwidth=36)
        cv = ttk.Scrollbar(case_wrap, orient=tk.VERTICAL, command=self._case_tree.yview)
        self._case_tree.configure(yscrollcommand=cv.set)
        self._case_tree.grid(row=0, column=0, sticky="nsew")
        cv.grid(row=0, column=1, sticky="ns")
        self._case_tree.bind("<<TreeviewSelect>>", self._on_case_select)
        bind_local_wheel(self._case_tree)

        # --- 체크리스트 + 상세 ---
        right = tk.Frame(body, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        summary = tk.Frame(right, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._summary_lbl = tk.Label(
            summary,
            textvariable=self._detail_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT, 9),
            justify=tk.LEFT,
            anchor=tk.W,
            wraplength=520,
        )
        self._summary_lbl.pack(fill=tk.X, padx=14, pady=10)

        task_card = tk.Frame(right, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        task_card.grid(row=1, column=0, sticky="nsew")
        task_card.grid_rowconfigure(2, weight=1)
        task_card.grid_columnconfigure(0, weight=1)

        head_row = tk.Frame(task_card, bg=COLORS["card"])
        head_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        tk.Label(head_row, text="절차 · 필수서류 · 담당", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(
            side=tk.LEFT
        )
        tk.Button(
            head_row,
            text="✓ 선택 항목 완료",
            bg="#0D9488",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._complete_selected_task,
        ).pack(side=tk.RIGHT)

        tk.Label(
            task_card,
            text="⚠ = 법정·4대보험 등 누락 시 과태료 위험  ·  지연 시 담당자·부서장·인사에게 알림",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).grid(row=1, column=0, sticky="w", padx=12)

        task_wrap = tk.Frame(task_card, bg=COLORS["card"])
        task_wrap.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 10))
        task_wrap.grid_rowconfigure(0, weight=1)
        task_wrap.grid_columnconfigure(0, weight=1)

        task_cols = ("title", "document", "assignee_name", "due_date", "status")
        self._task_tree = ttk.Treeview(task_wrap, columns=task_cols, show="headings", selectmode="browse", height=12)
        for col, label, w in (
            ("title", "절차", 140),
            ("document", "필수서류", 100),
            ("assignee_name", "담당", 64),
            ("due_date", "마감", 78),
            ("status", "상태", 48),
        ):
            self._task_tree.heading(col, text=label)
            self._task_tree.column(col, width=w, minwidth=40, stretch=(col == "title"))
        tv = ttk.Scrollbar(task_wrap, orient=tk.VERTICAL, command=self._task_tree.yview)
        self._task_tree.configure(yscrollcommand=tv.set)
        self._task_tree.grid(row=0, column=0, sticky="nsew")
        tv.grid(row=0, column=1, sticky="ns")
        self._task_tree.bind("<<TreeviewSelect>>", self._on_task_select)
        bind_local_wheel(self._task_tree)

        self._task_note_var = tk.StringVar(value="")
        tk.Label(
            task_card,
            textvariable=self._task_note_var,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=520,
            justify=tk.LEFT,
            anchor=tk.W,
        ).grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

    def refresh(self) -> None:
        hr_svc.ensure_seed()
        self._cases = hr_svc.list_onboarding_cases()
        self._reload_cases()
        if self._selected_case_id:
            if not any(str(c.get("id")) == self._selected_case_id for c in self._cases):
                self._selected_case_id = None
        if self._selected_case_id:
            self._select_case(self._selected_case_id)
        elif self._cases:
            self._case_tree.selection_set(str(self._cases[0].get("id")))
            self._select_case(str(self._cases[0].get("id")))

    def _reload_cases(self) -> None:
        tree = self._case_tree
        tree.delete(*tree.get_children())
        for case in self._cases:
            row = hr_svc.onboarding_summary_row(case)
            cid = str(row.get("id") or "")
            overdue = int(row.get("overdue_count") or 0)
            status = str(row.get("status") or "")
            if overdue:
                status = f"지연{overdue}"
            tree.insert(
                "",
                tk.END,
                iid=cid,
                values=(
                    row.get("employee_name"),
                    row.get("process_type"),
                    row.get("target_date"),
                    row.get("progress"),
                    status,
                ),
            )

    def _find_case(self, case_id: str) -> dict[str, Any] | None:
        for c in self._cases:
            if str(c.get("id")) == case_id:
                return c
        return hr_svc.get_onboarding_case(case_id)

    def _on_case_select(self, _event: tk.Event | None = None) -> None:
        sel = self._case_tree.selection()
        if sel:
            self._select_case(sel[0])

    def _select_case(self, case_id: str) -> None:
        self._selected_case_id = case_id
        case = self._find_case(case_id)
        if not case:
            return
        overdue = int(case.get("overdue_count") or 0)
        critical = sum(
            1 for t in case.get("tasks") or [] if t.get("critical") and t.get("status") != "완료"
        )
        lines = [
            f"【{case.get('employee_name')}】 {case.get('process_type')} · {case.get('target_date')}",
            f"부서: {case.get('department')}  ·  사업장: {case.get('site_name') or '-'}",
            f"진행 {case.get('progress_pct', 0)}% ({case.get('tasks_done')}/{case.get('tasks_total')})  ·  상태: {case.get('status')}",
        ]
        if critical:
            lines.append(f"⚠ 법정·4대보험 미완료 {critical}건")
        if overdue:
            lines.append(f"⚠ 지연 {overdue}건 — 담당자·인사·부서장 알림 발송")
        note = str(case.get("note") or "").strip()
        if note:
            lines.append(f"비고: {note}")
        if case.get("roster_synced"):
            lines.append(f"✓ 명부 반영 ({case.get('roster_sync_at') or '-'})")
        elif case.get("roster_sync_pending"):
            lines.append(f"⚠ 명부 미반영: {case.get('roster_sync_message', '')}")
        sig_line = hr_svc.signal_summary_for_case(case)
        if sig_line:
            lines.append(sig_line)
        self._detail_var.set("\n".join(lines))
        self._reload_tasks(case)

    def _reload_tasks(self, case: dict[str, Any]) -> None:
        tree = self._task_tree
        tree.delete(*tree.get_children())
        for task in case.get("tasks") or []:
            tid = str(task.get("id") or "")
            title = str(task.get("title") or "")
            if task.get("critical"):
                title = f"⚠ {title}"
            tree.insert(
                "",
                tk.END,
                iid=tid,
                values=(
                    title,
                    task.get("document"),
                    task.get("assignee_name"),
                    task.get("due_date"),
                    task.get("status"),
                ),
            )

    def _on_task_select(self, _event: tk.Event | None = None) -> None:
        if not self._selected_case_id:
            return
        sel = self._task_tree.selection()
        if not sel:
            self._task_note_var.set("")
            return
        case = self._find_case(self._selected_case_id)
        if not case:
            return
        task = next((t for t in case.get("tasks") or [] if str(t.get("id")) == sel[0]), None)
        if not task:
            return
        parts = []
        if task.get("legal_note"):
            parts.append(f"※ {task.get('legal_note')}")
        if task.get("category"):
            parts.append(f"분류: {task.get('category')}")
        if task.get("note"):
            parts.append(f"메모: {task.get('note')}")
        if task.get("completed_at"):
            parts.append(f"완료일: {task.get('completed_at')}")
        self._task_note_var.set("  ·  ".join(parts) if parts else "법정·내부 절차 항목입니다.")

    def _complete_selected_task(self) -> None:
        if not self._selected_case_id:
            messagebox.showinfo("입·퇴사", "케이스를 선택하세요.")
            return
        sel = self._task_tree.selection()
        if not sel:
            messagebox.showinfo("입·퇴사", "완료할 절차를 선택하세요.")
            return
        case = self._find_case(self._selected_case_id)
        task = next((t for t in (case or {}).get("tasks") or [] if str(t.get("id")) == sel[0]), None)
        if not task:
            return
        code = str(task.get("code") or "")

        if code == "resign_signal_register":
            from ui.hr_signal_panel import ask_resign_signal_registration

            reg = ask_resign_signal_registration(self)
            if not reg:
                return
            severity, category, summary = reg
            try:
                hr_svc.register_case_resign_signal(
                    self._selected_case_id,
                    severity=severity,
                    category=category,
                    summary=summary,
                )
            except ValueError as exc:
                messagebox.showwarning("신호등", str(exc), parent=self.winfo_toplevel())
                return

        if code == "hire_signal_check":
            case = self._find_case(self._selected_case_id)
            snap = (case or {}).get("signal_snapshot") or {}
            if snap.get("status") == "unknown":
                if messagebox.askyesno(
                    "신호등 조회",
                    "주민등록번호가 없어 신호등을 조회하지 못했습니다.\n"
                    "지금 주민번호를 입력해 다시 조회할까요?",
                    parent=self.winfo_toplevel(),
                ):
                    raw = simpledialog.askstring(
                        "주민등록번호",
                        "13자리 주민등록번호 (- 없이 가능):",
                        parent=self.winfo_toplevel(),
                    )
                    if raw:
                        try:
                            hr_svc.update_case_resident_rrn(self._selected_case_id, raw)
                        except ValueError as exc:
                            messagebox.showwarning("신호등", str(exc), parent=self.winfo_toplevel())
                            return
                        self.refresh()
                        case = self._find_case(self._selected_case_id)
            snap = (case or {}).get("signal_snapshot") or {}
            if snap.get("status") == "red":
                if not messagebox.askyesno(
                    "신호등 위험",
                    "🔴 위험 신호가 조회되었습니다. 그래도 입사 절차를 계속 진행할까요?",
                    parent=self.winfo_toplevel(),
                ):
                    return
            elif snap.get("status") == "yellow":
                messagebox.showinfo(
                    "신호등 주의",
                    "🟡 주의 신호 — 타 법인 퇴사 이력을 확인한 뒤 진행하세요.",
                    parent=self.winfo_toplevel(),
                )

        note = simpledialog.askstring("완료 처리", "메모 (선택):", parent=self.winfo_toplevel())
        case, sync = hr_svc.complete_onboarding_task(self._selected_case_id, sel[0], note=note or "")
        self.refresh()
        if sync and sync.get("action") in ("created", "updated"):
            if self._on_roster_synced:
                self._on_roster_synced()
            messagebox.showinfo("입·퇴사 · 명부", sync.get("message") or "명부에 반영되었습니다.")
        elif sync and sync.get("action") == "not_found":
            messagebox.showwarning("명부 미반영", sync.get("message") or "명부에서 직원을 찾을 수 없습니다.")
        else:
            messagebox.showinfo("입·퇴사", "완료 처리되었습니다.")

    def add_case_dialog(self) -> None:
        fields = hr_svc.form_fields("onboarding")
        values: dict[str, str] = {}
        for key, label, required in fields:
            val = simpledialog.askstring(
                "입·퇴사 등록",
                f"{label}{' *' if required else ''}:",
                parent=self.winfo_toplevel(),
            )
            if val is None:
                return
            if required and not str(val).strip():
                messagebox.showwarning("입·퇴사", f"{label}을(를) 입력하세요.")
                return
            values[key] = str(val).strip()
        try:
            case = hr_svc.create_onboarding_case(values)
        except Exception as exc:
            messagebox.showerror("입·퇴사", str(exc))
            return
        self.refresh()
        cid = str(case.get("id") or "")
        if cid:
            self._case_tree.selection_set(cid)
            self._select_case(cid)
        messagebox.showinfo(
            "입·퇴사",
            f"절차가 생성되었습니다.\n체크리스트 {len(case.get('tasks') or [])}건 · "
            "담당자에게 알림·할 일이 등록되었습니다.",
        )


def build_hr_onboarding_panel(parent: tk.Misc) -> HrOnboardingPanel:
    return HrOnboardingPanel(parent)
