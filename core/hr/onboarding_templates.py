"""
core/hr/onboarding_templates.py - 입·퇴사 절차·필수 서류 템플릿 (국내 HR 실무 기준)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssigneeRole = Literal["hr", "payroll", "dept_manager", "safety", "admin"]


@dataclass(frozen=True)
class OnboardingStepTemplate:
    code: str
    title: str
    document: str
    assignee_role: AssigneeRole
    due_offset_days: int  # target_date 기준 (음수=이전, 양수=이후)
    required: bool = True
    critical: bool = False  # 법정 기한·누락 시 경고 강조 (4대보험 상실 등)
    category: str = ""
    legal_note: str = ""


# 입사 — 근로계약·4대보험 취득·급여·안전교육 등
HIRE_STEPS: tuple[OnboardingStepTemplate, ...] = (
    OnboardingStepTemplate(
        "hire_contract",
        "근로계약서 작성·서명",
        "근로계약서",
        "hr",
        -3,
        category="계약",
        legal_note="입사 전 서면 근로계약 (근로기준법)",
    ),
    OnboardingStepTemplate(
        "hire_signal_check",
        "Bitween 신호등 조회",
        "주민번호 기준 타 법인 이력",
        "hr",
        -4,
        category="채용",
        legal_note="주민등록번호로 매칭 · 동명이인 구분 · 타 법인 퇴사 이력 참고",
    ),
    OnboardingStepTemplate(
        "hire_consent",
        "취업규칙·개인정보 동의",
        "동의서",
        "hr",
        -1,
        category="계약",
    ),
    OnboardingStepTemplate(
        "hire_roster",
        "근로자 명부 등록",
        "명부 등록",
        "hr",
        0,
        category="인사",
    ),
    OnboardingStepTemplate(
        "hire_payroll",
        "급여·4대보험 급여반영 등록",
        "급여 등록 신청",
        "payroll",
        -1,
        category="급여",
    ),
    OnboardingStepTemplate(
        "hire_insurance_acquire",
        "4대보험 취득신고",
        "4대보험 취득신고서",
        "hr",
        0,
        critical=True,
        category="4대보험",
        legal_note="입사일 14일 이내 (고용·산재·국민·건강)",
    ),
    OnboardingStepTemplate(
        "hire_employment_ins",
        "고용보험·산재보험 취득",
        "고용·산재 취득신고",
        "hr",
        0,
        critical=True,
        category="4대보험",
    ),
    OnboardingStepTemplate(
        "hire_pension_health",
        "국민연금·건강보험 취득",
        "국민·건강 취득신고",
        "hr",
        0,
        critical=True,
        category="4대보험",
    ),
    OnboardingStepTemplate(
        "hire_safety",
        "안전보건교육·현장 OT",
        "안전교육 이수증",
        "safety",
        7,
        category="안전",
        legal_note="산업안전보건법 교육",
    ),
    OnboardingStepTemplate(
        "hire_it_access",
        "OA·PC·출입카드·시스템 계정",
        "IT/출입 등록",
        "admin",
        0,
        required=False,
        category="IT",
    ),
    OnboardingStepTemplate(
        "hire_dept_brief",
        "부서 배치·업무 인수인계",
        "배치 확인",
        "dept_manager",
        0,
        category="인수인계",
    ),
)

# 퇴사 — 보험상실·퇴직금·인수인계·장비반납 등
RESIGN_STEPS: tuple[OnboardingStepTemplate, ...] = (
    OnboardingStepTemplate(
        "resign_letter",
        "사직서 접수·퇴사 의사 확인",
        "사직서",
        "dept_manager",
        -14,
        category="퇴사",
    ),
    OnboardingStepTemplate(
        "resign_handover",
        "업무·자료 인수인계",
        "인수인계 확인서",
        "dept_manager",
        -7,
        category="인수인계",
    ),
    OnboardingStepTemplate(
        "resign_equipment",
        "장비·출입카드·유니폼 반납",
        "반납 확인서",
        "dept_manager",
        0,
        category="총무",
    ),
    OnboardingStepTemplate(
        "resign_insurance_loss",
        "4대보험 상실신고",
        "4대보험 상실신고서",
        "hr",
        0,
        critical=True,
        category="4대보험",
        legal_note="퇴사일 14일 이내 — 누락 시 과태료",
    ),
    OnboardingStepTemplate(
        "resign_employment_loss",
        "고용보험·산재보험 상실",
        "고용·산재 상실신고",
        "hr",
        0,
        critical=True,
        category="4대보험",
    ),
    OnboardingStepTemplate(
        "resign_pension_health_loss",
        "국민연금·건강보험 상실",
        "국민·건강 상실신고",
        "hr",
        0,
        critical=True,
        category="4대보험",
    ),
    OnboardingStepTemplate(
        "resign_severance",
        "퇴직금·정산·원천징수",
        "퇴직정산서",
        "payroll",
        14,
        category="급여",
        legal_note="퇴사일 14일 이내 지급",
    ),
    OnboardingStepTemplate(
        "resign_signal_register",
        "퇴사 신호등 등록",
        "신호등 판정·Bitween 공유",
        "hr",
        0,
        category="퇴사",
        legal_note="퇴사 후에도 법인 간 채용 참고용으로 유지 (주민번호 매칭)",
    ),
    OnboardingStepTemplate(
        "resign_certificate",
        "퇴직증명서·경력증명서 발급",
        "퇴직증명서",
        "hr",
        7,
        category="증명서",
    ),
    OnboardingStepTemplate(
        "resign_roster",
        "명부 퇴사·퇴사일 반영",
        "명부 퇴사 처리",
        "hr",
        0,
        category="인사",
    ),
    OnboardingStepTemplate(
        "resign_privacy",
        "개인정보·자료 파기 확인",
        "파기 확인서",
        "hr",
        7,
        required=False,
        category="개인정보",
    ),
)

ROLE_LABELS: dict[str, str] = {
    "hr": "인사담당",
    "payroll": "급여담당",
    "dept_manager": "부서장",
    "safety": "안전관리",
    "admin": "총무·IT",
}


def steps_for_process(process_type: str) -> tuple[OnboardingStepTemplate, ...]:
    pt = str(process_type or "").strip()
    if pt == "퇴사":
        return RESIGN_STEPS
    return HIRE_STEPS
