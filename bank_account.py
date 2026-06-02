"""
bank_account.py - 급여 지급 계좌(예금주·계좌번호·은행) 명부 필드
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from roster_constants import norm_name_key

# 금융기관 코드 → 은행명 (지급내역 양식·이체 파일용)
BANK_CODE_TO_NAME: dict[str, str] = {
    "002": "산업은행",
    "003": "기업은행",
    "004": "국민은행",
    "007": "수협은행",
    "011": "농협은행",
    "012": "농협회원조합",
    "020": "우리은행",
    "023": "SC제일은행",
    "027": "한국씨티은행",
    "031": "대구은행",
    "032": "부산은행",
    "034": "광주은행",
    "035": "제주은행",
    "037": "전북은행",
    "039": "경남은행",
    "045": "새마을금고",
    "048": "신협",
    "050": "저축은행",
    "064": "산림조합",
    "071": "우체국",
    "081": "하나은행",
    "088": "신한은행",
    "089": "케이뱅크",
    "090": "카카오뱅크",
    "092": "토스뱅크",
}

_ACCOUNT_SPLIT_RE = re.compile(
    r"^([가-힣A-Za-z][가-힣A-Za-z0-9\s]*?)\s*[/｜|]\s*(.+)$"
)
_ACCOUNT_PREFIX_RE = re.compile(r"^([가-힣A-Za-z][가-힣A-Za-z0-9]*?)\s+(\d[\d\-]+.*)$")


def normalize_account_number(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace(" ", "")
    if not text:
        return ""
    return text


def normalize_holder_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_third_party_holder(employee_name: Any, holder_name: Any) -> bool:
    """예금주가 근로자 성명과 다르면 True (가족 명의 등)."""
    emp = normalize_holder_name(employee_name).replace(" ", "")
    holder = normalize_holder_name(holder_name).replace(" ", "")
    if not holder or not emp:
        return False
    return holder != emp


def bank_name_from_code(code: Any) -> str:
    text = str(code or "").strip()
    if not text:
        return ""
    key = text.zfill(3) if text.isdigit() else text
    return BANK_CODE_TO_NAME.get(key, BANK_CODE_TO_NAME.get(text.zfill(3), ""))


def parse_bank_and_account_from_text(value: Any) -> tuple[str, str]:
    """
    '국민은행 123-456' / '국민|123-456' / '123-456' 형태 분리.
    Returns (bank_name, account_number).
    """
    if value is None:
        return "", ""
    text = str(value).strip()
    if not text:
        return "", ""

    for pattern in (_ACCOUNT_SPLIT_RE, _ACCOUNT_PREFIX_RE):
        m = pattern.match(text)
        if m:
            bank = m.group(1).strip()
            acct = normalize_account_number(m.group(2))
            if bank and acct:
                return bank, acct

    if re.search(r"[^\d\-]", text) and re.search(r"\d", text):
        parts = text.split(None, 1)
        if len(parts) == 2 and re.search(r"\d", parts[1]):
            return parts[0].strip(), normalize_account_number(parts[1])

    return "", normalize_account_number(text)


def format_bank_account_display(rec: dict[str, Any]) -> str:
    """명부 표시용 — 은행명 + 계좌번호."""
    bank = str(rec.get("은행명") or "").strip()
    acct = normalize_account_number(rec.get("계좌번호") or rec.get("계좌"))
    if bank and acct:
        return f"{bank}  {acct}"
    if bank:
        return bank
    return acct


def apply_bank_account_to_record(rec: dict[str, Any]) -> None:
    """레거시 `계좌` ↔ `계좌번호` 동기화, 은행·예금주 보정."""
    bank = str(rec.get("은행명") or "").strip()
    acct_no = normalize_account_number(rec.get("계좌번호"))
    legacy_raw = rec.get("계좌")
    legacy = normalize_account_number(legacy_raw)

    if not bank or (not acct_no and legacy):
        parsed_bank, parsed_acct = parse_bank_and_account_from_text(legacy_raw)
        if parsed_bank and not bank:
            bank = parsed_bank
        if parsed_acct:
            if not acct_no:
                acct_no = parsed_acct
            elif not bank and parsed_bank:
                bank = parsed_bank

    if not acct_no and legacy:
        acct_no = legacy

    if not bank:
        bank = bank_name_from_code(rec.get("은행코드"))

    if acct_no:
        rec["계좌번호"] = acct_no
        rec["계좌"] = acct_no
    if bank:
        rec["은행명"] = bank
    holder = normalize_holder_name(rec.get("예금주"))
    if not holder:
        holder = normalize_holder_name(rec.get("성명"))
    if holder:
        rec["예금주"] = holder
    rec["_bank_account_display"] = format_bank_account_display(rec)
    rec["_pay_account_third_party"] = is_third_party_holder(rec.get("성명"), holder)


@lru_cache(maxsize=1)
def _load_payment_master_by_name() -> dict[str, dict[str, Any]]:
    try:
        from payroll_builder import TEMPLATES_DIR, load_payment_master
    except ImportError:
        return {}
    path = TEMPLATES_DIR / "지급내역양식.xlsx"
    if not path.is_file():
        return {}
    master = load_payment_master(path)
    by_name: dict[str, dict[str, Any]] = {}
    for key, info in master.items():
        if not isinstance(info, dict):
            continue
        by_name[key] = info
        display = str(info.get("name") or "").strip()
        if display:
            by_name[norm_name_key(display)] = info
    return by_name


def merge_payment_master_bank(rec: dict[str, Any], pay_info: dict[str, Any]) -> None:
    if not pay_info:
        return
    if not str(rec.get("은행명") or "").strip():
        bank = str(pay_info.get("bank_name") or "").strip()
        if not bank:
            bank = bank_name_from_code(pay_info.get("bank_code"))
        if bank:
            rec["은행명"] = bank
    if not str(rec.get("은행코드") or "").strip() and pay_info.get("bank_code"):
        rec["은행코드"] = str(pay_info.get("bank_code")).strip()
    if not normalize_account_number(rec.get("계좌번호")):
        acct = normalize_account_number(pay_info.get("account"))
        if acct:
            rec["계좌번호"] = acct
            rec["계좌"] = acct
    if not normalize_holder_name(rec.get("예금주")):
        holder = normalize_holder_name(pay_info.get("holder"))
        if holder:
            rec["예금주"] = holder


def enrich_roster_bank_info(rows: list[dict[str, Any]]) -> None:
    """명부 로드 시 은행명·계좌 보강 (지급내역 양식·계좌 문자열 파싱)."""
    master = _load_payment_master_by_name()
    for rec in rows:
        name_key = norm_name_key(rec.get("성명"))
        pay_info = master.get(name_key, {}) if name_key else {}
        apply_bank_account_to_record(rec)
        if pay_info:
            merge_payment_master_bank(rec, pay_info)
        apply_bank_account_to_record(rec)


def resolve_payment_from_roster(
    emp_roster: dict[str, Any] | None,
    pay_info: dict[str, Any],
    *,
    employee_name: str = "",
) -> dict[str, str]:
    """
    지급내역용 계좌 정보 — 명부 우선, 없으면 지급내역 양식 마스터.
    """
    roster = emp_roster or {}
    apply_bank_account_to_record(roster)

    name = employee_name or str(roster.get("성명") or pay_info.get("name") or "").strip()
    account = normalize_account_number(roster.get("계좌번호")) or normalize_account_number(
        roster.get("계좌")
    )
    if not account:
        account = normalize_account_number(pay_info.get("account"))

    holder = normalize_holder_name(roster.get("예금주"))
    if not holder:
        holder = normalize_holder_name(pay_info.get("holder"))
    if not holder:
        holder = name

    bank_name = str(roster.get("은행명") or pay_info.get("bank_name") or "").strip()
    bank_code = str(roster.get("은행코드") or pay_info.get("bank_code") or "").strip()

    return {
        "account": account,
        "holder": holder,
        "bank_name": bank_name,
        "bank_code": bank_code,
    }


def save_bank_account_fields(
    rec: dict[str, Any],
    *,
    holder: str,
    account_no: str,
    bank_name: str = "",
    bank_code: str = "",
) -> None:
    rec["예금주"] = normalize_holder_name(holder) or None
    acct = normalize_account_number(account_no)
    rec["계좌번호"] = acct or None
    rec["계좌"] = acct or None
    rec["은행명"] = str(bank_name or "").strip() or None
    rec["은행코드"] = str(bank_code or "").strip() or None
    apply_bank_account_to_record(rec)
