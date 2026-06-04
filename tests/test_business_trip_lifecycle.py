"""Business-trip lifecycle foundation contract tests."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.session_service import UserSession, logout
from core.workflow import service as wf_svc
from core.workflow.business_trip import (
    TRIP_SOURCE_KEYS,
    TRIP_VIEW_MODEL_KEYS,
    business_trip_view_model,
    can_transition_trip_status,
    default_business_trip_record,
    transition_trip_status,
)
from core.workflow.constants import (
    DOC_STATUS_SUBMITTED,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    KPI_REFLECTION_STATUSES,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_PLANNED,
    TRIP_STATUSES,
)
from core.workflow.permissions import can_view_business_trip_lifecycle
from core.workflow.store import _load_raw, _save_raw


class BusinessTripLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._tenant = "trip_tenant"
        self._patch_root = patch("core.workflow.store.WORKFLOW_ROOT", Path(self._tmpdir) / "workflow")
        self._patch_root.start()

    def tearDown(self) -> None:
        self._patch_root.stop()
        logout()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _session(self, uid: str, role: str = "staff") -> UserSession:
        return UserSession(
            user_id=uid,
            tenant_id=self._tenant,
            username=uid,
            display_name=uid,
            role=role,
        )

    def test_status_taxonomy_separates_document_and_kpi_states(self) -> None:
        self.assertEqual(
            TRIP_STATUSES,
            (
                "draft",
                "planned",
                "approved",
                "in_progress",
                "diary_due",
                "overdue",
                "completed",
                "cancelled",
            ),
        )
        self.assertNotIn(DOC_STATUS_SUBMITTED, TRIP_STATUSES)
        self.assertNotIn(KPI_REFLECTION_REFLECTED, TRIP_STATUSES)
        self.assertEqual(KPI_REFLECTION_STATUSES, ("blocked", "ready", "reflected", "not_applicable"))

    def test_store_defaults_and_migration_freeze_shape(self) -> None:
        _save_raw(
            self._tenant,
            {
                "version": 1,
                "documents": [],
                "business_trips": [
                    {
                        "id": "legacy-id",
                        "title": "Legacy trip",
                        "status": "unknown",
                        "source": {"kind": "workflow", "document_id": "doc-1"},
                    }
                ],
            },
        )
        db = _load_raw(self._tenant)
        self.assertIn("business_trips", db)
        self.assertIn("business_trip_seq", db)
        migrated = db["business_trips"][0]
        self.assertEqual(migrated["trip_id"], "legacy-id")
        self.assertEqual(migrated["tenant_id"], self._tenant)
        self.assertEqual(migrated["status"], TRIP_STATUS_DRAFT)
        self.assertEqual(migrated["dedupe_key"], "doc-1")
        self.assertEqual(tuple(business_trip_view_model(migrated).keys()), TRIP_VIEW_MODEL_KEYS)
        self.assertEqual(TRIP_SOURCE_KEYS, ("kind", "document_id", "dedupe_key"))

    def test_store_surfaces_business_trip_migration_failures(self) -> None:
        _save_raw(self._tenant, {"business_trips": [{"trip_id": "bad"}]})

        with patch("core.workflow.business_trip.migrate_business_trips", side_effect=RuntimeError("migration boom")):
            with self.assertRaisesRegex(RuntimeError, "migration boom"):
                _load_raw(self._tenant)

    def test_state_machine_allows_approved_path_only(self) -> None:
        self.assertTrue(can_transition_trip_status(TRIP_STATUS_DRAFT, TRIP_STATUS_PLANNED))
        self.assertFalse(can_transition_trip_status(TRIP_STATUS_DRAFT, TRIP_STATUS_COMPLETED))
        record = default_business_trip_record(self._tenant, trip_id="trip-1", status=TRIP_STATUS_APPROVED)
        in_progress = transition_trip_status(record, TRIP_STATUS_IN_PROGRESS)
        self.assertFalse(can_transition_trip_status(TRIP_STATUS_IN_PROGRESS, TRIP_STATUS_COMPLETED))
        diary_due = transition_trip_status(in_progress, TRIP_STATUS_DIARY_DUE)
        completed = transition_trip_status(diary_due, TRIP_STATUS_COMPLETED)
        self.assertEqual(completed["status"], TRIP_STATUS_COMPLETED)
        self.assertEqual(completed["kpi_reflection_status"], KPI_REFLECTION_READY)
        with self.assertRaises(ValueError):
            transition_trip_status(record, TRIP_STATUS_COMPLETED)

    def test_visibility_predicate_is_tenant_bound_and_viewer_is_not_global(self) -> None:
        db = _load_raw(self._tenant)
        db["user_profiles"] = [
            {"user_id": "viewer", "workflow_roles": ["viewer"], "site_ids": ["site-a"], "department_ids": []},
            {"user_id": "manager", "workflow_roles": ["site_manager"], "site_ids": ["site-a"], "department_ids": []},
            {"user_id": "direct-manager", "workflow_roles": [], "site_ids": [], "department_ids": []},
            {
                "user_id": "dept-manager",
                "workflow_roles": ["department_manager"],
                "site_ids": [],
                "department_ids": ["dept-a"],
            },
            {"user_id": "requester", "manager_user_id": "direct-manager", "workflow_roles": []},
        ]
        _save_raw(self._tenant, db)
        trip = default_business_trip_record(
            self._tenant,
            trip_id="trip-visible",
            requester_id="requester",
            executor_id="executor",
            site_id="site-a",
            department_id="dept-a",
        )
        self.assertFalse(can_view_business_trip_lifecycle(self._session("viewer"), trip, tenant_id=self._tenant))
        self.assertTrue(can_view_business_trip_lifecycle(self._session("manager"), trip, tenant_id=self._tenant))
        self.assertTrue(can_view_business_trip_lifecycle(self._session("direct-manager"), trip, tenant_id=self._tenant))
        self.assertTrue(can_view_business_trip_lifecycle(self._session("dept-manager"), trip, tenant_id=self._tenant))
        self.assertTrue(can_view_business_trip_lifecycle(self._session("requester"), trip, tenant_id=self._tenant))
        self.assertTrue(can_view_business_trip_lifecycle(self._session("admin", role="admin"), trip, tenant_id=self._tenant))
        self.assertFalse(can_view_business_trip_lifecycle(self._session("admin", role="admin"), trip, tenant_id="other"))

    def test_service_upsert_is_idempotent_by_source_dedupe_key(self) -> None:
        sess = self._session("requester")
        first = wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "title": "서울 출장",
                "status": TRIP_STATUS_PLANNED,
                "source": {"kind": "workflow", "document_id": "doc-1", "dedupe_key": "trip:doc-1"},
            },
            session=sess,
        )
        second = wf_svc.upsert_business_trip_lifecycle(
            self._tenant,
            fields={
                "title": "서울 출장 수정",
                "source": {"kind": "workflow", "document_id": "doc-1", "dedupe_key": "trip:doc-1"},
            },
            session=sess,
        )
        self.assertEqual(first["trip_id"], second["trip_id"])
        self.assertEqual(second["title"], "서울 출장 수정")
        self.assertEqual(len(wf_svc.list_business_trips(self._tenant, session=sess)), 1)


if __name__ == "__main__":
    unittest.main()
