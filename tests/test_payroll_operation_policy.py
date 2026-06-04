from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_policy_store import (
    INPUT_ATTENDANCE,
    INPUT_HYBRID,
    INPUT_INVOICE,
    clear_site_payroll_operation_policy,
    default_payroll_operation_policy,
    normalize_payroll_operation_policy,
    resolve_payroll_operation_policy,
    save_site_payroll_operation_policy,
    save_tenant_payroll_operation_policy,
)


class PayrollOperationPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._patch = patch(
            "services.payroll_settings_store.app_data_dir",
            return_value=Path(self._tmpdir.name),
        )
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    def test_normalize_invalid_input_basis_uses_hybrid_default(self) -> None:
        policy = normalize_payroll_operation_policy(
            {
                "input_basis": "bad",
                "attendance": {
                    "rounding_minutes": -10,
                    "late_grace_minutes": 9999,
                    "missing_clock_policy": "bad",
                },
            }
        )

        self.assertEqual(policy["input_basis"], INPUT_HYBRID)
        self.assertEqual(policy["attendance"]["rounding_minutes"], 1)
        self.assertEqual(policy["attendance"]["late_grace_minutes"], 240)
        self.assertEqual(policy["attendance"]["missing_clock_policy"], "warn")

    def test_tenant_policy_is_used_when_site_has_no_override(self) -> None:
        save_tenant_payroll_operation_policy(
            {
                "input_basis": INPUT_ATTENDANCE,
                "payday": "10일",
                "attendance": {"rounding_minutes": 15},
            },
            tenant_id="tenant-a",
        )

        resolved = resolve_payroll_operation_policy("Site A", tenant_id="tenant-a")

        self.assertEqual(resolved["source"], "tenant")
        self.assertEqual(resolved["policy"]["input_basis"], INPUT_ATTENDANCE)
        self.assertEqual(resolved["policy"]["attendance"]["rounding_minutes"], 15)

    def test_site_policy_overrides_and_can_be_cleared(self) -> None:
        save_tenant_payroll_operation_policy(
            default_payroll_operation_policy(),
            tenant_id="tenant-a",
        )
        save_site_payroll_operation_policy(
            "Site A",
            {"input_basis": INPUT_INVOICE},
            tenant_id="tenant-a",
        )

        site_resolved = resolve_payroll_operation_policy("Site A", tenant_id="tenant-a")
        self.assertEqual(site_resolved["source"], "site")
        self.assertEqual(site_resolved["policy"]["input_basis"], INPUT_INVOICE)

        clear_site_payroll_operation_policy("Site A", tenant_id="tenant-a")
        fallback = resolve_payroll_operation_policy("Site A", tenant_id="tenant-a")
        self.assertEqual(fallback["source"], "tenant")
        self.assertEqual(fallback["policy"]["input_basis"], INPUT_HYBRID)


if __name__ == "__main__":
    unittest.main()
