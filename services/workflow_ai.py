"""
services/workflow_ai.py - 기안·결재·실행업무 AI 보조 (OpenAI, 서버/서비스 전용)
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.session_service import UserSession, get_session
from core.user_store import list_users_for_tenant
from core.workflow.constants import DOC_TYPE_LABELS
from core.workflow.store import list_departments, list_sites
from services.ai_safety_policy import assess_ai_request_safety
from services.openai_client import OpenAIKeyMissingError, create_openai_client, resolve_openai_model


def _fallback_draft(document_type: str, raw_text: str, amount: int = 0) -> dict[str, Any]:
    label = DOC_TYPE_LABELS.get(document_type, "기안")
    return {
        "title": f"{label} — {raw_text[:40]}".strip(" —"),
        "summary": raw_text[:200],
        "structured_content": {
            "purpose": raw_text,
            "background": "",
            "details": raw_text,
            "expected_cost": str(amount) if amount else "",
            "expected_effect": "",
            "execution_plan": "",
            "risk": "결재 전 예산·일정을 확인하세요.",
        },
        "recommended_approval_line": [],
        "recommended_executors": [],
        "recommended_tasks": [],
        "recommended_due_date": "",
        "recommended_category": "일반",
    }


def draft_assist(
    *,
    document_type: str,
    raw_text: str,
    site_id: str = "",
    department_id: str = "",
    amount: int = 0,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """POST /api/ai/workflow/draft-assist 에 해당하는 데스크톱 서비스 함수."""
    sess = session or get_session()
    safety = assess_ai_request_safety(raw_text)
    if not safety.allowed:
        return {**_fallback_draft(document_type, raw_text, amount), "ai_note": safety.message}

    try:
        client = create_openai_client(sess)
        model = resolve_openai_model(sess)
    except OpenAIKeyMissingError:
        return _fallback_draft(document_type, raw_text, amount)

    tenant_id = sess.tenant_id if sess else ""
    sites = list_sites(tenant_id) if tenant_id else []
    users = list_users_for_tenant(tenant_id) if tenant_id else []
    user_lines = [f"- {u.display_name} ({u.user_id}, role={u.role})" for u in users[:20]]

    system = (
        "You are Bitween ERP assistant. Respond with ONLY valid JSON matching the schema. "
        "Korean text for user-visible fields. No markdown."
    )
    schema = {
        "title": "string",
        "summary": "string",
        "structured_content": {
            "purpose": "",
            "background": "",
            "details": "",
            "expected_cost": "",
            "expected_effect": "",
            "execution_plan": "",
            "risk": "",
        },
        "recommended_approval_line": [{"approver_id": "", "approver_role": ""}],
        "recommended_executors": [{"user_id": "", "reason": ""}],
        "recommended_tasks": [{"title": "", "description": ""}],
        "recommended_due_date": "YYYY-MM-DD",
        "recommended_category": "",
    }
    user_msg = json.dumps(
        {
            "document_type": document_type,
            "raw_text": raw_text,
            "site_id": site_id,
            "department_id": department_id,
            "amount": amount,
            "sites": sites,
            "departments": list_departments(tenant_id, site_id) if tenant_id else [],
            "users": user_lines,
            "schema": schema,
        },
        ensure_ascii=False,
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        parsed = _parse_json(text)
        if parsed:
            return parsed
    except Exception:
        pass
    return _fallback_draft(document_type, raw_text, amount)


def _parse_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def executive_summary_ai(summary: dict[str, Any], *, session: UserSession | None = None) -> dict[str, str]:
    """임원 보고 AI 요약 (실패 시 빈 문자열)."""
    sess = session or get_session()
    base = {"ai_summary": "", "risks": ""}
    try:
        client = create_openai_client(sess)
        model = resolve_openai_model(sess)
    except OpenAIKeyMissingError:
        return base
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Respond JSON only: {\"ai_summary\":\"...\",\"risks\":\"...\"} in Korean.",
                },
                {"role": "user", "content": json.dumps(summary, ensure_ascii=False)[:8000]},
            ],
            temperature=0.2,
        )
        parsed = _parse_json((resp.choices[0].message.content or "").strip())
        if parsed:
            return {
                "ai_summary": str(parsed.get("ai_summary") or ""),
                "risks": str(parsed.get("risks") or ""),
            }
    except Exception:
        pass
    return base
