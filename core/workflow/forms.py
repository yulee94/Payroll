"""
core/workflow/forms.py - 양식별 필드·필수값·기본 결재선 (다우오피스·SAP Concur·네이버웍스 패턴)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.workflow.constants import (
    ATTENDANCE_TYPES,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_CLOSING,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
)

APPROVER_ROLES: dict[str, str] = {
    "department_manager": "부서장",
    "site_manager": "사업장장",
    "executive": "임원",
    "finance": "재무",
    "hr": "인사",
    "purchasing": "구매",
    "admin": "관리자",
}

EXPENSE_CATEGORIES = ("법인카드", "현금·영수증", "경비정산", "출장비", "기타")


@dataclass(frozen=True)
class FormFieldDef:
    key: str
    label: str
    field_type: str = "text"  # text | multiline | date | number | select
    required: bool = False
    options: tuple[str, ...] = ()
    placeholder: str = ""
    maps_to: str = ""  # document top-level field alias


def _fields(*items: FormFieldDef) -> tuple[FormFieldDef, ...]:
    return items


COMMON_PERIOD = (
    FormFieldDef("period_start", "업무 시작일", "date", required=True, maps_to="period_start"),
    FormFieldDef("period_end", "업무 종료일", "date", required=True, maps_to="period_end"),
)

FORM_SCHEMAS: dict[str, tuple[FormFieldDef, ...]] = {
    DOC_TYPE_GENERAL: _fields(
        FormFieldDef("title", "제목", required=True, maps_to="title"),
        *COMMON_PERIOD,
        FormFieldDef("purpose", "기안 목적", required=True),
        FormFieldDef("content", "상세 내용", "multiline", required=True, maps_to="summary"),
        FormFieldDef("expected_outcome", "기대 성과", "multiline"),
        FormFieldDef("due_date", "완료 희망일", "date", maps_to="due_date"),
    ),
    DOC_TYPE_ATTENDANCE: _fields(
        FormFieldDef("title", "제목", required=True, maps_to="title"),
        FormFieldDef(
            "attendance_type",
            "근태 유형",
            "select",
            required=True,
            options=tuple(ATTENDANCE_TYPES.values()),
        ),
        FormFieldDef("period_start", "시작일", "date", required=True, maps_to="period_start"),
        FormFieldDef("period_end", "종료일", "date", required=True, maps_to="period_end"),
        FormFieldDef("reason", "사유", "multiline", required=True, maps_to="summary"),
        FormFieldDef("substitute", "업무 인수자", placeholder="부재 시 대리인"),
    ),
    DOC_TYPE_PURCHASE: _fields(
        FormFieldDef("title", "구매 건명", required=True, maps_to="title"),
        FormFieldDef("item_summary", "품목 요약", required=True),
        FormFieldDef("vendor", "거래처/공급사"),
        FormFieldDef("period_start", "납기 희망일", "date", required=True, maps_to="period_start"),
        FormFieldDef("period_end", "사용 기간 종료", "date", maps_to="period_end"),
        FormFieldDef("total_amount", "예상 금액(원)", "number", required=True, maps_to="total_amount"),
        FormFieldDef("purpose", "구매 사유", "multiline", required=True, maps_to="summary"),
    ),
    DOC_TYPE_EXPENSE: _fields(
        FormFieldDef("title", "지출 건명", required=True, maps_to="title"),
        FormFieldDef(
            "expense_category",
            "지출 구분",
            "select",
            required=True,
            options=EXPENSE_CATEGORIES,
        ),
        FormFieldDef("period_start", "사용일(시작)", "date", required=True, maps_to="period_start"),
        FormFieldDef("period_end", "사용일(종료)", "date", maps_to="period_end"),
        FormFieldDef("total_amount", "금액(원)", "number", required=True, maps_to="total_amount"),
        FormFieldDef("purpose", "지출 목적", "multiline", required=True, maps_to="summary"),
    ),
    DOC_TYPE_CLOSING: _fields(
        FormFieldDef("title", "보고 제목", required=True, maps_to="title"),
        FormFieldDef("closing_month", "마감 월", required=True, placeholder="YYYY-MM"),
        FormFieldDef("period_start", "집계 시작", "date", required=True, maps_to="period_start"),
        FormFieldDef("period_end", "집계 종료", "date", required=True, maps_to="period_end"),
        FormFieldDef("summary", "실적 요약", "multiline", required=True, maps_to="summary"),
        FormFieldDef("issues", "특이·리스크", "multiline"),
    ),
}

DEFAULT_APPROVAL_TEMPLATES: dict[str, tuple[tuple[str, str], ...]] = {
    DOC_TYPE_GENERAL: (
        ("department_manager", "부서장"),
        ("executive", "임원"),
    ),
    DOC_TYPE_ATTENDANCE: (("department_manager", "부서장"), ("hr", "인사")),
    DOC_TYPE_PURCHASE: (
        ("department_manager", "부서장"),
        ("purchasing", "구매"),
        ("finance", "재무"),
    ),
    DOC_TYPE_EXPENSE: (
        ("department_manager", "부서장"),
        ("finance", "재무"),
    ),
    DOC_TYPE_CLOSING: (
        ("site_manager", "사업장장"),
        ("finance", "재무"),
        ("executive", "임원"),
    ),
}

REQUIRED_HINTS: dict[str, str] = {
    DOC_TYPE_GENERAL: "필수: 제목, 기간, 기안 목적, 상세 내용",
    DOC_TYPE_ATTENDANCE: "필수: 제목, 근태 유형, 기간, 사유",
    DOC_TYPE_PURCHASE: "필수: 건명, 품목, 납기, 금액, 구매 사유",
    DOC_TYPE_EXPENSE: "필수: 건명, 지출 구분, 사용일, 금액, 목적",
    DOC_TYPE_CLOSING: "필수: 제목, 마감 월, 집계 기간, 실적 요약",
}


def get_form_schema(
    document_type: str,
    tenant_id: str = "",
    *,
    template_id: str = "",
) -> tuple[FormFieldDef, ...]:
    if tenant_id and template_id:
        try:
            from core.workflow.form_templates import resolve_template_schema

            tpl_fields = resolve_template_schema(tenant_id, template_id)
            if tpl_fields:
                return tpl_fields
        except Exception:
            pass
    if tenant_id and not template_id:
        try:
            from core.workflow.config_store import resolve_form_schema

            return resolve_form_schema(tenant_id, document_type)
        except Exception:
            pass
    return FORM_SCHEMAS.get(document_type, FORM_SCHEMAS[DOC_TYPE_GENERAL])


def get_required_hint(document_type: str) -> str:
    return REQUIRED_HINTS.get(document_type, "필수 항목을 입력하세요.")


def validate_form_values(
    document_type: str,
    values: dict[str, str],
    *,
    tenant_id: str = "",
    template_id: str = "",
) -> list[str]:
    errors: list[str] = []
    for field in get_form_schema(document_type, tenant_id, template_id=template_id):
        raw = str(values.get(field.key) or "").strip()
        if field.required and not raw:
            errors.append(f"「{field.label}」은(는) 필수입니다.")
        if field.field_type == "number" and raw:
            try:
                int(raw.replace(",", ""))
            except ValueError:
                errors.append(f"「{field.label}」은(는) 숫자로 입력하세요.")
        if field.key == "closing_month" and raw and len(raw) < 7:
            errors.append("마감 월은 YYYY-MM 형식이어야 합니다.")
    ps = str(values.get("period_start") or "").strip()
    pe = str(values.get("period_end") or "").strip()
    if ps and pe and ps > pe:
        errors.append("시작일이 종료일보다 늦을 수 없습니다.")
    return errors


def build_document_fields(document_type: str, values: dict[str, str]) -> dict[str, Any]:
    """양식 값 → create_document / update_document 인자."""
    v = {k: str(val or "").strip() for k, val in values.items()}
    title = v.get("title", "")
    summary = v.get("summary") or v.get("content") or v.get("purpose") or v.get("reason") or ""
    if not summary:
        parts = [v.get(k) for k in ("purpose", "content", "reason", "item_summary") if v.get(k)]
        summary = "\n".join(parts)
    amount = 0
    if v.get("total_amount"):
        try:
            amount = int(v.get("total_amount", "0").replace(",", ""))
        except ValueError:
            amount = 0
    payload = dict(v)
    payload["document_type"] = document_type
    return {
        "title": title,
        "summary": summary,
        "content": summary,
        "total_amount": amount,
        "due_date": v.get("due_date") or v.get("period_end") or "",
        "period_start": v.get("period_start", ""),
        "period_end": v.get("period_end", ""),
        "payload": payload,
    }


def attendance_type_key(label: str) -> str:
    for k, lbl in ATTENDANCE_TYPES.items():
        if lbl == label:
            return k
    return "other"
