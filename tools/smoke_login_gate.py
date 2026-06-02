"""Smoke: login gate and per-tenant payroll data scope."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.access_control import load_records_for_period_secured
from core.session_service import get_session, login, logout, session_tenant_id, try_restore_session
from core.tenant_data_scope import discover_scopes_for_tenant, tenant_allowed_affiliates
from core.tenant_store import get_active_tenant_id
from core.user_store import get_user


def _scopes_for_ui() -> list:
    tid = session_tenant_id()
    return discover_scopes_for_tenant(tid) if tid else []


def main() -> None:
    logout(clear_saved=True)
    try_restore_session()
    assert get_session() is None
    assert _scopes_for_ui() == []
    assert load_records_for_period_secured("2026-05", session=None) == []
    print("OK logged-out: empty periods and records")

    rec = get_user("fa44b2e202f74095a8d567d271c3cfe6")
    assert rec is not None and rec.tenant_id == "coss"
    login(rec, remember=False)
    tid = session_tenant_id()
    assert tid == "coss"
    coss_scopes = discover_scopes_for_tenant("coss")
    assert len(coss_scopes) > 0, "coss user should see coss scopes"
    elso_aff = tenant_allowed_affiliates("test_a")
    for s in coss_scopes:
        assert s.affiliate in tenant_allowed_affiliates("coss")
        assert s.affiliate not in elso_aff or s.affiliate == "(주)코스"
    print(f"OK coss user: {len(coss_scopes)} scopes, affiliates={tenant_allowed_affiliates('coss')}")

    logout(clear_saved=True)
    rec_b = get_user("5f2ea5c4c6f743d69aa1f4b05c3ac154")
    assert rec_b is not None and rec_b.tenant_id == "test_a"
    login(rec_b, remember=False)
    assert session_tenant_id() == "test_a"
    assert get_active_tenant_id() == "test_a"
    a_scopes = _scopes_for_ui()
    coss_only = discover_scopes_for_tenant("coss")
    assert len(a_scopes) >= 0
    for s in a_scopes:
        assert s.affiliate in tenant_allowed_affiliates("test_a")
    for s in coss_only:
        if s.affiliate in tenant_allowed_affiliates("coss") and s.affiliate not in tenant_allowed_affiliates(
            "test_a"
        ):
            assert s.key not in {x.key for x in a_scopes}, f"test_a must not see coss scope {s.key}"
    print(f"OK test_a user: {len(a_scopes)} scopes, active={get_active_tenant_id()}")
    print("All smoke checks passed.")


if __name__ == "__main__":
    main()
