"""tests/test_bulletin.py - 그룹 공유게시판"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.bulletin import service as bulletin
from core.bulletin.service import Announcement, BulletinVisibility
from core.session_service import UserSession


def _sess(tenant_id: str = "coss", role: str = "admin") -> UserSession:
    return UserSession(
        user_id="u1",
        tenant_id=tenant_id,
        username="admin",
        display_name="관리자",
        role=role,
    )


class TestBulletinVisibility(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store = Path(self._tmpdir) / "announcements.json"
        bulletin.reset_store_for_tests(self._store)

    def _ann(self, vis: BulletinVisibility, **kw) -> Announcement:
        return Announcement(
            id="a1",
            title=kw.get("title", "테스트"),
            body=kw.get("body", "내용"),
            author_user_id="u1",
            author_name="관리자",
            author_tenant_id="coss",
            author_org="(주)코스",
            created_at="2026-06-01T10:00:00",
            updated_at="2026-06-01T10:00:00",
            pinned=False,
            visibility=vis,
        )

    def test_group_wide_visible_all_tenants(self) -> None:
        ann = self._ann(BulletinVisibility(all_group=True))
        self.assertTrue(bulletin.is_visible_to(ann, tenant_id="elso", site_ids=[]))
        self.assertTrue(bulletin.is_visible_to(ann, tenant_id="coss", site_ids=["site_hq"]))

    def test_tenant_filter(self) -> None:
        ann = self._ann(BulletinVisibility(tenants=["coss"]))
        self.assertTrue(bulletin.is_visible_to(ann, tenant_id="coss", site_ids=[]))
        self.assertFalse(bulletin.is_visible_to(ann, tenant_id="elso", site_ids=[]))

    def test_site_filter(self) -> None:
        vis = BulletinVisibility(
            sites=[{"tenant_id": "coss", "site_id": "site_miryang"}],
        )
        ann = self._ann(vis)
        self.assertTrue(
            bulletin.is_visible_to(ann, tenant_id="coss", site_ids=["site_miryang"])
        )
        self.assertFalse(
            bulletin.is_visible_to(ann, tenant_id="coss", site_ids=["site_hq"])
        )
        self.assertFalse(bulletin.is_visible_to(ann, tenant_id="coss", site_ids=[]))
        self.assertFalse(bulletin.is_visible_to(ann, tenant_id="elso", site_ids=["site_miryang"]))

    def test_combined_tenant_and_site(self) -> None:
        vis = BulletinVisibility(
            tenants=["elso"],
            sites=[{"tenant_id": "coss", "site_id": "site_hq"}],
        )
        ann = self._ann(vis)
        self.assertTrue(bulletin.is_visible_to(ann, tenant_id="elso", site_ids=[]))
        self.assertTrue(
            bulletin.is_visible_to(ann, tenant_id="coss", site_ids=["site_hq"])
        )
        self.assertFalse(
            bulletin.is_visible_to(ann, tenant_id="coss", site_ids=["site_miryang"])
        )


class TestBulletinCrud(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._store = Path(self._tmpdir) / "announcements.json"
        bulletin.reset_store_for_tests(self._store)

    @patch.object(bulletin, "can_post_bulletin", return_value=True)
    @patch.object(bulletin, "can_post_group_wide", return_value=True)
    @patch.object(bulletin, "_is_group_hq_tenant", return_value=True)
    def test_create_and_list(self, *_mocks) -> None:
        sess = _sess()
        ann = bulletin.create_announcement(
            title="본사 공지",
            body="전체 그룹 안내",
            visibility=BulletinVisibility(all_group=True),
            session=sess,
        )
        self.assertTrue(ann.id)
        listed = bulletin.list_announcements_for_viewer(
            tenant_id="elso",
            user_id="u2",
        )
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].title, "본사 공지")

    @patch.object(bulletin, "can_post_bulletin", return_value=True)
    @patch.object(bulletin, "can_post_group_wide", return_value=False)
    def test_tenant_admin_scope_restriction(self, *_mocks) -> None:
        sess = _sess(tenant_id="elso")
        with self.assertRaises(ValueError):
            bulletin.create_announcement(
                title="타 법인",
                body="불가",
                visibility=BulletinVisibility(tenants=["coss"]),
                session=sess,
            )

    @patch.object(bulletin, "can_post_bulletin", return_value=True)
    @patch.object(bulletin, "can_post_group_wide", return_value=False)
    def test_tenant_admin_own_tenant(self, *_mocks) -> None:
        sess = _sess(tenant_id="elso")
        ann = bulletin.create_announcement(
            title="엘소 공지",
            body="법인 내부",
            visibility=BulletinVisibility(tenants=["elso"]),
            session=sess,
        )
        self.assertEqual(ann.visibility.tenants, ["elso"])
        visible = bulletin.list_announcements_for_viewer(tenant_id="elso", user_id="u2")
        hidden = bulletin.list_announcements_for_viewer(tenant_id="coss", user_id="u1")
        self.assertEqual(len(visible), 1)
        self.assertEqual(len(hidden), 0)


class TestScopeFormatting(unittest.TestCase):
    def test_preview_all_group(self) -> None:
        text = bulletin.format_scope_preview(BulletinVisibility(all_group=True))
        self.assertIn("전체 그룹", text)

    def test_badge_counts(self) -> None:
        vis = BulletinVisibility(tenants=["coss", "elso"], sites=[{"tenant_id": "coss", "site_id": "s1"}])
        badge = bulletin.format_scope_badge(vis)
        self.assertIn("법인 2", badge)
        self.assertIn("사업장 1", badge)


if __name__ == "__main__":
    unittest.main()
