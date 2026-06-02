"""
tests/test_org_access.py - 조직·직위 기반 접근 제어
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.org_positions import POS_CEO, POS_MEMBER, POS_MANAGER
from core.org_store import import_org_tree, list_units
from core.org_access import (
    can_access_platform,
    can_manage_org,
    user_permissions,
)
from core.roles import ROLE_STAFF
from core.session_service import UserSession, login, logout
from core.user_store import register_user, update_user_org


class OrgAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        users_file = self._root / "users" / "registry.json"
        users_file.parent.mkdir(parents=True)
        users_file.write_text(json.dumps({"users": {}, "by_tenant": {}}), encoding="utf-8")
        org_dir = self._root / "org"
        org_dir.mkdir(parents=True)

        self._patches = [
            patch("core.user_store.USERS_FILE", users_file),
            patch("core.user_store.app_data_dir", return_value=self._root),
            patch("core.org_store.ORG_DIR", org_dir),
            patch("core.org_store.app_data_dir", return_value=self._root),
        ]
        for p in self._patches:
            p.start()

        import_org_tree(
            "coss",
            [
                {
                    "unit_id": "root",
                    "name": "COSS",
                    "parent_id": "",
                    "platform_ids": ["payroll", "workflow"],
                },
                {
                    "unit_id": "finance",
                    "name": "재무팀",
                    "parent_id": "root",
                    "platform_ids": ["payroll", "accounting"],
                },
                {
                    "unit_id": "maint",
                    "name": "정비팀",
                    "parent_id": "root",
                    "platform_ids": ["maintenance"],
                },
            ],
            root_id="root",
        )

        self.ceo = register_user(
            tenant_id="coss",
            username="ceo_test",
            password="pass1234",
            display_name="대표",
            org_unit_id="root",
            position=POS_CEO,
            role="admin",
        )
        self.finance_mgr = register_user(
            tenant_id="coss",
            username="fin_mgr",
            password="pass1234",
            display_name="재무팀장",
            org_unit_id="finance",
            position=POS_MANAGER,
            role="finance",
            manager_user_id=self.ceo.user_id,
        )
        self.maint_member = register_user(
            tenant_id="coss",
            username="maint1",
            password="pass1234",
            display_name="정비담당",
            org_unit_id="maint",
            position=POS_MEMBER,
            role=ROLE_STAFF,
            manager_user_id=self.ceo.user_id,
        )

    def tearDown(self) -> None:
        logout(clear_saved=False)
        for p in reversed(self._patches):
            p.stop()
        self._tmpdir.cleanup()

    def test_ceo_has_all_platforms(self) -> None:
        perms = user_permissions(self.ceo.user_id)
        self.assertTrue(can_access_platform("payroll", session=UserSession.from_record(self.ceo)))
        self.assertTrue(can_access_platform("maintenance", session=UserSession.from_record(self.ceo)))
        self.assertTrue(can_manage_org(UserSession.from_record(self.ceo)))
        self.assertIn("platform.accounting", perms)

    def test_team_platform_scoping(self) -> None:
        login(self.finance_mgr, remember=False)
        self.assertTrue(can_access_platform("payroll"))
        self.assertTrue(can_access_platform("accounting"))
        self.assertFalse(can_access_platform("maintenance"))
        logout(clear_saved=False)

        login(self.maint_member, remember=False)
        self.assertFalse(can_access_platform("payroll"))
        self.assertTrue(can_access_platform("maintenance"))
        self.assertFalse(can_access_platform("accounting"))

    def test_org_tree_imported(self) -> None:
        units = list_units("coss")
        self.assertEqual(len(units), 3)


if __name__ == "__main__":
    unittest.main()
