"""
core/workflow/form_templates.py - COSS GW 등에서 가져온 테넌트별 양식함

저장: app_data/workflow/{tenant_id}/form_templates.json
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.workflow.constants import (
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
)
from core.workflow.forms import FormFieldDef

WORKFLOW_ROOT = app_data_dir() / "workflow"


def _workflow_tenant_id(tenant_id: str) -> str:
    """양식함 저장 경로 = 그룹 루트 테넌트 (결재 DB와 동일)."""
    tid = str(tenant_id or "").strip()
    if not tid:
        return ""
    try:
        from core.group_store import get_workflow_tenant_id

        return get_workflow_tenant_id(tid) or tid
    except Exception:
        return tid


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def templates_path(tenant_id: str) -> Path:
    return WORKFLOW_ROOT / tenant_id.strip() / "form_templates.json"


def _slug(name: str) -> str:
    s = re.sub(r"[^\w가-힣]+", "_", name.strip())
    s = s.strip("_").lower()[:48]
    return f"coss_{s}" if s else f"coss_{uuid.uuid4().hex[:8]}"


def _field(
    key: str,
    label: str,
    field_type: str = "text",
    *,
    required: bool = False,
    options: tuple[str, ...] = (),
    placeholder: str = "",
    maps_to: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "field_type": field_type,
        "required": required,
        "options": list(options),
        "placeholder": placeholder,
        "maps_to": maps_to or key,
    }


# COSS GW 양식함 — 필드 정의 (GW 명칭 기준)
COSS_BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "기안서",
        "category": "일반",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "시작일", "date", required=True, maps_to="period_start"),
            _field("period_end", "종료일", "date", required=True, maps_to="period_end"),
            _field("purpose", "기안 목적", required=True),
            _field("content", "상세 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "유류비 지출품의서",
        "category": "지출",
        "document_type": DOC_TYPE_EXPENSE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "사용기간 시작", "date", required=True, maps_to="period_start"),
            _field("period_end", "사용기간 종료", "date", required=True, maps_to="period_end"),
            _field("vehicle", "차량/번호", required=True),
            _field("distance_km", "주행거리(km)", "number"),
            _field("total_amount", "금액(원)", "number", required=True, maps_to="total_amount"),
            _field("purpose", "사용 목적", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "일일업무일지",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("work_date", "업무일", "date", required=True, maps_to="period_start"),
            _field("department", "부서/팀"),
            _field("content", "금일 업무", "multiline", required=True, maps_to="summary"),
            _field("next_plan", "익일 계획", "multiline"),
        ],
    },
    {
        "name": "지출결의서",
        "category": "지출",
        "document_type": DOC_TYPE_EXPENSE,
        "fields": [
            _field("title", "지출 건명", required=True, maps_to="title"),
            _field("expense_category", "지출 구분", "select", required=True, options=("법인카드", "현금·영수증", "경비정산", "출장비", "기타")),
            _field("period_start", "사용일", "date", required=True, maps_to="period_start"),
            _field("total_amount", "금액(원)", "number", required=True, maps_to="total_amount"),
            _field("purpose", "지출 목적", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "휴가신청서",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("attendance_type", "휴가 유형", "select", required=True, options=("연차", "반차(오전)", "반차(오후)", "병가", "기타")),
            _field("period_start", "시작일", "date", required=True, maps_to="period_start"),
            _field("period_end", "종료일", "date", required=True, maps_to="period_end"),
            _field("reason", "사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "연차신청서",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "시작일", "date", required=True, maps_to="period_start"),
            _field("period_end", "종료일", "date", required=True, maps_to="period_end"),
            _field("reason", "사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "경조휴가 및 경조금 지출결의서",
        "category": "인사",
        "document_type": DOC_TYPE_EXPENSE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("event_type", "경조 구분", required=True),
            _field("period_start", "일자", "date", required=True, maps_to="period_start"),
            _field("total_amount", "경조금(원)", "number", maps_to="total_amount"),
            _field("purpose", "내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "급여기안서",
        "category": "인사",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("pay_month", "급여월", required=True, placeholder="YYYY-MM"),
            _field("pay_date", "지급일", "date"),
            _field("total_amount", "총 지급액(원)", "number", maps_to="total_amount"),
            _field("purpose", "기안 사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "주간업무보고서",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "주간 시작", "date", required=True, maps_to="period_start"),
            _field("period_end", "주간 종료", "date", required=True, maps_to="period_end"),
            _field("content", "주요 실적", "multiline", required=True, maps_to="summary"),
            _field("issues", "이슈·건의", "multiline"),
        ],
    },
    {
        "name": "출장보고서",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "출장 시작", "date", required=True, maps_to="period_start"),
            _field("period_end", "출장 종료", "date", required=True, maps_to="period_end"),
            _field("destination", "출장지", required=True),
            _field("content", "출장 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "출장비정산지출결의",
        "category": "지출",
        "document_type": DOC_TYPE_EXPENSE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "출장 시작", "date", required=True, maps_to="period_start"),
            _field("period_end", "출장 종료", "date", maps_to="period_end"),
            _field("total_amount", "정산 금액(원)", "number", required=True, maps_to="total_amount"),
            _field("purpose", "정산 내역", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "코스대외공문",
        "category": "일반",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "문서 제목", required=True, maps_to="title"),
            _field("recipient", "수신", required=True),
            _field("content", "본문", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "협조문",
        "category": "일반",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("recipient_dept", "협조 부서", required=True),
            _field("content", "협조 요청 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "회의록",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "회의명", required=True, maps_to="title"),
            _field("meeting_date", "회의일", "date", required=True, maps_to="period_start"),
            _field("attendees", "참석자"),
            _field("content", "회의 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "재해발생보고서",
        "category": "안전",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("incident_date", "발생일시", "date", required=True, maps_to="period_start"),
            _field("site", "발생 장소", required=True),
            _field("content", "경위 및 조치", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "차량수리의뢰서",
        "category": "자산",
        "document_type": DOC_TYPE_PURCHASE,
        "fields": [
            _field("title", "건명", required=True, maps_to="title"),
            _field("vehicle", "차량", required=True),
            _field("total_amount", "예상 비용(원)", "number", maps_to="total_amount"),
            _field("purpose", "수리 사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "착수보고서",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "사업명", required=True, maps_to="title"),
            _field("period_start", "착수일", "date", required=True, maps_to="period_start"),
            _field("content", "착수 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "철수보고서",
        "category": "보고",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "사업명", required=True, maps_to="title"),
            _field("period_end", "철수일", "date", required=True, maps_to="period_end"),
            _field("content", "철수 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "부재취소원",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("original_date", "취소 대상 일자", "date", required=True),
            _field("reason", "취소 사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "개인인사기록카드",
        "category": "인사",
        "document_type": DOC_TYPE_GENERAL,
        "fields": [
            _field("title", "대상자", required=True, maps_to="title"),
            _field("change_type", "변경 구분", required=True),
            _field("content", "변경 내용", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "6.연장근무 신청서_addWork",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("work_date", "근무일", "date", required=True, maps_to="period_start"),
            _field("hours", "연장 시간", required=True),
            _field("reason", "사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "7.출퇴근시간 변경 신청서_atdChgWrkTmForm",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("work_date", "적용일", "date", required=True, maps_to="period_start"),
            _field("new_time", "변경 시간", required=True),
            _field("reason", "사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "8.출근지연 신청서_atdDelay",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("work_date", "일자", "date", required=True, maps_to="period_start"),
            _field("delay_reason", "지연 사유", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "3.월간근무계획신청서_mnthWrkSchdlRest",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("target_month", "대상 월", required=True, placeholder="YYYY-MM"),
            _field("content", "근무 계획", "multiline", required=True, maps_to="summary"),
        ],
    },
    {
        "name": "4.하반기 연차 신청서_secondhalfyear",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("period_start", "시작일", "date", required=True, maps_to="period_start"),
            _field("period_end", "종료일", "date", required=True, maps_to="period_end"),
            _field("reason", "사유", "multiline", maps_to="summary"),
        ],
    },
    {
        "name": "5.대휴 발생 신청서_atdSubHoliDay",
        "category": "근태",
        "document_type": DOC_TYPE_ATTENDANCE,
        "fields": [
            _field("title", "제목", required=True, maps_to="title"),
            _field("work_date", "발생일", "date", required=True, maps_to="period_start"),
            _field("reason", "사유", "multiline", required=True, maps_to="summary"),
        ],
    },
]


def _normalize_builtin(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row.get("name") or "").strip()
    tid = str(row.get("id") or _slug(name))
    return {
        "id": tid,
        "name": name,
        "category": str(row.get("category") or "기타"),
        "document_type": str(row.get("document_type") or DOC_TYPE_GENERAL),
        "gw_form_name": name,
        "gw_form_id": row.get("gw_form_id") or "",
        "enabled": True,
        "fields": row.get("fields") or [],
        "source": "coss_gw_builtin",
    }


def _load_store(tenant_id: str) -> dict[str, Any]:
    path = templates_path(tenant_id)
    if not path.is_file():
        return {"version": 1, "tenant_id": tenant_id, "templates": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("templates", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "tenant_id": tenant_id, "templates": []}


def _save_store(tenant_id: str, data: dict[str, Any]) -> None:
    path = templates_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_templates(tenant_id: str, *, enabled_only: bool = True) -> list[dict[str, Any]]:
    wf_tid = _workflow_tenant_id(tenant_id)
    rows = list(_load_store(wf_tid).get("templates") or [])
    if enabled_only:
        rows = [r for r in rows if isinstance(r, dict) and r.get("enabled", True)]
    return sorted(rows, key=lambda r: (str(r.get("category") or ""), str(r.get("name") or "")))


def get_template(tenant_id: str, template_id: str) -> dict[str, Any] | None:
    tid = str(template_id).strip()
    for row in list_templates(tenant_id, enabled_only=False):
        if str(row.get("id") or "") == tid:
            return row
    return None


def template_to_field_defs(template: dict[str, Any]) -> tuple[FormFieldDef, ...]:
    out: list[FormFieldDef] = []
    for f in template.get("fields") or []:
        if not isinstance(f, dict):
            continue
        out.append(
            FormFieldDef(
                key=str(f.get("key") or ""),
                label=str(f.get("label") or ""),
                field_type=str(f.get("field_type") or "text"),
                required=bool(f.get("required")),
                options=tuple(f.get("options") or ()),
                placeholder=str(f.get("placeholder") or ""),
                maps_to=str(f.get("maps_to") or ""),
            )
        )
    return tuple(out)


def resolve_template_schema(tenant_id: str, template_id: str) -> tuple[FormFieldDef, ...] | None:
    tpl = get_template(tenant_id, template_id)
    if not tpl:
        return None
    fields = template_to_field_defs(tpl)
    return fields if fields else None


def ensure_form_templates(tenant_id: str) -> dict[str, int]:
    """양식함 JSON이 없거나 fields가 비어 있으면 COSS 내장 정의로 채웁니다."""
    wf_tid = _workflow_tenant_id(tenant_id) or str(tenant_id or "").strip()
    if not wf_tid:
        return {"added": 0, "updated": 0, "total": 0}
    path = templates_path(wf_tid)
    store = _load_store(wf_tid)
    templates = [t for t in (store.get("templates") or []) if isinstance(t, dict)]
    needs_merge = (
        not path.is_file()
        or len(templates) < len(COSS_BUILTIN_TEMPLATES)
        or any(not (t.get("fields") or []) for t in templates)
    )
    if needs_merge:
        return merge_gw_templates(wf_tid)
    return {"added": 0, "updated": 0, "total": len(templates)}


def merge_gw_templates(
    tenant_id: str,
    extra_names: list[str] | None = None,
    *,
    inbox_summary: dict[str, Any] | None = None,
    mail_folders: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Builtin + GW에서 발견한 양식명을 병합 저장. 반환: added, updated, total."""
    wf_tid = _workflow_tenant_id(tenant_id) or str(tenant_id or "").strip()
    store = _load_store(wf_tid)
    by_name: dict[str, dict[str, Any]] = {}
    for row in store.get("templates") or []:
        if isinstance(row, dict):
            by_name[str(row.get("gw_form_name") or row.get("name") or "")] = row

    added = 0
    updated = 0
    for raw in COSS_BUILTIN_TEMPLATES:
        norm = _normalize_builtin(raw)
        key = norm["gw_form_name"]
        if key in by_name:
            existing = by_name[key]
            existing["fields"] = norm["fields"]
            existing["document_type"] = norm["document_type"]
            existing["category"] = norm["category"]
            updated += 1
        else:
            by_name[key] = norm
            added += 1

    # GW 문서에서 추출한 추가 양식명 → 일반 기안 스키마
    for name in extra_names or []:
        nm = str(name).strip()
        if not nm or nm in by_name:
            continue
        doc_type = DOC_TYPE_GENERAL
        if any(k in nm for k in ("구매", "구입", "소모품")):
            doc_type = DOC_TYPE_PURCHASE
        elif any(k in nm for k in ("지출", "품의", "결의")):
            doc_type = DOC_TYPE_EXPENSE
        elif any(k in nm for k in ("연차", "휴가", "근무", "출근", "부재")):
            doc_type = DOC_TYPE_ATTENDANCE
        by_name[nm] = _normalize_builtin(
            {
                "name": nm,
                "category": "GW",
                "document_type": doc_type,
                "fields": deepcopy(COSS_BUILTIN_TEMPLATES[0]["fields"]),
            }
        )
        added += 1

    builtin_by_name = {str(b.get("name") or ""): b for b in COSS_BUILTIN_TEMPLATES}
    for row in by_name.values():
        if row.get("fields"):
            continue
        nm = str(row.get("gw_form_name") or row.get("name") or "")
        src = builtin_by_name.get(nm)
        if src:
            row["fields"] = _normalize_builtin(src)["fields"]
        else:
            row["fields"] = deepcopy(COSS_BUILTIN_TEMPLATES[0]["fields"])

    store["templates"] = list(by_name.values())
    store["fetched_at"] = _now_iso()
    store["source"] = "gw.cossok.com"
    if inbox_summary:
        store["inbox_summary"] = inbox_summary
    if mail_folders:
        store["mail_folders"] = mail_folders
    _save_store(wf_tid, store)
    return {"added": added, "updated": updated, "total": len(store["templates"])}
