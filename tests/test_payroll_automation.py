from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_automation import (
    PayrollAutomationRequest,
    PayrollAutomationResult,
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


if __name__ == "__main__":
    unittest.main()
