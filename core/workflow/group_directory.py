"""
core/workflow/group_directory.py - 그룹 통합 사용자·결재자 조회
"""

from __future__ import annotations

from dataclasses import dataclass

from core.group_store import get_group, get_group_for_tenant
from core.user_store import UserRecord, list_users_for_tenant


@dataclass(frozen=True)
class GroupUser:
    user: UserRecord
    tenant_id: str
    entity_id: str
    entity_name: str
    is_hq: bool


def list_group_users(group_id: str) -> list[GroupUser]:
    grp = get_group(group_id)
    if not grp:
        return []
    from core.workflow.config_store import load_workflow_config

    cfg = load_workflow_config(group_id)
    entity_by_tenant = {
        str(e.get("tenant_id") or ""): e
        for e in (cfg.get("legal_entities") or [])
        if isinstance(e, dict)
    }
    out: list[GroupUser] = []
    for tid in grp.tenant_ids:
        ent = entity_by_tenant.get(tid, {})
        for user in list_users_for_tenant(tid):
            out.append(
                GroupUser(
                    user=user,
                    tenant_id=tid,
                    entity_id=str(ent.get("entity_id") or tid),
                    entity_name=str(ent.get("name_ko") or ent.get("code") or tid),
                    is_hq=bool(ent.get("is_group_hq")),
                )
            )
    return sorted(out, key=lambda g: (not g.is_hq, g.entity_name, g.user.display_name))


def list_group_users_for_tenant(tenant_id: str) -> list[GroupUser]:
    grp = get_group_for_tenant(tenant_id)
    if not grp:
        user = list_users_for_tenant(tenant_id)
        return [
            GroupUser(u, tenant_id, tenant_id, tenant_id, False)
            for u in user
        ]
    return list_group_users(grp.group_id)


def format_group_user_label(gu: GroupUser) -> str:
    pos = gu.user.position or ""
    from core.org_positions import position_label

    pl = position_label(pos) if pos else ""
    role_part = f" · {pl}" if pl else ""
    return f"{gu.user.display_name}{role_part}  [{gu.entity_name}]"


def group_user_department_label(gu: GroupUser) -> str:
    uid = str(gu.user.org_unit_id or "").strip()
    if not uid:
        return ""
    try:
        from core.org_store import get_unit

        unit = get_unit(gu.tenant_id, uid)
        return unit.name if unit else ""
    except Exception:
        return ""


def list_entity_filter_options(group_users: list[GroupUser]) -> list[tuple[str, str]]:
    """법인 필터 (id, 표시명). id='' = 전체."""
    seen: dict[str, str] = {}
    for gu in group_users:
        key = str(gu.entity_id or gu.tenant_id or "")
        if key and key not in seen:
            seen[key] = str(gu.entity_name or key)
    items = sorted(seen.items(), key=lambda x: x[1])
    return [("", "전체 법인")] + items


def filter_group_users(
    group_users: list[GroupUser],
    *,
    query: str = "",
    entity_id: str = "",
) -> list[GroupUser]:
    q = str(query or "").strip().lower()
    ent = str(entity_id or "").strip()
    out: list[GroupUser] = []
    for gu in group_users:
        if ent and gu.entity_id != ent and gu.tenant_id != ent:
            continue
        if not q:
            out.append(gu)
            continue
        dept = group_user_department_label(gu).lower()
        from core.org_positions import position_label

        pos = position_label(gu.user.position or "").lower()
        hay = " ".join(
            [
                gu.user.display_name.lower(),
                gu.user.username.lower(),
                gu.entity_name.lower(),
                dept,
                pos,
            ]
        )
        if q in hay or all(part in hay for part in q.split() if part):
            out.append(gu)
    return out


