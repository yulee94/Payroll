"""
integrations/government_insurance.py - 정부/4대보험 연동 (예정)

향후 한국 정부·공공 API에서 국민연금·건강보험·고용보험 등을
자동 조회하는 어댑터를 이 모듈에 구현합니다.

현재는 인터페이스만 정의합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class InsuranceFetchResult:
    national_pension: int = 0
    health_insurance: int = 0
    long_term_care: int = 0
    employment_insurance: int = 0
    source: str = "manual"
    raw: dict | None = None


class GovernmentInsuranceProvider(Protocol):
    """4대보험 공공 API 연동 인터페이스."""

    def fetch_for_employee(self, emp_no: str, period: str) -> InsuranceFetchResult:
        ...


class ManualInsuranceProvider:
    """현재: 명부·청구서 수동 입력."""

    def fetch_for_employee(self, emp_no: str, period: str) -> InsuranceFetchResult:
        _ = emp_no, period
        return InsuranceFetchResult(source="manual")


def get_insurance_provider() -> GovernmentInsuranceProvider:
    """설정에 따라 API/Manual 프로바이더 반환 (추후 확장)."""
    from core.config import APP_CONFIG

    if APP_CONFIG.government_api_enabled:
        # return PublicApiInsuranceProvider(...)
        pass
    return ManualInsuranceProvider()
