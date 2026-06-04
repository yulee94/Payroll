"""Workflow permission Rust migration contract tests."""

from __future__ import annotations

import unittest

from services.workflow_api_contract import workflow_api_contract


class WorkflowPermissionContractTests(unittest.TestCase):
    def test_contract_declares_rust_operational_permissions(self) -> None:
        contract = workflow_api_contract()
        permissions = contract["business_trip_permissions"]

        self.assertIn("can_view_site_report", permissions["rust_entrypoints"])
        self.assertIn("can_close_month", permissions["rust_entrypoints"])
        self.assertIn("can_manage_execution_task", permissions["rust_entrypoints"])
        self.assertIn("Admin/executive/finance can view any site report", permissions["operational_invariants"])
        self.assertIn("Site managers can close month only for visible sites", permissions["operational_invariants"])
        self.assertIn("Executor role without assignment does not grant task management", permissions["operational_invariants"])


if __name__ == "__main__":
    unittest.main()
