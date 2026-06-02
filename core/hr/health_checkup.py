"""
core/hr/health_checkup.py - 건강검진 대상 조회 · 검사기록지 업로드

Phase 1 (현재): NHIS/사대보험 실시간 API 미연동.
  - 건강보험공단 사업장관리자 포털에서보낸 CSV/Excel 명단 import
  - 또는 HR이 수동 등록
  - 직원은 사번·주민번호로 대상 여부 self-check, 결과지(PDF/이미지) 업로드

Phase 2: HealthCheckupProvider 인터페이스로 공식 API 어댑터 연동 가능.

건강검진 자격 실시간 조회는 제3자 데스크톱 앱에 공개 API로 제공되지 않는 경우가
대부분이며, 사대보험 EDI·고용주 포털 연동은 사업자 등록·보안인증·제휴 계약이
필요합니다. 본 모듈은 import/수동 경로를 기본으로 합니다.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import threading
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from core.hr.traffic_signal import mask_rrn, normalize_rrn
from core.paths import app_data_dir
from core.session_service import get_session, session_tenant_id

CheckupType = Literal["general", "special"]
EligibilityStatus = Literal["pending", "completed", "waived"]

_CHECKUP_ROOT = app_data_dir() / "health_checkup"
_lock = threading.Lock()

CHECKUP_TYPE_LABELS: dict[str, str] = {
    "general": "일반 건강검진",
    "special": "특수건강검진",
}

STATUS_LABELS: dict[str, str] = {
    "pending": "미수검",
    "completed": "수검완료",
    "waived": "면제/제외",
}

# NHIS 공식 안내 (브라우저에서 직접 확인용)
NHIS_PUBLIC_URL = "https://www.nhis.or.kr"

# CSV 헤더 별칭 → 내부 필드
_CSV_ALIASES: dict[str, tuple[str, ...]] = {
    "employee_no": ("employee_no", "사번", "emp_no", "empno", "employee_id", "직원번호"),
    "employee_name": ("employee_name", "name", "성명", "이름", "직원명"),
    "rrn": ("rrn", "resident_rrn", "주민등록번호", "주민번호", "jumin"),
    "checkup_type": ("checkup_type", "검진유형", "유형", "type", "검진구분"),
    "period_start": ("period_start", "기간시작", "시작일", "검진시작", "start_date"),
    "period_end": ("period_end", "기간종료", "종료일", "검진종료", "end_date", "마감일"),
    "special_exam_types": ("special_exam_types", "특수검사", "특별검사", "특검항목"),
    "status": ("status", "상태", "수검상태"),
    "department": ("department", "부서", "dept"),
    "note": ("note", "비고", "메모"),
}

ALLOWED_UPLOAD_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"})


@dataclass
class EligibilityRecord:
    """건강검진 대상자 1명."""

    id: str
    employee_no: str
    employee_name: str
    rrn_hash: str
    rrn_masked: str
    checkup_type: CheckupType
    period_start: str
    period_end: str
    special_exam_types: list[str] = field(default_factory=list)
    status: EligibilityStatus = "pending"
    department: str = ""
    note: str = ""
    imported_at: str = ""
    source: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "employee_no": self.employee_no,
            "employee_name": self.employee_name,
            "rrn_hash": self.rrn_hash,
            "rrn_masked": self.rrn_masked,
            "checkup_type": self.checkup_type,
            "checkup_type_label": CHECKUP_TYPE_LABELS.get(self.checkup_type, self.checkup_type),
            "period_start": self.period_start,
            "period_end": self.period_end,
            "special_exam_types": list(self.special_exam_types),
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "department": self.department,
            "note": self.note,
            "imported_at": self.imported_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EligibilityRecord:
        ct = str(raw.get("checkup_type") or "general").strip().lower()
        if ct in ("special", "특수", "특수건강검진", "특검"):
            ct = "special"
        else:
            ct = "general"
        st = str(raw.get("status") or "pending").strip().lower()
        if st in ("completed", "완료", "수검", "수검완료"):
            st = "completed"
        elif st in ("waived", "면제", "제외"):
            st = "waived"
        else:
            st = "pending"
        exams = raw.get("special_exam_types") or []
        if isinstance(exams, str):
            exams = [x.strip() for x in re.split(r"[,;/|]", exams) if x.strip()]
        return cls(
            id=str(raw.get("id") or _new_id()),
            employee_no=str(raw.get("employee_no") or "").strip(),
            employee_name=str(raw.get("employee_name") or "").strip(),
            rrn_hash=str(raw.get("rrn_hash") or ""),
            rrn_masked=str(raw.get("rrn_masked") or ""),
            checkup_type=ct,  # type: ignore[arg-type]
            period_start=str(raw.get("period_start") or "")[:10],
            period_end=str(raw.get("period_end") or "")[:10],
            special_exam_types=list(exams),
            status=st,  # type: ignore[arg-type]
            department=str(raw.get("department") or "").strip(),
            note=str(raw.get("note") or "").strip(),
            imported_at=str(raw.get("imported_at") or ""),
            source=str(raw.get("source") or "manual"),
        )


@dataclass
class UploadRecord:
    """검사기록지(결과지) 업로드."""

    id: str
    eligibility_id: str
    employee_no: str
    employee_name: str
    file_path: str
    original_filename: str
    uploaded_at: str
    uploaded_by: str
    checkup_date: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "eligibility_id": self.eligibility_id,
            "employee_no": self.employee_no,
            "employee_name": self.employee_name,
            "file_path": self.file_path,
            "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at,
            "uploaded_by": self.uploaded_by,
            "checkup_date": self.checkup_date,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UploadRecord:
        return cls(
            id=str(raw.get("id") or _new_id()),
            eligibility_id=str(raw.get("eligibility_id") or ""),
            employee_no=str(raw.get("employee_no") or "").strip(),
            employee_name=str(raw.get("employee_name") or "").strip(),
            file_path=str(raw.get("file_path") or ""),
            original_filename=str(raw.get("original_filename") or ""),
            uploaded_at=str(raw.get("uploaded_at") or ""),
            uploaded_by=str(raw.get("uploaded_by") or ""),
            checkup_date=str(raw.get("checkup_date") or "")[:10],
            note=str(raw.get("note") or "").strip(),
        )


@dataclass
class LookupResult:
    """조회 결과 (직원 self-check)."""

    eligible: bool
    records: list[dict[str, Any]]
    message: str
    uploads: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "records": self.records,
            "message": self.message,
            "uploads": self.uploads,
        }


@runtime_checkable
class HealthCheckupProvider(Protocol):
    """
    Phase 2: 공식 NHIS/사대보험 API 연동 시 구현.
    lookup_eligibility는 실시간 자격 조회를 반환합니다.
    """

    def lookup_eligibility(
        self, tenant_id: str, employee_identifier: str
    ) -> list[dict[str, Any]]: ...

    def is_live(self) -> bool: ...


class LocalImportHealthCheckupProvider:
    """Phase 1: 로컬 import DB 기반 provider."""

    def lookup_eligibility(
        self, tenant_id: str, employee_identifier: str
    ) -> list[dict[str, Any]]:
        result = lookup_eligibility(tenant_id, employee_identifier)
        return result.records

    def is_live(self) -> bool:
        return False


class _NoOpRemoteProvider(ABC):
    """미구현 원격 API 스텁 — is_live False."""

    def is_live(self) -> bool:
        return False

    @abstractmethod
    def lookup_eligibility(
        self, tenant_id: str, employee_identifier: str
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


_active_provider: HealthCheckupProvider | None = None


def get_provider() -> HealthCheckupProvider:
    global _active_provider
    if _active_provider is None:
        _active_provider = LocalImportHealthCheckupProvider()
    return _active_provider


def set_provider(provider: HealthCheckupProvider | None) -> None:
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


def _normalize_employee_no(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).upper()


def _parse_checkup_type(value: Any) -> CheckupType:
    s = str(value or "").strip().lower()
    if s in ("special", "특수", "특수건강검진", "특검", "특별검사"):
        return "special"
    return "general"


def _parse_status(value: Any) -> EligibilityStatus:
    s = str(value or "").strip().lower()
    if s in ("completed", "완료", "수검", "수검완료", "done"):
        return "completed"
    if s in ("waived", "면제", "제외"):
        return "waived"
    return "pending"


def _tenant_dir(tenant_id: str) -> Path:
    return _CHECKUP_ROOT / tenant_id


def _db_path(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "database.json"


def _uploads_dir(tenant_id: str) -> Path:
    return _tenant_dir(tenant_id) / "uploads"


def _empty_db() -> dict[str, Any]:
    return {
        "eligibility": [],
        "uploads": [],
        "meta": {"last_import_at": "", "last_import_source": "", "api_connected": False},
    }


def _load_db(tenant_id: str) -> dict[str, Any]:
    path = _db_path(tenant_id)
    if not path.is_file():
        return _empty_db()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            out = _empty_db()
            out["eligibility"] = list(raw.get("eligibility") or [])
            out["uploads"] = list(raw.get("uploads") or [])
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


def _match_identifier(row: dict[str, Any], identifier: str) -> bool:
    ident = identifier.strip()
    if not ident:
        return False
    emp_no = _normalize_employee_no(row.get("employee_no"))
    if emp_no and emp_no == _normalize_employee_no(ident):
        return True
    rrn = normalize_rrn(ident)
    if rrn and str(row.get("rrn_hash") or "") == _rrn_hash(rrn):
        return True
    name = re.sub(r"\s+", "", ident)
    if name and re.sub(r"\s+", "", str(row.get("employee_name") or "")) == name:
        return True
    return False


def _normalize_header(h: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(h or "").strip().lower())


def _map_csv_row(raw: dict[str, str]) -> dict[str, str]:
    """헤더 별칭을 내부 필드명으로 매핑."""
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


def is_api_connected(tenant_id: str | None = None) -> bool:
    """실시간 NHIS API 연동 여부 (Phase 1: 항상 False)."""
    db = _load_db(_tid(tenant_id))
    return bool(db.get("meta", {}).get("api_connected")) and get_provider().is_live()


def help_text_ko() -> str:
    return (
        "【건강검진 안내】\n"
        "· 본 프로그램은 건강보험공단(NHIS) 실시간 API에 연결되어 있지 않습니다.\n"
        "· HR 담당자가 NHIS 사업장관리자 포털에서 받은 명단(CSV)을 가져오거나, "
        "수동으로 대상자를 등록해야 합니다.\n"
        "· 직원은 사번 또는 주민등록번호로 「내 검진 대상 여부」를 확인하고, "
        "수검 후 검사기록지(PDF·이미지)를 업로드할 수 있습니다.\n"
        "· 공식 자격·일정 확인은 건강보험공단 홈페이지에서 직접 확인하세요.\n"
        f"  ({NHIS_PUBLIC_URL})\n"
        "· 향후 공식 제휴 API가 제공되면 HealthCheckupProvider로 연동할 수 있습니다."
    )


def list_eligibility(tenant_id: str | None = None) -> list[dict[str, Any]]:
    db = _load_db(_tid(tenant_id))
    return [EligibilityRecord.from_dict(r).to_dict() for r in db.get("eligibility") or []]


def list_uploads(
    tenant_id: str | None = None,
    *,
    eligibility_id: str | None = None,
) -> list[dict[str, Any]]:
    db = _load_db(_tid(tenant_id))
    rows = [UploadRecord.from_dict(u) for u in db.get("uploads") or []]
    if eligibility_id:
        rows = [u for u in rows if u.eligibility_id == eligibility_id]
    return [u.to_dict() for u in rows]


def add_eligibility_manual(
    *,
    tenant_id: str | None = None,
    employee_no: str = "",
    employee_name: str = "",
    rrn: str = "",
    checkup_type: str = "general",
    period_start: str = "",
    period_end: str = "",
    special_exam_types: list[str] | None = None,
    status: str = "pending",
    department: str = "",
    note: str = "",
) -> dict[str, Any]:
    tid = _tid(tenant_id)
    rrn_key = normalize_rrn(rrn) if rrn else None
    rec = EligibilityRecord(
        id=_new_id(),
        employee_no=employee_no.strip(),
        employee_name=employee_name.strip(),
        rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
        rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
        checkup_type=_parse_checkup_type(checkup_type),
        period_start=period_start[:10] or date.today().isoformat(),
        period_end=period_end[:10] or f"{date.today().year}-12-31",
        special_exam_types=list(special_exam_types or []),
        status=_parse_status(status),
        department=department.strip(),
        note=note.strip(),
        imported_at=_now_iso(),
        source="manual",
    )

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        db.setdefault("eligibility", []).append(rec.to_dict())
        return rec.to_dict()

    return _mutate(tid, mut)


def import_eligibility_csv(
    csv_path: str | Path,
    *,
    tenant_id: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """
    NHIS 사업장 포털 등에서보낸 CSV를 import.
    replace=True면 기존 import/manual 명단을 덮어씁니다.
    """
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
            if not any(mapped.get(k) for k in ("employee_no", "employee_name", "rrn")):
                continue
            rrn_key = normalize_rrn(mapped.get("rrn", ""))
            exams = mapped.get("special_exam_types", "")
            exam_list = (
                [x.strip() for x in re.split(r"[,;/|]", exams) if x.strip()] if exams else []
            )
            rec = EligibilityRecord(
                id=_new_id(),
                employee_no=mapped.get("employee_no", ""),
                employee_name=mapped.get("employee_name", ""),
                rrn_hash=_rrn_hash(rrn_key) if rrn_key else "",
                rrn_masked=mask_rrn(rrn_key) if rrn_key else "",
                checkup_type=_parse_checkup_type(mapped.get("checkup_type", "general")),
                period_start=(mapped.get("period_start") or "")[:10],
                period_end=(mapped.get("period_end") or "")[:10],
                special_exam_types=exam_list,
                status=_parse_status(mapped.get("status", "pending")),
                department=mapped.get("department", ""),
                note=mapped.get("note", ""),
                imported_at=_now_iso(),
                source=f"csv:{path.name}",
            )
            if not rec.period_start:
                rec.period_start = date.today().isoformat()
            if not rec.period_end:
                rec.period_end = f"{date.today().year}-12-31"
            imported.append(rec.to_dict())

    if not imported:
        raise ValueError("가져올 수 있는 대상자 행이 없습니다. 사번·성명·주민번호 열을 확인하세요.")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        if replace:
            db["eligibility"] = imported
        else:
            db.setdefault("eligibility", []).extend(imported)
        db.setdefault("meta", {})["last_import_at"] = _now_iso()
        db["meta"]["last_import_source"] = str(path.name)
        return {"imported_count": len(imported), "replace": replace}

    summary = _mutate(tid, mut)
    summary["records"] = imported
    return summary


def delete_eligibility(eligibility_id: str, *, tenant_id: str | None = None) -> bool:
    tid = _tid(tenant_id)

    def mut(db: dict[str, Any]) -> bool:
        before = len(db.get("eligibility") or [])
        db["eligibility"] = [
            r for r in db.get("eligibility") or [] if str(r.get("id")) != str(eligibility_id)
        ]
        db["uploads"] = [
            u for u in db.get("uploads") or [] if str(u.get("eligibility_id")) != str(eligibility_id)
        ]
        return len(db["eligibility"]) < before

    return bool(_mutate(tid, mut))


def lookup_eligibility(
    tenant_id: str | None,
    employee_identifier: str,
) -> LookupResult:
    """
    사번·주민번호·성명으로 대상 여부 조회.
    Provider가 live이면 원격 조회 후 로컬과 병합 가능 (Phase 2).
    """
    tid = _tid(tenant_id)
    ident = str(employee_identifier or "").strip()
    if not ident:
        return LookupResult(
            eligible=False,
            records=[],
            message="사번 또는 주민등록번호(13자리)를 입력하세요.",
        )

    provider = get_provider()
    remote_rows: list[dict[str, Any]] = []
    if provider.is_live():
        try:
            remote_rows = list(provider.lookup_eligibility(tid, ident))
        except Exception:
            remote_rows = []

    db = _load_db(tid)
    local_matches = [
        EligibilityRecord.from_dict(r).to_dict()
        for r in db.get("eligibility") or []
        if _match_identifier(r, ident)
    ]
    all_records = remote_rows + [r for r in local_matches if r not in remote_rows]

    uploads: list[dict[str, Any]] = []
    for rec in all_records:
        eid = str(rec.get("id") or "")
        uploads.extend(list_uploads(tid, eligibility_id=eid))

    if not all_records:
        return LookupResult(
            eligible=False,
            records=[],
            message=(
                "등록된 검진 대상 정보가 없습니다. "
                "HR이 NHIS 명단을 가져왔는지 확인하거나, 건강보험공단 사이트에서 직접 확인하세요."
            ),
            uploads=[],
        )

    types = {r.get("checkup_type_label") or r.get("checkup_type") for r in all_records}
    msg = f"건강검진 대상입니다. ({', '.join(sorted(types))})"
    return LookupResult(eligible=True, records=all_records, message=msg, uploads=uploads)


def save_upload(
    *,
    source_file: str | Path,
    eligibility_id: str,
    checkup_date: str,
    tenant_id: str | None = None,
    uploaded_by: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    """검사기록지 파일을 tenant uploads 폴더에 저장하고 메타데이터 기록."""
    tid = _tid(tenant_id)
    src = Path(source_file)
    if not src.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {src}")

    suffix = src.suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError(f"허용되지 않는 파일 형식입니다: {suffix}")

    db = _load_db(tid)
    elig_row = next(
        (r for r in db.get("eligibility") or [] if str(r.get("id")) == str(eligibility_id)),
        None,
    )
    if not elig_row:
        raise ValueError("검진 대상 정보를 찾을 수 없습니다. 먼저 대상 여부를 조회하세요.")

    upload_id = _new_id()
    dest_dir = _uploads_dir(tid)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{upload_id}{suffix}"
    dest_path = dest_dir / dest_name
    shutil.copy2(src, dest_path)

    actor = uploaded_by
    if actor is None:
        sess = get_session()
        actor = sess.user_id if sess else ""

    rel_path = f"uploads/{dest_name}"
    upload = UploadRecord(
        id=upload_id,
        eligibility_id=str(eligibility_id),
        employee_no=str(elig_row.get("employee_no") or ""),
        employee_name=str(elig_row.get("employee_name") or ""),
        file_path=rel_path,
        original_filename=src.name,
        uploaded_at=_now_iso(),
        uploaded_by=actor or "",
        checkup_date=checkup_date[:10] or date.today().isoformat(),
        note=note.strip(),
    )

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        db.setdefault("uploads", []).append(upload.to_dict())
        for r in db.get("eligibility") or []:
            if str(r.get("id")) == str(eligibility_id):
                r["status"] = "completed"
        return upload.to_dict()

    return _mutate(tid, mut)


def resolve_upload_path(tenant_id: str, relative_path: str) -> Path:
    return _tenant_dir(tenant_id) / relative_path


def import_meta(tenant_id: str | None = None) -> dict[str, Any]:
    db = _load_db(_tid(tenant_id))
    return dict(db.get("meta") or {})
