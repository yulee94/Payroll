"""Business-trip lifecycle foundation contract tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.workflow import constants as c
from core.workflow.business_trip import (
    TRIP_SOURCE_KEYS,
    TRIP_VIEW_MODEL_KEYS,
    business_trip_view_model,
    can_transition_trip_status,
    default_business_trip_record,
    find_business_trip_by_source,
    migrate_business_trip_record,
    migrate_business_trips,
    normalize_trip_source,
    transition_trip_status,
)
from core.workflow.permissions import can_view_business_trip_lifecycle


class BusinessTripLifecycleContractTests(unittest.TestCase):
    def test_status_taxonomy_is_frozen_and_separate_from_kpi_reflection(self) -> None:
        self.assertEqual(
            c.TRIP_STATUSES,
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
        self.assertEqual(c.KPI_REFLECTION_STATUSES, ("blocked", "ready", "reflected", "not_applicable"))
        self.assertNotIn(c.KPI_REFLECTION_READY, c.TRIP_STATUSES)
        self.assertNotIn(c.KPI_REFLECTION_REFLECTED, c.TRIP_STATUSES)

        trip = default_business_trip_record("tenant-a", status=c.TRIP_STATUS_IN_PROGRESS)
        completed = transition_trip_status(trip, c.TRIP_STATUS_COMPLETED)

        self.assertEqual(completed["status"], c.TRIP_STATUS_COMPLETED)
        self.assertEqual(completed["kpi_reflection_status"], c.KPI_REFLECTION_READY)
        self.assertNotEqual(completed["status"], completed["kpi_reflection_status"])

    def test_migration_defaults_preserve_trip_id_and_view_model_shape(self) -> None:
        legacy = {
            "id": "legacy-1",
            "tenant_id": "",
            "status": "unknown-status",
            "source": {"kind": "bad", "document_id": "DOC-7"},
            "legacy_note": "kept",
        }

        migrated = migrate_business_trip_record("tenant-a", legacy)
        view = business_trip_view_model(migrated)

        self.assertEqual(migrated["id"], "legacy-1")
        self.assertEqual(migrated["trip_id"], "legacy-1")
        self.assertEqual(migrated["tenant_id"], "tenant-a")
        self.assertEqual(migrated["status"], c.TRIP_STATUS_DRAFT)
        self.assertEqual(migrated["kpi_reflection_status"], c.KPI_REFLECTION_BLOCKED)
        self.assertEqual(migrated["source"], {"kind": c.TRIP_SOURCE_KIND_MANUAL, "document_id": "DOC-7", "dedupe_key": "DOC-7"})
        self.assertEqual(migrated["dedupe_key"], "DOC-7")
        self.assertEqual(migrated["legacy_note"], "kept")
        self.assertEqual(tuple(view.keys()), TRIP_VIEW_MODEL_KEYS)
        self.assertNotIn("legacy_note", view)

    def test_store_migration_adds_business_trip_collection_and_normalizes_rows(self) -> None:
        db = {"business_trips": [{"id": "trip-1", "status": c.TRIP_STATUS_APPROVED}], "business_trip_seq": 0}

        changed = migrate_business_trips(db, "tenant-a")

        self.assertTrue(changed)
        self.assertEqual(db["business_trip_seq"], 0)
        self.assertEqual(db["business_trips"][0]["trip_id"], "trip-1")
        self.assertEqual(db["business_trips"][0]["tenant_id"], "tenant-a")
        self.assertEqual(db["business_trips"][0]["kpi_reflection_status"], c.KPI_REFLECTION_BLOCKED)

    def test_tenant_bound_visibility_matrix_basics(self) -> None:
        trip = default_business_trip_record(
            "tenant-a",
            requester_id="requester-1",
            executor_id="executor-1",
            site_id="site-1",
            department_id="dept-1",
        )
        profiles = {
            "admin-1": {"workflow_roles": [c.WF_ROLE_ADMIN]},
            "viewer-1": {"workflow_roles": [c.WF_ROLE_VIEWER]},
            "site-manager-1": {"workflow_roles": [c.WF_ROLE_SITE_MANAGER], "site_ids": ["site-1"]},
            "dept-hr-1": {"workflow_roles": [c.WF_ROLE_HR], "department_ids": ["dept-1"]},
        }

        with patch("core.workflow.permissions.get_user_profile", side_effect=lambda _tenant, uid: profiles.get(uid)):
            self.assertTrue(can_view_business_trip_lifecycle({"user_id": "admin-1"}, trip, tenant_id="tenant-a"))
            self.assertTrue(can_view_business_trip_lifecycle({"user_id": "requester-1"}, trip, tenant_id="tenant-a"))
            self.assertTrue(can_view_business_trip_lifecycle({"user_id": "executor-1"}, trip, tenant_id="tenant-a"))
            self.assertTrue(can_view_business_trip_lifecycle({"user_id": "site-manager-1"}, trip, tenant_id="tenant-a"))
            self.assertTrue(can_view_business_trip_lifecycle({"user_id": "dept-hr-1"}, trip, tenant_id="tenant-a"))
            self.assertFalse(can_view_business_trip_lifecycle({"user_id": "viewer-1"}, trip, tenant_id="tenant-a"))
            self.assertFalse(can_view_business_trip_lifecycle({"user_id": "admin-1"}, trip, tenant_id="tenant-b"))

    def test_source_and_dedupe_key_shape_supports_import_idempotency(self) -> None:
        source = normalize_trip_source(
            {"kind": c.TRIP_SOURCE_KIND_GW_IMPORT, "document_id": "GW-42", "dedupe_key": "gw:GW-42"}
        )
        trip = default_business_trip_record("tenant-a", source=source)
        db = {"business_trips": [trip]}

        self.assertEqual(tuple(source.keys()), TRIP_SOURCE_KEYS)
        self.assertEqual(trip["dedupe_key"], "gw:GW-42")
        self.assertIs(find_business_trip_by_source(db, source={"kind": c.TRIP_SOURCE_KIND_GW_IMPORT, "dedupe_key": "gw:GW-42"}), trip)
        self.assertIs(find_business_trip_by_source(db, source={"document_id": "GW-42"}), trip)
        self.assertIsNone(find_business_trip_by_source(db, source={"document_id": "GW-99"}))

    def test_status_state_machine_rejects_skipping_required_lifecycle_steps(self) -> None:
        self.assertTrue(can_transition_trip_status(c.TRIP_STATUS_DRAFT, c.TRIP_STATUS_PLANNED))
        self.assertFalse(can_transition_trip_status(c.TRIP_STATUS_DRAFT, c.TRIP_STATUS_COMPLETED))

        trip = default_business_trip_record("tenant-a", status=c.TRIP_STATUS_DRAFT)
        with self.assertRaises(ValueError):
            transition_trip_status(trip, c.TRIP_STATUS_COMPLETED)


if __name__ == "__main__":
    unittest.main()
