#!/usr/bin/env python3
"""
fetch_gw.py - Pull COSS groupware data into app_data/gw_import/ (re-runnable).

Usage (from 급여프로그램/):
  set GW_USER=...
  set GW_PASS=...
  python tools/gw_import/fetch_gw.py
  python tools/gw_import/fetch_gw.py --modules org,forms,board
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from repo root
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.paths import app_data_dir
from tools.gw_import.gw_client import GwClient, node_label

IMPORT_DIR = app_data_dir() / "gw_import"
MANIFEST_FILE = IMPORT_DIR / "manifest.json"

DEFAULT_MODULES = ("org", "companies", "forms", "board", "address")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_org(client: GwClient) -> dict[str, object]:
    flat = client.walk_org_tree("ROOT")
    companies = [n for n in flat if n.get("type") == 2]
    users = [n for n in flat if n.get("type") == 3 or n.get("empId")]
    depts = [n for n in flat if n.get("type") not in (1, 2, 3) and n.get("folder")]
    return {
        "fetched_at": _now(),
        "mode": "admin_api",
        "flat_nodes": flat,
        "counts": {
            "total_nodes": len(flat),
            "companies": len(companies),
            "departments": len(depts),
            "person_nodes": len(users),
        },
        "company_labels": sorted({node_label(n) for n in companies if node_label(n)}),
    }


def fetch_forms_admin(client: GwClient) -> dict[str, object]:
    """Admin 양식관리 HTML probe — list page snapshot metadata only."""
    client.ensure_login()
    r = client.session.get(f"{client.session.headers.get('Referer', '')}" or f"{GwClient.__module__}")
    # Navigate admin form list endpoint (may redirect to HTML)
    resp = client.session.get(
        "https://gw.cossok.com/gw/manage/form/formMain.do",
        timeout=60,
        allow_redirects=True,
    )
    return {
        "fetched_at": _now(),
        "status_code": resp.status_code,
        "final_url": resp.url,
        "title_hint": "양식관리" if "form" in resp.url.lower() else "",
        "html_bytes": len(resp.content),
        "note": "Full form schemas require browser scrape or dedicated API; HTML shell captured.",
    }


def fetch_user_org_chart(client: GwClient) -> dict[str, object]:
    """User-mode 조직도 page."""
    resp = client.session.get(
        "https://gw.cossok.com/gw/data/org/info/orgInfoMain.do?gwHisFrom=mainMenu",
        timeout=60,
    )
    return {
        "fetched_at": _now(),
        "mode": "user",
        "status_code": resp.status_code,
        "final_url": resp.url,
        "html_bytes": len(resp.content),
    }


def fetch_board_modules(client: GwClient) -> dict[str, object]:
    """Probe module admin pages (게시판)."""
    results: list[dict[str, object]] = []
    for name, path in (
        ("board_admin", "/gw/manage/module/brdMain.do"),
        ("doc_box", "/gw/manage/module/docMain.do"),
        ("calendar", "/gw/manage/module/schMain.do"),
    ):
        resp = client.session.get(f"https://gw.cossok.com{path}", timeout=60, allow_redirects=True)
        results.append(
            {
                "module": name,
                "status_code": resp.status_code,
                "final_url": resp.url,
                "html_bytes": len(resp.content),
            }
        )
    return {"fetched_at": _now(), "modules": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch COSS groupware data into app_data/gw_import/")
    parser.add_argument(
        "--modules",
        default=",".join(DEFAULT_MODULES),
        help=f"Comma-separated: {','.join(DEFAULT_MODULES)}",
    )
    parser.add_argument("--out", type=Path, default=IMPORT_DIR)
    args = parser.parse_args()
    modules = {m.strip().lower() for m in args.modules.split(",") if m.strip()}

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    client = GwClient()
    client.login()
    manifest: dict[str, object] = {
        "fetched_at": _now(),
        "source": "gw.cossok.com",
        "import_mode": "admin_api",
        "modules": {},
    }

    if "org" in modules or "companies" in modules:
        org_data = fetch_org(client)
        _write_json(out / "org_tree.json", org_data)
        manifest["modules"]["org"] = org_data["counts"]

    if "forms" in modules:
        forms = fetch_forms_admin(client)
        _write_json(out / "forms_probe.json", forms)
        manifest["modules"]["forms"] = {"status": forms.get("status_code")}

    if "address" in modules:
        addr = fetch_user_org_chart(client)
        _write_json(out / "org_user_view.json", addr)
        manifest["modules"]["address"] = {"status": addr.get("status_code")}

    if "board" in modules:
        board = fetch_board_modules(client)
        _write_json(out / "board_probe.json", board)
        manifest["modules"]["board"] = len(board.get("modules", []))

    _write_json(MANIFEST_FILE if args.out == IMPORT_DIR else out / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
