"""
scripts/build_developer_zip.py - 개발자 전달용 EXE + 설치 스크립트 ZIP (바탕화면)

사용:
  python scripts/build_developer_zip.py
  python scripts/build_developer_zip.py --desktop "D:\\Users\\MY\\Desktop"
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_version() -> str:
    text = (ROOT / "core" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "1.0.0"


def _source_mtime_max() -> float:
    """주요 소스 최신 수정 시각 (EXE가 이보다 오래되면 재빌드 필요)."""
    candidates = [
        ROOT / "core" / "config.py",
        ROOT / "app_ui.py",
        ROOT / "main.py",
    ]
    candidates.extend((ROOT / "core").glob("*.py"))
    mtimes = [p.stat().st_mtime for p in candidates if p.is_file()]
    return max(mtimes) if mtimes else 0.0


def _write_build_info(dest_config_dir: Path, *, version: str, exe: Path) -> None:
    from scripts.update_publish import sha256_file

    dest_config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "build_date": date.today().isoformat(),
        "exe_sha256": sha256_file(exe)[:16],
    }
    (dest_config_dir / "build_info.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            check=True,
        )


def _clean_excel_lock_files(root: Path) -> None:
    for p in root.rglob("~$*"):
        try:
            p.unlink()
        except OSError:
            pass


def build_exe() -> Path:
    _clean_excel_lock_files(ROOT / "templates")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "payroll.spec"],
        cwd=ROOT,
        check=True,
    )
    exe = ROOT / "dist" / "COSS_Payroll.exe"
    if not exe.is_file():
        raise SystemExit("빌드 실패: dist/COSS_Payroll.exe 가 없습니다.")
    return exe


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.is_dir():
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "~$*"),
    )


def _write_install_bat(dest: Path) -> None:
    bat = r"""@echo off
chcp 65001 >nul
setlocal EnableExtensions
set "SRC=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\BitweenPayroll"
set "EXE_NAME=COSS_Payroll.exe"
set "SHORTCUT_NAME=Bitween Payroll.lnk"
set "VBS=%TEMP%\bitween_create_shortcut.vbs"

echo.
echo  ========================================
echo   Bitween 급여·인사 — PC 설치
echo  ========================================
echo.
echo  설치 위치: %INSTALL_DIR%
echo.

