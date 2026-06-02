"""
senior_internship.py - 시니어 인턴십(만 60세) 명부 표시·상태

보건복지부·한국노인인력개발원 「시니어인턴십(현장실습훈련)」 참여 제외 직종(단순노무) 반영:
경비·미화·청소·요양보호·간병·방문판매·조경·가사도우미 등 (수행기관 공고·안내 기준)

표시: 만 60세 이상 + 지원 가능 직종만 O / △ / X
      단순노무 해당 시 「제외」
"""

from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any

from annual_leave_accrual import parse_hire_date
from utils import is_senior_60_plus_roster_record

STATUS_IN_PROGRESS = "진행중"
STATUS_COMPLETED = "완료"

_MARK_O = "O"
_MARK_X = "X"
_MARK_PROGRESS = "△"
_MARK_JOB_EXCLUDED = "제외"

_DATE_PLACEHOLDER = "0000.00.00"

FILTER_SENIOR_ALL = "전체"
FILTER_SENIOR_ELIGIBLE = "시니어 지원가능"
FILTER_SENIOR_EXCLUDED = "시니어 제외(단순노무)"
FILTER_SENIOR_AGE_60 = "만60세 이상"

SENIOR_FILTER_CHOICES: tuple[str, ...] = (
    FILTER_SENIOR_ALL,
    FILTER_SENIOR_ELIGIBLE,
    FILTER_SENIOR_EXCLUDED,
    FILTER_SENIOR_AGE_60,
)

# 단순노무·지원 제외 직종 키워드 (공고문·수행기관 안내 종합)
_EXCLUDED_JOB_KEYWORDS: tuple[str, ...] = (
    "경비",
    "경호",
    "청소",
    "미화",
    "청소관리",
    "시설관리",
    "조경",
    "요양보호",
    "요양",
    "간병",
    "방문판매",
    "이동판매",
    "노점",
    "온라인판매",
    "온라인 판매",
    "가사도우미",
    "가사",
    "도우미",
    "대리운전",
    "판매원",
    "환경미화",
    "환경관리",
)

_EXCLUSION_LEGAL_NOTE = (
    "시니어인턴십(현장실습훈련): 경비·미화·청소·요양보호·간병·방문판매·조경 등 "
    "단순노무 직종은 참여 제외(보건복지부·한국노인인력개발원 사업안내)"
)


def senior_internship_help_text() -> str:
    return (
        f"{_EXCLUSION_LEGAL_NOTE}\n"
        "· O: 지원 가능  ·  △: 진행중  ·  X: 지원 완료  ·  제외: 만60세이나 단순노무 직종"
    )


def _norm_job_text(value: Any) -> str:
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value).strip())
    for ch in (" ", "\u00a0", "\u3000", "\t", "\n", "/", "·", "-"):
        s = s.replace(ch, "")
    return s.lower()


def job_description_text(rec: dict[str, Any]) -> str:
    """명부·청구서 직무 텍스트 통합."""
    parts: list[str] = []
    for key in ("업무", "직책", "비고", "dept", "소속"):
        val = rec.get(key)
        if val is not None and str(val).strip():
            parts.append(str(val).strip())
    return " / ".join(parts)


def classify_senior_internship_job(rec: dict[str, Any]) -> tuple[bool, str]:
    """
    단순노무(시니어인턴십 제외) 여부.

    Returns:
        (제외여부, 사유 라벨)
    """
    raw = job_description_text(rec)
    compact = _norm_job_text(raw)
    if not compact:
        return False, ""

    for kw in _EXCLUDED_JOB_KEYWORDS:
        nkw = _norm_job_text(kw)
        if nkw and nkw in compact:
            label = kw
            if kw == "요양" and "요양보호" in compact:
                label = "요양보호"
            return True, label

    return False, ""


def is_senior_internship_program_eligible(
    rec: dict[str, Any],
    *,
    as_of: date | None = None,
) -> bool:
    """만 60세 이상이면서 단순노무 제외 직종이 아닌 경우만 시니어인턴십 지원 대상."""
    if not is_senior_60_plus_roster_record(rec, as_of=as_of):
        return False
    excluded, _reason = classify_senior_internship_job(rec)
    return not excluded


