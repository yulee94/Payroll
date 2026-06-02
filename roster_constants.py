"""명부·연차대장 공통 헤더 매핑."""

from __future__ import annotations

import unicodedata
from typing import Any, Iterable

ROSTER_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "사번": ("사번", "사원번호", "NO.", "NO"),
    "성명": ("성명", "이름", "사원명"),
    "업무": ("업무", "직무", "담당업무"),
    "직책": ("직책", "직위", "직급"),
    "임원": ("임원", "임원여부", "임원구분", "임원 해당"),
    "비고": ("비고", "메모", "특이사항"),
    "고용형태": (
        "고용형태",
        "고용 구분",
        "근로형태",
        "고용형식",
        "직종구분",
    ),
    "기본시급": ("기본시급", "기본 시급", "기본급시급"),
    "통상시급": ("통상시급", "통상 시급"),
    "국민연금": ("국민연금",),
    "건강보험": ("건강보험",),
    "소득세": ("소득세",),
    "휴대폰": ("휴대폰", "핸드폰", "연락처"),
    "이메일": ("이메일", "email", "E-mail", "메일"),
    "급여명세서이메일": (
        "급여명세서이메일",
        "명세서이메일",
        "급여명세서 이메일",
        "payslip_email",
    ),
    "주민번호": ("주민번호", "생년월일"),
    "입사일": ("입사일", "현재입사일", "현재 입사일"),
    "퇴사일": ("퇴사일", "퇴직일", "퇴사 일자"),
    "최초입사일": ("최초입사일", "그룹최초입사일", "최초 입사일", "그룹 최초입사일"),
    "고용승계이력": ("고용승계이력", "승계이력", "고용승계", "승계 경로"),
    "근무지": ("근무지", "근무처", "사업장"),
    "계열사": ("계열사", "소속회사", "법인", "그룹사"),
    "장애인": (
        "장애인",
        "장애인유무",
        "장애 여부",
        "장애인 여부",
        "장애인여부",
        "장애인고용",
        "장애인 해당",
    ),
    "장애등급": (
        "장애등급",
        "장애 등급",
        "장애정도",
        "중경증",
        "장애인등급",
    ),
    "계좌": ("계좌",),
    "계좌번호": ("계좌번호", "급여계좌", "급여 계좌번호"),
    "예금주": ("예금주", "급여예금주", "수취인", "예금주명"),
    "은행명": ("은행명", "은행", "급여은행", "은행명칭", "거래은행"),
    "은행코드": ("은행코드", "금융기관코드"),
    "수당": ("수당", "고정수당"),
    "잔여연차": ("잔여연차", "잔여 연차", "연차잔여", "연차 잔여"),
    "발생연차": ("발생연차", "발생 연차", "연차발생", "연차 발생"),
    "사용연차": ("사용연차", "사용 연차", "연차사용", "연차 사용"),
    "사용월": ("사용월", "연차사용월", "사용 월"),
    "연차사용메모": ("연차사용메모", "연차 사용메모", "연차메모", "연차 사용 메모"),
    "예상발생연차": (
        "예상발생연차",
        "발생예정연차",
        "발생예상연차",
        "예상연차",
        "예상 발생연차",
        "연차발생예정",
    ),
    "시니어인턴십상태": (
        "시니어인턴십상태",
        "시니어인턴십",
        "시니어 인턴십",
        "시니어인턴십(만60)",
        "시니어 인턴십(만60)",
    ),
    "시니어인턴십지원일": (
        "시니어인턴십지원일",
        "시니어지원일",
        "지원일자",
        "시니어 인턴십 지원일",
    ),
    "시니어인턴십재직충족일": (
        "시니어인턴십재직충족일",
        "재직충족일",
        "재직충족기간",
        "재직 충족 기간",
        "시니어 재직충족일",
    ),
}


def norm_name_key(name: Any) -> str:
    """성명 비교용 정규화: 공백·전각공백·NBSP 제거, NFKC 통일."""
    if name is None:
        return ""
    s = unicodedata.normalize("NFKC", str(name).strip())
    for ch in (" ", "\u00a0", "\u3000", "\t", "\n", "\r"):
        s = s.replace(ch, "")
    return s


def names_similar(a: str, b: str, max_diff: int = 1) -> bool:
    """길이가 같고 글자 차이가 max_diff 이하이면 유사 이름으로 본다."""
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) != len(b):
        return False
    return sum(x != y for x, y in zip(a, b)) <= max_diff


def find_fuzzy_name_key(
    key: str,
    candidates: Iterable[str],
    max_diff: int = 1,
) -> str | None:
    """후보 중 유사 이름이 정확히 1명이면 해당 키를 반환."""
    if not key:
        return None
    cand_list = list(candidates)
    if key in cand_list:
        return key
    matches = [c for c in cand_list if names_similar(key, c, max_diff)]
    if len(matches) == 1:
        return matches[0]
    return None


def build_header_map(ws, aliases: dict[str, tuple[str, ...]]) -> dict[str, int]:
    headers: dict[str, int] = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(1, c).value
        if v is None:
            continue
        raw = str(v).strip().replace("\n", " ")
        for canonical, names in aliases.items():
            if raw in names:
                headers[canonical] = c
                break
    return headers
