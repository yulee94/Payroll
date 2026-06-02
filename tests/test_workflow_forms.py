"""워크플로우 양식·팔로우업 테스트."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import DOC_TYPE_EXPENSE, DOC_TYPE_GENERAL
from core.workflow.forms import build_document_fields, validate_form_values
from core.workflow.seed import seed_tenant_if_empty
from services import workspace_store as ws


class WorkflowFormTests(unittest.TestCase):
    def test_validate_required_fields(self) -> None:
        errors = validate_form_values(DOC_TYPE_GENERAL, {"title": "테스트"})
        self.assertTrue(any("기안 목적" in e or "시작" in e for e in errors))

    def test_build_document_fields(self) -> None:
        built = build_document_fields(
            DOC_TYPE_EXPENSE,
            {
                "title": "법인카드",
                "expense_category": "법인카드",
                "period_start": "2026-05-01",
                "period_end": "2026-05-01",
                "total_amount": "12000",
                "purpose": "회의비",
            },
        )
        self.assertEqual(built["total_amount"], 12000)
        self.assertEqual(built["period_start"], "2026-05-01")


class WorkflowFollowUpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "test_follow_tenant"
        self._patch_wf = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_wf.start()
        self._patch_ws.start()

    def tearDown(self) -> None:
        self._patch_wf.stop()
        self._patch_ws.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self) -> UserSession:
        return UserSession(
            user_id="u1",
            tenant_id=self._tenant,
            username="tester",
            display_name="테스터",
            role="admin",
        )

    def test_submit_creates_todo_and_calendar(self) -> None:
        session_service._session = self._session()  # noqa: SLF001
        seed_tenant_if_empty(self._tenant)
        sess = self._session()
        doc = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="일정 연동 테스트",
            summary="본문",
            period_start="2026-06-01",
            period_end="2026-06-10",
            session=sess,
        )
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": "u1", "approver_role": "admin"}],
            session=sess,
        )
        todos = ws.list_todos(sess)
        self.assertTrue(any("결재 진행" in t.get("title", "") for t in todos))
        events = ws.list_calendar_events(2026, 6, sess)
        self.assertTrue(any("일정 연동" in e.get("title", "") for e in events))


if __name__ == "__main__":
    unittest.main()
