"""tests/test_edi_insurance.py - 사대보험 EDI 보험료 Provider·급여 반영."""

from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.payroll import edi_insurance as edi
from core.payroll_calc_rules import resolve_social_insurance
from services.payroll_settings_store import save_edi_insurance_config
from utils import calc_employment_insurance


class TestEdiInsurance(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        root = Path(self._tmpdir)
        self._settings_dir = root / "payroll_settings"
        self._settings_dir.mkdir(parents=True)
        (self._settings_dir / "t_edi.json").write_text(
            '{"edi_insurance":{"use_edi_premiums":false}}',
            encoding="utf-8",
        )

        self._root_patcher = patch.object(edi, "_EDI_ROOT", root / "edi_insurance")
        self._root_patcher.start()
        self._tenant_patcher = patch.object(edi, "session_tenant_id", return_value="t_edi")
        self._tenant_patcher.start()
        self._store_patcher = patch(
            "services.payroll_settings_store.app_data_dir", return_value=root
        )
        self._store_patcher.start()
        self._active_patcher = patch(
            "services.payroll_settings_store.get_active_tenant_id", return_value="t_edi"
        )
        self._active_patcher.start()
        self.addCleanup(self._root_patcher.stop)
        self.addCleanup(self._tenant_patcher.stop)
        self.addCleanup(self._store_patcher.stop)
        self.addCleanup(self._active_patcher.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_csv_import_and_lookup(self) -> None:
        csv_path = Path(self._tmpdir) / "edi.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "사번",
                    "성명",
                    "급여월",
                    "국민연금",
                    "건강보험",
                    "고용보험",
                ]
            )
            w.writerow(["E01", "홍길동", "2026-05", "100000", "50000", "30000"])

        summary = edi.import_premiums_csv(csv_path, tenant_id="t_edi")
        self.assertEqual(summary["imported_count"], 1)

        rec = edi.get_stored_premium(
            period="2026-05",
            employee_id="E01",
            tenant_id="t_edi",
        )
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.national_pension, 100_000)
        self.assertEqual(rec.health_insurance, 50_000)
        self.assertEqual(rec.employment_insurance, 30_000)
        self.assertGreater(rec.long_term_care, 0)

    def test_apply_to_payroll_when_enabled(self) -> None:
        edi.add_premium_manual(
            employee_id="E02",
            employee_name="김철수",
            period="2026-06",
            national_pension=80_000,
            health_insurance=40_000,
            long_term_care=5_000,
            employment_insurance=20_000,
            tenant_id="t_edi",
        )
        save_edi_insurance_config(use_edi_premiums=True, tenant_id="t_edi")

        gross = 2_500_000
        inv = {"name": "김철수", "gross_pay": gross}
        resolve_social_insurance(
            inv,
            identity="900101-1",
            payroll_period="2026-06",
            emp_roster={"사번": "E02", "성명": "김철수"},
            tenant_id="t_edi",
        )
        self.assertTrue(inv.get("edi_premium_source"))
        self.assertEqual(inv.get("edi_premium_badge"), "EDI 조회")
        self.assertEqual(inv["national_pension"], 80_000)
        self.assertEqual(inv["health_insurance"], 40_000)
        self.assertEqual(inv["employment_insurance"], 20_000)
        self.assertNotEqual(inv["employment_insurance"], calc_employment_insurance(gross))

    def test_fallback_calculated_when_edi_off(self) -> None:
        save_edi_insurance_config(use_edi_premiums=False, tenant_id="t_edi")
        edi.add_premium_manual(
            employee_id="E03",
            employee_name="이영희",
            period="2026-06",
            national_pension=999_999,
            tenant_id="t_edi",
        )
        gross = 2_000_000
        inv = {"name": "이영희", "gross_pay": gross}
        resolve_social_insurance(
            inv,
            identity="850101-2",
            payroll_period="2026-06",
            emp_roster={"사번": "E03", "성명": "이영희"},
            tenant_id="t_edi",
        )
        self.assertFalse(inv.get("edi_premium_source"))
        self.assertEqual(inv["employment_insurance"], calc_employment_insurance(gross))

    def test_tenant_isolation(self) -> None:
        edi.add_premium_manual(
            employee_id="E99",
            employee_name="타테넌트",
            period="2026-05",
            national_pension=1,
            tenant_id="other_tenant",
        )
        rec = edi.get_stored_premium(
            period="2026-05",
            employee_id="E99",
            tenant_id="t_edi",
        )
        self.assertIsNone(rec)

    def test_local_provider_raises_without_data(self) -> None:
        provider = edi.LocalStoredEdiProvider()
        with self.assertRaises(LookupError):
            provider.lookup_premiums("X", "", "", "2099-01")

    def test_edi_web_service_stub_not_live(self) -> None:
        stub = edi.EdiWebServiceProvider(endpoint_url="https://example.invalid")
        self.assertFalse(stub.is_live())
        with self.assertRaises(NotImplementedError):
            stub.lookup_premiums("1", "", "", "2026-05")


if __name__ == "__main__":
    unittest.main()
