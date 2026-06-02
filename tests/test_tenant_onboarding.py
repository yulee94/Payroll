"""
tests/test_tenant_onboarding.py - 첫 로그인 온보딩·Bitween 로그인 브랜딩
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import BITWEEN_LOGO_PATH
from core.roles import ROLE_ADMIN, ROLE_STAFF
from core.session_service import UserSession, login, logout
from core.tenant_store import (
    create_tenant,
    mark_onboarding_completed,
    tenant_needs_onboarding,
    update_tenant,
)
from core.user_store import register_user
from ui.brand_assets import resolve_bitween_logo_path
from ui.onboarding_wizard import should_show_tenant_onboarding


class TenantOnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        users_file = self._root / "users" / "registry.json"
        users_file.parent.mkdir(parents=True)
        users_file.write_text(json.dumps({"users": {}, "by_tenant": {}}), encoding="utf-8")
        tenants_file = self._root / "tenants.json"
        tenants_file.write_text(
            json.dumps({"active_tenant_id": "newco", "tenants": {}}),
            encoding="utf-8",
        )

        self._patches = [
            patch("core.user_store.USERS_FILE", users_file),
            patch("core.user_store.app_data_dir", return_value=self._root),
            patch("core.tenant_store.TENANTS_FILE", tenants_file),
            patch("core.tenant_store.TENANT_LOGOS_DIR", self._root / "tenant_logos"),
            patch("core.tenant_store.app_data_dir", return_value=self._root),
            patch("core.session_service.SESSION_FILE", self._root / "session.json"),
            patch("core.session_service.app_data_dir", return_value=self._root),
        ]
        for p in self._patches:
            p.start()

        create_tenant(
            tenant_id="newco",
            display_name="New Co",
            login_id="newco",
            set_active=True,
        )
        self.admin = register_user(
            tenant_id="newco",
            username="admin",
            password="pass1234",
            display_name="관리자",
            role=ROLE_ADMIN,
        )
        self.staff = register_user(
            tenant_id="newco",
            username="staff",
            password="pass1234",
            display_name="직원",
            role=ROLE_STAFF,
        )

    def tearDown(self) -> None:
        logout(clear_saved=True)
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_new_tenant_needs_onboarding(self) -> None:
        self.assertTrue(tenant_needs_onboarding("newco"))

    def test_completed_onboarding_skips(self) -> None:
        mark_onboarding_completed("newco")
        self.assertFalse(tenant_needs_onboarding("newco"))

    def test_profile_fill_completes_onboarding_flag(self) -> None:
        update_tenant(
            "newco",
            display_name_ko="(주)뉴코",
            contact="hr@newco.example",
        )
        mark_onboarding_completed("newco")
        self.assertFalse(tenant_needs_onboarding("newco"))

    def test_should_show_only_for_admin(self) -> None:
        login(self.admin, remember=False)
        self.assertTrue(should_show_tenant_onboarding())
        logout(clear_saved=True)
        login(self.staff, remember=False)
        self.assertFalse(should_show_tenant_onboarding())

    def test_bitween_logo_path_exists(self) -> None:
        path = resolve_bitween_logo_path()
        self.assertTrue(path.is_file())
        self.assertEqual(path, BITWEEN_LOGO_PATH)


if __name__ == "__main__":
    unittest.main()
