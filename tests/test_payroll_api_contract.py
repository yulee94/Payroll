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
