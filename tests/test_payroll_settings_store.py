"""
tests/test_payroll_settings_store.py - 사업장별 급여 산출 설정
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.payroll_settings_store import (
    DEFAULT_SHUTDOWN_PAY_PERCENT,
    apply_tenant_defaults_to_all_sites,
    clear_site_payroll_settings,
    copy_site_settings_from_tenant_default,
    get_shutdown_pay_percent,
    load_tenant_payroll_settings,
    resolve_payroll_calc_settings,
    save_default_workplace_hours_policy,
    save_shutdown_pay_percent,
    save_site_shutdown_pay_percent,
    save_workplace_hours_policy,
)
from services.workplace_hours import MODE_FIXED, policy_for_workplace


class PayrollSettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._global_path = self._root / "config" / "payroll_settings.json"
        self._global_path.parent.mkdir(parents=True)
        self._global_path.write_text(
            json.dumps(
                {
                    "shutdown_pay_percent": 70.0,
                    "default_workplace_hours_policy": {"mode": "fixed", "hours": 209},
                    "workplace_hours_policies": {
                        "한국앰코": {"mode": "fixed", "hours": 200},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self._patches = [
            patch(
                "services.payroll_settings_store.GLOBAL_SETTINGS_PATH",
                self._global_path,
            ),
            patch(
                "services.payroll_settings_store.app_data_dir",
                return_value=self._root,
            ),
            patch(
                "services.payroll_settings_store.get_active_tenant_id",
                return_value="tenant_test",
            ),
            patch(
                "services.workplace_hours.load_payroll_settings",
                side_effect=lambda tenant_id=None: __import__(
                    "services.payroll_settings_store", fromlist=["load_payroll_settings"]
                ).load_payroll_settings(tenant_id),
            ),
        ]
        for p in self._patches:
            p.start()

        tenant_path = self._root / "payroll_settings" / "tenant_test.json"
        if tenant_path.is_file():
            tenant_path.unlink()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_seed_tenant_from_global_on_first_load(self) -> None:
        tenant = load_tenant_payroll_settings("tenant_test")
        self.assertEqual(tenant["site_settings"]["한국앰코"]["workplace_hours_policy"]["hours"], 200)

    def test_fallback_global_when_no_site_override(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        resolved = resolve_payroll_calc_settings("없는사업장")
        self.assertEqual(resolved["shutdown_pay_percent"], 70.0)
        self.assertEqual(resolved["shutdown_source"], "tenant")
        self.assertEqual(resolved["hours_source"], "tenant")

    def test_site_shutdown_override(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        save_site_shutdown_pay_percent("한국앰코", 80.0)
        resolved = resolve_payroll_calc_settings("한국앰코")
        self.assertEqual(resolved["shutdown_pay_percent"], 80.0)
        self.assertEqual(resolved["shutdown_source"], "site")
        self.assertTrue(get_shutdown_pay_percent("한국앰코") == 80.0)

    def test_tenant_default_overrides_global(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        save_shutdown_pay_percent(75.0)
        self.assertEqual(get_shutdown_pay_percent(), 75.0)
        resolved = resolve_payroll_calc_settings("새사업장")
        self.assertEqual(resolved["shutdown_pay_percent"], 75.0)
        self.assertEqual(resolved["shutdown_source"], "tenant")

    def test_site_hours_policy_and_clear(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        save_workplace_hours_policy("한국앰코", mode=MODE_FIXED, hours=180)
        pol = policy_for_workplace("한국앰코")
        self.assertEqual(pol["hours"], 180.0)
        clear_site_payroll_settings("한국앰코")
        resolved = resolve_payroll_calc_settings("한국앰코")
        self.assertFalse(resolved["has_site_override"])
        self.assertEqual(resolved["hours_source"], "tenant")

    def test_copy_from_tenant_default(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        save_shutdown_pay_percent(72.0)
        save_default_workplace_hours_policy(mode=MODE_FIXED, hours=210)
        copy_site_settings_from_tenant_default("한국앰코")
        resolved = resolve_payroll_calc_settings("한국앰코")
        self.assertEqual(resolved["shutdown_pay_percent"], 72.0)
        self.assertEqual(resolved["workplace_hours_policy"]["hours"], 210.0)
        self.assertEqual(resolved["shutdown_source"], "site")
        self.assertEqual(resolved["hours_source"], "site")

    def test_apply_to_all_sites(self) -> None:
        load_tenant_payroll_settings("tenant_test")
        save_shutdown_pay_percent(73.0)
        with patch(
            "services.payroll_settings_store.list_config_workplaces",
            return_value=["한국앰코", "부산공장"],
        ):
            count = apply_tenant_defaults_to_all_sites()
        self.assertEqual(count, 2)
        for wp in ("한국앰코", "부산공장"):
            resolved = resolve_payroll_calc_settings(wp)
            self.assertEqual(resolved["shutdown_pay_percent"], 73.0)
            self.assertTrue(resolved["has_site_override"])

    def test_global_fallback_when_tenant_shutdown_unset(self) -> None:
        path = self._root / "payroll_settings" / "tenant_test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "shutdown_pay_percent": None,
                    "default_workplace_hours_policy": {"mode": "fixed", "hours": 209},
                    "site_settings": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.assertEqual(get_shutdown_pay_percent(), DEFAULT_SHUTDOWN_PAY_PERCENT)


if __name__ == "__main__":
    unittest.main()
