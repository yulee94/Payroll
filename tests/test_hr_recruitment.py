"""tests/test_hr_recruitment.py - 그룹 공유 채용공고 · 인재풀"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.group_store import GroupRecord
from core.hr import recruitment as rec


class TestApplicantDedupe(unittest.TestCase):
    def test_rrn_key(self) -> None:
        self.assertEqual(
            rec.applicant_dedupe_key(rrn="670204-2447413", name="홍길동", contact="010"),
            "rrn:6702042447413",
        )

    def test_name_phone_key(self) -> None:
        key = rec.applicant_dedupe_key(name="홍길동", contact="010-1234-5678")
        self.assertEqual(key, "np:홍길동:01012345678")


class TestHrRecruitmentSharing(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        root = Path(self._tmpdir)
        self._tenant_dir = root / "tenants"
        self._group_dir = root / "groups"
        self._groups_file = root / "groups_registry.json"

        patchers = [
            patch.object(rec, "_TENANT_DIR", self._tenant_dir),
            patch.object(rec, "_GROUP_DIR", self._group_dir),
            patch.object(rec, "_RECRUITMENT_ROOT", root),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

        self._group_patcher = patch(
            "core.hr.recruitment.get_group_for_tenant",
            side_effect=self._mock_group,
        )
        self._group_patcher.start()
        self.addCleanup(self._group_patcher.stop)

        self._tenant_patcher = patch(
            "core.hr.recruitment.get_tenant",
            side_effect=self._mock_tenant,
        )
        self._tenant_patcher.start()
        self.addCleanup(self._tenant_patcher.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _mock_group(self, tenant_id: str) -> GroupRecord | None:
        if tenant_id in ("coss", "elso"):
            return GroupRecord(
                group_id="test_group",
                name="Test Group",
                root_tenant_id="coss",
                tenant_ids=("coss", "elso"),
            )
        return None

    def _mock_tenant(self, tenant_id: str):
        names = {"coss": "COSS", "elso": "ELSO", "other": "Other"}
        if tenant_id not in names:
            return None

        class _T:
            display_name = names[tenant_id]
            display_name_ko = names[tenant_id]

        return _T()

    def test_create_posting_shared_within_group(self) -> None:
        posting = rec.create_posting(
            tenant_id="coss",
            department="인사",
            site="서울",
            title="HR 담당",
            description="채용 업무",
        )
        self.assertEqual(posting["status"], "open")

        coss_posts = rec.list_my_postings("coss")
        self.assertEqual(len(coss_posts), 1)

        elso_view = rec.list_group_postings("elso", include_own=False)
        self.assertEqual(len(elso_view), 1)
        self.assertEqual(elso_view[0]["title"], "HR 담당")
        self.assertEqual(elso_view[0]["source_tenant_id"], "coss")

        other_view = rec.list_group_postings("other", include_own=False)
        self.assertEqual(len(other_view), 0)

    def test_closed_posting_removed_from_group(self) -> None:
        posting = rec.create_posting(
            tenant_id="coss",
            department="재무",
            title="회계",
        )
        rec.update_posting(posting["id"], tenant_id="coss", status=rec.POSTING_STATUS_CLOSED)
        elso_view = rec.list_group_postings("elso", include_own=False)
        self.assertEqual(len(elso_view), 0)

    def test_talent_pool_visible_across_tenants(self) -> None:
        posting = rec.create_posting(
            tenant_id="coss",
            department="생산",
            title="기사",
        )
        applicant = rec.add_applicant(
            posting["id"],
            tenant_id="coss",
            name="김인재",
            contact="01011112222",
            rrn="9001011234567",
        )
        rec.update_applicant(
            applicant["id"],
            tenant_id="coss",
            status="talent_pool",
            recommended=True,
        )

        pool_elso = rec.list_talent_pool("elso")
        self.assertEqual(len(pool_elso), 1)
        self.assertEqual(pool_elso[0]["name"], "김인재")
        self.assertTrue(pool_elso[0]["recommended"])

    def test_rrn_dedup(self) -> None:
        posting = rec.create_posting(
            tenant_id="coss",
            department="영업",
            title="영업사원",
        )
        rec.add_applicant(
            posting["id"],
            tenant_id="coss",
            name="박지원",
            contact="01099998888",
            rrn="8001011000001",
        )
        dup = rec.find_duplicate_applicant(
            tenant_id="coss",
            rrn="800101-1000001",
            name="다른이름",
            contact="01000000000",
        )
        self.assertIsNotNone(dup)
        self.assertEqual(dup["name"], "박지원")

    def test_link_talent_to_posting(self) -> None:
        src_post = rec.create_posting(
            tenant_id="coss",
            department="IT",
            title="개발자",
        )
        src_app = rec.add_applicant(
            src_post["id"],
            tenant_id="coss",
            name="이개발",
            contact="01055556666",
        )
        rec.update_applicant(src_app["id"], tenant_id="coss", status="talent_pool")

        dst_post = rec.create_posting(
            tenant_id="elso",
            department="IT",
            title="SW 엔지니어",
        )
        pool = rec.list_talent_pool("elso")
        self.assertEqual(len(pool), 1)
        linked = rec.link_talent_to_posting(pool[0]["dedupe_key"], dst_post["id"], tenant_id="elso")
        self.assertEqual(linked["name"], "이개발")
        self.assertEqual(linked["ref_tenant_id"], "coss")
        self.assertIn("그룹 인재풀 참조", linked["resume_notes"])

        elso_apps = rec.list_applicants("elso")
        self.assertEqual(len(elso_apps), 1)


if __name__ == "__main__":
    unittest.main()
