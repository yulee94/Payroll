"""Workflow document permission Rust migration contract tests."""

from __future__ import annotations

import unittest

from services.workflow_api_contract import workflow_api_contract


class WorkflowDocumentPermissionContractTests(unittest.TestCase):
    def test_contract_declares_rust_document_permissions(self) -> None:
        contract = workflow_api_contract()
        permissions = contract["business_trip_permissions"]

        self.assertIn("WorkflowApprovalStep", permissions["permission_dtos"])
        self.assertIn("WorkflowDocumentPermissionInput", permissions["permission_dtos"])
        self.assertIn("can_view_document", permissions["rust_entrypoints"])
        self.assertIn("can_edit_document", permissions["rust_entrypoints"])
        self.assertIn("can_submit_document", permissions["rust_entrypoints"])
        self.assertIn("can_approve_document", permissions["rust_entrypoints"])
        self.assertIn("Document permissions run after the business-trip document legal-scope gate", permissions["document_permission_invariants"])
        self.assertIn("Requesters can edit and submit only draft or requested_changes documents", permissions["document_permission_invariants"])
        self.assertIn("Only the current pending approval-step assignee can approve without supplied org workflow-approval capability", permissions["document_permission_invariants"])
        self.assertIn("Supplied org workflow-approval capability only grants approve override to admin/executive/finance workflow authority", permissions["document_permission_invariants"])


if __name__ == "__main__":
    unittest.main()
