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
                "mfa_otp": "123456",
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
                "push_token": (f"apns-{platform}-token" if platform == "ios" else f"fcm-{platform}-token"),
                "branch_id": "branch-review-001",
                "app_version": "0.1.0",
                "os_version": "18.0",
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
        self.assertEqual(contract["surface"]["name"], "Mobile App API")
        self.assertIn("Web Admin API", contract["api_surfaces"]["web_admin"]["name"])
        self.assertIn("/api/v1/login", paths)
        self.assertIn("/api/v1/branches", paths)
        self.assertIn("/api/v1/tasks", paths)
        self.assertIn("/api/v2/tasks", paths)
        self.assertIn("/api/v1/config", paths)
        self.assertIn("/api/v1/attendance/check", paths)
        self.assertIn("/api/v1/location/geofence-event", paths)
        self.assertIn("/api/v1/push/send", paths)
        self.assertIn("/api/v1/sync/offline", paths)
        self.assertIn("/api/v1/payroll/{period}", paths)
        self.assertIn("/api/v1/hr/documents", paths)
        self.assertIn("/api/v1/hr/notifications/{id}/ack", paths)
        self.assertNotIn("/mobile/v1/attendance/check", paths)
        self.assertEqual(contract["privacy_defaults"]["biometric_storage"], "device_only_pass_fail")
        self.assertEqual(contract["privacy_defaults"]["payroll_visibility"], "own_employee_only")
        self.assertEqual(contract["legacy_aliases"]["replacement_base_path"], "/api/v1")
        security = contract["security"]
        self.assertEqual(
            security["login_flow"],
            ["company_account_login", "otp_or_mfa", "device_registration", "branch_permission_check", "app_use"],
        )
        self.assertIn("plain_password", security["forbidden_local_storage"])
        self.assertIn("resident_registration_number", security["forbidden_local_storage"])
        self.assertIn("card_number", security["forbidden_local_storage"])
        self.assertIn("long_lived_admin_token", security["forbidden_local_storage"])
        self.assertIn("iOS Keychain", security["required_encrypted_storage_when_needed"])
        self.assertIn("Android Keystore", security["required_encrypted_storage_when_needed"])
        self.assertTrue(security["push_notifications"]["required"])
        self.assertIn("payment_settlement", security["push_notifications"]["event_kinds"])
        self.assertTrue(security["offline_mode"]["required"])
        self.assertEqual(security["offline_mode"]["server_idempotency_fields"], ["request_id", "sync_id", "created_at", "device_id"])

    def test_mobile_login_requires_mfa(self) -> None:
        with self.assertRaises(PermissionError):
            app_api.mobile_login(
                {
                    "tenant_id": self._tenant,
                    "username": "worker",
                    "password": "secret1",
                    "device_uid": "ios-002",
                }
            )

    def test_mobile_app_config_declares_server_version_policy(self) -> None:
        config = app_api.get_mobile_app_config("0.0.1")
        policy = config["version_policy"]

        self.assertIn("minimum_supported_version", policy)
        self.assertIn("latest_version", policy)
        self.assertIn("force_update_required", policy)
        self.assertIn("maintenance_mode", policy)
        self.assertIn("notice_message", policy)
        self.assertTrue(policy["force_update_required"])
        self.assertEqual(policy["example"]["current_app_version"], "1.0.0")
        self.assertEqual(policy["example"]["minimum_supported_version"], "1.1.0")
        self.assertIn("test_account", config["review_metadata_required"])

    def test_mobile_branches_and_versioned_tasks_are_available(self) -> None:
        self._register_worker_device_and_consents(platform="android")
        branches = app_api.list_mobile_branches(tenant_id=self._tenant, token=self.worker_token)
        self.assertEqual(branches["version"], "v1")
        self.assertTrue(branches["branches"])
        self.assertIn("branch_id", branches["branches"][0])

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
        app_api.mobile_geofence_event(
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
        manager_token = app_api.mobile_login(
            {
                "tenant_id": self._tenant,
                "username": "manager",
                "password": "secret1",
                "mfa_otp": "123456",
            }
        )["token"]

        tasks_v1 = app_api.list_mobile_tasks_v1(tenant_id=self._tenant, token=manager_token)
        tasks_v2 = app_api.list_mobile_tasks_v2(tenant_id=self._tenant, token=manager_token)
        self.assertEqual(tasks_v1["version"], "v1")
        self.assertEqual(tasks_v2["version"], "v2")
        self.assertEqual(tasks_v1["tasks"][0]["task_type"], "geofence_alert")
        self.assertIn("branch_id", tasks_v1["tasks"][0])
        self.assertEqual(tasks_v2["tasks"][0]["api_version"], "v2")
        self.assertIn("permissions", tasks_v2["tasks"][0])

    def test_device_registration_persists_push_token_fields_and_push_queue(self) -> None:
        self._register_worker_device_and_consents(platform="ios")
        devices = store.list_devices(tenant_id=self._tenant, user_id=self.worker.user_id)

        self.assertEqual(len(devices), 1)
        device = devices[0].to_dict()
        self.assertEqual(device["user_id"], self.worker.user_id)
        self.assertEqual(device["branch_id"], "branch-review-001")
        self.assertTrue(device["device_uid"])
        self.assertEqual(device["push_token"], "apns-ios-token")
        self.assertEqual(device["platform"], "ios")
        self.assertEqual(device["app_version"], "0.1.0")
        self.assertTrue(device["last_active_at"])

        pushed = app_api.send_mobile_push_notification(
            {
                "event_kind": "work_assignment",
                "user_id": self.worker.user_id,
                "branch_id": "branch-review-001",
                "title": "작업 배정",
                "body": "신규 작업이 배정되었습니다.",
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )
        self.assertTrue(pushed["ok"])
        self.assertEqual(pushed["queued"], 1)
        self.assertEqual(pushed["notifications"][0]["provider"], "APNs")
        self.assertEqual(pushed["notifications"][0]["event_kind"], "work_assignment")

    def test_offline_sync_deduplicates_same_purchase_request(self) -> None:
        self._register_worker_device_and_consents(platform="android")
        payload = {
            "request_type": "purchase_request",
            "branch_id": "branch-review-001",
            "payload": {
                "title": "안전장갑 구매요청",
                "summary": "현장 안전장갑 보충",
                "items": [{"item_name": "안전장갑", "quantity": 10, "unit_price": 5000}],
            },
        }
        synced = app_api.sync_mobile_offline_requests(
            {
                "requests": [
                    {"request_id": "req-1", "sync_id": "sync-1", "created_at": "2026-06-09T09:00:00Z", "device_id": "android-001", **payload},
                    {"request_id": "req-2", "sync_id": "sync-2", "created_at": "2026-06-09T09:01:00Z", "device_id": "android-001", **payload},
                    {"request_id": "req-3", "sync_id": "sync-3", "created_at": "2026-06-09T09:02:00Z", "device_id": "android-001", **payload},
                ]
            },
            tenant_id=self._tenant,
            token=self.worker_token,
        )

        self.assertTrue(synced["ok"])
        self.assertEqual(synced["processed"], 1)
        self.assertEqual(synced["duplicates"], 2)
        self.assertFalse(synced["results"][0]["duplicate"])
        self.assertTrue(synced["results"][1]["duplicate"])
        self.assertEqual(len(store.list_offline_sync_records(tenant_id=self._tenant, device_id="android-001")), 1)

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
                "mfa_otp": "123456",
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
