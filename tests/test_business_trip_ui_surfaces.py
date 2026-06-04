"""Business-trip UI surface regressions and Tkinter smoke evidence."""

from __future__ import annotations

import inspect
import shutil
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.kpi import service as kpi_svc
from core.module_store import load_module_db
from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import DOC_TYPE_BUSINESS_TRIP_REQUEST, DOC_TYPE_GENERAL, KPI_REFLECTION_REFLECTED
from services import workspace_store as ws
from ui.workflow_hub_panel import WorkflowHubPanel, format_business_trip_dashboard_lines
from ui.workspace_labels import workspace_source_label


class BusinessTripUiSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "trip_ui_surface"
        self._patch_wf = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_app_data = patch("core.module_store.app_data_dir", lambda: Path(self._tmpdir))
        self._patch_wf.start()
        self._patch_ws.start()
        self._patch_app_data.start()
        session_service._session = self._session("requester", role="admin")  # noqa: SLF001

    def tearDown(self) -> None:
        logout()
        self._patch_app_data.stop()
        self._patch_ws.stop()
        self._patch_wf.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self, uid: str = "requester", role: str = "admin") -> UserSession:
        return UserSession(
            user_id=uid,
            tenant_id=self._tenant,
            username=uid,
            display_name=uid,
            role=role,
        )

    def _approve_trip(self, *, period_end: str = "2026-06-01") -> tuple[dict, str, dict]:
        sess = self._session("requester", role="admin")
        doc = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_BUSINESS_TRIP_REQUEST,
            title="UI 출장 점검",
            summary="출장 UI smoke",
            site_id="site-a",
            department_id="dept-a",
            period_start="2026-06-01",
            period_end=period_end,
            payload={"recommended_executor_id": "executor", "destination": "대전"},
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        approved = wf_svc.approve_document(self._tenant, doc["id"], session=sess)
        trip_id = approved["content_json"]["trip_id"]
        task = next(
            t for t in wf_svc.list_execution_tasks(self._tenant, session=sess) if t["trip_id"] == trip_id
        )
        return approved, trip_id, task

    def _approve_trip_report(self, trip_id: str, source_document_id: str) -> dict:
        sess = self._session("requester", role="admin")
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
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            report["id"],
            [{"approver_id": sess.user_id, "approver_role": "admin"}],
            session=sess,
        )
        return wf_svc.approve_document(self._tenant, report["id"], session=sess)

    def test_workspace_source_labels_cover_workflow_trip_items(self) -> None:
        self.assertEqual(workspace_source_label({"source": "workflow"}), "전자결재")
        self.assertEqual(workspace_source_label({"source": "workflow_approval"}), "결재")
        self.assertEqual(workspace_source_label({"source": "workflow_execution"}), "실행업무")
        self.assertEqual(workspace_source_label({"source": "business_trip_overdue"}), "출장 지연")
        self.assertEqual(workspace_source_label({"source": "manual"}), "")

    def test_trip_dashboard_formatter_groups_status_and_kpi_state(self) -> None:
        lines = format_business_trip_dashboard_lines(
            {
                "counts": {"ongoing": 1, "completed": 1, "overdue": 1},
                "kpi_summary": {"blocked": 1, "ready": 1, "reflected": 1},
                "sections": {
                    "overdue": [
                        {
                            "trip_id": "trip-overdue",
                            "title": "지연 출장",
                            "status": "overdue",
                            "kpi_reflection_status": "blocked",
                            "period_start": "2026-06-01",
                            "period_end": "2026-06-02",
                        }
                    ],
                    "ongoing": [{"trip_id": "trip-active", "title": "진행 출장", "status": "in_progress"}],
                    "completed": [{"trip_id": "trip-done", "title": "완료 출장", "status": "completed"}],
                },
            }
        )
        text = "\n".join(lines)
        self.assertIn("출장 lifecycle 현황", text)
        self.assertIn("[지연] 1건", text)
        self.assertIn("실적", text)

    def test_trip_dashboard_refresh_control_is_read_only(self) -> None:
        source = inspect.getsource(WorkflowHubPanel._build_reports_tab)
        self.assertIn('"새로고침"', source)
        self.assertNotIn("지연 평가", source)
        self.assertNotIn("evaluate_business_trip_overdues", source)

    def test_workflow_hub_trip_dashboard_tk_smoke_renders_overdue_path(self) -> None:
        self._approve_trip(period_end="2026-06-01")
        wf_svc.evaluate_business_trip_overdues(
            self._tenant,
            session=self._session("requester", role="admin"),
            today="2026-06-04",
        )
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        try:
            root.withdraw()
            panel = WorkflowHubPanel(root)
            panel._reload_trip_dashboard()  # noqa: SLF001 - smoke the service-backed pane.
            content = panel._trip_text.get("1.0", tk.END)  # noqa: SLF001
            self.assertIn("출장 lifecycle 현황", content)
            self.assertIn("[지연] 1건", content)
            self.assertIn("UI 출장 점검", content)
        finally:
            root.destroy()

    def test_kpi_hub_dashboard_counts_reflected_trip_results(self) -> None:
        approved, trip_id, task = self._approve_trip(period_end="2026-06-03")
        wf_svc.complete_execution_task(self._tenant, task["id"], session=self._session("executor", role="staff"))
        self._approve_trip_report(trip_id, approved["id"])
        reflected = wf_svc.reflect_business_trip_kpi(self._tenant, trip_id, session=self._session("requester", "admin"))
        self.assertEqual(reflected["kpi_reflection_status"], KPI_REFLECTION_REFLECTED)

        labels = {label: hint for label, _value, hint in kpi_svc.dashboard_kpis()}
        kpi_db = load_module_db(kpi_svc.MODULE, self._tenant, kpi_svc._EMPTY)  # noqa: SLF001
        self.assertEqual(len([r for r in kpi_db["individual"] if r.get("source") == "business_trip"]), 1)
        self.assertIn("출장 실적 1건 반영", labels["개인 KPI"])

        todos = ws.list_todos(self._session("executor", role="staff"))
        self.assertTrue(any(t.get("trip_id") == approved["content_json"]["trip_id"] for t in todos))


if __name__ == "__main__":
    unittest.main()
