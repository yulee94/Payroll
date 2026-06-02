"""Fix GW-imported tenant IDs to ASCII slugs required by tenant_store."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.org_store import ORG_DIR
from core.tenant_store import TENANTS_FILE, load_registry, save_registry
from core.user_store import USERS_FILE, _load_raw, _save_raw

REMAP = {
    "대상솔루션": "daesang",
    "디에스엘": "dsl",
    "베스텍": "bestec",
    "진성": "jinung",
    "케이앤엘": "knl",
    "제이와이테크": "jiyitech",
    "코스텍": None,  # merge into coss
}


def main() -> None:
    reg = load_registry()
    tenants = reg.get("tenants") or {}
    users_raw = _load_raw()
    users = users_raw.get("users") or {}
    by_tenant = users_raw.get("by_tenant") or {}

    for old_tid, new_tid in REMAP.items():
        if old_tid not in tenants:
            continue
        old = tenants.pop(old_tid)
        if new_tid is None:
            # merge data_affiliates into coss
            coss = tenants.get("coss", {})
            for a in old.get("data_affiliates") or []:
                if a not in (coss.get("data_affiliates") or []):
                    coss.setdefault("data_affiliates", []).append(a)
            # move org file units into coss
            old_org = ORG_DIR / f"{old_tid}.json"
            if old_org.is_file():
                coss_org_path = ORG_DIR / "coss.json"
                if coss_org_path.is_file():
                    cdata = json.loads(coss_org_path.read_text(encoding="utf-8"))
                    odata = json.loads(old_org.read_text(encoding="utf-8"))
                    cdata.setdefault("units", {}).update(odata.get("units") or {})
                    coss_org_path.write_text(json.dumps(cdata, ensure_ascii=False, indent=2), encoding="utf-8")
                old_org.unlink()
            # reassign users
            for uid in by_tenant.pop(old_tid, []):
                row = users.get(uid)
                if isinstance(row, dict):
                    row["tenant_id"] = "coss"
                    by_tenant.setdefault("coss", []).append(uid)
            continue

        if new_tid in tenants:
            continue
        old["tenant_id"] = new_tid
        old["login_id"] = new_tid
        tenants[new_tid] = old
        org_old = ORG_DIR / f"{old_tid}.json"
        org_new = ORG_DIR / f"{new_tid}.json"
        if org_old.is_file():
            shutil.move(str(org_old), str(org_new))
        for uid in by_tenant.pop(old_tid, []):
            row = users.get(uid)
            if isinstance(row, dict):
                row["tenant_id"] = new_tid
            by_tenant.setdefault(new_tid, []).append(uid)

    reg["tenants"] = tenants
    save_registry(reg)
    users_raw["by_tenant"] = by_tenant
    _save_raw(users_raw)
    print("fixed tenants", list(REMAP.keys()))


if __name__ == "__main__":
    main()
