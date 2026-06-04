"""
core/kpi/service.py - KPI · 경영 (법인 / 사업장 / 개인)

임원용 손익·KPI 집계. 추후 회계·급여·인사 API 연동 및 실시간 갱신.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id

MODULE = "kpi"

STATUS_OK = "정상"
STATUS_WARN = "주의"
STATUS_CRITICAL = "위험"

_EMPTY: dict[str, Any] = {
    "sites": [],
    "entities": [],
    "individual": [],
    "alerts": [],
    "seeded": False,
}

TAB_IDS = ("map", "entities", "sites", "individual", "alerts")

TAB_LABELS = {
    "map": "경영 지도",
    "entities": "법인 손익",
    "sites": "사업장",
    "individual": "개인 KPI",
    "alerts": "이슈 · 알림",
}

RECORD_TAB_IDS = ("entities", "sites", "individual", "alerts")

# 지역별 지도 좌표 (사업장 100+일 때 지역 단위로만 표시)
REGION_META: dict[str, dict[str, Any]] = {
    "서울": {"label": "서울·수도권", "map_x": 0.48, "map_y": 0.28},
    "경기": {"label": "경기", "map_x": 0.38, "map_y": 0.40},
    "인천": {"label": "인천", "map_x": 0.30, "map_y": 0.32},
    "부산": {"label": "부산·경남", "map_x": 0.76, "map_y": 0.82},
    "대구": {"label": "대구·경북", "map_x": 0.60, "map_y": 0.58},
    "광주": {"label": "광주·전라", "map_x": 0.34, "map_y": 0.72},
    "대전": {"label": "대전·충청", "map_x": 0.42, "map_y": 0.52},
    "울산": {"label": "울산", "map_x": 0.78, "map_y": 0.70},
    "강원": {"label": "강원", "map_x": 0.55, "map_y": 0.20},
    "제주": {"label": "제주", "map_x": 0.28, "map_y": 0.92},
    "기타": {"label": "기타", "map_x": 0.50, "map_y": 0.50},
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _won_short(n: int) -> str:
    if abs(n) >= 100_000_000:
        return f"{n / 100_000_000:+.1f}억"
    if abs(n) >= 10_000:
        return f"{n / 10_000:+,.0f}만"
    return f"{n:+,}"


def _parse_margin_pct(value: Any) -> float:
    """숫자·'+12.7%' 문자열 모두 허용."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().rstrip("%").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _default_entities(period: str) -> list[dict[str, Any]]:
    return [
        {
            "id": _new_id(),
            "legal_entity": "(주)코스",
            "code": "COSS",
            "revenue": 4_820_000_000,
            "cost": 4_210_000_000,
            "profit": 610_000_000,
            "margin_pct": 12.7,
            "status": STATUS_OK,
            "period": period,
        },
        {
            "id": _new_id(),
            "legal_entity": "ELSO",
            "code": "ELSO",
            "revenue": 1_240_000_000,
            "cost": 1_080_000_000,
            "profit": 160_000_000,
            "margin_pct": 12.9,
            "status": STATUS_OK,
            "period": period,
        },
        {
            "id": _new_id(),
            "legal_entity": "청운",
            "code": "CHEONGUN",
            "revenue": 680_000_000,
            "cost": 710_000_000,
            "profit": -30_000_000,
            "margin_pct": -4.4,
            "status": STATUS_CRITICAL,
            "period": period,
        },
    ]


def _region_status(sites: list[dict[str, Any]]) -> str:
    if any(s.get("status") == STATUS_CRITICAL for s in sites):
        return STATUS_CRITICAL
    if any(s.get("status") == STATUS_WARN for s in sites):
        return STATUS_WARN
    return STATUS_OK


