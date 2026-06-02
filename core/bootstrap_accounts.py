"""
core/bootstrap_accounts.py - 설치본·첫 실행 시 계정·고객사 설정 복사
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from core.paths import app_data_dir, app_install_dir, bundle_dir, ensure_app_data_dirs, is_frozen


def _registry_has_users(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(isinstance(data, dict) and data.get("users"))
    except (OSError, json.JSONDecodeError):
        return False


def _copy_if_missing(src: Path, dest: Path) -> bool:
    if not src.is_file() or dest.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def ensure_bootstrap_user_data() -> None:
    """
    EXE 설치 후 로그인용 users/registry.json · tenants.json 이 없으면
    설치 폴더 또는 개발용 번들에서 AppData 로 복사합니다.
    """
    data = ensure_app_data_dirs()
    users_dest = data / "users" / "registry.json"
    tenants_dest = data / "tenants.json"

    if _registry_has_users(users_dest) and tenants_dest.is_file():
        return

    sources: list[Path] = []
    bundled = bundle_dir()
    if bundled is not None:
        sources.append(bundled)
    if is_frozen():
        sources.append(app_install_dir())
    dev_root = Path(__file__).resolve().parent.parent
    if dev_root not in sources:
        sources.append(dev_root)

    for src in sources:
        if not _registry_has_users(users_dest):
            _copy_if_missing(src / "users" / "registry.json", users_dest)
            _copy_if_missing(src / "bootstrap" / "users_registry.json", users_dest)
        if not tenants_dest.is_file():
            _copy_if_missing(src / "tenants.json", tenants_dest)
            sample = src / "tenants.json.sample"
            if sample.is_file():
                _copy_if_missing(sample, tenants_dest)
        if _registry_has_users(users_dest):
            break

    from core.bootstrap_org import ensure_coss_org_bootstrap
    from core.bootstrap_group import ensure_coss_group

    ensure_coss_org_bootstrap()
    ensure_coss_group()
