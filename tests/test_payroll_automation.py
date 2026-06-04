from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_automation import (
    PayrollAutomationRequest,
    PayrollAutomationResult,
    run_attendance_payroll,
    run_invoice_payroll,
    run_mixed_payroll,
    run_payroll_automation,
)
from services.payroll_policy_store import INPUT_ATTENDANCE
from services.payroll_scope import PayrollScope


class PayrollAutomationRoutingTests(unittest.TestCase):
    def _scope(self) -> PayrollScope:
        return PayrollScope("Affiliate", "Site A", "2026-05")

    def test_explicit_invoice_request_ignores_attendance_policy(self) -> None:
        expected = PayrollAutomationResult(
            ok=True,
            scope=self._scope(),
            input_type="invoice",
            raw={"count": 1},
        )
        request = PayrollAutomationRequest(
            scope=self._scope(),
            invoice_path=Path("invoice.xlsx"),
            input_type="invoice",
            tenant_id="tenant-a",
        )
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={"policy": {"input_basis": INPUT_ATTENDANCE}},
        ), patch("services.payroll_automation._process_invoice_path", return_value=expected) as process:
            result = run_payroll_automation(request)

        self.assertTrue(result.ok)
        self.assertEqual(result.input_type, "invoice")
        process.assert_called_once()

    def test_auto_request_uses_attendance_policy(self) -> None:
        request = PayrollAutomationRequest(
            scope=self._scope(),
            invoice_path=Path("invoice.xlsx"),
            input_type="auto",
            tenant_id="tenant-a",
        )
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={"policy": {"input_basis": INPUT_ATTENDANCE}},
        ):
            result = run_payroll_automation(request)

        self.assertFalse(result.ok)
        self.assertEqual(result.input_type, "attendance")
        self.assertIn("근태 파일", result.error)

    def test_convenience_entrypoints_build_explicit_requests(self) -> None:
        expected = PayrollAutomationResult(ok=True, scope=self._scope(), input_type="invoice")
        with patch("services.payroll_automation.run_payroll_automation", return_value=expected) as run:
            run_invoice_payroll("invoice.xlsx", self._scope(), tenant_id="tenant-a")
            run_attendance_payroll("attendance.csv", self._scope(), tenant_id="tenant-a")
            run_mixed_payroll("invoice.xlsx", "attendance.csv", self._scope(), tenant_id="tenant-a")

        invoice_req = run.call_args_list[0].args[0]
        attendance_req = run.call_args_list[1].args[0]
        mixed_req = run.call_args_list[2].args[0]

        self.assertEqual(invoice_req.input_type, "invoice")
        self.assertEqual(invoice_req.invoice_path, Path("invoice.xlsx"))
        self.assertIsNone(invoice_req.attendance_path)
        self.assertEqual(attendance_req.input_type, "attendance")
        self.assertEqual(attendance_req.attendance_path, Path("attendance.csv"))
        self.assertIsNone(attendance_req.invoice_path)
        self.assertEqual(mixed_req.input_type, "mixed")
        self.assertEqual(mixed_req.invoice_path, Path("invoice.xlsx"))
        self.assertEqual(mixed_req.attendance_path, Path("attendance.csv"))
        self.assertEqual(mixed_req.tenant_id, "tenant-a")

    def test_api_result_includes_policy_context_without_exception_object(self) -> None:
        result = PayrollAutomationResult(
            ok=False,
            scope=self._scope(),
            input_type="attendance",
            operation_policy={"input_basis": "attendance"},
            operation_policy_source="site",
            error="근태 파일이 필요합니다.",
            exception=ValueError("근태 파일이 필요합니다."),
        )

        payload = result.as_dict()

        self.assertEqual(payload["operation_policy"], {"input_basis": "attendance"})
        self.assertEqual(payload["operation_policy_source"], "site")
        self.assertNotIn("exception", payload)


if __name__ == "__main__":
    unittest.main()
