"""
services/ai_safety_policy.py - Personal AI 보안·플랫폼 변경 금지 정책

AI는 사용자 업무 산출물(초안·차트·개인 To-Do·일정)만 생성·갱신합니다.
플랫폼 코드·설정·권한·급여 원장·명부·고객사 데이터는 읽기·안내만 가능하며 변경할 수 없습니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.config import MONTHLY_REPORTS_DIR
from core.paths import app_data_dir, app_install_dir
from core.session_service import UserSession

# --- 요청 차단 (플랫폼·보안 관련) ---

_FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"플랫폼|bitween|비트윈|시스템|프로그램|앱", r"수정|변경|업데이트|패치|설치|배포|다운그레이드|리팩"),
    (r"코드|소스|main\.py|app_ui|설정파일|config", r"수정|변경|고쳐|패치|작성해"),
    (r"권한|역할|role|관리자|admin|계정|아이디|비밀번호|패스워드", r"추가|삭제|변경|부여|해제|만들|등록|초기화"),
    (r"고객사|tenant|법인", r"추가|삭제|변경|전환|등록"),
    (r"급여\s*설정|payroll_settings|access_policy|organizations\.json", r"수정|변경|바꿔|저장"),
    (r"명부|roster|근로자\s*명부", r"수정|변경|저장|삭제|추가|업데이트"),
    (r"급여\s*산출|청구서\s*업로드|process_invoice|스냅샷", r"실행|처리|업로드|삭제|초기화|되돌리"),
    (r"자료함|output|스냅샷|payroll_snapshot", r"삭제|지워|초기화|변경"),
    (r"템플릿|templates|양식\s*파일", r"수정|변경|덮어|교체"),
    (r"registry\.json|tenants\.json|users/", r"수정|변경|삭제|쓰기"),
    (r"api\s*키|openai|secret|토큰", r"노출|알려|출력|보여"),
    (r"다른\s*사용자|타\s*계정|타인", r"조회|삭제|변경|접속"),
    (r"자동\s*업데이트|exe|빌드|pyinstaller", r"실행|설치|배포"),
    (r"우회|해킹|권한\s*없이", r""),
)

# 단일 키워드로도 차단
_FORBIDDEN_PHRASES = (
    "플랫폼 수정",
    "플랫폼 변경",
    "플랫폼 업데이트",
    "시스템 설정 변경",
    "권한 변경해",
    "관리자 만들어",
    "계정 추가해",
    "고객사 삭제",
    "명부 수정해",
    "급여 설정 바꿔",
    "청구서 업로드해줘",
    "급여 산출 실행",
    "스냅샷 삭제",
    "코드 수정",
    "소스 수정",
)

# 허용되는 AI 쓰기 범주 (안내용)
ALLOWED_AI_WRITES_KO = (
    "본인 To-Do·캘린더 (개인 업무함)",
    "본인 AI 대화 기록·생성 차트 이미지 (ai_assets)",
    "요청 시 월별 보고 Excel·초안 (권한·기존 산출 데이터 기반, 보고서 폴더만)",
)


@dataclass(frozen=True)
class SafetyAssessment:
    allowed: bool
    blocked: bool
    category: str = ""
    user_message: str = ""

    @property
    def denial_text(self) -> str:
        if self.allowed:
            return ""
        return self.user_message or (
            "보안 정책상 Personal AI는 플랫폼·설정·권한·급여 원장·명부를 "
            "변경하거나 업데이트할 수 없습니다.\n\n"
            "가능한 작업: 업무 질의, 보고·기안 초안, 자료·양식 검색, "
            "차트·Excel 보고서 생성(권한 범위), 개인 할 일·일정 등록.\n"
            "플랫폼 변경은 관리자·해당 메뉴에서 직접 진행해 주세요."
        )


def assess_ai_request_safety(question: str) -> SafetyAssessment:
    """사용자 질문이 플랫폼 변경·보안 위반인지 검사."""
    text = str(question or "").strip()
    if not text:
        return SafetyAssessment(allowed=True, blocked=False)

    tl = text.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in tl or phrase in text:
            return SafetyAssessment(
                allowed=False,
                blocked=True,
                category="platform_modify",
                user_message=_denial_for_category("platform_modify"),
            )

    for topic_pat, action_pat in _FORBIDDEN_PATTERNS:
        if re.search(topic_pat, text, re.I):
            if not action_pat or re.search(action_pat, text, re.I):
                return SafetyAssessment(
                    allowed=False,
                    blocked=True,
                    category="platform_modify",
                    user_message=_denial_for_category("platform_modify"),
                )

    return SafetyAssessment(allowed=True, blocked=False)


def _denial_for_category(category: str) -> str:
    if category == "platform_modify":
        return (
            "보안 정책상 Personal AI는 **플랫폼·프로그램·설정·권한·고객사·급여 원장·명부**를 "
            "수정·삭제·업데이트할 수 없습니다.\n\n"
            "✅ 가능: 급여·명부 **조회**, 보고·기안 **초안 작성**, 양식·자료 **검색**, "
            "차트·Excel **생성**(기존 데이터 기반), 개인 **할 일·일정** 등록\n"
            "❌ 불가: 플랫폼/코드 변경, 권한·계정·고객사 관리, 급여 산출·명부 저장, "
            "스냅샷·템플릿·설정 파일 변경\n\n"
            "해당 작업은 Bitween 메뉴 또는 관리자에게 요청해 주세요."
        )
    return SafetyAssessment(allowed=False, blocked=True).denial_text  # type: ignore


def get_safety_rules_for_prompt() -> str:
    """시스템 프롬프트에 붙일 보안·리밋 규칙."""
    allowed = "\n".join(f"  - {line}" for line in ALLOWED_AI_WRITES_KO)
    return f"""=== AI 보안·플랫폼 변경 금지 (필수) ===