def _bulk_demo_sites(period_seed: int) -> list[dict[str, Any]]:
    """데모용 — 지역별 다수 사업장 (실데이터 연동 시 대체)."""
    specs: list[tuple[str, int, str, float, float]] = [
        ("서울", 14, "(주)코스", 0.46, 0.30),
        ("경기", 28, "ELSO", 0.36, 0.42),
        ("인천", 10, "ELSO", 0.28, 0.34),
        ("부산", 16, "(주)코스", 0.74, 0.80),
        ("대구", 12, "청운", 0.58, 0.60),
        ("광주", 8, "(주)코스", 0.32, 0.74),
        ("대전", 9, "ELSO", 0.40, 0.54),
        ("울산", 7, "(주)코스", 0.76, 0.68),
        ("강원", 6, "청운", 0.52, 0.22),
        ("제주", 4, "(주)코스", 0.26, 0.90),
    ]
    out: list[dict[str, Any]] = []
    idx = 0
    for region, count, entity, bx, by in specs:
        meta = REGION_META.get(region, REGION_META["기타"])
        for n in range(1, count + 1):
            idx += 1
            base_rev = 80_000_000 + (idx * 17_000_000) % 420_000_000
            margin_roll = (idx * 13 + period_seed) % 100
            if margin_roll < 8:
                margin = -4.0 - (idx % 5)
                status = STATUS_CRITICAL
            elif margin_roll < 22:
                margin = 3.0 + (idx % 4)
                status = STATUS_WARN
            else:
                margin = 8.0 + (idx % 12)
                status = STATUS_OK
            cost = int(base_rev / (1 + margin / 100))
            profit = base_rev - cost
            jitter_x = ((idx * 7) % 20 - 10) / 200
            jitter_y = ((idx * 11) % 20 - 10) / 200
            note = ""
            if status == STATUS_CRITICAL:
                note = "적자 · 구조조정 검토"
            elif status == STATUS_WARN:
                note = "마진 하락 · KPI 미달"
            out.append(
                {
                    "id": _new_id(),
                    "site_name": f"{meta['label'].split('·')[0]} 현장 {n:02d}",
                    "legal_entity": entity,
                    "region": region,
                    "map_x": min(0.92, max(0.08, bx + jitter_x)),
                    "map_y": min(0.92, max(0.08, by + jitter_y)),
                    "revenue": base_rev,
                    "cost": cost,
                    "profit": profit,
                    "margin_pct": round(margin, 1),
                    "status": status,
                    "headcount": 8 + (idx % 45),
                    "note": note,
                }
            )
    return out


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        changed = False
        if len(db.get("sites") or []) < 50:
            db["sites"] = list(db.get("sites") or [])
            db["sites"].extend(_bulk_demo_sites(date.today().month))
            changed = True
        if not db.get("entities"):
            db["entities"] = _default_entities(date.today().strftime("%Y-%m"))
            changed = True
        if changed:
            save_module_db(MODULE, tid, db)
        return
    existing_individual = list(db.get("individual") or [])
    period = date.today().strftime("%Y-%m")
    db["entities"] = _default_entities(period)
    db["sites"] = [
        {
            "id": _new_id(),
            "site_name": "서울 강남 본사",
            "legal_entity": "(주)코스",
            "region": "서울",
            "map_x": 0.48,
            "map_y": 0.38,
            "revenue": 2_100_000_000,
            "cost": 1_820_000_000,
            "profit": 280_000_000,
            "margin_pct": 13.3,
            "status": STATUS_OK,
            "headcount": 42,
            "note": "",
        },
        {
            "id": _new_id(),
            "site_name": "화성 정비사업장",
            "legal_entity": "ELSO",
            "region": "경기",
            "map_x": 0.42,
            "map_y": 0.42,
            "revenue": 980_000_000,
            "cost": 850_000_000,
            "profit": 130_000_000,
            "margin_pct": 13.3,
            "status": STATUS_OK,
            "headcount": 68,
            "note": "",
        },
        {
            "id": _new_id(),
            "site_name": "부산 AMKR 현장",
            "legal_entity": "(주)코스",
            "region": "부산",
            "map_x": 0.72,
            "map_y": 0.78,
            "revenue": 520_000_000,
            "cost": 490_000_000,
            "profit": 30_000_000,
            "margin_pct": 5.8,
            "status": STATUS_WARN,
            "headcount": 35,
            "note": "원가율 상승 · KPI 미달",
        },
        {
            "id": _new_id(),
            "site_name": "대구 물류센터",
            "legal_entity": "청운",
            "region": "대구",
            "map_x": 0.58,
            "map_y": 0.62,
            "revenue": 410_000_000,
            "cost": 445_000_000,
            "profit": -35_000_000,
            "margin_pct": -8.5,
            "status": STATUS_CRITICAL,
            "headcount": 22,
            "note": "적자 · 구조조정 검토",
        },
        {
            "id": _new_id(),
            "site_name": "인천 입항 현장",
            "legal_entity": "ELSO",
            "region": "인천",
            "map_x": 0.38,
            "map_y": 0.35,
            "revenue": 260_000_000,
            "cost": 230_000_000,
            "profit": 30_000_000,
            "margin_pct": 11.5,
            "status": STATUS_OK,
            "headcount": 18,
            "note": "",
        },
    ]
    db["sites"].extend(_bulk_demo_sites(date.today().month))
    default_individual = [
        {
            "id": _new_id(),
            "employee_name": "김민수",
            "org_unit": "재무팀",
            "site_name": "서울 강남 본사",
            "kpi_name": "월마감 정확도",
            "target": "100%",
            "actual": "98%",
            "score": 92,
            "payroll_link": "예정",
            "status": STATUS_OK,
        },
        {
            "id": _new_id(),
            "employee_name": "박철수",
            "org_unit": "정비사업부",
            "site_name": "화성 정비사업장",
            "kpi_name": "WO 완료율",
            "target": "95%",
            "actual": "88%",
            "score": 78,
            "payroll_link": "예정",
            "status": STATUS_WARN,
        },
        {
            "id": _new_id(),
            "employee_name": "이영희",
            "org_unit": "인사팀",
            "site_name": "서울 강남 본사",
            "kpi_name": "채용 리드타임",
            "target": "30일",
            "actual": "24일",
            "score": 105,
            "payroll_link": "연동",
            "status": STATUS_OK,
        },
    ]
    seen_keys = {str(row.get("source_key") or row.get("id") or "") for row in default_individual}
    for row in existing_individual:
        key = str(row.get("source_key") or row.get("id") or "")
        if key and key in seen_keys:
            continue
        default_individual.append(row)
        if key:
            seen_keys.add(key)
    db["individual"] = default_individual
    db["alerts"] = [
        {
            "id": _new_id(),
            "site_name": "대구 물류센터",
            "legal_entity": "청운",
            "severity": "위험",
            "title": "월간 적자 지속",
            "message": "2개월 연속 적자 — 원가·인력 재배치 검토 필요",
            "occurred_date": date.today().isoformat(),
            "status": "미조치",
        },
        {
            "id": _new_id(),
            "site_name": "부산 AMKR 현장",
            "legal_entity": "(주)코스",
            "severity": "주의",
            "title": "매출총이익률 하락",
            "message": "전월 대비 마진 -3.2%p — 현장 KPI 2건 미달",
            "occurred_date": date.today().isoformat(),
            "status": "검토중",
        },
    ]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def _db() -> dict[str, Any]:
    ensure_seed()
    return load_module_db(MODULE, _tid(), _EMPTY)


