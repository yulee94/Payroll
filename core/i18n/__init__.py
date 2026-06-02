"""Bitween 다국어(i18n) — UI·문서 통번역."""

from core.i18n.document_translate import (
    translate_document_fields,
    translate_report_body,
    translate_text,
    translation_note,
)
from core.i18n.locale_store import get_saved_locale, set_saved_locale
from core.i18n.registry import (
    SUPPORTED_LOCALES,
    add_locale_listener,
    get_locale,
    init_i18n,
    locale_display_name,
    remove_locale_listener,
    set_locale,
    t,
    tf,
)

__all__ = [
    "SUPPORTED_LOCALES",
    "add_locale_listener",
    "get_locale",
    "get_saved_locale",
    "init_i18n",
    "locale_display_name",
    "remove_locale_listener",
    "set_locale",
    "set_saved_locale",
    "t",
    "tf",
    "translate_document_fields",
    "translate_report_body",
    "translate_text",
    "translation_note",
]
