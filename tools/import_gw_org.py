"""
COSS 그룹웨어 조직·인사 스냅샷 → Bitween 급여앱 반영 (일회성 import).

입력: AppData/Local/Temp 의 coss_tree_export.json, coss_personnel.json
(사전 실행: coss_tree_enrich.py, coss_fetch_personnel.py)

자격증명은 저장하지 않습니다.
"""
from __future__ import annotations

import json
import re
import secrets
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.org_positions import normalize_position
from core.org_store import ORG_DIR, _load_raw, _save_raw
from core.paths import app_data_dir
from core.roles import ROLE_STAFF
from core.tenant_store import TENANTS_FILE, load_registry, save_registry

TREE_EXPORT = Path(r"C:\Users\MY\AppData\Local\Temp\coss_tree_export.json")
PERSONNEL_EXPORT = Path(r"C:\Users\MY\AppData\Local\Temp\coss_personnel.json")
REPORT_PATH = ROOT / "data" / "imports" / "gw_import_report.json"

# 기존 테넌트 매핑 (display_name_ko 기준)
KNOWN_TENANT_BY_CORP: dict[str, str] = {
    "㈜코스": "coss",
    "(주)코스": "coss",
    "㈜엘소": "elso",
    "(주)엘소": "elso",
    "㈜씨앤엘": "cnlos",
    "(주)씨엔엘": "cnlos",
    "(주)씨엔엘오에스": "cnlos",
    "㈜청운": "cheongun",
    "(주)청운": "cheongun",
}

