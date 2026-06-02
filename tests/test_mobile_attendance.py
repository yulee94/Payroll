"""모바일 출퇴근·급여 연동 스캐폴드 단위 테스트."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.mobile import payroll_source, profile, store, sync
from core.mobile.models import AttendanceEvent, SiteGeofence
from core.session_service import UserSession, logout


class MobileAttendanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "test_mobile_tenant"
        self._patch_data = patch(
            "core.paths.app_data_dir",
            lambda: Path(self._tmpdir),
        )
        self._patch_data.start()
        session_service._session = UserSession(  # noqa: SLF001
            user_id="u1",
            tenant_id=self._tenant,
            username="tester",
            display_name="테스터",
            role="staff",
        )

    def tearDown(self) -> None:
        self._patch_data.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_geofence_contains(self) -> None:
        fence = SiteGeofence(
            id="g1",
            site_name="테스트 현장",
            latitude=37.0,
            longitude=127.0,
            radius_m=200,
        )
        self.assertTrue(fence.contains(37.0005, 127.0005))
        self.assertFalse(fence.contains(38.0, 128.0))

    def test_ingest_verified_event(self) -> None:
        store.ensure_seed(self._tenant)
        payload = {
            "employee_name": "박철수",
            "site_name": "화성 정비사업장",
            "event_type": "clock_in",
            "event_at": "2026-05-01T08:00:00",
            "latitude": 37.1996,
            "longitude": 126.8310,
            "biometric_kind": "fingerprint",
            "biometric_ref": "vault://bio/demo/park001",
        }
        ev = sync.ingest_attendance_event(payload, tenant_id=self._tenant)
        self.assertEqual(ev.status, "verified")
        self.assertTrue(ev.geofence_ok)
        self.assertTrue(ev.biometric_ok)

    def test_ingest_rejected_outside_geofence(self) -> None:
        store.ensure_seed(self._tenant)
        payload = {
            "employee_name": "박철수",
            "site_name": "화성 정비사업장",
            "event_type": "clock_in",
            "event_at": "2026-05-02T08:00:00",
            "latitude": 35.0,
            "longitude": 129.0,
            "biometric_kind": "fingerprint",
            "biometric_ref": "vault://bio/demo/park001",
        }
        ev = sync.ingest_attendance_event(payload, tenant_id=self._tenant)
        self.assertEqual(ev.status, "rejected")
        self.assertFalse(ev.geofence_ok)

    def test_aggregate_and_invoice_rows(self) -> None:
        store.ensure_seed(self._tenant)
        rows, summaries = payroll_source.build_attendance_payroll_inputs(
            "2026-05",
            tenant_id=self._tenant,
        )
        # 시드 데이터는 전월 이벤트 — 빈 집계 가능
        self.assertIsInstance(rows, list)
        self.assertIsInstance(summaries, list)

        # 인위적 verified 쌍 추가 후 집계
        store.append_event(
            AttendanceEvent(
                id="",
                employee_name="테스트",
                site_name="화성 정비사업장",
                event_type="clock_in",
                event_at="2026-05-10T09:00:00",
                latitude=37.1996,
                longitude=126.8310,
                status="verified",
                geofence_ok=True,
                biometric_ok=True,
            ),
            self._tenant,
        )
        store.append_event(
            AttendanceEvent(
                id="",
                employee_name="테스트",
                site_name="화성 정비사업장",
                event_type="clock_out",
                event_at="2026-05-10T18:00:00",
                latitude=37.1996,
                longitude=126.8310,
                status="verified",
                geofence_ok=True,
                biometric_ok=True,
            ),
            self._tenant,
        )
        summaries = payroll_source.aggregate_period_hours("2026-05", tenant_id=self._tenant)
        self.assertGreaterEqual(len(summaries), 1)
        test_sum = next(s for s in summaries if s.employee_name == "테스트")
        self.assertAlmostEqual(test_sum.work_hours, 9.0, places=1)
        rows = payroll_source.summaries_to_invoice_rows(summaries)
        self.assertEqual(rows[0]["_payroll_source"], payroll_source.PAYROLL_SOURCE_ATTENDANCE)

    def test_mobile_profile_update(self) -> None:
        store.ensure_seed(self._tenant)
        updated = profile.update_employee_mobile_profile(
            "김민수",
            {"email": "kim@test.com", "payslip_email": "kim@test.com"},
            tenant_id=self._tenant,
        )
        self.assertEqual(updated["email"], "kim@test.com")
        got = profile.get_employee_mobile_profile("김민수", tenant_id=self._tenant)
        self.assertEqual(got["payslip_email"], "kim@test.com")


if __name__ == "__main__":
    unittest.main()