if not exist "%SRC%%EXE_NAME%" (
  echo [오류] COSS_Payroll.exe 를 찾을 수 없습니다.
  echo          ZIP을 풀은 폴더에서 이 파일을 실행하세요.
  pause
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo  파일 복사 중...
copy /Y "%SRC%%EXE_NAME%" "%INSTALL_DIR%\%EXE_NAME%" >nul
if exist "%SRC%templates" xcopy /E /I /Y "%SRC%templates" "%INSTALL_DIR%\templates\" >nul
if exist "%SRC%assets" xcopy /E /I /Y "%SRC%assets" "%INSTALL_DIR%\assets\" >nul
if exist "%SRC%config" xcopy /E /I /Y "%SRC%config" "%INSTALL_DIR%\config\" >nul
if exist "%SRC%locales" xcopy /E /I /Y "%SRC%locales" "%INSTALL_DIR%\locales\" >nul
if exist "%SRC%employees" xcopy /E /I /Y "%SRC%employees" "%INSTALL_DIR%\employees\" >nul
if exist "%SRC%users" xcopy /E /I /Y "%SRC%users" "%INSTALL_DIR%\users\" >nul
if exist "%SRC%tenants.json" copy /Y "%SRC%tenants.json" "%INSTALL_DIR%\" >nul
if exist "%SRC%.env.example" copy /Y "%SRC%.env.example" "%INSTALL_DIR%\.env.example" >nul

set "DATA_DIR=%LOCALAPPDATA%\Bitween\Payroll"
if not exist "%DATA_DIR%\users" mkdir "%DATA_DIR%\users"
if exist "%SRC%users\registry.json" (
  copy /Y "%SRC%users\registry.json" "%DATA_DIR%\users\" >nul
  echo  로그인 계정 AppData 복사됨
)
if exist "%SRC%tenants.json" (
  copy /Y "%SRC%tenants.json" "%DATA_DIR%\" >nul
)
if exist "%SRC%config\update_channel.json" (
  copy /Y "%SRC%config\update_channel.json" "%DATA_DIR%\" >nul
)

echo  바탕화면 바로가기 생성...
del "%VBS%" 2>nul
(
  echo Set oWS = CreateObject^("WScript.Shell"^)
  echo sDesktop = oWS.SpecialFolders^("Desktop"^)
  echo sLink = sDesktop ^& "\%SHORTCUT_NAME%"
  echo Set oLnk = oWS.CreateShortcut^(sLink^)
  echo oLnk.TargetPath = "%INSTALL_DIR%\%EXE_NAME%"
  echo oLnk.WorkingDirectory = "%INSTALL_DIR%"
  echo oLnk.Description = "Bitween Payroll"
  echo oLnk.Save
  echo WScript.Echo sLink
) > "%VBS%"

set "DESKTOP_LNK="
for /f "delims=" %%i in ('cscript //nologo "%VBS%" 2^>^&1') do set "DESKTOP_LNK=%%i"
del "%VBS%" 2>nul

if not defined DESKTOP_LNK (
  echo  [경고] 바탕화면 바로가기를 만들지 못했습니다.
  echo         「바탕화면_바로가기_만들기.bat」를 실행해 보세요.
  goto :startmenu
)

if not exist "%DESKTOP_LNK%" (
  echo  [경고] 바로가기 파일 확인 실패: %DESKTOP_LNK%
  goto :startmenu
)
echo  바탕화면: %DESKTOP_LNK%

:startmenu
echo  시작 메뉴 바로가기 생성...
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%SM%" mkdir "%SM%" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell;$s=$ws.CreateShortcut('%SM%\%SHORTCUT_NAME%');$s.TargetPath='%INSTALL_DIR%\%EXE_NAME%';$s.WorkingDirectory='%INSTALL_DIR%';$s.Save()" 2>nul

echo.
echo  [완료] 설치되었습니다.
if defined DESKTOP_LNK if exist "%DESKTOP_LNK%" (
  echo  바탕화면 「%SHORTCUT_NAME%」 아이콘으로 실행하세요.
) else (
  echo  시작 메뉴 또는 %INSTALL_DIR%\%EXE_NAME% 로 실행하세요.
)
echo.
pause
endlocal
"""
    (dest / "설치.bat").write_text(bat, encoding="utf-8-sig")

    fix_bat = r"""@echo off
chcp 65001 >nul
setlocal
set "INSTALL_DIR=%LOCALAPPDATA%\BitweenPayroll"
set "EXE_NAME=COSS_Payroll.exe"
set "SHORTCUT_NAME=Bitween Payroll.lnk"
set "VBS=%TEMP%\bitween_create_shortcut.vbs"

if not exist "%INSTALL_DIR%\%EXE_NAME%" (
  echo [오류] 먼저 설치.bat 으로 설치하거나 COSS_Payroll.exe 가 있는지 확인하세요.
  echo       경로: %INSTALL_DIR%
  pause
  exit /b 1
)

echo 바탕화면 바로가기 생성 중...
del "%VBS%" 2>nul
(
  echo Set oWS = CreateObject^("WScript.Shell"^)
  echo sDesktop = oWS.SpecialFolders^("Desktop"^)
  echo sLink = sDesktop ^& "\%SHORTCUT_NAME%"
  echo Set oLnk = oWS.CreateShortcut^(sLink^)
  echo oLnk.TargetPath = "%INSTALL_DIR%\%EXE_NAME%"
  echo oLnk.WorkingDirectory = "%INSTALL_DIR%"
  echo oLnk.Description = "Bitween Payroll"
  echo oLnk.Save
  echo WScript.Echo sLink
) > "%VBS%"

for /f "delims=" %%i in ('cscript //nologo "%VBS%" 2^>^&1') do set "DESKTOP_LNK=%%i"
del "%VBS%" 2>nul

if exist "%DESKTOP_LNK%" (
  echo [완료] 바로가기 생성됨:
  echo   %DESKTOP_LNK%
) else (
  echo [실패] 바로가기를 만들지 못했습니다.
  echo OneDrive 바탕화면 사용 시 탐색기에서 직접 확인해 주세요.
)
pause
endlocal
"""
    (dest / "바탕화면_바로가기_만들기.bat").write_text(fix_bat, encoding="utf-8-sig")


def _write_account_recovery_bat(dest: Path) -> None:
    bat = r"""@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0"
set "DATA_DIR=%LOCALAPPDATA%\Bitween\Payroll"

echo.
echo  Bitween 로그인 계정 복구
echo  대상: %DATA_DIR%
echo.

if not exist "%SRC%users\registry.json" (
  echo [오류] users\registry.json 이 이 폴더에 없습니다.
  pause
  exit /b 1
)

if not exist "%DATA_DIR%\users" mkdir "%DATA_DIR%\users"
copy /Y "%SRC%users\registry.json" "%DATA_DIR%\users\" >nul
if exist "%SRC%tenants.json" copy /Y "%SRC%tenants.json" "%DATA_DIR%\" >nul

echo  [완료] 계정·고객사 설정을 복사했습니다.
echo  프로그램을 다시 실행한 뒤 로그인하세요.
echo.
pause
endlocal
"""
    (dest / "계정_복구.bat").write_text(bat, encoding="utf-8-sig")


def _write_run_bat(dest: Path) -> None:
    bat = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "COSS_Payroll.exe" (
  echo COSS_Payroll.exe 를 찾을 수 없습니다.
  pause
  exit /b 1
)
start "" "%~dp0COSS_Payroll.exe"
"""
    (dest / "바로_실행.bat").write_text(bat, encoding="utf-8-sig")


def _write_readme(dest: Path, version: str) -> None:
    text = f"""Bitween 급여·인사 — 개발자 배포 패키지 (v{version})
빌드일: {date.today().isoformat()}

■ 포함 파일
  COSS_Payroll.exe     실행 파일
  templates/           Excel 양식 (급여대장·명세서·명부 등)
  assets/, config/, locales/
  users/registry.json  로그인 계정 (설치 시 AppData로 복사)
  tenants.json         고객사 설정
  설치.bat             PC 설치 + 바탕화면 바로가기 + 계정 복사
  계정_복구.bat        로그인 실패 시 AppData 계정 재복사
  바로_실행.bat        설치 없이 ZIP 폴더에서 바로 실행

■ 설치 방법 (권장 — 새 PC·동료 개발자)
  1. 실행 중인 Bitween/COSS Payroll 을 모두 종료합니다.
  2. ZIP 전체를 「새 폴더」에 압축 해제합니다. (기존 폴더 위에 덮어쓰지 마세요)
  3. 「설치.bat」을 더블클릭합니다.
  4. 완료 후 바탕화면 「Bitween Payroll」 아이콘으로 실행합니다.
     (OneDrive 바탕화면을 쓰는 경우에도 자동으로 연결됩니다.)

  바로가기가 없으면 「바탕화면_바로가기_만들기.bat」를 실행하세요.

  설치 경로: %LOCALAPPDATA%\\BitweenPayroll
  로그인 데이터: %LOCALAPPDATA%\\Bitween\\Payroll\\users

■ 이전 버전이 보일 때 (업그레이드)
  - 바탕화면/작업 표시줄 바로가기가 예전 COSS_Payroll.exe 를 가리키는 경우가 많습니다.
    바로가기 속성 → 대상 경로가 아래 설치 폴더인지 확인하세요.
  - 예전 ZIP 폴더의 COSS_Payroll.exe 를 직접 실행하지 마세요.
  - 그래도 같으면: 프로그램 종료 → %LOCALAPPDATA%\\BitweenPayroll 폴더 삭제
    → 새 ZIP 압축 해제 → 설치.bat 재실행.
  - 로그인 화면·사이드바 하단에 표시되는 버전·빌드일을 확인하세요.
  - output/logs/payroll_YYYYMMDD.log 첫 줄에 exe 경로·빌드 시각이 기록됩니다.

■ 로그인 (개발용 패키지)
  고객사: COSS Group (coss)
  아이디: admin
  비밀번호: 배포 담당자에게 확인 (설치.bat 실행 시 계정 파일이 복사됩니다)
  ※ 로그인이 안 되면 「계정_복구.bat」를 실행한 뒤 다시 시도하세요.

■ 설치 없이 테스트
  「바로_실행.bat」 또는 COSS_Payroll.exe 를 직접 실행합니다.

■ 사용자 데이터
  급여 산출 결과·로그인·워크스페이스는 다음에 저장됩니다.
  %LOCALAPPDATA%\\Bitween\\Payroll

■ 자동 업데이트 (개발자 PC)
  빌드 시 「Bitween_Payroll_Updates」 채널(또는 --update-channel UNC)에
  version.json + COSS_Payroll.exe 가 배포됩니다.
  설치된 프로그램은 실행 시 새 버전을 확인하고 「지금 업데이트」로 EXE를 교체합니다.
  팀 공유: python scripts/build_developer_zip.py --update-channel "\\\\서버\\공유\\BitweenPayroll"

■ 개발 환경에서 소스 실행 (선택)
  Python 3.10+ 권장
  pip install -r requirements.txt
  python main.py

■ OpenAI Personal AI (선택)
  .env.example 참고 — API 키는 프로그램 내 「API 설정」에서도 입력 가능합니다.

■ 문의
  COSS Group / Bitween 급여·인사 프로젝트 담당자에게 연락하세요.
"""
    (dest / "설치_안내.txt").write_text(text, encoding="utf-8")


def stage_package(exe: Path, version: str, *, manifest_url: str = "") -> Path:
    folder_name = f"Bitween_Payroll_개발자배포_v{version}"
    stage_root = ROOT / "release" / folder_name
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True)

    shutil.copy2(exe, stage_root / "COSS_Payroll.exe")
    for name in ("templates", "employees", "assets", "config", "locales"):
        _copy_tree(ROOT / name, stage_root / name)

    env_example = ROOT / ".env.example"
    if env_example.is_file():
        shutil.copy2(env_example, stage_root / ".env.example")

    tenants = ROOT / "tenants.json"
    if tenants.is_file():
        shutil.copy2(tenants, stage_root / "tenants.json")
    users_reg = ROOT / "users" / "registry.json"
    if users_reg.is_file():
        _copy_tree(ROOT / "users", stage_root / "users")

    _write_install_bat(stage_root)
    _write_account_recovery_bat(stage_root)
    _write_run_bat(stage_root)
    _write_readme(stage_root, version)

    _write_build_info(stage_root / "config", version=version, exe=exe)

    if manifest_url:
        sys.path.insert(0, str(ROOT))
        from scripts.update_publish import write_update_channel_config

        write_update_channel_config(stage_root / "config" / "update_channel.json", manifest_url)

    return stage_root


