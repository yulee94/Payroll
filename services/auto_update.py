"""
services/auto_update.py - 자동 업데이트 (설치본 재실행 방식)

회사 공유폴더/내부 URL의 version.json을 확인하고,
새 설치 파일(.exe)을 받아 Inno Setup 설치 프로그램을 조용히 실행합니다.
재설치 없이 IT가 공유폴더만 갱신하면 전 직원 PC에 반영됩니다.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import APP_CONFIG, APP_VERSION
from core.paths import is_frozen
from logger_util import get_logger

log = get_logger()


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    release_notes: str
    mandatory: bool
    installer_url: str
    installer_sha256: str = ""
    release_date: str = ""
    update_kind: str = ""  # portable_exe | inno (기본: 파일명으로 추론)


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    manifest: UpdateManifest | None = None
    error: str = ""

    @property
    def has_update(self) -> bool:
        return self.manifest is not None and parse_version(self.manifest.version) > parse_version(
            self.current_version
        )


def parse_version(value: str) -> tuple[int, ...]:
    raw = (value or "0").strip().lstrip("vV")
    parts: list[int] = []
    for chunk in raw.replace("_", ".").split("."):
        if not chunk:
            continue
        num = ""
        for ch in chunk:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num or "0"))
    return tuple(parts) or (0,)


def resolve_manifest_url() -> str:
    """
    업데이트 manifest 경로 (우선순위).
    1) config/update_channel.json (AppData · 설치 폴더)
    2) APP_CONFIG.update.manifest_url
    3) 바탕화면 Bitween_Payroll_Updates/version.json
    4) release/update_channel/version.json (개발 트리)
    """
    from core.paths import app_data_dir, app_install_dir, dev_root

    def _read_channel_file(path: Path) -> str:
        if not path.is_file():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return str(data.get("manifest_url") or "").strip()
        except (OSError, json.JSONDecodeError):
            return ""
        return ""

    for channel_path in (
        app_data_dir() / "update_channel.json",
        app_install_dir() / "config" / "update_channel.json",
    ):
        url = _read_channel_file(channel_path)
        if url:
            return url

    cfg_url = APP_CONFIG.update.manifest_url.strip()
    if cfg_url:
        return cfg_url

    desktop_manifest = Path.home() / "Desktop" / "Bitween_Payroll_Updates" / "version.json"
    if desktop_manifest.is_file():
        return str(desktop_manifest)

    repo_manifest = dev_root() / "release" / "update_channel" / "version.json"
    if repo_manifest.is_file():
        return str(repo_manifest)

    return ""


def should_check_updates() -> bool:
    cfg = APP_CONFIG.update
    if not cfg.enabled or not resolve_manifest_url():
        return False
    if is_frozen():
        return cfg.check_on_startup
    return cfg.check_on_startup and cfg.check_in_dev


def _load_manifest_text(url: str) -> str:
    url = url.strip()
    if url.startswith(("http://", "https://")):
        req = urllib.request.Request(url, headers={"User-Agent": "COSS-Payroll-Updater"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8-sig")
    # UNC · 로컬 경로
    path = Path(url)
    if not path.is_file():
        raise FileNotFoundError(f"업데이트 manifest를 찾을 수 없습니다: {path}")
    return path.read_text(encoding="utf-8-sig")


def _resolve_installer_source(url: str) -> str:
    url = url.strip()
    if url.startswith(("http://", "https://", "\\\\")):
        return url
    return str(Path(url).resolve())


def parse_manifest(data: dict[str, Any]) -> UpdateManifest:
    return UpdateManifest(
        version=str(data.get("version") or "").strip(),
        release_notes=str(data.get("release_notes") or "").strip(),
        mandatory=bool(data.get("mandatory")),
        installer_url=str(data.get("installer_url") or data.get("download_url") or "").strip(),
        installer_sha256=str(data.get("installer_sha256") or data.get("sha256") or "").strip().lower(),
        release_date=str(data.get("release_date") or "").strip(),
        update_kind=str(data.get("update_kind") or "").strip().lower(),
    )


def _infer_update_kind(manifest: UpdateManifest | None, installer_path: Path) -> str:
    if manifest and manifest.update_kind in ("portable_exe", "inno"):
        return manifest.update_kind
    name = installer_path.name.lower()
    if name == "coss_payroll.exe":
        return "portable_exe"
    if "setup" in name or name.endswith(".msi"):
        return "inno"
    return "portable_exe"


def check_for_update() -> UpdateCheckResult:
    current = APP_VERSION
    url = resolve_manifest_url()
    if not url:
        return UpdateCheckResult(current_version=current, error="manifest_url 미설정")

    try:
        raw = _load_manifest_text(url)
        manifest = parse_manifest(json.loads(raw))
        if not manifest.version:
            return UpdateCheckResult(current_version=current, error="manifest version 없음")
        if parse_version(manifest.version) <= parse_version(current):
            return UpdateCheckResult(current_version=current)
        if not manifest.installer_url:
            return UpdateCheckResult(current_version=current, error="installer_url 없음")
        return UpdateCheckResult(current_version=current, manifest=manifest)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        log.warning("업데이트 확인 실패: %s", exc)
        return UpdateCheckResult(current_version=current, error=str(exc))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_installer(source: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "COSS-Payroll-Updater"})
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        return

    src_path = Path(source)
    if not src_path.is_file():
        raise FileNotFoundError(f"설치 파일을 찾을 수 없습니다: {src_path}")
    import shutil

    shutil.copy2(src_path, dest)


def download_update(manifest: UpdateManifest) -> Path:
    source = _resolve_installer_source(manifest.installer_url)
    suffix = Path(source).suffix or ".exe"
    dest = Path(tempfile.gettempdir()) / "coss_payroll_update" / f"setup_{manifest.version}{suffix}"
    if dest.exists():
        dest.unlink()
    _download_installer(source, dest)
    if manifest.installer_sha256:
        digest = _sha256_file(dest)
        if digest.lower() != manifest.installer_sha256.lower():
            dest.unlink(missing_ok=True)
            raise ValueError("설치 파일 해시가 일치하지 않습니다.")
    return dest


def apply_portable_update(package_exe: Path, manifest: UpdateManifest | None = None) -> None:
    """ZIP/개발자 배포용 — 설치 폴더 EXE 교체 후 재실행 (데이터는 AppData 유지)."""
    from core.paths import app_data_dir, app_install_dir

    if not package_exe.is_file():
        raise FileNotFoundError(str(package_exe))

    install_dir = app_install_dir()
    target_exe = install_dir / "COSS_Payroll.exe"
    channel_tpl = package_exe.parent / "templates"
    data_tpl = app_data_dir() / "templates"

    bat = Path(tempfile.gettempdir()) / "bitween_apply_portable_update.bat"
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "timeout /t 2 /nobreak >nul",
        f'if not exist "{install_dir}" mkdir "{install_dir}"',
        f'copy /Y "{package_exe}" "{target_exe}" >nul',
    ]
    if channel_tpl.is_dir():
        lines.append(f'if not exist "{data_tpl}" mkdir "{data_tpl}"')
        lines.append(f'xcopy /E /I /Y "{channel_tpl}" "{data_tpl}\\" >nul')
    lines.extend(
        [
            f'start "" "{target_exe}"',
            "del \"%~f0\"",
        ]
    )
    bat.write_text("\r\n".join(lines), encoding="utf-8")

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", str(bat)], close_fds=True, creationflags=flags)
    log.info("portable 업데이트 적용 예약: %s → %s", package_exe, target_exe)
    os._exit(0)


def apply_update(
    installer_path: Path,
    silent: bool = True,
    manifest: UpdateManifest | None = None,
) -> None:
    """새 설치 파일 적용 후 현재 앱 종료."""
    if not installer_path.is_file():
        raise FileNotFoundError(str(installer_path))

    kind = _infer_update_kind(manifest, installer_path)
    if kind == "portable_exe":
        apply_portable_update(installer_path, manifest)
        return

    args = [str(installer_path)]
    if silent:
        args.extend(["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"])

    subprocess.Popen(args, close_fds=True)
    log.info("업데이트 설치 프로그램 실행: %s", installer_path)
    os._exit(0)


def format_update_message(result: UpdateCheckResult) -> str:
    if not result.manifest:
        return ""
    m = result.manifest
    lines = [
        f"새 버전 {m.version} 이(가) 있습니다. (현재 {result.current_version})",
        "",
    ]
    if m.release_date:
        lines.append(f"배포일: {m.release_date}")
        lines.append("")
    if m.release_notes:
        lines.append(m.release_notes)
        lines.append("")
    lines.append("「지금 업데이트」를 누르면 자동으로 설치됩니다.")
    if m.mandatory:
        lines.append("※ 필수 업데이트입니다.")
    return "\n".join(lines).strip()
