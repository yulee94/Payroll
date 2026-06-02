from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.payroll_settings_ui_bridge import install_payroll_settings_panel_integrations


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


if __name__ == "__main__":
    unittest.main()
