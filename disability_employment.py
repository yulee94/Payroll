"""
disability_employment.py - 장애인 고용(의무고용) 명부 표시·집계

법인(계열사)별 장애인 보유 인원 파악용.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DISABILITY_YES = "예"
DISABILITY_NO = "아니오"

FILTER_DISABILITY_ALL = "전체"
FILTER_DISABILITY_YES = "장애인"
FILTER_DISABILITY_NO = "비장애인"
FILTER_DISABILITY_UNSET = "미입력"

DISABILITY_FILTER_CHOICES: tuple[str, ...] = (
    FILTER_DISABILITY_ALL,
    FILTER_DISABILITY_YES,
    FILTER_DISABILITY_NO,
    FILTER_DISABILITY_UNSET,
)

AFFILIATE_UNSET_LABEL = "(미지정)"


def normalize_disability_flag(value: Any) -> str:
    """장애인 유무 → '' | 예 | 아니오."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    compact = text.replace(" ", "").upper()
    if compact in (
        "Y",
        "YES",
        "O",
        "○",
        "1",
        "TRUE",
        "예",
        "해당",
        "장애인",
        "장애해당",
        "장애해당자",
        "장애근로자",
    ):
        return DISABILITY_YES
    if compact in (
        "N",
        "NO",
        "X",
        "×",
        "-",
        "0",
        "FALSE",
        "아니오",
        "아니요",
        "무",
        "해당없음",
        "비장애",
        "비장애인",
        "일반",
    ) or compact.startswith("비장애"):
        return DISABILITY_NO
    if text in (DISABILITY_YES, DISABILITY_NO):
        return text
    return text


def normalize_disability_grade(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    compact = text.replace(" ", "")
    if compact in ("중증", "중증장애", "중증장애인"):
        return "중증"
    if compact in ("경증", "경증장애", "경증장애인"):
        return "경증"
    return text


def apply_disability_to_record(rec: dict[str, Any]) -> None:
    raw = rec.get("장애인")
    if raw is not None and str(raw).strip():
        rec["장애인"] = normalize_disability_flag(raw)
    grade = rec.get("장애등급")
    if grade is not None and str(grade).strip():
        rec["장애등급"] = normalize_disability_grade(grade)


def is_disabled_employee(rec: dict[str, Any]) -> bool:
    apply_disability_to_record(rec)
    return normalize_disability_flag(rec.get("장애인")) == DISABILITY_YES


def disability_flag_display(rec: dict[str, Any]) -> str:
    apply_disability_to_record(rec)
    return normalize_disability_flag(rec.get("장애인"))


def affiliate_key(rec: dict[str, Any]) -> str:
    aff = str(rec.get("계열사") or "").strip()
    return aff or AFFILIATE_UNSET_LABEL


def record_matches_disability_filter(rec: dict[str, Any], disability_filter: str) -> bool:
    filt = str(disability_filter or FILTER_DISABILITY_ALL).strip()
    if filt == FILTER_DISABILITY_ALL:
        return True
    flag = disability_flag_display(rec)
    if filt == FILTER_DISABILITY_UNSET:
        return not flag
    if filt == FILTER_DISABILITY_YES:
        return flag == DISABILITY_YES
    if filt == FILTER_DISABILITY_NO:
        return flag == DISABILITY_NO
    return True


@dataclass(frozen=True)
class AffiliateDisabilityStats:
    affiliate: str
    total: int
    disabled: int
    not_disabled: int
    unset: int

    @property
    def rate_pct(self) -> float:
        if self.total <= 0:
            return 0.0
        return 100.0 * self.disabled / self.total


def count_disability_by_affiliate(rows: list[dict[str, Any]]) -> list[AffiliateDisabilityStats]:
    buckets: dict[str, dict[str, int]] = {}
    for rec in rows:
        apply_disability_to_record(rec)
        key = affiliate_key(rec)
        if key not in buckets:
            buckets[key] = {"total": 0, "disabled": 0, "not_disabled": 0, "unset": 0}
        buckets[key]["total"] += 1
        flag = disability_flag_display(rec)
        if flag == DISABILITY_YES:
            buckets[key]["disabled"] += 1
        elif flag == DISABILITY_NO:
            buckets[key]["not_disabled"] += 1
        else:
            buckets[key]["unset"] += 1

    out: list[AffiliateDisabilityStats] = []
    for aff in sorted(buckets.keys(), key=lambda k: (k == AFFILIATE_UNSET_LABEL, k)):
        b = buckets[aff]
        out.append(
            AffiliateDisabilityStats(
                affiliate=aff,
                total=b["total"],
                disabled=b["disabled"],
                not_disabled=b["not_disabled"],
                unset=b["unset"],
            )
        )
    return out


def count_disability_totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    disabled = not_disabled = unset = 0
    for rec in rows:
        apply_disability_to_record(rec)
        flag = disability_flag_display(rec)
        if flag == DISABILITY_YES:
            disabled += 1
        elif flag == DISABILITY_NO:
            not_disabled += 1
        else:
            unset += 1
    return {
        "total": len(rows),
        "disabled": disabled,
        "not_disabled": not_disabled,
        "unset": unset,
    }


def format_affiliate_disability_summary(rows: list[dict[str, Any]], *, max_parts: int = 6) -> str:
    """한 줄 요약: 계열사별 장애인/재직."""
    totals = count_disability_totals(rows)
    if totals["total"] == 0:
        return "장애인 고용: 등록 인원 없음"
    parts = [f"장애인 {totals['disabled']}명 / 재직 {totals['total']}명"]
    by_aff = count_disability_by_affiliate(rows)
    aff_bits: list[str] = []
    for st in by_aff:
        if st.total <= 0:
            continue
        aff_bits.append(f"{st.affiliate} {st.disabled}/{st.total}")
    if aff_bits:
        shown = aff_bits[:max_parts]
        suffix = f" 외 {len(aff_bits) - max_parts}개" if len(aff_bits) > max_parts else ""
        parts.append("· " + "  ·  ".join(shown) + suffix)
    if totals["unset"]:
        parts.append(f"(미입력 {totals['unset']}명)")
    return "  ".join(parts)