def zip_package(stage_root: Path, desktop: Path, version: str) -> Path:
    desktop.mkdir(parents=True, exist_ok=True)
    zip_path = desktop / f"{stage_root.name}.zip"
    if zip_path.is_file():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in stage_root.rglob("*"):
            if path.is_file():
                arc = path.relative_to(stage_root.parent)
                zf.write(path, arc.as_posix())

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="개발자 배포 ZIP 생성")
    parser.add_argument(
        "--desktop",
        default=str(Path.home() / "Desktop"),
        help="ZIP 저장 폴더 (기본: 바탕화면)",
    )
    parser.add_argument("--skip-build", action="store_true", help="기존 dist/COSS_Payroll.exe 사용")
    parser.add_argument(
        "--update-channel",
        default="",
        help="자동 업데이트 채널 폴더 (UNC·로컬). 기본: 바탕화면\\Bitween_Payroll_Updates",
    )
    parser.add_argument(
        "--no-update-publish",
        action="store_true",
        help="업데이트 채널(version.json) 배포 생략",
    )
    args = parser.parse_args()

    version = _read_version()
    print(f"버전: {version}")

    if not args.skip_build:
        print("PyInstaller 확인...")
        _ensure_pyinstaller()
        print("EXE 빌드 중 (수 분 소요)...")
        exe = build_exe()
    else:
        exe = ROOT / "dist" / "COSS_Payroll.exe"
        if not exe.is_file():
            raise SystemExit("dist/COSS_Payroll.exe 없음 — --skip-build 제거 후 다시 실행")
        src_mtime = _source_mtime_max()
        exe_mtime = exe.stat().st_mtime
        if src_mtime > exe_mtime + 1:
            raise SystemExit(
                "dist/COSS_Payroll.exe 가 소스보다 오래되었습니다.\n"
                "  APP_VERSION 만 올리고 --skip-build 로 ZIP 만든 경우 UI 버전만 바뀌고\n"
                "  실행 파일은 예전 빌드일 수 있습니다. --skip-build 없이 다시 실행하세요."
            )

    manifest_url = ""
    if not args.no_update_publish:
        sys.path.insert(0, str(ROOT))
        from scripts.update_publish import default_desktop_channel, publish_update_channel

        channel_dir = Path(args.update_channel) if args.update_channel else default_desktop_channel()
        notes = "급여 저장 경로·자동 업데이트·로그인 개선"
        manifest_path = publish_update_channel(
            exe,
            version,
            channel_dir,
            release_notes=notes,
        )
        manifest_url = str(manifest_path.resolve())
        print(f"업데이트 채널 → {channel_dir}")
        print(f"  manifest: {manifest_path}")

    print("배포 폴더 구성...")
    stage = stage_package(exe, version, manifest_url=manifest_url)
    print(f"  → {stage}")

    desktop = Path(args.desktop)
    print(f"ZIP 생성 → {desktop}")
    zip_path = zip_package(stage, desktop, version)
    print(f"\n완료: {zip_path}")
    print(f"용량: {zip_path.stat().st_size / (1024*1024):.1f} MB")
    if manifest_url:
        print("\n※ 개발자 PC: 프로그램 실행 시 새 버전이 있으면 업데이트 안내가 표시됩니다.")


if __name__ == "__main__":
    main()
