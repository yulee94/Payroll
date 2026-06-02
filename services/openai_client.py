"""
services/openai_client.py - OpenAI SDK 클라이언트 (서비스 레이어만, UI/번들 미포함)

API 키: workspace 사용자 설정 → OPENAI_API_KEY 환경변수.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from services.openai_settings_store import load_openai_settings, resolve_openai_model

if TYPE_CHECKING:
    from openai import OpenAI

    from core.session_service import UserSession

COMPAT_FALLBACK_MODEL = "gpt-4o-mini"


class OpenAIKeyMissingError(RuntimeError):
    """API 키가 없을 때 — UI에서 명확한 안내용."""


def resolve_api_key(session: "UserSession | None" = None) -> tuple[str, str]:
    """
    Returns:
        (api_key, key_source) where key_source is user | env | none
    """
    settings = load_openai_settings(session)
    key = str(settings.get("api_key") or "").strip()
    source = str(settings.get("key_source") or "none")
    return key, source


def require_api_key(session: "UserSession | None" = None) -> str:
    key, source = resolve_api_key(session)
    if not key:
        raise OpenAIKeyMissingError(
            "OpenAI API 키가 없습니다.\n\n"
            "등록 방법:\n"
            "  1. Personal AI 창 → 「API 설정」에서 sk-... 키 입력 (이 계정에만 저장)\n"
            "  2. 또는 배포 PC/서버에 OPENAI_API_KEY 환경변수 설정\n\n"
            "키는 소스·실행 파일에 넣지 마세요. workspace JSON 또는 환경변수만 사용합니다."
        )
    return key


def create_openai_client(
    session: "UserSession | None" = None,
    *,
    api_key: str | None = None,
) -> "OpenAI":
    """서버(서비스) 전용 OpenAI 클라이언트."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai 패키지가 설치되지 않았습니다. "
            "프로젝트 폴더에서: pip install -r requirements.txt"
        ) from exc

    key = (api_key or "").strip() or require_api_key(session)
    return OpenAI(api_key=key)


def get_model_for_session(session: "UserSession | None" = None) -> str:
    settings = load_openai_settings(session)
    return resolve_openai_model(str(settings.get("model") or ""))
