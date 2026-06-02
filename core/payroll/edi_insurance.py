"""
core/payroll/edi_insurance.py - 사대보험 EDI 4대보험료 조회·적용

Phase 1 (현재): EDI 포털에서 내려받은 CSV/Excel 보험료 명세 import, 수동 등록.
Phase 2: EdiWebServiceProvider — 공인인증서·공단 제휴 EDI 웹서비스 연동 (미구현).

사대보험 EDI(국민연금·건강보험·고용·산재)는 사업자 등록, 공인/공동인증서,
공단별 EDI 클라이언트 또는 웹서비스 이용계약이 필요하며 임의 데스크톱용 공개 REST API가
아닙니다. 본 모듈은 import·수동 경로를 기본으로 합니다.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import threading
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from core.hr.traffic_signal import mask_rrn, normalize_rrn
from core.org_config import canonical_scope_workplace
from core.paths import app_data_dir
from core.session_service import session_tenant_id
from services.payroll_settings_store import _site_entry, get_edi_insurance_config
from utils import round_won, safe_number

PremiumSource = Literal["manual", "import", "api", "calculated"]
PeriodKey = str  # YYYY-MM

_EDI_ROOT = app_data_dir() / "edi_insurance"
_lock = threading.Lock()

# 공단 EDI·포털 안내 URL
NPS_EDI_URL = "https://www.nps.or.kr"
NHIS_EDI_URL = "https://www.nhis.or.kr"
KCOMWEL_EDI_URL = "https://total.kcomwel.or.kr"

SOURCE_LABELS: dict[str, str] = {
    "manual": "수동 등록",
    "import": "CSV 가져오기",
    "api": "EDI API",
    "calculated": "자동 산출",
}

_CSV_ALIASES: dict[str, tuple[str, ...]] = {
    "employee_id": ("employee_id", "employee_no", "사번", "emp_no", "직원번호"),
    "employee_name": ("employee_name", "name", "성명", "이름", "직원명"),
    "rrn": ("rrn", "resident_rrn", "주민등록번호", "주민번호", "jumin"),
    "management_no": (
        "management_no",
        "mgmt_no",
        "관리번호",
        "산재관리번호",
        "사업장관리번호",
    ),
    "period": ("period", "급여월", "적용월", "보험월", "payroll_period", "년월"),
    "national_pension": (
        "national_pension",
        "국민연금",
        "국민연금료",
        "pension",
        "np",
    ),
    "health_insurance": (
        "health_insurance",
        "건강보험",
        "건강보험료",
        "health",
        "hi",
    ),
    "long_term_care": (
        "long_term_care",
        "장기요양",
        "장기요양보험",
        "장기요양보험료",
        "ltc",
    ),
    "employment_insurance": (
        "employment_insurance",
        "고용보험",
        "고용보험료",
        "ei",
    ),
    "industrial_accident": (
        "industrial_accident",
        "산재보험",
        "산재보험료",
        "산재",
        "ia",
    ),
    "industrial_accident_employer": (
        "industrial_accident_employer",
        "산재보험_사업주",
        "산재사업주",
    ),
    "industrial_accident_employee": (
        "industrial_accident_employee",
        "산재보험_근로자",
        "산재근로자",
    ),
}


@dataclass
class InsurancePremiumRecord:
    """EDI·import 기준 1인 1월 보험료."""

    employee_id: str
    period: PeriodKey
    national_pension: int = 0
    health_insurance: int = 0
    long_term_care: int = 0
    employment_insurance: int = 0
    industrial_accident: int = 0
    industrial_accident_employer: int | None = None
    industrial_accident_employee: int | None = None
    employee_name: str = ""
    management_no: str = ""
    rrn_hash: str = ""
    rrn_masked: str = ""
    source: PremiumSource = "import"
    fetched_at: str = ""
    workplace: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "period": self.period,
            "national_pension": self.national_pension,
            "health_insurance": self.health_insurance,
            "long_term_care": self.long_term_care,
            "employment_insurance": self.employment_insurance,
            "industrial_accident": self.industrial_accident,
            "industrial_accident_employer": self.industrial_accident_employer,
            "industrial_accident_employee": self.industrial_accident_employee,
            "management_no": self.management_no,
            "rrn_hash": self.rrn_hash,
            "rrn_masked": self.rrn_masked,
            "source": self.source,
            "source_label": SOURCE_LABELS.get(self.source, self.source),
            "fetched_at": self.fetched_at,
            "workplace": self.workplace,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> InsurancePremiumRecord:
        src = str(raw.get("source") or "import").strip().lower()
        if src not in ("manual", "import", "api", "calculated"):
            src = "import"
        emp_emp = raw.get("industrial_accident_employer")
        emp_wrk = raw.get("industrial_accident_employee")
        return cls(
            employee_id=str(raw.get("employee_id") or "").strip(),
            employee_name=str(raw.get("employee_name") or "").strip(),
            period=_normalize_period(str(raw.get("period") or "")),
            national_pension=_parse_amount(raw.get("national_pension")),
            health_insurance=_parse_amount(raw.get("health_insurance")),
            long_term_care=_parse_amount(raw.get("long_term_care")),
            employment_insurance=_parse_amount(raw.get("employment_insurance")),
            industrial_accident=_parse_amount(raw.get("industrial_accident")),
            industrial_accident_employer=(
                _parse_amount(emp_emp) if emp_emp is not None and str(emp_emp).strip() else None
            ),
            industrial_accident_employee=(
                _parse_amount(emp_wrk) if emp_wrk is not None and str(emp_wrk).strip() else None
            ),
            management_no=str(raw.get("management_no") or "").strip(),
            rrn_hash=str(raw.get("rrn_hash") or ""),
            rrn_masked=str(raw.get("rrn_masked") or ""),
            source=src,  # type: ignore[arg-type]
            fetched_at=str(raw.get("fetched_at") or ""),
            workplace=str(raw.get("workplace") or "").strip(),
            note=str(raw.get("note") or "").strip(),
        )


@dataclass
class EdiApplyResult:
    """급여 산출 시 EDI 적용 결과."""

    applied: bool
    record: InsurancePremiumRecord | None = None
    message: str = ""


@runtime_checkable
class EdiInsuranceProvider(Protocol):
    """Phase 2: 사대보험 EDI 웹서비스 연동."""

    def lookup_premiums(
        self,
        employee_id: str,
        rrn: str,
        management_no: str,
        period: PeriodKey,
    ) -> InsurancePremiumRecord: ...

    def is_live(self) -> bool: ...


class LocalStoredEdiProvider:
    """Phase 1: app_data/edi_insurance 저장분 조회."""

    def lookup_premiums(
        self,
        employee_id: str,
        rrn: str,
        management_no: str,
        period: PeriodKey,
    ) -> InsurancePremiumRecord:
        rec = get_stored_premium(
            period=period,
            employee_id=employee_id,
            rrn=rrn,
            management_no=management_no,
        )
        if rec is None:
            raise LookupError("저장된 EDI 보험료가 없습니다.")
        return rec

    def is_live(self) -> bool:
        return False


class EdiWebServiceProvider(ABC):
    """
    Phase 2 스텁: 공단 EDI 웹서비스(XML/CSV) 연동.

    실제 연동 시 certificate_path, business_registration_no, api_endpoint_url 설정 필요.
    """

    def __init__(
        self,
        *,
        endpoint_url: str = "",
        certificate_path: str = "",
        business_registration_no: str = "",
    ) -> None:
        self.endpoint_url = str(endpoint_url or "").strip()
        self.certificate_path = str(certificate_path or "").strip()
        self.business_registration_no = str(business_registration_no or "").strip()

    def is_live(self) -> bool:
        return False

    def lookup_premiums(
        self,
        employee_id: str,
        rrn: str,
        management_no: str,
        period: PeriodKey,
    ) -> InsurancePremiumRecord:
        """
        TODO: 공인인증서 로그인 → EDI 보험료 조회 API (공단별 XML/전문).
        NHIS·NPS·KCOMWEL 포털 EDI보내기 형식과 동일 필드 매핑.
        """
        raise NotImplementedError(
            "사대보험 EDI 웹서비스 API 미연동 — CSV 가져오기 또는 수동 등록을 사용하세요."
        )


_active_provider: EdiInsuranceProvider | None = None


def get_provider() -> EdiInsuranceProvider:
    global _active_provider
    if _active_provider is None:
        _active_provider = LocalStoredEdiProvider()
    return _active_provider


def set_provider(provider: EdiInsuranceProvider | None) -> None:
    global _active_provider
    _active_provider = provider


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tid(tenant_id: str | None = None) -> str:
    return str(tenant_id or session_tenant_id() or "default").strip()


def _rrn_hash(digits: str) -> str:
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()


def _normalize_period(period: str) -> PeriodKey:
    text = str(period or "").strip().replace(".", "-").replace("/", "-")
    m = re.match(r"^(\d{4})-?(\d{1,2})$", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m2 = re.match(r"^(\d{4})(\d{2})$", text.replace("-", ""))
    if m2:
        return f"{m2.group(1)}-{m2.group(2)}"
    return text[:7] if len(text) >= 7 else text


def _parse_amount(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "").replace("원", "")
    if not text or text in ("-", "—", "N/A", "n/a"):
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def _normalize_header(h: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(h or "").strip().lower())


def _map_csv_row(raw: dict[str, str]) -> dict[str, str]:
    norm_row: dict[str, str] = {}
    for k, v in raw.items():
        norm_row[_normalize_header(k)] = str(v or "").strip()
    out: dict[str, str] = {}
    for field_name, aliases in _CSV_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in norm_row and norm_row[key]:
                out[field_name] = norm_row[key]
                break
    return out


def _tenant_dir(tenant_id: str) -> Path:
    return _EDI_ROOT / tenant_id


def _period_path(tenant_id: str, period: PeriodKey) -> Path:
    return _tenant_dir(tenant_id) / f"{_normalize_period(period)}.json"


def _empty_period_store(period: PeriodKey) -> dict[str, Any]:
    return {
        "period": _normalize_period(period),
        "records": [],
        "meta": {
            "last_import_at": "",
            "last_import_source": "",
            "api_connected": False,
        },
    }


def _load_period_store(tenant_id: str, period: PeriodKey) -> dict[str, Any]:
    path = _period_path(tenant_id, period)
    if not path.is_file():
        return _empty_period_store(period)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            out = _empty_period_store(period)
            out["records"] = list(raw.get("records") or [])
            meta = dict(out["meta"])
            if isinstance(raw.get("meta"), dict):
                meta.update(raw["meta"])
            out["meta"] = meta
            if raw.get("fetched_at"):
                out["fetched_at"] = raw["fetched_at"]
            return out
    except (OSError, JSONDecodeError):
        pass
    return _empty_period_store(period)


def _save_period_store(tenant_id: str, period: PeriodKey, data: dict[str, Any]) -> None:
    path = _period_path(tenant_id, period)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["period"] = _normalize_period(period)
    if not payload.get("fetched_at"):
        payload["fetched_at"] = _now_iso()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _mutate_period(tenant_id: str, period: PeriodKey, mutator) -> Any:
    with _lock:
        data = _load_period_store(tenant_id, period)
        result = mutator(data)
        _save_period_store(tenant_id, period, data)
        return result


def _match_record(
    records: list[dict[str, Any]],
    *,
    employee_id: str = "",
    employee_name: str = "",
    rrn: str = "",
    management_no: str = "",
) -> InsurancePremiumRecord | None:
    eid = str(employee_id or "").strip()
    nm = re.sub(r"\s+", "", str(employee_name or ""))
    mgmt = str(management_no or "").strip()
    rrn_key = normalize_rrn(rrn)
    r_hash = _rrn_hash(rrn_key) if rrn_key else ""

    candidates: list[InsurancePremiumRecord] = []
    for raw in records:
        rec = InsurancePremiumRecord.from_dict(raw)
        if eid and rec.employee_id == eid:
            candidates.append(rec)
            continue
        if r_hash and rec.rrn_hash == r_hash:
            candidates.append(rec)
            continue
        if nm and re.sub(r"\s+", "", rec.employee_name) == nm:
            candidates.append(rec)
            continue
        if mgmt and rec.management_no == mgmt and nm and re.sub(r"\s+", "", rec.employee_name) == nm:
            candidates.append(rec)

    if not candidates:
        return None
    candidates.sort(key=lambda x: x.fetched_at or "", reverse=True)
    return candidates[0]


def get_stored_premium(
    *,
    period: PeriodKey,
    employee_id: str = "",
    employee_name: str = "",
    rrn: str = "",
    management_no: str = "",
    tenant_id: str | None = None,
) -> InsurancePremiumRecord | None:
    tid = _tid(tenant_id)
    store = _load_period_store(tid, period)
    return _match_record(
        store.get("records") or [],
        employee_id=employee_id,
        employee_name=employee_name,
        rrn=rrn,
        management_no=management_no,
    )


def upsert_premium_record(
    record: InsurancePremiumRecord,
    *,
    tenant_id: str | None = None,
) -> InsurancePremiumRecord:
    """동일 사번·월 레코드를 갱신하거나 추가."""
    tid = _tid(tenant_id)
    period = _normalize_period(record.period)
    rec = deepcopy(record)
    rec.period = period
    if not rec.fetched_at:
        rec.fetched_at = _now_iso()

    def mut(store: dict[str, Any]) -> InsurancePremiumRecord:
        rows: list[dict[str, Any]] = list(store.get("records") or [])
        key_id = rec.employee_id.strip()
        key_hash = rec.rrn_hash
        filtered = [
            r
            for r in rows
            if not (
                (key_id and str(r.get("employee_id") or "").strip() == key_id)
                or (key_hash and str(r.get("rrn_hash") or "") == key_hash)
            )
        ]
        filtered.append(rec.to_dict())
        store["records"] = filtered
        store["fetched_at"] = _now_iso()
        return rec

    return _mutate_period(tid, period, mut)


def add_premium_manual(
    *,
    employee_id: str,
    period: PeriodKey,
    national_pension: int = 0,
    health_insurance: int = 0,
    long_term_care: int = 0,
    employment_insurance: int = 0,
    industrial_accident: int = 0,
    employee_name: str = "",
    management_no: str = "",
    rrn: str = "",
    workplace: str = "",
    note: str = "",
    tenant_id: str | None = None,
) -> InsurancePremiumRecord:
    rrn_key = normalize_rrn(rrn)
    if long_term_care <= 0 and health_insurance > 0:
        long_term_care = round_won(health_insurance * 0.1295)
    rec = InsurancePremiumRecord(
        employee_id=str(employee_id or "").strip(),
        employee_name=str(employee_name or "").strip(),
        period=_normalize_period(period),
        national_pension=_parse_amount(national_pension),
        health_insurance=_parse_amount(health_insurance),
        long_term_care=_parse_amount(long_term_care),
        employment_insurance=_parse_amount(employment_insurance),
        industrial_accident=_parse_amount(industrial_accident),
        management_no=str(management_no or "").strip(),
        rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
        rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
        source="manual",
        fetched_at=_now_iso(),
        workplace=str(workplace or "").strip(),
        note=str(note or "").strip(),
    )
    return upsert_premium_record(rec, tenant_id=tenant_id)


def import_premiums_csv(
    csv_path: str | Path,
    *,
    default_period: PeriodKey | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """EDI 포털·공단보내기 CSV import."""
    tid = _tid(tenant_id)
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    by_period: dict[str, list[InsurancePremiumRecord]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 헤더가 없습니다.")
        for raw in reader:
            mapped = _map_csv_row(raw)
            if not mapped.get("employee_id") and not mapped.get("employee_name") and not mapped.get("rrn"):
                continue
            period = _normalize_period(
                mapped.get("period") or default_period or date.today().strftime("%Y-%m")
            )
            rrn_key = normalize_rrn(mapped.get("rrn", ""))
            hi = _parse_amount(mapped.get("health_insurance"))
            ltc = _parse_amount(mapped.get("long_term_care"))
            if ltc <= 0 and hi > 0:
                ltc = round_won(hi * 0.1295)
            rec = InsurancePremiumRecord(
                employee_id=mapped.get("employee_id", ""),
                employee_name=mapped.get("employee_name", ""),
                period=period,
                national_pension=_parse_amount(mapped.get("national_pension")),
                health_insurance=hi,
                long_term_care=ltc,
                employment_insurance=_parse_amount(mapped.get("employment_insurance")),
                industrial_accident=_parse_amount(mapped.get("industrial_accident")),
                industrial_accident_employer=(
                    _parse_amount(mapped["industrial_accident_employer"])
                    if mapped.get("industrial_accident_employer")
                    else None
                ),
                industrial_accident_employee=(
                    _parse_amount(mapped["industrial_accident_employee"])
                    if mapped.get("industrial_accident_employee")
                    else None
                ),
                management_no=mapped.get("management_no", ""),
                rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
                rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
                source="import",
                fetched_at=_now_iso(),
            )
            by_period.setdefault(period, []).append(rec)

    if not by_period:
        raise ValueError("가져올 유효한 행이 없습니다. (사번·성명·주민번호 중 하나 필요)")

    total = 0
    for period, recs in by_period.items():
        for rec in recs:
            upsert_premium_record(rec, tenant_id=tid)
            total += 1

        def mut_meta(store: dict[str, Any]) -> None:
            meta = store.setdefault("meta", {})
            meta["last_import_at"] = _now_iso()
            meta["last_import_source"] = path.name

        _mutate_period(tid, period, mut_meta)

    return {"imported_count": total, "periods": list(by_period.keys()), "source": path.name}


def resolve_site_management_no(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> str:
    """산재관리번호 — payroll_settings site_settings."""
    from core.payroll.employment_insurance_65 import resolve_site_kcomwel_management_no

    return resolve_site_kcomwel_management_no(workplace, tenant_id=tenant_id)


def resolve_site_business_registration_no(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> str:
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        cfg = get_edi_insurance_config(tenant_id=tenant_id)
        return str(cfg.get("business_registration_no") or "").strip()
    entry = _site_entry(tenant_id, wp)
    for key in (
        "business_registration_no",
        "biz_reg_no",
        "사업자등록번호",
        "사업장등록번호",
    ):
        val = str(entry.get(key) or "").strip()
        if val:
            return val
    cfg = get_edi_insurance_config(tenant_id=tenant_id)
    return str(cfg.get("business_registration_no") or "").strip()


def batch_fetch_for_payroll(
    employee_roster: dict[str, dict[str, Any]],
    *,
    payroll_period: PeriodKey,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """
    급여 산출 전 명부 기준 EDI 조회(저장분·API).
    API 미연동 시 이미 import된 건만 집계합니다.
    """
    tid = _tid(tenant_id)
    period = _normalize_period(payroll_period)
    provider = get_provider()
    cfg = get_edi_insurance_config(tenant_id=tid)
    fetched = 0
    missing = 0
    errors: list[str] = []

    for _key, emp in (employee_roster or {}).items():
        emp_id = str(emp.get("사번") or "").strip()
        name = str(emp.get("성명") or "").strip()
        if not emp_id and not name:
            continue
        workplace = str(emp.get("근무지") or "").strip()
        mgmt = resolve_site_management_no(workplace, tenant_id=tid)
        rrn = str(emp.get("주민번호") or emp.get("birth") or "")
        existing = get_stored_premium(
            period=period,
            employee_id=emp_id,
            employee_name=name,
            rrn=rrn,
            management_no=mgmt,
            tenant_id=tid,
        )
        if existing is not None:
            fetched += 1
            continue
        if provider.is_live():
            try:
                rec = provider.lookup_premiums(emp_id, rrn, mgmt, period)
                rec.source = "api"
                upsert_premium_record(rec, tenant_id=tid)
                fetched += 1
            except Exception as exc:
                errors.append(f"{name or emp_id}: {exc}")
                missing += 1
        else:
            missing += 1

    return {
        "period": period,
        "fetched_count": fetched,
        "missing_count": missing,
        "api_live": provider.is_live(),
        "use_edi": bool(cfg.get("use_edi_premiums")),
        "errors": errors[:20],
    }


def apply_edi_premiums_to_inv(
    inv: dict[str, Any],
    *,
    payroll_period: PeriodKey,
    emp_roster: dict[str, Any] | None = None,
    tenant_id: str | None = None,
    respect_age_exempt: bool = True,
) -> EdiApplyResult:
    """
    EDI 보험료를 inv에 반영. use_edi_premiums=False 또는 저장분 없으면 미적용.
    respect_age_exempt: 만 65세 국민·건강·장기요양 면제 시 EDI로 덮어쓰지 않음.
    """
    tid = _tid(tenant_id)
    cfg = get_edi_insurance_config(tenant_id=tid)
    if not cfg.get("use_edi_premiums"):
        return EdiApplyResult(applied=False, message="EDI 보험료 사용 꺼짐")

    period = _normalize_period(payroll_period)
    roster = emp_roster or {}
    emp_id = str(roster.get("사번") or inv.get("employee_id") or "").strip()
    name = str(inv.get("name") or roster.get("성명") or "").strip()
    workplace = str(roster.get("근무지") or inv.get("workplace") or "").strip()
    rrn = str(roster.get("주민번호") or roster.get("birth") or "")
    mgmt = resolve_site_management_no(workplace, tenant_id=tid)

    rec = get_stored_premium(
        period=period,
        employee_id=emp_id,
        employee_name=name,
        rrn=rrn,
        management_no=mgmt,
        tenant_id=tid,
    )

    if rec is None and get_provider().is_live():
        try:
            rec = get_provider().lookup_premiums(emp_id, rrn, mgmt, period)
            rec.source = "api"
            upsert_premium_record(rec, tenant_id=tid)
        except Exception:
            rec = None

    if rec is None:
        return EdiApplyResult(applied=False, message="EDI 보험료 없음")

    age_exempt = bool(inv.get("insurance_exempt")) if respect_age_exempt else False

    if not age_exempt:
        if rec.national_pension > 0:
            inv["national_pension"] = rec.national_pension
        if rec.health_insurance > 0:
            inv["health_insurance"] = rec.health_insurance
        if rec.long_term_care > 0:
            inv["long_term_care"] = rec.long_term_care
        elif rec.health_insurance > 0:
            inv["long_term_care"] = round_won(rec.health_insurance * 0.1295)

    if rec.employment_insurance > 0:
        inv["employment_insurance"] = rec.employment_insurance
    elif rec.employment_insurance == 0 and not age_exempt:
        inv["employment_insurance"] = 0

    if rec.industrial_accident > 0:
        inv["industrial_accident"] = rec.industrial_accident
    if rec.industrial_accident_employer is not None:
        inv["industrial_accident_employer"] = rec.industrial_accident_employer
    if rec.industrial_accident_employee is not None:
        inv["industrial_accident_employee"] = rec.industrial_accident_employee

    inv["edi_premium_source"] = True
    inv["edi_premium_badge"] = "EDI 조회"
    inv["edi_premium_period"] = period
    inv["edi_premium_fetched_at"] = rec.fetched_at
    inv["edi_premium_source_type"] = rec.source

    inv["insurance_total"] = (
        int(safe_number(inv.get("health_insurance"), 0))
        + int(safe_number(inv.get("long_term_care"), 0))
        + int(safe_number(inv.get("national_pension"), 0))
        + int(safe_number(inv.get("employment_insurance"), 0))
    )

    return EdiApplyResult(applied=True, record=rec, message="EDI 보험료 적용")


def list_roster_edi_status(
    employee_roster: dict[str, dict[str, Any]],
    *,
    payroll_period: PeriodKey,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """명부 직원별 EDI 조회 vs 자동산출 표시용."""
    tid = _tid(tenant_id)
    period = _normalize_period(payroll_period)
    cfg = get_edi_insurance_config(tenant_id=tid)
    rows: list[dict[str, Any]] = []

    for _key, emp in (employee_roster or {}).items():
        name = str(emp.get("성명") or "").strip()
        if not name:
            continue
        emp_id = str(emp.get("사번") or "").strip()
        workplace = str(emp.get("근무지") or "").strip()
        rrn = str(emp.get("주민번호") or "")
        mgmt = resolve_site_management_no(workplace, tenant_id=tid)
        rec = get_stored_premium(
            period=period,
            employee_id=emp_id,
            employee_name=name,
            rrn=rrn,
            management_no=mgmt,
            tenant_id=tid,
        )
        has_edi = rec is not None
        rows.append(
            {
                "employee_id": emp_id,
                "employee_name": name,
                "workplace": workplace,
                "management_no": rec.management_no if rec else mgmt,
                "has_edi": has_edi,
                "source": rec.source if rec else "calculated",
                "source_label": (
                    SOURCE_LABELS.get(rec.source, rec.source) if rec else "자동 산출"
                ),
                "national_pension": rec.national_pension if rec else None,
                "health_insurance": rec.health_insurance if rec else None,
                "employment_insurance": rec.employment_insurance if rec else None,
                "fetched_at": rec.fetched_at if rec else "",
                "rrn_masked": rec.rrn_masked if rec else mask_rrn(normalize_rrn(rrn)),
            }
        )

    rows.sort(key=lambda x: (not x["has_edi"], x.get("employee_name") or ""))
    return rows


def is_api_connected(tenant_id: str | None = None) -> bool:
    cfg = get_edi_insurance_config(tenant_id=tenant_id)
    return bool(cfg.get("api_connected")) and get_provider().is_live()


def help_text_ko() -> str:
    return (
        "【EDI 4대보험료】\n"
        "· 국민연금·건강보험·고용·산재 EDI 포털에서 월 보험료 명세를 내려받아 CSV로 가져오거나 "
        "수동 등록하세요.\n"
        "· 실시간 API(Phase 2)는 공인인증서·사업자 EDI 가입·공단 웹서비스 계약이 필요합니다.\n"
        "· 「EDI 보험료로 급여 반영」을 켜면 조회된 금액이 자동 산출보다 우선 적용됩니다."
    )
