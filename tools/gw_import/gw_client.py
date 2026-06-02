"""
gw_client.py - COSS groupware (gw.cossok.com) HTTP session + API helpers.

Credentials via environment only (never commit):
  GW_USER, GW_PASS
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

GW_BASE = os.environ.get("GW_BASE_URL", "https://gw.cossok.com/gw").rstrip("/")
GW_USER = os.environ.get("GW_USER", "")
GW_PASS = os.environ.get("GW_PASS", "")


def _i18n_ko(blob: str | dict | None, *, dept: bool = True) -> str:
    if blob is None:
        return ""
    if isinstance(blob, dict):
        data = blob
    else:
        try:
            data = json.loads(str(blob))
        except json.JSONDecodeError:
            return str(blob)
    ko = data.get("ko") if isinstance(data, dict) else None
    if not isinstance(ko, dict):
        return ""
    if dept:
        return str(ko.get("deptName") or ko.get("cmpName") or "").strip()
    return str(ko.get("cmpName") or ko.get("deptName") or "").strip()


def node_label(node: dict[str, Any]) -> str:
    return _i18n_ko(node.get("deptI18ns")) or _i18n_ko(node.get("cmpI18ns")) or str(node.get("title") or "")


class GwClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self._logged_in = False

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Bitween-GW-Import/1.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }

    def login(self, *, user: str | None = None, password: str | None = None) -> dict[str, Any]:
        uid = (user or GW_USER).strip()
        pwd = password or GW_PASS
        if not uid or not pwd:
            raise ValueError("GW_USER and GW_PASS environment variables are required")

        self.session.headers.update(self._headers())
        self.session.get(f"{GW_BASE}/sub/common/login/cmmLogin.do", timeout=60)

        payload: dict[str, Any] = {
            "userId": uid,
            "pwd": pwd,
            "deptId": "",
            "langCode": "ko",
            "gwUrl": "gw.cossok.com",
            "sec": "",
        }
        dept_resp = self.session.post(
            f"{GW_BASE}/data/common/login/selectDepartmentList.do",
            data=json.dumps(payload),
            timeout=60,
        )
        dept_resp.raise_for_status()
        depts = dept_resp.json()
        if isinstance(depts, list) and depts:
            payload["deptId"] = next(
                (str(d.get("deptId") or "") for d in depts if d.get("reprsntDeptYn") == "Y"),
                str(depts[0].get("deptId") or ""),
            )

        login_resp = self.session.post(
            f"{GW_BASE}/data/common/login/selectLoginFlag.do?lang=ko",
            data=json.dumps(payload),
            timeout=60,
        )
        login_resp.raise_for_status()
        result = login_resp.json()
        code = result.get("resultCode") if isinstance(result, dict) else None
        if not isinstance(result, dict) or str(code) not in ("0", "00"):
            raise RuntimeError(f"Groupware login failed: {result!r}")
        self._logged_in = True
        return result

    def ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        self.ensure_login()
        url = path if path.startswith("http") else f"{GW_BASE}/{path.lstrip('/')}"
        resp = self.session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "json" not in ct and not resp.text.strip().startswith(("{", "[")):
            raise RuntimeError(f"Expected JSON from {url}, got {ct}: {resp.text[:200]}")
        return resp.json()

    def org_tree_nodes(
        self,
        dept_id: str,
        *,
        include_system: bool = True,
        node_type: str = "1",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"deptId": dept_id, "langCode": "ko"}
        if include_system:
            params["includeSystemYn"] = "Y"
            params["type"] = node_type
        raw = self.get_json("data/organization/selectOrgTreeList.do", params=params)
        if isinstance(raw, list):
            return [n for n in raw if isinstance(n, dict)]
        return []

    def walk_org_tree(
        self,
        root_id: str = "ROOT",
        *,
        max_depth: int = 12,
    ) -> list[dict[str, Any]]:
        """Depth-first flatten of org tree nodes (lazy children loaded)."""
        flat: list[dict[str, Any]] = []
        seen: set[str] = set()

        def visit(dept_id: str, depth: int, parent_key: str) -> None:
            if depth > max_depth or dept_id in seen:
                return
            seen.add(dept_id)
            nodes = self.org_tree_nodes(dept_id)
            for node in nodes:
                key = str(node.get("key") or node.get("deptId") or node.get("cmpId") or "")
                row = {
                    **node,
                    "_depth": depth,
                    "_parent_fetch_id": parent_key,
                    "_label_ko": node_label(node),
                }
                flat.append(row)
                child_id = key
                ntype = node.get("type")
                if node.get("folder") and child_id and ntype in (1, 2, None):
                    visit(child_id, depth + 1, key)
                elif node.get("folder") and str(node.get("deptId") or ""):
                    visit(str(node["deptId"]), depth + 1, key)

        visit(root_id, 0, "")
        return flat
