"""COSS 양식함·작성 스키마 테스트."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.workflow.form_templates import (
    COSS_BUILTIN_TEMPLATES,
    ensure_form_templates,
    get_template,
    list_templates,
    merge_gw_templates,
    resolve_template_schema,
    templates_path,
)
from core.workflow.forms import get_form_schema, validate_form_values
from core.workflow.constants import DOC_TYPE_BUSINESS_TRIP_REQUEST, DOC_TYPE_EXPENSE, DOC_TYPE_GENERAL


class TestFormTemplates(unittest.TestCase):
    def test_merge_builtin_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                stats = merge_gw_templates("test_tenant")
                self.assertGreaterEqual(stats["total"], len(COSS_BUILTIN_TEMPLATES))
                path = templates_path("test_tenant")
                self.assertTrue(path.is_file())
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(data.get("templates") or []), 20)

    def test_all_builtin_templates_have_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t_builtin")
                for row in list_templates("t_builtin"):
                    fields = row.get("fields") or []
                    self.assertGreater(
                        len(fields),
                        0,
                        msg=f"{row.get('name')} has no fields",
                    )

    def test_fuel_expense_template_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t1")
                tpl = get_template("t1", "coss_유류비_지출품의서")
                self.assertIsNotNone(tpl)
                assert tpl is not None
                self.assertEqual(tpl["document_type"], DOC_TYPE_EXPENSE)
                fields = resolve_template_schema("t1", tpl["id"])
                self.assertIsNotNone(fields)
                assert fields is not None
                keys = {f.key for f in fields}
                self.assertIn("vehicle", keys)
                self.assertIn("total_amount", keys)

    def test_business_trip_request_template_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t_trip")
                tpl = get_template("t_trip", "coss_출장신청서")
                self.assertIsNotNone(tpl)
                assert tpl is not None
                self.assertEqual(tpl["document_type"], DOC_TYPE_BUSINESS_TRIP_REQUEST)
                fields = resolve_template_schema("t_trip", tpl["id"])
                self.assertIsNotNone(fields)
                assert fields is not None
                keys = {f.key for f in fields}
                self.assertIn("destination", keys)
                self.assertIn("business_trip_purpose", keys)
                self.assertIn("executor_id", keys)

    def test_trip_report_template_links_to_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t_report")
                tpl = get_template("t_report", "coss_출장보고서")
                self.assertIsNotNone(tpl)
                assert tpl is not None
                self.assertEqual(tpl["document_type"], DOC_TYPE_GENERAL)
                fields = resolve_template_schema("t_report", tpl["id"])
                assert fields is not None
                trip_fields = [f for f in fields if f.key == "trip_id"]
                self.assertEqual(len(trip_fields), 1)
                self.assertTrue(trip_fields[0].required)
                self.assertEqual(trip_fields[0].maps_to, "trip_id")
                keys = {f.key for f in fields}
                self.assertIn("source_document_id", keys)

    def test_trip_linked_diary_template_keeps_optional_trip_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t_diary")
                tpl = get_template("t_diary", "coss_일일업무일지")
                self.assertIsNotNone(tpl)
                assert tpl is not None
                fields = resolve_template_schema("t_diary", tpl["id"])
                assert fields is not None
                trip_fields = [f for f in fields if f.key == "trip_id"]
                self.assertEqual(len(trip_fields), 1)
                self.assertFalse(trip_fields[0].required)
                self.assertEqual(trip_fields[0].maps_to, "trip_id")

    def test_validate_with_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t2")
                tpl = get_template("t2", "coss_유류비_지출품의서")
                assert tpl
                dtype = tpl["document_type"]
                errors = validate_form_values(
                    dtype,
                    {"title": "6월 유류비"},
                    tenant_id="t2",
                    template_id=tpl["id"],
                )
                self.assertTrue(any("금액" in e for e in errors))
                schema = get_form_schema(dtype, "t2", template_id=tpl["id"])
                self.assertGreater(len(schema), 3)

    def test_extra_gw_template_uses_fields_for_inferred_document_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", base / "workflow"):
                merge_gw_templates("t_extra", extra_names=["구매요청서_프로브", "출장신청_프로브"])
                purchase = next(t for t in list_templates("t_extra") if t["name"] == "구매요청서_프로브")
                trip = next(t for t in list_templates("t_extra") if t["name"] == "출장신청_프로브")
                self.assertNotEqual(purchase["document_type"], DOC_TYPE_BUSINESS_TRIP_REQUEST)
                purchase_keys = {f.key for f in resolve_template_schema("t_extra", purchase["id"]) or ()}
                trip_keys = {f.key for f in resolve_template_schema("t_extra", trip["id"]) or ()}
                self.assertIn("total_amount", purchase_keys)
                self.assertNotIn("business_trip_purpose", purchase_keys)
                self.assertNotIn("destination", purchase_keys)
                self.assertEqual(trip["document_type"], DOC_TYPE_BUSINESS_TRIP_REQUEST)
                self.assertIn("business_trip_purpose", trip_keys)

    def test_affiliate_tenant_resolves_group_workflow_templates(self) -> None:
        """계열사 로그인 ID로 조회해도 루트(coss) 양식함 필드를 불러온다."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wf_root = base / "workflow"
            with mock.patch("core.workflow.form_templates.WORKFLOW_ROOT", wf_root):
                merge_gw_templates("coss")
                with mock.patch(
                    "core.group_store.get_workflow_tenant_id",
                    side_effect=lambda tid: "coss" if tid == "elso" else tid,
                ):
                    ensure_form_templates("elso")
                    tpl = get_template("elso", "coss_기안서")
                    self.assertIsNotNone(tpl)
                    assert tpl is not None
                    schema = get_form_schema(
                        tpl["document_type"],
                        "elso",
                        template_id="coss_기안서",
                    )
                    keys = {f.key for f in schema}
                    self.assertIn("purpose", keys)
                    self.assertIn("content", keys)
                    self.assertGreaterEqual(len(schema), 5)


if __name__ == "__main__":
    unittest.main()
