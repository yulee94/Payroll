"""
services/korean_age_benefits.py - 연령별 혜택·국가지원 사업 카탈로그 (한국 법령·정책 참고)

※ 실제 신청·자격은 고용노동부·국민연금공단·복지부·지자체 공고를 반드시 확인하세요.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgeBenefitProgram:
    id: str
    title: str
    min_age: int
    max_age: int | None  # None = 상한 없음 (만 나이, 해당 연령 포함)
    law_refs: tuple[str, ...]
    summary: str
    hr_actions: tuple[str, ...]
    ask_questions: tuple[str, ...]
    tags: tuple[str, ...] = ()


# 만 나이 기준 — 급여·인사 실무에서 자주 쓰는 항목
AGE_BENEFIT_PROGRAMS: tuple[AgeBenefitProgram, ...] = (
    AgeBenefitProgram(
        id="insurance_exempt_65",
        title="4대보험 근로자 부담 면제",
        min_age=65,
        max_age=None,
        law_refs=("국민연금법", "국민건강보험법", "고용보험법"),
        summary=(
            "만 65세 이상 근로자는 국민연금·건강보험·장기요양·고용보험 "
            "근로자 부담금 납부 의무가 면제되는 경우가 많습니다. "
            "Bitween 급여 산출 시 해당 월 말일 기준으로 공제 0원을 적용합니다."
        ),
        hr_actions=(
            "근로자명부 주민번호로 만 나이 확인",
            "급여대장·명세서 4대보험 공제 0원 반영",
            "4대보험 EDI·자격득실 신고와 일치 여부 점검",
        ),
        ask_questions=(
            "해당 급여월 말일 기준 만 65세가 맞습니까?",
            "국민연금 수급·직장가입 유예 등 예외 해당 여부를 공단에 확인하셨나요?",
            "건강보험 피부양·지역가입자 전환 해당은 없습니까?",
        ),
        tags=("payroll", "insurance"),
    ),
    AgeBenefitProgram(
        id="pension_workplace_60",
        title="국민연금 직장가입(만 60세 전후)",
        min_age=60,
        max_age=64,
        law_refs=("국민연금법", "국민연금법 시행령"),
        summary=(
            "만 60세에 도달한 근로자는 국민연금 직장가입 의무에서 제외되는 등 "
            "가입·납부 규정이 달라질 수 있습니다. "
            "65세 미만이라도 연금 수급·가입 이력에 따라 달라지므로 공단 확인이 필요합니다."
        ),
        hr_actions=(
            "국민연금공단 자격득실·납부 이력 확인",
            "급여 공제액과 EDI 신고액 대조",
        ),
        ask_questions=(
            "만 60세 도달 월 이후 직장가입 유지·해지 처리를 하셨나요?",
            "임의계속가입·소급 납부 해당 여부가 있습니까?",
        ),
        tags=("payroll", "insurance"),
    ),
    AgeBenefitProgram(
        id="senior_internship_60",
        title="시니어 인턴십(현장실습훈련)",
        min_age=60,
        max_age=None,
        law_refs=(
            "노인복지법",
            "고령자고용촉진법",
            "보건복지부·한국노인인력개발원 시니어인턴십 안내",
        ),
        summary=(
            "만 60세 이상 구직자·재직자 대상 현장훈련·취업 연계 프로그램입니다. "
            "경비·미화·청소·요양보호·간병·방문판매·조경 등 단순노무 직종은 "
            "참여가 제한될 수 있습니다. 명부 「시니어인턴십」 열에서 상태를 관리합니다."
        ),
        hr_actions=(
            "직원 명부 → 시니어인턴십(O/△/X) 및 지원기간 기록",
            "단순노무 해당 시 「제외」 표시",
            "관할 노인인력개발원·고용센터 프로그램 안내",
        ),
        ask_questions=(
            "단순노무(경비·미화·청소 등) 직종 해당으로 지원 제외인가요?",
            "시니어 인턴십 지원·진행 중(O/△)인가요, 아직 미신청(O)인가요?",
            "재직충족 기간(지원일~재직충족일)을 명부에 입력하셨나요?",
        ),
        tags=("employment", "senior"),
    ),
    AgeBenefitProgram(
        id="elderly_employment",
        title="고령자 고용·취업 지원",
        min_age=60,
        max_age=None,
        law_refs=("고령자고용촉진법", "고용정책 기본법"),
        summary=(
            "고령자 친화적 일자리·공공일자리·취업알선 등 "
            "고용노동부·지자체 연계 프로그램을 검토할 수 있습니다."
        ),
        hr_actions=(
            "관할 고용센터(1350) 프로그램 안내",
            "사업장 고령자 고용 장려금·세액공제 해당 여부 확인(세무·노무 자문)",
        ),
        ask_questions=(
            "현재 고용 형태(도급·파견·정규)에서 지원 가능한 프로그램을 조회하셨나요?",
            "사업주 장려금·공공근로·노인일자리 사업 해당 여부가 있습니까?",
        ),
        tags=("employment", "senior"),
    ),
    AgeBenefitProgram(
        id="middle_career_40",
        title="중장년·경력지원(취업·전환)",
        min_age=40,
        max_age=64,
        law_refs=("고용노동부 중장년내일센터", "국민취업지원제도"),
        summary=(
            "만 40~64세 구직·이직·경력전환 지원(중장년내일센터, 국민취업지원제도 등). "
            "재직 중인 경우에도 퇴직 예정자·이중就業 검토 시 안내 가능합니다."
        ),
        hr_actions=(
            "고용센터·중장년내일센터 프로그램 목록 확인",
            "사내 전환·교육 연계 필요 시 인사팀 상담",
        ),
        ask_questions=(
            "경력전환·재취업 의사가 있으신가요?",
            "국민취업지원제도(1·2유형) 참여 이력·자격이 있습니까?",
        ),
        tags=("employment", "middle"),
    ),
    AgeBenefitProgram(
        id="youth_tomorrow",
        title="청년내일채움공제·청년 고용 지원",
        min_age=15,
        max_age=34,
        law_refs=("고용노동부 청년고용정책", "청년내일채움공제 운영 요강"),
        summary=(
            "만 15~34세 청년 대상 장기근속·고용유지 지원(내일채움공제 등) 및 "
            "청년 채용·인턴 장려금 프로그램을 검토할 수 있습니다."
        ),
        hr_actions=(
            "청년 해당 인원 채용·유지 시 고용센터·고용24 공고 확인",
            "사업주 청년 고용 장려금 신청 일정 관리",
        ),
        ask_questions=(
            "해당 직원이 청년내일채움공제 가입·유지 요건(연령·고용형태)에 맞습니까?",
            "청년 추가고용·인턴 지원금 신청을 검토 중이신가요?",
        ),
        tags=("employment", "youth"),
    ),
    AgeBenefitProgram(
        id="youth_leap_account",
        title="청년도약계좌·자산형성 지원",
        min_age=19,
        max_age=34,
        law_refs=("청년도약계좌법", "고용노동부·금융위 안내"),
        summary=(
            "만 19~34세 저소득·취약계층 청년 대상 "
            "자산형성·매칭 지원(소득·재산 요건 충족 시). "
            "급여·고용형태가 자격 판단에 영향을 줄 수 있습니다."
        ),
        hr_actions=(
            "해당 직원에게 금융·복지 상담 창구 안내",
            "근로소득·4대보험 가입 증빙 제공(본인 요청 시)",
        ),
        ask_questions=(
            "소득·재산 기준을 충족하는지 본인이 확인하셨나요?",
            "근로·도급·단시간 등 고용 형태가 프로그램 요건과 맞습니까?",
        ),
        tags=("welfare", "youth"),
    ),
    AgeBenefitProgram(
        id="disability_employment",
        title="장애인 고용·장애인일자리",
        min_age=15,
        max_age=None,
        law_refs=("장애인고용촉진 및 직업재활법",),
        summary=(
            "장애인 고용 의무·장애인 표준사업장·장애인일자리 등 "
            "장애 정도·연령에 따른 지원. 명부 장애·중증장애 열과 연계합니다."
        ),
        hr_actions=(
            "명부 장애·중증장애 정보 확인",
            "장애인 고용부담금·고용촉진장려금 해당 검토",
        ),
        ask_questions=(
            "장애인 등록·중증장애 해당 여부가 명부와 일치합니까?",
            "표준사업장·장애인 고용 의무 대상 사업장인가요?",
        ),
        tags=("employment", "disability"),
    ),
)


def programs_for_age(age: int) -> list[AgeBenefitProgram]:
    """만 나이에 해당하는 프로그램 목록."""
    out: list[AgeBenefitProgram] = []
    for p in AGE_BENEFIT_PROGRAMS:
        if age < p.min_age:
            continue
        if p.max_age is not None and age > p.max_age:
            continue
        out.append(p)
    return out