def normalize_senior_internship_status(value: Any) -> str:
    """내부 상태: '' | 진행중 | 완료."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in ("X", "×") or text in ("완료", "지원완료", "종료", "이력"):
        return STATUS_COMPLETED
    if upper in ("△", "▲", "△.") or text in ("진행중", "진행", "지원중"):
        return STATUS_IN_PROGRESS
    if upper in ("O", "○") or text in ("가능", "대상", "미지원"):
        return ""
    if text in ("제외", "지원불가", "불가"):
        return ""
    return text


def status_from_mark_input(mark: str) -> str:
    """UI 입력 O / X / △ → 저장용 상태."""
    text = str(mark or "").strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in ("O", "○"):
        return ""
    if upper in ("X", "×"):
        return STATUS_COMPLETED
    if upper in ("△", "▲"):
        return STATUS_IN_PROGRESS
    if text == "제외":
        return ""
    return normalize_senior_internship_status(text)


def format_roster_date(value: Any) -> str:
    """명부·화면용 YYYY.MM.DD."""
    d = parse_hire_date(value)
    if d is None:
        if value is None or str(value).strip() == "":
            return _DATE_PLACEHOLDER
        return str(value).strip()
    return f"{d.year:04d}.{d.month:02d}.{d.day:02d}"


def parse_roster_date_input(text: str) -> str | None:
    """입력 → YYYY.MM.DD 문자열. 빈 값·플레이스홀더는 None."""
    t = str(text or "").strip()
    if not t or t.replace(".", "") == "00000000" or t == _DATE_PLACEHOLDER:
        return None
    d = parse_hire_date(t)
    if d is None:
        return None
    return f"{d.year:04d}.{d.month:02d}.{d.day:02d}"


def senior_internship_mark(rec: dict[str, Any], *, as_of: date | None = None) -> str:
    if not is_senior_60_plus_roster_record(rec, as_of=as_of):
        return ""
    excluded, reason = classify_senior_internship_job(rec)
    if excluded:
        return _MARK_JOB_EXCLUDED
    status = normalize_senior_internship_status(rec.get("시니어인턴십상태"))
    if status == STATUS_COMPLETED:
        return _MARK_X
    if status == STATUS_IN_PROGRESS:
        return _MARK_PROGRESS
    return _MARK_O


def senior_internship_period_text(rec: dict[str, Any], *, as_of: date | None = None) -> str:
    if not is_senior_60_plus_roster_record(rec, as_of=as_of):
        return ""
    excluded, reason = classify_senior_internship_job(rec)
    if excluded:
        job = job_description_text(rec) or reason
        return f"단순노무 지원불가 ({reason or job})"
    start = format_roster_date(rec.get("시니어인턴십지원일"))
    end = format_roster_date(rec.get("시니어인턴십재직충족일"))
    return f"지원일자 {start} ~ 재직충족 기간 {end}"


def apply_senior_internship_display(rec: dict[str, Any], *, as_of: date | None = None) -> None:
    excluded, reason = classify_senior_internship_job(rec)
    rec["_senior_job_excluded"] = excluded
    rec["_senior_job_exclusion_reason"] = reason
    rec["_senior_program_eligible"] = is_senior_internship_program_eligible(rec, as_of=as_of)
    rec["_senior_internship_mark"] = senior_internship_mark(rec, as_of=as_of)
    rec["_senior_internship_period"] = senior_internship_period_text(rec, as_of=as_of)


def record_matches_senior_filter(
    rec: dict[str, Any],
    senior_filter: str,
    *,
    as_of: date | None = None,
) -> bool:
    apply_senior_internship_display(rec, as_of=as_of)
    filt = str(senior_filter or FILTER_SENIOR_ALL).strip()
    if filt == FILTER_SENIOR_ALL:
        return True

    age60 = is_senior_60_plus_roster_record(rec, as_of=as_of)
    excluded = bool(rec.get("_senior_job_excluded"))
    eligible = bool(rec.get("_senior_program_eligible"))

    if filt == FILTER_SENIOR_AGE_60:
        return age60
    if filt == FILTER_SENIOR_EXCLUDED:
        return age60 and excluded
    if filt == FILTER_SENIOR_ELIGIBLE:
        return eligible
    return True


def count_senior_internship_stats(
    rows: list[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> dict[str, int]:
    age_60 = job_excluded = program_eligible = in_progress = completed = 0
    for rec in rows:
        apply_senior_internship_display(rec, as_of=as_of)
        if not is_senior_60_plus_roster_record(rec, as_of=as_of):
            continue
        age_60 += 1
        if rec.get("_senior_job_excluded"):
            job_excluded += 1
            continue
        program_eligible += 1
        st = normalize_senior_internship_status(rec.get("시니어인턴십상태"))
        if st == STATUS_IN_PROGRESS:
            in_progress += 1
        elif st == STATUS_COMPLETED:
            completed += 1
    return {
        "age_60_plus": age_60,
        "job_excluded": job_excluded,
        "program_eligible": program_eligible,
        "in_progress": in_progress,
        "completed": completed,
        "can_apply": max(0, program_eligible - in_progress - completed),
        # 하위 호환
        "eligible": program_eligible,
    }
