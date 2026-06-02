"""증명·서류 유형 및 법정 필드 정의."""

from __future__ import annotations

from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    """지원 증명·서류 유형."""

    JOB_CHANGE = "job_change"
    PAYSLIP = "payslip"
    EMPLOYMENT = "employment"
    CAREER = "career"
    WITHHOLDING = "withholding"
    INCOME_LEDGER = "income_ledger"
    LOCAL_TAX = "local_tax"


DOCUMENT_LABELS: dict[str, str] = {
    DocumentType.JOB_CHANGE.value: "이직확인서",
    DocumentType.PAYSLIP.value: "급여명세서",
    DocumentType.EMPLOYMENT.value: "재직증명서",
    DocumentType.CAREER.value: "경력증명서",
    DocumentType.WITHHOLDING.value: "원천징수영수증",
    DocumentType.INCOME_LEDGER.value: "근로소득원천징수부(발췌)",
    DocumentType.LOCAL_TAX.value: "갑근세납세필증명(급여확인)",
}

DOCUMENT_DESCRIPTIONS: dict[str, str] = {
    DocumentType.JOB_CHANGE.value: "고용보험법 기준 이직확인서 (피보험기간·이직사유)",
    DocumentType.PAYSLIP.value: "급여 산출 데이터 기반 월별 급여명세서",
    DocumentType.EMPLOYMENT.value: "현재 재직 사실 확인",
    DocumentType.CAREER.value: "재직 기간·담당 업무 경력 확인",
    DocumentType.WITHHOLDING.value: "연말정산·대출용 근로소득 원천징수 영수",
    DocumentType.INCOME_LEDGER.value: "소득금액증명 대체용 월별 원천징수 발췌",
    DocumentType.LOCAL_TAX.value: "대출·금융기관 제출용 급여·갑근세 납부 확인",
}

# 즉시 다운로드 가능 (HR 승인 불필요)
DIRECT_DOWNLOAD_TYPES: frozenset[str] = frozenset(
    {
        DocumentType.PAYSLIP.value,
        DocumentType.EMPLOYMENT.value,
        DocumentType.WITHHOLDING.value,
    }
)

# HR 승인 후 다운로드
REQUIRES_APPROVAL_TYPES: frozenset[str] = frozenset(
    {
        DocumentType.JOB_CHANGE.value,
        DocumentType.CAREER.value,
        DocumentType.INCOME_LEDGER.value,
        DocumentType.LOCAL_TAX.value,
    }
)

LEGAL_DISCLAIMER = (
    "※ 본 문서는 시스템이 자동 생성한 양식입니다. "
    "인사(HR) 담당자의 내용 검토·직인(도장) 후 공식 발급됩니다. "
    "법적 효력이 필요한 경우 HR에 공식 발급을 요청하세요."
)


def document_field_requirements(doc_type: str) -> list[tuple[str, str]]:
    """유형별 필수·표준 항목 (한글 라벨, 설명)."""
    common_employer = [
        ("company_name", "사업장(법인)명"),
        ("biz_reg_no", "사업자등록번호"),
        ("ceo_name", "대표자"),
        ("company_address", "사업장 소재지"),
    ]
    common_employee = [
        ("employee_name", "성명"),
        ("rrn", "주민등록번호"),
        ("employee_no", "사번"),
        ("department", "부서"),
        ("position", "직위·직종"),
        ("hire_date", "입사일"),
    ]
    specs: dict[str, list[tuple[str, str]]] = {
        DocumentType.JOB_CHANGE.value: [
            *common_employer,
            *common_employee,
            ("resign_date", "퇴사일"),
            ("separation_reason", "이직(퇴직) 사유"),
            ("job_type", "직종"),
            ("insured_period", "고용보험 피보험기간"),
            ("issue_date", "발급일"),
        ],
        DocumentType.PAYSLIP.value: [
            ("employee_name", "성명"),
            ("period", "급여월"),
            ("gross_pay", "총지급액"),
            ("total_deduction", "공제합계"),
            ("net_pay", "실수령액"),
            ("income_tax", "소득세"),
            ("local_income_tax", "지방소득세"),
        ],
        DocumentType.EMPLOYMENT.value: [
            *common_employer,
            *common_employee,
            ("employment_status", "재직 여부"),
            ("tenure", "근속기간"),
            ("purpose", "용도"),
            ("issue_date", "발급일"),
        ],
        DocumentType.CAREER.value: [
            *common_employer,
            *common_employee,
            ("resign_date", "퇴사일(재직 중이면 공란)"),
            ("job_description", "담당 업무"),
            ("tenure", "근무기간"),
            ("issue_date", "발급일"),
        ],
        DocumentType.WITHHOLDING.value: [
            *common_employer,
            *common_employee,
            ("tax_year", "귀속연도"),
            ("total_gross", "총급여(과세)"),
            ("total_income_tax", "원천징수 소득세"),
            ("total_local_tax", "원천징수 지방소득세"),
            ("issue_date", "발급일"),
        ],
        DocumentType.INCOME_LEDGER.value: [
            *common_employer,
            *common_employee,
            ("tax_year", "귀속연도"),
            ("monthly_rows", "월별 급여·원천징수"),
            ("annual_total_gross", "연간 총급여"),
            ("annual_total_tax", "연간 원천징수세액"),
            ("issue_date", "발급일"),
        ],
        DocumentType.LOCAL_TAX.value: [
            *common_employer,
            *common_employee,
            ("recent_months", "최근 3개월 급여"),
            ("total_local_tax", "갑근세(지방소득세) 납부액"),
            ("avg_monthly_gross", "월평균 급여"),
            ("purpose", "용도(대출 등)"),
            ("issue_date", "발급일"),
        ],
    }
    return specs.get(str(doc_type), [])


def list_document_type_info() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dt in DocumentType:
        rows.append(
            {
                "id": dt.value,
                "label": DOCUMENT_LABELS[dt.value],
                "description": DOCUMENT_DESCRIPTIONS[dt.value],
                "direct_download": dt.value in DIRECT_DOWNLOAD_TYPES,
                "requires_approval": dt.value in REQUIRES_APPROVAL_TYPES,
            }
        )
    return rows
