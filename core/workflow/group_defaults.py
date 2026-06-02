"""
core/workflow/group_defaults.py - COSS Group 전자결재 기본 설정 (임의 시드, 고객사별 수정 가능)
"""

from __future__ import annotations

from typing import Any

from core.workflow.constants import (
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_CLOSING,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
)
from core.workflow.forms import EXPENSE_CATEGORIES, FORM_SCHEMAS, FormFieldDef

# --- 법인 / 계열사 (COSS 그룹) ---

COSS_LEGAL_ENTITIES: list[dict[str, Any]] = [
    {
        "entity_id": "entity_coss",
        "tenant_id": "coss",
        "name_ko": "(주)코스",
        "code": "COSS",
        "is_group_hq": True,
        "notes": "그룹 본사 · 경영·재무·임원 결재",
    },
    {
        "entity_id": "entity_elso",
        "tenant_id": "elso",
        "name_ko": "(주)엘소",
        "code": "ELSO",
        "is_group_hq": False,
        "notes": "계열사",
    },
    {
        "entity_id": "entity_cnlos",
        "tenant_id": "cnlos",
        "name_ko": "(주)씨엔엘오에스",
        "code": "CNLOS",
        "is_group_hq": False,
        "notes": "계열사",
    },
    {
        "entity_id": "entity_cheongun",
        "tenant_id": "cheongun",
        "name_ko": "(주)청운",
        "code": "CHEONGUN",
        "is_group_hq": False,
        "notes": "계열사",
    },
]

# --- 관리 조직 (현장직 제외, 보고·결재 축) ---

COSS_MANAGEMENT_UNITS: list[dict[str, Any]] = [
    {"unit_id": "unit_ceo", "name": "경영진", "entity_id": "entity_coss", "level": "executive"},
    {"unit_id": "unit_finance", "name": "재무·회계", "entity_id": "entity_coss", "level": "hq"},
    {"unit_id": "unit_hr", "name": "인사·총무", "entity_id": "entity_coss", "level": "hq"},
    {"unit_id": "unit_purchasing", "name": "구매", "entity_id": "entity_coss", "level": "hq"},
    {"unit_id": "unit_mgmt_elso", "name": "엘소 관리", "entity_id": "entity_elso", "level": "affiliate"},
    {"unit_id": "unit_mgmt_cnlos", "name": "CNL OS 관리", "entity_id": "entity_cnlos", "level": "affiliate"},
    {"unit_id": "unit_mgmt_cheongun", "name": "청운 관리", "entity_id": "entity_cheongun", "level": "affiliate"},
]

# --- 결재 역할 (고객사가 라벨·매핑 수정 가능) ---

DEFAULT_APPROVER_ROLE_DEFS: list[dict[str, Any]] = [
    {"role_key": "department_manager", "label": "부서장·팀장", "scope": "origin_entity"},
    {"role_key": "part_leader", "label": "파트장", "scope": "origin_entity"},
    {"role_key": "purchasing", "label": "구매", "scope": "origin_entity"},
    {"role_key": "finance", "label": "재무", "scope": "group_hq"},
    {"role_key": "hr", "label": "인사", "scope": "group_hq"},
    {"role_key": "executive", "label": "임원(이사·전무)", "scope": "group_hq"},
    {"role_key": "ceo", "label": "대표이사", "scope": "group_hq"},
    {"role_key": "report_only", "label": "경영 보고(열람)", "scope": "group_hq"},
]

# --- 결재 템플릿 ---

