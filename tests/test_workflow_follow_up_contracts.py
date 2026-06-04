"""Workflow follow-up Rust migration contract tests."""

from __future__ import annotations

import unittest

from services.workflow_api_contract import workflow_api_contract


class WorkflowFollowUpContractTests(unittest.TestCase):
    def test_contract_declares_rust_workflow_follow_up_planner(self) -> None:
        contract = workflow_api_contract()
        follow_up = contract["workflow_follow_up"]

        self.assertEqual(follow_up["rust_crate"], "bitween-workflow-core")
        self.assertEqual(follow_up["rust_module"], "workflow_follow_up")
        self.assertIn("WorkflowFollowUpDocument", follow_up["follow_up_dtos"])
        self.assertIn("WorkflowFollowUpAction", follow_up["follow_up_dtos"])
        self.assertIn("plan_submission_follow_up", follow_up["rust_entrypoints"])
        self.assertIn("plan_approval_complete_follow_up", follow_up["rust_entrypoints"])
        self.assertEqual(follow_up["action_types"], ["todo", "calendar"])
        self.assertIn("workflow_approval", follow_up["sources"])
        self.assertIn("Python executes workspace_store side effects", follow_up["python_boundary"])
        self.assertIn("approval-step numbering preserves original enumerate positions", follow_up["follow_up_invariants"])
        self.assertIn("executor completion calendar is omitted when executor equals requester", follow_up["follow_up_invariants"])


if __name__ == "__main__":
    unittest.main()
