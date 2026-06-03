from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_api_adapter import (
    build_payroll_api_request,
    payroll_api_response,
    run_payroll_api,
    scope_from_api_payload,
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

        payload = payroll_api_response(result)

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"], "boom")
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
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05",
                    "invoice_path": "invoice.xlsx",
                    "input_type": "invoice",
                }
            )

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["count"], 2)
        self.assertEqual(run.call_args.args[0].invoice_path, Path("invoice.xlsx"))


if __name__ == "__main__":
    unittest.main()
