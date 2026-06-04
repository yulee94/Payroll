"""Workflow inbox Rust migration contract tests."""

from __future__ import annotations

import unittest

from core.workflow import inbox as py_inbox
from services.workflow_api_contract import workflow_api_contract


class WorkflowInboxContractTests(unittest.TestCase):
    def test_contract_declares_rust_workflow_inbox_classification(self) -> None:
        contract = workflow_api_contract()
        inbox = contract["workflow_inbox"]

        self.assertEqual(inbox["rust_crate"], "bitween-workflow-core")
        self.assertEqual(inbox["rust_module"], "workflow_inbox")
        self.assertIn("WorkflowInboxDocument", inbox["inbox_dtos"])
        self.assertIn("WorkflowInboxMatchInput", inbox["inbox_dtos"])
        self.assertIn("matches_inbox", inbox["rust_entrypoints"])
        self.assertIn("filter_inbox_ids", inbox["rust_entrypoints"])
        self.assertEqual(inbox["inbox_ids"], list(py_inbox.INBOX_IDS))
        self.assertEqual(inbox["quick_tabs"], [tab[0] for tab in py_inbox.GW_INBOX_QUICK_TABS])
        self.assertIn("blank or all inbox id includes every supplied document", inbox["inbox_invariants"])
        self.assertIn("pending_approval is a legacy alias for to_approve", inbox["inbox_invariants"])
        self.assertIn("Python supplies can_approve_document and Rust does not read sessions or stores", inbox["python_boundary"])


if __name__ == "__main__":
    unittest.main()
