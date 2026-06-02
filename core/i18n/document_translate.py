"""
core/i18n/document_translate.py - 문서·보고서 본문 통번역 (OpenAI, 서버 전용)
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.i18n.registry import SUPPORTED_LOCALES, get_locale, t
from core.session_service import UserSession, get_session

_CACHE: dict[tuple[str, str, str], str] = {}


def translate_text(
    text: str,
    *,
    target_locale: str | None = None,
    source_locale: str | None = None,
    session: UserSession | None = None,
    use_cache: bool = True,
) -> str:
    """
    단일 텍스트 블록 번역. API 키 없으면 원문 반환.
    target_locale 기본값: 현재 UI 언어.
    """
    raw = str(text or "").strip()
    if not raw:
        return raw
    target = (target_locale or get_locale()).strip()
    source = (source_locale or "ko").strip()
    if target == source or target not in SUPPORTED_LOCALES:
        return raw

    cache_key = (source, target, raw)
    if use_cache and cache_key in _CACHE:
        return _CACHE[cache_key]

    target_name = SUPPORTED_LOCALES.get(target, {}).get("native", target)
    source_name = SUPPORTED_LOCALES.get(source, {}).get("native", source)

    try:
        from services.openai_client import OpenAIKeyMissingError, create_openai_client, resolve_openai_model

        sess = session or get_session()
        client = create_openai_client(sess)
        model = resolve_openai_model(sess)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a professional business translator. "
                        f"Translate from {source_name} to {target_name}. "
                        "Preserve numbers, dates, currency, proper nouns (company names), and line breaks. "
                        "Output ONLY the translation, no quotes or explanation."
                    ),
                },
                {"role": "user", "content": raw[:12000]},
            ],
            temperature=0.2,
        )
        out = (resp.choices[0].message.content or "").strip()
        if out:
            if use_cache:
                _CACHE[cache_key] = out
            return out
    except Exception:
        pass

    return raw


def translate_document_fields(
    fields: dict[str, Any],
    keys_to_translate: tuple[str, ...],
    *,
    target_locale: str | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """문서 dict의 지정 필드만 번역한 복사본 반환."""
    out = dict(fields)
    for k in keys_to_translate:
        if k in out and isinstance(out[k], str) and out[k].strip():
            out[k] = translate_text(out[k], target_locale=target_locale, session=session)
    return out


def translate_report_body(text: str, *, target_locale: str | None = None) -> str:
    """긴 보고서 텍스트: 섹션 단위로 나눠 번역 (API 한도 고려)."""
    target = target_locale or get_locale()
    if target == "ko" or not text.strip():
        return text
    chunks = re.split(r"(\n【[^】]+】\n)", text)
    out_parts: list[str] = []
    for part in chunks:
        if part.startswith("\n【") and part.endswith("】\n"):
            header = part.strip().strip("【】")
            out_parts.append(f"\n【{translate_text(header, target_locale=target)}】\n")
        elif part.strip():
            out_parts.append(translate_text(part, target_locale=target))
        else:
            out_parts.append(part)
    return "".join(out_parts)


def translation_note() -> str:
    return t("i18n.document.auto_translate_note", default="※ 자동 번역은 OpenAI API 설정 시 사용할 수 있습니다.")
