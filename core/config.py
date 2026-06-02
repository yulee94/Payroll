"""
core/config.py - COSS Group 앱 전역 설정

향후 모듈(4대보험 API, 로그인, 회계 등)이 공통으로 참조합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "coss_logo.png"
BITWEEN_LOGO_PATH = ASSETS_DIR / "bitween_logo.png"
LOGO_URL = "https://www.cossok.com/html/_skin/img/common/logo.png"
MONTHLY_REPORTS_DIR = BASE_DIR / "월별보고"

APP_VERSION = "1.0.1"


@dataclass(frozen=True)
class UpdateConfig:
    """자동 업데이트 — 회사 공유폴더 또는 내부 웹 URL의 version.json 참조."""

    enabled: bool = True
    # 예: r"\\\\fileserver\\coss\\payroll\\version.json"
    # 예: "https://intranet.cossok.com/payroll/version.json"
    manifest_url: str = ""
    check_on_startup: bool = True
    # True면 개발(소스) 실행에서도 업데이트 확인 (테스트용)
    check_in_dev: bool = False


@dataclass(frozen=True)
class BrandConfig:
    company_name: str = "COSS Group"
    company_name_ko: str = "(주)코스"
    product_name: str = "Bitween"
    product_icon: str = "🔗"
    product_tagline: str = "B2B 통합 플랫폼"
    primary_navy: str = "#1F3864"
    accent_blue: str = "#2563EB"


@dataclass
class AppConfig:
    brand: BrandConfig = field(default_factory=BrandConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    # 향후: auth_enabled, api_base_url, tenant_id 등
    # 배포(EXE) 시 "로그인 없으면 사용 불가"를 위한 게이트
    require_login: bool = True
    # 계정 등록(셀프 회원가입) 허용 여부: 배포본에서는 기본 False 권장
    allow_self_register: bool = False
    government_api_enabled: bool = False


APP_CONFIG = AppConfig()
