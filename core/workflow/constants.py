"""
core/workflow/constants.py - Bitween ERP/워크플로우 공통 상수
"""

from __future__ import annotations

# 문서 상태
DOC_STATUS_DRAFT = "draft"
DOC_STATUS_SUBMITTED = "submitted"
DOC_STATUS_IN_REVIEW = "in_review"
DOC_STATUS_APPROVED = "approved"
DOC_STATUS_REJECTED = "rejected"
DOC_STATUS_REQUESTED_CHANGES = "requested_changes"
DOC_STATUS_CANCELLED = "cancelled"
DOC_STATUS_COMPLETED = "completed"
DOC_STATUS_CLOSED = "closed"

DOC_STATUSES: tuple[str, ...] = (
    DOC_STATUS_DRAFT,
    DOC_STATUS_SUBMITTED,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_APPROVED,
    DOC_STATUS_REJECTED,
    DOC_STATUS_REQUESTED_CHANGES,
    DOC_STATUS_CANCELLED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_CLOSED,
)

DOC_STATUS_LABELS: dict[str, str] = {
    DOC_STATUS_DRAFT: "임시저장",
    DOC_STATUS_SUBMITTED: "상신",
    DOC_STATUS_IN_REVIEW: "결재중",
    DOC_STATUS_APPROVED: "최종승인",
    DOC_STATUS_REJECTED: "반려",
    DOC_STATUS_REQUESTED_CHANGES: "보완요청",
    DOC_STATUS_CANCELLED: "취소",
    DOC_STATUS_COMPLETED: "실행완료",
    DOC_STATUS_CLOSED: "마감완료",
}

# 문서 유형
DOC_TYPE_GENERAL = "GENERAL_DRAFT"
DOC_TYPE_ATTENDANCE = "ATTENDANCE_REQUEST"
DOC_TYPE_PURCHASE = "PURCHASE_REQUEST"
DOC_TYPE_EXPENSE = "EXPENSE_REPORT"
DOC_TYPE_CLOSING = "CLOSING_REPORT"
DOC_TYPE_BUSINESS_TRIP_REQUEST = "BUSINESS_TRIP_REQUEST"

DOC_TYPES: tuple[str, ...] = (
    DOC_TYPE_GENERAL,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_PURCHASE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_CLOSING,
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
)

DOC_TYPE_LABELS: dict[str, str] = {
    DOC_TYPE_GENERAL: "일반 기안",
    DOC_TYPE_ATTENDANCE: "근태신청",
    DOC_TYPE_PURCHASE: "구매요청",
    DOC_TYPE_EXPENSE: "지출결의",
    DOC_TYPE_CLOSING: "마감보고",
    DOC_TYPE_BUSINESS_TRIP_REQUEST: "출장신청서",
}


# 출장 lifecycle status taxonomy (business trip lifecycle, not document status)

TRIP_STATUS_DRAFT = "draft"
TRIP_STATUS_PLANNED = "planned"
TRIP_STATUS_APPROVED = "approved"
TRIP_STATUS_IN_PROGRESS = "in_progress"
TRIP_STATUS_DIARY_DUE = "diary_due"
TRIP_STATUS_OVERDUE = "overdue"
TRIP_STATUS_COMPLETED = "completed"
TRIP_STATUS_CANCELLED = "cancelled"

TRIP_STATUSES: tuple[str, ...] = (
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_PLANNED,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_OVERDUE,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_CANCELLED,
)

TRIP_STATUS_LABELS: dict[str, str] = {
    TRIP_STATUS_DRAFT: "임시저장",
    TRIP_STATUS_PLANNED: "출장계획",
    TRIP_STATUS_APPROVED: "출장승인",
    TRIP_STATUS_IN_PROGRESS: "출장실행",
    TRIP_STATUS_DIARY_DUE: "업무일지 필요",
    TRIP_STATUS_OVERDUE: "지연",
    TRIP_STATUS_COMPLETED: "실적반영 완료",
    TRIP_STATUS_CANCELLED: "취소",
}

KPI_REFLECTION_BLOCKED = "blocked"
KPI_REFLECTION_READY = "ready"
KPI_REFLECTION_REFLECTED = "reflected"
KPI_REFLECTION_NOT_APPLICABLE = "not_applicable"

KPI_REFLECTION_STATUSES: tuple[str, ...] = (
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    KPI_REFLECTION_NOT_APPLICABLE,
)

TRIP_SOURCE_KIND_WORKFLOW = "workflow"
TRIP_SOURCE_KIND_GW_IMPORT = "gw_import"
TRIP_SOURCE_KIND_MANUAL = "manual"

TRIP_SOURCE_KINDS: tuple[str, ...] = (
    TRIP_SOURCE_KIND_WORKFLOW,
    TRIP_SOURCE_KIND_GW_IMPORT,
    TRIP_SOURCE_KIND_MANUAL,
)

# 결재 단계 상태
STEP_PENDING = "pending"
STEP_APPROVED = "approved"
STEP_REJECTED = "rejected"
STEP_SKIPPED = "skipped"
STEP_REQUESTED_CHANGES = "requested_changes"

# 실행업무 상태
TASK_PENDING = "pending"
TASK_IN_PROGRESS = "in_progress"
TASK_COMPLETED = "completed"
TASK_DELAYED = "delayed"
TASK_CANCELLED = "cancelled"

TASK_STATUS_LABELS: dict[str, str] = {
    TASK_PENDING: "대기",
    TASK_IN_PROGRESS: "진행중",
    TASK_COMPLETED: "완료",
    TASK_DELAYED: "지연",
    TASK_CANCELLED: "취소",
}

# 근태 유형
ATTENDANCE_TYPES: dict[str, str] = {
    "annual_leave": "연차",
    "half_day_morning": "오전 반차",
    "half_day_afternoon": "오후 반차",
    "early_leave": "조퇴",
    "outside_work": "외근",
    "business_trip": "출장",
    "overtime": "야근",
    "holiday_work": "특근",
    "sick_leave": "병가",
    "other": "기타",
}

# 워크플로우 역할 (확장용 — UserProfile.workflow_roles)
WF_ROLE_ADMIN = "admin"
WF_ROLE_EXECUTIVE = "executive"
WF_ROLE_SITE_MANAGER = "site_manager"
WF_ROLE_DEPT_MANAGER = "department_manager"
WF_ROLE_APPROVER = "approver"
WF_ROLE_REQUESTER = "requester"
WF_ROLE_EXECUTOR = "executor"
WF_ROLE_FINANCE = "finance"
WF_ROLE_HR = "hr"
WF_ROLE_PURCHASING = "purchasing"
WF_ROLE_VIEWER = "viewer"

# 빠른 작성 템플릿 (다우오피스·네이버웍스·SAP Concur 유형 정렬)
DOC_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    (DOC_TYPE_GENERAL, "일반 기안", "품의·공문·업무협조"),
    (DOC_TYPE_ATTENDANCE, "근태 신청", "연차·반차·출장·야근"),
    (DOC_TYPE_BUSINESS_TRIP_REQUEST, "출장 신청", "출장계획·수행자·출장비"),
    (DOC_TYPE_EXPENSE, "지출 결의", "법인카드·경비·정산"),
    (DOC_TYPE_PURCHASE, "구매 요청", "자재·비품·외주 발주"),
    (DOC_TYPE_CLOSING, "마감 보고", "월마감·사업장 실적"),
)

# 마감 상태
CLOSING_OPEN = "open"
CLOSING_REVIEWING = "reviewing"
CLOSING_CLOSED = "closed"
CLOSING_REOPENED = "reopened"
