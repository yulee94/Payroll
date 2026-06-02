"""
ui/workflow_compose_dialog.py - 양식별 기안 작성·결재선·참조
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Any, Callable

from core.group_store import get_group_for_tenant, get_workflow_tenant_id
from core.session_service import require_session, session_tenant_id
from core.workflow.group_directory import (
    build_approval_line_from_template,
    format_group_user_label,
    list_group_users_for_tenant,
)
from core.user_store import list_users_for_tenant
from core.workflow import service as wf_svc
from core.workflow.constants import DOC_TYPE_LABELS, DOC_TYPE_GENERAL
from core.workflow.form_templates import ensure_form_templates, get_template
from core.workflow.forms import (
    DEFAULT_APPROVAL_TEMPLATES,
    build_document_fields,
    get_form_schema,
    get_required_hint,
    validate_form_values,
)
from core.workflow.store import list_departments, list_sites
from ui.approver_picker_dialog import pick_group_users
from ui.approval_line_panel import ApprovalLinePanel
from ui.theme import COLORS, FONT, FONT_BODY
from ui.workflow_theme import WF, flat_button


class WorkflowComposeDialog(tk.Toplevel):
    """양식별 필드 + 결재선 편집 + 상신/임시저장."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        tenant_id: str,
        document_type: str = DOC_TYPE_GENERAL,
        template_id: str = "",
        origin_tenant_id: str = "",
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._origin_tenant = str(origin_tenant_id or tenant_id).strip() or tenant_id
        self._tenant_id = get_workflow_tenant_id(self._origin_tenant) or tenant_id
        self._template_id = str(template_id or "").strip()
        tpl = get_template(self._tenant_id, self._template_id) if self._template_id else None
        if tpl:
            document_type = str(tpl.get("document_type") or document_type)
        self._doc_type = tk.StringVar(value=document_type)
        self._on_saved = on_saved
        self._field_vars: dict[str, tk.Variable] = {}
        self._field_widgets: dict[str, tk.Widget] = {}
        self._approval_rows: list[dict[str, Any]] = []
        self._group_users = list_group_users_for_tenant(self._origin_tenant)
        self._users = [gu.user for gu in self._group_users] or list_users_for_tenant(self._origin_tenant)

        title_suffix = f" — {tpl['name']}" if tpl else ""
        self.title(f"문서 작성{title_suffix}")
        self.geometry("860x760")
        self.minsize(680, 600)
        self.configure(bg=WF["page_bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build_ui()
        self._load_default_approval_line()
        self._rebuild_form_fields()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=WF["page_bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)

        head = tk.Frame(outer, bg=WF["card"], highlightbackground=WF["card_border"], highlightthickness=1)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        inner = tk.Frame(head, bg=WF["card"], padx=16, pady=12)
        inner.pack(fill=tk.X)
        tk.Label(inner, text="양식 작성", bg=WF["card"], fg=COLORS["text"], font=(FONT, 14, "bold")).pack(
            anchor=tk.W
        )
        row = tk.Frame(inner, bg=WF["card"])
        row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(row, text="문서 유형", bg=WF["card"], font=FONT_BODY, width=10, anchor=tk.W).pack(side=tk.LEFT)
        type_combo = ttk.Combobox(
            row,
            textvariable=self._doc_type,
            values=list(DOC_TYPE_LABELS.keys()),
            state="readonly",
            width=40,
        )
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        type_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_type_changed())

        self._hint_lbl = tk.Label(inner, text="", bg=WF["card"], fg=COLORS["muted"], font=(FONT, 9), anchor=tk.W)
        self._hint_lbl.pack(anchor=tk.W, pady=(8, 0))

        paned = ttk.Panedwindow(outer, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        form_wrap = tk.Frame(paned, bg=WF["page_bg"])
        paned.add(form_wrap, weight=3)
        canvas = tk.Canvas(form_wrap, bg=WF["card"], highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(form_wrap, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._form_host = tk.Frame(canvas, bg=WF["card"], padx=16, pady=12)
        self._form_win = canvas.create_window((0, 0), window=self._form_host, anchor=tk.NW)
        self._form_host.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(self._form_win, width=e.width))

        appr_wrap = tk.Frame(paned, bg=WF["page_bg"])
        paned.add(appr_wrap, weight=2)
        appr_card = tk.Frame(appr_wrap, bg=WF["card"], highlightbackground=WF["card_border"], highlightthickness=1)
        appr_card.pack(fill=tk.BOTH, expand=True)
        appr_inner = tk.Frame(appr_card, bg=WF["card"], padx=12, pady=10)
        appr_inner.pack(fill=tk.BOTH, expand=True)
        appr_inner.grid_rowconfigure(1, weight=1)
        appr_inner.grid_columnconfigure(0, weight=1)

        tk.Label(appr_inner, text="결재선", bg=WF["card"], fg=COLORS["text"], font=(FONT, 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        self._approval_panel = ApprovalLinePanel(
            appr_inner,
            group_users=self._group_users,
            users=self._users,
        )
        self._approval_panel.grid(row=1, column=0, sticky="nsew", pady=(8, 6))

        cc_head = tk.Frame(appr_inner, bg=WF["card"])
        cc_head.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        tk.Label(cc_head, text="참조", bg=WF["card"], fg=COLORS["text"], font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        flat_button(cc_head, "＋ 참조인 추가", command=self._add_cc_via_picker, bg=WF["tab_inactive"], padx=8, pady=3).pack(
            side=tk.RIGHT
        )
        flat_button(cc_head, "－", command=self._remove_cc, bg="#FEE2E2", fg="#B91C1C", padx=6, pady=3).pack(side=tk.RIGHT, padx=(0, 4))

        self._cc_list = tk.Listbox(appr_inner, selectmode=tk.SINGLE, height=3, font=FONT_BODY)
        self._cc_list.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._cc_user_ids: list[str] = []

        foot = tk.Frame(outer, bg=WF["page_bg"])
        foot.grid(row=3, column=0, sticky="ew")
        flat_button(foot, "임시저장", command=lambda: self._save(submit=False), bg=WF["tab_inactive"], padx=14, pady=8).pack(
            side=tk.LEFT
        )
        flat_button(foot, "상신", command=lambda: self._save(submit=True), bg=COLORS["accent"], fg="#FFF", padx=20, pady=8).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        flat_button(foot, "취소", command=self.destroy, bg=WF["tab_inactive"], padx=14, pady=8).pack(side=tk.RIGHT)

    def _on_type_changed(self) -> None:
        self._rebuild_form_fields()
        self._load_default_approval_line()

    def _rebuild_form_fields(self) -> None:
        for w in self._form_host.winfo_children():
            w.destroy()
        self._field_vars.clear()
        self._field_widgets.clear()
        dtype = self._doc_type.get()
        tpl = get_template(self._tenant_id, self._template_id) if self._template_id else None
        if tpl and tpl.get("fields"):
            req = sum(1 for f in tpl.get("fields") or [] if isinstance(f, dict) and f.get("required"))
            self._hint_lbl.configure(
                text=f"{tpl.get('name', '')} — 필수 항목 {req}개 · 양식함 전용 필드"
            )
        else:
            self._hint_lbl.configure(text=get_required_hint(dtype))
        today = date.today().isoformat()

        for field in get_form_schema(dtype, self._origin_tenant, template_id=self._template_id):
            tk.Label(
                self._form_host,
                text=f"{field.label}{' *' if field.required else ''}",
                bg=WF["card"],
                fg=COLORS["text"] if field.required else COLORS["muted"],
                font=(FONT, 9),
                anchor=tk.W,
            ).pack(anchor=tk.W, pady=(10, 2))

            if field.field_type == "multiline":
                w = tk.Text(self._form_host, height=3, font=FONT_BODY, wrap=tk.WORD, relief=tk.FLAT, highlightthickness=1)
                w.pack(fill=tk.X)
                self._field_widgets[field.key] = w
            elif field.field_type == "select":
                var = tk.StringVar()
                cb = ttk.Combobox(self._form_host, textvariable=var, values=list(field.options), state="readonly", font=FONT_BODY)
                cb.pack(fill=tk.X)
                self._field_vars[field.key] = var
            else:
                var = tk.StringVar()
                if field.field_type == "date" and field.key in ("period_start", "period_end"):
                    var.set(today)
                ent = tk.Entry(self._form_host, textvariable=var, font=FONT_BODY, relief=tk.FLAT, highlightthickness=1)
                ent.pack(fill=tk.X, ipady=4)
                self._field_vars[field.key] = var

        label = str(tpl.get("name") if (tpl := get_template(self._tenant_id, self._template_id)) else "") or DOC_TYPE_LABELS.get(dtype, dtype)
        if "title" in self._field_vars and not self._field_vars["title"].get().strip():
            self._field_vars["title"].set(f"{label} — ")

    def _collect_values(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, var in self._field_vars.items():
            out[key] = str(var.get()).strip()
        for key, w in self._field_widgets.items():
            if isinstance(w, tk.Text):
                out[key] = w.get("1.0", tk.END).strip()
        return out

    def _load_default_approval_line(self) -> None:
        self._approval_rows.clear()
        dtype = self._doc_type.get()
        amount = 0
        if "total_amount" in self._field_vars:
            try:
                amount = int(str(self._field_vars["total_amount"].get()).replace(",", "") or 0)
            except ValueError:
                amount = 0
        grp = get_group_for_tenant(self._origin_tenant)
        if grp:
            self._approval_rows = build_approval_line_from_template(
                grp.group_id,
                dtype,
                origin_tenant_id=self._origin_tenant,
                amount=amount,
            )
        if not self._approval_rows:
            template = DEFAULT_APPROVAL_TEMPLATES.get(dtype, DEFAULT_APPROVAL_TEMPLATES[DOC_TYPE_GENERAL])
            default_user = self._users[0].user_id if self._users else ""
            for role_key, role_label in template:
                uid = default_user
                for u in self._users:
                    if role_key in (u.role or ""):
                        uid = u.user_id
                        break
                self._approval_rows.append(
                    {"approver_id": uid, "approver_role": role_key, "role_label": role_label}
                )
        self._approval_panel.set_rows(self._approval_rows)

    def _refresh_cc_list(self) -> None:
        self._cc_list.delete(0, tk.END)
        gu_map = {gu.user.user_id: gu for gu in self._group_users}
        for uid in self._cc_user_ids:
            gu = gu_map.get(uid)
            if gu:
                self._cc_list.insert(tk.END, format_group_user_label(gu))
            else:
                name = next((u.display_name for u in self._users if u.user_id == uid), uid)
                self._cc_list.insert(tk.END, name)

    def _add_cc_via_picker(self) -> None:
        picked = pick_group_users(self, self._group_users, title="참조인 추가", multi=True)
        for gu in picked:
            if gu.user.user_id not in self._cc_user_ids:
                self._cc_user_ids.append(gu.user.user_id)
        self._refresh_cc_list()

    def _remove_cc(self) -> None:
        sel = self._cc_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._cc_user_ids):
            self._cc_user_ids.pop(idx)
            self._refresh_cc_list()

    def _selected_cc_ids(self) -> list[str]:
        return list(self._cc_user_ids)

    def _save(self, *, submit: bool) -> None:
        dtype = self._doc_type.get()
        values = self._collect_values()
        errors = validate_form_values(dtype, values, tenant_id=self._origin_tenant, template_id=self._template_id)
        if errors:
            messagebox.showwarning("필수 입력", "\n".join(errors[:6]), parent=self)
            return
        if submit and not self._approval_panel.get_rows():
            messagebox.showwarning("결재선", "결재선을 1단계 이상 추가하세요.", parent=self)
            return

        built = build_document_fields(dtype, values)
        if self._template_id:
            built["payload"]["gw_template_id"] = self._template_id
            tpl_row = get_template(self._tenant_id, self._template_id)
            if tpl_row:
                built["payload"]["gw_form_name"] = tpl_row.get("gw_form_name") or tpl_row.get("name")
        sess = require_session()
        sites = list_sites(self._tenant_id)
        site_id = sites[0]["id"] if sites else ""
        dept_id = ""
        if sites:
            deps = list_departments(self._tenant_id, site_id)
            dept_id = deps[0]["id"] if deps else ""

        try:
            doc = wf_svc.create_document(
                self._tenant_id,
                document_type=dtype,
                title=built["title"],
                summary=built["summary"],
                content=built["content"],
                site_id=site_id,
                department_id=dept_id,
                total_amount=built["total_amount"],
                due_date=built["due_date"],
                period_start=built["period_start"],
                period_end=built["period_end"],
                cc_user_ids=self._selected_cc_ids(),
                payload=built["payload"],
                session=sess,
            )
            if submit:
                rows = self._approval_panel.get_rows()
                line = [{"approver_id": r["approver_id"], "approver_role": r["approver_role"]} for r in rows]
                wf_svc.submit_document(
                    self._tenant_id,
                    doc["id"],
                    line,
                    session=sess,
                    cc_user_ids=self._selected_cc_ids(),
                )
                messagebox.showinfo(
                    "완료",
                    "상신되었습니다.\n관련자 To-Do·캘린더에 일정이 등록되었습니다.",
                    parent=self,
                )
            else:
                messagebox.showinfo("완료", "임시저장되었습니다.", parent=self)
            if self._on_saved:
                self._on_saved()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("오류", str(exc), parent=self)


def open_compose_dialog(
    parent: tk.Misc,
    *,
    document_type: str | None = None,
    template_id: str | None = None,
    on_saved=None,
) -> None:
    tid = session_tenant_id()
    if not tid:
        messagebox.showinfo("로그인 필요", "로그인 후 작성할 수 있습니다.", parent=parent)
        return
    wf_svc.ensure_tenant_seeded(tid)
    ensure_form_templates(tid)
    WorkflowComposeDialog(
        parent,
        tenant_id=tid,
        origin_tenant_id=tid,
        document_type=document_type or DOC_TYPE_GENERAL,
        template_id=template_id or "",
        on_saved=on_saved,
    )
