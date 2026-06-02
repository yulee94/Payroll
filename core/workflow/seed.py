"""
core/workflow/seed.py - 워크플로우 MVP 샘플 데이터
"""

from __future__ import annotations

from datetime import date
from typing import Any

from core.user_store import list_users_for_tenant
from core.workflow.constants import (
    DOC_STATUS_APPROVED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_IN_REVIEW,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
    STEP_APPROVED,
    STEP_PENDING,
    TASK_PENDING,
)
from core.workflow.store import _load_raw, _new_id, _now_iso, _save_raw, next_document_no


def seed_tenant_if_empty(tenant_id: str) -> bool:
    db = _load_raw(tenant_id)
    if db.get("documents"):
        return False
    _apply_seed(tenant_id, db)
    _save_raw(tenant_id, db)
    return True


def _apply_seed(tenant_id: str, db: dict[str, Any]) -> None:
    sites = [
        {"id": "site_hq", "name": "본사", "code": "HQ"},
        {"id": "site_miryang", "name": "밀양공장", "code": "MY"},
        {"id": "site_busan", "name": "부산지점", "code": "BS"},
        {"id": "site_gyeongnam", "name": "경남지점", "code": "GN"},
    ]
    departments = [
        {"id": "dept_mgmt", "site_id": "site_hq", "name": "경영지원"},
        {"id": "dept_sales", "site_id": "site_hq", "name": "영업"},
        {"id": "dept_purchase", "site_id": "site_hq", "name": "구매"},
        {"id": "dept_prod", "site_id": "site_miryang", "name": "생산"},
        {"id": "dept_qc", "site_id": "site_miryang", "name": "품질"},
        {"id": "dept_fin", "site_id": "site_hq", "name": "재무"},
        {"id": "dept_hr", "site_id": "site_hq", "name": "인사"},
    ]
    db["sites"] = sites
    db["departments"] = departments

    users = list_users_for_tenant(tenant_id)
    profiles: list[dict[str, Any]] = []
    for i, u in enumerate(users):
        roles = ["requester"]
        if u.role == "admin":
            roles = ["admin", "executive", "approver", "finance"]
        elif u.role == "finance":
            roles = ["finance", "approver", "executive"]
        if i == 0 and "purchasing" not in roles:
            roles.append("purchasing")
        profiles.append(
            {
                "user_id": u.user_id,
                "display_name": u.display_name,
                "title": "담당",
                "site_ids": [s["id"] for s in sites],
                "department_ids": [departments[0]["id"]],
                "workflow_roles": roles,
            }
        )
    db["user_profiles"] = profiles

    if not users:
        return

    req = users[0]
    approver = users[1] if len(users) > 1 else users[0]

    def _doc(
        title: str,
        dtype: str,
        status: str,
        amount: int,
        site_id: str = "site_hq",
        dept_id: str = "dept_mgmt",
    ) -> str:
        doc_id = _new_id()
        db.setdefault("documents", []).append(
            {
                "id": doc_id,
                "document_no": next_document_no(db),
                "document_type": dtype,
                "title": title,
                "summary": title,
                "content": "",
                "status": status,
                "site_id": site_id,
                "department_id": dept_id,
                "requester_id": req.user_id,
                "total_amount": amount,
                "currency": "KRW",
                "category": "",
                "requested_date": date.today().isoformat(),
                "due_date": "",
                "approved_at": _now_iso() if status == DOC_STATUS_APPROVED else "",
                "rejected_at": "",
                "completed_at": "",
                "closed_at": "",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "content_json": {},
            }
        )
        return doc_id

    d1 = _doc("리튬지게차 판매사업 추진 기안", DOC_TYPE_GENERAL, DOC_STATUS_IN_REVIEW, 0)
    db.setdefault("approval_steps", []).extend(
        [
            {
                "id": _new_id(),
                "document_id": d1,
                "step_order": 1,
                "approver_id": approver.user_id,
                "approver_role": "department_manager",
                "status": STEP_PENDING,
                "approved_at": "",
                "rejected_at": "",
                "comment": "",
            },
            {
                "id": _new_id(),
                "document_id": d1,
                "step_order": 2,
                "approver_id": approver.user_id,
                "approver_role": "executive",
                "status": STEP_PENDING,
                "approved_at": "",
                "rejected_at": "",
                "comment": "",
            },
        ]
    )

    d2 = _doc("항차 지게차 구매요청", DOC_TYPE_PURCHASE, DOC_STATUS_APPROVED, 45_000_000, "site_miryang", "dept_purchase")
    db["purchase_requests"].append(
        {
            "id": _new_id(),
            "document_id": d2,
            "purchase_category": "설비",
            "vendor_name": "○○중장비",
            "item_name": "항차 지게차",
            "quantity": 1,
            "unit_price": 45_000_000,
            "total_amount": 45_000_000,
            "required_date": date.today().isoformat(),
            "purpose": "생산 라인 증설",
        }
    )
    db["purchase_request_items"].append(
        {
            "id": _new_id(),
            "document_id": d2,
            "item_name": "항차 지게차 3.0t",
            "quantity": 1,
            "unit_price": 45_000_000,
            "total_amount": 45_000_000,
        }
    )
    db["execution_tasks"].append(
        {
            "id": _new_id(),
            "document_id": d2,
            "title": "구매 발주 진행",
            "description": "항차 지게차 구매요청 승인 후 발주",
            "executor_id": req.user_id,
            "site_id": "site_miryang",
            "department_id": "dept_purchase",
            "due_date": date.today().isoformat(),
            "priority": "high",
            "status": TASK_PENDING,
            "ai_recommended_action": "견적서 2곳 이상 비교 후 발주",
            "completed_at": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
    )

    d3 = _doc("사무용품 구매요청", DOC_TYPE_PURCHASE, DOC_STATUS_DRAFT, 350_000)
    db["purchase_requests"].append(
        {
            "id": _new_id(),
            "document_id": d3,
            "purchase_category": "소모품",
            "vendor_name": "",
            "item_name": "사무용품 일괄",
            "quantity": 1,
            "unit_price": 350_000,
            "total_amount": 350_000,
            "required_date": "",
            "purpose": "본사 사무실",
        }
    )

    d4 = _doc("출장비 지출결의", DOC_TYPE_EXPENSE, DOC_STATUS_APPROVED, 280_000)
    db["expense_reports"].append(
        {
            "id": _new_id(),
            "document_id": d4,
            "expense_date": date.today().isoformat(),
            "expense_category": "출장비",
            "vendor_name": "",
            "payment_method": "법인카드",
            "amount": 250_000,
            "vat_amount": 30_000,
            "total_amount": 280_000,
            "description": "부산지점 방문",
            "cost_center": "영업",
        }
    )

    d5 = _doc("연차 신청", DOC_TYPE_ATTENDANCE, DOC_STATUS_DRAFT, 0)
    db["attendance_requests"].append(
        {
            "id": _new_id(),
            "document_id": d5,
            "attendance_type": "annual_leave",
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "start_time": "",
            "end_time": "",
            "reason": "개인 사유",
            "substitute_user_id": "",
            "emergency_contact": "",
        }
    )

    month = date.today().strftime("%Y-%m")
    db["monthly_closings"].append(
        {
            "id": _new_id(),
            "site_id": "site_hq",
            "month": month,
            "status": "open",
            "checklist": {"pending_docs": 1, "pending_tasks": 1},
            "closed_at": "",
            "created_at": _now_iso(),
        }
    )
    db["profit_loss"].append(
        {
            "id": _new_id(),
            "site_id": "site_miryang",
            "month": month,
            "revenue": 120_000_000,
            "purchase_cost": 45_000_000,
            "labor_cost": 38_000_000,
            "operating_expense": 12_000_000,
            "other_expense": 0,
            "gross_profit": 75_000_000,
            "operating_profit": 25_000_000,
            "memo": "MVP 샘플",
        }
    )