def resolve_approver_for_step(
    group_id: str,
    *,
    step: dict,
    origin_tenant_id: str,
    users: list[GroupUser] | None = None,
) -> str:
    """템플릿 단계 → 기본 결재자 user_id (없으면 빈 문자열)."""
    if users is None:
        users = list_group_users(group_id)
    role_key = str(step.get("role_key") or "")
    scope = str(step.get("scope") or "origin_entity")
    origin_entity = None
    hq_entity = None
    from core.workflow.config_store import load_workflow_config

    for ent in load_workflow_config(group_id).get("legal_entities") or []:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("tenant_id") or "") == origin_tenant_id:
            origin_entity = ent
        if ent.get("is_group_hq"):
            hq_entity = ent

    def _pool_for_scope() -> list[GroupUser]:
        if scope == "group_hq" and hq_entity:
            tid = str(hq_entity.get("tenant_id") or "")
            return [u for u in users if u.tenant_id == tid]
        tid = str((origin_entity or {}).get("tenant_id") or origin_tenant_id)
        return [u for u in users if u.tenant_id == tid]

    pool = _pool_for_scope()
    role_map = {
        "department_manager": ("manager", "team_lead", "director", "admin"),
        "part_leader": ("team_lead", "manager"),
        "purchasing": ("staff", "finance"),
        "finance": ("finance", "admin"),
        "hr": ("staff", "admin"),
        "executive": ("executive", "director", "ceo"),
        "ceo": ("ceo",),
        "report_only": ("executive", "ceo"),
    }
    pos_keys = role_map.get(role_key, (role_key,))
    for gu in pool:
        pos = (gu.user.position or "").lower()
        role = (gu.user.role or "").lower()
        if pos in pos_keys or role in pos_keys:
            return gu.user.user_id
        if role_key in role and role_key != "report_only":
            return gu.user.user_id
    if pool:
        return pool[0].user.user_id
    return users[0].user.user_id if users else ""


def build_approval_line_from_template(
    group_id: str,
    document_type: str,
    *,
    origin_tenant_id: str,
    amount: int = 0,
) -> list[dict]:
    from core.workflow.config_store import pick_approval_template
    from core.workflow.forms import APPROVER_ROLES

    tpl = pick_approval_template(group_id, document_type, amount=amount)
    if not tpl:
        from core.workflow.constants import DOC_TYPE_GENERAL
        from core.workflow.forms import DEFAULT_APPROVAL_TEMPLATES

        fallback = DEFAULT_APPROVAL_TEMPLATES.get(document_type, DEFAULT_APPROVAL_TEMPLATES.get(DOC_TYPE_GENERAL, ()))
        users = list_group_users(group_id)
        out = []
        for role_key, role_label in fallback:
            uid = resolve_approver_for_step(
                group_id,
                step={"role_key": role_key, "scope": "origin_entity"},
                origin_tenant_id=origin_tenant_id,
                users=users,
            )
            out.append(
                {
                    "approver_id": uid,
                    "approver_role": role_key,
                    "role_label": role_label,
                    "approver_tenant_id": origin_tenant_id,
                }
            )
        return out

    users = list_group_users(group_id)
    steps = tpl.get("steps") or []
    out = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_amt_min = int(step.get("amount_min") or 0)
        if step_amt_min and amount < step_amt_min:
            continue
        role_key = str(step.get("role_key") or "")
        uid = resolve_approver_for_step(
            group_id,
            step=step,
            origin_tenant_id=origin_tenant_id,
            users=users,
        )
        gu = next((u for u in users if u.user.user_id == uid), None)
        approver_tenant = gu.tenant_id if gu else origin_tenant_id
        label = APPROVER_ROLES.get(role_key, role_key)
        for rd in load_workflow_config_roles(group_id):
            if rd.get("role_key") == role_key:
                label = str(rd.get("label") or label)
                break
        out.append(
            {
                "approver_id": uid,
                "approver_role": role_key,
                "role_label": label,
                "approver_tenant_id": approver_tenant,
            }
        )
    return out


def load_workflow_config_roles(group_id: str) -> list[dict]:
    from core.workflow.config_store import load_workflow_config

    return [r for r in (load_workflow_config(group_id).get("approver_roles") or []) if isinstance(r, dict)]
