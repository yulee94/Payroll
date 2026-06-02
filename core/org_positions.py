"""
core/org_positions.py - 조직 직위·권한 템플릿
"""

from __future__ import annotations

# 직위 ID
POS_CEO = "ceo"
POS_EXECUTIVE = "executive"
POS_DIRECTOR = "director"
POS_MANAGER = "manager"
POS_TEAM_LEAD = "team_lead"
POS_SENIOR = "senior"
POS_MEMBER = "member"
POS_INTERN = "intern"

POSITION_ORDER: tuple[str, ...] = (
    POS_CEO,
    POS_EXECUTIVE,
    POS_DIRECTOR,
    POS_MANAGER,
    POS_TEAM_LEAD,
    POS_SENIOR,
    POS_MEMBER,
    POS_INTERN,
)

POSITION_LABELS: dict[str, str] = {
    POS_CEO: "대표이사",
    POS_EXECUTIVE: "임원",
    POS_DIRECTOR: "본부장·이사",
    POS_MANAGER: "팀장·과장",
    POS_TEAM_LEAD: "파트장·주임",
    POS_SENIOR: "선임·대리",
    POS_MEMBER: "담당·사원",
    POS_INTERN: "인턴·수습",
}

# 플랫폼·기능 권한 키
PERM_ORG_MANAGE = "org.manage"
PERM_TENANT_ADMIN = "tenant.admin"
PERM_USER_ROLES = "user.roles"
PERM_PAYROLL = "platform.payroll"
PERM_PAYROLL_EXEC = "platform.payroll.executive"
PERM_PAYROLL_SETTINGS = "platform.payroll.settings"
PERM_HR = "platform.hr"
PERM_RECRUITMENT = "platform.recruitment"
PERM_KPI = "platform.kpi"
PERM_KPI_EXEC = "platform.kpi.executive"
PERM_WORKFLOW = "platform.workflow"
PERM_WORKFLOW_APPROVE = "platform.workflow.approve"
PERM_MAINTENANCE = "platform.maintenance"
PERM_BIDDING = "platform.bidding"
PERM_ACCOUNTING = "platform.accounting"
PERM_ACCOUNTING_CLOSE = "platform.accounting.close"

ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        PERM_ORG_MANAGE,
        PERM_TENANT_ADMIN,
        PERM_USER_ROLES,
        PERM_PAYROLL,
        PERM_PAYROLL_EXEC,
        PERM_PAYROLL_SETTINGS,
        PERM_HR,
        PERM_RECRUITMENT,
        PERM_KPI,
        PERM_KPI_EXEC,
        PERM_WORKFLOW,
        PERM_WORKFLOW_APPROVE,
        PERM_MAINTENANCE,
        PERM_BIDDING,
        PERM_ACCOUNTING,
        PERM_ACCOUNTING_CLOSE,
    }
)

# 직위별 기본 권한 (팀 platform 할당과 AND)
POSITION_PERMISSIONS: dict[str, frozenset[str]] = {
    POS_CEO: ALL_PERMISSIONS,
    POS_EXECUTIVE: frozenset(
        {
            PERM_PAYROLL,
            PERM_PAYROLL_EXEC,
            PERM_PAYROLL_SETTINGS,
            PERM_HR,
            PERM_RECRUITMENT,
            PERM_KPI,
            PERM_KPI_EXEC,
            PERM_WORKFLOW,
            PERM_WORKFLOW_APPROVE,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
            PERM_ACCOUNTING_CLOSE,
            PERM_USER_ROLES,
        }
    ),
    POS_DIRECTOR: frozenset(
        {
            PERM_PAYROLL,
            PERM_PAYROLL_EXEC,
            PERM_HR,
            PERM_RECRUITMENT,
            PERM_KPI,
            PERM_WORKFLOW,
            PERM_WORKFLOW_APPROVE,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
        }
    ),
    POS_MANAGER: frozenset(
        {
            PERM_PAYROLL,
            PERM_HR,
            PERM_RECRUITMENT,
            PERM_KPI,
            PERM_WORKFLOW,
            PERM_WORKFLOW_APPROVE,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
        }
    ),
    POS_TEAM_LEAD: frozenset(
        {
            PERM_PAYROLL,
            PERM_HR,
            PERM_RECRUITMENT,
            PERM_KPI,
            PERM_WORKFLOW,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
        }
    ),
    POS_SENIOR: frozenset(
        {
            PERM_PAYROLL,
            PERM_HR,
            PERM_RECRUITMENT,
            PERM_KPI,
            PERM_WORKFLOW,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
        }
    ),
    POS_MEMBER: frozenset(
        {
            PERM_WORKFLOW,
            PERM_MAINTENANCE,
            PERM_BIDDING,
            PERM_ACCOUNTING,
        }
    ),
    POS_INTERN: frozenset({PERM_WORKFLOW}),
}

# 팀(조직)에 연결 가능한 플랫폼 ID
ORG_PLATFORM_IDS: tuple[str, ...] = (
    "payroll",
    "hr",
    "recruitment",
    "kpi",
    "workflow",
    "maintenance",
    "bidding",
    "accounting",
)

ORG_PLATFORM_LABELS: dict[str, str] = {
    "payroll": "급여",
    "hr": "인사 · 노무",
    "recruitment": "채용 · 마당",
    "kpi": "KPI · 경영",
    "workflow": "업무 · 전자결재",
    "maintenance": "정비 사업부",
    "bidding": "입찰",
    "accounting": "회계 · 경리",
}

PLATFORM_TO_PERM: dict[str, str] = {
    "payroll": PERM_PAYROLL,
    "hr": PERM_HR,
    "recruitment": PERM_RECRUITMENT,
    "kpi": PERM_KPI,
    "workflow": PERM_WORKFLOW,
    "maintenance": PERM_MAINTENANCE,
    "bidding": PERM_BIDDING,
    "accounting": PERM_ACCOUNTING,
}


def normalize_position(value: str | None) -> str:
    p = str(value or "").strip().lower()
    if p in POSITION_LABELS:
        return p
    aliases = {
        "대표": POS_CEO,
        "대표이사": POS_CEO,
        "ceo": POS_CEO,
        "임원": POS_EXECUTIVE,
        "이사": POS_DIRECTOR,
        "본부장": POS_DIRECTOR,
        "팀장": POS_MANAGER,
        "과장": POS_MANAGER,
        "파트장": POS_TEAM_LEAD,
        "주임": POS_TEAM_LEAD,
        "대리": POS_SENIOR,
        "선임": POS_SENIOR,
        "사원": POS_MEMBER,
        "담당": POS_MEMBER,
        "staff": POS_MEMBER,
    }
    return aliases.get(p, POS_MEMBER if not p else p)


def position_label(position_id: str) -> str:
    return POSITION_LABELS.get(normalize_position(position_id), POSITION_LABELS[POS_MEMBER])


def permissions_for_position(position_id: str) -> frozenset[str]:
    return POSITION_PERMISSIONS.get(normalize_position(position_id), POSITION_PERMISSIONS[POS_MEMBER])