def dashboard_kpis() -> list[tuple[str, str, str]]:
    db = _db()
    sites = db.get("sites") or []
    alerts = db.get("alerts") or []
    rev = sum(int(s.get("revenue") or 0) for s in sites)
    profit = sum(int(s.get("profit") or 0) for s in sites)
    margin = (profit / rev * 100) if rev else 0
    issues = sum(1 for s in sites if s.get("status") in (STATUS_WARN, STATUS_CRITICAL))
    trip_reflections = sum(1 for row in db.get("individual") or [] if row.get("source") == "business_trip")
    return [
        ("총 매출", _won_short(rev), f"사업장 {len(sites)}곳"),
        ("총 이익", _won_short(profit), f"평균 마진 {margin:.1f}%"),
        ("이슈 사업장", str(issues), f"알림 {len(alerts)}건"),
        ("개인 KPI", str(len(db.get("individual") or [])), f"출장 실적 {trip_reflections}건 반영"),
    ]


def executive_summary() -> dict[str, Any]:
    db = _db()
    sites = list(db.get("sites") or [])
    return {
        "sites": sites,
        "alerts": list(db.get("alerts") or []),
        "entity_count": len(db.get("entities") or []),
        "issue_count": sum(1 for s in sites if s.get("status") != STATUS_OK),
    }


def list_records(tab_id: str) -> list[dict[str, Any]]:
    db = _db()
    key_map = {
        "entities": "entities",
        "sites": "sites",
        "individual": "individual",
        "alerts": "alerts",
    }
    raw = list(db.get(key_map.get(tab_id, "")) or [])
    rows: list[dict[str, Any]] = []
    for row in raw:
        item = dict(row)
        if tab_id in ("entities", "sites"):
            for key in ("revenue", "cost", "profit"):
                if key in item and item[key] not in ("", None):
                    try:
                        item[key] = _won_short(int(item[key]))
                    except (TypeError, ValueError):
                        pass
            if "margin_pct" in item:
                item["margin_pct"] = f"{_parse_margin_pct(item.get('margin_pct')):+.1f}%"
        rows.append(item)
    return rows


