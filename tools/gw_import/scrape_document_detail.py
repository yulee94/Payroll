#!/usr/bin/env python3
"""
scrape_document_detail.py — Parse one COSS GW document (content + attachments).

Browser workflow (user stays logged in):
  1. Open document in GW (list → 새창 or doc link).
  2. Save browser MCP snapshot to a .log/.yaml file OR export HTML.
  3. Run:
       python tools/gw_import/scrape_document_detail.py --gw-doc-id ID --snapshot path/to/snapshot.log
     Optional attachments folder:
       python tools/gw_import/scrape_document_detail.py --gw-doc-id ID --snapshot snap.log --attach-dir ./files

Also accepts --url (records gw_url), --html, --json, or --input detail.json.
Writes: app_data/gw_import/details/{gw_doc_id}.json
         app_data/gw_import/attachments/{gw_doc_id}/*
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.gw_import.detail_parser import load_detail_file, parse_detail_payload
from core.gw_import.gw_document_api import (
    detail_from_approval_view,
    download_attachments,
    fetch_approval_view,
    gw_popup_url,
    load_cookies_into_session,
)
from core.gw_import.paths import gw_attachments_dir, gw_details_dir
from core.gw_import.store import save_detail_cache

GW_DOC_VIEW_URL = (
    "https://gw.cossok.com/gw/biz/eap/approval/eapApprMain.do"
    "?mode=view&apprId={gw_doc_id}"
)
GW_DOC_POPUP_URL = (
    "https://gw.cossok.com/gw/sub/eap/approval/eapApprViewPopup.do"
    "?apprId={gw_doc_id}"
)


def _copy_attachments(gw_doc_id: str, attach_dir: Path) -> list[dict[str, object]]:
    dest = gw_attachments_dir(gw_doc_id)
    out: list[dict[str, object]] = []
    if not attach_dir.is_dir():
        return out
    for src in sorted(attach_dir.iterdir()):
        if not src.is_file():
            continue
        target = dest / src.name
        shutil.copy2(src, target)
        out.append({"name": src.name, "path": str(target), "size": target.stat().st_size})
    return out


def build_detail_from_args(args: argparse.Namespace) -> dict[str, object]:
    detail: dict[str, object] = {}
    if args.json and Path(args.json).is_file():
        detail = load_detail_file(Path(args.json))
    elif args.input and Path(args.input).is_file():
        detail = load_detail_file(Path(args.input))
    elif args.html and Path(args.html).is_file():
        detail = load_detail_file(Path(args.html))
    elif args.snapshot and Path(args.snapshot).is_file():
        detail = load_detail_file(Path(args.snapshot))
    else:
        raise SystemExit("Provide --snapshot, --html, --json, or --input")

    gid = str(args.gw_doc_id or detail.get("gw_doc_id") or "").strip()
    if not gid:
        raise SystemExit("--gw-doc-id is required when not present in source file")
    detail["gw_doc_id"] = gid
    if args.url:
        detail["gw_url"] = args.url
    elif not detail.get("gw_url"):
        detail["gw_url"] = gw_popup_url(gid)
    if args.list_kind:
        detail["gw_list"] = args.list_kind
    if args.title:
        detail["title"] = args.title
    if args.attach_dir:
        detail["attachments"] = _copy_attachments(gid, Path(args.attach_dir))
    return parse_detail_payload(detail)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse GW document detail into app_data cache")
    parser.add_argument("--gw-doc-id", help="COSS document id from list link")
    parser.add_argument("--url", help="Document URL (optional)")
    parser.add_argument("--snapshot", type=Path, help="Browser MCP snapshot log/yaml")
    parser.add_argument("--html", type=Path, help="Saved HTML page")
    parser.add_argument("--json", type=Path, help="Detail JSON")
    parser.add_argument("--input", type=Path, help="Alias for --json")
    parser.add_argument("--attach-dir", type=Path, help="Folder with downloaded attachment files")
    parser.add_argument("--list-kind", default="", help="pending|draft|circulate|completed|...")
    parser.add_argument("--title", default="", help="Override title")
    parser.add_argument("--print-url", action="store_true", help="Print suggested GW URL and exit")
    parser.add_argument("--print-popup-url", action="store_true", help="Print popup view URL (recommended)")
    parser.add_argument("--fetch-api", action="store_true", help="Fetch via selectApprovalView HTTP API")
    parser.add_argument("--cookies-file", type=Path, help="Browser session cookies JSON (no credentials in repo)")
    parser.add_argument("--download-attachments", action="store_true", help="With --fetch-api, download files")
    args = parser.parse_args()

    if args.print_url and args.gw_doc_id:
        print(GW_DOC_VIEW_URL.format(gw_doc_id=args.gw_doc_id))
        return 0
    if args.print_popup_url and args.gw_doc_id:
        print(GW_DOC_POPUP_URL.format(gw_doc_id=args.gw_doc_id))
        return 0

    if args.fetch_api:
        if not args.gw_doc_id:
            raise SystemExit("--gw-doc-id required with --fetch-api")
        import os
        import requests
        from tools.gw_import.gw_client import GwClient

        session = requests.Session()
        if args.cookies_file and Path(args.cookies_file).is_file():
            load_cookies_into_session(session, Path(args.cookies_file))
        else:
            GwClient(session=session).login(
                user=os.environ.get("GW_USER", ""),
                password=os.environ.get("GW_PASS", ""),
            )
        res = fetch_approval_view(session, args.gw_doc_id)
        detail = detail_from_approval_view(res, args.gw_doc_id, gw_list=args.list_kind or "")
        if args.download_attachments and detail.get("attachments"):
            detail = download_attachments(session, detail)
        if args.title:
            detail["title"] = args.title
        path = save_detail_cache(detail)
        print(
            json.dumps(
                {
                    "gw_doc_id": detail.get("gw_doc_id"),
                    "detail_path": str(path),
                    "content_html_len": len(detail.get("content_html") or ""),
                    "attachments": len(detail.get("attachments") or []),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    detail = build_detail_from_args(args)
    path = save_detail_cache(detail)
    gw_details_dir()

    report = {
        "gw_doc_id": detail.get("gw_doc_id"),
        "title": detail.get("title"),
        "detail_path": str(path),
        "attachments": len(detail.get("attachments") or []),
        "content_chars": len(detail.get("content_text") or ""),
        "gw_url": detail.get("gw_url"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
