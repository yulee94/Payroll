from __future__ import annotations

import json
import unittest

from services.payroll_api_adapter import build_payroll_api_request
from services.payroll_api_contract import (
    PAYROLL_API_ENDPOINT,
    PAYROLL_API_HEALTH_ENDPOINT,
    PAYROLL_API_READINESS_ENDPOINT,
    PAYROLL_API_VALIDATE_ENDPOINT,
    payroll_api_contract,
    payroll_api_request_example,
)


class PayrollApiContractTests(unittest.TestCase):
    def test_contract_is_json_serializable_and_versioned(self) -> None:
        contract = payroll_api_contract()

        json.dumps(contract, ensure_ascii=False)

        self.assertEqual(contract["version"], "v1")
        self.assertEqual(contract["http"]["method"], "POST")
        self.assertEqual(contract["http"]["path"], PAYROLL_API_ENDPOINT)
        self.assertEqual(contract["http"]["validation_path"], PAYROLL_API_VALIDATE_ENDPOINT)
        self.assertEqual(contract["http"]["health_path"], PAYROLL_API_HEALTH_ENDPOINT)
        self.assertEqual(contract["http"]["readiness_path"], PAYROLL_API_READINESS_ENDPOINT)
        self.assertIn("mixed", contract["input_types"])

    def test_contract_examples_build_internal_requests(self) -> None:
        for input_type in ("invoice", "attendance", "mixed"):
            with self.subTest(input_type=input_type):
                request = build_payroll_api_request(
                    payroll_api_request_example(input_type=input_type)
                )

                self.assertEqual(request.input_type, input_type)
                self.assertEqual(request.scope.period, "2026-05")
                self.assertEqual(request.tenant_id, "coss")

    def test_response_contract_never_exposes_exception(self) -> None:
        response = payroll_api_contract()["response"]

        self.assertIn("exception", response["never_include"])
        self.assertNotIn("exception", response["success"])
        self.assertNotIn("exception", response["error"])
        self.assertNotIn("exception", response["run_error"])

    def test_response_contract_declares_frontend_error_codes(self) -> None:
        response = payroll_api_contract()["response"]

        self.assertIn("error_code", response["stable_fields"])
        self.assertIn("details", response["stable_fields"])
        self.assertIn("will_run", response["stable_fields"])
        self.assertIn("can_run", response["stable_fields"])
        self.assertIn("requested_input_type", response["stable_fields"])
        self.assertIn("operation_policy", response["stable_fields"])
        self.assertIn("operation_policy_source", response["stable_fields"])
        self.assertEqual(response["success"]["error_code"], "")
        self.assertEqual(response["error"]["error_code"], "invalid_period")
        self.assertEqual(response["run_error"]["error_code"], "payroll_run_failed")
        self.assertTrue(response["run_error"]["will_run"])
        self.assertFalse(response["run_error"]["can_run"])
        self.assertIn("run_response", response["run_response_entrypoint"])
        self.assertIn("missing_input_path", response["error_codes"])

    def test_contract_declares_validation_only_response(self) -> None:
        contract = payroll_api_contract()
        fields = contract["request"]["fields"]
        response = contract["response"]

        self.assertIn("validate_payroll_api_payload", contract["validation_entrypoint"])
        self.assertTrue(any(field["name"] == "validate_only" for field in fields))
        self.assertEqual(response["validation"]["status"], "validated")
        self.assertFalse(response["validation"]["will_run"])
        self.assertTrue(response["validation"]["can_run"])
        self.assertEqual(response["validation"]["requested_input_type"], "mixed")
        self.assertEqual(response["validation"]["operation_policy_source"], "tenant")
        self.assertEqual(response["validation"]["error_code"], "")

    def test_contract_declares_rust_attendance_aggregation(self) -> None:
        contract = payroll_api_contract()
        aggregation = contract["attendance_aggregation"]
        response = contract["response"]

        self.assertIn("aggregate_attendance_records", aggregation["rust_entrypoint"])
        self.assertIn("services.attendance_import._aggregate_records", aggregation["python_compatibility_source"])
        self.assertIn("name_key", aggregation["source_record_fields"])
        self.assertIn("_attendance_days", aggregation["invoice_row_fields"])
        self.assertEqual(aggregation["example_policy"]["rounding_minutes"], 15)
        self.assertEqual(aggregation["example_invoice_rows"][0]["work_days"], 8.0)
        self.assertEqual(aggregation["example_invoice_rows"][0]["early_leave_hours"], 0.25)
        self.assertTrue(aggregation["example_invoice_rows"][0]["_attendance_input"])
        self.assertIn("aggregate_attendance_records", response["attendance_aggregation_entrypoint"])

    def test_contract_declares_rust_workplace_hours_application(self) -> None:
        contract = payroll_api_contract()
        workplace = contract["workplace_hours_application"]
        response = contract["response"]

        self.assertIn("apply_monthly_hours_to_invoice", workplace["rust_entrypoint"])
        self.assertIn("services.workplace_hours.apply_monthly_hours_to_invoice", workplace["python_compatibility_source"])
        self.assertIn("work_or_fixed", workplace["mode_values"])
        self.assertIn("_monthly_work_hours", workplace["invoice_fields"])
        self.assertEqual(workplace["example_policy"]["mode"], "invoice_work_days")
        self.assertEqual(workplace["example_resolution"]["hours"], 192)
        self.assertEqual(workplace["example_resolution"]["source"], "청구장: 청구서 근무시간")
        self.assertEqual(workplace["example_application"]["invoice"]["_monthly_work_hours"], 192)
        self.assertIn("apply_monthly_hours_to_invoice", response["workplace_hours_application_entrypoint"])

    def test_contract_declares_rust_invoice_audit_row(self) -> None:
        contract = payroll_api_contract()
        audit = contract["invoice_audit_row"]
        response = contract["response"]

        self.assertIn("audit_invoice_row", audit["rust_entrypoint"])
        self.assertIn("core.payroll.invoice_audit.audit_invoice_row", audit["python_compatibility_source"])
        self.assertEqual(audit["status_values"], ["pass", "warn"])
        self.assertIn("_monthly_work_hours", audit["record_fields"])
        self.assertIn("fixed_hours_source", audit["row_fields"])
        self.assertEqual(audit["example_row"]["status"], "warn")
        self.assertEqual(audit["example_row"]["break_hours"], 9)
        self.assertEqual(audit["example_row"]["calc_base_salary"], 2_090_000)
        self.assertIn("기본급 불일치", audit["example_row"]["flags"][0])
        self.assertIn("audit_invoice_row", response["invoice_audit_row_entrypoint"])

    def test_contract_declares_rust_invoice_audit_batch(self) -> None:
        contract = payroll_api_contract()
        audit = contract["invoice_audit_batch"]
        response = contract["response"]

        self.assertIn("audit_invoice_batch", audit["rust_entrypoint"])
        self.assertIn("core.payroll.invoice_audit.audit_invoice_payroll", audit["python_compatibility_source"])
        self.assertIn("fixed_profile", audit["item_fields"])
        self.assertEqual(audit["summary_fields"], ["total", "pass", "warn"])
        self.assertEqual(audit["example_result"]["summary"], {"total": 3, "pass": 2, "warn": 1})
        self.assertEqual(audit["example_result"]["pass_count"], 2)
        self.assertEqual(audit["example_result"]["warn_count"], 1)
        self.assertEqual([row["name"] for row in audit["example_result"]["rows"]], ["A", "B", "C"])
        self.assertIn("audit_invoice_batch", response["invoice_audit_batch_entrypoint"])


    def test_contract_declares_rust_social_insurance_calculation(self) -> None:
        contract = payroll_api_contract()
        social = contract["social_insurance_calculation"]
        response = contract["response"]

        self.assertIn("calculate_social_insurance", social["rust_entrypoint"])
        self.assertIn("insurance.calculate_insurance", social["python_compatibility_source"])
        self.assertEqual(social["rates"]["national_pension"], 0.045)
        self.assertEqual(social["rates"]["health_insurance"], 0.03545)
        self.assertEqual(social["rates"]["long_term_care_ratio"], 0.1295)
        self.assertEqual(social["rates"]["employment_insurance_worker"], 0.009)
        self.assertEqual(social["example_result"]["national_pension"], 135_000)
        self.assertEqual(social["example_result"]["health_insurance"], 106_350)
        self.assertEqual(social["example_result"]["long_term_care"], 13_772)
        self.assertEqual(social["example_result"]["employment_insurance"], 27_000)
        self.assertEqual(social["example_result"]["total"], 282_122)
        self.assertIn(
            "calculate_social_insurance",
            response["social_insurance_calculation_entrypoint"],
        )

    def test_contract_declares_rust_deduction_finalization(self) -> None:
        contract = payroll_api_contract()
        deductions = contract["deduction_finalization"]
        response = contract["response"]

        self.assertIn("finalize_payroll_deductions", deductions["rust_entrypoint"])
        self.assertIn("tax.calculate_tax", deductions["python_compatibility_source"])
        self.assertEqual(deductions["method_values"], ["preset", "simplified_table"])
        self.assertIn("preset_local_income_tax", deductions["input_fields"])
        self.assertEqual(deductions["example_result"]["taxable_pay"], 2_700_000)
        self.assertEqual(deductions["example_result"]["income_tax"], 210_000)
        self.assertEqual(deductions["example_result"]["local_income_tax"], 21_000)
        self.assertEqual(deductions["example_result"]["total_deduction"], 551_000)
        self.assertEqual(deductions["example_result"]["net_pay"], 2_449_000)
        self.assertIn(
            "finalize_payroll_deductions",
            response["deduction_finalization_entrypoint"],
        )

    def test_contract_declares_rust_payroll_earnings_calculation(self) -> None:
        contract = payroll_api_contract()
        earnings = contract["earnings_calculation"]
        response = contract["response"]

        self.assertIn("calculate_payroll_earnings", earnings["rust_entrypoint"])
        self.assertIn("calculator.calculate_salary", earnings["python_compatibility_source"])
        self.assertIn("ordinary_hourly", earnings["input_fields"])
        self.assertIn("overlap_premium", earnings["earnings_fields"])
        self.assertEqual(earnings["constants"]["standard_monthly_hours"], 209)
        self.assertEqual(earnings["constants"]["meal_allowance_per_day"], 5_500)
        self.assertEqual(earnings["example_result"]["ordinary_hourly"], 10_478.47)
        self.assertEqual(earnings["example_result"]["gross_pay"], 2_871_528)
        self.assertEqual(earnings["example_result"]["non_taxable_pay"], 121_000)
        self.assertEqual(earnings["example_raw_amount_result"]["hours"]["overtime"], 16.666666666666668)
        self.assertEqual(earnings["example_raw_amount_result"]["non_taxable_pay"], 200_000)
        self.assertIn(
            "calculate_payroll_earnings",
            response["earnings_calculation_entrypoint"],
        )

    def test_contract_declares_rust_ei65_payroll_decision(self) -> None:
        contract = payroll_api_contract()
        ei65 = contract["ei65_payroll_decision"]
        response = contract["response"]

        self.assertIn("resolve_ei_65_for_payroll", ei65["rust_entrypoint"])
        self.assertIn("core.payroll.employment_insurance_65.resolve_ei_65_for_payroll", ei65["python_compatibility_source"])
        self.assertEqual(ei65["status_values"], ["exempt", "liable", "unknown"])
        self.assertEqual(ei65["unknown_default_values"], ["skip", "deduct"])
        self.assertIn("latest_verification", ei65["input_fields"])
        self.assertEqual(ei65["example_result"]["status"], "exempt")
        self.assertEqual(ei65["example_result"]["premium_amount"], 0)
        self.assertFalse(ei65["example_result"]["deduct_employment_insurance"])
        self.assertIsNone(ei65["example_unknown_result"]["premium_amount"])
        self.assertIn("공제 생략", ei65["example_unknown_result"]["warning"])
        self.assertIn("resolve_ei_65_for_payroll", response["ei65_payroll_decision_entrypoint"])


    def test_contract_declares_rust_edi_insurance_application(self) -> None:
        contract = payroll_api_contract()
        edi = contract["edi_insurance_application"]
        response = contract["response"]

        self.assertIn("apply_edi_premiums_to_invoice", edi["rust_entrypoint"])
        self.assertIn("core.payroll.edi_insurance.apply_edi_premiums_to_inv", edi["python_compatibility_source"])
        self.assertEqual(edi["source_values"], ["manual", "import", "api", "calculated"])
        self.assertIn("respect_age_exempt", edi["config_fields"])
        self.assertIn("industrial_accident_employee", edi["record_fields"])
        self.assertEqual(edi["messages"]["badge"], "EDI 조회")
        self.assertEqual(edi["example_application"]["invoice"]["long_term_care"], 5_180)
        self.assertEqual(edi["example_application"]["invoice"]["insurance_total"], 145_180)
        self.assertEqual(edi["example_application"]["invoice"]["edi_premium_source_type"], "manual")
        self.assertIn(
            "apply_edi_premiums_to_invoice",
            response["edi_insurance_application_entrypoint"],
        )

    def test_contract_declares_rust_site_benefits_application(self) -> None:
        contract = payroll_api_contract()
        benefits = contract["site_benefits_application"]
        response = contract["response"]

        self.assertIn("apply_site_benefits_to_invoice", benefits["rust_entrypoint"])
        self.assertIn("core.payroll.site_benefits.apply_site_benefits_to_invoice", benefits["python_compatibility_source"])
        self.assertEqual(benefits["source_values"], ["site", "tenant", "global"])
        self.assertIn("identity_insurance_already_applied", benefits["config_fields"])
        self.assertIn("_workers_day_source", benefits["invoice_fields"])
        self.assertEqual(benefits["example_application"]["workers_day_allowance"], 12_000)
        self.assertEqual(benefits["example_application"]["identity_guarantee_insurance_deduction"], -20_000)
        self.assertEqual(
            benefits["example_application"]["invoice"]["_identity_insurance_source"],
            "site",
        )
        self.assertIn(
            "apply_site_benefits_to_invoice",
            response["site_benefits_application_entrypoint"],
        )

    def test_contract_declares_rust_fixed_hours_application(self) -> None:
        contract = payroll_api_contract()
        fixed = contract["fixed_hours_application"]
        response = contract["response"]

        self.assertIn("apply_fixed_hours_to_invoice", fixed["rust_entrypoint"])
        self.assertIn("core.payroll.fixed_hours.apply_fixed_hours_to_invoice", fixed["python_compatibility_source"])
        self.assertIn("monthly_salary", fixed["pay_type_values"])
        self.assertIn("_invoice_work_days", fixed["invoice_fields"])
        self.assertEqual(fixed["example_profile"]["monthly_fixed_hours"], 209)
        self.assertEqual(fixed["example_application"]["invoice"]["work_days"], 209)
        self.assertEqual(fixed["example_application"]["invoice"]["ot_hours"], 20)
        self.assertEqual(fixed["example_application"]["invoice"]["special_hours"], 10)
        self.assertIn("청구서 연장(5h)", fixed["example_application"]["audit_flags"][2])
        self.assertIn("apply_fixed_hours_to_invoice", response["fixed_hours_application_entrypoint"])

    def test_contract_declares_rust_operation_policy_resolution(self) -> None:
        contract = payroll_api_contract()
        resolution = contract["policy_resolution"]
        response = contract["response"]

        self.assertIn("validate_run_payload_with_policy_settings", resolution["rust_entrypoint"])
        self.assertEqual(resolution["precedence"], ["site", "tenant", "global"])
        self.assertIn("site_policies", resolution["settings_snapshot_fields"])
        self.assertEqual(resolution["example_resolution"]["source"], "site")
        self.assertTrue(resolution["example_resolution"]["has_site_override"])
        self.assertIn(
            "validate_run_payload_with_policy_settings",
            response["policy_resolution_entrypoint"],
        )

    def test_contract_declares_rust_execution_planning(self) -> None:
        contract = payroll_api_contract()
        plan = contract["execution_plan"]
        response = contract["response"]

        self.assertIn("plan_run_request", plan["rust_entrypoint"])
        self.assertIn("plan_payroll_execution", plan["planner_entrypoint"])
        self.assertEqual(plan["backend_values"], ["python_compatibility"])
        self.assertIn("attach_attendance_sheet", plan["step_kinds"])
        self.assertEqual(plan["example_plan"]["backend"], "python_compatibility")
        self.assertEqual(plan["example_plan"]["input_type"], "mixed")
        self.assertEqual(plan["example_plan"]["requested_input_type"], "auto")
        self.assertEqual(plan["example_plan"]["steps"][0]["kind"], "extract_attendance")
        self.assertIn("plan_run_request", response["execution_plan_entrypoint"])

    def test_contract_declares_rust_authorization_decisions(self) -> None:
        contract = payroll_api_contract()
        authorization = contract["authorization"]
        response = contract["response"]["authorization"]

        self.assertIn("authorize_run_request", authorization["rust_entrypoint"])
        self.assertEqual(authorization["permissions"]["validate"], ["platform.payroll"])
        self.assertEqual(authorization["permissions"]["run"], ["platform.payroll.executive"])
        self.assertIn("tenant_mismatch", authorization["deny_reason_codes"])
        self.assertIn("effective_platform_ids", authorization["abac_attributes"])
        self.assertTrue(response["allowed"]["allowed"])
        self.assertEqual(response["allowed"]["required_permissions"], ["platform.payroll.executive"])
        self.assertFalse(response["denied"]["allowed"])
        self.assertEqual(response["denied"]["reason_code"], "tenant_mismatch")

    def test_contract_declares_rust_service_health_and_readiness(self) -> None:
        response = payroll_api_contract()["response"]

        self.assertEqual(response["health"]["status"], "ok")
        self.assertEqual(response["health"]["service"], "bitween-payroll-api")
        self.assertEqual(response["health"]["version"], "v1")
        self.assertEqual(response["readiness"]["state"], "not_ready")
        self.assertFalse(response["readiness"]["ready"])
        self.assertTrue(response["readiness"]["checks"][0]["required"])
        self.assertEqual(response["readiness"]["checks"][1]["state"], "degraded")
        self.assertFalse(response["readiness"]["checks"][1]["required"])


if __name__ == "__main__":
    unittest.main()