DEFAULT_PLATFORMS = ["payroll", "hr", "workflow"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slug_id(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9가-힣]+", "", name)
    s = s.replace("주", "").replace("㈜", "")[:12].lower()
    if not s:
        s = "corp"
    if s[0].isdigit():
        s = "c" + s
    return s


def corp_display_ko(short: str) -> str:
    if short.startswith("(주)") or short.startswith("㈜"):
        return short
    return f"(주){short.replace('㈜', '')}"


def resolve_tenant_id(corp_name: str, registry: dict) -> str:
    corp = corp_name.strip()
    if corp in KNOWN_TENANT_BY_CORP:
        return KNOWN_TENANT_BY_CORP[corp]
    for ko, tid in KNOWN_TENANT_BY_CORP.items():
        if ko in corp or corp in ko:
            return tid
    tid = slug_id(corp)
    tenants = registry.get("tenants") or {}
    if tid in tenants:
        return tid
    # 충돌 방지
    base = tid
    n = 2
    while tid in tenants:
        tid = f"{base}{n}"
        n += 1
    return tid


def infer_corp_from_dept(dept_name: str, affiliates: list[str]) -> str:
    dn = dept_name.strip()
    if dn in ("퇴사", "부서미지정", "회사"):
        return "㈜코스"
    for aff in sorted(affiliates, key=len, reverse=True):
        if dn.startswith(aff) or aff.replace("㈜", "(주)") in dn:
            return aff
    m = re.match(r"^(\(주\)[^\s_]+|㈜[^\s_]+)", dn)
    if m:
        token = m.group(1).replace("(주)", "㈜")
        for aff in affiliates:
            if aff.replace("㈜", "") in token.replace("㈜", ""):
                return aff
        return token if token.startswith("㈜") else f"㈜{token.replace('(주)', '')}"
    return "㈜코스"


def merge_organizations(affiliates: list[dict]) -> dict:
    path = ROOT / "config" / "organizations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    names = []
    for a in affiliates:
        nm = str(a.get("name") or "").strip()
        if nm and nm not in ("회사", "부서미지정"):
            names.append(nm)
    # unique preserve order
    seen: set[str] = set()
    aff_list = []
    for nm in names:
        if nm in seen:
            continue
        seen.add(nm)
        aff_list.append({"name": corp_display_ko(nm), "workplaces": []})
    if aff_list:
        data["affiliates"] = aff_list
        if not data.get("default_affiliate"):
            data["default_affiliate"] = aff_list[0]["name"]
    return data


def ensure_tenant(registry: dict, corp: str) -> str:
    tid = resolve_tenant_id(corp, registry)
    tenants = registry.setdefault("tenants", {})
    if tid not in tenants:
        short = corp.replace("㈜", "").replace("(주)", "").strip()
        tenants[tid] = {
            "tenant_id": tid,
            "display_name": short.upper() if len(short) <= 6 else short,
            "display_name_ko": corp_display_ko(corp),
            "login_id": tid,
            "notes": f"COSS GW import ({corp})",
            "logo_filename": "",
            "data_affiliates": [corp_display_ko(corp)],
            "created_at": _now(),
            "updated_at": _now(),
        }
    else:
        raw = tenants[tid]
        ko = corp_display_ko(corp)
        das = raw.get("data_affiliates") or []
        if ko not in das:
            das.append(ko)
            raw["data_affiliates"] = das
            raw["updated_at"] = _now()
    return tid


def build_org_units(
    tenant_id: str,
    corp: str,
    departments: list[dict],
    root_gw: str,
) -> tuple[str, dict[str, dict]]:
    """Returns root_id and units dict for one tenant."""
    units: dict[str, dict] = {}
    root_id = f"gw_{root_gw}" if root_gw else f"gw_root_{tenant_id}"
    units[root_id] = {
        "unit_id": root_id,
        "name": corp,
        "parent_id": "",
        "sort_order": 0,
        "platform_ids": DEFAULT_PLATFORMS,
        "head_user_id": "",
        "notes": "GW import root",
        "created_at": _now(),
    }
    # filter departments for this corp
    corp_depts = []
    for d in departments:
        dn = str(d.get("name") or "")
        if not dn or dn in ("회사", "부서미지정"):
            continue
        if infer_corp_from_dept(dn, [corp]) == corp or dn.startswith(corp):
            corp_depts.append(d)
    # index by gw_key
    by_key = {d["gw_key"]: d for d in corp_depts if d.get("gw_key")}
    added: set[str] = set()

    def ensure_unit(gw_key: str, sort_order: int) -> str:
        if gw_key in added:
            return gw_key
        d = by_key.get(gw_key)
        if not d:
            return ""
        parent_gw = str(d.get("parent_gw_id") or "")
        parent_uid = root_id
        if parent_gw and parent_gw in by_key:
            parent_uid = ensure_unit(parent_gw, 0) or root_id
        elif parent_gw and parent_gw.startswith("C"):
            parent_uid = root_id
        uid = gw_key
        units[uid] = {
            "unit_id": uid,
            "name": d.get("name") or gw_key,
            "parent_id": parent_uid,
            "sort_order": sort_order,
            "platform_ids": DEFAULT_PLATFORMS,
            "head_user_id": "",
            "notes": "GW import",
            "created_at": _now(),
        }
        added.add(gw_key)
        return uid

    for i, d in enumerate(sorted(corp_depts, key=lambda x: x.get("name", ""))):
        ensure_unit(d["gw_key"], i + 1)

    return root_id, units


def merge_org_file(tenant_id: str, root_id: str, new_units: dict[str, dict], *, replace: bool) -> int:
    raw = _load_raw(tenant_id)
    existing = raw.get("units") or {}
    if replace or not existing:
        raw["units"] = new_units
        raw["root_id"] = root_id
    else:
        # merge: keep existing, add/update GW units
        for uid, row in new_units.items():
            existing[uid] = row
        raw["units"] = existing
        if not raw.get("root_id"):
            raw["root_id"] = root_id
    _save_raw(tenant_id, raw)
    return len(new_units)


def sync_users(
    personnel: list[dict],
    corp_to_tenant: dict[str, str],
    affiliates: list[str],
    *,
    create_missing: bool = True,
) -> dict[str, int]:
    from core.user_store import _load_raw, _save_raw, find_user_by_username, _hash_password

    stats = {"updated": 0, "created": 0, "skipped": 0}
    raw = _load_raw()
    users = raw.setdefault("users", {})
    by_tenant: dict[str, list[str]] = raw.setdefault("by_tenant", {})

    for p in personnel:
        name = str(p.get("name") or "").strip()
        uname = str(p.get("gw_user_id") or "").strip().lower()
        dept_name = str(p.get("dept_name") or "")
        if not name or not uname:
            stats["skipped"] += 1
            continue
        if dept_name == "퇴사":
            stats["skipped"] += 1
            continue
        corp = infer_corp_from_dept(dept_name, affiliates)
        tid = corp_to_tenant.get(corp, "coss")
        dept_id = str(p.get("dept_id") or "")
        org_unit = dept_id if dept_id and not dept_id.startswith("RETIREMENT") else ""
        pos = normalize_position(str(p.get("position") or ""))

        existing = find_user_by_username(tid, uname)
        if existing:
            row = users.get(existing.user_id)
            if isinstance(row, dict):
                row["display_name"] = name
                if org_unit:
                    row["org_unit_id"] = org_unit
                row["position"] = pos
                stats["updated"] += 1
            continue

        if not create_missing:
            stats["skipped"] += 1
            continue

        uid = uuid.uuid4().hex
        salt_hex, hash_hex = _hash_password(secrets.token_urlsafe(12))
        users[uid] = {
            "user_id": uid,
            "tenant_id": tid,
            "username": uname,
            "display_name": name,
            "role": ROLE_STAFF,
            "org_unit_id": org_unit,
            "position": pos,
            "manager_user_id": "",
            "password_salt": salt_hex,
            "password_hash": hash_hex,
            "created_at": _now(),
            "gw_import": True,
            "gw_emp_id": p.get("gw_emp_id"),
            "notes": "GW import — 비밀번호 재설정 필요",
        }
        by_tenant.setdefault(tid, []).append(uid)
        stats["created"] += 1

    _save_raw(raw)
    return stats


def main() -> None:
    if not TREE_EXPORT.is_file() or not PERSONNEL_EXPORT.is_file():
        raise SystemExit("Export files missing. Run GW export scripts first.")

    tree = json.loads(TREE_EXPORT.read_text(encoding="utf-8"))
    personnel = json.loads(PERSONNEL_EXPORT.read_text(encoding="utf-8"))

    affiliates_raw = tree.get("affiliates") or []
    affiliate_names = [
        str(a.get("name") or "").strip()
        for a in affiliates_raw
        if str(a.get("name") or "").strip() not in ("회사",)
    ]
    # dedupe
    seen: set[str] = set()
    affiliate_names = [x for x in affiliate_names if not (x in seen or seen.add(x))]

    org_cfg = merge_organizations(affiliates_raw)
    (ROOT / "config" / "organizations.json").write_text(
        json.dumps(org_cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    registry = load_registry()
    corp_to_tenant: dict[str, str] = {}
    for corp in affiliate_names:
        corp_to_tenant[corp] = ensure_tenant(registry, corp)
    save_registry(registry)

    departments = tree.get("departments") or []
    org_counts: dict[str, int] = {}
    for corp, tid in corp_to_tenant.items():
        root_gw = "C1234567892"
        root_id, units = build_org_units(tid, corp, departments, root_gw)
        # coss: merge with existing bootstrap org
        replace = tid != "coss" or not (ORG_DIR / f"{tid}.json").is_file()
        if tid == "coss" and (ORG_DIR / "coss.json").is_file():
            replace = False
        n = merge_org_file(tid, root_id, units, replace=replace)
        org_counts[tid] = n

    user_stats = sync_users(personnel, corp_to_tenant, affiliate_names, create_missing=True)

    report = {
        "imported_at": _now(),
        "affiliate_count": len(affiliate_names),
        "affiliates": affiliate_names,
        "tenants": corp_to_tenant,
        "org_unit_counts": org_counts,
        "personnel_total": len(personnel),
        "user_sync": user_stats,
        "notes": [
            "신규 GW 연동 계정은 임의 비밀번호이며 앱에서 재설정이 필요합니다.",
            "coss 테넌트 조직도는 기존 부트스트랩 구조에 GW 부서를 병합했습니다.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
