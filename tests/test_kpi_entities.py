"""tests/test_kpi_entities.py - 법인 손익(entities) 데이터·표시"""

from __future__ import annotations

import unittest

from core.kpi import service as kpi_svc
from core.kpi.service import _EMPTY, _parse_margin_pct
from core.module_store import load_module_db, save_module_db


class TestKpiEntities(unittest.TestCase):
    def test_parse_margin_pct_accepts_percent_string(self) -> None:
        self.assertAlmostEqual(_parse_margin_pct("+12.7%"), 12.7)
        self.assertAlmostEqual(_parse_margin_pct("-4.4%"), -4.4)
        self.assertEqual(_parse_margin_pct("bad"), 0.0)

    def test_list_records_entities_has_rows_after_seed(self) -> None:
        tid = "test_kpi_entities_seed"
        save_module_db(kpi_svc.MODULE, tid, dict(_EMPTY))
        kpi_svc.ensure_seed(tid)
        rows = kpi_svc.list_records("entities")
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("legal_entity", rows[0])

    def test_ensure_seed_backfills_missing_entities(self) -> None:
        tid = "test_kpi_entities_backfill"
        save_module_db(
            kpi_svc.MODULE,
            tid,
            {
                "seeded": True,
                "sites": [{"id": "x", "site_name": "t", "region": "서울", "status": "정상"}],
                "entities": [],
                "individual": [],
                "alerts": [],
            },
        )
        kpi_svc.ensure_seed(tid)
        db = load_module_db(kpi_svc.MODULE, tid, _EMPTY)
        self.assertGreaterEqual(len(db.get("entities") or []), 1)


if __name__ == "__main__":
    unittest.main()
