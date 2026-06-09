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

    def test_aggregates_rows_by_normalized_name_with_grace_and_rounding(self) -> None:
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
        attendance_path = Path(self._tmpdir.name) / "attendance_grouped.csv"
        attendance_path.write_text(
            "성명,소속,근무지,근무시간,지각분,조퇴분,연장,야간,특근,연차,결근\n"
            "홍 길동,Payroll,Site A,4,10,0,0.5,1,0,0,0\n"
            "홍길동,Payroll,Site A,4,0,5,0.5,0,2,1,0.5\n",
            encoding="utf-8-sig",
        )

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="Site A",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "홍 길동")
        self.assertEqual(row["dept"], "Payroll")
        self.assertEqual(row["workplace"], "Site A")
        self.assertEqual(row["_attendance_days"], 2)
        self.assertTrue(row["_attendance_input"])
        self.assertAlmostEqual(row["work_days"], 8.0)
        self.assertAlmostEqual(row["early_leave_hours"], 0.25)
        self.assertAlmostEqual(row["ot_hours"], 1.0)
        self.assertAlmostEqual(row["night_hours"], 1.0)
        self.assertAlmostEqual(row["special_hours"], 2.0)
        self.assertAlmostEqual(row["leave_days"], 1.0)
        self.assertAlmostEqual(row["unpaid_days"], 0.5)

    def test_recognizes_alternate_attendance_header_keywords(self) -> None:
        save_tenant_payroll_operation_policy(
            {
                "attendance": {
                    "rounding_minutes": 15,
                    "late_grace_minutes": 0,
                    "early_leave_grace_minutes": 0,
                }
            },
            tenant_id="tenant-a",
        )
        attendance_path = Path(self._tmpdir.name) / "attendance_alt_headers.csv"
        attendance_path.write_text(
            "직원성명,근무부서,현장명,총근로시간,지각분,조퇴분,연장근로,심야시간,특근시간,휴가일수,결근일수\n"
            "김철수,생산,한국앰코,8,0,30,1,2,3,0.5,1\n",
            encoding="utf-8-sig",
        )

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="기본현장",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "김철수")
        self.assertEqual(row["dept"], "생산")
        self.assertEqual(row["workplace"], "한국앰코")
        self.assertAlmostEqual(row["work_days"], 8.0)
        self.assertAlmostEqual(row["early_leave_hours"], 0.5)
        self.assertAlmostEqual(row["ot_hours"], 1.0)
        self.assertAlmostEqual(row["night_hours"], 2.0)
        self.assertAlmostEqual(row["special_hours"], 3.0)
        self.assertAlmostEqual(row["leave_days"], 0.5)
        self.assertAlmostEqual(row["unpaid_days"], 1.0)

    def test_symbol_calendar_attendance_marks_are_aggregated(self) -> None:
        save_tenant_payroll_operation_policy(
            {
                "attendance": {
                    "rounding_minutes": 15,
                    "late_grace_minutes": 0,
                    "early_leave_grace_minutes": 0,
                }
            },
            tenant_id="tenant-a",
        )
        attendance_path = Path(self._tmpdir.name) / "attendance_symbol_calendar.csv"
        attendance_path.write_text(
            "성명,소속,근무지,5월 1일,2026-05-02,3일,4일,5일\n"
            "박문자,생산,한국앰코,●,●,반차,결근,◐\n",
            encoding="utf-8-sig",
        )

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="기본현장",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "박문자")
        self.assertEqual(row["dept"], "생산")
        self.assertEqual(row["workplace"], "한국앰코")
        self.assertEqual(row["_attendance_days"], 5)
        self.assertAlmostEqual(row["work_days"], 24.0)
        self.assertAlmostEqual(row["leave_days"], 0.5)
        self.assertAlmostEqual(row["unpaid_days"], 1.0)
        self.assertFalse(result.warnings)

    def test_symbol_total_work_column_is_read_as_full_day(self) -> None:
        save_tenant_payroll_operation_policy(
            {
                "attendance": {
                    "rounding_minutes": 15,
                    "late_grace_minutes": 0,
                    "early_leave_grace_minutes": 0,
                }
            },
            tenant_id="tenant-a",
        )
        attendance_path = Path(self._tmpdir.name) / "attendance_symbol_total.csv"
        attendance_path.write_text(
            "근무자,총근로시간\n김표식,●\n",
            encoding="utf-8-sig",
        )

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="기본현장",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "김표식")
        self.assertEqual(row["_attendance_days"], 1)
        self.assertAlmostEqual(row["work_days"], 8.0)

    def test_xlsx_symbol_calendar_marks_are_supported(self) -> None:
        from openpyxl import Workbook

        save_tenant_payroll_operation_policy(
            {
                "attendance": {
                    "rounding_minutes": 15,
                    "late_grace_minutes": 0,
                    "early_leave_grace_minutes": 0,
                }
            },
            tenant_id="tenant-a",
        )
        attendance_path = Path(self._tmpdir.name) / "attendance_symbol_calendar.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["근무자", "1일", "2일", "3일"])
        ws.append(["엑셀표식", "●", "○", "✕"])
        wb.save(attendance_path)

        result = extract_attendance_invoice_rows(
            attendance_path,
            workplace="기본현장",
            tenant_id="tenant-a",
        )

        self.assertEqual(result.count, 1)
        row = result.invoice_rows[0]
        self.assertEqual(row["name"], "엑셀표식")
        self.assertEqual(row["_attendance_days"], 3)
        self.assertAlmostEqual(row["work_days"], 16.0)
        self.assertAlmostEqual(row["unpaid_days"], 1.0)


if __name__ == "__main__":
    unittest.main()
