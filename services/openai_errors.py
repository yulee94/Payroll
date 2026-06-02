"""
services/openai_errors.py - OpenAI API 오류 분류·사용자 안내 문구
"""

from __future__ import annotations

QUOTA_USER_MESSAGE = (
    "OpenAI 사용 한도가 초과되었거나 결제(크레딧)가 부족합니다.\n\n"
    "확인 방법:\n"
    "  1. https://platform.openai.com/settings/organization/billing\n"
    "     → 결제 수단 등록·선불 크레딧 충전\n"
    "  2. https://platform.openai.com/usage → 사용량·한도 확인\n"
    "  3. 새 API 키를 만들었다면 해당 조직(Organization) 결제가 연결됐는지 확인\n\n"
    "한도가 복구되면 Personal AI에서 ChatGPT 답변이 다시 동작합니다."
)


class OpenAIQuotaError(RuntimeError):
    """429 insufficient_quota — 결제·크레딧 문제."""


def is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "insufficient_quota" in text:
        return True
    if "exceeded your current quota" in text:
        return True
    if "error code: 429" in text and "quota" in text:
        return True
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if code == 429 and "quota" in text:
        return True
    return False


def user_message_for_error(exc: BaseException) -> str:
    if isinstance(exc, OpenAIQuotaError):
        return str(exc) or QUOTA_USER_MESSAGE
    if is_quota_error(exc):
        return QUOTA_USER_MESSAGE
    return str(exc)
