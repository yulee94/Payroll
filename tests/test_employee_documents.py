"""Issue #76 개인별 HR 문서관리·만료 알림."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from core.module_store import invalidate_module_db_cache
from core.roles import ROLE_ADMIN, ROLE_FINANCE, ROLE_STAFF
from core.session_service import UserSession
from core.hr.employee_documents import service as docs


class EmployeeDocumentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            patch("core.module_store.app_data_dir", return_value=self.root),
            patch("core.hr.employee_documents.service.app_data_dir", return_value=self.root),
        ]
        for p in self.patches:
            p.start()
        invalidate_module_db_cache()
        self.admin = UserSession("admin1", "tenant-doc", "admin", "관리자", ROLE_ADMIN)
        self.employee = UserSession("emp1", "tenant-doc", "emp", "직원", ROLE_STAFF)
        self.other = UserSession("emp2", "tenant-doc", "other", "타직원", ROLE_STAFF)
        self.finance = UserSession("fin1", "tenant-doc", "finance", "급여담당", ROLE_FINANCE)
        self.file = self.root / "contract.pdf"
        self.file.write_bytes(b"contract-data-v1")

    def tearDown(self) -> None:
        invalidate_module_db_cache()
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_upload_encrypts_metadata_and_requires_review(self) -> None:
        row = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            department="인사",
            position="사원",
            document_type="employment_contract",
            source_path=self.file,
            issued_date="2026-06-01",
        )

        self.assertEqual(row["status"], docs.STATUS_REVIEW_REQUIRED)
        self.assertTrue(row["encrypted"])
        self.assertNotIn("encrypted_path", row)
        stored = next((self.root / docs.MODULE / "tenant-doc" / "files").glob("*.bin"))
        self.assertNotEqual(stored.read_bytes(), b"contract-data-v1")

        approved = docs.approve_document(row["id"], tenant_id="tenant-doc", session=self.admin)
        self.assertIsNotNone(approved)
        self.assertEqual(approved["status"], docs.STATUS_VALID)

        payload, meta = docs.download_document(row["id"], reason="본인 계약서 확인", tenant_id="tenant-doc", session=self.employee)
        self.assertEqual(payload, b"contract-data-v1")
        self.assertEqual(meta["download_history"][-1]["user_id"], "emp1")
        self.assertEqual(meta["download_history"][-1]["reason"], "본인 계약서 확인")

        audit_actions = {a["action"] for a in docs.list_audit_logs(tenant_id="tenant-doc", document_id=row["id"])}
        self.assertIn("document_uploaded", audit_actions)
        self.assertIn("document_approved", audit_actions)
        self.assertIn("document_downloaded", audit_actions)
        self.assertTrue(docs.verify_audit_log_integrity(tenant_id="tenant-doc")["ok"])

    def test_employee_can_only_see_own_documents(self) -> None:
        own = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            document_type="resume",
            source_path=self.file,
        )
        other = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E002",
            employee_user_id="emp2",
            employee_name="김타인",
            document_type="resume",
            source_path=self.file,
        )

        visible = docs.list_employee_documents(tenant_id="tenant-doc", session=self.employee)
        self.assertEqual([r["id"] for r in visible], [own["id"]])
        self.assertIsNone(docs.get_document("missing", tenant_id="tenant-doc", session=self.employee))
        with self.assertRaises(PermissionError):
            docs.get_document(other["id"], tenant_id="tenant-doc", session=self.employee)

    def test_payroll_documents_are_limited_to_finance_or_admin(self) -> None:
        salary = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            document_type="salary_contract",
            source_path=self.file,
            issued_date="2026-01-01",
        )
        docs.approve_document(salary["id"], tenant_id="tenant-doc", session=self.admin)

        # Employee can see/download own salary contract, but unrelated staff cannot.
        self.assertTrue(docs.list_employee_documents(tenant_id="tenant-doc", session=self.employee))
        self.assertEqual(docs.list_employee_documents(tenant_id="tenant-doc", session=self.other), [])

        finance_rows = docs.list_employee_documents(tenant_id="tenant-doc", session=self.finance)
        self.assertEqual(finance_rows[0]["id"], salary["id"])

    def test_expiry_status_notifications_and_versioning(self) -> None:
        exp = (date.today() + timedelta(days=7)).isoformat()
        first = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            document_type="license_certificate",
            document_name="경비지도사",
            source_path=self.file,
            issued_date="2026-01-01",
            expiry_date=exp,
        )
        docs.approve_document(first["id"], tenant_id="tenant-doc", session=self.admin)
        docs.sync_expiration_statuses(tenant_id="tenant-doc")
        rows = docs.list_employee_documents(tenant_id="tenant-doc", session=self.admin)
        self.assertEqual(rows[0]["status"], docs.STATUS_EXPIRING)

        notices = docs.generate_expiry_notifications(tenant_id="tenant-doc")
        self.assertTrue(any(n["document_id"] == first["id"] for n in notices))

        replacement = self.root / "license-v2.pdf"
        replacement.write_bytes(b"license-v2")
        second = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            document_type="license_certificate",
            document_name="경비지도사",
            source_path=replacement,
            issued_date="2026-06-01",
            expiry_date=(date.today() + timedelta(days=400)).isoformat(),
        )
        self.assertEqual(second["version"], 2)
        all_rows = docs.list_employee_documents(tenant_id="tenant-doc", session=self.admin, current_only=False)
        old = next(r for r in all_rows if r["id"] == first["id"])
        self.assertFalse(old["current"])
        self.assertEqual(old["status"], docs.STATUS_RENEWED)

    def test_document_type_policy_rejects_bad_extension_and_missing_expiry(self) -> None:
        bad = self.root / "license.exe"
        bad.write_bytes(b"bad")
        with self.assertRaises(ValueError):
            docs.upload_document(
                tenant_id="tenant-doc",
                session=self.admin,
                employee_id="E001",
                employee_name="홍길동",
                employee_user_id="emp1",
                document_type="license_certificate",
                source_path=bad,
                issued_date="2026-01-01",
                expiry_date="2027-01-01",
            )

    def test_issue78_permission_delete_restore_and_retention_governance(self) -> None:
        row = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            document_type="privacy_consent",
            source_path=self.file,
        )
        docs.approve_document(row["id"], tenant_id="tenant-doc", session=self.admin)

        req = docs.request_document_permission(
            row["id"],
            reason="개인정보 원본 확인 필요",
            scopes=("unmasked_view", "download"),
            tenant_id="tenant-doc",
            session=self.employee,
        )
        self.assertEqual(req["status"], "대기")
        approved = docs.approve_permission_request(req["id"], tenant_id="tenant-doc", session=self.admin)
        self.assertEqual(approved["status"], "승인")
        unmasked = docs.get_document(row["id"], tenant_id="tenant-doc", session=self.employee, unmasked=True)
        self.assertEqual(unmasked["id"], row["id"])

        delete_req = docs.request_delete_document(
            row["id"],
            reason="잘못된 파일 업로드",
            tenant_id="tenant-doc",
            session=self.employee,
        )
        docs.approve_delete_request(delete_req["id"], tenant_id="tenant-doc", session=self.admin)
        hidden = docs.list_employee_documents(tenant_id="tenant-doc", session=self.admin)
        self.assertFalse(any(d["id"] == row["id"] for d in hidden))
        deleted = docs.list_employee_documents(tenant_id="tenant-doc", session=self.admin, include_deleted=True)
        self.assertTrue(any(d["id"] == row["id"] and d["deleted"] for d in deleted))

        restored = docs.restore_document(row["id"], reason="오삭제 복구", tenant_id="tenant-doc", session=self.admin)
        self.assertFalse(restored["deleted"])
        archived = docs.archive_document(
            row["id"],
            reason="분리보관 테스트",
            retention_status="분리 보관",
            tenant_id="tenant-doc",
            session=self.admin,
        )
        self.assertTrue(archived["download_restricted"])

        actions = {a["action"] for a in docs.list_audit_logs(tenant_id="tenant-doc")}
        self.assertIn("permission_requested", actions)
        self.assertIn("permission_approved", actions)
        self.assertIn("document_delete_requested", actions)
        self.assertIn("document_delete_approved", actions)
        self.assertIn("document_restored", actions)
        self.assertIn("retention_policy_changed", actions)

    def test_issue78_required_rules_ocr_esign_integration_and_notification_ack(self) -> None:
        pii_file = self.root / "resume.txt"
        pii_file.write_text("홍길동 900101-1234567 010-1234-5678", encoding="utf-8")
        row = docs.upload_document(
            tenant_id="tenant-doc",
            session=self.admin,
            employee_id="E001",
            employee_user_id="emp1",
            employee_name="홍길동",
            employment_type="정규직",
            document_type="resume",
            source_path=pii_file,
        )
        self.assertTrue(row["contains_personal_data"])
        self.assertTrue(row["masking_applied"])

        gaps = docs.required_document_gaps(
            {"employee_id": "E001", "employee_name": "홍길동", "employment_type": "정규직"},
            tenant_id="tenant-doc",
        )
        self.assertIn("employment_contract", gaps["missing_document_types"])

        ocr = docs.record_ocr_result(
            row["id"],
            extracted_values={"rrn": "900101-1234567", "phone": "010-1234-5678"},
            confidence=0.91,
            tenant_id="tenant-doc",
            session=self.admin,
        )
        self.assertEqual(ocr["masked_values"]["rrn"], "900101-1******")

        esign = docs.record_e_signature_event(
            {"document_id": row["id"], "external_document_id": "esign-1", "signature_status": "completed"},
            tenant_id="tenant-doc",
            session=self.admin,
        )
        self.assertEqual(esign["signature_status"], "completed")
        erp = docs.record_external_integration_event(
            "erp",
            "sync_document",
            status="failed",
            document_id=row["id"],
            failure_reason="timeout",
            tenant_id="tenant-doc",
            session=self.admin,
        )
        self.assertEqual(erp["failure_reason"], "timeout")

        notice = docs.list_notifications(tenant_id="tenant-doc")[0]
        ack = docs.acknowledge_notification(notice["id"], action_note="확인", tenant_id="tenant-doc", session=self.employee)
        self.assertEqual(ack["status"], "조치 완료")
        self.assertTrue(docs.verify_audit_log_integrity(tenant_id="tenant-doc")["ok"])
        with self.assertRaises(ValueError):
            docs.upload_document(
                tenant_id="tenant-doc",
                session=self.admin,
                employee_id="E001",
                employee_name="홍길동",
                employee_user_id="emp1",
                document_type="license_certificate",
                source_path=self.file,
                issued_date="",
                expiry_date="",
            )


if __name__ == "__main__":
    unittest.main()
