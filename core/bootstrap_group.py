"""
core/bootstrap_group.py - COSS Group · 계열사 · 전자결재 설정 부트스트랩
"""

from __future__ import annotations

from core.group_store import DEFAULT_GROUP_ID, create_group, get_group, load_registry
from core.org_positions import POS_CEO, POS_DIRECTOR, POS_MANAGER, POS_MEMBER
from core.roles import ROLE_ADMIN, ROLE_FINANCE, ROLE_STAFF
from core.tenant_store import DEFAULT_TENANT_ID, create_tenant, get_tenant, list_tenants
from core.user_store import find_user_by_username, register_user
from core.workflow.config_store import ensure_workflow_config
from core.workflow.group_defaults import coss_workflow_config

COSS_AFFILIATES: tuple[tuple[str, str, str, str], ...] = (
    ("elso", "ELSO", "(주)엘소", "elso"),
    ("cnlos", "CNL OS", "(주)씨엔엘오에스", "cnlos"),
    ("cheongun", "청운", "(주)청운", "cheongun"),
)


def _ensure_affiliate_tenants() -> list[str]:
    ids = [DEFAULT_TENANT_ID]
    for tenant_id, display, name_ko, login_id in COSS_AFFILIATES:
        if get_tenant(tenant_id) is None:
            try:
                create_tenant(
                    tenant_id=tenant_id,
                    display_name=display,
                    display_name_ko=name_ko,
                    login_id=login_id,
                    notes=f"COSS Group 계열사 ({name_ko})",
                )
            except ValueError:
                pass
        ids.append(tenant_id)
    return ids


def ensure_coss_group() -> dict[str, bool]:
    """COSS Group 레지스트리·워크플로 설정·샘플 계정."""
    tenant_ids = _ensure_affiliate_tenants()
    created_group = False
    grp = get_group(DEFAULT_GROUP_ID)
    if not grp:
        create_group(
            group_id=DEFAULT_GROUP_ID,
            name="COSS Group",
            root_tenant_id=DEFAULT_TENANT_ID,
            tenant_ids=tuple(tenant_ids),
            notes="Bitween 기본 그룹 — 전자결재·계열사 통합",
        )
        created_group = True
        grp = get_group(DEFAULT_GROUP_ID)
    else:
        reg = load_registry()
        row = reg.get("groups", {}).get(DEFAULT_GROUP_ID, {})
        existing = set(row.get("tenant_ids") or [])
        for tid in tenant_ids:
            if tid not in existing:
                from core.group_store import add_tenant_to_group

                add_tenant_to_group(DEFAULT_GROUP_ID, tid)

    config_created = not bool(ensure_workflow_config(DEFAULT_GROUP_ID, factory=coss_workflow_config).get("_existing"))
    ensure_workflow_config(DEFAULT_GROUP_ID, factory=coss_workflow_config)

    users_created = _ensure_sample_affiliate_users()
    return {
        "group_created": created_group,
        "config_seeded": True,
        "sample_users": users_created,
    }


def _ensure_sample_affiliate_users() -> int:
    """계열사 관리직 샘플 계정 (임의 — 고객사가 수정 가능)."""
    from core.bootstrap_org import COSS_CEO_USERNAME, ensure_coss_ceo_account

    ensure_coss_ceo_account()
    samples = [
        ("coss", "coss_finance", "COSS 재무팀장", "entity_coss", POS_MANAGER, ROLE_FINANCE),
        ("coss", "coss_purchasing", "COSS 구매담당", "entity_coss", POS_MEMBER, ROLE_STAFF),
        ("elso", "elso_mgr", "엘소 관리팀장", "entity_elso", POS_MANAGER, ROLE_STAFF),
        ("cnlos", "cnlos_mgr", "CNL OS 관리팀장", "entity_cnlos", POS_MANAGER, ROLE_STAFF),
        ("cheongun", "cheongun_mgr", "청운 관리팀장", "entity_cheongun", POS_MANAGER, ROLE_STAFF),
        ("coss", "coss_exec", "COSS 재무임원", "entity_coss", POS_DIRECTOR, ROLE_FINANCE),
    ]
    ceo = find_user_by_username("coss", COSS_CEO_USERNAME)
    mgr = ceo.user_id if ceo else ""
    count = 0
    entity_units = {
        "entity_coss": "coss_root",
        "entity_elso": "dept_mgmt",
        "entity_cnlos": "dept_mgmt",
        "entity_cheongun": "dept_mgmt",
    }
    for tenant_id, username, name, _eid, pos, role in samples:
        if find_user_by_username(tenant_id, username):
            continue
        register_user(
            tenant_id=tenant_id,
            username=username,
            password="Team2026!",
            display_name=name,
            org_unit_id=entity_units.get(_eid, ""),
            position=pos,
            manager_user_id=mgr,
            role=role,
        )
        count += 1
    return count
