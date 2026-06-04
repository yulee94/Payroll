"""Workflow form Rust migration contract tests."""

from __future__ import annotations

import unittest

from core.workflow import forms as py_forms
from services.workflow_api_contract import workflow_api_contract


class WorkflowFormContractTests(unittest.TestCase):
    def test_contract_declares_rust_workflow_form_value_core(self) -> None:
        contract = workflow_api_contract()
        forms = contract["workflow_forms"]

        self.assertEqual(forms["rust_crate"], "bitween-workflow-core")
        self.assertEqual(forms["rust_module"], "workflow_forms")
        self.assertIn("WorkflowFormFieldDef", forms["form_dtos"])
        self.assertIn("WorkflowDocumentFields", forms["form_dtos"])
        self.assertIn("validate_form_values", forms["rust_entrypoints"])
        self.assertIn("build_document_fields", forms["rust_entrypoints"])
        self.assertEqual(forms["document_types"], list(py_forms.FORM_SCHEMAS.keys()))
        self.assertIn("Python supplies tenant/template-specific schemas", forms["python_boundary"])
        self.assertIn("number fields strip commas before integer parsing", forms["form_invariants"])
        self.assertIn("payload injects document_type after trimming supplied values", forms["form_invariants"])


if __name__ == "__main__":
    unittest.main()
