"""
core/maintenance/service.py - 정비 사업부 데이터 (작업지시·설비·일정·부품)

시장 참고: Fiix CMMS, UpKeep, SAP PM, IBM Maximo — 작업지시·예방정비·부품재고 중심.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "maintenance"

_EMPTY: dict[str, Any] = {
    "work_orders": [],
    "assets": [],
    "schedules": [],
    "parts": [],
    "seeded": False,
}

TAB_IDS = ("work_orders", "assets", "schedules", "parts")

TAB_LABELS = {
    "work_orders": "작업 지시",
    "assets": "설비 이력",
    "schedules": "정비 일정",
    "parts": "부품 재고",
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return date.today().isoformat()


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        return
    d = date.today()
    db["assets"] = [
        {
            "id": _new_id(),
            "code": "EQ-AC-001",
            "name": "냉각수 펌프 A",
            "site": "한국앰코생산",
            "status": "가동",
            "last_service": (d - timedelta(days=45)).isoformat(),
            "note": "월 1회 점검",
        },
        {
            "id": _new_id(),
            "code": "EQ-HVAC-02",
            "name": "공조기 2호",
            "site": "코스 본사",
            "status": "가동",
            "last_service": (d - timedelta(days=12)).isoformat(),
            "note": "필터 교체 주기 3개월",
        },
    ]
    db["work_orders"] = [
        {
            "id": _new_id(),
            "wo_no": "WO-2026-0142",
            "title": "펌프 A 베어링 점검",
            "priority": "보통",
            "status": "진행중",
            "assignee": "정비팀 김OO",
            "due_date": (d + timedelta(days=3)).isoformat(),
            "site": "한국앰코생산",
        },
        {
            "id": _new_id(),
            "wo_no": "WO-2026-0143",
            "title": "공조기 필터 교체",
            "priority": "낮음",
            "status": "대기",
            "assignee": "외주 A사",
            "due_date": (d + timedelta(days=7)).isoformat(),
            "site": "코스 본사",
        },
    ]
    db["schedules"] = [
        {
            "id": _new_id(),
            "plan": "예방정비 — 펌프 A",
            "cycle": "월 1회",
            "next_date": (d + timedelta(days=10)).isoformat(),
            "owner": "정비팀",
            "site": "한국앰코생산",
        },
        {
            "id": _new_id(),
            "plan": "법정검사 — 압력용기",
            "cycle": "연 1회",
            "next_date": (d + timedelta(days=45)).isoformat(),
            "owner": "안전관리",
            "site": "한국앰코생산",
        },
    ]
    db["parts"] = [
        {
            "id": _new_id(),
            "sku": "BRG-6205",
            "name": "베어링 6205",
            "qty": 8,
            "min_qty": 4,
            "location": "창고 A-3",
            "vendor": "SKF",
        },
        {
            "id": _new_id(),
            "sku": "FLT-HVAC-01",
            "name": "공조 필터",
            "qty": 2,
            "min_qty": 6,
            "location": "창고 B-1",
            "vendor": "대한필터",
        },
    ]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def dashboard_kpis(tenant_id: str | None = None) -> list[tuple[str, str, str]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    open_wo = sum(1 for w in db["work_orders"] if w.get("status") not in ("완료", "취소"))
    due_soon = sum(
        1
        for s in db["schedules"]
        if s.get("next_date", "") <= (date.today() + timedelta(days=14)).isoformat()
    )
    low_stock = sum(1 for p in db["parts"] if int(p.get("qty", 0)) < int(p.get("min_qty", 0)))
    return [
        ("진행 작업지시", str(open_wo), "Fiix·SAP PM형 WO"),
        ("14일 내 정비", str(due_soon), "예방정비 일정"),
        ("부족 재고", str(low_stock), "최소재고 미만"),
        ("등록 설비", str(len(db["assets"])), "자산·이력"),
    ]


def list_records(tab_id: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    key = tab_id if tab_id in TAB_IDS else "work_orders"
    rows = list(db.get(key) or [])
    if key == "work_orders":
        return sorted(rows, key=lambda r: r.get("due_date", ""))
    if key == "schedules":
        return sorted(rows, key=lambda r: r.get("next_date", ""))
    if key == "parts":
        return sorted(rows, key=lambda r: r.get("name", ""))
    return rows


def add_record(tab_id: str, fields: dict[str, str], tenant_id: str | None = None) -> dict[str, Any]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()

    def _mut(data: dict[str, Any]) -> dict[str, Any]:
        rec: dict[str, Any] = {"id": _new_id()}
        if tab_id == "work_orders":
            rec.update(
                {
                    "wo_no": fields.get("wo_no") or f"WO-{date.today().year}-{len(data['work_orders'])+1:04d}",
                    "title": fields.get("title", ""),
                    "priority": fields.get("priority", "보통"),
                    "status": fields.get("status", "대기"),
                    "assignee": fields.get("assignee", ""),
                    "due_date": fields.get("due_date") or _today(),
                    "site": fields.get("site", ""),
                }
            )
            data["work_orders"].append(rec)
        elif tab_id == "assets":
            rec.update(
                {
                    "code": fields.get("code", ""),
                    "name": fields.get("name", ""),
                    "site": fields.get("site", ""),
                    "status": fields.get("status", "가동"),
                    "last_service": fields.get("last_service") or _today(),
                    "note": fields.get("note", ""),
                }
            )
            data["assets"].append(rec)
        elif tab_id == "schedules":
            rec.update(
                {
                    "plan": fields.get("plan", ""),
                    "cycle": fields.get("cycle", "월 1회"),
                    "next_date": fields.get("next_date") or _today(),
                    "owner": fields.get("owner", ""),
                    "site": fields.get("site", ""),
                }
            )
            data["schedules"].append(rec)
        elif tab_id == "parts":
            rec.update(
                {
                    "sku": fields.get("sku", ""),
                    "name": fields.get("name", ""),
                    "qty": int(fields.get("qty") or 0),
                    "min_qty": int(fields.get("min_qty") or 0),
                    "location": fields.get("location", ""),
                    "vendor": fields.get("vendor", ""),
                }
            )
            data["parts"].append(rec)
        return rec

    return mutate_module_db(MODULE, tid, _EMPTY, _mut)


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    cols = {
        "work_orders": (
            ("wo_no", "지시번호", 100),
            ("title", "작업명", 180),
            ("status", "상태", 70),
            ("priority", "우선", 60),
            ("assignee", "담당", 90),
            ("due_date", "완료예정", 90),
            ("site", "사업장", 100),
        ),
        "assets": (
            ("code", "설비코드", 90),
            ("name", "설비명", 140),
            ("site", "사업장", 100),
            ("status", "상태", 60),
            ("last_service", "최근정비", 90),
            ("note", "비고", 160),
        ),
        "schedules": (
            ("plan", "정비계획", 180),
            ("cycle", "주기", 70),
            ("next_date", "다음일정", 90),
            ("owner", "담당", 90),
            ("site", "사업장", 100),
        ),
        "parts": (
            ("sku", "품번", 90),
            ("name", "품명", 140),
            ("qty", "재고", 50),
            ("min_qty", "최소", 50),
            ("location", "위치", 80),
            ("vendor", "공급처", 100),
        ),
    }
    return cols.get(tab_id, cols["work_orders"])


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    """(field_key, label, required)"""
    forms = {
        "work_orders": (
            ("title", "작업명", True),
            ("assignee", "담당", False),
            ("due_date", "완료예정(YYYY-MM-DD)", False),
            ("site", "사업장", False),
        ),
        "assets": (
            ("code", "설비코드", True),
            ("name", "설비명", True),
            ("site", "사업장", False),
            ("note", "비고", False),
        ),
        "schedules": (
            ("plan", "정비계획", True),
            ("cycle", "주기", False),
            ("next_date", "다음일정", False),
            ("owner", "담당", False),
        ),
        "parts": (
            ("sku", "품번", True),
            ("name", "품명", True),
            ("qty", "재고수량", False),
            ("min_qty", "최소재고", False),
            ("location", "보관위치", False),
        ),
    }
    return forms.get(tab_id, forms["work_orders"])
