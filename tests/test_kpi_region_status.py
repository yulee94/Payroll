"""tests/test_kpi_region_status.py - KPI 지역 상태 집계"""

from __future__ import annotations

import unittest

from core.kpi import service as kpi_svc


class TestRegionStatus(unittest.TestCase):
    def test_region_status_priority(self) -> None:
        sites_ok = [{"status": kpi_svc.STATUS_OK}, {"status": kpi_svc.STATUS_OK}]
        self.assertEqual(kpi_svc._region_status(sites_ok), kpi_svc.STATUS_OK)

        sites_warn = [{"status": kpi_svc.STATUS_OK}, {"status": kpi_svc.STATUS_WARN}]
        self.assertEqual(kpi_svc._region_status(sites_warn), kpi_svc.STATUS_WARN)

        sites_critical = [{"status": kpi_svc.STATUS_WARN}, {"status": kpi_svc.STATUS_CRITICAL}]
        self.assertEqual(kpi_svc._region_status(sites_critical), kpi_svc.STATUS_CRITICAL)


if __name__ == "__main__":
    unittest.main()

