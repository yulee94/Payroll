"""Business-trip workflow lifecycle integration regressions."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import (
    DOC_STATUS_APPROVED,
    DOC_STATUS_CANCELLED,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_REJECTED,
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
    DOC_TYPE_GENERAL,
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_NOT_APPLICABLE,
    KPI_REFLECTION_READY,
    TASK_COMPLETED,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_PLANNED,
)
from core.workflow.store import _load_raw, _save_raw


class BusinessTripWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "trip_workflow_integration"
        self._patch_root = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_root.start()

    def tearDown(self) -> None:
        self._patch_root.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self, uid: str = "requester", role: str = "admin") -> UserSession:
        return UserSession(
            user_id=uid,
            tenant_id=self._tenant,
            username=uid,
            display_name=uid,
            role=role,
        )

    def _create_business_trip_document(self, *, session: UserSession | None = None) -> dict:
        sess = session or self._session()
        return wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_BUSINESS_TRIP_REQUEST,
            title="부산 출장",
            summary="고객사 방문",
            site_id="site-a",
            department_id="dept-a",
            period_start="2026-06-10",
            period_end="2026-06-12",
            payload={"recommended_executor_id": sess.user_id},
            session=sess,
        )

    def _approve_trip_report(self, trip_id: str, source_document_id: str, *, session: UserSession) -> dict:
        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과 보고",
            payload={
                "trip_id": trip_id,
                "source_document_id": source_document_id,
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
                "report_body": "업무 결과",
            },
            session=session,
        )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": session.user_id, "approver_role": "admin"}],
            session=session,
        )
        return wf_svc.approve_document(self._tenant, report["id"], session=session)

    def test_submit_approve_and_task_completion_keep_status_domains_separate(self) -> None:
        sess = self._session()
        doc = self._create_business_trip_document(session=sess)
        trip_id = doc["content_json"]["trip_id"]
        trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(trip["status"], TRIP_STATUS_DRAFT)
        self.assertEqual(trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

        submitted = wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        planned = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(submitted["status"], DOC_STATUS_IN_REVIEW)
        self.assertEqual(planned["status"], TRIP_STATUS_PLANNED)
        self.assertNotEqual(submitted["status"], planned["status"])
        self.assertEqual(planned["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

        approved = wf_svc.approve_document(self._tenant, doc["id"], session=sess)
        approved_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        tasks = wf_svc.list_execution_tasks(self._tenant, session=sess)
        self.assertEqual(approved["status"], DOC_STATUS_APPROVED)
        self.assertEqual(approved_trip["status"], TRIP_STATUS_APPROVED)
        self.assertEqual(len(wf_svc.list_business_trips(self._tenant, session=sess)), 1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["trip_id"], trip_id)

        completed_task = wf_svc.complete_execution_task(self._tenant, tasks[0]["id"], session=sess)
        diary_due_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(completed_task["status"], TASK_COMPLETED)
        self.assertEqual(diary_due_trip["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(diary_due_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)
        self.assertNotEqual(diary_due_trip["status"], diary_due_trip["kpi_reflection_status"])

        audit_count = len(_load_raw(self._tenant)["audit_logs"])
        wf_svc.complete_execution_task(self._tenant, tasks[0]["id"], session=sess)
        self.assertEqual(len(_load_raw(self._tenant)["audit_logs"]), audit_count)

        report = self._approve_trip_report(trip_id, doc["id"], session=sess)
        completed_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(report["status"], DOC_STATUS_APPROVED)
        self.assertEqual(completed_trip["status"], TRIP_STATUS_COMPLETED)
        self.assertEqual(completed_trip["kpi_reflection_status"], KPI_REFLECTION_READY)
        self.assertEqual(completed_trip["report_document_id"], report["id"])

    def test_reject_and_cancel_paths_update_lifecycle_without_duplicate_rows(self) -> None:
        sess = self._session()
        rejected_doc = self._create_business_trip_document(session=sess)
        rejected_trip_id = rejected_doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            rejected_doc["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )

        rejected = wf_svc.reject_document(self._tenant, rejected_doc["id"], comment="반려", session=sess)
        rejected_trip = wf_svc.get_business_trip(self._tenant, rejected_trip_id, session=sess)
        self.assertEqual(rejected["status"], DOC_STATUS_REJECTED)
        self.assertEqual(rejected_trip["status"], TRIP_STATUS_CANCELLED)
        self.assertEqual(rejected_trip["kpi_reflection_status"], KPI_REFLECTION_NOT_APPLICABLE)

        cancelled_doc = self._create_business_trip_document(session=sess)
        cancelled_trip_id = cancelled_doc["content_json"]["trip_id"]
        cancelled = wf_svc.cancel_document(self._tenant, cancelled_doc["id"], comment="취소", session=sess)
        cancelled_trip = wf_svc.get_business_trip(self._tenant, cancelled_trip_id, session=sess)
        self.assertEqual(cancelled["status"], DOC_STATUS_CANCELLED)
        self.assertEqual(cancelled_trip["status"], TRIP_STATUS_CANCELLED)
        self.assertEqual(len(wf_svc.list_business_trips(self._tenant, session=sess)), 2)

    def test_document_audit_snapshot_does_not_drift_when_trip_link_is_added(self) -> None:
        sess = self._session()
        doc = self._create_business_trip_document(session=sess)
        db = _load_raw(self._tenant)
        created_audit = next(a for a in db["audit_logs"] if a["action"] == "document_created")
        self.assertNotIn("trip_id", created_audit["after_json"].get("content_json") or {})
        self.assertIn("trip_id", doc["content_json"])
        self.assertTrue(any(a["action"] == "business_trip_lifecycle_created_from_document" for a in db["audit_logs"]))

    def test_update_preserves_trip_link_and_document_audit_snapshot(self) -> None:
        sess = self._session()
        doc = self._create_business_trip_document(session=sess)
        trip_id = doc["content_json"]["trip_id"]

        updated = wf_svc.update_document(
            self._tenant,
            doc["id"],
            fields={
                "title": "부산 출장 수정",
                "payload": {"recommended_executor_id": sess.user_id, "destination": "Busan"},
            },
            session=sess,
        )
        trips = wf_svc.list_business_trips(self._tenant, session=sess)
        db = _load_raw(self._tenant)
        updated_audit = next(a for a in db["audit_logs"] if a["action"] == "document_updated")

        self.assertEqual(updated["content_json"]["trip_id"], trip_id)
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["trip_id"], trip_id)
        self.assertEqual(trips[0]["title"], "부산 출장 수정")
        self.assertNotIn("trip_id", updated_audit["after_json"].get("content_json") or {})

    def test_trip_dedupe_key_links_multiple_documents_to_one_lifecycle(self) -> None:
        sess = self._session()
        first = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_BUSINESS_TRIP_REQUEST,
            title="외부 출장 1",
            summary="중복 키 테스트",
            payload={"recommended_executor_id": sess.user_id, "trip_dedupe_key": "external-trip-42"},
            session=sess,
        )
        second = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_BUSINESS_TRIP_REQUEST,
            title="외부 출장 2",
            summary="중복 키 테스트",
            payload={"recommended_executor_id": sess.user_id, "trip_dedupe_key": "external-trip-42"},
            session=sess,
        )
        trips = wf_svc.list_business_trips(self._tenant, session=sess)

        self.assertEqual(len(trips), 1)
        self.assertEqual(first["content_json"]["trip_id"], second["content_json"]["trip_id"])
        self.assertEqual(trips[0]["dedupe_key"], "business-trip:external-trip-42")

    def test_direct_upsert_uses_service_tenant_over_payload_tenant(self) -> None:
        sess = self._session()
        trip = wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "tenant_id": "other-tenant",
                "title": "테넌트 고정 출장",
                "source": {"kind": "manual", "dedupe_key": "manual:tenant-lock"},
            },
            session=sess,
        )

        self.assertEqual(trip["tenant_id"], self._tenant)
        self.assertEqual(len(wf_svc.list_business_trips(self._tenant, session=sess)), 1)

    def test_cross_tenant_session_cannot_complete_execution_task(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]

        other_tenant_executor = UserSession(
            user_id=task["executor_id"],
            tenant_id="other-tenant",
            username="other",
            display_name="other",
            role="admin",
        )
        with self.assertRaises(PermissionError):
            wf_svc.complete_execution_task(self._tenant, task["id"], session=other_tenant_executor)

    def test_view_scoped_user_can_read_but_not_transition_lifecycle(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        db = _load_raw(self._tenant)
        db["user_profiles"] = [
            {"user_id": "viewer", "workflow_roles": ["viewer"], "viewer_site_ids": ["site-a"]},
        ]
        _save_raw(self._tenant, db)

        viewer = self._session("viewer", role="staff")
        visible = wf_svc.list_business_trips(self._tenant, session=viewer)
        self.assertEqual([row["trip_id"] for row in visible], [trip_id])
        with self.assertRaises(PermissionError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_PLANNED, session=viewer)

    def test_direct_completion_transition_requires_report_link(self) -> None:
        sess = self._session()
        doc = self._create_business_trip_document(session=sess)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=sess)
        task = wf_svc.list_execution_tasks(self._tenant, session=sess)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=sess)

        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_COMPLETED, session=sess)


if __name__ == "__main__":
    unittest.main()
