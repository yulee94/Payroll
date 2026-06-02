"""법정·규정 문서함 (정관·인사규정·법정 의무 자료)."""

from core.compliance_docs.store import (
    acknowledge_document,
    category_label,
    delete_document,
    get_document,
    has_acknowledged,
    list_documents,
    requires_acknowledgment,
    upload_document,
)
from core.compliance_docs.permissions import can_manage_compliance_docs, can_view_compliance_docs

__all__ = [
    "acknowledge_document",
    "can_manage_compliance_docs",
    "can_view_compliance_docs",
    "category_label",
    "delete_document",
    "get_document",
    "has_acknowledged",
    "list_documents",
    "requires_acknowledgment",
    "upload_document",
]
