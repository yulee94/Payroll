from __future__ import annotations

import json
import unittest

from core.api_surfaces import api_surface_contract, build_api_path


class ApiSurfaceContractTests(unittest.TestCase):
    def test_contract_declares_separate_api_surfaces(self) -> None:
        contract = api_surface_contract()

        json.dumps(contract, ensure_ascii=False)

        names = contract["required_surfaces"]
        self.assertEqual(
            names,
            [
                "Web Admin API",
                "Mobile App API",
                "Public Customer API",
                "Internal Admin API",
            ],
        )
        surfaces = contract["surfaces"]
        self.assertEqual(surfaces["mobile_app"]["gateway_host"], "mobile-api.bitween.example")
        self.assertEqual(surfaces["internal_admin"]["exposure"], "private_subnet_only")
        self.assertEqual(surfaces["mobile_app"]["auth"], "bearer_token_device_binding")

    def test_mobile_app_api_paths_are_versioned(self) -> None:
        self.assertEqual(build_api_path("mobile_app", "login", version="v1"), "/api/v1/login")
        self.assertEqual(build_api_path("mobile_app", "/branches", version="v1"), "/api/v1/branches")
        self.assertEqual(build_api_path("mobile_app", "tasks", version="v1"), "/api/v1/tasks")
        self.assertEqual(build_api_path("mobile_app", "tasks", version="v2"), "/api/v2/tasks")


if __name__ == "__main__":
    unittest.main()
