"""
scripts/update_publish.py - 자동 업데이트 채널(version.json + EXE) 배포 공통 로직
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTABLE_EXE_NAME = "COSS_Payroll.exe"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_desktop_channel() -> Path:
    return Path.home() / "Desktop" / "Bitween_Payroll_Updates"


def write_portable_manifest(
    *,
    version: str,
    package_exe: Path,
    manifest_path: Path,
    release_notes: str = "",
    mandatory: bool = False,
) -> None:
    payload = {
        "version": version,
        "release_date": date.today().isoformat(),
        "release_notes": release_notes or "Bitween 급여·인사 업데이트",
        "mandatory": mandatory,
        "update_kind": "portable_exe",
        "installer_url": str(package_exe.resolve()),
        "installer_sha256": sha256_file(package_exe),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_update_channel_config(config_path: Path, manifest_url: str) -> None:
    payload = {
        "manifest_url": manifest_url.replace("/", "\\"),
        "description": "자동 업데이트 manifest 경로 (UNC·https·로컬 파일)",
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_update_channel(
    exe: Path,
    version: str,
    channel_dir: Path,
    *,
    sync_templates: bool = True,
    release_notes: str = "",
) -> Path:
    """
    채널 폴더에 COSS_Payroll.exe + version.json (+ templates) 배포.
    Returns manifest path.
    """
    channel_dir.mkdir(parents=True, exist_ok=True)
    dest_exe = channel_dir / PORTABLE_EXE_NAME
    shutil.copy2(exe, dest_exe)

    if sync_templates:
        src_tpl = ROOT / "templates"
        dest_tpl = channel_dir / "templates"
        if src_tpl.is_dir():
            if dest_tpl.exists():
                shutil.rmtree(dest_tpl)
            shutil.copytree(
                src_tpl,
                dest_tpl,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "~$*"),
            )

    manifest_path = channel_dir / "version.json"
    write_portable_manifest(
        version=version,
        package_exe=dest_exe,
        manifest_path=manifest_path,
        release_notes=release_notes,
    )
    return manifest_path
