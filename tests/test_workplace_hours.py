"""
tests/test_workplace_hours.py - 사업장별 월 기본근로시간·산출
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.workplace_hours import (
    MODE_FIXED,
    MODE_INVOICE_WORK,
    apply_monthly_hours_to_invoice,
    normalize_policy,
    policy_for_workplace,
    resolve_monthly_work_hours,
)
from services.payroll_settings_store import (
    save_default_workplace_hours_policy,
    save_workplace_hours_policy,
)


class WorkplaceHoursTests(unittest.TestCase):
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
                    "workplace_hours_policies": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._patches = [
            patch("services.payroll_settings_store.GLOBAL_SETTINGS_PATH", self._global_path),
            patch("services.payroll_settings_store.app_data_dir", return_value=self._root),
            patch("services.payroll_settings_store.get_active_tenant_id", return_value="t_hours"),
        ]
        for p in self._patches:
            p.start()
        tenant_path = self._root / "payroll_settings" / "t_hours.json"
        if tenant_path.is_file():
            tenant_path.unlink()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_normalize_optional_daily_and_break(self) -> None:
        pol = normalize_policy(
            {"mode": "fixed", "hours": 209, "daily_hours": 8, "break_minutes": 60}
        )
        self.assertEqual(pol["daily_hours"], 8.0)
        self.assertEqual(pol["break_minutes"], 60.0)

    def test_resolve_fixed_policy(self) -> None:
        save_workplace_hours_policy("테스트장", mode=MODE_FIXED, hours=200)
        inv = {"base_days": 209, "work_days": 180}
        hours, src = resolve_monthly_work_hours(inv, "테스트장")
        self.assertEqual(hours, 200.0)
        self.assertIn("고정", src)

    def test_resolve_invoice_work_mode(self) -> None:
        save_workplace_hours_policy("청구장", mode=MODE_INVOICE_WORK, hours=209)
        inv = {"base_days": 209, "work_days": 195}
        hours, _ = resolve_monthly_work_hours(inv, "청구장")
        self.assertEqual(hours, 195.0)

    def test_apply_monthly_hours_to_invoice(self) -> None:
        save_default_workplace_hours_policy(mode=MODE_FIXED, hours=209)
        inv: dict = {"work_days": 0, "base_days": 209}
        h = apply_monthly_hours_to_invoice(inv, "")
        self.assertEqual(h, 209.0)
        self.assertEqual(inv["_monthly_work_hours"], 209.0)

    def test_fallback_tenant_default(self) -> None:
        save_default_workplace_hours_policy(mode=MODE_FIXED, hours=210)
        pol = policy_for_workplace("미등록사업장")
        self.assertEqual(pol["hours"], 210.0)


if __name__ == "__main__":
    unittest.main()
