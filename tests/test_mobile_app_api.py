"""Worker mobile app API vertical-slice tests."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.mobile import app_api, store
from core.module_store import invalidate_module_db_cache
from core.session_service import UserSession
from core.user_store import register_user
from core.workflow import service as wf_svc


class MobileAppApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "mobile_api_tenant"
        root = Path(self._tmpdir)
        self._patches = [
            patch("core.paths.app_data_dir", lambda: root),
            patch("core.module_store.app_data_dir", lambda: root),
            patch("core.hr.employee_documents.service.app_data_dir", lambda: root),
            patch("core.user_store.USERS_FILE", root / "users" / "registry.json"),
            patch("core.workflow.store.WORKFLOW_ROOT", root / "workflow"),
        ]
        for p in self._patches:
            p.start()
        invalidate_module_db_cache()
        self.manager = register_user(
            tenant_id=self._tenant,
            username="manager",
            password="secret1",
            display_name="관리자",
            role="admin",
        )
        self.worker = register_user(
            tenant_id=self._tenant,
            username="worker",
            password="secret1",
            display_name="박철수",
            role="staff",
            org_unit_id="dept-hr",
            manager_user_id=self.manager.user_id,
        )
        self.worker_login = app_api.mobile_login(
            {
                "tenant_id": self._tenant,
                "username": "worker",
                "password": "secret1",
                "device_uid": "ios-001",
            }
        )
        self.worker_token = self.worker_login["token"]

    def tearDown(self) -> None:
        invalidate_module_db_cache()
        for p in reversed(self._patches):
            p.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _register_worker_device_and_consents(self, *, platform: str = "ios") -> None:
        app_api.register_mobile_device(
            {
                "device_uid": f"{platform}-001",
                "platform": platform,
                "push_token": f"ExpoPushToken[{platform}]",
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        app_api.record_mobile_consents(
            {
                "device_uid": f"{platform}-001",
                "consents": [
                    {"kind": "privacy", "granted": True},
                    {"kind": "location", "granted": True},
                    {"kind": "biometric", "granted": True},
                    {"kind": "notifications", "granted": True},
                    {"kind": "payroll", "granted": True},
                ],
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )

    def test_ios_device_only_biometric_check_in_is_verified(self) -> None:
        self._register_worker_device_and_consents(platform="ios")
        result = app_api.mobile_check_attendance(
            {
                "device_uid": "ios-001",
                "site_name": "화성 정비사업장",
                "event_type": "clock_in",
                "event_at": "2026-06-04T08:55:00",
                "latitude": 37.1996,
                "longitude": 126.8310,
                "biometric_kind": "face",
                "biometric_ok": True,
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["event"]["status"], "verified")
        self.assertTrue(result["event"]["biometric_ref"].startswith("device://local-auth/ios/"))

    def test_mobile_contract_declares_privacy_defaults_and_platform_endpoints(self) -> None:
        contract = app_api.mobile_api_contract()
        paths = {row["path"] for row in contract["endpoints"]}
        self.assertIn("/mobile/v1/attendance/check", paths)
        self.assertIn("/mobile/v1/location/geofence-event", paths)
        self.assertIn("/mobile/v1/payroll/{period}", paths)
        self.assertIn("/mobile/v1/hr/documents", paths)
        self.assertIn("/mobile/v1/hr/notifications/{id}/ack", paths)
        self.assertEqual(contract["privacy_defaults"]["biometric_storage"], "device_only_pass_fail")
        self.assertEqual(contract["privacy_defaults"]["payroll_visibility"], "own_employee_only")

    def test_mobile_hr_document_upload_list_and_ack_notification(self) -> None:
        self._register_worker_device_and_consents(platform="ios")
        uploaded = app_api.upload_mobile_hr_document(
            {
                "employee_id": "E-MOB-1",
                "document_type": "resume",
                "file_name": "resume.txt",
                "file_bytes": b"mobile resume 900101-1234567",
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertTrue(uploaded["requires_approval"])
        listed = app_api.list_mobile_hr_documents(tenant_id=self._tenant, token=self.worker_token)
        self.assertEqual(listed["documents"][0]["id"], uploaded["document"]["id"])
        self.assertTrue(listed["notifications"])
        acked = app_api.ack_mobile_hr_document_notification(
            listed["notifications"][0]["id"],
            tenant_id=self._tenant,
            token=self.worker_token,
            action_note="앱에서 확인",
        )
        self.assertEqual(acked["notification"]["status"], "조치 완료")

    def test_unauthorized_exit_alerts_manager_and_can_be_acknowledged(self) -> None:
        self._register_worker_device_and_consents(platform="android")
        app_api.mobile_check_attendance(
            {
                "device_uid": "android-001",
                "site_name": "화성 정비사업장",
                "event_type": "clock_in",
                "event_at": "2026-06-04T09:00:00",
                "latitude": 37.1996,
                "longitude": 126.8310,
                "biometric_kind": "fingerprint",
                "biometric_ok": True,
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        exit_result = app_api.mobile_geofence_event(
            {
                "device_uid": "android-001",
                "site_name": "화성 정비사업장",
                "transition": "exit",
                "detected_at": "2026-06-04T10:00:00",
                "latitude": 37.25,
                "longitude": 126.9,
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertFalse(exit_result["authorized"])
        alert = exit_result["alert"]
        self.assertEqual(alert["manager_user_id"], self.manager.user_id)
        self.assertTrue(alert["worker_warning_sent"])
        self.assertTrue(alert["manager_alert_sent"])

        manager_token = app_api.mobile_login(
            {
                "tenant_id": self._tenant,
                "username": "manager",
                "password": "secret1",
            }
        )["token"]
        listed = app_api.list_mobile_manager_alerts(
            tenant_id=self._tenant,
            token=manager_token,
        )
        self.assertEqual(len(listed["alerts"]), 1)
        acked = app_api.ack_mobile_alert(
            alert["id"],
            tenant_id=self._tenant,
            token=manager_token,
            comment="확인",
        )
        self.assertEqual(acked["alert"]["status"], "acknowledged")

    def test_approved_attendance_request_suppresses_exit_alert(self) -> None:
        self._register_worker_device_and_consents(platform="ios")
        app_api.mobile_check_attendance(
            {
                "device_uid": "ios-001",
                "site_name": "화성 정비사업장",
                "event_type": "clock_in",
                "event_at": "2026-06-04T09:00:00",
                "latitude": 37.1996,
                "longitude": 126.8310,
                "biometric_kind": "face",
                "biometric_ok": True,
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        created = app_api.create_mobile_attendance_request(
            {
                "title": "출장신청서",
                "attendance_type": "출장",
                "start_at": "2026-06-04T09:30:00",
                "end_at": "2026-06-04T12:00:00",
                "site_name": "화성 정비사업장",
                "reason": "고객사 방문",
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertTrue(created["submitted"])
        wf_svc.approve_document(
            self._tenant,
            created["document"]["id"],
            session=UserSession.from_record(self.manager),
        )
        synced = app_api.sync_mobile_absence_windows(
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertEqual(len(synced["windows"]), 1)

        exit_result = app_api.mobile_geofence_event(
            {
                "device_uid": "ios-001",
                "site_name": "화성 정비사업장",
                "transition": "exit",
                "detected_at": "2026-06-04T10:00:00",
                "latitude": 37.25,
                "longitude": 126.9,
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertTrue(exit_result["authorized"])
        self.assertIsNone(exit_result["alert"])

    def test_payroll_summary_returns_only_logged_in_worker_record(self) -> None:
        self._register_worker_device_and_consents(platform="ios")
        with patch(
            "core.mobile.app_api._load_payroll_records_for_mobile",
            return_value=[
                {
                    "name": "박철수",
                    "gross_pay": 3_000_000,
                    "net_pay": 2_700_000,
                    "total_deduction": 300_000,
                    "income_tax": 100_000,
                    "local_income_tax": 10_000,
                    "remaining_annual_leave": 7.5,
                },
                {
                    "name": "다른직원",
                    "gross_pay": 9_999_999,
                    "net_pay": 9_999_999,
                },
            ],
        ):
            summary = app_api.get_mobile_payroll_summary(
                "2026-06",
                tenant_id=self._tenant,
                token=self.worker_token,
            )
        self.assertEqual(summary["status"], "finalized")
        self.assertEqual(summary["employee_name"], "박철수")
        self.assertEqual(summary["gross_pay"], 3_000_000)
        self.assertEqual(summary["tax"], 110_000)


if __name__ == "__main__":
    unittest.main()
