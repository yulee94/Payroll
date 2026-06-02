"""Locale catalog loading (UTF-8 BOM safe)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.i18n.registry import LOCALES_DIR, _load_catalog, init_i18n, set_locale, t


class TestI18nCatalog(unittest.TestCase):
    def test_ko_catalog_loads_with_bom(self) -> None:
        catalog = _load_catalog("ko")
        self.assertIn("nav.home", catalog)
        self.assertEqual(catalog["nav.home"], "플랫폼 홈")

    def test_locale_switch_updates_nav_labels(self) -> None:
        init_i18n("ko")
        self.assertEqual(t("nav.home"), "플랫폼 홈")
        set_locale("en")
        self.assertEqual(t("nav.home"), "Home")

    def test_all_supported_locale_files_parse(self) -> None:
        for path in LOCALES_DIR.glob("*.json"):
            with self.subTest(locale=path.stem):
                catalog = _load_catalog(path.stem)
                self.assertIsInstance(catalog, dict)
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
                self.assertIsInstance(raw, dict)


if __name__ == "__main__":
    unittest.main()
