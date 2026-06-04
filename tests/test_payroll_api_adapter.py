from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_api_adapter import (
    build_payroll_api_request,
    payroll_api_response,
    run_payroll_api,
    scope_from_api_payload,
    validate_payroll_api_payload,
)
from services.payroll_automation import PayrollAutomationResult
from services.payroll_scope import PayrollScope


class PayrollApiAdapterTests(unittest.TestCase):
    def test_scope_can_be_built_from_nested_payload(self) -> None:
        scope = scope_from_api_payload(
            {
                "scope": {
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                }
            }
        )

        self.assertEqual(scope, PayrollScope("Affiliate", "Site A", "2026-05"))

    def test_scope_can_be_built_from_scope_key(self) -> None:
        original = PayrollScope("Affiliate", "Site A", "2026-05")

        self.assertEqual(scope_from_api_payload({"scope": original.key}), original)

    def test_scope_can_be_built_from_api_scope_string(self) -> None:
        self.assertEqual(
            scope_from_api_payload({"scope": "Affiliate/Site A/2026-05"}),
            PayrollScope("Affiliate", "Site A", "2026-05"),
        )

    def test_build_request_accepts_camel_case_paths_and_metadata(self) -> None:
        request = build_payroll_api_request(
            {
                "scope": {
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                },
                "invoicePath": "invoice.xlsx",
                "attendancePath": "attendance.csv",
                "inputType": "mixed",
                "tenantId": "tenant-a",
                "metadata": {"request_id": "req-1"},
            }
        )

        self.assertEqual(request.scope, PayrollScope("Affiliate", "Site A", "2026-05"))
        self.assertEqual(request.invoice_path, Path("invoice.xlsx"))
        self.assertEqual(request.attendance_path, Path("attendance.csv"))
        self.assertEqual(request.input_type, "mixed")
        self.assertEqual(request.tenant_id, "tenant-a")
        self.assertEqual(request.metadata, {"request_id": "req-1"})

    def test_invalid_period_is_rejected_before_backend_run(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM"):
            build_payroll_api_request(
                {"affiliate": "Affiliate", "workplace": "Site A", "period": "202605"}
            )

    def test_api_response_adds_status_without_exception_object(self) -> None:
        result = PayrollAutomationResult(
            ok=False,
            scope=PayrollScope("Affiliate", "Site A", "2026-05"),
            input_type="attendance",
            error="boom",
            exception=ValueError("boom"),
        )

        payload = payroll_api_response(result, request_id="req-1")

        self.assertEqual(payload["status"], "error")
        self.assertTrue(payload["will_run"])
        self.assertFalse(payload["can_run"])
        self.assertEqual(payload["scope"], "Affiliate/Site A/2026-05")
        self.assertEqual(payload["scope_key"], PayrollScope("Affiliate", "Site A", "2026-05").key)
        self.assertEqual(payload["error_code"], "payroll_run_failed")
        self.assertEqual(payload["details"], {})
        self.assertEqual(payload["error"], "boom")
        self.assertEqual(payload["request_id"], "req-1")
        self.assertNotIn("exception", payload)

    def test_run_payroll_api_uses_backend_and_returns_response(self) -> None:
        result = PayrollAutomationResult(
            ok=True,
            scope=PayrollScope("Affiliate", "Site A", "2026-05"),
            input_type="invoice",
            count=2,
        )
        with patch("services.payroll_api_adapter.run_payroll_automation", return_value=result) as run:
            payload = run_payroll_api(
                {
                    "requestId": "req-1",
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                    "invoice_path": "invoice.xlsx",
                    "input_type": "invoice",
                }
            )

        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["will_run"])
        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["error_code"], "")
        self.assertEqual(run.call_args.args[0].invoice_path, Path("invoice.xlsx"))

    def test_run_payroll_api_returns_error_response_for_invalid_payload(self) -> None:
        with patch("services.payroll_api_adapter.run_payroll_automation") as run:
            payload = run_payroll_api(
                {
                    "request_id": "req-bad",
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "202605",
                }
            )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "error")
        self.assertFalse(payload["will_run"])
        self.assertFalse(payload["can_run"])
        self.assertEqual(payload["request_id"], "req-bad")
        self.assertEqual(payload["error_code"], "invalid_period")
        self.assertEqual(payload["details"]["period_format"], "YYYY-MM")
        self.assertIn("YYYY-MM", payload["error"])
        run.assert_not_called()

    def test_run_payroll_api_returns_error_code_for_missing_required_path(self) -> None:
        with patch("services.payroll_api_adapter.run_payroll_automation") as run:
            payload = run_payroll_api(
                {
                    "request_id": "req-missing-path",
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                    "input_type": "mixed",
                    "invoice_path": "invoice.xlsx",
                }
            )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "error")
        self.assertFalse(payload["will_run"])
        self.assertFalse(payload["can_run"])
        self.assertEqual(payload["error_code"], "missing_input_path")
        self.assertEqual(payload["details"]["missing_fields"], ["attendance_path"])
        self.assertIn("attendancePath", payload["details"]["accepted_aliases"]["attendance_path"])
        run.assert_not_called()

    def test_run_payroll_api_returns_error_code_for_invalid_input_type(self) -> None:
        payload = run_payroll_api(
            {
                "affiliate": "Affiliate",
                "workplace": "Site A",
                "period": "2026-05",
                "input_type": "spreadsheet",
                "invoice_path": "invoice.xlsx",
            }
        )

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["will_run"])
        self.assertFalse(payload["can_run"])
        self.assertEqual(payload["error_code"], "invalid_input_type")
        self.assertIn("mixed", payload["details"]["allowed_input_types"])

    def test_run_payroll_api_returns_error_response_for_non_mapping_payload(self) -> None:
        payload = run_payroll_api("bad")  # type: ignore[arg-type]

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "error")
        self.assertFalse(payload["will_run"])
        self.assertFalse(payload["can_run"])
        self.assertEqual(payload["error_code"], "invalid_payload")
        self.assertIn("dict", payload["error"])

    def test_validate_payroll_api_payload_returns_normalized_request(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={
                "policy": {"input_basis": "hybrid", "payday": "25일"},
                "source": "tenant",
            },
        ), patch("services.payroll_api_adapter.run_payroll_automation") as run:
            payload = validate_payroll_api_payload(
                {
                    "request_id": "req-validate",
                    "scope": "Affiliate/Site A/2026-05",
                    "invoice_path": "invoice.xlsx",
                    "attendance_path": "attendance.csv",
                    "input_type": "mixed",
                    "tenant_id": "tenant-a",
                    "metadata": {"requested_by": "frontend"},
                }
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "validated")
        self.assertFalse(payload["will_run"])
        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["request_id"], "req-validate")
        self.assertEqual(payload["scope"], "Affiliate/Site A/2026-05")
        self.assertEqual(payload["scope_key"], PayrollScope("Affiliate", "Site A", "2026-05").key)
        self.assertEqual(payload["input_type"], "mixed")
        self.assertEqual(payload["requested_input_type"], "mixed")
        self.assertEqual(payload["tenant_id"], "tenant-a")
        self.assertEqual(payload["paths"], {"invoice": "invoice.xlsx", "attendance": "attendance.csv"})
        self.assertEqual(payload["metadata_keys"], ["requested_by"])
        self.assertEqual(payload["operation_policy"], {"input_basis": "hybrid", "payday": "25일"})
        self.assertEqual(payload["operation_policy_source"], "tenant")
        run.assert_not_called()

    def test_run_payroll_api_validate_only_does_not_call_backend(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={
                "policy": {"input_basis": "invoice", "payday": "25일"},
                "source": "tenant",
            },
        ), patch("services.payroll_api_adapter.run_payroll_automation") as run:
            payload = run_payroll_api(
                {
                    "request_id": "req-dry",
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                    "invoice_path": "invoice.xlsx",
                    "input_type": "invoice",
                    "validate_only": True,
                }
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "validated")
        self.assertFalse(payload["will_run"])
        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["paths"], {"invoice": "invoice.xlsx"})
        self.assertEqual(payload["operation_policy_source"], "tenant")
        run.assert_not_called()

    def test_validate_only_preview_resolves_auto_input_from_policy(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={
                "policy": {"input_basis": "attendance", "payday": "25일"},
                "source": "site",
            },
        ), patch("services.payroll_api_adapter.run_payroll_automation") as run:
            payload = run_payroll_api(
                {
                    "request_id": "req-auto",
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                    "attendance_path": "attendance.csv",
                    "input_type": "auto",
                    "validate_only": True,
                }
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "validated")
        self.assertTrue(payload["can_run"])
        self.assertEqual(payload["requested_input_type"], "auto")
        self.assertEqual(payload["input_type"], "attendance")
        self.assertEqual(payload["operation_policy_source"], "site")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
