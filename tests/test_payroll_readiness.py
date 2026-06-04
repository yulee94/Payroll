from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_readiness import payroll_readiness_cards, payroll_readiness_snapshot


class PayrollReadinessTests(unittest.TestCase):
    def test_snapshot_reports_ready_payroll_automation_state(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={"policy": {"input_basis": "custom"}, "source": "tenant"},
        ), patch(
            "services.payroll_policy_store.operation_policy_source_label",
            return_value="tenant default",
        ), patch(
            "services.employee_roster_store.canonical_roster_path",
            return_value=Path("templates/roster.xlsx"),
        ), patch(
            "services.employee_roster_store.roster_exists",
            return_value=True,
        ), patch(
            "services.employee_roster_store.roster_updated_display",
            return_value="2026-06-01 09:47",
        ), patch(
            "payroll_archive.list_payroll_periods",
            return_value=["2026-05", "2026-04"],
        ):
            snapshot = payroll_readiness_snapshot(tenant_id="tenant-a")

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["status"], "ready")
        self.assertEqual(snapshot["tenant_id"], "tenant-a")
        self.assertEqual(snapshot["ready_count"], 4)
        self.assertEqual(snapshot["attention_count"], 0)
        json.dumps(snapshot, ensure_ascii=False)
        self.assertEqual([item["id"] for item in snapshot["items"]], [
            "input_basis",
            "roster",
            "payroll_outputs",
            "api_contract",
        ])

    def test_snapshot_marks_missing_roster_as_attention_without_failing(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={"policy": {"input_basis": "custom"}, "source": "global"},
        ), patch(
            "services.payroll_policy_store.operation_policy_source_label",
            return_value="built-in",
        ), patch(
            "services.employee_roster_store.canonical_roster_path",
            return_value=Path("templates/roster.xlsx"),
        ), patch(
            "services.employee_roster_store.roster_exists",
            return_value=False,
        ), patch(
            "payroll_archive.list_payroll_periods",
            return_value=[],
        ):
            snapshot = payroll_readiness_snapshot(tenant_id="tenant-a")

        by_id = {item["id"]: item for item in snapshot["items"]}
        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "attention")
        self.assertEqual(snapshot["attention_count"], 1)
        self.assertEqual(snapshot["pending_count"], 1)
        self.assertEqual(by_id["roster"]["status"], "attention")
        self.assertEqual(by_id["payroll_outputs"]["status"], "pending")

    def test_cards_are_launcher_friendly_strings(self) -> None:
        with patch(
            "services.payroll_policy_store.resolve_payroll_operation_policy",
            return_value={"policy": {"input_basis": "custom"}, "source": "tenant"},
        ), patch(
            "services.payroll_policy_store.operation_policy_source_label",
            return_value="tenant default",
        ), patch(
            "services.employee_roster_store.canonical_roster_path",
            return_value=Path("templates/roster.xlsx"),
        ), patch(
            "services.employee_roster_store.roster_exists",
            return_value=True,
        ), patch(
            "services.employee_roster_store.roster_updated_display",
            return_value="2026-06-01 09:47",
        ), patch(
            "payroll_archive.list_payroll_periods",
            return_value=["2026-05"],
        ):
            cards = payroll_readiness_cards(tenant_id="tenant-a")

        self.assertEqual(len(cards), 4)
        for card in cards:
            for key in ("id", "title", "value", "detail", "status", "color"):
                self.assertIsInstance(card[key], str)


if __name__ == "__main__":
    unittest.main()
