"""
tests/test_compliance_docs.py - 법정·규정 문서함
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.compliance_docs.categories import (
    CATEGORY_BYLAWS,
    CATEGORY_CPR_FIRST_AID,
    CATEGORY_MINIMUM_WAGE,
)
from core.compliance_docs.permissions import (
    can_manage_compliance_docs,
    can_view_compliance_docs,
)
from core.compliance_docs.store import (
    acknowledge_document,
    get_document,
    has_acknowledged,
    list_documents,
    upload_document,
)
from core.org_positions import POS_CEO, POS_MEMBER
from core.roles import ROLE_ADMIN, ROLE_STAFF
from core.session_service import UserSession, login, logout
from core.tenant_store import create_tenant
from core.user_store import register_user


class ComplianceDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        users_file = self._root / "users" / "registry.json"
        users_file.parent.mkdir(parents=True)
        users_file.write_text(json.dumps({"users": {}, "by_tenant": {}}), encoding="utf-8")
        tenants_file = self._root / "tenants.json"
        tenants_file.write_text(
            json.dumps({"active_tenant_id": "tenant_a", "tenants": {}}),
            encoding="utf-8",
        )

        self._patches = [
            patch("core.user_store.USERS_FILE", users_file),
            patch("core.user_store.app_data_dir", return_value=self._root),
            patch("core.compliance_docs.store.app_data_dir", return_value=self._root),
            patch("core.tenant_store.TENANTS_FILE", tenants_file),
            patch("core.tenant_store.TENANT_LOGOS_DIR", self._root / "tenant_logos"),
            patch("core.tenant_store.app_data_dir", return_value=self._root),
        ]
        for p in self._patches:
            p.start()

        create_tenant(
            tenant_id="tenant_a",
            display_name="Tenant A",
            login_id="tenant_a",
            set_active=True,
        )
        create_tenant(
            tenant_id="tenant_b",
            display_name="Tenant B",
            login_id="tenant_b",
        )

        self.hr_admin = register_user(
            tenant_id="tenant_a",
            username="hr_admin",
            password="pass1234",
            display_name="HR관리",
            position=POS_CEO,
            role=ROLE_ADMIN,
        )
        self.staff_a = register_user(
            tenant_id="tenant_a",
            username="staff_a",
            password="pass1234",
            display_name="직원A",
            position=POS_MEMBER,
            role=ROLE_STAFF,
        )
        self.staff_b = register_user(
            tenant_id="tenant_b",
            username="staff_b",
            password="pass1234",
            display_name="직원B",
            position=POS_MEMBER,
            role=ROLE_STAFF,
        )

        self._sample = self._root / "sample.pdf"
        self._sample.write_bytes(b"%PDF-1.4 test")

    def tearDown(self) -> None:
        logout(clear_saved=False)
        for p in reversed(self._patches):
            p.stop()
        self._tmpdir.cleanup()

    def _login(self, user) -> UserSession:
        logout(clear_saved=False)
        return login(user, remember=False)

    def test_upload_and_list(self) -> None:
        self._login(self.hr_admin)
        doc = upload_document(
            category=CATEGORY_BYLAWS,
            title="COSS 정관",
            description="2024 개정",
            effective_date="2024-01-01",
            source_path=self._sample,
        )
        self.assertEqual(doc["title"], "COSS 정관")
        self.assertTrue(doc["is_active"])

        rows = list_documents(category=CATEGORY_BYLAWS)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], doc["id"])

        stored = self._root / "compliance_docs" / "tenant_a" / "files" / f"{doc['id']}.pdf"
        self.assertTrue(stored.is_file())

    def test_tenant_isolation(self) -> None:
        self._login(self.hr_admin)
        upload_document(
            category=CATEGORY_BYLAWS,
            title="A법인 정관",
            source_path=self._sample,
        )

        self._login(self.staff_b)
        self.assertTrue(can_view_compliance_docs())
        rows_b = list_documents()
        self.assertEqual(rows_b, [])

        got = get_document("nonexistent")
        self.assertIsNone(got)

    def test_category_filter(self) -> None:
        self._login(self.hr_admin)
        upload_document(category=CATEGORY_BYLAWS, title="정관", source_path=self._sample)
        upload_document(category=CATEGORY_MINIMUM_WAGE, title="최저임금", source_path=self._sample)

        statutory = list_documents(category=CATEGORY_MINIMUM_WAGE)
        self.assertEqual(len(statutory), 1)
        self.assertEqual(statutory[0]["title"], "최저임금")

    def test_acknowledgment(self) -> None:
        self._login(self.hr_admin)
        doc = upload_document(
            category=CATEGORY_CPR_FIRST_AID,
            title="심폐소생술 교육",
            source_path=self._sample,
        )
        doc_id = doc["id"]

        self._login(self.staff_a)
        self.assertFalse(has_acknowledged(doc_id))
        self.assertTrue(can_view_compliance_docs())
        self.assertFalse(can_manage_compliance_docs())

        ack = acknowledge_document(doc_id)
        self.assertIn("acknowledged_at", ack)
        self.assertTrue(has_acknowledged(doc_id))

    def test_staff_cannot_upload(self) -> None:
        self._login(self.staff_a)
        self.assertFalse(can_manage_compliance_docs())
        with self.assertRaises(PermissionError):
            upload_document(
                category=CATEGORY_BYLAWS,
                title="무단 업로드",
                source_path=self._sample,
            )


if __name__ == "__main__":
    unittest.main()
