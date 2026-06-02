"""워크플로우 MVP 단위 테스트 (OpenAI 호출 없음)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import DOC_STATUS_APPROVED, DOC_STATUS_IN_REVIEW, DOC_TYPE_GENERAL
from core.workflow.permissions import can_view_document
from core.workflow.seed import seed_tenant_if_empty


class WorkflowMvpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "test_workflow_tenant"
        self._patch_root = patch(
            "core.workflow.store.WORKFLOW_ROOT",
            Path(self._tmpdir) / "workflow",
        )
        self._patch_root.start()

    def tearDown(self) -> None:
        self._patch_root.stop()
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

    def _login(self) -> None:
        session_service._session = self._session()  # noqa: SLF001

    def test_seed_and_create_submit_approve(self) -> None:
        self._login()
        seed_tenant_if_empty(self._tenant)
        doc = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="테스트 기안",
            summary="단위 테스트",
            session=self._session(),
        )
        self.assertTrue(doc.get("document_no"))
        line = [{"approver_id": "u1", "approver_role": "admin"}]
        submitted = wf_svc.submit_document(self._tenant, doc["id"], line, session=self._session())
        self.assertEqual(submitted["status"], DOC_STATUS_IN_REVIEW)
        approved = wf_svc.approve_document(self._tenant, doc["id"], session=self._session())
        self.assertEqual(approved["status"], DOC_STATUS_APPROVED)
        tasks = wf_svc.list_execution_tasks(self._tenant, session=self._session())
        self.assertGreaterEqual(len(tasks), 1)

    def test_inbox_filters(self) -> None:
        self._login()
        seed_tenant_if_empty(self._tenant)
        sess = self._session()
        counts = wf_svc.inbox_counts(self._tenant, session=sess)
        self.assertIn("to_approve", counts)
        self.assertIn("circulate", counts)
        self.assertIn("completed", counts)
        pending = wf_svc.list_documents(self._tenant, inbox="to_approve", session=sess)
        for d in pending:
            self.assertIn(d.get("status"), ("submitted", "in_review"))

    def test_permissions_view(self) -> None:
        self._login()
        seed_tenant_if_empty(self._tenant)
        sess = self._session()
        docs = wf_svc.list_documents(self._tenant, session=sess)
        if docs:
            self.assertTrue(can_view_document(sess, docs[0], tenant_id=self._tenant))


if __name__ == "__main__":
    unittest.main()
