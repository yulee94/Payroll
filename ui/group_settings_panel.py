"""
ui/group_settings_panel.py - 그룹·법인·결재선 자체 설정 (판매 고객사 메인 계정용)
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from core.group_store import (
    DEFAULT_GROUP_ID,
    add_tenant_to_group,
    get_group,
    get_group_for_tenant,
    list_groups,
)
from core.org_access import can_manage_org, require_org_management
from core.session_service import get_session, is_logged_in, session_tenant_id
from core.tenant_store import create_tenant, get_tenant, list_tenants
from core.workflow.config_store import (
    ensure_workflow_config,
    load_workflow_config,
    save_workflow_config,
    update_approval_templates,
    update_legal_entities,
    update_procurement_chain,
)
from core.workflow.group_defaults import coss_workflow_config
from ui.theme import COLORS, FONT, FONT_BODY

OnChanged = Callable[[], None]


class GroupSettingsPanel(ttk.Frame):
    """그룹 메인(대표) 계정: 법인·결재 템플릿·연동 체인 설정."""

    def __init__(self, master: tk.Misc, *, on_changed: OnChanged | None = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._on_changed = on_changed
        self._group_id = ""
        self._build()
        self.refresh()

    def _build(self) -> None:
        pad = ttk.Frame(self, padding=24)
        pad.pack(fill=tk.BOTH, expand=True)

        ttk.Label(pad, text="그룹 · 전자결재 설정", font=(FONT, 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            pad,
            text=(
                "Bitween을 도입한 각 그룹(고객사)은 메인 계정에서 법인·계열사, 결재선 템플릿, "
                "구매~회계 연동 단계를 직접 조정합니다. COSS는 기본값이 채워져 있으며 "
                "추후 화면에서 수정하거나 타사 판매 시 새 그룹에 동일 구조를 복제할 수 있습니다."
            ),
            wraplength=920,
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(8, 12))

        self._status = tk.StringVar(value="")
        ttk.Label(pad, textvariable=self._status, font=(FONT, 9), foreground=COLORS["muted"]).pack(
            anchor=tk.W, pady=(0, 8)
        )

        nb = ttk.Notebook(pad)
        nb.pack(fill=tk.BOTH, expand=True)

        self._tab_entities = ttk.Frame(nb, padding=12)
        self._tab_templates = ttk.Frame(nb, padding=12)
        self._tab_chain = ttk.Frame(nb, padding=12)
        self._tab_info = ttk.Frame(nb, padding=12)
        nb.add(self._tab_entities, text="법인 · 계열사")
        nb.add(self._tab_templates, text="결재선 템플릿")
        nb.add(self._tab_chain, text="구매·회계 연동")
        nb.add(self._tab_info, text="운영 안내")

        self._build_entities_tab()
        self._build_templates_tab()
        self._build_chain_tab()
        self._build_info_tab()

        btn_row = ttk.Frame(pad)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(btn_row, text="COSS 기본값 다시 적용", command=self._reset_defaults).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="새로고침", command=self.refresh).pack(side=tk.RIGHT)

    def _build_entities_tab(self) -> None:
        ttk.Label(
            self._tab_entities,
            text="그룹에 속한 법인·계열사입니다. 테넌트(로그인 법인)와 1:1로 연결됩니다.",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(0, 8))
        cols = ("name_ko", "code", "tenant_id", "hq", "notes")
        self._entity_tree = ttk.Treeview(self._tab_entities, columns=cols, show="headings", height=8)
        for c, t, w in (
            ("name_ko", "법인명", 160),
            ("code", "코드", 80),
            ("tenant_id", "테넌트 ID", 100),
            ("hq", "본사", 50),
            ("notes", "비고", 220),
        ):
            self._entity_tree.heading(c, text=t)
            self._entity_tree.column(c, width=w)
        self._entity_tree.pack(fill=tk.BOTH, expand=True)
        row = ttk.Frame(self._tab_entities)
        row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(row, text="＋ 법인 추가", command=self._add_entity).pack(side=tk.LEFT)

    def _build_templates_tab(self) -> None:
        ttk.Label(
            self._tab_templates,
            text="문서 유형·금액 구간별 기본 결재선입니다. 기안 시 자동 제안됩니다.",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(0, 8))
        cols = ("name", "document_type", "amount_range", "steps")
        self._tpl_tree = ttk.Treeview(self._tab_templates, columns=cols, show="headings", height=10)
        for c, t, w in (
            ("name", "템플릿명", 200),
            ("document_type", "문서유형", 120),
            ("amount_range", "금액구간", 140),
            ("steps", "결재 단계", 320),
        ):
            self._tpl_tree.heading(c, text=t)
            self._tpl_tree.column(c, width=w)
        self._tpl_tree.pack(fill=tk.BOTH, expand=True)

    def _build_chain_tab(self) -> None:
        ttk.Label(
            self._tab_chain,
            text="구매요청 → 발주 → 입고 → 지출결의 → 회계전표 → 지급확인 (모듈 연동 로드맵)",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(0, 8))
        cols = ("order", "label", "document_type", "owner", "next")
        self._chain_tree = ttk.Treeview(self._tab_chain, columns=cols, show="headings", height=8)
        for c, t, w in (
            ("order", "#", 40),
            ("label", "단계", 140),
            ("document_type", "문서유형", 140),
            ("owner", "담당", 100),
            ("next", "다음 단계", 140),
        ):
            self._chain_tree.heading(c, text=t)
            self._chain_tree.column(c, width=w)
        self._chain_tree.pack(fill=tk.BOTH, expand=True)

    def _build_info_tab(self) -> None:
        txt = tk.Text(self._tab_info, height=18, font=(FONT, 10), wrap=tk.WORD, relief=tk.FLAT)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(
            tk.END,
            (
                "■ 그룹 메인 계정 역할\n"
                "  · 법인(계열사) 등록 · 결재선 템플릿 · 연동 체인 설정\n"
                "  · 하위 조직·계정은 「조직 · 계정」 메뉴에서 branch-out\n\n"
                "■ 교차 결재\n"
                "  · A계열사 기안 → COSS 본사 임원 결재 가능 (설정된 템플릿 scope: group_hq)\n\n"
                "■ 타사 판매 시\n"
                "  · 새 그룹 생성 → 루트 테넌트·메인 계정 1개 제공\n"
                "  · 고객사가 법인·결재선·양식을 Self-service 로 조정\n\n"
                "■ COSS 대표 계정 (초기)\n"
                "  · 아이디 coss_ceo / 비밀번호 Coss2026!\n"
                "  · 계열사 샘플: elso_mgr, cnlos_mgr, cheongun_mgr (Team2026!)\n"
            ),
        )
        txt.configure(state=tk.DISABLED)

    def refresh(self) -> None:
        if not is_logged_in():
            self._status.set("로그인 후 그룹 설정을 이용할 수 있습니다.")
            return
        try:
            require_org_management()
        except PermissionError as exc:
            self._status.set(str(exc))
            return

        tid = session_tenant_id() or ""
        grp = get_group_for_tenant(tid)
        if not grp:
            self._status.set("이 테넌트는 그룹에 연결되어 있지 않습니다.")
            return
        self._group_id = grp.group_id
        cfg = ensure_workflow_config(grp.group_id)
        self._status.set(f"{grp.name} ({grp.group_id}) — 루트 테넌트: {grp.root_tenant_id}")

        self._entity_tree.delete(*self._entity_tree.get_children())
        for ent in cfg.get("legal_entities") or []:
            if not isinstance(ent, dict):
                continue
            self._entity_tree.insert(
                "",
                tk.END,
                values=(
                    ent.get("name_ko", ""),
                    ent.get("code", ""),
                    ent.get("tenant_id", ""),
                    "Y" if ent.get("is_group_hq") else "",
                    ent.get("notes", ""),
                ),
            )

        self._tpl_tree.delete(*self._tpl_tree.get_children())
        for tpl in cfg.get("approval_templates") or []:
            if not isinstance(tpl, dict):
                continue
            lo = int(tpl.get("amount_min") or 0)
            hi = int(tpl.get("amount_max") or 0)
            steps = tpl.get("steps") or []
            step_txt = " → ".join(
                f"{s.get('role_key', '')}({s.get('scope', '')})" for s in steps if isinstance(s, dict)
            )
            self._tpl_tree.insert(
                "",
                tk.END,
                values=(
                    tpl.get("name", ""),
                    tpl.get("document_type", ""),
                    f"{lo:,} ~ {hi:,}",
                    step_txt,
                ),
            )

        self._chain_tree.delete(*self._chain_tree.get_children())
        for i, st in enumerate(cfg.get("procurement_chain") or [], start=1):
            if not isinstance(st, dict):
                continue
            self._chain_tree.insert(
                "",
                tk.END,
                values=(
                    i,
                    st.get("label", ""),
                    st.get("document_type", ""),
                    st.get("owner_role", ""),
                    st.get("next_stage", ""),
                ),
            )

    def _add_entity(self) -> None:
        if not self._group_id:
            return
        name = simpledialog.askstring("법인 추가", "법인명 (예: (주)○○):", parent=self.winfo_toplevel())
        if not name or not name.strip():
            return
        code = simpledialog.askstring("법인 코드", "코드 (영문, 예: ABC):", parent=self.winfo_toplevel()) or ""
        tenant_id = simpledialog.askstring(
            "테넌트 ID", "테넌트 ID (영문, 예: abc):", parent=self.winfo_toplevel()
        )
        if not tenant_id or not tenant_id.strip():
            return
        tid = tenant_id.strip().lower()
        login_id = simpledialog.askstring("로그인 ID", "로그인 ID:", parent=self.winfo_toplevel()) or tid
        try:
            if get_tenant(tid) is None:
                create_tenant(
                    tenant_id=tid,
                    display_name=code or name,
                    display_name_ko=name.strip(),
                    login_id=login_id.strip(),
                    notes=f"{self._group_id} 계열사",
                )
            add_tenant_to_group(self._group_id, tid)
            cfg = load_workflow_config(self._group_id)
            entities = list(cfg.get("legal_entities") or [])
            entities.append(
                {
                    "entity_id": f"entity_{tid}",
                    "tenant_id": tid,
                    "name_ko": name.strip(),
                    "code": code.strip().upper() or tid.upper(),
                    "is_group_hq": False,
                    "notes": "",
                }
            )
            update_legal_entities(self._group_id, entities)
            self.refresh()
            if self._on_changed:
                self._on_changed()
            messagebox.showinfo("추가됨", f"법인 「{name}」이(가) 등록되었습니다.", parent=self.winfo_toplevel())
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("오류", str(exc), parent=self.winfo_toplevel())

    def _reset_defaults(self) -> None:
        if not self._group_id:
            return
        if not messagebox.askyesno(
            "기본값 적용",
            "COSS 기본 법인·결재선·연동 체인으로 덮어씁니다.\n계속할까요?",
            parent=self.winfo_toplevel(),
        ):
            return
        data = coss_workflow_config()
        data["group_id"] = self._group_id
        grp = get_group(self._group_id)
        if grp:
            data["group_name"] = grp.name
        save_workflow_config(self._group_id, data)
        self.refresh()
        messagebox.showinfo("적용됨", "COSS 기본 설정이 적용되었습니다.", parent=self.winfo_toplevel())
