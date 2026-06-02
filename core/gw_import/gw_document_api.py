"""
HTTP fetch for COSS GW approval document body + attachments.

Uses an authenticated requests.Session (GwClient or cookies file).
Never log or persist credentials.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from core.gw_import.detail_parser import parse_approval_line, parse_detail_payload
from core.gw_import.paths import gw_attachments_dir

GW_BASE = "https://gw.cossok.com/gw"
GW_POPUP_URL = GW_BASE + "/sub/eap/approval/eapApprViewPopup.do?apprId={gw_doc_id}"
GW_VIEW_URL = (
    GW_BASE + "/biz/eap/approval/eapApprMain.do?mode=view&apprId={gw_doc_id}"
)
SELECT_APPROVAL_VIEW = GW_BASE + "/data/eap/approval/selectApprovalView.do"
FILE_DOWNLOAD = GW_BASE + "/data/eap/download/eapFileDownload.do"


def gw_popup_url(gw_doc_id: str) -> str:
    return GW_POPUP_URL.format(gw_doc_id=str(gw_doc_id).strip())


def gw_view_url(gw_doc_id: str) -> str:
    return GW_VIEW_URL.format(gw_doc_id=str(gw_doc_id).strip())


def load_cookies_into_session(session: requests.Session, cookie_path: Path) -> None:
    """Load cookies from JSON (EditThisCookie / browser export) or Netscape format."""
    text = cookie_path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        items = json.loads(text)
        if not isinstance(items, list):
            raise ValueError("Cookie JSON must be a list")
        for c in items:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "").strip()
            value = str(c.get("value") or "")
            if not name:
                continue
            session.cookies.set(
                name,
                value,
                domain=str(c.get("domain") or "gw.cossok.com"),
                path=str(c.get("path") or "/"),
            )
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            session.cookies.set(parts[5], parts[6], domain=parts[0], path=parts[2])


def _api_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bitween-GW-Import/1.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }


def fetch_approval_view(
    session: requests.Session,
    gw_doc_id: str,
    *,
    appr_box_id: str = "",
    doc_id: str = "",
    item_no: int = 0,
) -> dict[str, Any]:
    """POST selectApprovalView.do — full document metadata + HTML content + attachments."""
    session.headers.update(_api_headers())
    payload: dict[str, Any] = {
        "apprId": str(gw_doc_id).strip(),
        "apprBoxId": appr_box_id or "",
        "docId": doc_id or "",
        "itemNo": item_no,
        "apprIds": "",
    }
    resp = session.post(
        SELECT_APPROVAL_VIEW,
        data=json.dumps(payload),
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected approval view response: {type(data)}")
    code = data.get("resultCode")
    if code is not None and str(code) not in ("0", "00", ""):
        msg = data.get("resultMsg") or data.get("message") or data
        raise RuntimeError(f"GW API error {code}: {msg}")
    return data


def _pick_doc_entry(res: dict[str, Any], item_no: int = 0) -> dict[str, Any]:
    doc_list = res.get("apprDocList")
    if isinstance(doc_list, list) and doc_list:
        idx = min(max(item_no, 0), len(doc_list) - 1)
        row = doc_list[idx]
        if isinstance(row, dict):
            return row
    return {}


def _extract_content_html(doc_entry: dict[str, Any], res: dict[str, Any]) -> str:
    for key in ("content", "docContent", "editorContent", "bodyHtml"):
        val = doc_entry.get(key) or res.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:500_000]
    return ""


def _extract_title(res: dict[str, Any], doc_entry: dict[str, Any]) -> str:
    form = res.get("eapFormVo") or {}
    if isinstance(form, dict):
        for k in ("formName", "formTitle", "title"):
            t = str(form.get(k) or "").strip()
            if t:
                return t
    for k in ("docTitle", "title", "subject"):
        t = str(doc_entry.get(k) or res.get(k) or "").strip()
        if t:
            return t
    return ""


def _extract_approval_steps(res: dict[str, Any]) -> dict[str, Any]:
    line = res.get("apprLineInfo")
    steps: list[dict[str, str]] = []
    if isinstance(line, dict):
        for row in line.get("apprLineList") or line.get("lines") or []:
            if not isinstance(row, dict):
                continue
            steps.append(
                {
                    "name": str(row.get("empName") or row.get("userName") or "").strip(),
                    "role": str(row.get("apprTypeName") or row.get("apprType") or "").strip(),
                    "status": str(row.get("apprStatusName") or row.get("apprStatus") or "").strip(),
                }
            )
    raw = res.get("apprLineInfoStr") or res.get("apprLineText") or ""
    if not steps and isinstance(raw, str) and "▶" in raw:
        steps = parse_approval_line(raw)
    return {"steps": steps, "raw": line if isinstance(line, dict) else {}}


def detail_from_approval_view(
    res: dict[str, Any],
    gw_doc_id: str,
    *,
    gw_list: str = "",
) -> dict[str, Any]:
    doc_entry = _pick_doc_entry(res)
    content_html = _extract_content_html(doc_entry, res)
    title = _extract_title(res, doc_entry)
    drafter = str(res.get("draftEmpName") or res.get("draftUserName") or "").strip()
    doc_number = str(doc_entry.get("docNo") or res.get("docNo") or "").strip()
    drafted_at = str(doc_entry.get("draftDt") or res.get("draftDt") or "")[:10]
    completed_at = str(doc_entry.get("endDt") or res.get("endDt") or "")[:10]
    form_name = ""
    form = res.get("eapFormVo")
    if isinstance(form, dict):
        form_name = str(form.get("formName") or "").strip()

    att_meta: list[dict[str, Any]] = []
    for f in res.get("attFileList") or doc_entry.get("attFileList") or []:
        if not isinstance(f, dict):
            continue
        att_meta.append(
            {
                "name": str(f.get("fileName") or f.get("name") or "").strip(),
                "file_id": str(f.get("fileId") or "").strip(),
                "file_grp_id": str(f.get("fileGrpId") or f.get("docId") or "").strip(),
                "size": int(f.get("fileSize") or f.get("size") or 0),
            }
        )

    return parse_detail_payload(
        {
            "gw_doc_id": gw_doc_id,
            "title": title,
            "doc_number": doc_number,
            "drafter": drafter,
            "drafted_at": drafted_at.replace(".", "-") if drafted_at else "",
            "completed_at": completed_at.replace(".", "-") if completed_at else "",
            "form_name": form_name,
            "gw_list": gw_list,
            "gw_url": gw_popup_url(gw_doc_id),
            "content_html": content_html,
            "attachments": [
                {
                    "name": a["name"],
                    "path": "",
                    "size": a["size"],
                    "url": (
                        f"{FILE_DOWNLOAD}?docId={a['file_grp_id']}&fileId={a['file_id']}"
                        if a.get("file_id") and a.get("file_grp_id")
                        else ""
                    ),
                    "_file_id": a.get("file_id"),
                    "_file_grp_id": a.get("file_grp_id"),
                }
                for a in att_meta
                if a.get("name")
            ],
            "approval_workflow_json": _extract_approval_steps(res),
            "source": "gw_api",
            "_api_doc_id": str(doc_entry.get("docId") or res.get("docId") or ""),
        }
    )


def download_attachments(
    session: requests.Session,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Download attachment files into gw_import/attachments/{gw_doc_id}/."""
    gid = str(detail.get("gw_doc_id") or "").strip()
    dest_dir = gw_attachments_dir(gid)
    out: list[dict[str, Any]] = []
    for att in detail.get("attachments") or []:
        if not isinstance(att, dict):
            continue
        name = str(att.get("name") or "attachment").strip()
        file_id = str(att.get("_file_id") or att.get("file_id") or "").strip()
        grp_id = str(att.get("_file_grp_id") or att.get("file_grp_id") or "").strip()
        if not file_id or not grp_id:
            out.append(att)
            continue
        dest = dest_dir / name
        url = f"{FILE_DOWNLOAD}?docId={grp_id}&fileId={file_id}"
        try:
            r = session.get(url, timeout=180, stream=True)
            r.raise_for_status()
            dest.write_bytes(r.content)
            out.append(
                {
                    "name": name,
                    "path": str(dest),
                    "size": dest.stat().st_size,
                }
            )
        except requests.RequestException as exc:
            out.append({**att, "download_error": str(exc)})
    detail = dict(detail)
    detail["attachments"] = out
    return detail


def is_synthetic_body(detail: dict[str, Any]) -> bool:
    ct = str(detail.get("content_text") or "").strip()
    ch = str(detail.get("content_html") or "").strip()
    if ch and len(ch) > 80:
        return False
    if ct.startswith("(COSS 그룹웨어"):
        return True
    if not ch and len(ct) < 120:
        return True
    return False


def needs_full_scrape(detail: dict[str, Any] | None) -> bool:
    if not detail:
        return True
    if is_synthetic_body(detail):
        return True
    ch = str(detail.get("content_html") or "").strip()
    if len(ch) < 80:
        return True
    return False
