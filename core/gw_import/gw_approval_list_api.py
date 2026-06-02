"""
Paginated COSS GW approval inbox lists via selectEapApprList.do.

Requires authenticated session (GwClient login or session_cookies.json).
"""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from core.gw_import.detail_parser import parse_inbox_sample_line

SELECT_EAP_APPR_LIST = "https://gw.cossok.com/gw/data/eap/approval/selectEapApprList.do"

# GW eapConstants.menuCode values (see eapApprList.js)
APPR_BOX_BY_LIST_KIND: dict[str, str] = {
    "pending": "approvalWait",
    "in_progress": "approvalPrgss",
    "approval_confirm": "approvalConfirm",
    "approval_return": "approvalRtn",
    "completed": "finishConfirm",
    "finish_return": "finishRtn",
    "circulate": "innerActDisp",
    "draft_progress": "draftPrgss",
    "draft_approved": "draftConfirm",
    "draft_return": "draftRtn",
    "draft_temp": "draftTemp",
}


def _default_payload(appr_box_id: str, *, page_no: int = 1, page_size: int = 30) -> dict[str, Any]:
    return {
        "codeGrp": "PORTLET_APPR_CODE",
        "apprBoxId": appr_box_id,
        "foreignTabId": "wait",
        "pageNo": page_no,
        "pageSize": page_size,
        "certPrintYn": "",
        "searchParams": {
            "PERIOD_TRGT": "101",
            "SEARCH_CODE": "DOC_SUBJECT",
            "SEARCH_VALUE": "",
            "emgncyYn": "",
            "apprStatusCode": "",
            "formId": "",
            "LAST_ORDER_APPR": "N",
            "SECRET_APPR": "N",
        },
        "orderParams": {"draftDt": "DESC"},
        "divisionMode": "list",
        "labelIds": [],
        "nonLabel": "N",
    }


def _row_from_list_entry(entry: Any) -> dict[str, Any] | None:
    if isinstance(entry, list) and entry:
        cell = entry[0] if isinstance(entry[0], dict) else {}
    elif isinstance(entry, dict):
        cell = entry
    else:
        return None
    if not isinstance(cell, dict):
        return None
    gid = str(
        cell.get("apprId")
        or cell.get("apprid")
        or cell.get("APPR_ID")
        or ""
    ).strip()
    title = str(
        cell.get("docSubject")
        or cell.get("docsubject")
        or cell.get("title")
        or ""
    ).strip()
    drafter = str(
        cell.get("draftEmpName")
        or cell.get("draftempname")
        or ""
    ).strip()
    if not gid and not title:
        return None
    return {
        "gw_doc_id": gid,
        "title": title,
        "drafter": drafter,
        "doc_id": str(cell.get("docId") or cell.get("docid") or "").strip(),
        "form_name": str(cell.get("formName") or cell.get("formname") or "").strip(),
        "draft_dt": str(cell.get("draftDt") or cell.get("draftdt") or "").strip(),
    }


def fetch_approval_list_page(
    session: requests.Session,
    appr_box_id: str,
    *,
    page_no: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bitween-GW-Import/1.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    payload = _default_payload(appr_box_id, page_no=page_no, page_size=page_size)
    resp = session.post(SELECT_EAP_APPR_LIST, data=json.dumps(payload), timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected list response: {type(data)}")
    return data


def paginate_approval_list(
    session: requests.Session,
    list_kind: str,
    *,
    appr_box_id: str = "",
    page_size: int = 30,
    max_pages: int = 0,
    rate_sec: float = 0.25,
) -> tuple[list[dict[str, Any]], int]:
    """
    Fetch all pages for a list kind. Returns (rows, gw_total_count).
    max_pages=0 means until exhausted.
    """
    box = appr_box_id or APPR_BOX_BY_LIST_KIND.get(list_kind, list_kind)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    page = 1
    total = 0

    while True:
        if max_pages and page > max_pages:
            break
        res = fetch_approval_list_page(session, box, page_no=page, page_size=page_size)
        total = int(res.get("allCnt") or res.get("totalCnt") or 0)
        chunk = res.get("list") or []
        if not isinstance(chunk, list):
            break
        added = 0
        for entry in chunk:
            row = _row_from_list_entry(entry)
            if not row:
                continue
            gid = str(row.get("gw_doc_id") or "").strip()
            key = gid or f"title:{row.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            rows.append({**row, "gw_list": list_kind, "appr_box_id": box})
            added += 1
        if added == 0:
            break
        if total and len(rows) >= total:
            break
        if len(chunk) < page_size:
            break
        page += 1
        if rate_sec > 0:
            time.sleep(rate_sec)

    return rows, total


def rows_from_document_samples(lines: list[Any]) -> list[dict[str, Any]]:
    """Fallback when API auth unavailable — parse gw_scrape_extended samples."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        raw = line.get("line") if isinstance(line, dict) else str(line)
        parsed = parse_inbox_sample_line(str(raw or ""))
        gid = str(parsed.get("gw_doc_id") or "").strip()
        key = f"id:{gid}" if gid else f"title:{parsed.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(parsed)
    return out