COSS_APPROVAL_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "tpl_general",
        "document_type": DOC_TYPE_GENERAL,
        "name": "일반 기안 (표준)",
        "amount_min": 0,
        "amount_max": 999_999_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "executive", "scope": "group_hq", "amount_min": 5_000_000},
        ],
    },
    {
        "template_id": "tpl_attendance",
        "document_type": DOC_TYPE_ATTENDANCE,
        "name": "근태 신청 (표준)",
        "amount_min": 0,
        "amount_max": 999_999_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "hr", "scope": "group_hq"},
        ],
    },
    {
        "template_id": "tpl_purchase_small",
        "document_type": DOC_TYPE_PURCHASE,
        "name": "구매요청 — 500만원 미만",
        "amount_min": 0,
        "amount_max": 4_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "purchasing", "scope": "origin_entity"},
        ],
    },
    {
        "template_id": "tpl_purchase_mid",
        "document_type": DOC_TYPE_PURCHASE,
        "name": "구매요청 — 500만~1천만원",
        "amount_min": 5_000_000,
        "amount_max": 9_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "purchasing", "scope": "origin_entity"},
            {"role_key": "finance", "scope": "group_hq"},
        ],
    },
    {
        "template_id": "tpl_purchase_large",
        "document_type": DOC_TYPE_PURCHASE,
        "name": "구매요청 — 1천만원 이상 (임원)",
        "amount_min": 10_000_000,
        "amount_max": 999_999_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "purchasing", "scope": "origin_entity"},
            {"role_key": "finance", "scope": "group_hq"},
            {"role_key": "executive", "scope": "group_hq"},
        ],
    },
    {
        "template_id": "tpl_expense",
        "document_type": DOC_TYPE_EXPENSE,
        "name": "지출결의 (표준)",
        "amount_min": 0,
        "amount_max": 999_999_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "finance", "scope": "group_hq"},
        ],
    },
    {
        "template_id": "tpl_closing",
        "document_type": DOC_TYPE_CLOSING,
        "name": "월마감·경영 보고",
        "amount_min": 0,
        "amount_max": 999_999_999_999,
        "steps": [
            {"role_key": "department_manager", "scope": "origin_entity"},
            {"role_key": "finance", "scope": "group_hq"},
            {"role_key": "executive", "scope": "group_hq"},
            {"role_key": "report_only", "scope": "group_hq"},
        ],
    },
]

# --- 구매·지출 연동 체인 (향후 발주·입고·회계 연결) ---

COSS_PROCUREMENT_CHAIN: list[dict[str, Any]] = [
    {
        "stage_id": "purchase_request",
        "label": "구매요청서",
        "document_type": DOC_TYPE_PURCHASE,
        "next_stage": "purchase_order",
        "owner_role": "requester",
    },
    {
        "stage_id": "purchase_order",
        "label": "발주서",
        "document_type": "PURCHASE_ORDER",
        "next_stage": "goods_receipt",
        "owner_role": "purchasing",
    },
    {
        "stage_id": "goods_receipt",
        "label": "입고확인",
        "document_type": "GOODS_RECEIPT",
        "next_stage": "expense_report",
        "owner_role": "purchasing",
    },
    {
        "stage_id": "expense_report",
        "label": "계산서·지출결의",
        "document_type": DOC_TYPE_EXPENSE,
        "next_stage": "accounting_post",
        "owner_role": "finance",
    },
    {
        "stage_id": "accounting_post",
        "label": "회계 전표·자산등록",
        "document_type": "ACCOUNTING_VOUCHER",
        "next_stage": "payment_confirm",
        "owner_role": "finance",
    },
    {
        "stage_id": "payment_confirm",
        "label": "지급 확인",
        "document_type": "PAYMENT_CONFIRM",
        "next_stage": "",
        "owner_role": "finance",
    },
]


def _field_to_dict(f: FormFieldDef) -> dict[str, Any]:
    return {
        "key": f.key,
        "label": f.label,
        "field_type": f.field_type,
        "required": f.required,
        "options": list(f.options),
        "placeholder": f.placeholder,
        "maps_to": f.maps_to,
    }


def default_document_type_configs() -> list[dict[str, Any]]:
    from core.workflow.constants import DOC_TYPE_LABELS

    out = []
    for dtype, schema in FORM_SCHEMAS.items():
        out.append(
            {
                "document_type": dtype,
                "label": DOC_TYPE_LABELS.get(dtype, dtype),
                "enabled": True,
                "fields": [_field_to_dict(f) for f in schema],
            }
        )
    return out


def empty_workflow_config(group_id: str, group_name: str) -> dict[str, Any]:
    return {
        "version": 1,
        "group_id": group_id,
        "group_name": group_name,
        "legal_entities": [],
        "management_units": [],
        "approver_roles": list(DEFAULT_APPROVER_ROLE_DEFS),
        "approval_templates": [],
        "document_types": default_document_type_configs(),
        "procurement_chain": [],
        "settings": {
            "field_workers_excluded": True,
            "cross_entity_approval": True,
            "workflow_storage": "group_root",
            "historical_import_enabled": True,
        },
    }


def coss_workflow_config() -> dict[str, Any]:
    cfg = empty_workflow_config("coss_group", "COSS Group")
    cfg["legal_entities"] = list(COSS_LEGAL_ENTITIES)
    cfg["management_units"] = list(COSS_MANAGEMENT_UNITS)
    cfg["approval_templates"] = list(COSS_APPROVAL_TEMPLATES)
    cfg["procurement_chain"] = list(COSS_PROCUREMENT_CHAIN)
    return cfg
