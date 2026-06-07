"""개인별 HR 문서관리·만료 알림 서비스.

This module implements Issue #76 as a backend-safe MVP:
- encrypted-at-rest file envelopes under app data;
- tenant-scoped JSON metadata via module_store;
- document-type policy settings;
- versioning/renewal, review, rejection, audit logs, history;
- expiry status sync and notification records.

External messenger/email/calendar integrations can consume the notification rows
later; no live external calls are made here.
"""

from __future__ import annotations

import base64
import hashlib
import html
import mimetypes
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.paths import app_data_dir
from core.session_service import UserSession, get_session, session_tenant_id
from core.hr.employee_documents.permissions import (
    can_approve_document_requests,
    can_download_document,
    can_manage_employee_documents,
    can_upload_employee_document,
    can_view_employee_documents,
    is_payroll_document,
    is_sensitive_document,
)
from core.hr.employee_documents.types import DOCUMENT_LABELS, DocumentType, document_field_requirements, list_document_type_info
from core.roles import ROLE_ADMIN, ROLE_FINANCE, ROLE_STAFF, normalize_role

MODULE = "hr_documents"

STATUS_VALID = "유효"
STATUS_EXPIRING = "만료 예정"
STATUS_EXPIRED = "만료"
STATUS_RENEWED = "갱신 완료"
STATUS_REVIEW_REQUIRED = "검토 필요"
STATUS_REJECTED = "반려"
STATUS_QUARANTINED = "격리"

DOCUMENT_STATUSES: tuple[str, ...] = (
    STATUS_VALID,
    STATUS_EXPIRING,
    STATUS_EXPIRED,
    STATUS_RENEWED,
    STATUS_REVIEW_REQUIRED,
    STATUS_REJECTED,
    STATUS_QUARANTINED,
)

DEFAULT_REMINDER_DAYS: tuple[int, ...] = (90, 60, 30, 7, 0)
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".hwp", ".hwpx", ".txt")
DEFAULT_NOTIFICATION_CHANNELS: tuple[str, ...] = ("platform", "mobile_push")
DEFAULT_RESTORE_DAYS = 30
DEFAULT_LEGAL_REVIEW_NOTICE = "노무/법무/개인정보보호 담당자 검토 필요"
HIGH_RISK_GRADES: frozenset[str] = frozenset({"high", "critical", "고", "최고", "높음"})
RETENTION_STATUSES: tuple[str, ...] = (
    "일반 보관",
    "법정 보관",
    "장기 보관",
    "분리 보관",
    "백업 보관",
    "보존 잠금",
    "제공 제한",
    "다운로드 제한",
    "법무 검토 필요",
)

_EMPTY: dict[str, Any] = {
    "document_types": [],
    "documents": [],
    "audit_logs": [],
    "notifications": [],
    "permission_requests": [],
    "delete_requests": [],
    "restore_requests": [],
    "backup_records": [],
    "employment_type_rules": [],
    "integration_logs": [],
    "electronic_signature_records": [],
    "settings": {
        "max_upload_bytes": DEFAULT_MAX_UPLOAD_BYTES,
        "default_reminder_days": list(DEFAULT_REMINDER_DAYS),
        "default_notification_channels": list(DEFAULT_NOTIFICATION_CHANNELS),
        "encryption_required": True,
        "soft_delete_default": True,
        "restore_window_days": DEFAULT_RESTORE_DAYS,
        "download_reason_required": True,
        "legal_review_notice": DEFAULT_LEGAL_REVIEW_NOTICE,
        "immutable_audit_chain": True,
    },
    "seeded": False,
}

TAB_IDS = ("documents", "document_types", "document_alerts", "permission_requests", "delete_restore", "document_audit")
TAB_LABELS = {
    "documents": "문서관리",
    "document_types": "문서 유형",
    "document_alerts": "만료·알림",
    "permission_requests": "권한 요청",
    "delete_restore": "삭제·복구",
    "document_audit": "감사로그",
}

_DEFAULT_DOCUMENT_TYPES: tuple[dict[str, Any], ...] = (
    {
        "type_id": "employment_contract",
        "label": "근로계약서",
        "required": True,
        "expiry_required": False,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": False,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": (".pdf", ".doc", ".docx", ".hwp", ".hwpx"),
        "notify_roles": ("employee", "hr", "admin"),
    },
    {
        "type_id": "resume",
        "label": "이력서",
        "required": True,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
    {
        "type_id": "career_certificate",
        "label": "경력증명서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
    {
        "type_id": "graduation_certificate",
        "label": "졸업증명서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
    {
        "type_id": "license_certificate",
        "label": "자격증",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 730,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "manager", "hr"),
    },
    {
        "type_id": "training_completion",
        "label": "교육수료증",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "manager", "hr"),
    },
    {
        "type_id": "privacy_consent",
        "label": "개인정보 수집·이용 동의서",
        "required": True,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": (".pdf", ".png", ".jpg", ".jpeg"),
        "notify_roles": ("employee", "hr", "admin"),
    },
    {
        "type_id": "nda",
        "label": "비밀유지계약서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": False,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": (".pdf", ".doc", ".docx", ".hwp", ".hwpx"),
        "notify_roles": ("employee", "hr", "admin"),
    },
    {
        "type_id": "salary_contract",
        "label": "연봉계약서",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": False,
        "sensitive": True,
        "payroll_related": True,
        "retention_years": 5,
        "allowed_extensions": (".pdf", ".doc", ".docx", ".hwp", ".hwpx"),
        "notify_roles": ("employee", "hr", "payroll", "admin"),
    },
    {
        "type_id": "payroll_tax",
        "label": "급여·세무 관련 서류",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": False,
        "sensitive": True,
        "payroll_related": True,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("hr", "payroll", "admin"),
    },
    {
        "type_id": "identity_document",
        "label": "신분확인서류",
        "required": True,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": (".pdf", ".png", ".jpg", ".jpeg"),
        "notify_roles": ("employee", "hr", "admin"),
    },
    {
        "type_id": "visa_status",
        "label": "체류자격·비자 관련 서류",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr", "admin"),
    },
    {
        "type_id": "company_custom",
        "label": "기타 회사 지정 문서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": False,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
    {
        "type_id": "job_application",
        "label": "입사지원서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
        "document_stage": "입사 전",
    },
    {
        "type_id": "third_party_consent",
        "label": "개인정보 제3자 제공 동의서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": (".pdf", ".png", ".jpg", ".jpeg"),
        "notify_roles": ("employee", "hr", "admin"),
        "legal_mandatory": True,
    },
    {
        "type_id": "pledge",
        "label": "서약서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
    {
        "type_id": "security_pledge",
        "label": "보안서약서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr", "admin"),
        "risk_grade": "high",
    },
    {
        "type_id": "safety_health",
        "label": "안전보건 관련 문서",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "manager", "safety", "hr", "executive"),
        "legal_mandatory": True,
        "executive_report": True,
        "risk_grade": "high",
        "work_restriction_policy": "미갱신 시 현장 투입 제한 검토",
    },
    {
        "type_id": "serious_accident_training",
        "label": "중대재해 관련 교육/확인 문서",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "manager", "safety", "hr", "executive"),
        "legal_mandatory": True,
        "executive_report": True,
        "risk_grade": "critical",
        "work_restriction_policy": "미갱신 시 고위험 작업 배정 제한 검토",
    },
    {
        "type_id": "health_checkup_submission",
        "label": "건강검진 관련 제출 확인 문서",
        "required": False,
        "expiry_required": True,
        "default_validity_days": 365,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": False,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr", "safety"),
        "risk_grade": "high",
    },
    {
        "type_id": "bank_account",
        "label": "계좌 관련 증빙 문서",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": True,
        "payroll_related": True,
        "retention_years": 5,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "payroll", "hr"),
    },
    {
        "type_id": "employment_proof",
        "label": "재직 관련 증빙서류",
        "required": False,
        "expiry_required": False,
        "default_validity_days": 0,
        "approval_required": True,
        "employee_upload_allowed": True,
        "sensitive": False,
        "payroll_related": False,
        "retention_years": 3,
        "allowed_extensions": DEFAULT_ALLOWED_EXTENSIONS,
        "notify_roles": ("employee", "hr"),
    },
)

_DEFAULT_EMPLOYMENT_TYPE_RULES: tuple[dict[str, Any], ...] = (
    {"employment_type": "정규직", "required_document_types": ("employment_contract", "resume", "privacy_consent", "nda")},
    {"employment_type": "계약직", "required_document_types": ("employment_contract", "privacy_consent")},
    {"employment_type": "외국인 근로자", "required_document_types": ("employment_contract", "privacy_consent", "visa_status")},
    {"employment_type": "안전 관련 직무", "required_document_types": ("safety_health", "serious_accident_training", "training_completion")},
    {"employment_type": "급여 지급 대상자", "required_document_types": ("bank_account", "payroll_tax")},
)


def _tid(tenant_id: str | None = None) -> str:
    return str(tenant_id or session_tenant_id() or "default").strip() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().isoformat()


def _parse_date(value: str | None) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        d = _parse_date(text)
        return datetime.combine(d, datetime.min.time()) if d else None


def _restore_deadline(deleted_at: str, *, days: int = DEFAULT_RESTORE_DAYS) -> str:
    base = _parse_datetime(deleted_at) or datetime.now()
    return (base + timedelta(days=days)).date().isoformat()


def _actor(session: UserSession | None = None, uploaded_by: str = "") -> tuple[str, str, str]:
    sess = session or get_session()
    if sess:
        return sess.user_id, sess.display_name, sess.role
    return str(uploaded_by or "system"), str(uploaded_by or "system"), ROLE_ADMIN


def _files_dir(tenant_id: str) -> Path:
    return app_data_dir() / MODULE / tenant_id / "files"


def _extension(filename: str) -> str:
    return Path(str(filename or "")).suffix.lower()


