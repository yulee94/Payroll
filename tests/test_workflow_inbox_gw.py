"""GW 결재함·메일 폴더 대응 테스트."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.constants import DOC_STATUS_SUBMITTED, DOC_TYPE_GENERAL
from core.workflow.inbox import GW_INBOX_QUICK_TABS, matches_inbox
from core.workflow.seed import seed_tenant_if_empty
from services import workspace_store as ws


class GwInboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "test_gw_inbox"
        self._patch_wf = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_wf.start()
        self._patch_ws.start()

    def tearDown(self) -> None:
        self._patch_wf.stop()
        self._patch_ws.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self, uid: str = "u1") -> UserSession:
        return UserSession(
            user_id=uid,
            tenant_id=self._tenant,
            username=uid,
            display_name=uid,
            role="admin",
        )

    def test_gw_quick_tabs_defined(self) -> None:
        ids = [t[0] for t in GW_INBOX_QUICK_TABS]
        self.assertEqual(ids, ["all", "to_approve", "my_draft", "circulate"])

    def test_circulate_inbox_cc_only(self) -> None:
        session_service._session = self._session("u1")  # noqa: SLF001
        seed_tenant_if_empty(self._tenant)
        sess = self._session("u1")
        doc = wf_svc.create_document(
            self._tenant,
            document_type=DOC_TYPE_GENERAL,
            title="공람 테스트",
            summary="본문",
            session=self._session("u2"),
            cc_user_ids=["u1"],
        )
        wf_svc.submit_document(
            self._tenant,
            doc["id"],
            [{"approver_id": "u2", "approver_role": "admin"}],
            session=self._session("u2"),
        )
        submitted = wf_svc.get_document(self._tenant, doc["id"], session=sess)
        self.assertTrue(
            matches_inbox(submitted, "circulate", session=sess, tenant_id=self._tenant)
        )
        counts = wf_svc.inbox_counts(self._tenant, session=sess)
        self.assertIn("circulate", counts)


class GwMailFolderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_ws.start()
        session_service._session = UserSession(  # noqa: SLF001
            user_id="u1",
            tenant_id="t1",
            username="u1",
            display_name="테스터",
            role="admin",
        )

    def tearDown(self) -> None:
        self._patch_ws.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_mail_folders(self) -> None:
        sess = session_service.get_session()
        assert sess is not None
        ws.add_mail("받은편지", "내용", folder="inbox", session=sess)
        ws.add_mail("보낸편지", "내용", folder="sent", session=sess)
        inbox = ws.list_mail(sess, folder="inbox")
        sent = ws.list_mail(sess, folder="sent")
        self.assertEqual(len(inbox), 1)
        self.assertEqual(len(sent), 1)
        self.assertEqual(ws.unread_mail_count(sess), 1)
