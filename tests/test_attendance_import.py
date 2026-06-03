from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.attendance_import import extract_attendance_invoice_rows
from services.payroll_policy_store import save_tenant_payroll_operation_policy


class AttendanceImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._data_dir = Path(self._tmpdir.name) / "app_data"
        self._patch = patch(
            "services.payroll_settings_store.app_data_dir",
            return_value=self._data_dir,
        )
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    def test_late_and_early_leave_columns_are_treated_as_minutes(self) -> None:
        save_tenant_payroll_operation_policy(
            {
                "attendance": {
                    "rounding_minutes": 15,
                    "late_grace_minutes": 5,
                    "early_leave_grace_minutes": 0,
                }
            },
            tenant_id="tenant-a",
        )
        attendance_path = Path(self._tmpdir.name) / "attendance.csv"
        attendance_path.write_text(
            "성명,근무시간,지각분,조퇴분,연장\n홍길동,8,10,5,1\n",
            encoding="utf-8-sig",
        )

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="Site A",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "홍길동")
        self.assertAlmostEqual(row["work_days"], 8.0)
        self.assertAlmostEqual(row["early_leave_hours"], 0.25)
        self.assertAlmostEqual(row["ot_hours"], 1.0)


if __name__ == "__main__":
    unittest.main()