def upsert_business_trip_reflection(tenant_id: str, trip: dict[str, Any]) -> dict[str, Any]:
    """Reflect one completed business trip into the individual KPI dataset.

    The source key makes the adapter idempotent: repeated workflow reflection
    updates the same KPI row instead of duplicating 실적 records.
    """
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    rows: list[dict[str, Any]] = list(db.get("individual") or [])
    trip_id = str(trip.get("trip_id") or trip.get("id") or "").strip()
    source_key = f"business_trip:{trip_id}"
    existing = next((row for row in rows if row.get("source_key") == source_key), None)
    now = date.today().isoformat()
    row = {
        "id": str((existing or {}).get("id") or _new_id()),
        "employee_name": str(trip.get("executor_id") or trip.get("requester_id") or ""),
        "org_unit": str(trip.get("department_id") or ""),
        "site_name": str(trip.get("site_id") or ""),
        "kpi_name": "출장 실적 반영",
        "target": "출장 완료",
        "actual": str(trip.get("title") or trip_id),
        "score": 100,
        "payroll_link": "연동",
        "status": STATUS_OK,
        "source": "business_trip",
        "source_key": source_key,
        "trip_id": trip_id,
        "document_id": str(trip.get("approved_document_id") or ""),
        "reflected_at": now,
    }
    if existing is None:
        rows.append(row)
    else:
        existing.update(row)
        row = dict(existing)
    db["individual"] = rows
    save_module_db(MODULE, tid, db)
    return dict(row)


def list_sites() -> list[dict[str, Any]]:
    db = _db()
    return list(db.get("sites") or [])


def list_sites_by_region(region: str) -> list[dict[str, Any]]:
    return [s for s in list_sites() if str(s.get("region") or "") == region]


def aggregate_regions() -> list[dict[str, Any]]:
    """사업장을 지역 단위로 집계 — 지도에는 이 결과만 표시."""
    by_region: dict[str, list[dict[str, Any]]] = {}
    for site in list_sites():
        region = str(site.get("region") or "기타")
        by_region.setdefault(region, []).append(site)

    rows: list[dict[str, Any]] = []
    for region, group in by_region.items():
        meta = REGION_META.get(region, REGION_META["기타"])
        rev = sum(int(s.get("revenue") or 0) for s in group)
        cost = sum(int(s.get("cost") or 0) for s in group)
        profit = sum(int(s.get("profit") or 0) for s in group)
        margin = (profit / rev * 100) if rev else 0.0
        issues = sum(1 for s in group if s.get("status") in (STATUS_WARN, STATUS_CRITICAL))
        sorted_sites = sorted(
            group,
            key=lambda s: (
                0 if s.get("status") == STATUS_CRITICAL else 1 if s.get("status") == STATUS_WARN else 2,
                int(s.get("profit") or 0),
            ),
        )
        rows.append(
            {
                "id": region,
                "region": region,
                "label": meta["label"],
                "map_x": meta["map_x"],
                "map_y": meta["map_y"],
                "site_count": len(group),
                "revenue": rev,
                "cost": cost,
                "profit": profit,
                "margin_pct": round(margin, 1),
                "status": _region_status(group),
                "issue_count": issues,
                "sites": sorted_sites,
            }
        )
    rows.sort(key=lambda r: (-int(r.get("issue_count") or 0), -abs(int(r.get("profit") or 0))))
    return rows


def get_site(site_id: str) -> dict[str, Any] | None:
    for s in list_sites():
        if s.get("id") == site_id:
            return s
    return None


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    specs: dict[str, tuple[tuple[str, str, int], ...]] = {
        "entities": (
            ("legal_entity", "법인", 90),
            ("revenue", "매출", 90),
            ("cost", "비용", 90),
            ("profit", "이익", 80),
            ("margin_pct", "마진%", 60),
            ("status", "상태", 60),
        ),
        "sites": (
            ("site_name", "사업장", 120),
            ("legal_entity", "법인", 80),
            ("region", "지역", 60),
            ("profit", "이익", 80),
            ("margin_pct", "마진%", 60),
            ("status", "상태", 60),
        ),
        "individual": (
            ("employee_name", "성명", 80),
            ("org_unit", "부서", 80),
            ("site_name", "사업장", 100),
            ("kpi_name", "KPI", 100),
            ("actual", "실적", 60),
            ("score", "점수", 50),
            ("payroll_link", "급여연동", 70),
            ("status", "상태", 60),
        ),
        "alerts": (
            ("severity", "등급", 50),
            ("site_name", "사업장", 110),
            ("title", "제목", 120),
            ("message", "내용", 180),
            ("status", "조치", 60),
        ),
    }
    return specs.get(tab_id, (("id", "ID", 80),))


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    return (("note", "메모", True),)


def add_record(tab_id: str, values: dict[str, str]) -> dict[str, Any]:
    raise NotImplementedError("KPI 데이터는 회계·현장 시스템 연동 후 등록됩니다.")
