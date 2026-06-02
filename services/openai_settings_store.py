"""
services/openai_settings_store.py - OpenAI API 설정 (사용자별 저장 + 환경변수 폴백)

모델 우선순위: OPENAI_MODEL 환경변수 > 사용자 workspace 설정 > gpt-4o-mini
API 키 우선순위: 사용자 workspace > OPENAI_API_KEY 환경변수
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.session_service import UserSession, require_session

# gpt-4o-mini: 대부분 계정에서 사용 가능. 고급 모델은 API 설정에서 지정.
DEFAULT_MODEL = "gpt-4o-mini"
_SETTINGS_DIR = app_data_dir() / "ai"


def sanitize_api_key(raw: str | None) -> str:
    """
    OpenAI API 키만 허용 (sk-..., ASCII, 공백·줄바꿈 없음).
    채팅 복사·한글 문구가 들어간 값은 빈 문자열로 처리합니다.
    """
    if raw is None:
        return ""
    key = str(raw).strip()
    if not key:
        return ""
    if any(ch in key for ch in "\n\r\t "):
        return ""
    if not key.startswith("sk-") or len(key) < 20 or len(key) > 512:
        return ""
    try:
        key.encode("ascii")
    except UnicodeEncodeError:
        return ""
    return key


def validate_api_key_input(raw: str | None) -> tuple[str, str | None]:
    """저장 전 검증. (정규화된 키, 오류 메시지) — 빈 값은 키 삭제."""
    if raw is None:
        return "", None
    text = str(raw).strip()
    if not text:
        return "", None
    clean = sanitize_api_key(text)
    if clean:
        return clean, None
    return "", (
        "API 키 형식이 올바르지 않습니다.\n\n"
        "· platform.openai.com → API keys 에서 발급한\n"
        "  sk- 로 시작하는 키만 입력하세요.\n"
        "· 채팅 화면·안내 문구(ℹ 등)를 붙여넣지 마세요."
    )


def _env_api_key() -> str:
    return sanitize_api_key(os.environ.get("OPENAI_API_KEY", ""))


def resolve_openai_model(user_model: str | None = None) -> str:
    """OPENAI_MODEL env > user setting > DEFAULT_MODEL."""
    env_model = os.environ.get("OPENAI_MODEL", "").strip()
    if env_model:
        return env_model
    user = str(user_model or "").strip()
    if user:
        return user
    return DEFAULT_MODEL


def _user_settings_path(sess: UserSession) -> Path:
    return (
        app_data_dir()
        / "workspace"
        / sess.tenant_id
        / "users"
        / sess.user_id
        / "openai_settings.json"
    )


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_openai_settings(session: UserSession | None = None) -> dict[str, Any]:
    sess = session or require_session()
    raw = _load(_user_settings_path(sess))
    user_key = sanitize_api_key(str(raw.get("api_key") or ""))
    env_key = _env_api_key()
    api_key = user_key or env_key
    user_model_raw = str(raw.get("model") or "").strip()
    model = resolve_openai_model(user_model_raw or None)
    return {
        "api_key": api_key,
        "model": model,
        "enabled": bool(raw.get("enabled", True)),
        "key_source": "user" if user_key else ("env" if env_key else "none"),
        "key_invalid_stored": bool(str(raw.get("api_key") or "").strip()) and not user_key,
        "model_source": (
            "env"
            if os.environ.get("OPENAI_MODEL", "").strip()
            else ("user" if user_model_raw else "default")
        ),
    }


def save_openai_settings(
    *,
    api_key: str | None = None,
    model: str | None = None,
    enabled: bool | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or require_session()
    path = _user_settings_path(sess)
    data = _load(path)
    if api_key is not None:
        clean, err = validate_api_key_input(api_key)
        if err:
            raise ValueError(err)
        data["api_key"] = clean
    if model is not None:
        data["model"] = str(model).strip() or DEFAULT_MODEL
    if enabled is not None:
        data["enabled"] = enabled
    _save(path, data)
    return load_openai_settings(sess)


def has_api_key(session: UserSession | None = None) -> bool:
    return bool(load_openai_settings(session).get("api_key"))
