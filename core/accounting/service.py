"""
core/accounting/service.py - 회계·경리 (더존 SmartA·SAP FI·Peachtree 유형 MVP)
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "accounting"

_EMPTY: dict[str, Any] = {
    "vouchers": [],
    "tax_events": [],
    "cash_plan": [],
    "reports": [],
    "seeded": False,
}

TAB_IDS = ("vouchers", "tax_events", "cash_plan", "reports")

TAB_LABELS = {
    "vouchers": "전표 입력",
    "tax_events": "세무 신고",
    "cash_plan": "자금 계획",
    "reports": "결산 보고",
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _fmt_won(n: int) -> str:
    return f"{n:,}"


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        return
    d = date.today()
    ym = d.strftime("%Y-%m")
    db["vouchers"] = [
        {
            "id": _new_id(),
            "voucher_no": f"JV-{ym}-0041",
            "date": d.isoformat(),
            "account": "급여",
            "debit": "45000000",
            "credit": "0",
            "memo": f"{ym} 급여",
            "status": "승인",
        },
        {
            "id": _new_id(),
            "voucher_no": f"JV-{ym}-0042",
            "date": d.isoformat(),
            "account": "보통예금",
            "debit": "0",
            "credit": "45000000",
            "memo": f"{ym} 급여 지급",
            "status": "승인",
        },
    ]
    db["tax_events"] = [
        {
            "id": _new_id(),
            "tax_type": "원천세",
            "period": ym,
            "due_date": (d.replace(day=10) if d.day <= 10 else (d.replace(day=1) + timedelta(days=32)).replace(day=10)).isoformat(),
            "status": "예정",
            "note": "급여 원천징수",
        },
        {
            "id": _new_id(),
            "tax_type": "부가세",
            "period": f"{d.year}Q{(d.month - 1) // 3 + 1}",
            "due_date": (d + timedelta(days=25)).isoformat(),
            "status": "준비",
            "note": "매출·매입 합산",
        },
    ]
    db["cash_plan"] = [
        {
            "id": _new_id(),
            "week": f"{ym} W1",
            "inflow": "52000000",
            "outflow": "48000000",
            "balance": "125000000",
            "note": "급여·세금 출금",
        },
        {
            "id": _new_id(),
            "week": f"{ym} W2",
            "inflow": "38000000",
            "outflow": "22000000",
            "balance": "141000000",
            "note": "도급비 입금 예정",
        },
    ]
    db["reports"] = [
        {
            "id": _new_id(),
            "report": "손익계산서(월)",
            "period": ym,
            "status": "작성중",
            "owner": "재무팀",
            "updated": d.isoformat(),
        },
        {
            "id": _new_id(),
            "report": "재무상태표(월)",
            "period": ym,
            "status": "검토",
            "owner": "재무팀",
            "updated": d.isoformat(),
        },
    ]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def dashboard_kpis(tenant_id: str | None = None) -> list[tuple[str, str, str]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    pending_v = sum(1 for v in db["vouchers"] if v.get("status") != "승인")
    tax_due = sum(
        1
        for t in db["tax_events"]
        if t.get("status") in ("예정", "준비")
        and t.get("due_date", "") <= (date.today() + timedelta(days=30)).isoformat()
    )
    try:
        balance = int(db["cash_plan"][-1].get("balance", 0)) if db["cash_plan"] else 0
    except (ValueError, IndexError):
        balance = 0
    return [
        ("미승인 전표", str(pending_v), "전표입력·결재"),
        ("30일 내 세무", str(tax_due), "신고 일정"),
        ("자금 잔액", _fmt_won(balance), "주간 자금계획"),
        ("결산 보고", str(len(db["reports"])), "월·분기"),
    ]


def list_records(tab_id: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    key = tab_id if tab_id in TAB_IDS else "vouchers"
    return list(db.get(key) or [])


def add_record(tab_id: str, fields: dict[str, str], tenant_id: str | None = None) -> dict[str, Any]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    ym = date.today().strftime("%Y-%m")

    def _mut(data: dict[str, Any]) -> dict[str, Any]:
        rec: dict[str, Any] = {"id": _new_id()}
        if tab_id == "vouchers":
            rec.update(
                {
                    "voucher_no": fields.get("voucher_no")
                    or f"JV-{ym}-{len(data['vouchers'])+1:04d}",
                    "date": fields.get("date") or date.today().isoformat(),
                    "account": fields.get("account", ""),
                    "debit": fields.get("debit", "0"),
                    "credit": fields.get("credit", "0"),
                    "memo": fields.get("memo", ""),
                    "status": "임시",
                }
            )
            data["vouchers"].append(rec)
        elif tab_id == "tax_events":
            rec.update(
                {
                    "tax_type": fields.get("tax_type", "부가세"),
                    "period": fields.get("period") or ym,
                    "due_date": fields.get("due_date") or date.today().isoformat(),
                    "status": "예정",
                    "note": fields.get("note", ""),
                }
            )
            data["tax_events"].append(rec)
        elif tab_id == "cash_plan":
            rec.update(
                {
                    "week": fields.get("week") or f"{ym} W?",
                    "inflow": fields.get("inflow", "0"),
                    "outflow": fields.get("outflow", "0"),
                    "balance": fields.get("balance", "0"),
                    "note": fields.get("note", ""),
                }
            )
            data["cash_plan"].append(rec)
        elif tab_id == "reports":
            rec.update(
                {
                    "report": fields.get("report", ""),
                    "period": fields.get("period") or ym,
                    "status": "작성중",
                    "owner": fields.get("owner", ""),
                    "updated": date.today().isoformat(),
                }
            )
            data["reports"].append(rec)
        return rec

    return mutate_module_db(MODULE, tid, _EMPTY, _mut)


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    cols = {
        "vouchers": (
            ("voucher_no", "전표번호", 110),
            ("date", "일자", 90),
            ("account", "계정", 90),
            ("debit", "차변", 80),
            ("credit", "대변", 80),
            ("memo", "적요", 140),
            ("status", "상태", 60),
        ),
        "tax_events": (
            ("tax_type", "세목", 80),
            ("period", "과세기간", 80),
            ("due_date", "신고기한", 90),
            ("status", "상태", 60),
            ("note", "비고", 160),
        ),
        "cash_plan": (
            ("week", "주차", 80),
            ("inflow", "입금", 90),
            ("outflow", "출금", 90),
            ("balance", "잔액", 100),
            ("note", "비고", 140),
        ),
        "reports": (
            ("report", "보고서", 140),
            ("period", "기간", 80),
            ("status", "상태", 60),
            ("owner", "담당", 80),
            ("updated", "갱신", 90),
        ),
    }
    return cols.get(tab_id, cols["vouchers"])


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    forms = {
        "vouchers": (
            ("account", "계정과목", True),
            ("debit", "차변(원)", False),
            ("credit", "대변(원)", False),
            ("memo", "적요", False),
        ),
        "tax_events": (
            ("tax_type", "세목", True),
            ("period", "과세기간", False),
            ("due_date", "신고기한", False),
            ("note", "비고", False),
        ),
        "cash_plan": (
            ("week", "주차", True),
            ("inflow", "입금(원)", False),
            ("outflow", "출금(원)", False),
            ("note", "비고", False),
        ),
        "reports": (
            ("report", "보고서명", True),
            ("period", "기간", False),
            ("owner", "담당", False),
        ),
    }
    return forms.get(tab_id, forms["vouchers"])