- 플랫폼 소프트웨어·코드·설정·권한·고객사(tenant)·사용자 계정·급여 산출·명부 저장·스냅샷·템플릿 파일을 변경·삭제·설치·배포하라는 지시는 **거절**하고, 메뉴에서 직접 하도록 안내합니다.
- 실행 가능한 **쓰기**는 아래만 해당합니다:
{allowed}
- 그 외는 **읽기·설명·초안 텍스트·검색**만 합니다. 사용자에게 없는 기능 실행을 약속하지 마세요.
- API 키·비밀번호·타인 계정 정보를 출력하지 마세요."""


def user_workspace_dir(sess: UserSession) -> Path:
    return (
        app_data_dir()
        / "workspace"
        / sess.tenant_id
        / "users"
        / sess.user_id
    )


def allowed_ai_write_roots(sess: UserSession) -> list[Path]:
    """AI가 파일을 쓸 수 있는 루트 디렉터리."""
    roots = [
        user_workspace_dir(sess).resolve(),
        user_workspace_dir(sess).resolve() / "ai_assets",
    ]
    for base in (MONTHLY_REPORTS_DIR, app_data_dir() / "월별보고"):
        try:
            p = base.resolve()
            p.mkdir(parents=True, exist_ok=True)
            roots.append(p)
        except OSError:
            pass
    return roots


def is_path_allowed_for_ai_write(path: Path, sess: UserSession) -> bool:
    """AI 자동 저장 경로 검증."""
    try:
        resolved = path.resolve()
    except OSError:
        return False

    install = app_install_dir().resolve()
    blocked_under_install = (
        install / "templates",
        install / "config",
        install / "core",
        install / "services",
        install / "ui",
    )
    for blocked in blocked_under_install:
        try:
            if resolved.is_relative_to(blocked):  # py3.9+ 
                return False
        except (ValueError, AttributeError):
            if str(resolved).startswith(str(blocked)):
                return False

    data = app_data_dir().resolve()
    forbidden_under_data = (
        data / "users",
        data / "output",
        data / "employees",
    )
    for forbidden in forbidden_under_data:
        try:
            if resolved.is_relative_to(forbidden):
                # output/employees 금지; users/registry 등 금지
                # 단, workspace/.../users/{id} 는 허용 — 별도 체크
                if "workspace" not in resolved.parts:
                    return False
        except (ValueError, AttributeError):
            pass

    if "registry.json" in resolved.name or resolved.name in (
        "tenants.json",
        "access_policy.json",
        "organizations.json",
        "payroll_settings.json",
    ):
        return False

    for root in allowed_ai_write_roots(sess):
        try:
            if resolved.is_relative_to(root):
                return True
        except (ValueError, AttributeError):
            if str(resolved).startswith(str(root)):
                return True

    return False


def assert_ai_write_allowed(path: Path, sess: UserSession) -> None:
    if not is_path_allowed_for_ai_write(path, sess):
        raise PermissionError(
            f"보안 정책상 AI가 이 경로에 저장할 수 없습니다: {path}\n"
            "개인 업무함·보고서 출력 폴더만 허용됩니다."
        )