def _normalize_exts(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return list(DEFAULT_ALLOWED_EXTENSIONS)
    if isinstance(values, str):
        raw = re.split(r"[,/|\s]+", values)
    else:
        raw = [str(v) for v in values]
    out = []
    for value in raw:
        v = value.strip().lower()
        if not v:
            continue
        if not v.startswith("."):
            v = f".{v}"
        out.append(v)
    return out or list(DEFAULT_ALLOWED_EXTENSIONS)


def _base_policy(row: dict[str, Any]) -> dict[str, Any]:
    policy = dict(row)
    policy.setdefault("reminder_days", list(DEFAULT_REMINDER_DAYS))
    policy.setdefault("notification_channels", list(DEFAULT_NOTIFICATION_CHANNELS))
    policy.setdefault("upload_roles", [ROLE_ADMIN, "hr"])
    policy.setdefault("view_roles", [ROLE_ADMIN, "hr"])
    policy.setdefault("download_roles", [ROLE_ADMIN, "hr"])
    policy.setdefault("active", True)
    policy.setdefault("document_stage", "재직 중")
    policy.setdefault("risk_grade", "normal")
    policy.setdefault("legal_risk_message", DEFAULT_LEGAL_REVIEW_NOTICE)
    policy.setdefault("retention_policy", "일반 보관")
    policy.setdefault("backup_policy", "암호화 백업 보관")
    policy.setdefault("approval_steps", [])
    policy.setdefault("required_employment_types", [])
    policy.setdefault("required_stages", [])
    policy.setdefault("work_restriction_policy", "")
    policy["allowed_extensions"] = _normalize_exts(policy.get("allowed_extensions"))
    policy["notify_roles"] = list(policy.get("notify_roles") or ("employee", "hr"))
    policy["notification_channels"] = list(policy.get("notification_channels") or DEFAULT_NOTIFICATION_CHANNELS)
    policy["required"] = bool(policy.get("required"))
    policy["expiry_required"] = bool(policy.get("expiry_required"))
    policy["approval_required"] = bool(policy.get("approval_required"))
    policy["employee_upload_allowed"] = bool(policy.get("employee_upload_allowed"))
    policy["sensitive"] = bool(policy.get("sensitive"))
    policy["payroll_related"] = bool(policy.get("payroll_related"))
    policy["legal_mandatory"] = bool(policy.get("legal_mandatory"))
    policy["executive_report"] = bool(policy.get("executive_report"))
    policy["contains_personal_data"] = bool(policy.get("contains_personal_data", policy["sensitive"]))
    policy["contains_unique_id"] = bool(policy.get("contains_unique_id", False))
    policy["download_allowed"] = bool(policy.get("download_allowed", True))
    policy["download_reason_required"] = bool(policy.get("download_reason_required", True))
    policy["masking_default"] = bool(policy.get("masking_default", policy["sensitive"]))
    policy["ocr_enabled"] = bool(policy.get("ocr_enabled", policy["type_id"] in {"employment_contract", "career_certificate", "graduation_certificate", "license_certificate", "training_completion", "visa_status", "safety_health"}))
    policy["e_signature_enabled"] = bool(policy.get("e_signature_enabled", policy["type_id"] in {"employment_contract", "salary_contract", "nda", "privacy_consent"}))
    policy["recoverable"] = bool(policy.get("recoverable", True))
    policy["retirement_retention"] = bool(policy.get("retirement_retention", True))
    policy["default_validity_days"] = int(policy.get("default_validity_days") or 0)
    policy["retention_years"] = int(policy.get("retention_years") or 3)
    return policy


def _seed_types() -> list[dict[str, Any]]:
    return [_base_policy(dict(row)) for row in _DEFAULT_DOCUMENT_TYPES]


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = _tid(tenant_id)
    db = load_module_db(MODULE, tid, _EMPTY)
    changed = False
    if not db.get("document_types"):
        db["document_types"] = _seed_types()
        changed = True
    else:
        by_id = {str(t.get("type_id")): t for t in db.get("document_types") or []}
        for default in _seed_types():
            if default["type_id"] not in by_id:
                db.setdefault("document_types", []).append(default)
                changed = True
        db["document_types"] = [_base_policy(t) for t in db.get("document_types") or []]
    if not db.get("seeded"):
        db["seeded"] = True
        changed = True
    if not db.get("employment_type_rules"):
        db["employment_type_rules"] = [
            {
                **rule,
                "required_document_types": list(rule.get("required_document_types") or []),
                "active": True,
                "created_at": _now_iso(),
            }
            for rule in _DEFAULT_EMPLOYMENT_TYPE_RULES
        ]
        changed = True
    if changed:
        save_module_db(MODULE, tid, db)


def _db(tenant_id: str | None = None) -> dict[str, Any]:
    ensure_seed(tenant_id)
    return load_module_db(MODULE, _tid(tenant_id), _EMPTY)


def _policy_for(doc_type: str, db: dict[str, Any]) -> dict[str, Any]:
    wanted = str(doc_type or "").strip()
    for row in db.get("document_types") or []:
        if str(row.get("type_id")) == wanted or str(row.get("label")) == wanted:
            return _base_policy(row)
    raise ValueError(f"등록되지 않은 문서 유형입니다: {doc_type}")


def _status_for(expiry_date: str, policy: dict[str, Any], *, as_of: date | None = None, base_status: str = "") -> str:
    if base_status in {STATUS_REVIEW_REQUIRED, STATUS_REJECTED, STATUS_RENEWED}:
        return base_status
    exp = _parse_date(expiry_date)
    if not exp:
        return STATUS_VALID
    today = as_of or date.today()
    if exp < today:
        return STATUS_EXPIRED
    reminder_days = [int(d) for d in (policy.get("reminder_days") or DEFAULT_REMINDER_DAYS)]
    window = max(reminder_days) if reminder_days else 0
    if (exp - today).days <= window:
        return STATUS_EXPIRING
    return STATUS_VALID


def _derive_expiry(issued_date: str, start_date: str, explicit_expiry: str, policy: dict[str, Any]) -> str:
    if explicit_expiry:
        return str(explicit_expiry)[:10]
    validity = int(policy.get("default_validity_days") or 0)
    if validity <= 0:
        return ""
    base = _parse_date(start_date) or _parse_date(issued_date)
    if not base:
        return ""
    return (base + timedelta(days=validity)).isoformat()


def _crypto_key(tenant_id: str, doc_id: str) -> bytes:
    return hashlib.sha256(f"{tenant_id}:{doc_id}:bitween-hr-documents".encode("utf-8")).digest()


def _xor_stream(data: bytes, tenant_id: str, doc_id: str) -> bytes:
    key = _crypto_key(tenant_id, doc_id)
    out = bytearray()
    counter = 0
    for i in range(0, len(data), 32):
        block_key = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
        block = data[i : i + 32]
        out.extend(b ^ block_key[j] for j, b in enumerate(block))
        counter += 1
    return bytes(out)


def _write_encrypted_file(tenant_id: str, doc_id: str, raw: bytes) -> tuple[str, str]:
    folder = _files_dir(tenant_id)
    folder.mkdir(parents=True, exist_ok=True)
    encrypted = _xor_stream(raw, tenant_id, doc_id)
    path = folder / f"{doc_id}.bin"
    envelope = b"BTW-HR-DOC:v1\n" + base64.b64encode(encrypted)
    path.write_bytes(envelope)
    return str(path), hashlib.sha256(raw).hexdigest()


def _read_encrypted_file(tenant_id: str, doc_id: str, encrypted_path: str) -> bytes:
    data = Path(encrypted_path).read_bytes()
    prefix = b"BTW-HR-DOC:v1\n"
    if not data.startswith(prefix):
        raise ValueError("지원하지 않는 문서 저장 형식입니다.")
    encrypted = base64.b64decode(data[len(prefix) :])
    return _xor_stream(encrypted, tenant_id, doc_id)


def _canonical_hash(row: dict[str, Any]) -> str:
    import json

    payload = {k: v for k, v in row.items() if k != "hash"}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _audit(
    db: dict[str, Any],
    *,
    actor_id: str,
    action: str,
    document_id: str = "",
    details: dict[str, Any] | None = None,
    reason: str = "",
    result_status: str = "success",
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    actor_name = sess.display_name if sess and sess.user_id == actor_id else ""
    actor_role = sess.role if sess and sess.user_id == actor_id else ""
    logs = db.setdefault("audit_logs", [])
    prev_hash = str(logs[-1].get("hash") or "") if logs else ""
    row = {
        "id": _new_id(),
        "occurred_at": _now_iso(),
        "actor_id": actor_id,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "action": action,
        "document_id": document_id,
        "reason": str(reason or ""),
        "result_status": result_status,
        "details": dict(details or {}),
        "prev_hash": prev_hash,
    }
    row["hash"] = _canonical_hash(row)
    logs.append(row)
    return row


def verify_audit_log_integrity(*, tenant_id: str | None = None) -> dict[str, Any]:
    """Validate the append-only hash chain used as a lightweight WORM guard."""

    rows = list(_db(tenant_id).get("audit_logs") or [])
    prev = ""
    for idx, row in enumerate(rows):
        if not row.get("hash"):
            # Legacy pre-governance rows are immutable in storage but do not
            # participate in the hash chain.  The next hashed row restarts it.
            prev = ""
            continue
        if str(row.get("prev_hash") or "") != prev:
            return {"ok": False, "index": idx, "reason": "prev_hash_mismatch", "id": row.get("id", "")}
        expected = _canonical_hash(row)
        if str(row.get("hash") or "") != expected:
            return {"ok": False, "index": idx, "reason": "hash_mismatch", "id": row.get("id", "")}
        prev = str(row.get("hash") or "")
    return {"ok": True, "count": len(rows), "head_hash": prev}


def _notification(
    db: dict[str, Any],
    *,
    document: dict[str, Any],
    ntype: str,
    title: str,
    message: str,
    target_roles: Iterable[str],
    key: str = "",
    channels: Iterable[str] | None = None,
    priority: str = "normal",
    escalation_level: int = 0,
    due_at: str = "",
) -> dict[str, Any] | None:
    key = key or f"{ntype}:{document.get('id')}:{title}"
    for n in db.get("notifications") or []:
        if n.get("dedupe_key") == key:
            return None
    row = {
        "id": _new_id(),
        "created_at": _now_iso(),
        "type": ntype,
        "title": title,
        "message": message,
        "document_id": document.get("id", ""),
        "employee_id": document.get("employee_id", ""),
        "employee_user_id": document.get("employee_user_id", ""),
        "target_roles": list(target_roles),
        "channels": list(channels or DEFAULT_NOTIFICATION_CHANNELS),
        "status": "발송 대기",
        "send_results": [],
        "read_at": "",
        "acknowledged_at": "",
        "acknowledged_by": "",
        "action_completed_at": "",
        "action_note": "",
        "priority": priority,
        "escalation_level": escalation_level,
        "due_at": due_at,
        "dedupe_key": key,
        "read": False,
    }
    db.setdefault("notifications", []).append(row)
    return row


def _mask_filename(filename: str) -> str:
    suffix = Path(filename).suffix
    stem = Path(filename).stem
    if len(stem) <= 2:
        return f"**{suffix}"
    return f"{stem[0]}***{stem[-1]}{suffix}"


_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("resident_registration_number", re.compile(r"\b\d{6}[- ]?[1-8]\d{6}\b")),
    ("phone_number", re.compile(r"\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b")),
    ("bank_account", re.compile(r"\b\d{2,6}[- ]\d{2,6}[- ]\d{4,8}\b")),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
)


def mask_text_value(value: str) -> str:
    """Apply conservative Korean HR PII masking for previews/OCR snippets."""

    text = str(value or "")

    def _rrn(m: re.Match[str]) -> str:
        raw = m.group(0)
        return raw[:8] + "*" * max(0, len(raw) - 8)

    def _phone(m: re.Match[str]) -> str:
        raw = m.group(0)
        return raw[:4] + "****" + raw[-4:]

    def _account(m: re.Match[str]) -> str:
        raw = m.group(0)
        return raw[:3] + "*" * max(3, len(raw) - 6) + raw[-3:]

    text = _PII_PATTERNS[0][1].sub(_rrn, text)
    text = _PII_PATTERNS[1][1].sub(_phone, text)
    text = _PII_PATTERNS[2][1].sub(_account, text)
    text = _PII_PATTERNS[3][1].sub(lambda m: m.group(0).split("@", 1)[0][:2] + "***@" + m.group(0).split("@", 1)[1], text)
    return text


def _detect_personal_data(raw: bytes, *, filename: str = "") -> dict[str, Any]:
    sample = ""
    try:
        sample = raw[:200_000].decode("utf-8", errors="ignore")
    except Exception:
        sample = ""
    matches: dict[str, int] = {}
    for label, pattern in _PII_PATTERNS:
        count = len(pattern.findall(sample))
        if count:
            matches[label] = count
    ext = _extension(filename)
    encrypted_hint = raw.startswith(b"%PDF-") and b"/Encrypt" in raw[:4096]
    suspicious = b"\x00" in raw[:1024] and ext in {".txt", ".csv"}
    return {
        "personal_data_detected": bool(matches),
        "unique_id_detected": bool(matches.get("resident_registration_number")),
        "pii_matches": matches,
        "masking_preview": mask_text_value(sample[:1000]) if sample else "",
        "encrypted_upload_detected": bool(encrypted_hint),
        "damage_suspected": bool(suspicious),
    }


def _public_doc(row: dict[str, Any], *, mask_sensitive: bool = True) -> dict[str, Any]:
    out = dict(row)
    out.pop("encrypted_path", None)
    out.pop("file_hash", None)
    out.pop("masking_preview", None)
    if mask_sensitive and out.get("ocr_extracted_values"):
        out["ocr_extracted_values"] = {
            str(k): mask_text_value(str(v)) for k, v in dict(out.get("ocr_extracted_values") or {}).items()
        }
    filename = str(out.get("file_name") or "")
    out["display_file_name"] = _mask_filename(filename) if mask_sensitive and out.get("sensitive") else filename
    out["payroll_restricted"] = bool(out.get("payroll_related"))
    out["sensitive_restricted"] = bool(out.get("sensitive"))
    out["legal_review_notice"] = DEFAULT_LEGAL_REVIEW_NOTICE
    return out


def list_document_types(*, tenant_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
    db = _db(tenant_id)
    rows = [_base_policy(t) for t in db.get("document_types") or []]
    if active_only:
        rows = [r for r in rows if r.get("active", True)]
    return sorted(rows, key=lambda r: str(r.get("label") or ""))


def document_type_label(doc_type: str) -> str:
    for row in list_document_types(active_only=False):
        if row.get("type_id") == doc_type:
            return str(row.get("label") or doc_type)
    return DOCUMENT_LABELS.get(str(doc_type), str(doc_type))


def save_document_type(values: dict[str, Any], *, tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 유형 설정은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)
    type_id = str(values.get("type_id") or "").strip() or re.sub(r"\W+", "_", str(values.get("label") or "custom").casefold()).strip("_")
    if not type_id:
        raise ValueError("문서 유형 ID 또는 라벨이 필요합니다.")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        policy = _base_policy({**values, "type_id": type_id})
        rows = db.setdefault("document_types", [])
        for idx, row in enumerate(rows):
            if str(row.get("type_id")) == type_id:
                rows[idx] = {**row, **policy, "updated_at": _now_iso(), "updated_by": actor_id}
                _audit(db, actor_id=actor_id, action="document_type_updated", details={"type_id": type_id})
                return rows[idx]
        policy.update({"created_at": _now_iso(), "created_by": actor_id})
        rows.append(policy)
        _audit(db, actor_id=actor_id, action="document_type_created", details={"type_id": type_id})
        return policy

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def deactivate_document_type(type_id: str, *, tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 유형 삭제는 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for row in db.get("document_types") or []:
            if str(row.get("type_id")) == str(type_id):
                row["active"] = False
                row["deleted_at"] = _now_iso()
                row["deleted_by"] = actor_id
                _audit(db, actor_id=actor_id, action="document_type_deactivated", details={"type_id": type_id})
                return row
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_employment_type_rules(*, tenant_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
    rows = [dict(r) for r in _db(tenant_id).get("employment_type_rules") or []]
    if active_only:
        rows = [r for r in rows if r.get("active", True)]
    return sorted(rows, key=lambda r: str(r.get("employment_type") or ""))


def save_employment_type_rule(
    values: dict[str, Any],
    *,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("고용형태별 필수 문서 설정은 HR 관리자 또는 최고관리자만 가능합니다.")
    employment_type = str(values.get("employment_type") or "").strip()
    if not employment_type:
        raise ValueError("고용형태가 필요합니다.")
    docs = values.get("required_document_types") or values.get("document_types") or []
    if isinstance(docs, str):
        docs = [d.strip() for d in re.split(r"[,/|\s]+", docs) if d.strip()]
    actor_id, _actor_name, _role = _actor(sess)
    tid = _tid(tenant_id)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = {
            "employment_type": employment_type,
            "required_document_types": [str(d) for d in docs],
            "legal_entity": str(values.get("legal_entity") or ""),
            "department": str(values.get("department") or ""),
            "job_duty": str(values.get("job_duty") or ""),
            "workplace": str(values.get("workplace") or ""),
            "active": bool(values.get("active", True)),
            "updated_at": _now_iso(),
            "updated_by": actor_id,
        }
        rows = db.setdefault("employment_type_rules", [])
        for idx, existing in enumerate(rows):
            if str(existing.get("employment_type") or "") == employment_type:
                rows[idx] = {**existing, **row}
                _audit(db, actor_id=actor_id, action="employment_type_rule_updated", details={"employment_type": employment_type}, session=sess)
                return dict(rows[idx])
        row["id"] = _new_id()
        row["created_at"] = _now_iso()
        rows.append(row)
        _audit(db, actor_id=actor_id, action="employment_type_rule_created", details={"employment_type": employment_type}, session=sess)
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def required_document_gaps(
    employee: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Return missing required document types for one employee profile."""

    db = _db(tenant_id)
    emp_id = str(employee.get("employee_id") or employee.get("employee_no") or employee.get("id") or employee.get("name") or employee.get("employee_name") or "")
    emp_type = str(employee.get("employment_type") or employee.get("employmentStatus") or "").strip()
    required: set[str] = {
        str(t.get("type_id"))
        for t in db.get("document_types") or []
        if t.get("required") and t.get("active", True)
    }
    for rule in db.get("employment_type_rules") or []:
        if not rule.get("active", True):
            continue
        if emp_type and str(rule.get("employment_type") or "") not in {emp_type, "급여 지급 대상자"}:
            continue
        # Optional dimensions narrow the rule when configured.
        for dim in ("legal_entity", "department", "job_duty", "workplace"):
            if rule.get(dim) and str(rule.get(dim)) != str(employee.get(dim) or ""):
                break
        else:
            required.update(str(d) for d in rule.get("required_document_types") or [])
    existing = {
        str(d.get("document_type"))
        for d in db.get("documents") or []
        if not d.get("deleted") and d.get("current", True) and str(d.get("employee_id") or d.get("employee_no") or d.get("employee_name")) == emp_id
    }
    by_type = {str(t.get("type_id")): str(t.get("label") or t.get("type_id")) for t in db.get("document_types") or []}
    missing = sorted(required - existing)
    return {
        "employee_id": emp_id,
        "employment_type": emp_type,
        "required_document_types": sorted(required),
        "submitted_document_types": sorted(existing),
        "missing_document_types": missing,
        "missing_labels": [by_type.get(t, t) for t in missing],
    }


def upload_document(
    *,
    employee_id: str,
    employee_name: str,
    document_type: str,
    document_name: str = "",
    department: str = "",
    position: str = "",
    employee_user_id: str = "",
    employee_no: str = "",
    legal_entity: str = "",
    workplace: str = "",
    job_title: str = "",
    job_duty: str = "",
    employment_type: str = "",
    employment_status: str = "재직",
    source_path: str | Path | None = None,
    file_bytes: bytes | None = None,
    file_name: str = "",
    file_password_supplied: bool = False,
    duplicate_action: str = "new_version",
    issued_date: str = "",
    start_date: str = "",
    expiry_date: str = "",
    renewal_required: bool | None = None,
    alert_base_date: str = "",
    memo: str = "",
    approval_line: list[dict[str, Any]] | None = None,
    uploaded_by: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Upload or renew an employee HR document.

    Duplicate current documents with the same employee/type/name are handled as
    renewal versions: the old row becomes 갱신 완료 and the new row is current.
    """

    tid = _tid(tenant_id)
    db = _db(tid)
    policy = _policy_for(document_type, db)
    sess = session or get_session()
    if not can_upload_employee_document(employee_user_id, session=sess, doc_type_policy=policy):
        raise PermissionError("해당 직원 문서를 업로드할 권한이 없습니다.")

    if source_path is None and file_bytes is None:
        raise ValueError("업로드할 파일 경로 또는 바이트가 필요합니다.")
    if source_path is not None:
        path = Path(source_path)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        raw = path.read_bytes()
        file_name = file_name or path.name
    else:
        raw = bytes(file_bytes or b"")
        file_name = file_name or "upload.bin"
    if not raw:
        raise ValueError("빈 파일은 업로드할 수 없습니다.")

    settings = db.get("settings") or {}
    max_size = int(settings.get("max_upload_bytes") or DEFAULT_MAX_UPLOAD_BYTES)
    if len(raw) > max_size:
        raise ValueError(f"파일 용량이 제한({max_size} bytes)을 초과했습니다.")
    ext = _extension(file_name)
    allowed = set(_normalize_exts(policy.get("allowed_extensions")))
    if ext not in allowed:
        raise ValueError(f"허용되지 않은 파일 형식입니다: {ext or '(확장자 없음)'}")
    if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR" in raw:
        raise ValueError("악성코드 검사 결과 의심 파일로 차단되었습니다.")
    scan = _detect_personal_data(raw, filename=file_name)
    if scan.get("damage_suspected"):
        raise ValueError("파일 손상 또는 확장자 위장 가능성이 있어 업로드할 수 없습니다.")
    if scan.get("encrypted_upload_detected") and not file_password_supplied:
        raise ValueError(
            "비밀번호로 보호된 파일입니다. 일회성 비밀번호로 암호 해제 후 보안 저장소에 재암호화하거나, "
            "비밀번호를 해제한 파일을 업로드하세요."
        )

    expiry = _derive_expiry(issued_date, start_date, expiry_date, policy)
    if policy.get("expiry_required") and not expiry:
        raise ValueError("이 문서 유형은 만료일이 필요합니다.")
    exp_dt = _parse_date(expiry)
    start_dt = _parse_date(start_date)
    issued_dt = _parse_date(issued_date)
    if exp_dt and start_dt and exp_dt < start_dt:
        raise ValueError("만료일은 시작일보다 빠를 수 없습니다.")
    if exp_dt and issued_dt and exp_dt < issued_dt:
        raise ValueError("만료일은 발급일보다 빠를 수 없습니다.")

    actor_id, actor_name, _role = _actor(sess, uploaded_by)
    doc_id = _new_id()
    encrypted_path, file_hash = _write_encrypted_file(tid, doc_id, raw)
    mime, _enc = mimetypes.guess_type(file_name)
    doc_label = str(policy.get("label") or document_type)
    doc_name = str(document_name or doc_label)

    def mut(data: dict[str, Any]) -> dict[str, Any]:
        latest_version = 0
        duplicate_of = ""
        for existing in data.get("documents") or []:
            if not existing.get("deleted") and str(existing.get("file_hash") or "") == file_hash:
                duplicate_of = str(existing.get("id") or "")
            same_key = (
                not existing.get("deleted")
                and existing.get("current", True)
                and str(existing.get("employee_id") or "") == str(employee_id)
                and str(existing.get("document_type") or "") == str(policy["type_id"])
                and str(existing.get("document_name") or "") == doc_name
            )
            if str(existing.get("employee_id") or "") == str(employee_id) and str(existing.get("document_type") or "") == str(policy["type_id"]):
                latest_version = max(latest_version, int(existing.get("version") or 0))
            if same_key and duplicate_action != "new_document":
                existing["current"] = False
                existing["status"] = STATUS_RENEWED
                existing["renewed_by_document_id"] = doc_id
                existing["last_modified_by"] = actor_id
                existing["last_modified_at"] = _now_iso()
        status = STATUS_REVIEW_REQUIRED if policy.get("approval_required") else _status_for(expiry, policy)
        row = {
            "id": doc_id,
            "employee_id": str(employee_id),
            "employee_user_id": str(employee_user_id or ""),
            "employee_name": str(employee_name),
            "employee_no": str(employee_no or employee_id),
            "legal_entity": str(legal_entity or ""),
            "workplace": str(workplace or ""),
            "department": str(department or ""),
            "position": str(position or ""),
            "job_title": str(job_title or position or ""),
            "job_duty": str(job_duty or ""),
            "employment_type": str(employment_type or ""),
            "employment_status": str(employment_status or "재직"),
            "document_type": str(policy["type_id"]),
            "document_type_label": doc_label,
            "document_name": doc_name,
            "document_description": str(policy.get("description") or ""),
            "file_name": str(file_name),
            "file_extension": ext,
            "file_format": mime or ext.lstrip(".").upper(),
            "file_size": len(raw),
            "encrypted": True,
            "encrypted_path": encrypted_path,
            "file_hash": file_hash,
            "duplicate": bool(duplicate_of),
            "duplicate_of_document_id": duplicate_of,
            "duplicate_resolution": duplicate_action if duplicate_of else "",
            "uploaded_at": _now_iso(),
            "uploaded_by": actor_id,
            "uploaded_by_name": actor_name,
            "issued_date": str(issued_date or "")[:10],
            "start_date": str(start_date or "")[:10],
            "expiry_date": expiry,
            "renewal_required": bool(renewal_required) if renewal_required is not None else bool(policy.get("expiry_required") or expiry),
            "alert_base_date": str(alert_base_date or expiry or "")[:10],
            "next_renewal_date": str(expiry or "")[:10],
            "notification_targets": list(policy.get("notify_roles") or []),
            "notification_channels": list(policy.get("notification_channels") or DEFAULT_NOTIFICATION_CHANNELS),
            "status": status,
            "approval_status": "검토대기" if status == STATUS_REVIEW_REQUIRED else "승인불필요",
            "approval_line": list(approval_line or policy.get("approval_steps") or []),
            "admin_memo": str(memo or ""),
            "version": latest_version + 1,
            "current": True,
            "last_modified_by": actor_id,
            "last_modified_at": _now_iso(),
            "download_history": [],
            "view_history": [],
            "sensitive": bool(policy.get("sensitive") or is_sensitive_document(doc_label)),
            "payroll_related": bool(policy.get("payroll_related") or is_payroll_document(doc_label)),
            "legal_mandatory": bool(policy.get("legal_mandatory")),
            "executive_report": bool(policy.get("executive_report")),
            "risk_grade": str(policy.get("risk_grade") or "normal"),
            "legal_risk_message": str(policy.get("legal_risk_message") or DEFAULT_LEGAL_REVIEW_NOTICE),
            "work_restriction_policy": str(policy.get("work_restriction_policy") or ""),
            "retention_years": int(policy.get("retention_years") or 3),
            "retention_status": str(policy.get("retention_policy") or "일반 보관"),
            "backup_status": "백업 보관",
            "backup_required": True,
            "retention_locked": bool(policy.get("legal_mandatory")),
            "download_restricted": not bool(policy.get("download_allowed", True)),
            "download_reason_required": bool(policy.get("download_reason_required", True)),
            "contains_personal_data": bool(policy.get("contains_personal_data") or scan.get("personal_data_detected")),
            "contains_unique_id": bool(policy.get("contains_unique_id") or scan.get("unique_id_detected")),
            "personal_data_detected": bool(scan.get("personal_data_detected")),
            "unique_id_detected": bool(scan.get("unique_id_detected")),
            "pii_matches": dict(scan.get("pii_matches") or {}),
            "masking_applied": bool(policy.get("masking_default") or scan.get("personal_data_detected")),
            "masking_review_required": bool(scan.get("personal_data_detected")),
            "masking_preview": str(scan.get("masking_preview") or ""),
            "ocr_enabled": bool(policy.get("ocr_enabled")),
            "ocr_status": "검토 필요" if policy.get("ocr_enabled") else "비대상",
            "ocr_extracted_values": {},
            "malware_scan_result": "통과",
            "encrypted_upload_detected": bool(scan.get("encrypted_upload_detected")),
            "file_password_reencrypted": bool(file_password_supplied and scan.get("encrypted_upload_detected")),
            "reviewed_by": "",
            "reviewed_at": "",
            "rejection_reason": "",
            "delete_requested_by": "",
            "delete_approved_by": "",
            "deleted_at": "",
            "delete_reason": "",
            "recoverable_until": "",
            "restore_status": "해당없음",
            "deleted": False,
        }
        data.setdefault("documents", []).append(row)
        data.setdefault("backup_records", []).append(
            {
                "id": _new_id(),
                "document_id": doc_id,
                "file_hash": file_hash,
                "storage_path": encrypted_path,
                "backup_status": "백업 보관",
                "encrypted": True,
                "created_at": _now_iso(),
                "access_roles": ["admin"],
            }
        )
        _audit(
            data,
            actor_id=actor_id,
            action="document_uploaded",
            document_id=doc_id,
            details={
                "employee_id": employee_id,
                "document_type": policy["type_id"],
                "version": row["version"],
                "duplicate": bool(duplicate_of),
                "malware_scan_result": row["malware_scan_result"],
                "encrypted_upload_detected": row["encrypted_upload_detected"],
            },
            session=sess,
        )
        if duplicate_of:
            _audit(data, actor_id=actor_id, action="document_duplicate_checked", document_id=doc_id, details={"duplicate_of_document_id": duplicate_of, "resolution": duplicate_action}, session=sess)
        _notification(
            data,
            document=row,
            ntype="hr_document_review_requested" if status == STATUS_REVIEW_REQUIRED else "hr_document_uploaded",
            title=f"[문서관리] {doc_label} 업로드",
            message=f"{employee_name} · {doc_name} · 상태: {status}",
            target_roles=policy.get("notify_roles") or ("hr",),
            channels=policy.get("notification_channels") or DEFAULT_NOTIFICATION_CHANNELS,
            key=f"upload:{doc_id}",
        )
        return _public_doc(row, mask_sensitive=False)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def _iter_visible_documents(
    db: dict[str, Any],
    *,
    session: UserSession | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    sess = session or get_session()
    rows: list[dict[str, Any]] = []
    for row in db.get("documents") or []:
        if row.get("deleted") and not (include_deleted and can_manage_employee_documents(sess)):
            continue
        if can_view_employee_documents(str(row.get("employee_user_id") or ""), session=sess, document=row):
            rows.append(row)
    return rows


def list_employee_documents(
    *,
    tenant_id: str | None = None,
    session: UserSession | None = None,
    filters: dict[str, Any] | None = None,
    current_only: bool = False,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    sync_expiration_statuses(tenant_id=tid)
    db = _db(tid)
    rows = _iter_visible_documents(db, session=session, include_deleted=include_deleted or bool((filters or {}).get("include_deleted")))
    f = filters or {}

    def hit(row: dict[str, Any]) -> bool:
        if current_only and not row.get("current", True):
            return False
        for key in (
            "employee_name",
            "employee_id",
            "employee_no",
            "legal_entity",
            "workplace",
            "department",
            "position",
            "job_title",
            "job_duty",
            "employment_type",
            "employment_status",
            "document_type",
            "status",
            "approval_status",
            "uploaded_by",
            "reviewed_by",
            "retention_status",
        ):
            val = str(f.get(key) or "").strip()
            if val and val.casefold() not in str(row.get(key) or row.get(f"{key}_label") or "").casefold():
                return False
        for key in ("sensitive", "contains_unique_id", "download_restricted", "deleted", "backup_required", "retention_locked", "ocr_enabled", "executive_report", "legal_mandatory"):
            if key in f and f.get(key) not in (None, "") and bool(row.get(key)) != bool(f.get(key)):
                return False
        if f.get("expiring_within_days") not in (None, ""):
            exp = _parse_date(str(row.get("expiry_date") or ""))
            if not exp:
                return False
            days = int(f.get("expiring_within_days") or 0)
            delta = (exp - date.today()).days
            if delta < 0 or delta > days:
                return False
        return True

    return [_public_doc(r) for r in rows if hit(r)]


def _active_permission_grants(db: dict[str, Any], *, document_id: str, user_id: str, scope: str = "") -> list[dict[str, Any]]:
    now = datetime.now()
    out: list[dict[str, Any]] = []
    for req in db.get("permission_requests") or []:
        if str(req.get("document_id") or "") != str(document_id):
            continue
        if str(req.get("requester_id") or "") != str(user_id):
            continue
        if str(req.get("status") or "") != "승인":
            continue
        if scope and scope not in set(req.get("scopes") or []):
            continue
        expires = _parse_datetime(str(req.get("expires_at") or ""))
        if expires and expires < now:
            req["status"] = "만료"
            req["expired_at"] = _now_iso()
            continue
        out.append(req)
    return out


def _can_view_unmasked(document: dict[str, Any], *, session: UserSession | None = None, db: dict[str, Any] | None = None) -> bool:
    sess = session or get_session()
    if not sess:
        return False
    if can_manage_employee_documents(sess):
        return True
    if document.get("payroll_related") and normalize_role(sess.role) == ROLE_FINANCE:
        return True
    data = db or _db()
    return bool(_active_permission_grants(data, document_id=str(document.get("id") or ""), user_id=sess.user_id, scope="unmasked_view"))


def get_document(
    document_id: str,
    *,
    tenant_id: str | None = None,
    session: UserSession | None = None,
    include_deleted: bool = False,
    unmasked: bool = False,
) -> dict[str, Any] | None:
    db = _db(tenant_id)
    for row in db.get("documents") or []:
        if str(row.get("id")) == str(document_id) and (not row.get("deleted") or include_deleted):
            if row.get("deleted") and not can_manage_employee_documents(session):
                raise PermissionError("삭제 표시 문서는 최고관리자/HR 관리자만 조회할 수 있습니다.")
            if not can_view_employee_documents(str(row.get("employee_user_id") or ""), session=session, document=row):
                raise PermissionError("문서를 조회할 권한이 없습니다.")
            if unmasked and not _can_view_unmasked(row, session=session, db=db):
                raise PermissionError("비마스킹 원본 메타데이터를 조회할 권한이 없습니다.")
            return _public_doc(row, mask_sensitive=not unmasked)
    return None


def request_document_permission(
    document_id: str,
    *,
    reason: str,
    scopes: Iterable[str] = ("unmasked_view",),
    duration_hours: int = 24,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not sess:
        raise PermissionError("로그인이 필요합니다.")
    reason_text = str(reason or "").strip()
    if not reason_text:
        raise ValueError("권한 요청 사유가 필요합니다.")
    scope_list = [str(s).strip() for s in scopes if str(s).strip()]
    if not scope_list:
        raise ValueError("권한 요청 범위가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        doc = next((r for r in db.get("documents") or [] if str(r.get("id")) == str(document_id) and not r.get("deleted")), None)
        if doc is None:
            raise FileNotFoundError(document_id)
        # A requester may ask for elevated access only if they can at least
        # identify the document through normal HR visibility rules.
        if not can_view_employee_documents(str(doc.get("employee_user_id") or ""), session=sess, document=doc):
            raise PermissionError("권한 요청 대상 문서를 조회할 수 없습니다.")
        row = {
            "id": _new_id(),
            "document_id": document_id,
            "employee_id": doc.get("employee_id", ""),
            "requester_id": actor_id,
            "requester_name": actor_name,
            "requester_role": sess.role,
            "scopes": scope_list,
            "reason": reason_text,
            "duration_hours": max(1, int(duration_hours or 1)),
            "requested_at": _now_iso(),
            "status": "대기",
            "approved_by": "",
            "approved_at": "",
            "expires_at": "",
            "revoked_at": "",
            "review_memo": "",
        }
        db.setdefault("permission_requests", []).append(row)
        _audit(db, actor_id=actor_id, action="permission_requested", document_id=document_id, reason=reason_text, details={"request_id": row["id"], "scopes": scope_list}, session=sess)
        _notification(db, document=doc, ntype="hr_document_permission_requested", title="[문서관리] 권한 요청", message=f"{actor_name} · {doc.get('document_name')} · {', '.join(scope_list)}", target_roles=("hr", "admin"), key=f"permission-request:{row['id']}")
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def approve_permission_request(
    request_id: str,
    *,
    duration_hours: int | None = None,
    memo: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 권한 승인은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = next((r for r in db.get("permission_requests") or [] if str(r.get("id")) == str(request_id)), None)
        if row is None:
            raise FileNotFoundError(request_id)
        if str(row.get("status") or "") != "대기":
            raise ValueError("이미 처리된 권한 요청입니다.")
        hours = max(1, int(duration_hours or row.get("duration_hours") or 24))
        expires = datetime.now() + timedelta(hours=hours)
        row.update(
            {
                "status": "승인",
                "approved_by": actor_id,
                "approved_by_name": actor_name,
                "approved_at": _now_iso(),
                "expires_at": expires.isoformat(timespec="seconds"),
                "review_memo": str(memo or ""),
            }
        )
        _audit(db, actor_id=actor_id, action="permission_approved", document_id=str(row.get("document_id") or ""), reason=str(row.get("reason") or ""), details={"request_id": request_id, "expires_at": row["expires_at"]}, session=sess)
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def reject_permission_request(
    request_id: str,
    *,
    reason: str,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 권한 반려는 HR 관리자 또는 최고관리자만 가능합니다.")
    if not str(reason or "").strip():
        raise ValueError("권한 반려 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = next((r for r in db.get("permission_requests") or [] if str(r.get("id")) == str(request_id)), None)
        if row is None:
            raise FileNotFoundError(request_id)
        row.update({"status": "반려", "rejected_by": actor_id, "rejected_by_name": actor_name, "rejected_at": _now_iso(), "review_memo": str(reason).strip()})
        _audit(db, actor_id=actor_id, action="permission_rejected", document_id=str(row.get("document_id") or ""), reason=str(reason), details={"request_id": request_id}, session=sess)
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def revoke_permission_grant(
    request_id: str,
    *,
    reason: str,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 권한 회수는 HR 관리자 또는 최고관리자만 가능합니다.")
    if not str(reason or "").strip():
        raise ValueError("권한 회수 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = next((r for r in db.get("permission_requests") or [] if str(r.get("id")) == str(request_id)), None)
        if row is None:
            raise FileNotFoundError(request_id)
        row.update({"status": "회수", "revoked_by": actor_id, "revoked_at": _now_iso(), "revoke_reason": str(reason).strip()})
        _audit(db, actor_id=actor_id, action="permission_revoked", document_id=str(row.get("document_id") or ""), reason=str(reason), details={"request_id": request_id}, session=sess)
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_permission_requests(*, tenant_id: str | None = None, status: str = "") -> list[dict[str, Any]]:
    rows = list(_db(tenant_id).get("permission_requests") or [])
    if status:
        rows = [r for r in rows if str(r.get("status") or "") == status]
    return rows


def record_view(document_id: str, *, tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    tid = _tid(tenant_id)
    sess = session or get_session()
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id) or row.get("deleted"):
                continue
            if not can_view_employee_documents(str(row.get("employee_user_id") or ""), session=sess, document=row):
                raise PermissionError("문서를 열람할 권한이 없습니다.")
            event = {"at": _now_iso(), "user_id": actor_id, "user_name": actor_name}
            row.setdefault("view_history", []).append(event)
            _audit(db, actor_id=actor_id, action="document_viewed", document_id=document_id, session=sess)
            return _public_doc(row)
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def download_document(
    document_id: str,
    *,
    reason: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
    masked: bool = False,
    ip_address: str = "",
    device_info: str = "",
) -> tuple[bytes, dict[str, Any]]:
    tid = _tid(tenant_id)
    sess = session or get_session()
    actor_id, actor_name, _role = _actor(sess)
    reason_text = str(reason or "").strip()
    payload: bytes | None = None
    public: dict[str, Any] | None = None

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        nonlocal payload, public
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id) or row.get("deleted"):
                continue
            if not can_download_document(row, session=sess):
                raise PermissionError("문서를 다운로드할 권한이 없습니다.")
            policy = _policy_for(str(row.get("document_type")), db)
            has_download_grant = bool(sess and _active_permission_grants(db, document_id=str(row.get("id") or ""), user_id=sess.user_id, scope="download"))
            if row.get("download_restricted") and not (can_manage_employee_documents(sess) or has_download_grant):
                raise PermissionError("이 문서 유형은 다운로드 제한 상태입니다. 권한 요청이 필요합니다.")
            if policy.get("download_reason_required", True) and not reason_text:
                raise ValueError("문서 다운로드 사유가 필요합니다.")
            payload = _read_encrypted_file(tid, str(row.get("id")), str(row.get("encrypted_path")))
            event = {
                "at": _now_iso(),
                "user_id": actor_id,
                "user_name": actor_name,
                "reason": reason_text,
                "masked": bool(masked),
                "ip_address": ip_address,
                "device_info": device_info,
            }
            row.setdefault("download_history", []).append(event)
            row["last_downloaded_at"] = event["at"]
            row["last_downloaded_by"] = actor_id
            _audit(
                db,
                actor_id=actor_id,
                action="document_downloaded",
                document_id=document_id,
                reason=reason_text,
                details={
                    "file_name": row.get("file_name"),
                    "version": row.get("version"),
                    "masked": bool(masked),
                    "ip_address": ip_address,
                    "device_info": device_info,
                },
                session=sess,
            )
            public = _public_doc(row, mask_sensitive=masked)
            return public
        raise FileNotFoundError(document_id)

    meta = mutate_module_db(MODULE, tid, _EMPTY, mut)
    assert payload is not None
    return payload, meta


def approve_document(document_id: str, *, memo: str = "", tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    sess = session or get_session()
    if not can_approve_document_requests(sess):
        raise PermissionError("문서를 승인할 권한이 없습니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id) or row.get("deleted"):
                continue
            policy = _policy_for(str(row.get("document_type")), db)
            row["status"] = _status_for(str(row.get("expiry_date") or ""), policy)
            row["approval_status"] = "승인완료"
            row["reviewed_by"] = actor_id
            row["reviewed_by_name"] = actor_name
            row["reviewed_at"] = _now_iso()
            row["last_modified_by"] = actor_id
            row["last_modified_at"] = _now_iso()
            if memo:
                row["admin_memo"] = memo
            _audit(db, actor_id=actor_id, action="document_approved", document_id=document_id, details={"status": row["status"]}, session=sess)
            _notification(db, document=row, ntype="hr_document_approved", title="[문서관리] 문서 승인 완료", message=f"{row.get('employee_name')} · {row.get('document_name')} 승인 완료", target_roles=("employee", "hr"), key=f"approved:{document_id}")
            return _public_doc(row, mask_sensitive=False)
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def reject_document(document_id: str, *, reason: str, tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    sess = session or get_session()
    if not can_approve_document_requests(sess):
        raise PermissionError("문서를 반려할 권한이 없습니다.")
    if not str(reason or "").strip():
        raise ValueError("반려 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id) or row.get("deleted"):
                continue
            row["status"] = STATUS_REJECTED
            row["approval_status"] = "반려"
            row["rejection_reason"] = str(reason).strip()
            row["reviewed_by"] = actor_id
            row["reviewed_by_name"] = actor_name
            row["reviewed_at"] = _now_iso()
            row["last_modified_by"] = actor_id
            row["last_modified_at"] = _now_iso()
            _audit(db, actor_id=actor_id, action="document_rejected", document_id=document_id, reason=str(reason), details={"reason": reason}, session=sess)
            _notification(db, document=row, ntype="hr_document_rejected", title="[문서관리] 문서 반려·재업로드 요청", message=f"{row.get('employee_name')} · {row.get('document_name')} 반려: {reason}", target_roles=("employee", "hr"), key=f"rejected:{document_id}")
            return _public_doc(row, mask_sensitive=False)
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def soft_delete_document(document_id: str, *, reason: str = "", tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서를 삭제할 권한이 없습니다.")
    if not str(reason or "").strip():
        raise ValueError("삭제 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id):
                continue
            deleted_at = _now_iso()
            row["deleted"] = True
            row["deleted_at"] = deleted_at
            row["deleted_by"] = actor_id
            row["delete_approved_by"] = actor_id
            row["delete_reason"] = str(reason or "")
            row["recoverable_until"] = _restore_deadline(deleted_at, days=int((db.get("settings") or {}).get("restore_window_days") or DEFAULT_RESTORE_DAYS))
            row["restore_status"] = "복구 가능"
            _audit(db, actor_id=actor_id, action="document_deleted", document_id=document_id, reason=str(reason), details={"reason": reason, "soft_delete": True, "recoverable_until": row["recoverable_until"]}, session=sess)
            _notification(db, document=row, ntype="hr_document_deleted", title="[문서관리] 문서 삭제/변경", message=f"{row.get('employee_name')} · {row.get('document_name')} 삭제 처리", target_roles=("hr", "admin"), key=f"deleted:{document_id}")
            return _public_doc(row)
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def request_delete_document(
    document_id: str,
    *,
    reason: str,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Create a deletion request; employees never directly delete originals."""

    sess = session or get_session()
    if not sess:
        raise PermissionError("로그인이 필요합니다.")
    if not str(reason or "").strip():
        raise ValueError("삭제 요청 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        doc = next((r for r in db.get("documents") or [] if str(r.get("id")) == str(document_id) and not r.get("deleted")), None)
        if doc is None:
            raise FileNotFoundError(document_id)
        if not can_view_employee_documents(str(doc.get("employee_user_id") or ""), session=sess, document=doc):
            raise PermissionError("삭제 요청을 생성할 권한이 없습니다.")
        row = {
            "id": _new_id(),
            "document_id": document_id,
            "employee_id": doc.get("employee_id", ""),
            "employee_user_id": doc.get("employee_user_id", ""),
            "document_name": doc.get("document_name", ""),
            "requester_id": actor_id,
            "requester_name": actor_name,
            "reason": str(reason).strip(),
            "status": "대기",
            "requested_at": _now_iso(),
            "reviewed_by": "",
            "reviewed_at": "",
            "review_memo": "",
        }
        db.setdefault("delete_requests", []).append(row)
        doc["delete_requested_by"] = actor_id
        _audit(db, actor_id=actor_id, action="document_delete_requested", document_id=document_id, reason=row["reason"], details={"request_id": row["id"]}, session=sess)
        _notification(db, document=doc, ntype="hr_document_delete_requested", title="[문서관리] 삭제 요청", message=f"{doc.get('employee_name')} · {doc.get('document_name')} 삭제 요청", target_roles=("manager", "hr", "admin"), key=f"delete-request:{row['id']}")
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_delete_requests(*, tenant_id: str | None = None, status: str = "") -> list[dict[str, Any]]:
    rows = list(_db(tenant_id).get("delete_requests") or [])
    if status:
        rows = [r for r in rows if str(r.get("status") or "") == status]
    return rows


def approve_delete_request(
    request_id: str,
    *,
    memo: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("삭제 요청 승인은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        req = next((r for r in db.get("delete_requests") or [] if str(r.get("id")) == str(request_id)), None)
        if req is None:
            raise FileNotFoundError(request_id)
        if str(req.get("status") or "") != "대기":
            raise ValueError("이미 처리된 삭제 요청입니다.")
        doc_id = str(req.get("document_id") or "")
        doc = next((r for r in db.get("documents") or [] if str(r.get("id")) == doc_id), None)
        if doc is None:
            raise FileNotFoundError(doc_id)
        deleted_at = _now_iso()
        req.update({"status": "승인", "reviewed_by": actor_id, "reviewed_by_name": actor_name, "reviewed_at": deleted_at, "review_memo": memo})
        doc.update(
            {
                "deleted": True,
                "deleted_at": deleted_at,
                "deleted_by": str(req.get("requester_id") or ""),
                "delete_requested_by": str(req.get("requester_id") or ""),
                "delete_approved_by": actor_id,
                "delete_reason": str(req.get("reason") or ""),
                "recoverable_until": _restore_deadline(deleted_at, days=int((db.get("settings") or {}).get("restore_window_days") or DEFAULT_RESTORE_DAYS)),
                "restore_status": "복구 가능",
                "last_modified_by": actor_id,
                "last_modified_at": deleted_at,
            }
        )
        _audit(db, actor_id=actor_id, action="document_delete_approved", document_id=doc_id, reason=str(req.get("reason") or ""), details={"request_id": request_id, "recoverable_until": doc["recoverable_until"]}, session=sess)
        _notification(db, document=doc, ntype="hr_document_deleted", title="[문서관리] 삭제 요청 승인", message=f"{doc.get('employee_name')} · {doc.get('document_name')} 삭제 표시", target_roles=("employee", "hr", "admin"), key=f"delete-approved:{request_id}")
        return dict(req)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def reject_delete_request(
    request_id: str,
    *,
    reason: str,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("삭제 요청 반려는 HR 관리자 또는 최고관리자만 가능합니다.")
    if not str(reason or "").strip():
        raise ValueError("삭제 요청 반려 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        req = next((r for r in db.get("delete_requests") or [] if str(r.get("id")) == str(request_id)), None)
        if req is None:
            raise FileNotFoundError(request_id)
        req.update({"status": "반려", "reviewed_by": actor_id, "reviewed_by_name": actor_name, "reviewed_at": _now_iso(), "review_memo": str(reason).strip()})
        _audit(db, actor_id=actor_id, action="document_delete_rejected", document_id=str(req.get("document_id") or ""), reason=str(reason), details={"request_id": request_id}, session=sess)
        return dict(req)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def restore_document(
    document_id: str,
    *,
    reason: str,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 복구는 HR 관리자 또는 최고관리자만 가능합니다.")
    if not str(reason or "").strip():
        raise ValueError("복구 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id):
                continue
            if not row.get("deleted"):
                return _public_doc(row, mask_sensitive=False)
            deadline = _parse_date(str(row.get("recoverable_until") or ""))
            if deadline and deadline < date.today():
                raise ValueError("일반 복구 가능 기간(1개월)이 지났습니다. 백업/아카이브 접근 정책 검토가 필요합니다.")
            row["deleted"] = False
            row["restored_by"] = actor_id
            row["restored_by_name"] = actor_name
            row["restored_at"] = _now_iso()
            row["restore_reason"] = str(reason).strip()
            row["restore_status"] = "복구 완료"
            row["last_modified_by"] = actor_id
            row["last_modified_at"] = _now_iso()
            restore_req = {
                "id": _new_id(),
                "document_id": document_id,
                "restored_by": actor_id,
                "restored_by_name": actor_name,
                "reason": str(reason).strip(),
                "restored_at": row["restored_at"],
            }
            db.setdefault("restore_requests", []).append(restore_req)
            _audit(db, actor_id=actor_id, action="document_restored", document_id=document_id, reason=str(reason), details={"restore_id": restore_req["id"]}, session=sess)
            return _public_doc(row, mask_sensitive=False)
        raise FileNotFoundError(document_id)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def sync_expiration_statuses(*, tenant_id: str | None = None, as_of: date | None = None) -> int:
    tid = _tid(tenant_id)
    today = as_of or date.today()

    def mut(db: dict[str, Any]) -> int:
        changed = 0
        for row in db.get("documents") or []:
            if row.get("deleted") or not row.get("current", True):
                continue
            if row.get("status") in {STATUS_REVIEW_REQUIRED, STATUS_REJECTED, STATUS_RENEWED}:
                continue
            policy = _policy_for(str(row.get("document_type")), db)
            new_status = _status_for(str(row.get("expiry_date") or ""), policy, as_of=today)
            if new_status != row.get("status"):
                old = row.get("status")
                row["status"] = new_status
                row["last_modified_at"] = _now_iso()
                _audit(db, actor_id="system", action="document_status_changed", document_id=str(row.get("id")), details={"from": old, "to": new_status})
                changed += 1
            if new_status in {STATUS_EXPIRING, STATUS_EXPIRED}:
                days_left = ((_parse_date(str(row.get("expiry_date") or "")) or today) - today).days
                high_risk = str(policy.get("risk_grade") or "").casefold() in HIGH_RISK_GRADES or bool(policy.get("executive_report"))
                targets = list(policy.get("notify_roles") or ("employee", "hr"))
                if high_risk and (new_status == STATUS_EXPIRED or days_left <= 7):
                    for role in ("executive", "admin"):
                        if role not in targets:
                            targets.append(role)
                _notification(
                    db,
                    document=row,
                    ntype="hr_document_expiring" if new_status == STATUS_EXPIRING else "hr_document_expired",
                    title=f"[문서관리] {new_status} — {row.get('document_type_label')}",
                    message=f"{row.get('employee_name')} · {row.get('document_name')} · 만료일 {row.get('expiry_date') or '없음'} · {row.get('legal_risk_message') or DEFAULT_LEGAL_REVIEW_NOTICE if high_risk else ''}".strip(),
                    target_roles=targets,
                    channels=policy.get("notification_channels") or DEFAULT_NOTIFICATION_CHANNELS,
                    priority="high" if high_risk else "normal",
                    escalation_level=1 if high_risk and days_left <= 7 else 0,
                    key=f"expiry:{row.get('id')}:{new_status}:{today.isoformat()}",
                )
        return changed

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def generate_expiry_notifications(*, tenant_id: str | None = None, as_of: date | None = None) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    today = as_of or date.today()
    sync_expiration_statuses(tenant_id=tid, as_of=today)

    def mut(db: dict[str, Any]) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for row in db.get("documents") or []:
            if row.get("deleted") or not row.get("current", True):
                continue
            exp = _parse_date(str(row.get("expiry_date") or ""))
            if not exp:
                continue
            days_left = (exp - today).days
            policy = _policy_for(str(row.get("document_type")), db)
            reminders = {int(d) for d in (policy.get("reminder_days") or DEFAULT_REMINDER_DAYS)}
            if days_left in reminders or days_left < 0:
                high_risk = str(policy.get("risk_grade") or "").casefold() in HIGH_RISK_GRADES or bool(policy.get("executive_report"))
                targets = list(policy.get("notify_roles") or ("employee", "hr"))
                if high_risk and (days_left <= 7):
                    for role in ("executive", "admin"):
                        if role not in targets:
                            targets.append(role)
                n = _notification(
                    db,
                    document=row,
                    ntype="hr_document_renewal_due" if days_left >= 0 else "hr_document_expired",
                    title=f"[문서관리] 갱신 요청 — {row.get('document_type_label')}",
                    message=f"{row.get('employee_name')} · {row.get('document_name')} · 만료 {days_left}일 전" if days_left >= 0 else f"{row.get('employee_name')} · {row.get('document_name')} · 만료됨 · {DEFAULT_LEGAL_REVIEW_NOTICE if high_risk else ''}",
                    target_roles=targets,
                    channels=policy.get("notification_channels") or DEFAULT_NOTIFICATION_CHANNELS,
                    priority="high" if high_risk else "normal",
                    escalation_level=1 if high_risk and days_left <= 7 else 0,
                    key=f"renewal:{row.get('id')}:{days_left}",
                )
                if n:
                    created.append(n)
        return created

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_notifications(*, tenant_id: str | None = None, unread_only: bool = False) -> list[dict[str, Any]]:
    rows = list(_db(tenant_id).get("notifications") or [])
    if unread_only:
        rows = [r for r in rows if not r.get("read")]
    return rows


def acknowledge_notification(
    notification_id: str,
    *,
    action_note: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    tid = _tid(tenant_id)
    sess = session or get_session()
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for row in db.get("notifications") or []:
            if str(row.get("id")) != str(notification_id):
                continue
            row["read"] = True
            row["read_at"] = row.get("read_at") or _now_iso()
            row["acknowledged_at"] = _now_iso()
            row["acknowledged_by"] = actor_id
            row["status"] = "사용자 확인"
            row["action_note"] = str(action_note or "")
            if action_note:
                row["action_completed_at"] = _now_iso()
                row["status"] = "조치 완료"
            _audit(db, actor_id=actor_id, action="notification_acknowledged", document_id=str(row.get("document_id") or ""), details={"notification_id": notification_id, "action_note": action_note}, session=sess)
            return dict(row)
        raise FileNotFoundError(notification_id)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def escalate_unacknowledged_notifications(
    *,
    tenant_id: str | None = None,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    """Escalate unacknowledged HR document alerts to HR/executive targets."""

    tid = _tid(tenant_id)
    now = as_of or datetime.now()

    def mut(db: dict[str, Any]) -> list[dict[str, Any]]:
        changed: list[dict[str, Any]] = []
        for row in db.get("notifications") or []:
            if row.get("read") or row.get("acknowledged_at"):
                continue
            created = _parse_datetime(str(row.get("created_at") or ""))
            if not created:
                continue
            age_hours = (now - created).total_seconds() / 3600
            targets = list(row.get("target_roles") or [])
            old_level = int(row.get("escalation_level") or 0)
            new_level = old_level
            if age_hours >= 72:
                new_level = max(new_level, 2)
                for role in ("hr", "admin"):
                    if role not in targets:
                        targets.append(role)
                row["status"] = "조치 지연"
            elif age_hours >= 24:
                new_level = max(new_level, 1)
                row["status"] = "재발송 완료"
            if new_level != old_level:
                row["escalation_level"] = new_level
                row["target_roles"] = targets
                row.setdefault("send_results", []).append({"at": _now_iso(), "channel": "platform", "status": row["status"]})
                _audit(db, actor_id="system", action="notification_escalated", document_id=str(row.get("document_id") or ""), details={"notification_id": row.get("id"), "from": old_level, "to": new_level})
                changed.append(dict(row))
        return changed

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_audit_logs(*, tenant_id: str | None = None, document_id: str = "", session: UserSession | None = None) -> list[dict[str, Any]]:
    tid = _tid(tenant_id)
    if session is not None and not can_manage_employee_documents(session):
        raise PermissionError("감사로그 조회 권한이 없습니다.")
    if session is not None:
        actor_id, _actor_name, _role = _actor(session)

        def mut(db: dict[str, Any]) -> None:
            _audit(db, actor_id=actor_id, action="audit_log_viewed", details={"document_id": document_id}, session=session)

        mutate_module_db(MODULE, tid, _EMPTY, mut)
    rows = list(_db(tid).get("audit_logs") or [])
    if document_id:
        rows = [r for r in rows if str(r.get("document_id")) == str(document_id)]
    return rows


def record_ocr_result(
    document_id: str,
    *,
    extracted_values: dict[str, Any],
    confidence: float = 0.0,
    status: str = "검토 필요",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("OCR 결과 반영은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id) or row.get("deleted"):
                continue
            masked = {str(k): mask_text_value(str(v)) for k, v in dict(extracted_values or {}).items()}
            row["ocr_status"] = str(status or "검토 필요")
            row["ocr_processed_at"] = _now_iso()
            row["ocr_confidence"] = float(confidence or 0)
            row["ocr_extracted_values"] = dict(extracted_values or {})
            row["masking_preview"] = "\n".join(f"{k}: {v}" for k, v in masked.items())
            row["masking_review_required"] = True
            row["last_modified_by"] = actor_id
            row["last_modified_at"] = _now_iso()
            result = {
                "id": _new_id(),
                "document_id": document_id,
                "status": row["ocr_status"],
                "confidence": row["ocr_confidence"],
                "extracted_values": dict(extracted_values or {}),
                "masked_values": masked,
                "processed_at": row["ocr_processed_at"],
                "processed_by": actor_id,
            }
            db.setdefault("integration_logs", []).append({"id": _new_id(), "system": "ocr", "operation": "extract", "status": row["ocr_status"], "document_id": document_id, "created_at": _now_iso(), "payload": {"confidence": confidence}})
            _audit(db, actor_id=actor_id, action="ocr_processed", document_id=document_id, details={"status": row["ocr_status"], "confidence": confidence}, session=sess)
            return result
        raise FileNotFoundError(document_id)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def record_e_signature_event(
    values: dict[str, Any],
    *,
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("전자서명 연동 기록은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)
    document_id = str(values.get("document_id") or "")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": _new_id(),
            "document_id": document_id,
            "external_service": str(values.get("external_service") or values.get("provider") or "e-signature"),
            "external_document_id": str(values.get("external_document_id") or ""),
            "requester_id": str(values.get("requester_id") or actor_id),
            "signer_id": str(values.get("signer_id") or ""),
            "sent_at": str(values.get("sent_at") or _now_iso()),
            "completed_at": str(values.get("completed_at") or ""),
            "signature_status": str(values.get("signature_status") or values.get("status") or "requested"),
            "failure_reason": str(values.get("failure_reason") or ""),
            "auto_saved": bool(values.get("auto_saved", False)),
            "created_at": _now_iso(),
        }
        db.setdefault("electronic_signature_records", []).append(row)
        db.setdefault("integration_logs", []).append({"id": _new_id(), "system": "electronic_signature", "operation": row["signature_status"], "status": row["signature_status"], "document_id": document_id, "external_id": row["external_document_id"], "created_at": _now_iso(), "payload": dict(values)})
        _audit(db, actor_id=actor_id, action="electronic_signature_event_recorded", document_id=document_id, details={"external_document_id": row["external_document_id"], "status": row["signature_status"]}, session=sess)
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def record_external_integration_event(
    system: str,
    operation: str,
    *,
    status: str,
    document_id: str = "",
    external_id: str = "",
    payload: dict[str, Any] | None = None,
    failure_reason: str = "",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("외부 연동 기록은 HR 관리자 또는 최고관리자만 가능합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": _new_id(),
            "system": str(system or ""),
            "operation": str(operation or ""),
            "status": str(status or ""),
            "document_id": str(document_id or ""),
            "external_id": str(external_id or ""),
            "payload": dict(payload or {}),
            "failure_reason": str(failure_reason or ""),
            "created_at": _now_iso(),
            "created_by": actor_id,
        }
        db.setdefault("integration_logs", []).append(row)
        _audit(db, actor_id=actor_id, action="external_integration_event_recorded", document_id=str(document_id or ""), details={"system": system, "operation": operation, "status": status, "failure_reason": failure_reason}, session=sess)
        if failure_reason:
            doc = next((d for d in db.get("documents") or [] if str(d.get("id")) == str(document_id)), {})
            _notification(db, document=doc, ntype="hr_document_integration_failed", title="[문서관리] 외부 연동 실패", message=f"{system} · {operation} · {failure_reason}", target_roles=("hr", "admin"), key=f"integration-failed:{row['id']}")
        return dict(row)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_integration_logs(*, tenant_id: str | None = None, system: str = "") -> list[dict[str, Any]]:
    rows = list(_db(tenant_id).get("integration_logs") or [])
    if system:
        rows = [r for r in rows if str(r.get("system") or "") == system]
    return rows


def archive_document(
    document_id: str,
    *,
    reason: str,
    retention_status: str = "분리 보관",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or get_session()
    if not can_manage_employee_documents(sess):
        raise PermissionError("문서 보존/아카이브 변경은 HR 관리자 또는 최고관리자만 가능합니다.")
    if retention_status not in RETENTION_STATUSES:
        raise ValueError("지원하지 않는 보존 상태입니다.")
    if not str(reason or "").strip():
        raise ValueError("보존/아카이브 변경 사유가 필요합니다.")
    tid = _tid(tenant_id)
    actor_id, _actor_name, _role = _actor(sess)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for row in db.get("documents") or []:
            if str(row.get("id")) != str(document_id):
                continue
            row["retention_status"] = retention_status
            row["archived"] = retention_status in {"분리 보관", "백업 보관", "장기 보관", "보존 잠금"}
            row["download_restricted"] = retention_status in {"제공 제한", "다운로드 제한", "법무 검토 필요", "분리 보관", "백업 보관"}
            row["retention_changed_by"] = actor_id
            row["retention_changed_at"] = _now_iso()
            row["retention_change_reason"] = str(reason).strip()
            _audit(db, actor_id=actor_id, action="retention_policy_changed", document_id=document_id, reason=str(reason), details={"retention_status": retention_status, "download_restricted": row["download_restricted"]}, session=sess)
            return _public_doc(row, mask_sensitive=False)
        raise FileNotFoundError(document_id)

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def list_backup_records(*, tenant_id: str | None = None, session: UserSession | None = None) -> list[dict[str, Any]]:
    if session is not None and not can_manage_employee_documents(session):
        raise PermissionError("백업 보존 문서 조회는 HR 관리자 또는 최고관리자만 가능합니다.")
    rows = [dict(r) for r in _db(tenant_id).get("backup_records") or []]
    for row in rows:
        row.pop("storage_path", None)
    return rows


def dashboard_summary(*, tenant_id: str | None = None, employees: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    tid = _tid(tenant_id)
    sync_expiration_statuses(tenant_id=tid)
    db = _db(tid)
    docs = [d for d in db.get("documents") or [] if not d.get("deleted") and d.get("current", True)]
    employee_ids = {str(d.get("employee_id") or d.get("employee_name") or "") for d in docs if d.get("employee_id") or d.get("employee_name")}
    if employees:
        employee_ids.update(str(e.get("employee_id") or e.get("employee_no") or e.get("name") or e.get("employee_name") or "") for e in employees)
        employee_ids.discard("")
    required_types = [t for t in db.get("document_types") or [] if t.get("required") and t.get("active", True)]
    missing_required = 0
    missing_by_employee: dict[str, list[str]] = {}
    for emp in employee_ids:
        emp_docs = [d for d in docs if str(d.get("employee_id") or d.get("employee_name")) == emp]
        emp_types = {str(d.get("document_type")) for d in emp_docs}
        missing = [str(t.get("label") or t.get("type_id")) for t in required_types if str(t.get("type_id")) not in emp_types]
        if missing:
            missing_required += len(missing)
            missing_by_employee[emp] = missing
    by_dept: dict[str, int] = {}
    by_entity: dict[str, int] = {}
    by_type_expiry: dict[str, dict[str, int]] = {}
    high_risk_docs: list[dict[str, Any]] = []
    for d in docs:
        by_dept[str(d.get("department") or "(미지정)")] = by_dept.get(str(d.get("department") or "(미지정)"), 0) + 1
        by_entity[str(d.get("legal_entity") or "(미지정)")] = by_entity.get(str(d.get("legal_entity") or "(미지정)"), 0) + 1
        label = str(d.get("document_type_label") or d.get("document_type") or "")
        status = str(d.get("status") or "")
        by_type_expiry.setdefault(label, {})[status] = by_type_expiry.setdefault(label, {}).get(status, 0) + 1
        if str(d.get("risk_grade") or "").casefold() in HIGH_RISK_GRADES or d.get("executive_report") or d.get("legal_mandatory"):
            high_risk_docs.append(d)
    total_docs = len(docs)
    approved_docs = sum(1 for d in docs if d.get("approval_status") in {"승인완료", "승인불필요"})
    rejected_docs = sum(1 for d in docs if d.get("status") == STATUS_REJECTED)
    renewal_done = sum(1 for d in db.get("documents") or [] if d.get("status") == STATUS_RENEWED)
    download_count = sum(len(d.get("download_history") or []) for d in db.get("documents") or [])
    sensitive_view_count = sum(len(d.get("view_history") or []) for d in docs if d.get("sensitive") or d.get("contains_unique_id"))
    pending_permission_requests = sum(1 for r in db.get("permission_requests") or [] if r.get("status") == "대기")
    return {
        "total_employees": len(employee_ids),
        "total_documents": total_docs,
        "employees_without_documents": sum(1 for emp in employee_ids if not any(str(d.get("employee_id") or d.get("employee_name")) == emp for d in docs)),
        "missing_required_documents": missing_required,
        "missing_by_employee": missing_by_employee,
        "required_submission_rate": 0 if not required_types or not employee_ids else round(100 * (1 - (missing_required / max(1, len(required_types) * len(employee_ids)))), 1),
        "approval_rate": 0 if not total_docs else round(100 * approved_docs / total_docs, 1),
        "rejection_rate": 0 if not total_docs else round(100 * rejected_docs / total_docs, 1),
        "renewal_completion_rate": 0 if not (renewal_done + total_docs) else round(100 * renewal_done / (renewal_done + total_docs), 1),
        "expiring_documents": sum(1 for d in docs if d.get("status") == STATUS_EXPIRING),
        "expired_documents": sum(1 for d in docs if d.get("status") == STATUS_EXPIRED),
        "review_pending_documents": sum(1 for d in docs if d.get("status") == STATUS_REVIEW_REQUIRED),
        "rejected_documents": sum(1 for d in docs if d.get("status") == STATUS_REJECTED),
        "unacknowledged_notifications": sum(1 for n in db.get("notifications") or [] if not n.get("read")),
        "high_risk_documents": len(high_risk_docs),
        "executive_report_documents": sum(1 for d in docs if d.get("executive_report")),
        "download_count": download_count,
        "sensitive_view_count": sensitive_view_count,
        "permission_request_count": len(db.get("permission_requests") or []),
        "pending_permission_requests": pending_permission_requests,
        "deleted_documents": sum(1 for d in db.get("documents") or [] if d.get("deleted")),
        "backup_records": len(db.get("backup_records") or []),
        "department_submission_counts": by_dept,
        "legal_entity_submission_counts": by_entity,
        "document_type_status_counts": by_type_expiry,
        "risk_documents": [_public_doc(d) for d in high_risk_docs],
        "renewal_required_documents": [
            _public_doc(d) for d in docs if d.get("status") in {STATUS_EXPIRING, STATUS_EXPIRED, STATUS_REVIEW_REQUIRED, STATUS_REJECTED}
        ],
        "legal_review_notice": DEFAULT_LEGAL_REVIEW_NOTICE,
    }


# ModuleHub-compatible functions ------------------------------------------------


def dashboard_kpis() -> list[tuple[str, str, str]]:
    s = dashboard_summary()
    return [
        ("직원/문서", f"{s['total_employees']}/{s['total_documents']}", f"미제출 {s['employees_without_documents']}명"),
        ("필수 누락", str(s["missing_required_documents"]), f"제출률 {s['required_submission_rate']}%"),
        ("만료 예정", str(s["expiring_documents"]), f"만료 {s['expired_documents']}건"),
        ("리스크", str(s["high_risk_documents"]), f"검토 {s['review_pending_documents']} · 반려 {s['rejected_documents']}"),
    ]


def list_records(tab_id: str) -> list[dict[str, Any]]:
    if tab_id == "document_types":
        return list_document_types(active_only=False)
    if tab_id == "document_alerts":
        generate_expiry_notifications()
        return list_notifications()
    if tab_id == "permission_requests":
        return list_permission_requests()
    if tab_id == "delete_restore":
        rows = list_delete_requests()
        restored = _db().get("restore_requests") or []
        return rows + [{**r, "status": "복구 완료", "requester_name": r.get("restored_by_name", ""), "requested_at": r.get("restored_at", "")} for r in restored]
    if tab_id == "document_audit":
        return list_audit_logs()
    return list_employee_documents()


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    if tab_id == "document_types":
        return (
            ("type_id", "유형ID", 120),
            ("label", "문서 유형", 150),
            ("required", "필수", 50),
            ("expiry_required", "만료필수", 70),
            ("default_validity_days", "기본일수", 70),
            ("approval_required", "승인", 50),
            ("employee_upload_allowed", "직원업로드", 80),
            ("payroll_related", "급여", 50),
            ("sensitive", "민감", 50),
        )
    if tab_id == "document_alerts":
        return (
            ("created_at", "생성", 130),
            ("type", "알림유형", 140),
            ("title", "제목", 180),
            ("employee_id", "직원ID", 90),
            ("target_roles", "대상", 120),
            ("channels", "채널", 120),
            ("status", "상태", 90),
            ("escalation_level", "단계", 50),
            ("message", "메시지", 260),
        )
    if tab_id == "permission_requests":
        return (
            ("requested_at", "요청일", 130),
            ("requester_name", "요청자", 90),
            ("employee_id", "직원ID", 90),
            ("document_id", "문서ID", 110),
            ("scopes", "범위", 150),
            ("status", "상태", 70),
            ("expires_at", "만료", 130),
            ("reason", "사유", 240),
        )
    if tab_id == "delete_restore":
        return (
            ("requested_at", "요청/복구일", 130),
            ("requester_name", "요청자", 90),
            ("document_id", "문서ID", 110),
            ("document_name", "문서명", 150),
            ("status", "상태", 70),
            ("reason", "사유", 240),
            ("reviewed_by_name", "승인자", 90),
        )
    if tab_id == "document_audit":
        return (
            ("occurred_at", "일시", 130),
            ("actor_id", "사용자", 120),
            ("action", "행위", 150),
            ("document_id", "문서ID", 110),
            ("details", "상세", 260),
        )
    return (
        ("employee_id", "직원ID", 80),
        ("employee_name", "성명", 80),
        ("department", "부서", 90),
        ("position", "직책", 70),
        ("document_type_label", "문서유형", 130),
        ("document_name", "문서명", 150),
        ("display_file_name", "파일", 140),
        ("uploaded_at", "업로드", 130),
        ("expiry_date", "만료일", 90),
        ("status", "상태", 80),
        ("version", "Ver", 45),
    )


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    if tab_id == "document_types":
        return (
            ("type_id", "문서유형 ID", False),
            ("label", "문서 유형명", True),
            ("required", "필수 여부(true/false)", False),
            ("expiry_required", "만료일 필수(true/false)", False),
            ("default_validity_days", "기본 유효기간(일)", False),
            ("employee_upload_allowed", "직원 업로드 허용(true/false)", False),
        )
    if tab_id in {"document_alerts", "document_audit", "permission_requests", "delete_restore"}:
        return (("note", "읽기 전용 탭입니다", False),)
    return (
        ("employee_id", "직원 ID/사번", True),
        ("employee_name", "직원명", True),
        ("employee_user_id", "직원 사용자ID", False),
        ("employee_no", "사번", False),
        ("legal_entity", "법인", False),
        ("workplace", "사업장/근무지", False),
        ("department", "부서", False),
        ("position", "직책", False),
        ("employment_type", "고용형태", False),
        ("employment_status", "재직상태", False),
        ("document_type", "문서 유형 ID", True),
        ("document_name", "문서명", False),
        ("source_path", "업로드 파일 경로", True),
        ("issued_date", "발급일(YYYY-MM-DD)", False),
        ("start_date", "시작일(YYYY-MM-DD)", False),
        ("expiry_date", "만료일(YYYY-MM-DD)", False),
        ("memo", "관리자 메모", False),
    )


def _boolish(value: Any) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "예", "네", "필수", "허용"}


def add_record(tab_id: str, values: dict[str, str]) -> dict[str, Any]:
    if tab_id == "document_types":
        vals: dict[str, Any] = dict(values)
        for key in ("required", "expiry_required", "employee_upload_allowed"):
            if key in vals:
                vals[key] = _boolish(vals[key])
        if vals.get("default_validity_days"):
            vals["default_validity_days"] = int(vals["default_validity_days"])
        return save_document_type(vals)
    if tab_id in {"document_alerts", "document_audit"}:
        raise ValueError("읽기 전용 탭입니다.")
    return upload_document(
        employee_id=values.get("employee_id", ""),
        employee_name=values.get("employee_name", ""),
        employee_user_id=values.get("employee_user_id", ""),
        employee_no=values.get("employee_no", ""),
        legal_entity=values.get("legal_entity", ""),
        workplace=values.get("workplace", ""),
        department=values.get("department", ""),
        position=values.get("position", ""),
        employment_type=values.get("employment_type", ""),
        employment_status=values.get("employment_status", "재직"),
        document_type=values.get("document_type", ""),
        document_name=values.get("document_name", ""),
        source_path=values.get("source_path", ""),
        issued_date=values.get("issued_date", ""),
        start_date=values.get("start_date", ""),
        expiry_date=values.get("expiry_date", ""),
        memo=values.get("memo", ""),
    )


# Backward-compatible certificate/self-service API names ------------------------


def create_document_request(**kwargs: Any) -> dict[str, Any]:
    return upload_document(**kwargs)


def list_document_requests(*, tenant_id: str | None = None) -> list[dict[str, Any]]:
    return list_employee_documents(tenant_id=tenant_id, filters={"status": STATUS_REVIEW_REQUIRED})


def approve_request(request_id: str, *, memo: str = "", tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    return approve_document(request_id, memo=memo, tenant_id=tenant_id, session=session)


def reject_request(request_id: str, *, reason: str, tenant_id: str | None = None, session: UserSession | None = None) -> dict[str, Any] | None:
    return reject_document(request_id, reason=reason, tenant_id=tenant_id, session=session)


def list_payroll_periods_for_ui() -> list[str]:
    try:
        from payroll_archive import list_payroll_periods

        return list(list_payroll_periods())
    except Exception:
        return []


def list_roster_employees() -> list[dict[str, Any]]:
    try:
        from services.employee_roster_store import load_roster_rows_secured

        rows = load_roster_rows_secured()
        return [dict(r) for r in rows]
    except Exception:
        return []


def generate_document(doc_type: str, context: dict[str, Any] | None = None) -> str:
    return preview_document_html(doc_type, context or {})


def preview_document_html(doc_type: str, context: dict[str, Any] | None = None) -> str:
    ctx = context or {}
    label = document_type_label(doc_type)
    rows = document_field_requirements(doc_type)
    if not rows:
        rows = [(k, k) for k in sorted(ctx)]
    body = "".join(
        f"<tr><th>{html.escape(label_ko)}</th><td>{html.escape(str(ctx.get(key, '')))}</td></tr>"
        for key, label_ko in rows
    )
    return f"<html><body><h1>{html.escape(label)}</h1><table>{body}</table></body></html>"


def save_document_html(html_text: str, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(str(html_text), encoding="utf-8")
    return out


def batch_export_documents(
    document_ids: Iterable[str],
    *,
    reason: str = "HR 문서 일괄 내보내기",
    tenant_id: str | None = None,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    exported = []
    ids = [str(doc_id) for doc_id in document_ids]
    if len(ids) > 10 and not can_manage_employee_documents(session):
        raise PermissionError("대량 다운로드는 HR 관리자 또는 최고관리자 권한이 필요합니다.")
    for doc_id in ids:
        payload, meta = download_document(str(doc_id), reason=reason, tenant_id=tenant_id, session=session)
        exported.append({"document_id": doc_id, "file_name": meta.get("file_name"), "bytes": len(payload)})
    return exported


# Preserve old type-info helper but include managed upload types as well.
def list_generated_document_types() -> list[dict[str, Any]]:
    return list_document_type_info()
