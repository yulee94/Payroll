from __future__ import annotations

import json
import unittest

from services.payroll_api_adapter import build_payroll_api_request
from services.payroll_api_contract import (
    PAYROLL_API_ENDPOINT,
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

    def test_response_contract_declares_frontend_error_codes(self) -> None:
        response = payroll_api_contract()["response"]

        self.assertIn("error_code", response["stable_fields"])
        self.assertIn("details", response["stable_fields"])
        self.assertEqual(response["success"]["error_code"], "")
        self.assertEqual(response["error"]["error_code"], "invalid_period")
        self.assertIn("missing_input_path", response["error_codes"])


if __name__ == "__main__":
    unittest.main()
