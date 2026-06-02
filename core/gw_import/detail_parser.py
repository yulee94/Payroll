"""
Parse COSS GW document detail from JSON export, HTML page, or browser snapshot YAML.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
from pathlib import Path
from typing import Any

_SNAPSHOT_DOC_ID = re.compile(
    r"name: ([0-9a-f]{18,})\s+ref: e\d+\s+value: \1",
    re.IGNORECASE,
)
_SNAPSHOT_LINK_TITLE = re.compile(
    r"- role: link\s+name: ([^\n]+)\s+ref: e\d+",
)
_HTML_TITLE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)
_HTML_BODY = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.I)
_HTML_ATTACH = re.compile(
    r'href=["\']([^"\']+(?:download|attach|file)[^"\']*)["\'][^>]*>([^<]{1,200})',
    re.I,
)
_SNAPSHOT_ATTACH = re.compile(
    r"name:\s+([^\n]+\.(?:pdf|hwp|docx?|xlsx?|zip|png|jpe?g|pptx?))\s",
    re.I,
)
_SNAPSHOT_LISTITEM = re.compile(
    r"- role: listitem\s+name:\s+([^\n]+)",
    re.I,
)
_IFRAME_BODY = re.compile(
    r"<div[^>]*id=[\"']dext_body[\"'][^>]*>([\s\S]*?)</div>\s*</html>",
    re.I,
)
_APPROVAL_ARROW = re.compile(r"([^\s▶]+)\(([^)]+)\)")
_SAMPLE_LINE = re.compile(
    r'^\[([^\]]+)\]\s*(.+?)\s+(\d{4}\.\d{2}\.\d{2})?\s*(?:새창)?\s*(.*)$'
)


def stable_gw_doc_id(seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:18]
    return h


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", html, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(re.sub(r"\s+", " ", text)).strip()
    return text


def parse_approval_line(line: str) -> list[dict[str, str]]:
    """Parse '김미라(합의) ▶ 전성진(결재)' style approval chain."""
    steps: list[dict[str, str]] = []
    for part in re.split(r"\s*▶\s*", line):
        part = part.strip().strip('"')
        if not part:
            continue
        m = _APPROVAL_ARROW.search(part)
        if m:
            steps.append({"name": m.group(1).strip(), "role": m.group(2).strip(), "status": ""})
        elif part.endswith(")") and "(" in part:
            name, role = part.rsplit("(", 1)
            steps.append({"name": name.strip(), "role": role.rstrip(")").strip(), "status": ""})
    return steps


def parse_inbox_sample_line(line: str) -> dict[str, Any]:
    """Parse gw_scrape_extended document_samples line into list row + partial detail."""
    raw = str(line or "").strip().strip('"')
    form_name = ""
    m_form = re.match(r"\[([^\]]+)\]", raw)
    if m_form:
        form_name = m_form.group(1).strip()
        raw = raw[m_form.end() :].strip()
    date_m = re.search(r"(\d{4}\.\d{2}\.\d{2})", raw)
    drafted_at = date_m.group(1).replace(".", "-") if date_m else ""
    if date_m:
        raw = raw[: date_m.start()] + raw[date_m.end() :]
    raw = raw.replace("새창", "").strip()
    approval_part = ""
    if "▶" in raw or "(기안)" in raw:
        idx = raw.find("(")
        if idx > 0 and any(x in raw for x in ("기안", "합의", "결재")):
            title = raw[:idx].strip()
            approval_part = raw[idx - 1 if raw[idx - 1].isalpha() else idx :].strip()
            if title.endswith("("):
                title = title[:-1].strip()
        else:
            title = raw
    else:
        title = raw
    title = re.sub(r"\s+", " ", title).strip()[:300]
    steps = parse_approval_line(approval_part) if approval_part else []
    drafter = ""
    if steps and steps[0].get("role") == "기안":
        drafter = steps[0].get("name", "")
    gid = stable_gw_doc_id(f"{form_name}|{title}|{drafted_at}")
    return {
        "gw_doc_id": gid,
        "title": title,
        "form_name": form_name,
        "drafted_at": drafted_at,
        "drafter": drafter,
        "approval_workflow_json": {"steps": steps, "raw_line": line},
        "gw_list": "to_approve",
    }


def parse_popup_snapshot(text: str, *, gw_doc_id: str = "") -> dict[str, Any]:
    """Parse eapApprViewPopup browser snapshot (attachments + metadata; body often in iframe)."""
    gid = gw_doc_id.strip()
    if not gid:
        m = re.search(r"apprId=([0-9a-f]{18,})", text, re.I)
        if m:
            gid = m.group(1)

    attach_names: list[str] = []
    for m in _SNAPSHOT_ATTACH.finditer(text):
        name = m.group(1).strip()
        if name and name not in attach_names:
            attach_names.append(name)
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("name:") and re.search(
            r"\.(pdf|hwp|docx?|xlsx?|zip|png|jpe?g|pptx?)\s*$", s, re.I
        ):
            name = s.split("name:", 1)[-1].strip()
            if name and name not in attach_names and "선택 파일" not in name:
                attach_names.append(name)

    list_items = [x.strip() for x in _SNAPSHOT_LISTITEM.findall(text)]
    skip_phrases = (
        "조회현황",
        "결재현황",
        "이 문서를",
        "메일 보내기",
        "PC 저장",
        "문서 정보",
        "이전 문서",
        "다음 문서",
        "인쇄",
        "결재 의견",
        "문서변경",
        "댓글",
        "내 PC",
        "첨부",
        "전체",
        "내 컴퓨터",
        "메신저",
        "비밀결재",
        "비밀번호",
        "목록을 선택",
        "의견 목록",
        "변경 이력",
    )
    meta_lines = [
        li
        for li in list_items
        if li
        and not any(p in li for p in skip_phrases)
        and not re.search(r"\.(pdf|hwp|docx?|xlsx?)$", li, re.I)
    ]

    return {
        "gw_doc_id": gid,
        "title": "",
        "content_text": "\n".join(meta_lines) if meta_lines else "",
        "content_html": "",
        "attachments": [{"name": n, "path": "", "size": 0} for n in attach_names],
        "approval_workflow_json": {"popup_list_items": list_items[:40]},
        "source": "browser_popup_snapshot",
        "_iframe_blocked": True,
    }


def parse_snapshot_yaml(text: str) -> dict[str, Any]:
    """Best-effort parse of browser accessibility snapshot for one document view."""
    if "eapApprViewPopup" in text or "유류비" in text or _SNAPSHOT_ATTACH.search(text):
        popup = parse_popup_snapshot(text)
        if popup.get("attachments") or popup.get("content_text"):
            return popup

    doc_ids = _SNAPSHOT_DOC_ID.findall(text)
    gw_doc_id = doc_ids[0] if doc_ids else ""
    links = [m.strip() for m in _SNAPSHOT_LINK_TITLE.findall(text) if m.strip() and m.strip() != "새창으로 열기"]
    title = ""
    for name in links:
        if len(name) > 8 and "새창" not in name:
            title = name
            break
    if not title and links:
        title = links[0]

    field_lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("name:") and "ref:" not in s:
            val = s.split("name:", 1)[-1].strip()
            if val and val not in (title, gw_doc_id, "새창으로 열기"):
                field_lines.append(val)

    body_parts = [x for x in field_lines if len(x) > 20 or "\n" in x]
    content_text = "\n".join(body_parts) if body_parts else "\n".join(field_lines[-30:])
    attach_names = [x for x in field_lines if re.search(r"\.(pdf|hwp|docx?|xlsx?|zip|png|jpg)$", x, re.I)]

    return {
        "gw_doc_id": gw_doc_id,
        "title": title,
        "content_text": content_text,
        "content_html": "",
        "attachments": [{"name": n, "path": "", "size": 0} for n in attach_names],
        "approval_workflow_json": {"snapshot_fields": field_lines[:80]},
        "source": "browser_snapshot",
    }


def parse_iframe_html(html: str, *, gw_doc_id: str = "") -> dict[str, Any]:
    """Extract COSS form body from saved iframe / print HTML."""
    body_m = _IFRAME_BODY.search(html)
    if body_m:
        body_html = body_m.group(1)
    else:
        body_m = _HTML_BODY.search(html)
        body_html = body_m.group(1) if body_m else html
    return parse_html_detail(
        f"<html><body>{body_html}</body></html>",
        gw_doc_id=gw_doc_id,
    )


def parse_html_detail(html: str, *, gw_doc_id: str = "") -> dict[str, Any]:
    title_m = _HTML_TITLE.search(html)
    title = title_m.group(1).strip() if title_m else ""
    body_m = _IFRAME_BODY.search(html) or _HTML_BODY.search(html)
    body_html = body_m.group(1) if body_m else html
    content_text = _strip_html(body_html)
    attachments: list[dict[str, Any]] = []
    for href, label in _HTML_ATTACH.findall(body_html):
        name = html_lib.unescape(label.strip()) or Path(href).name
        attachments.append({"name": name, "url": href, "path": "", "size": 0})
    return {
        "gw_doc_id": gw_doc_id,
        "title": title,
        "content_html": body_html[:500_000],
        "content_text": content_text[:200_000],
        "attachments": attachments,
        "source": "html",
    }


def parse_detail_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a detail JSON dict (from scrape tool or fixture)."""
    gid = str(data.get("gw_doc_id") or "").strip()
    if not gid and data.get("title"):
        gid = stable_gw_doc_id(str(data.get("title")))
    out: dict[str, Any] = {
        "gw_doc_id": gid,
        "title": str(data.get("title") or "").strip(),
        "doc_number": str(data.get("doc_number") or data.get("document_no") or "").strip(),
        "drafter": str(data.get("drafter") or "").strip(),
        "drafted_at": str(data.get("drafted_at") or data.get("requested_date") or "").strip()[:10],
        "completed_at": str(data.get("completed_at") or "").strip()[:10],
        "form_name": str(data.get("form_name") or "").strip(),
        "gw_list": str(data.get("gw_list") or data.get("list_kind") or "").strip(),
        "gw_url": str(data.get("gw_url") or "").strip(),
        "content_html": str(data.get("content_html") or "").strip(),
        "content_text": str(data.get("content_text") or data.get("content") or "").strip(),
        "attachments": [],
        "approval_workflow_json": data.get("approval_workflow_json")
        if isinstance(data.get("approval_workflow_json"), dict)
        else {"steps": data.get("approval_steps") or []},
        "source": str(data.get("source") or "json"),
    }
    if not out["content_text"] and out["content_html"]:
        out["content_text"] = _strip_html(out["content_html"])
    raw_att = data.get("attachments") or []
    if isinstance(raw_att, list):
        for a in raw_att:
            if isinstance(a, dict):
                out["attachments"].append(
                    {
                        "name": str(a.get("name") or "").strip(),
                        "path": str(a.get("path") or "").strip(),
                        "size": int(a.get("size") or 0),
                        "url": str(a.get("url") or "").strip(),
                    }
                )
            elif isinstance(a, str) and a.strip():
                out["attachments"].append({"name": a.strip(), "path": "", "size": 0, "url": ""})
    return out


def load_detail_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Detail JSON must be an object")
        return parse_detail_payload(data)
    if path.suffix.lower() in (".html", ".htm"):
        gid = path.stem.split("_")[0] if "_" in path.stem else path.stem
        parsed = parse_iframe_html(text, gw_doc_id=gid)
        return parse_detail_payload(parsed)
    if path.suffix.lower() in (".yaml", ".yml", ".log"):
        return parse_detail_payload(parse_snapshot_yaml(text))
    return parse_detail_payload(parse_snapshot_yaml(text))
