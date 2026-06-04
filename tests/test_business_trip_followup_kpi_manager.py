"""Business-trip follow-up, overdue, KPI, and manager-view regressions."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.kpi import service as kpi_svc
from core.module_store import load_module_db
from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import (
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
    DOC_TYPE_GENERAL,
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    TASK_DELAYED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_OVERDUE,
)
from core.workflow.follow_up import sync_approval_complete_follow_up, sync_submission_follow_up
from core.workflow.store import _load_raw, _save_raw
from services import workspace_store as ws


class BusinessTripFollowUpKpiManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "trip_followup_kpi"
        self._patch_wf = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_app_data = patch("core.module_store.app_data_dir", lambda: Path(self._tmpdir))
        self._patch_wf.start()
        self._patch_ws.start()
        self._patch_app_data.start()

    def tearDown(self) -> None:
        self._patch_app_data.stop()
        self._patch_ws.stop()
        self._patch_wf.stop()
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

    def _create_trip_document(
        self,
        *,
        requester: UserSession | None = None,
        executor_id: str = "executor",
        title: str = "대전 고객사 출장",
        site_id: str = "site-a",
        department_id: str = "dept-a",
        period_start: str = "2026-06-01",
        period_end: str = "2026-06-03",
    ) -> dict:
        sess = requester or self._session("requester", role="admin")
        return wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_BUSINESS_TRIP_REQUEST,
            title=title,
            summary="출장 업무",
            site_id=site_id,
            department_id=department_id,
            period_start=period_start,
            period_end=period_end,
            payload={"recommended_executor_id": executor_id, "destination": "대전"},
            session=sess,
        )

    def _approve_trip(
        self,
        *,
        requester: UserSession | None = None,
        executor_id: str = "executor",
        period_end: str = "2026-06-03",
        site_id: str = "site-a",
        department_id: str = "dept-a",
    ) -> tuple[dict, str, dict]:
        sess = requester or self._session("requester", role="admin")
        doc = self._create_trip_document(
            requester=sess,
            executor_id=executor_id,
            site_id=site_id,
            department_id=department_id,
            period_end=period_end,
        )
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        approved = wf_svc.approve_document(self._tenant, doc["id"], session=sess)
        trip_id = approved["content_json"]["trip_id"]
        task = next(t for t in wf_svc.list_execution_tasks(self._tenant, session=sess) if t["trip_id"] == trip_id)
        return approved, trip_id, task

    def _approve_trip_report(self, trip_id: str, source_document_id: str, *, session: UserSession) -> dict:
        report = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="출장보고서",
            summary="출장 결과",
            payload={
                "trip_id": trip_id,
                "source_document_id": source_document_id,
                "template_name": "출장보고서",
                "business_trip_artifact": "trip_report",
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

    def test_follow_up_source_links_are_idempotent(self) -> None:
        sess = self._session("requester", role="admin")
        doc = self._create_trip_document(requester=sess, executor_id="executor")
        approval_line = [{"approver_id": "approver", "approver_role": "department_manager"}]
        submitted = wf_svc.submit_document(self._tenant, doc["id"], approval_line, session=sess)

        sync_submission_follow_up(submitted, approval_line, session=sess, cc_user_ids=[])
        requester_todos = ws.list_todos(self._session("requester", role="staff"))
        requester_events = ws.list_calendar_events(2026, 6, self._session("requester", role="staff"))
        approver_todos = ws.list_todos(self._session("approver", role="staff"))
        approver_events = ws.list_calendar_events(2026, 6, self._session("approver", role="staff"))

        self.assertEqual(len([t for t in requester_todos if t.get("source") == "workflow"]), 1)
        self.assertEqual(len([e for e in requester_events if e.get("source") == "workflow"]), 1)
        self.assertEqual(len([t for t in approver_todos if t.get("source") == "workflow_approval"]), 1)
        self.assertEqual(len([e for e in approver_events if e.get("source") == "workflow_approval"]), 1)
        self.assertTrue(all(t.get("document_id") == doc["id"] and t.get("source_key") for t in requester_todos))

        approved = wf_svc.approve_document(self._tenant, doc["id"], session=self._session("approver", role="admin"))
        sync_approval_complete_follow_up(approved, session=sess, executor_id="executor")
        executor_todos = ws.list_todos(self._session("executor", role="staff"))
        executor_events = ws.list_calendar_events(2026, 6, self._session("executor", role="staff"))
        self.assertEqual(len([t for t in executor_todos if t.get("source") == "workflow_execution"]), 1)
        self.assertEqual(len([e for e in executor_events if e.get("source") == "workflow_execution"]), 1)
        self.assertEqual(executor_todos[0]["trip_id"], approved["content_json"]["trip_id"])

    def test_overdue_evaluator_delays_task_and_escalates_once(self) -> None:
        admin = self._session("requester", role="admin")
        _doc, trip_id, task = self._approve_trip(requester=admin, executor_id="executor", period_end="2026-06-01")
        db = _load_raw(self._tenant)
        db["user_profiles"] = [
            {"user_id": "requester", "manager_user_id": "requester-manager", "workflow_roles": []},
            {"user_id": "executor", "manager_user_id": "executor-manager", "workflow_roles": []},
            {"user_id": "site-manager", "workflow_roles": ["site_manager"], "site_ids": ["site-a"]},
            {"user_id": "dept-manager", "workflow_roles": ["department_manager"], "department_ids": ["dept-a"]},
        ]
        _save_raw(self._tenant, db)

        first = wf_svc.evaluate_business_trip_overdues(self._tenant, session=admin, today="2026-06-04")
        second = wf_svc.evaluate_business_trip_overdues(self._tenant, session=admin, today="2026-06-04")
        delayed_task = next(
            t for t in wf_svc.list_execution_tasks(self._tenant, session=admin) if t["id"] == task["id"]
        )
        overdue_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=admin)
        notifications = [
            n
            for n in _load_raw(self._tenant)["notifications"]
            if n.get("type") == "business_trip_overdue_escalation" and n.get("related_task_id") == task["id"]
        ]
        manager_todos = ws.list_todos(self._session("executor-manager", role="staff"))

        self.assertEqual(first["delayed_tasks"], 1)
        self.assertEqual(second["delayed_tasks"], 0)
        self.assertEqual(delayed_task["status"], TASK_DELAYED)
        self.assertEqual(overdue_trip["status"], TRIP_STATUS_OVERDUE)
        self.assertEqual(len({n["user_id"] for n in notifications}), 6)
        self.assertEqual(len(notifications), 6)
        self.assertEqual(len([t for t in manager_todos if t.get("source") == "business_trip_overdue"]), 1)
        self.assertEqual(manager_todos[0]["trip_id"], trip_id)

    def test_overdue_evaluator_requires_authorized_tenant_manager(self) -> None:
        admin = self._session("requester", role="admin")
        self._approve_trip(requester=admin, executor_id="executor", period_end="2026-06-01")

        with self.assertRaises(PermissionError):
            wf_svc.evaluate_business_trip_overdues(
                self._tenant,
                session=self._session("executor", role="staff"),
                today="2026-06-04",
            )
        with self.assertRaises(PermissionError):
            wf_svc.evaluate_business_trip_overdues(
                self._tenant,
                session=UserSession(
                    user_id="requester",
                    tenant_id="other-tenant",
                    username="requester",
                    display_name="requester",
                    role="admin",
                ),
                today="2026-06-04",
            )

    def test_kpi_reflection_adapter_is_stateful_and_idempotent(self) -> None:
        admin = self._session("requester", role="admin")
        _doc, trip_id, task = self._approve_trip(requester=admin, executor_id="executor")
        ready_task = wf_svc.complete_execution_task(
            self._tenant,
            task["id"],
            session=self._session("executor", role="staff"),
        )
        self.assertEqual(ready_task["status"], "completed")
        diary_due = wf_svc.get_business_trip(self._tenant, trip_id, session=admin)
        self.assertEqual(diary_due["status"], TRIP_STATUS_DIARY_DUE)
        self.assertEqual(diary_due["kpi_reflection_status"], KPI_REFLECTION_BLOCKED)

        self._approve_trip_report(trip_id, _doc["id"], session=admin)

        ready_rows = wf_svc.list_business_trip_kpi_reflections(
            self._tenant,
            session=admin,
            kpi_reflection_status=KPI_REFLECTION_READY,
        )
        first = wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=admin)
        second = wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=admin)
        reflected_trip = wf_svc.get_business_trip(self._tenant, trip_id, session=admin)
        kpi_db = load_module_db(kpi_svc.MODULE, self._tenant, kpi_svc._EMPTY)  # noqa: SLF001
        reflected_records = [r for r in kpi_db["individual"] if r.get("source_key") == f"business_trip:{trip_id}"]

        self.assertEqual([row["trip_id"] for row in ready_rows], [trip_id])
        self.assertEqual(first["kpi_reflection_status"], KPI_REFLECTION_REFLECTED)
        self.assertEqual(second["kpi_record"]["id"], first["kpi_record"]["id"])
        self.assertEqual(reflected_trip["kpi_reflection_status"], KPI_REFLECTION_REFLECTED)
        self.assertEqual(len(reflected_records), 1)

    def test_manual_trip_cannot_reflect_kpi_without_report_and_execution_proof(self) -> None:
        admin = self._session("admin", role="admin")
        with self.assertRaises(ValueError):
            wf_svc.upsert_business_trip_lifecycle(
                self._tenant,
                fields={
                    "trip_id": "manual-complete-without-proof",
                    "title": "증빙 없는 수기 완료 출장",
                    "status": TRIP_STATUS_COMPLETED,
                    "kpi_reflection_status": KPI_REFLECTION_READY,
                    "requester_id": "requester-a",
                    "executor_id": "executor-a",
                    "site_id": "site-a",
                    "department_id": "dept-a",
                    "source": {"kind": "manual", "dedupe_key": "manual:without-proof"},
                },
                session=admin,
            )

        db = _load_raw(self._tenant)
        db["business_trips"].append(
            {
                "id": "manual-direct-row",
                "trip_id": "manual-direct-row",
                "tenant_id": self._tenant,
                "status": TRIP_STATUS_COMPLETED,
                "kpi_reflection_status": KPI_REFLECTION_READY,
                "title": "저장소 직접 삽입 수기 출장",
                "requester_id": "requester-a",
                "executor_id": "executor-a",
                "site_id": "site-a",
                "department_id": "dept-a",
                "period_start": "2026-06-01",
                "period_end": "2026-06-03",
                "approved_document_id": "",
                "diary_document_id": "",
                "report_document_id": "",
                "source": {"kind": "manual", "dedupe_key": "manual:direct-row"},
                "dedupe_key": "manual:direct-row",
                "created_at": "2026-06-04T00:00:00",
                "updated_at": "2026-06-04T00:00:00",
            }
        )
        _save_raw(self._tenant, db)

        with self.assertRaises(ValueError):
            wf_svc.reflect_business_trip_kpi(self._tenant, "manual-direct-row", session=admin)

    def test_manager_dashboard_filters_visible_trips_and_sections(self) -> None:
        admin = self._session("admin", role="admin")
        visible_overdue = wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "trip_id": "trip-visible-overdue",
                "title": "현장 A 지연 출장",
                "status": TRIP_STATUS_OVERDUE,
                "kpi_reflection_status": KPI_REFLECTION_BLOCKED,
                "requester_id": "requester-a",
                "executor_id": "executor-a",
                "site_id": "site-a",
                "department_id": "dept-a",
                "source": {"kind": "manual", "dedupe_key": "manual:visible-overdue"},
            },
            session=admin,
        )
        hidden_doc, hidden_trip_id, hidden_task = self._approve_trip(
            requester=admin,
            executor_id="executor-b",
            site_id="site-b",
            department_id="dept-b",
        )
        wf_svc.complete_execution_task(self._tenant, hidden_task["id"], session=admin)
        self._approve_trip_report(hidden_trip_id, hidden_doc["id"], session=admin)
        wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "trip_id": "trip-visible-ongoing",
                "title": "현장 A 진행 출장",
                "status": TRIP_STATUS_IN_PROGRESS,
                "kpi_reflection_status": KPI_REFLECTION_BLOCKED,
                "requester_id": "requester-a",
                "executor_id": "executor-a",
                "site_id": "site-a",
                "department_id": "dept-a",
                "source": {"kind": "manual", "dedupe_key": "manual:visible-ongoing"},
            },
            session=admin,
        )
        db = _load_raw(self._tenant)
        db["user_profiles"] = [
            {"user_id": "site-manager", "workflow_roles": ["site_manager"], "site_ids": ["site-a"]},
        ]
        _save_raw(self._tenant, db)

        dashboard = wf_svc.business_trip_manager_dashboard(
            self._tenant,
            session=self._session("site-manager", role="staff"),
        )
        visible_ids = {row["trip_id"] for row in dashboard["trips"]}

        self.assertEqual(visible_ids, {visible_overdue["trip_id"], "trip-visible-ongoing"})
        self.assertEqual([row["trip_id"] for row in dashboard["sections"]["overdue"]], ["trip-visible-overdue"])
        self.assertEqual([row["trip_id"] for row in dashboard["sections"]["ongoing"]], ["trip-visible-ongoing"])
        self.assertEqual(dashboard["counts"]["completed"], 0)
        self.assertEqual(dashboard["kpi_summary"][KPI_REFLECTION_BLOCKED], 2)


if __name__ == "__main__":
    unittest.main()
