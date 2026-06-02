"""
core/recruitment/service.py - 채용 · 마당 (법인 채용공고·지원·채널 관리 MVP)

추후 고용24·SNS API 연동을 위한 채널 레코드·상태 필드를 포함합니다.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "recruitment"

# 게시 상태
STATUS_DRAFT = "작성중"
STATUS_PENDING = "승인대기"
STATUS_LIVE = "게시중"
STATUS_CLOSED = "마감"
STATUS_WITHDRAWN = "철회"

# 채널 (API 연동 예정)
CHANNEL_BITWEEN = "Bitween 채용마당"
CHANNEL_WORK24 = "고용24"
CHANNEL_SNS = "SNS(링크)"
CHANNEL_INTERNAL = "사내 게시"

CHANNEL_PENDING = "연동예정"
CHANNEL_QUEUED = "게시대기"
CHANNEL_LIVE = "게시중"
CHANNEL_FAILED = "실패"
CHANNEL_MANUAL = "수동완료"

_EMPTY: dict[str, Any] = {
    "postings": [],
    "applications": [],
    "channels": [],
    "seeded": False,
}

TAB_IDS = ("postings", "marketplace", "applications", "channels")

TAB_LABELS = {
    "postings": "채용공고",
    "marketplace": "채용마당",
    "applications": "지원 접수",
    "channels": "채널 · 홍보",
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return date.today().isoformat()


def _postings(db: dict[str, Any]) -> list[dict[str, Any]]:
    return list(db.get("postings") or [])


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        return
    d = date.today()
    p1 = _new_id()
    p2 = _new_id()
    db["postings"] = [
        {
            "id": p1,
            "legal_entity": "COSS",
            "department": "경영지원 · 재무",
            "title": "재무·회계 담당 (정규직)",
            "employment_type": "정규직",
            "workplace": "서울 강남",
            "headcount": "1",
            "salary_note": "면접 후 협의 (회사 내규)",
            "deadline": (d + timedelta(days=21)).isoformat(),
            "status": STATUS_LIVE,
            "posted_date": d.isoformat(),
            "contact": "인사팀 coss_hr@example.com",
            "summary": "법인 회계·자금·세무 보조, 전자결재·급여 연동 업무",
        },
        {
            "id": p2,
            "legal_entity": "ELSO",
            "department": "정비사업부",
            "title": "설비 정비 기사",
            "employment_type": "정규직",
            "workplace": "경기 화성",
            "headcount": "2",
            "salary_note": "경력 3년↑ 우대",
            "deadline": (d + timedelta(days=14)).isoformat(),
            "status": STATUS_LIVE,
            "posted_date": (d - timedelta(days=3)).isoformat(),
            "contact": "정비팀 elso_maint@example.com",
            "summary": "CMMS·예방정비·작업지시 운영",
        },
        {
            "id": _new_id(),
            "legal_entity": "COSS",
            "department": "인사팀",
            "title": "HR·노무 담당",
            "employment_type": "정규직",
            "workplace": "서울",
            "headcount": "1",
            "salary_note": "협의",
            "deadline": (d + timedelta(days=30)).isoformat(),
            "status": STATUS_PENDING,
            "posted_date": "",
            "contact": "인사팀",
            "summary": "명부·연차·채용·노무 실무",
        },
    ]
    db["applications"] = [
        {
            "id": _new_id(),
            "posting_title": "재무·회계 담당 (정규직)",
            "applicant_name": "홍길동",
            "apply_date": (d - timedelta(days=2)).isoformat(),
            "channel": CHANNEL_BITWEEN,
            "status": "서류검토",
            "note": "",
        },
        {
            "id": _new_id(),
            "posting_title": "설비 정비 기사",
            "applicant_name": "김기술",
            "apply_date": (d - timedelta(days=1)).isoformat(),
            "channel": "지인 추천",
            "status": "1차면접",
            "note": "자격증 보유",
        },
    ]
    db["channels"] = [
        {
            "id": _new_id(),
            "posting_title": "재무·회계 담당 (정규직)",
            "channel": CHANNEL_BITWEEN,
            "status": CHANNEL_LIVE,
            "external_url": "bitween://recruitment/live",
            "published_at": d.isoformat(),
            "note": "플랫폼 내 채용마당 게시",
        },
        {
            "id": _new_id(),
            "posting_title": "재무·회계 담당 (정규직)",
            "channel": CHANNEL_WORK24,
            "status": CHANNEL_PENDING,
            "external_url": "",
            "published_at": "",
            "note": "API 연동 후 자동 게시 예정",
        },
        {
            "id": _new_id(),
            "posting_title": "설비 정비 기사",
            "channel": CHANNEL_SNS,
            "status": CHANNEL_MANUAL,
            "external_url": "",
            "published_at": d.isoformat(),
            "note": "링크 공유·수동 게시",
        },
    ]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def dashboard_kpis() -> list[tuple[str, str, str]]:
    ensure_seed()
    db = load_module_db(MODULE, _tid(), _EMPTY)
    posts = _postings(db)
    live = sum(1 for p in posts if p.get("status") == STATUS_LIVE)
    pending = sum(1 for p in posts if p.get("status") == STATUS_PENDING)
    apps = db.get("applications") or []
    reviewing = sum(1 for a in apps if a.get("status") in ("서류검토", "1차면접", "2차면접"))
    ch = db.get("channels") or []
    api_ready = sum(1 for c in ch if c.get("status") == CHANNEL_PENDING)
    return [
        ("채용공고", str(len(posts)), f"게시 {live} · 대기 {pending}"),
        ("채용마당", str(live), "플랫폼 내 공개"),
        ("지원 접수", str(len(apps)), f"진행 {reviewing}건"),
        ("채널", str(len(ch)), f"API연동예정 {api_ready}"),
    ]


def list_records(tab_id: str) -> list[dict[str, Any]]:
    ensure_seed()
    db = load_module_db(MODULE, _tid(), _EMPTY)
    if tab_id == "postings":
        return _postings(db)
    if tab_id == "marketplace":
        return [p for p in _postings(db) if p.get("status") == STATUS_LIVE]
    if tab_id == "applications":
        return list(db.get("applications") or [])
    if tab_id == "channels":
        return list(db.get("channels") or [])
    return []


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    specs: dict[str, tuple[tuple[str, str, int], ...]] = {
        "postings": (
            ("legal_entity", "법인", 70),
            ("department", "부서", 100),
            ("title", "공고명", 160),
            ("employment_type", "고용", 60),
            ("workplace", "근무지", 80),
            ("deadline", "마감", 90),
            ("status", "상태", 70),
        ),
        "marketplace": (
            ("legal_entity", "법인", 70),
            ("title", "공고명", 180),
            ("department", "부서", 100),
            ("employment_type", "고용", 60),
            ("workplace", "근무지", 80),
            ("deadline", "마감", 90),
            ("contact", "문의", 120),
        ),
        "applications": (
            ("posting_title", "공고", 140),
            ("applicant_name", "지원자", 80),
            ("apply_date", "접수일", 90),
            ("channel", "유입", 90),
            ("status", "상태", 70),
            ("note", "비고", 120),
        ),
        "channels": (
            ("posting_title", "공고", 140),
            ("channel", "채널", 110),
            ("status", "상태", 80),
            ("published_at", "게시일", 90),
            ("external_url", "URL", 120),
            ("note", "비고", 140),
        ),
    }
    return specs.get(tab_id, (("id", "ID", 80),))


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    forms: dict[str, tuple[tuple[str, str, bool], ...]] = {
        "postings": (
            ("legal_entity", "법인명", True),
            ("department", "채용 부서", True),
            ("title", "공고명", True),
            ("employment_type", "고용형태(정규/계약/인턴)", True),
            ("workplace", "근무지", True),
            ("headcount", "채용 인원", False),
            ("salary_note", "임금·처우", True),
            ("deadline", "마감일(YYYY-MM-DD)", True),
            ("contact", "문의처", True),
            ("summary", "업무 요약", False),
        ),
        "applications": (
            ("posting_title", "공고명", True),
            ("applicant_name", "지원자 성명", True),
            ("channel", "유입 채널", False),
            ("note", "비고", False),
        ),
        "channels": (
            ("posting_title", "공고명", True),
            ("channel", "채널(Bitween/고용24/SNS 등)", True),
            ("note", "메모", False),
        ),
        "marketplace": (
            ("legal_entity", "법인명", True),
            ("department", "채용 부서", True),
            ("title", "공고명", True),
            ("employment_type", "고용형태", True),
            ("workplace", "근무지", True),
            ("deadline", "마감일(YYYY-MM-DD)", True),
            ("contact", "문의처", True),
        ),
    }
    return forms.get(tab_id, (("note", "내용", True),))


def add_record(tab_id: str, values: dict[str, str]) -> dict[str, Any]:
    ensure_seed()
    key_map = {
        "postings": "postings",
        "marketplace": "postings",
        "applications": "applications",
        "channels": "channels",
    }
    store_key = key_map.get(tab_id)
    if not store_key:
        raise ValueError(f"등록 불가 탭: {tab_id}")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = {"id": _new_id(), **values}
        if tab_id in ("postings", "marketplace"):
            row.setdefault("status", STATUS_DRAFT)
            row.setdefault("posted_date", "")
            if tab_id == "marketplace":
                row["status"] = STATUS_LIVE
                row["posted_date"] = _today()
        if tab_id == "applications":
            row.setdefault("apply_date", _today())
            row.setdefault("status", "서류검토")
            row.setdefault("channel", CHANNEL_BITWEEN)
        if tab_id == "channels":
            row.setdefault("status", CHANNEL_QUEUED)
            row.setdefault("external_url", "")
            row.setdefault("published_at", "")
        db.setdefault(store_key, []).append(row)
        return row

    return mutate_module_db(MODULE, _tid(), _EMPTY, mut)
