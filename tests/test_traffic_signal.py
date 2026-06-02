"""tests/test_traffic_signal.py - HR 신호등 (주민번호 매칭)"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.hr import traffic_signal as sig


class TestRrnNormalize(unittest.TestCase):
    def test_normalize_with_dash(self) -> None:
        self.assertEqual(sig.normalize_rrn("670204-2447413"), "6702042447413")

    def test_invalid_length(self) -> None:
        self.assertIsNone(sig.normalize_rrn("123456"))

    def test_mask(self) -> None:
        self.assertEqual(sig.mask_rrn("6702042447413"), "670204-2******")


class TestTrafficSignalRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._reg_path = Path(self._tmpdir) / "registry.json"
        patcher = patch.object(sig, "_REGISTRY_PATH", self._reg_path)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_register_and_lookup_cross_tenant(self) -> None:
        sig.register_resign_signal(
            rrn="6702042447413",
            tenant_id="coss",
            employee_name="홍길동",
            severity="yellow",
            category="근태",
            summary="무단결근 3회",
            case_id="c1",
            resign_date="2026-05-31",
        )
        prof = sig.lookup_by_rrn("670204-2447413")
        assert prof is not None
        self.assertEqual(prof.status, "yellow")
        self.assertEqual(len(prof.issues), 1)
        self.assertEqual(prof.issues[0].tenant_id, "coss")

        prof2 = sig.lookup_by_rrn("6702042447413")
        assert prof2 is not None
        self.assertEqual(prof2.status, "yellow")

    def test_persist_after_resign(self) -> None:
        sig.record_hire_event(
            rrn="9001011234567",
            tenant_id="elso",
            employee_name="김철수",
            hire_date="2024-01-01",
        )
        sig.record_resign_event(
            rrn="9001011234567",
            tenant_id="elso",
            employee_name="김철수",
            resign_date="2026-06-01",
        )
        prof = sig.lookup_by_rrn("9001011234567")
        assert prof is not None
        self.assertFalse(prof.active_employment)
        self.assertEqual(prof.employment_history[-1].resign_date, "2026-06-01")

    @patch("core.access_control.load_roster_rows_secured")
    def test_find_rrn_duplicate_names(self, mock_rows) -> None:
        mock_rows.return_value = [
            {"성명": "박민수", "주민번호": "800101-1000001"},
            {"성명": "박민수", "주민번호": "800101-2000002"},
        ]
        self.assertIsNone(sig.find_rrn_for_employee_name("박민수", tenant_id="coss"))
        mock_rows.return_value = [{"성명": "박민수", "주민번호": "800101-1000001"}]
        self.assertEqual(
            sig.find_rrn_for_employee_name("박민수", tenant_id="coss"),
            "8001011000001",
        )


if __name__ == "__main__":
    unittest.main()
