"""직원 증명·서류 자동 생성 (self-service + HR)."""

from core.hr.employee_documents.permissions import (
    can_approve_document_requests,
    can_generate_for_employee,
    can_manage_employee_documents,
    can_view_employee_documents,
)
from core.hr.employee_documents.service import (
    approve_request,
    batch_export_documents,
    create_document_request,
    document_type_label,
    generate_document,
    list_document_requests,
    list_document_types,
    list_payroll_periods_for_ui,
    list_roster_employees,
    preview_document_html,
    reject_request,
    save_document_html,
)
from core.hr.employee_documents.types import (
    DIRECT_DOWNLOAD_TYPES,
    DocumentType,
    REQUIRES_APPROVAL_TYPES,
    document_field_requirements,
)

__all__ = [
    "DIRECT_DOWNLOAD_TYPES",
    "DocumentType",
    "REQUIRES_APPROVAL_TYPES",
    "approve_request",
    "batch_export_documents",
    "can_approve_document_requests",
    "can_generate_for_employee",
    "can_manage_employee_documents",
    "can_view_employee_documents",
    "create_document_request",
    "document_field_requirements",
    "document_type_label",
    "generate_document",
    "list_document_requests",
    "list_document_types",
    "list_payroll_periods_for_ui",
    "list_roster_employees",
    "preview_document_html",
    "reject_request",
    "save_document_html",
]
