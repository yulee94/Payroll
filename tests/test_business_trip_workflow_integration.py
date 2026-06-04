"""Business-trip workflow lifecycle integration regressions."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.group_store import create_group
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
    KPI_REFLECTION_REFLECTED,
    TASK_COMPLETED,
    TASK_PENDING,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_OVERDUE,
    TRIP_STATUS_PLANNED,
)
from core.workflow.store import _load_raw, _save_raw


class BusinessTripWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "trip_workflow_integration"
        self._patch_root = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_group_file = patch("core.group_store.GROUPS_FILE", Path(self._tmpdir) / "groups" / "registry.json")
        self._patch_config_root = patch("core.workflow.config_store.CONFIG_ROOT", Path(self._tmpdir) / "groups")
        self._patch_root.start()
        self._patch_group_file.start()
        self._patch_config_root.start()

    def tearDown(self) -> None:
        self._patch_config_root.stop()
        self._patch_group_file.stop()
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
        self.assertEqual(completed_trip["origin_tenant_id"], self._tenant)
        self.assertEqual(completed_trip["traveler_user_id"], sess.user_id)
        self.assertEqual(completed_trip["plan_document_id"], doc["id"])
        self.assertEqual(completed_trip["execution_task_id"], tasks[0]["id"])
        self.assertEqual(completed_trip["planned_start"], "2026-06-10")
        self.assertEqual(completed_trip["planned_end"], "2026-06-12")
        self.assertTrue(completed_trip["actual_start"])
        self.assertTrue(completed_trip["actual_end"])
        self.assertTrue(completed_trip["diary_due_at"])
        self.assertTrue(completed_trip["completed_at"])

    def test_report_approval_cannot_complete_trip_before_execution_task(self) -> None:
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

        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과 보고",
            payload={
                "trip_id": trip_id,
                "source_document_id": doc["id"],
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
                "report_body": "업무 결과",
            },
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )

        with self.assertRaises(ValueError):
            wf_svc.approve_document(self._tenant, report["id"], session=sess)

        blocked_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        blocked_report = wf_svc.get_document(self._tenant, report["id"], session=sess)
        tasks = wf_svc.list_execution_tasks(self._tenant, session=sess)
        self.assertEqual(blocked_trip["status"], TRIP_STATUS_APPROVED)
        self.assertEqual(blocked_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)
        self.assertEqual(blocked_report["status"], DOC_STATUS_IN_REVIEW)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], task["id"])
        self.assertEqual(tasks[0]["status"], TASK_PENDING)

        wf_svc.complete_execution_task(self._tenant, task["id"], session=sess)
        approved_report = wf_svc.approve_document(self._tenant, report["id"], session=sess)
        completed_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        tasks_after_report = wf_svc.list_execution_tasks(self._tenant, session=sess)
        self.assertEqual(approved_report["status"], DOC_STATUS_APPROVED)
        self.assertEqual(completed_trip["status"], TRIP_STATUS_COMPLETED)
        self.assertEqual(completed_trip["kpi_reflection_status"], KPI_REFLECTION_READY)
        self.assertEqual(completed_trip["report_document_id"], report["id"])
        self.assertEqual(len(tasks_after_report), 1)

    def test_admin_repair_cannot_move_to_diary_due_before_execution_task(self) -> None:
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

        wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_IN_PROGRESS, session=sess)
        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_DIARY_DUE, session=sess)

        pending_task = wf_svc.list_execution_tasks(self._tenant, session=sess)[0]
        blocked_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(pending_task["status"], TASK_PENDING)
        self.assertEqual(blocked_trip["status"], TRIP_STATUS_IN_PROGRESS)
        self.assertEqual(blocked_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

        wf_svc.complete_execution_task(self._tenant, task["id"], session=sess)
        diary_due_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(diary_due_trip["status"], TRIP_STATUS_DIARY_DUE)

    def test_admin_repair_normalizes_status_before_terminal_gates(self) -> None:
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

        wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, "in_progress", session=sess)
        for raw_status in ("diary_due ", " completed "):
            with self.assertRaises(ValueError):
                wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, raw_status, session=sess)
        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, "COMPLETED", session=sess)

        pending_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(pending_trip["status"], TRIP_STATUS_IN_PROGRESS)
        self.assertEqual(pending_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)
        self.assertEqual(pending_trip["report_document_id"], "")

    def test_same_tenant_user_cannot_link_report_to_another_users_trip(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=owner)

        attacker = self._session("attacker", role="staff")
        with self.assertRaises(PermissionError):
            wf_svc.create_document(
                self._tenant,
                document_type=DOC_TYPE_GENERAL,
                title="출장보고서",
                summary="타인 출장 결과 보고",
                payload={
                    "trip_id": trip_id,
                    "source_document_id": doc["id"],
                    "template_name": "출장보고서",
                    "business_trip_artifact": "trip_report",
                },
                session=attacker,
            )

        unchanged_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=owner)
        self.assertEqual(unchanged_trip["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(unchanged_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

    def test_unrelated_report_approver_cannot_complete_another_users_trip(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=owner)

        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과 보고",
            payload={
                "trip_id": trip_id,
                "source_document_id": doc["id"],
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
            },
            session=owner,
        )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": "unrelated-approver", "approver_role": "approver"}],
            session=owner,
        )

        with self.assertRaises(PermissionError):
            wf_svc.approve_document(
                self._tenant,
                report["id"],
                session=self._session("unrelated-approver", role="staff"),
            )

        blocked_report = wf_svc.get_document(self._tenant, report["id"], session=owner)
        unchanged_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=owner)
        self.assertEqual(blocked_report["status"], DOC_STATUS_IN_REVIEW)
        self.assertEqual(unchanged_trip["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(unchanged_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

    def test_cross_tenant_admin_cannot_read_dashboard_or_reflect_trip(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=owner)
        self._approve_trip_report(trip_id, doc["id"], session=owner)

        other_admin = UserSession(
            user_id="other-admin",
            tenant_id="other-tenant",
            username="other-admin",
            display_name="other-admin",
            role="admin",
        )
        with self.assertRaises(PermissionError):
            wf_svc.list_business_trips(self._tenant, session=other_admin)
        with self.assertRaises(PermissionError):
            wf_svc.get_business_trip(self._tenant, trip_id, session=other_admin)
        with self.assertRaises(PermissionError):
            wf_svc.list_business_trip_kpi_reflections(self._tenant, session=other_admin)
        with self.assertRaises(PermissionError):
            wf_svc.business_trip_manager_dashboard(self._tenant, session=other_admin)
        with self.assertRaises(PermissionError):
            wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=other_admin)

        ready_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=owner)
        self.assertEqual(ready_trip["kpi_reflection_status"], KPI_REFLECTION_READY)

    def test_same_group_sibling_admin_cannot_read_or_mutate_origin_tenant_trip(self) -> None:
        create_group(
            name="Trip Workflow Group",
            root_tenant_id=self._tenant,
            tenant_ids=(self._tenant, "sibling-tenant"),
            group_id="trip-workflow-group",
        )
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=owner)
        self._approve_trip_report(trip_id, doc["id"], session=owner)
        sibling_admin = UserSession(
            user_id="sibling-admin",
            tenant_id="sibling-tenant",
            username="sibling-admin",
            display_name="sibling-admin",
            role="admin",
        )

        self.assertEqual(wf_svc.list_business_trips(self._tenant, session=sibling_admin), [])
        self.assertEqual(wf_svc.business_trip_manager_dashboard(self._tenant, session=sibling_admin)["counts"]["total"], 0)
        self.assertEqual(wf_svc.list_execution_tasks(self._tenant, session=sibling_admin), [])
        with self.assertRaises(PermissionError):
            wf_svc.get_business_trip(self._tenant, trip_id, session=sibling_admin)
        with self.assertRaises(PermissionError):
            wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=sibling_admin)

        with self.assertRaises(PermissionError):
            wf_svc.create_document(
                self._tenant,
                document_type=DOC_TYPE_GENERAL,
                title="출장보고서",
                summary="형제 법인 관리자 보고",
                payload={
                    "trip_id": trip_id,
                    "source_document_id": doc["id"],
                    "template_name": "출장보고서",
                    "business_trip_artifact": "trip_report",
                },
                session=sibling_admin,
            )

    def test_same_group_sibling_assigned_approver_cannot_read_or_approve_origin_trip_request(self) -> None:
        create_group(
            name="Trip Workflow Group",
            root_tenant_id=self._tenant,
            tenant_ids=(self._tenant, "sibling-tenant"),
            group_id="trip-workflow-group-approver",
        )
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": "sibling-admin", "approver_role": "admin"}],
            session=owner,
        )
        sibling_admin = UserSession(
            user_id="sibling-admin",
            tenant_id="sibling-tenant",
            username="sibling-admin",
            display_name="sibling-admin",
            role="admin",
        )

        self.assertNotIn(doc["id"], [row["id"] for row in wf_svc.list_documents(self._tenant, session=sibling_admin)])
        with self.assertRaises(PermissionError):
            wf_svc.get_document(self._tenant, doc["id"], session=sibling_admin)
        with self.assertRaises(PermissionError):
            wf_svc.approve_document(self._tenant, doc["id"], session=sibling_admin)

        unchanged_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=owner)
        self.assertEqual(unchanged_trip["status"], TRIP_STATUS_PLANNED)
        self.assertEqual(wf_svc.list_execution_tasks(self._tenant, session=owner), [])

    def test_cross_tenant_admin_cannot_mutate_trip_report_documents(self) -> None:
        owner = self._session("owner", role="admin")
        doc = self._create_business_trip_document(session=owner)
        trip_id = doc["content_json"]["trip_id"]
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": owner.user_id, "approver_role": "admin"}],
            session=owner,
        )
        wf_svc.approve_document(self._tenant, doc["id"], session=owner)
        task = wf_svc.list_execution_tasks(self._tenant, session=owner)[0]
        wf_svc.complete_execution_task(self._tenant, task["id"], session=owner)
        other_admin = UserSession(
            user_id="other-admin",
            tenant_id="other-tenant",
            username="other-admin",
            display_name="other-admin",
            role="admin",
        )

        with self.assertRaises(PermissionError):
            wf_svc.create_document(
                self._tenant,
                document_type=DOC_TYPE_GENERAL,
                title="출장보고서",
                summary="타 테넌트 관리자 보고",
                payload={
                    "trip_id": trip_id,
                    "source_document_id": doc["id"],
                    "template_name": "출장보고서",
                    "business_trip_artifact": "trip_report",
                },
                session=other_admin,
            )

        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과 보고",
            payload={
                "trip_id": trip_id,
                "source_document_id": doc["id"],
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
            },
            session=owner,
        )
        with self.assertRaises(PermissionError):
            wf_svc.submit_document(
                self._tenant,
                report["id"],
                [{"approver_id": "other-admin", "approver_role": "admin"}],
                session=other_admin,
            )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": "other-admin", "approver_role": "admin"}],
            session=owner,
        )
        with self.assertRaises(PermissionError):
            wf_svc.approve_document(self._tenant, report["id"], session=other_admin)

        unchanged_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=owner)
        self.assertEqual(unchanged_trip["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(unchanged_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

    def test_approved_daily_work_log_links_without_completing_trip(self) -> None:
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

        diary = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="업무일지",
            summary="출장 업무일지",
            payload={
                "trip_id": trip_id,
                "template_name": "업무일지",
                "business_trip_artifact": "daily_diary",
                "diary_body": "고객 미팅 및 후속 업무 정리",
            },
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            diary["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        approved_diary = wf_svc.approve_document(self._tenant, diary["id"], session=sess)
        diary_due_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)

        self.assertEqual(approved_diary["status"], DOC_STATUS_APPROVED)
        self.assertEqual(diary_due_trip["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(diary_due_trip["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)
        self.assertEqual(diary_due_trip["diary_document_id"], diary["id"])
        self.assertEqual(diary_due_trip["report_document_id"], "")
        self.assertFalse(diary_due_trip["completed_at"])
        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_COMPLETED, session=sess)
        with self.assertRaises(ValueError):
            wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=sess)

    def test_trip_report_template_metadata_survives_edited_title(self) -> None:
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

        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="현장 방문 결과 공유",
            summary="고객 후속 조치",
            payload={
                "trip_id": trip_id,
                "gw_template_id": "coss_출장보고서",
                "gw_form_name": "출장보고서",
                "content": "출장 결과",
            },
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        approved_report = wf_svc.approve_document(self._tenant, report["id"], session=sess)
        completed_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)

        self.assertEqual(approved_report["status"], DOC_STATUS_APPROVED)
        self.assertEqual(completed_trip["status"], TRIP_STATUS_COMPLETED)
        self.assertEqual(completed_trip["kpi_reflection_status"], KPI_REFLECTION_READY)
        self.assertEqual(completed_trip["report_document_id"], report["id"])

    def test_draft_report_does_not_replace_approved_completion_evidence(self) -> None:
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
        approved_report = self._approve_trip_report(trip_id, doc["id"], session=sess)
        ready_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(ready_trip["report_document_id"], approved_report["id"])
        self.assertEqual(ready_trip["kpi_reflection_status"], KPI_REFLECTION_READY)

        draft_report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서 수정본",
            summary="아직 승인되지 않은 수정본",
            payload={
                "trip_id": trip_id,
                "business_trip_artifact": "trip_report",
                "report_body": "초안",
            },
            session=sess,
        )
        after_draft = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        reflected = wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=sess)

        self.assertNotEqual(draft_report["id"], approved_report["id"])
        self.assertEqual(after_draft["report_document_id"], approved_report["id"])
        self.assertEqual(after_draft["status"], TRIP_STATUS_COMPLETED)
        self.assertEqual(after_draft["kpi_reflection_status"], KPI_REFLECTION_READY)
        self.assertEqual(reflected["kpi_reflection_status"], KPI_REFLECTION_REFLECTED)

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

    def test_direct_upsert_cannot_seed_diary_due_without_execution_task(self) -> None:
        sess = self._session()
        with self.assertRaises(ValueError):
            wf_svc.upsert_business_trip_lifecycle(
                self._tenant,
                fields={
                    "trip_id": "manual-diary-due-without-task",
                    "title": "실행 증빙 없는 보고 대기 출장",
                    "status": TRIP_STATUS_DIARY_DUE,
                    "requester_id": sess.user_id,
                    "executor_id": sess.user_id,
                    "site_id": "site-a",
                    "department_id": "dept-a",
                    "source": {"kind": "manual", "dedupe_key": "manual:diary-due-without-task"},
                },
                session=sess,
            )

    def test_direct_upsert_cannot_seed_overdue_or_kpi_ready_without_lifecycle_proof(self) -> None:
        sess = self._session()
        with self.assertRaises(ValueError):
            wf_svc.upsert_business_trip_lifecycle(
                self._tenant,
                fields={
                    "trip_id": "manual-overdue-without-task",
                    "title": "실행업무 없는 지연 출장",
                    "status": TRIP_STATUS_OVERDUE,
                    "requester_id": sess.user_id,
                    "executor_id": sess.user_id,
                    "site_id": "site-a",
                    "department_id": "dept-a",
                    "source": {"kind": "manual", "dedupe_key": "manual:overdue-without-task"},
                },
                session=sess,
            )
        rejected = wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "trip_id": "manual-ready-non-completed",
                "title": "완료 전 실적대기 오염 입력",
                "status": TRIP_STATUS_IN_PROGRESS,
                "kpi_reflection_status": KPI_REFLECTION_READY,
                "requester_id": sess.user_id,
                "executor_id": sess.user_id,
                "site_id": "site-a",
                "department_id": "dept-a",
                "source": {"kind": "manual", "dedupe_key": "manual:ready-non-completed"},
            },
            session=sess,
        )
        self.assertEqual(rejected["status"], TRIP_STATUS_IN_PROGRESS)
        self.assertEqual(rejected["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

    def test_admin_repair_cannot_transition_to_overdue_without_execution_task(self) -> None:
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
        db = _load_raw(self._tenant)
        db["execution_tasks"] = []
        _save_raw(self._tenant, db)

        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_OVERDUE, session=sess)

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

    def test_direct_completion_transition_requires_approved_report_link(self) -> None:
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

        draft_report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과 보고",
            payload={
                "trip_id": trip_id,
                "source_document_id": doc["id"],
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
                "report_body": "업무 결과",
            },
            session=sess,
        )
        with self.assertRaises(ValueError):
            wf_svc.transition_business_trip_lifecycle(self._tenant, trip_id, TRIP_STATUS_COMPLETED, session=sess)

        wf_svc.submit_document(
            self._tenant,
            draft_report["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        approved_report = wf_svc.approve_document(self._tenant, draft_report["id"], session=sess)
        completed_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=sess)
        self.assertEqual(approved_report["status"], DOC_STATUS_APPROVED)
        self.assertEqual(completed_trip["status"], TRIP_STATUS_COMPLETED)


if __name__ == "__main__":
    unittest.main()
