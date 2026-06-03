from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.payroll_policy_store import (
    INPUT_ATTENDANCE,
    INPUT_LABELS,
    MISSING_CLOCK_DEDUCT,
    MISSING_CLOCK_LABELS,
)
from services.payroll_settings_ui_bridge import (
    _operation_policy_from_panel,
    install_payroll_settings_panel_integrations,
)


class _FakeText:
    def __init__(self) -> None:
        self.value = ""
        self.state = "disabled"

    def configure(self, **kwargs) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]

    def get(self, *_args) -> str:
        return self.value

    def delete(self, *_args) -> None:
        self.value = ""

    def insert(self, _index: str, value: str) -> None:
        self.value = value


class _FakeVar:
    def __init__(self, value) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class PayrollSettingsUiBridgeTests(unittest.TestCase):
    def test_setup_guide_is_appended_to_existing_breakdown(self) -> None:
        class DummyPanel:
            def __init__(self) -> None:
                self._breakdown_text = _FakeText()

            def _refresh_breakdown_panel(self) -> None:
                self._breakdown_text.configure(state="normal")
                self._breakdown_text.insert("1.0", "base breakdown")
                self._breakdown_text.configure(state="disabled")

            def _is_tenant_scope(self) -> bool:
                return False

            def _selected_workplace(self) -> str:
                return "Site A"

            def _tenant_id(self) -> str:
                return "tenant-a"

        settings_module = SimpleNamespace(PayrollSettingsPanel=DummyPanel)
        install_payroll_settings_panel_integrations(settings_module)

        panel = DummyPanel()
        with patch(
            "services.payroll_self_service.format_payroll_setup_guide",
            return_value="setup guide",
        ):
            panel._refresh_breakdown_panel()

        self.assertEqual(panel._breakdown_text.value, "base breakdown\n\nsetup guide")
        self.assertEqual(panel._breakdown_text.state, "disabled")
        self.assertTrue(DummyPanel._bitween_setup_guide_patched)

    def test_operation_policy_payload_from_settings_vars(self) -> None:
        panel = SimpleNamespace(
            _op_input_label_to_key={label: key for key, label in INPUT_LABELS.items()},
            _op_missing_label_to_key={label: key for key, label in MISSING_CLOCK_LABELS.items()},
            _op_input_var=_FakeVar(INPUT_LABELS[INPUT_ATTENDANCE]),
            _op_payday_var=_FakeVar("10일"),
            _op_show_guide_var=_FakeVar(False),
            _op_note_var=_FakeVar("site-specific rule"),
            _op_attendance_enabled_var=_FakeVar(True),
            _op_attendance_source_var=_FakeVar("biometric"),
            _op_rounding_var=_FakeVar("15"),
            _op_late_grace_var=_FakeVar("5"),
            _op_early_leave_grace_var=_FakeVar("3"),
            _op_overtime_rounding_var=_FakeVar("30"),
            _op_missing_clock_var=_FakeVar(MISSING_CLOCK_LABELS[MISSING_CLOCK_DEDUCT]),
            _op_holiday_source_var=_FakeVar("attendance"),
        )

        payload = _operation_policy_from_panel(panel)

        self.assertEqual(payload["input_basis"], INPUT_ATTENDANCE)
        self.assertEqual(payload["payday"], "10일")
        self.assertFalse(payload["show_setup_guide"])
        self.assertEqual(payload["policy_note"], "site-specific rule")
        self.assertEqual(payload["attendance"]["rounding_minutes"], 15)
        self.assertEqual(payload["attendance"]["late_grace_minutes"], 5)
        self.assertEqual(payload["attendance"]["early_leave_grace_minutes"], 3)
        self.assertEqual(payload["attendance"]["overtime_rounding_minutes"], 30)
        self.assertEqual(payload["attendance"]["missing_clock_policy"], MISSING_CLOCK_DEDUCT)
        self.assertEqual(payload["attendance"]["holiday_source"], "attendance")


if __name__ == "__main__":
    unittest.main()
