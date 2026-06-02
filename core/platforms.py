"""
core/platforms.py - COSS Group 통합 플랫폼 런처 정의

신규 사업부·기능은 PLATFORMS 목록에 항목을 추가하고 enabled·entry_page 를 연결합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PlatformDef:
    id: str
    title: str
    subtitle: str
    description: str
    accent: str
    icon_glyph: str
    enabled: bool
    entry_page: str | None
    features: tuple[str, ...]
    status_label: str = ""
    nav_tabs: tuple[tuple[str, str], ...] = ()


PLATFORMS: tuple[PlatformDef, ...] = (
    PlatformDef(
        id="workflow",
        title="업무 · 전자결재",
        subtitle="Workflow & ERP",
        description=(
            "다우오피스·네이버웍스형 결재함(결재/진행/완료/반려/참조), "
            "근태·구매·지출 양식, 실행업무·사업장·임원 보고·월마감 허브입니다."
        ),
        accent="#2563EB",
        icon_glyph="◎",
        enabled=True,
        entry_page="workflow",
        features=("홈·결재함", "양식 작성", "실행업무", "사업장·임원 보고", "월마감"),
        status_label="MVP",
    ),
    PlatformDef(
        id="payroll",
        title="급여",
        subtitle="Payroll",
        description=(
            "도급비 청구서 업로드, 급여대장·명세서·지급내역 산출, "
            "월별 자료함·요약·보고를 관리합니다."
        ),
        accent="#1F3864",
        icon_glyph="₩",
        enabled=True,
        entry_page="home",
        features=("급여 산출", "월별 자료함", "월별 요약", "급여 보고", "급여 설정"),
        status_label="운영 중",
    ),
    PlatformDef(
        id="hr",
        title="인사 · 노무",
        subtitle="HR & Labor",
        description=(
            "근로자 명부, 연차·휴가, 근태, 근로계약, 증명서 발급, "
            "노무·징계, 입·퇴사 절차(4대보험·퇴직금·알림), "
            "건강검진 대상 조회·결과지 업로드를 관리합니다."
        ),
        accent="#0D9488",
        icon_glyph="👥",
        enabled=True,
        entry_page="hr",
        features=("직원 명부", "연차·휴가", "근태", "근로계약", "증명서", "노무·입퇴사", "법정·규정", "건강검진", "절차·알림"),
        status_label="MVP",
        nav_tabs=(
            ("roster", "직원 명부"),
            ("leave", "연차 · 휴가"),
            ("attendance", "근태"),
            ("contracts", "근로계약"),
            ("certificates", "증명서"),
            ("labor", "노무 · 징계"),
            ("onboarding", "입 · 퇴사"),
            ("severance", "퇴직금"),
            ("compliance_docs", "법정 · 규정"),
            ("signal", "신호등"),
            ("health_checkup", "건강검진"),
        ),
    ),
    PlatformDef(
        id="recruitment",
        title="채용 · 마당",
        subtitle="Recruitment",
        description=(
            "법인별 채용공고 작성·승인, 플랫폼 내 채용마당 게시, "
            "지원 접수 및 고용24·SNS 등 외부 채널 홍보 상태를 관리합니다."
        ),
        accent="#DB2777",
        icon_glyph="📣",
        enabled=True,
        entry_page="recruitment",
        features=("채용공고", "채용마당", "지원 접수", "채널 · 홍보"),
        status_label="MVP",
        nav_tabs=(
            ("postings", "채용공고"),
            ("marketplace", "채용마당"),
            ("applications", "지원 접수"),
            ("channels", "채널 · 홍보"),
        ),
    ),
    PlatformDef(
        id="kpi",
        title="KPI · 경영",
        subtitle="Executive KPI",
        description=(
            "법인·사업장·개인 KPI와 손익을 한눈에 — 경영 지도, 이슈 알림, "
            "인사·급여 연동(예정), 회계 실시간 연동(예정)."
        ),
        accent="#4F46E5",
        icon_glyph="📊",
        enabled=True,
        entry_page="kpi",
        features=("경영 지도", "법인 손익", "사업장 KPI", "개인 KPI", "이슈 알림"),
        status_label="MVP",
        nav_tabs=(
            ("map", "경영 지도"),
            ("entities", "법인 손익"),
            ("sites", "사업장"),
            ("individual", "개인 KPI"),
            ("alerts", "이슈 · 알림"),
        ),
    ),
    PlatformDef(
        id="maintenance",
        title="정비 사업부",
        subtitle="Maintenance / CMMS",
        description=(
            "Fiix·SAP PM형 작업지시(WO), 설비·자산 이력, 예방정비 일정, "
            "부품 재고·외주 정비를 관리합니다."
        ),
        accent="#0F766E",
        icon_glyph="⚙",
        enabled=True,
        entry_page="maintenance",
        features=("작업 지시", "설비 이력", "정비 일정", "부품 재고"),
        status_label="MVP",
        nav_tabs=(
            ("work_orders", "작업 지시"),
            ("assets", "설비 이력"),
            ("schedules", "정비 일정"),
            ("parts", "부품 재고"),
        ),
    ),
    PlatformDef(
        id="bidding",
        title="입찰",
        subtitle="Bidding",
        description=(
            "나라장터·Procore형 공고 관리, 견적·원가 분석, "
            "제출 일정 및 낙찰·패찰 이력을 한곳에서 추적합니다."
        ),
        accent="#7C3AED",
        icon_glyph="◆",
        enabled=True,
        entry_page="bidding",
        features=("공고 관리", "견적 산출", "제출 일정", "낙찰 이력"),
        status_label="MVP",
        nav_tabs=(
            ("notices", "공고 관리"),
            ("estimates", "견적 산출"),
            ("submissions", "제출 일정"),
            ("history", "낙찰 이력"),
        ),
    ),
    PlatformDef(
        id="accounting",
        title="회계 · 경리",
        subtitle="Accounting",
        description=(
            "더존·SAP FI형 전표 입력, 세무 신고 일정, "
            "주간 자금 계획 및 월·분기 결산 보고 허브입니다."
        ),
        accent="#B45309",
        icon_glyph="▣",
        enabled=True,
        entry_page="accounting",
        features=("전표 입력", "세무 신고", "자금 계획", "결산 보고"),
        status_label="MVP",
        nav_tabs=(
            ("vouchers", "전표 입력"),
            ("tax_events", "세무 신고"),
            ("cash_plan", "자금 계획"),
            ("reports", "결산 보고"),
        ),
    ),
    PlatformDef(
        id="mobile",
        title="현장 · 모바일",
        subtitle="Field Mobile",
        description=(
            "사업장 GPS·지문/얼굴인식 출퇴근, 근무시간 누적 급여(청구서 없음), "
            "연차·급여 조회·계좌·명세서 이메일 셀프서비스. Bitween HR·급여와 동기화."
        ),
        accent="#059669",
        icon_glyph="📱",
        enabled=False,
        entry_page=None,
        features=("GPS 출퇴근", "생체인증", "근태 급여", "연차·급여 조회", "프로필"),
        status_label="준비 중",
    ),
)


def get_platform(platform_id: str) -> PlatformDef | None:
    for p in PLATFORMS:
        if p.id == platform_id:
            return p
    return None


def list_enabled_platforms() -> list[PlatformDef]:
    return [p for p in PLATFORMS if p.enabled]


PlatformOpenHandler = Callable[[str], None]
