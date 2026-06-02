"""사내 메신저 soft-delete·컴플라이언스 로그 테스트."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.session_service as session_service
from core.session_service import UserSession, logout
from core.user_store import UserRecord
from services import workspace_store as ws


def _user(uid: str, tenant: str, name: str) -> UserRecord:
    return UserRecord(
        user_id=uid,
        tenant_id=tenant,
        username=uid,
        display_name=name,
        role="staff",
    )


class MessengerSoftDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "test_messenger_tenant"
        self._patch_ws = patch("services.workspace_store.WORKSPACE_ROOT", Path(self._tmpdir) / "workspace")
        self._patch_ws.start()
        self._users = {
            "u1": _user("u1", self._tenant, "사용자1"),
            "u2": _user("u2", self._tenant, "사용자2"),
        }

        def _get_user(user_id: str) -> UserRecord | None:
            return self._users.get(user_id)

        self._patch_user = patch("services.workspace_store.get_user", side_effect=_get_user)
        self._patch_user.start()

    def tearDown(self) -> None:
        self._patch_user.stop()
        self._patch_ws.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self, user_id: str = "u1") -> UserSession:
        u = self._users[user_id]
        return UserSession(
            user_id=u.user_id,
            tenant_id=u.tenant_id,
            username=u.username,
            display_name=u.display_name,
            role=u.role,
        )

    def test_delete_message_hides_from_ui_feed_only_for_deleter(self) -> None:
        session_service._session = self._session("u1")  # noqa: SLF001
        ws.send_message("u2", "비밀 메시지", self._session("u1"))
        ws.send_message("u1", "답장", self._session("u2"))

        all_before = ws.get_thread_messages_all("u2", self._session("u1"))
        msg_id = all_before[0]["id"]

        ws.delete_message_for_user(msg_id, "u2", self._session("u1"))

        visible_u1 = ws.get_thread_messages("u2", self._session("u1"))
        visible_u2 = ws.get_thread_messages("u1", self._session("u2"))
        all_after = ws.get_thread_messages_all("u2", self._session("u1"))

        self.assertEqual(len(all_after), 2)
        self.assertEqual(len(visible_u1), 1)
        self.assertEqual(visible_u1[0]["text"], "답장")
        self.assertEqual(len(visible_u2), 2)
        self.assertNotIn(msg_id, [m.get("id") for m in visible_u1])

        hidden = all_after[0]["user_visibility"]["u1"]
        self.assertFalse(hidden["visible"])
        self.assertEqual(hidden["deleted_by"], "u1")
        self.assertTrue(hidden.get("deleted_at"))

    def test_server_record_persists_after_delete(self) -> None:
        session_service._session = self._session("u1")  # noqa: SLF001
        sent = ws.send_message("u2", "보관 대상", self._session("u1"))
        ws.delete_message_for_user(sent["id"], "u2", self._session("u1"))

        all_msgs = ws.get_thread_messages_all("u2", self._session("u1"))
        stored = next(m for m in all_msgs if m.get("id") == sent["id"])

        self.assertEqual(stored["text"], "보관 대상")
        self.assertIn("user_visibility", stored)
        self.assertFalse(stored["user_visibility"]["u1"]["visible"])

    def test_clear_thread_creates_audit_log(self) -> None:
        session_service._session = self._session("u1")  # noqa: SLF001
        ws.send_message("u2", "첫 메시지", self._session("u1"))
        ws.send_message("u2", "둘째 메시지", self._session("u1"))

        count = ws.clear_thread_for_user("u2", self._session("u1"))
        self.assertEqual(count, 2)
        self.assertEqual(ws.get_thread_messages("u2", self._session("u1")), [])

        events = ws.list_compliance_audit_events(self._tenant)
        actions = [e.get("action") for e in events]
        self.assertIn("thread_clear_for_user", actions)
        clear_evt = next(e for e in events if e.get("action") == "thread_clear_for_user")
        self.assertEqual(clear_evt.get("actor_user_id"), "u1")
        self.assertEqual(clear_evt.get("message_count"), 2)

    def test_single_delete_creates_audit_log(self) -> None:
        session_service._session = self._session("u1")  # noqa: SLF001
        sent = ws.send_message("u2", "감사 로그 테스트", self._session("u1"))
        ws.delete_message_for_user(sent["id"], "u2", self._session("u1"))

        events = ws.list_compliance_audit_events(self._tenant)
        evt = next(e for e in events if e.get("action") == "message_soft_delete")
        self.assertEqual(evt.get("message_id"), sent["id"])
        self.assertEqual(evt.get("actor_user_id"), "u1")
        self.assertIn("감사 로그 테스트", evt.get("text_preview", ""))


if __name__ == "__main__":
    unittest.main()
