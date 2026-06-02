from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.payroll_scope import PayrollScope
from services.payroll_ui_bridge import (
    install_app_ui_integrations,
    process_invoice_via_automation,
)


class _DummyDashboard:
    def _build_layout(self) -> None:
        return None

    def _coerce_page_for_session(self, page: str) -> str:
        return page

    def show_page(self, page: str) -> str:
        return page


class PayrollUiBridgeTests(unittest.TestCase):
    def test_install_integrations_patches_dashboard_and_process_invoice(self) -> None:
        app_ui = SimpleNamespace(
            PayrollDashboard=type("DashboardForPatch", (_DummyDashboard,), {}),
            process_invoice=lambda *_args, **_kwargs: {"original": True},
        )

        install_app_ui_integrations(app_ui)

        self.assertTrue(app_ui._bitween_payroll_integrations_installed)
        self.assertTrue(app_ui.PayrollDashboard._bitween_perf_patched)
        self.assertIs(app_ui.process_invoice, process_invoice_via_automation)
        self.assertTrue(callable(app_ui._bitween_original_process_invoice))

    def test_process_invoice_via_automation_returns_backend_raw_payload(self) -> None:
        scope = PayrollScope("Affiliate", "Site", "2026-05")
        result = SimpleNamespace(ok=True, raw={"count": 3}, as_dict=lambda: {"ok": True})
        with patch("services.payroll_automation.run_invoice_payroll", return_value=result) as run:
            payload = process_invoice_via_automation("invoice.xlsx", scope)

        self.assertEqual(payload, {"count": 3})
        self.assertEqual(run.call_args.kwargs["tenant_id"], None)

    def test_process_invoice_via_automation_raises_backend_error(self) -> None:
        scope = PayrollScope("Affiliate", "Site", "2026-05")
        result = SimpleNamespace(
            ok=False,
            raw={},
            error="boom",
            exception=None,
            as_dict=lambda: {"ok": False},
        )
        with patch("services.payroll_automation.run_invoice_payroll", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                process_invoice_via_automation("invoice.xlsx", scope)

    def test_process_invoice_via_automation_reraises_preserved_exception(self) -> None:
        scope = PayrollScope("Affiliate", "Site", "2026-05")
        original = ValueError("validation failed")
        result = SimpleNamespace(
            ok=False,
            raw={},
            error="validation failed",
            exception=original,
            as_dict=lambda: {"ok": False},
        )
        with patch("services.payroll_automation.run_invoice_payroll", return_value=result):
            with self.assertRaises(ValueError) as ctx:
                process_invoice_via_automation("invoice.xlsx", scope)
        self.assertIs(ctx.exception, original)


if __name__ == "__main__":
    unittest.main()
