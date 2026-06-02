"""
core/bidding/service.py - 입찰·공고·견적 (나라장터·Procore·BidNet 유형 MVP)
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "bidding"

_EMPTY: dict[str, Any] = {
    "notices": [],
    "estimates": [],
    "submissions": [],
    "history": [],
    "seeded": False,
}

TAB_IDS = ("notices", "estimates", "submissions", "history")

TAB_LABELS = {
    "notices": "공고 관리",
    "estimates": "견적 산출",
    "submissions": "제출 일정",
    "history": "낙찰 이력",
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        return
    d = date.today()
    db["notices"] = [
        {
            "id": _new_id(),
            "notice_no": "2026-0421-001",
            "title": "시설 유지보수 용역",
            "agency": "한국앰코",
            "method": "일반경쟁",
            "deadline": (d + timedelta(days=12)).isoformat(),
            "budget": "120000000",
            "status": "검토중",
        },
        {
            "id": _new_id(),
            "notice_no": "2026-0415-008",
            "title": "청소·위생 도급",
            "agency": "코스그룹",
            "method": "제한경쟁",
            "deadline": (d + timedelta(days=5)).isoformat(),
            "budget": "48000000",
            "status": "참여예정",
        },
    ]
    db["estimates"] = [
        {
            "id": _new_id(),
            "notice_no": "2026-0421-001",
            "version": "v1",
            "direct_cost": "92000000",
            "margin_pct": "12",
            "bid_amount": "103040000",
            "status": "작성중",
            "owner": "원가팀",
        },
    ]
    db["submissions"] = [
        {
            "id": _new_id(),
            "notice_no": "2026-0421-001",
            "submit_date": (d + timedelta(days=11)).isoformat(),
            "channel": "나라장터",
            "docs": "제안서·가격서",
            "owner": "입찰팀",
            "status": "준비중",
        },
        {
            "id": _new_id(),
            "notice_no": "2026-0415-008",
            "submit_date": (d + timedelta(days=4)).isoformat(),
            "channel": "이메일",
            "docs": "견적서",
            "owner": "사업팀",
            "status": "제출완료",
        },
    ]
    db["history"] = [
        {
            "id": _new_id(),
            "notice_no": "2025-1208-003",
            "title": "보안·경비 용역",
            "result": "낙찰",
            "bid_amount": "356000000",
            "winner": "(주)코스",
            "closed_date": "2025-12-20",
        },
        {
            "id": _new_id(),
            "notice_no": "2025-0910-002",
            "title": "설비 정비",
            "result": "패찰",
            "bid_amount": "89000000",
            "winner": "A정비",
            "closed_date": "2025-09-25",
        },
    ]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def dashboard_kpis(tenant_id: str | None = None) -> list[tuple[str, str, str]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    active = sum(1 for n in db["notices"] if n.get("status") not in ("마감", "불참"))
    due = sum(
        1
        for s in db["submissions"]
        if s.get("status") != "제출완료"
        and s.get("submit_date", "") <= (date.today() + timedelta(days=7)).isoformat()
    )
    wins = sum(1 for h in db["history"] if h.get("result") == "낙찰")
    total = len(db["history"]) or 1
    return [
        ("진행 공고", str(active), "나라장터·수의형"),
        ("7일 내 제출", str(due), "일정 알림"),
        ("낙찰률", f"{wins * 100 // total}%", f"{wins}/{total}건"),
        ("견적 버전", str(len(db["estimates"])), "원가·마진"),
    ]


def list_records(tab_id: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    key = tab_id if tab_id in TAB_IDS else "notices"
    rows = list(db.get(key) or [])
    if key in ("notices", "submissions"):
        return sorted(rows, key=lambda r: r.get("deadline", r.get("submit_date", "")))
    return rows


def add_record(tab_id: str, fields: dict[str, str], tenant_id: str | None = None) -> dict[str, Any]:
    ensure_seed(tenant_id)
    tid = tenant_id or _tid()

    def _mut(data: dict[str, Any]) -> dict[str, Any]:
        rec: dict[str, Any] = {"id": _new_id()}
        if tab_id == "notices":
            rec.update(
                {
                    "notice_no": fields.get("notice_no") or f"{date.today():%Y-%m%d}-{len(data['notices'])+1:03d}",
                    "title": fields.get("title", ""),
                    "agency": fields.get("agency", ""),
                    "method": fields.get("method", "일반경쟁"),
                    "deadline": fields.get("deadline") or date.today().isoformat(),
                    "budget": fields.get("budget", "0"),
                    "status": fields.get("status", "검토중"),
                }
            )
            data["notices"].append(rec)
        elif tab_id == "estimates":
            direct = int(fields.get("direct_cost") or 0)
            margin = float(fields.get("margin_pct") or 10)
            bid = int(direct * (1 + margin / 100))
            rec.update(
                {
                    "notice_no": fields.get("notice_no", ""),
                    "version": fields.get("version") or "v1",
                    "direct_cost": str(direct),
                    "margin_pct": str(margin),
                    "bid_amount": str(bid),
                    "status": "작성중",
                    "owner": fields.get("owner", ""),
                }
            )
            data["estimates"].append(rec)
        elif tab_id == "submissions":
            rec.update(
                {
                    "notice_no": fields.get("notice_no", ""),
                    "submit_date": fields.get("submit_date") or date.today().isoformat(),
                    "channel": fields.get("channel", "나라장터"),
                    "docs": fields.get("docs", ""),
                    "owner": fields.get("owner", ""),
                    "status": "준비중",
                }
            )
            data["submissions"].append(rec)
        elif tab_id == "history":
            rec.update(
                {
                    "notice_no": fields.get("notice_no", ""),
                    "title": fields.get("title", ""),
                    "result": fields.get("result", "낙찰"),
                    "bid_amount": fields.get("bid_amount", "0"),
                    "winner": fields.get("winner", ""),
                    "closed_date": fields.get("closed_date") or date.today().isoformat(),
                }
            )
            data["history"].append(rec)
        return rec

    return mutate_module_db(MODULE, tid, _EMPTY, _mut)


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    cols = {
        "notices": (
            ("notice_no", "공고번호", 110),
            ("title", "공고명", 160),
            ("agency", "발주처", 90),
            ("method", "방식", 70),
            ("deadline", "마감", 90),
            ("budget", "예산", 90),
            ("status", "상태", 70),
        ),
        "estimates": (
            ("notice_no", "공고", 100),
            ("version", "Ver", 40),
            ("direct_cost", "직접비", 80),
            ("margin_pct", "마진%", 50),
            ("bid_amount", "투찰가", 90),
            ("status", "상태", 60),
            ("owner", "담당", 80),
        ),
        "submissions": (
            ("notice_no", "공고", 100),
            ("submit_date", "제출일", 90),
            ("channel", "제출처", 80),
            ("docs", "서류", 120),
            ("owner", "담당", 80),
            ("status", "상태", 70),
        ),
        "history": (
            ("notice_no", "공고", 100),
            ("title", "공고명", 140),
            ("result", "결과", 50),
            ("bid_amount", "투찰/계약", 90),
            ("winner", "낙찰자", 90),
            ("closed_date", "마감일", 90),
        ),
    }
    return cols.get(tab_id, cols["notices"])


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    forms = {
        "notices": (
            ("title", "공고명", True),
            ("agency", "발주처", False),
            ("deadline", "마감일", False),
            ("budget", "예산(원)", False),
        ),
        "estimates": (
            ("notice_no", "공고번호", True),
            ("direct_cost", "직접비(원)", True),
            ("margin_pct", "마진(%)", False),
            ("owner", "담당", False),
        ),
        "submissions": (
            ("notice_no", "공고번호", True),
            ("submit_date", "제출일", False),
            ("channel", "제출처", False),
            ("owner", "담당", False),
        ),
        "history": (
            ("title", "공고명", True),
            ("result", "결과(낙찰/패찰)", False),
            ("bid_amount", "금액(원)", False),
            ("winner", "낙찰자", False),
        ),
    }
    return forms.get(tab_id, forms["notices"])
