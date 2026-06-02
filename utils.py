"""
공통 유틸리티 함수 모음.
엑셀 셀 값 변환, 병합 셀 안전 기록, 고용보험 계산 등
프로그램 전역에서 재사용합니다.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Optional

SENIOR_AGE_YEARS = 60

from openpyxl.cell.cell import MergedCell
from openpyxl.worksheet.worksheet import Worksheet

# 근로기준법상 월 소정근로시간 (주 40시간 × 52주 ÷ 12개월 ≈ 209)
STANDARD_MONTHLY_HOURS = 209

# 식대 단가 (원/일)
MEAL_ALLOWANCE_PER_DAY = 5500


def safe_number(value: Any, default: float = 0.0) -> float:
    """
    콤마·문자열·숫자 등 다양한 형태의 값을 float로 안전하게 변환합니다.

    예) "1,234,567" → 1234567.0, None → default, "" → default
    초보자 팁: 엑셀에서 읽은 값은 타입이 제각각이므로 항상 이 함수를 거치세요.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return default
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in ("none", "nan", "-", "—"):
        return default
    # 숫자만 추출 (콤마, 원, 공백 제거)
    cleaned = re.sub(r"[^\d.\-]", "", text.replace(",", ""))
    if not cleaned or cleaned in (".", "-", "-."):
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def format_hours_or_days(value: float) -> float | int:
    """
    근무시간·연차일수 등 — 소수 허용, 반올림하지 않음.

    Excel·화면 표시용: 정수면 int, 아니면 float 그대로.
    """
    v = safe_number(value, 0.0)
    if abs(v - round(v, 6)) < 1e-9:
        return int(v) if v == int(v) else v
    return v


def parse_birth_date_from_korean_rrn(value: Any, *, as_of: date | None = None) -> date | None:
    """
    주민등록번호(또는 앞 6자리 생년월일)에서 생년월일을 추출합니다.

    7번째 자리(성별·세기 코드): 1·2·5·6 → 1900년대, 3·4·7·8 → 2000년대.
    6자리만 있으면 기준일 대비 2자리 연도 해석(한국 관례)을 사용합니다.
    """
    if value is None:
        return None
    text = re.sub(r"\s", "", str(value).strip())
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.replace("-", ""))
    if len(digits) < 6:
        return None
    as_of = as_of or date.today()
    try:
        yy = int(digits[0:2])
        mm = int(digits[2:4])
        dd = int(digits[4:6])
    except ValueError:
        return None
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None

    year: int | None = None
    if len(digits) >= 7:
        century = int(digits[6])
        if century in (1, 2, 5, 6):
            year = 1900 + yy
        elif century in (3, 4, 7, 8):
            year = 2000 + yy
        elif century in (9, 0):
            year = 1800 + yy

    if year is None:
        pivot = as_of.year % 100
        year = 1900 + yy if yy > pivot else 2000 + yy

    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def age_years_at(birth: date, as_of: date | None = None) -> int:
    """만 나이(생일 기준)."""
    as_of = as_of or date.today()
    years = as_of.year - birth.year
    if (as_of.month, as_of.day) < (birth.month, birth.day):
        years -= 1
    return years


def is_senior_60_plus_from_rrn(rrn: Any, *, as_of: date | None = None) -> bool:
    """주민번호 기준 만 60세 이상 여부."""
    birth = parse_birth_date_from_korean_rrn(rrn, as_of=as_of)
    if birth is None:
        return False
    return age_years_at(birth, as_of) >= SENIOR_AGE_YEARS


def is_senior_60_plus_roster_record(rec: dict[str, Any], *, as_of: date | None = None) -> bool:
    """명부 레코드(주민번호 필드) 기준 만 60세 이상."""
    return is_senior_60_plus_from_rrn(rec.get("주민번호"), as_of=as_of)


def round_won(amount: float) -> int:
    """
    급여 **금액(원)** 산출 시에만 ROUND(반올림).

    근무시간·연차·반차 일수 등에는 사용하지 마세요 → format_hours_or_days.
    """
    return int(round(amount))


def round_won_tens(amount: float) -> int:
    """급여 금액 — 10원 단위 ROUND(반올림)."""
    return int(round(amount / 10)) * 10


def write_merged_safe(ws: Worksheet, cell_ref: str, value: Any) -> None:
    """
    병합(Merged)된 셀에도 안전하게 값을 기록합니다.

    openpyxl은 병합 셀의 비-좌상단 위치에 직접 쓰면 MergedCell 오류가 납니다.
    이 함수는 해당 좌표가 병합 영역이면 merge 범위의 좌상단 셀에 값을 씁니다.
    """
    cell = ws[cell_ref]
    if isinstance(cell, MergedCell):
        for merged_range in ws.merged_cells.ranges:
            if cell.coordinate in merged_range:
                top_left = ws.cell(row=merged_range.min_row, column=merged_range.min_col)
                top_left.value = value
                return
    else:
        cell.value = value


def calc_employment_insurance(taxable_total: float) -> int:
    """고용보험(실업급여) 근로자 부담분 — 과세총액 × 0.9%, 10원 단위 ROUND."""
    from insurance import EMPLOYMENT_INSURANCE_WORKER_RATE

    return round_won_tens(taxable_total * EMPLOYMENT_INSURANCE_WORKER_RATE)


def is_likely_hours(value: float, ordinary_hourly: float) -> bool:
    """
    청구서 셀 값이 '시간'인지 '금액'인지 추정합니다.

    - 300 이하의 소수/정수 → 시간으로 간주
    - 통상시급×1.5×값과 ±5% 이내면 금액(연장수당)으로 간주
    """
    if value <= 0:
        return False
    if value <= 300:
        expected_pay = ordinary_hourly * 1.5 * value
        # 금액으로 보이면 (큰 숫자) hours가 아님
        if value >= 1000:
            return False
        if expected_pay > 0 and abs(value - expected_pay) / expected_pay < 0.05:
            return False
        return True
    return False
