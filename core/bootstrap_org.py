"""
core/bootstrap_org.py - COSS 조직도·대표 계정 초기 시드
"""

from __future__ import annotations

from core.org_positions import (
    POS_CEO,
    POS_DIRECTOR,
    POS_MANAGER,
    POS_MEMBER,
    POS_TEAM_LEAD,
)
from core.org_store import get_root_unit_id, import_org_tree, list_units
from core.roles import ROLE_ADMIN, ROLE_FINANCE, ROLE_STAFF
from core.user_store import find_user_by_username, register_user, update_user_org
from core.tenant_store import DEFAULT_TENANT_ID

# COSS 대표 계정 (최초 부트스트랩용 — 배포 후 비밀번호 변경 권장)
COSS_CEO_USERNAME = "coss_ceo"
COSS_CEO_DEFAULT_PASSWORD = "Coss2026!"

COSS_ORG_UNITS: list[dict] = [
    {
        "unit_id": "coss_root",
        "name": "COSS Group",
        "parent_id": "",
        "sort_order": 0,
        "platform_ids": ["payroll", "hr", "recruitment", "kpi", "workflow", "maintenance", "bidding", "accounting"],
        "notes": "최상위 — 대표이사",
    },
    {
        "unit_id": "dept_mgmt",
        "name": "경영지원본부",
        "parent_id": "coss_root",
        "sort_order": 1,
        "platform_ids": ["payroll", "hr", "recruitment", "kpi", "workflow", "accounting"],
    },
    {
        "unit_id": "team_finance",
        "name": "재무팀",
        "parent_id": "dept_mgmt",
        "sort_order": 2,
        "platform_ids": ["payroll", "accounting"],
    },
    {
        "unit_id": "team_hr",
        "name": "인사팀",
        "parent_id": "dept_mgmt",
        "sort_order": 3,
        "platform_ids": ["hr", "recruitment", "workflow"],
    },
    {
        "unit_id": "dept_maint",
        "name": "정비사업부",
        "parent_id": "coss_root",
        "sort_order": 4,
        "platform_ids": ["maintenance", "workflow"],
    },
    {
        "unit_id": "dept_bid",
        "name": "입찰팀",
        "parent_id": "coss_root",
        "sort_order": 5,
        "platform_ids": ["bidding", "workflow"],
    },
    {
        "unit_id": "dept_acct",
        "name": "회계팀",
        "parent_id": "coss_root",
        "sort_order": 6,
        "platform_ids": ["accounting", "payroll"],
    },
]


def ensure_coss_org_structure(tenant_id: str = DEFAULT_TENANT_ID) -> bool:
    """조직도가 없으면 COSS 기본 트리 생성. True=새로 생성."""
    if list_units(tenant_id):
        return False
    import_org_tree(tenant_id, COSS_ORG_UNITS, root_id="coss_root")
    return True


def ensure_coss_ceo_account(tenant_id: str = DEFAULT_TENANT_ID) -> bool:
    """대표이사 계정이 없으면 생성. True=새로 생성."""
    existing = find_user_by_username(tenant_id, COSS_CEO_USERNAME)
    root_id = get_root_unit_id(tenant_id) or "coss_root"
    if existing:
        if not existing.org_unit_id or existing.position != POS_CEO:
            update_user_org(
                existing.user_id,
                org_unit_id=root_id,
                position=POS_CEO,
            )
        return False
    register_user(
        tenant_id=tenant_id,
        username=COSS_CEO_USERNAME,
        password=COSS_CEO_DEFAULT_PASSWORD,
        display_name="COSS 대표이사",
        org_unit_id=root_id,
        position=POS_CEO,
        role=ROLE_ADMIN,
    )
    return True


def ensure_coss_org_bootstrap(tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, bool]:
    org_created = ensure_coss_org_structure(tenant_id)
    ceo_created = ensure_coss_ceo_account(tenant_id)
    return {"org_created": org_created, "ceo_created": ceo_created}


def seed_sample_team_accounts(tenant_id: str = DEFAULT_TENANT_ID) -> None:
    """데모용 팀별 샘플 계정 (이미 있으면 건너뜀)."""
    samples = [
        ("coss_finance", "재무팀장", "team_finance", POS_MANAGER, ROLE_FINANCE),
        ("coss_hr", "인사담당", "team_hr", POS_TEAM_LEAD, ROLE_STAFF),
        ("coss_maint", "정비팀장", "dept_maint", POS_TEAM_LEAD, ROLE_STAFF),
        ("coss_bid", "입찰담당", "dept_bid", POS_MEMBER, ROLE_STAFF),
        ("coss_acct", "회계팀장", "dept_acct", POS_MANAGER, ROLE_FINANCE),
    ]
    ceo = find_user_by_username(tenant_id, COSS_CEO_USERNAME)
    mgr_id = ceo.user_id if ceo else ""
    for username, name, unit_id, pos, role in samples:
        if find_user_by_username(tenant_id, username):
            continue
        register_user(
            tenant_id=tenant_id,
            username=username,
            password="Team2026!",
            display_name=name,
            org_unit_id=unit_id,
            position=pos,
            manager_user_id=mgr_id,
            role=role,
        )
