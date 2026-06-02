"""
core/payroll/employment_insurance_65.py - 만 65세 이상 고용보험 부과 확인

Phase 1 (현재): KCOMWEL(근로복지공단) 포털 조회 결과를 HR이 수동 등록하거나 CSV import.
Phase 2: KcomwelEmploymentInsuranceProvider로 공인인증서 API 연동 (미구현).

만 65세 이상 근로자는 실업급여 수급 자격(부과고지보험료)에 따라 고용보험 공제 여부가 달라집니다.
· 부과고지보험료 = 0 → 실업급여 비대상 → 고용보험 납부 없음
· 부과고지보험료 > 0 → 실업급여 대상 → 고용보험 공제 적용
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

from annual_leave_accrual import period_end_date
from core.hr.traffic_signal import mask_rrn, normalize_rrn
from core.org_config import canonical_scope_workplace
from core.paths import app_data_dir
from core.session_service import session_tenant_id
from insurance import INSURANCE_EXEMPT_AGE_YEARS, is_insurance_exempt
from services.payroll_settings_store import _site_entry
from utils import age_years_at, parse_birth_date_from_korean_rrn

EligibilityStatus = Literal["exempt", "liable", "unknown"]
VerificationSource = Literal["manual", "import", "api"]
UnknownDefault = Literal["skip", "deduct"]

_EI65_ROOT = app_data_dir() / "employment_insurance_65"
_lock = threading.Lock()

KCOMWEL_PORTAL_URL = "https://total.kcomwel.or.kr"

STATUS_LABELS: dict[str, str] = {
    "exempt": "납부 없음 (0원)",
    "liable": "납부 대상",
    "unknown": "미확인",
}

SOURCE_LABELS: dict[str, str] = {
    "manual": "수동 등록",
    "import": "CSV 가져오기",
    "api": "API 연동",
}

_CSV_ALIASES: dict[str, tuple[str, ...]] = {
    "employee_id": ("employee_id", "employee_no", "사번", "emp_no", "직원번호"),
    "employee_name": ("employee_name", "name", "성명", "이름", "직원명"),
    "management_no": (
        "management_no",
        "mgmt_no",
        "관리번호",
        "산재관리번호",
        "사업장관리번호",
    ),
    "premium_amount": (
        "premium_amount",
        "premium",
        "부과고지보험료",
        "고지보험료",
        "보험료",
        "부과보험료",
    ),
    "check_date": ("check_date", "조회일", "확인일", "조회일자", "date"),
    "rrn": ("rrn", "주민등록번호", "주민번호", "jumin"),
}


@dataclass
class VerificationRecord:
    """KCOMWEL 조회 결과 1건."""

    id: str
    employee_id: str
    employee_name: str
    check_date: str
    premium_amount: int
    management_no: str
    source: VerificationSource
    rrn_hash: str = ""
    rrn_masked: str = ""
    workplace: str = ""
    note: str = ""
    created_at: str = ""

    @property
    def status(self) -> EligibilityStatus:
        if self.premium_amount <= 0:
            return "exempt"
        return "liable"

    def to_dict(self) -> dict[str, Any]:
        st = self.status
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "check_date": self.check_date,
            "premium_amount": self.premium_amount,
            "management_no": self.management_no,
            "source": self.source,
            "source_label": SOURCE_LABELS.get(self.source, self.source),
            "status": st,
            "status_label": STATUS_LABELS.get(st, st),
            "rrn_hash": self.rrn_hash,
            "rrn_masked": self.rrn_masked,
            "workplace": self.workplace,
            "note": self.note,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> VerificationRecord:
        src = str(raw.get("source") or "manual").strip().lower()
        if src not in ("manual", "import", "api"):
            src = "manual"
        premium = _parse_premium(raw.get("premium_amount"))
        return cls(
            id=str(raw.get("id") or _new_id()),
            employee_id=str(raw.get("employee_id") or "").strip(),
            employee_name=str(raw.get("employee_name") or "").strip(),
            check_date=str(raw.get("check_date") or "")[:10],
            premium_amount=premium,
            management_no=str(raw.get("management_no") or "").strip(),
            source=src,  # type: ignore[arg-type]
            rrn_hash=str(raw.get("rrn_hash") or ""),
            rrn_masked=str(raw.get("rrn_masked") or ""),
            workplace=str(raw.get("workplace") or "").strip(),
            note=str(raw.get("note") or "").strip(),
            created_at=str(raw.get("created_at") or ""),
        )


@dataclass
class EI65PayrollResult:
    """급여 산출 시 고용보험 65+ 판정."""

    status: EligibilityStatus
    premium_amount: int | None
    management_no: str
    deduct_employment_insurance: bool
    warning: str = ""
    default_action: UnknownDefault = "skip"


@runtime_checkable
class KcomwelEmploymentInsuranceProvider(Protocol):
    """
    Phase 2: KCOMWEL 공식 API 연동 시 구현.
    lookup_premium은 개인별 부과고지보험료(원)를 반환합니다.
    """

    def lookup_premium(self, management_no: str, name: str) -> int: ...

    def is_live(self) -> bool: ...


class LocalImportEI65Provider:
    """Phase 1: 로컬 DB 기반 provider."""

    def lookup_premium(self, management_no: str, name: str) -> int:
        tid = _tid(None)
        mgmt = str(management_no or "").strip()
        nm = re.sub(r"\s+", "", str(name or ""))
        db = _load_db(tid)
        matches = [
            VerificationRecord.from_dict(r)
            for r in db.get("verifications") or []
            if (mgmt and str(r.get("management_no") or "").strip() == mgmt)
            or (nm and re.sub(r"\s+", "", str(r.get("employee_name") or "")) == nm)
        ]
        if not matches:
            return -1
        matches.sort(key=lambda x: x.check_date or "", reverse=True)
        return matches[0].premium_amount

    def is_live(self) -> bool:
        return False


class _NoOpKcomwelProvider(ABC):
    """미구현 원격 API 스텁."""

    def is_live(self) -> bool:
        return False

    @abstractmethod
    def lookup_premium(self, management_no: str, name: str) -> int:
        raise NotImplementedError


_active_provider: KcomwelEmploymentInsuranceProvider | None = None


def get_provider() -> KcomwelEmploymentInsuranceProvider:
    global _active_provider
    if _active_provider is None:
        _active_provider = LocalImportEI65Provider()
    return _active_provider


def set_provider(provider: KcomwelEmploymentInsuranceProvider | None) -> None:
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


def _parse_premium(value: Any) -> int:
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
    for field, aliases in _CSV_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in norm_row and norm_row[key]:
                out[field] = norm_row[key]
                break
    return out


def _tenant_dir(tenant_id: str) -> Path:
    return _EI65_ROOT / tenant_id


def _db_path(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "database.json"


def _empty_db() -> dict[str, Any]:
    return {
        "verifications": [],
        "meta": {
            "unknown_default": "skip",
            "api_connected": False,
            "last_import_at": "",
            "last_import_source": "",
        },
    }


def _load_db(tenant_id: str) -> dict[str, Any]:
    path = _db_path(tenant_id)
    if not path.is_file():
        return _empty_db()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            out = _empty_db()
            out["verifications"] = list(raw.get("verifications") or [])
            meta = dict(out["meta"])
            if isinstance(raw.get("meta"), dict):
                meta.update(raw["meta"])
            out["meta"] = meta
            return out
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_db()


def _save_db(tenant_id: str, data: dict[str, Any]) -> None:
    path = _db_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _mutate(tenant_id: str, mutator) -> Any:
    with _lock:
        data = _load_db(tenant_id)
        result = mutator(data)
        _save_db(tenant_id, data)
        return result


def is_age_65_plus(identity: Any, *, as_of: date | None = None) -> bool:
    """만 65세 이상 여부 (주민번호·생년월일 기준)."""
    return is_insurance_exempt(identity, as_of=as_of)


def age_years_from_identity(identity: Any, *, as_of: date | None = None) -> int | None:
    birth = parse_birth_date_from_korean_rrn(identity, as_of=as_of)
    if birth is None:
        return None
    return age_years_at(birth, as_of)


def get_unknown_default(*, tenant_id: str | None = None) -> UnknownDefault:
    db = _load_db(_tid(tenant_id))
    val = str(db.get("meta", {}).get("unknown_default") or "skip").strip().lower()
    return "deduct" if val == "deduct" else "skip"


def set_unknown_default(action: UnknownDefault, *, tenant_id: str | None = None) -> None:
    tid = _tid(tenant_id)
    action = "deduct" if action == "deduct" else "skip"

    def mut(db: dict[str, Any]) -> None:
        db.setdefault("meta", {})["unknown_default"] = action

    _mutate(tid, mut)


def resolve_site_kcomwel_management_no(
    workplace: str,
    *,
    tenant_id: str | None = None,
) -> str:
    """
    사업장 산재관리번호 — payroll_settings site_registry(site_settings)에 있으면 반환.
    """
    wp = canonical_scope_workplace(str(workplace or "").strip())
    if not wp:
        return ""
    entry = _site_entry(tenant_id, wp)
    for key in ("kcomwel_management_no", "industrial_accident_mgmt_no", "산재관리번호"):
        val = str(entry.get(key) or "").strip()
        if val:
            return val
    return ""


def _match_employee(
    row: dict[str, Any],
    *,
    employee_id: str = "",
    employee_name: str = "",
    identity: Any = None,
) -> bool:
    eid = re.sub(r"\s+", "", str(employee_id or "").strip()).upper()
    if eid and re.sub(r"\s+", "", str(row.get("employee_id") or "").strip()).upper() == eid:
        return True
    nm = re.sub(r"\s+", "", str(employee_name or ""))
    if nm and re.sub(r"\s+", "", str(row.get("employee_name") or "")) == nm:
        return True
    rrn = normalize_rrn(identity) if identity else None
    if rrn and str(row.get("rrn_hash") or "") == _rrn_hash(rrn):
        return True
    return False


def get_latest_verification(
    *,
    employee_id: str = "",
    employee_name: str = "",
    identity: Any = None,
    tenant_id: str | None = None,
) -> VerificationRecord | None:
    tid = _tid(tenant_id)
    rows = [
        VerificationRecord.from_dict(r)
        for r in _load_db(tid).get("verifications") or []
        if _match_employee(
            r,
            employee_id=employee_id,
            employee_name=employee_name,
            identity=identity,
        )
    ]
    if not rows:
        return None
    rows.sort(key=lambda x: (x.check_date, x.created_at), reverse=True)
    return rows[0]


def list_verifications(tenant_id: str | None = None) -> list[dict[str, Any]]:
    db = _load_db(_tid(tenant_id))
    rows = [VerificationRecord.from_dict(r).to_dict() for r in db.get("verifications") or []]
    rows.sort(key=lambda x: (x.get("check_date") or "", x.get("employee_name") or ""), reverse=True)
    return rows


def add_verification_manual(
    *,
    tenant_id: str | None = None,
    employee_id: str = "",
    employee_name: str = "",
    management_no: str = "",
    premium_amount: int | str = 0,
    check_date: str = "",
    rrn: str = "",
    workplace: str = "",
    note: str = "",
) -> dict[str, Any]:
    tid = _tid(tenant_id)
    rrn_key = normalize_rrn(rrn) if rrn else None
    rec = VerificationRecord(
        id=_new_id(),
        employee_id=employee_id.strip(),
        employee_name=employee_name.strip(),
        check_date=(check_date or date.today().isoformat())[:10],
        premium_amount=_parse_premium(premium_amount),
        management_no=management_no.strip(),
        source="manual",
        rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
        rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
        workplace=workplace.strip(),
        note=note.strip(),
        created_at=_now_iso(),
    )

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        db.setdefault("verifications", []).append(rec.to_dict())
        return rec.to_dict()

    return _mutate(tid, mut)


def import_verifications_csv(
    csv_path: str | Path,
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """KCOMWEL 포털 조회 결과 CSV import (관리번호, 성명, 부과고지보험료)."""
    tid = _tid(tenant_id)
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    imported: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 헤더가 없습니다.")
        for raw in reader:
            mapped = _map_csv_row(raw)
            if not mapped.get("employee_name") and not mapped.get("management_no"):
                continue
            rrn_key = normalize_rrn(mapped.get("rrn", ""))
            rec = VerificationRecord(
                id=_new_id(),
                employee_id=mapped.get("employee_id", ""),
                employee_name=mapped.get("employee_name", ""),
                check_date=(mapped.get("check_date") or date.today().isoformat())[:10],
                premium_amount=_parse_premium(mapped.get("premium_amount", 0)),
                management_no=mapped.get("management_no", ""),
                source="import",
                rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
                rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
                created_at=_now_iso(),
            )
            imported.append(rec.to_dict())

    if not imported:
        raise ValueError("가져올 유효한 행이 없습니다. (성명 또는 관리번호 필요)")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        db.setdefault("verifications", []).extend(imported)
        meta = db.setdefault("meta", {})
        meta["last_import_at"] = _now_iso()
        meta["last_import_source"] = path.name
        return {"imported_count": len(imported), "source": path.name}

    return _mutate(tid, mut)


def resolve_ei_65_for_payroll(
    *,
    identity: Any,
    payroll_period: str,
    employee_id: str = "",
    employee_name: str = "",
    workplace: str = "",
    tenant_id: str | None = None,
) -> EI65PayrollResult:
    """
    만 65세 이상 근로자의 고용보험 공제 여부를 판정합니다.
    65세 미만이면 liable(일반 공제)로 반환합니다.
    """
    as_of = period_end_date(payroll_period)
    if not is_age_65_plus(identity, as_of=as_of):
        return EI65PayrollResult(
            status="liable",
            premium_amount=None,
            management_no="",
            deduct_employment_insurance=True,
        )

    default_action = get_unknown_default(tenant_id=tenant_id)
    mgmt = resolve_site_kcomwel_management_no(workplace, tenant_id=tenant_id)
    rec = get_latest_verification(
        employee_id=employee_id,
        employee_name=employee_name,
        identity=identity,
        tenant_id=tenant_id,
    )

    if rec is None and get_provider().is_live() and mgmt:
        try:
            premium = get_provider().lookup_premium(mgmt, employee_name)
            if premium >= 0:
                rec = VerificationRecord(
                    id=_new_id(),
                    employee_id=employee_id,
                    employee_name=employee_name,
                    check_date=date.today().isoformat(),
                    premium_amount=premium,
                    management_no=mgmt,
                    source="api",
                    created_at=_now_iso(),
                )
        except Exception:
            rec = None

    if rec is None:
        label = employee_name or employee_id or "해당 직원"
        action_label = "공제 적용" if default_action == "deduct" else "공제 생략"
        return EI65PayrollResult(
            status="unknown",
            premium_amount=None,
            management_no=mgmt,
            deduct_employment_insurance=(default_action == "deduct"),
            default_action=default_action,
            warning=(
                f"{label}: 만 {INSURANCE_EXEMPT_AGE_YEARS}세 이상 고용보험 KCOMWEL 확인 미완료 "
                f"→ 설정 기본값({action_label}) 적용"
            ),
        )

    deduct = rec.status == "liable"
    return EI65PayrollResult(
        status=rec.status,
        premium_amount=rec.premium_amount,
        management_no=rec.management_no or mgmt,
        deduct_employment_insurance=deduct,
    )


def list_65_plus_roster_rows(
    employee_roster: dict[str, dict[str, Any]],
    *,
    payroll_period: str,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """명부에서 만 65세 이상 직원과 확인 상태 목록."""
    as_of = period_end_date(payroll_period)
    tid = _tid(tenant_id)
    rows: list[dict[str, Any]] = []

    for _key, emp in (employee_roster or {}).items():
        name = str(emp.get("성명") or "").strip()
        if not name:
            continue
        identity = emp.get("주민번호") or emp.get("birth")
        if not is_age_65_plus(identity, as_of=as_of):
            continue
        emp_id = str(emp.get("사번") or "").strip()
        workplace = str(emp.get("근무지") or "").strip()
        age = age_years_from_identity(identity, as_of=as_of)
        rec = get_latest_verification(
            employee_id=emp_id,
            employee_name=name,
            identity=identity,
            tenant_id=tid,
        )
        status: EligibilityStatus = rec.status if rec else "unknown"
        site_mgmt = resolve_site_kcomwel_management_no(workplace, tenant_id=tid)
        rows.append(
            {
                "employee_id": emp_id,
                "employee_name": name,
                "age": age,
                "workplace": workplace,
                "site_management_no": site_mgmt,
                "status": status,
                "status_label": STATUS_LABELS.get(status, status),
                "management_no": rec.management_no if rec else "",
                "check_date": rec.check_date if rec else "",
                "premium_amount": rec.premium_amount if rec else None,
                "deduct_label": (
                    "납부 O" if status == "liable" else ("납부 X" if status == "exempt" else "미확인")
                ),
            }
        )

    rows.sort(key=lambda x: (x.get("status") == "unknown", x.get("employee_name") or ""))
    return rows


def list_pending_verification(
    employee_roster: dict[str, dict[str, Any]],
    *,
    payroll_period: str,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """확인이 필요한(unknown) 65+ 직원."""
    return [
        r
        for r in list_65_plus_roster_rows(
            employee_roster, payroll_period=payroll_period, tenant_id=tenant_id
        )
        if r.get("status") == "unknown"
    ]


def collect_ei_65_payroll_warnings(
    invoice_rows: list[dict[str, Any]],
    employee_roster: dict[str, dict[str, Any]] | None,
    *,
    payroll_period: str,
    tenant_id: str | None = None,
) -> list[str]:
    """급여 산출 시 65+ 미확인 직원 요약 경고 (개별 경고는 inv['ei_65_warning'])."""
    roster = employee_roster or {}
    pending = list_pending_verification(roster, payroll_period=payroll_period, tenant_id=tenant_id)
    if not pending:
        return []
    names = ", ".join(r["employee_name"] for r in pending[:5])
    extra = f" 외 {len(pending) - 5}명" if len(pending) > 5 else ""
    return [
        f"만 {INSURANCE_EXEMPT_AGE_YEARS}세 이상 고용보험 미확인 {len(pending)}명: {names}{extra}"
    ]


def is_api_connected(tenant_id: str | None = None) -> bool:
    db = _load_db(_tid(tenant_id))
    return bool(db.get("meta", {}).get("api_connected")) and get_provider().is_live()


def help_text_ko() -> str:
    return (
        "【만 65세 고용보험】\n"
        "· 근로복지공단(KCOMWEL) 포털에서 「개인별 부과고지보험료」를 조회한 뒤 "
        "관리번호·성명·부과고지보험료를 등록하세요.\n"
        "· 부과고지보험료 0원 → 실업급여 비대상 → 급여에서 고용보험 공제 없음\n"
        "· 0원 초과 → 실업급여 대상 → 고용보험 공제 적용\n"
        "· API 연동(Phase 2)은 공인인증서·공식 제휴가 필요합니다."
    )
