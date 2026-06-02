"""
scripts/publish_release.py - EXE 빌드 + version.json 생성 (IT 배포용)

사용:
  python scripts/publish_release.py
  python scripts/publish_release.py --manifest-base "\\\\fileserver\\coss\\payroll"

결과:
  dist/COSS_Payroll.exe
  release/COSS_Payroll_Setup_{version}.exe  (Inno Setup 설치 시)
  release/version.json                      (직원 PC 자동 업데이트용)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_app_version() -> str:
    text = (ROOT / "core" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("core/config.py 에 APP_VERSION 이 없습니다.")
    return m.group(1)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_exe() -> Path:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "payroll.spec"],
        cwd=ROOT,
        check=True,
    )
    exe = ROOT / "dist" / "COSS_Payroll.exe"
    if not exe.is_file():
        raise SystemExit("빌드 실패: dist/COSS_Payroll.exe 없음")
    return exe


def write_manifest(version: str, installer_path: Path, manifest_path: Path, base_url: str) -> None:
    if base_url:
        base = base_url.rstrip("\\/")
        installer_url = f"{base}/COSS_Payroll_Setup_{version}.exe"
        update_kind = "inno"
    else:
        installer_url = str(installer_path.resolve())
        update_kind = "inno" if "setup" in installer_path.name.lower() else "portable_exe"

    payload = {
        "version": version,
        "release_date": date.today().isoformat(),
        "release_notes": "COSS Group 급여·인사 업데이트",
        "mandatory": False,
        "update_kind": update_kind,
        "installer_url": installer_url,
        "installer_sha256": _sha256(installer_path),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest → {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="COSS Payroll 릴리스 빌드")
    parser.add_argument(
        "--manifest-base",
        default="",
        help="version.json 의 installer_url 기준 (UNC 또는 https URL)",
    )
    parser.add_argument("--skip-pyinstaller", action="store_true")
    args = parser.parse_args()

    version = _read_app_version()
    print(f"버전: {version}")

    if not args.skip_pyinstaller:
        exe = build_exe()
        print(f"EXE → {exe}")

    release_dir = ROOT / "release"
    setup = release_dir / f"COSS_Payroll_Setup_{version}.exe"
    portable = ROOT / "dist" / "COSS_Payroll.exe"

    if setup.is_file():
        write_manifest(version, setup, release_dir / "version.json", args.manifest_base)
        print("완료 — release/version.json 을 공유폴더에 복사하면 자동 업데이트가 동작합니다.")
        return

    if portable.is_file():
        from scripts.update_publish import publish_update_channel

        channel = release_dir / "update_channel"
        publish_update_channel(portable, version, channel)
        print(
            "※ Inno Setup 설치 파일이 없어 portable 채널로 manifest 를 생성했습니다.\n"
            f"  {channel / 'version.json'}\n"
            "  또는: python scripts/build_developer_zip.py"
        )
        return

    print(
        "※ 설치 파일·EXE 가 없습니다.\n"
        '  PyInstaller 빌드 후 다시 실행하거나 build_developer_zip.py 를 사용하세요.\n'
        f"  예상 Setup: {setup}"
    )


if __name__ == "__main__":
    main()
