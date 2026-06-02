"""COSS groupware document import — content, attachments, archive."""

__all__ = ["upsert_gw_document", "parse_detail_payload"]


def __getattr__(name: str):
    if name == "upsert_gw_document":
        from core.gw_import.importer import upsert_gw_document

        return upsert_gw_document
    if name == "parse_detail_payload":
        from core.gw_import.detail_parser import parse_detail_payload

        return parse_detail_payload
    raise AttributeError(name)
