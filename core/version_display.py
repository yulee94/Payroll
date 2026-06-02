"""앱에 표시·로그할 버전 정보 (빌드 메타 + EXE 경로)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from core.config import APP_VERSION
from core.paths import app_install_dir, dev_root, is_frozen
from logger_util import get_logger


def _build_info_path() -> Path | None:
    if is_frozen():
        p = app_install_dir() / "config" / "build_info.json"
        return p if p.is_file() else None
    p = dev_root() / "config" / "build_info.json"
    return p if p.is_file() else None


def load_build_info() -> dict[str, str]:
    path = _build_info_path()
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v is not None}
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


def app_version_label(*, include_build_date: bool = True) -> str:
    info = load_build_info()
    ver = (info.get("version") or APP_VERSION).strip() or APP_VERSION
    label = f"v{ver.lstrip('vV')}"
    if include_build_date:
        bd = (info.get("build_date") or "").strip()
        if bd:
            return f"{label} · {bd}"
    return label


def runtime_executable() -> Path | None:
    if is_frozen():
        return Path(sys.executable).resolve()
    return None


def log_startup_version() -> None:
    log = get_logger()
    exe = runtime_executable()
    parts = [f"Bitween Payroll {app_version_label()}"]
    if exe is not None:
        try:
            mtime = datetime.fromtimestamp(exe.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            parts.append(f"exe={exe}")
            parts.append(f"built={mtime}")
        except OSError:
            parts.append(f"exe={exe}")
    elif not is_frozen():
        parts.append("mode=python-source")
        parts.append(f"root={dev_root()}")
    log.info(" | ".join(parts))
