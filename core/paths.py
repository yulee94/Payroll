"""
core/paths.py - 실행 환경별 경로 (개발 · PyInstaller · 설치본)
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_REQUIRED_TEMPLATES = (
    "급여대장양식.xlsx",
    "급여명세서양식.xlsx",
    "지급내역양식.xlsx",
)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def dev_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path | None:
    """PyInstaller onefile 추출 폴더 (내장 리소스·계정 샘플)."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return None


def app_install_dir() -> Path:
    """프로그램 설치/실행 폴더 (템플릿·리소스)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return dev_root()


def app_data_dir() -> Path:
    """
    사용자 데이터 폴더 (output, employees, 로그 등).
    설치본은 LocalAppData에 두어 Program Files 쓰기 제한·업데이트 시 데이터 보존.
    """
    if is_frozen():
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "Bitween" / "Payroll"
    return dev_root()


def _template_source_dirs() -> list[Path]:
    roots: list[Path] = []
    bundled = bundle_dir()
    if bundled is not None:
        roots.append(bundled)
    if is_frozen():
        roots.append(app_install_dir())
    roots.append(dev_root())
    return roots


def _has_payroll_templates(folder: Path) -> bool:
    return folder.is_dir() and all((folder / name).is_file() for name in _REQUIRED_TEMPLATES)


def seed_templates_directory(dest: Path | None = None) -> Path:
    """설치본: AppData/templates 에 양식·명부 시드 (쓰기 가능)."""
    target = dest or (app_data_dir() / "templates")
    if _has_payroll_templates(target):
        return target
    target.mkdir(parents=True, exist_ok=True)
    for root in _template_source_dirs():
        src = root / "templates"
        if not _has_payroll_templates(src):
            continue
        for item in src.iterdir():
            dest_item = target / item.name
            if item.is_dir():
                if dest_item.exists():
                    shutil.copytree(item, dest_item, dirs_exist_ok=True)
                else:
                    shutil.copytree(item, dest_item)
            elif item.is_file() and not item.name.startswith("~$"):
                shutil.copy2(item, dest_item)
        break
    return target


def templates_dir() -> Path:
    """급여 양식·근로자명부 경로 (설치본은 AppData, 개발은 프로젝트)."""
    if is_frozen():
        return seed_templates_directory()
    return dev_root() / "templates"


def output_dir() -> Path:
    if is_frozen():
        return app_data_dir() / "output"
    return dev_root() / "output"


def employees_dir() -> Path:
    if is_frozen():
        return app_data_dir() / "employees"
    return dev_root() / "employees"


def payroll_diff_dir() -> Path:
    if is_frozen():
        return app_data_dir() / "급여차이내역"
    return dev_root() / "급여차이내역"


def leave_usage_ledger_dir() -> Path:
    if is_frozen():
        return app_data_dir() / "연차사용대장"
    return dev_root() / "연차사용대장"


def monthly_reports_dir() -> Path:
    if is_frozen():
        return app_data_dir() / "월별보고"
    return dev_root() / "월별보고"


def _copy_tree_if_empty(src: Path, dest: Path) -> bool:
    if not src.is_dir() or not any(src.iterdir()):
        return False
    if dest.exists() and any(dest.iterdir()):
        return False
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    return True


def migrate_legacy_data_paths() -> None:
    """설치 폴더·이전 잘못된 경로에 있던 output 등을 AppData로 이전."""
    if not is_frozen():
        return
    data = app_data_dir()
    pairs = (
        ("output", output_dir()),
        ("employees", employees_dir()),
        ("월별보고", monthly_reports_dir()),
        ("급여차이내역", payroll_diff_dir()),
        ("연차사용대장", leave_usage_ledger_dir()),
        ("templates", data / "templates"),
    )
    sources: list[Path] = [app_install_dir()]
    bundled = bundle_dir()
    if bundled is not None and bundled != sources[0]:
        sources.append(bundled)
    for folder_name, dest in pairs:
        for src_root in sources:
            src = src_root / folder_name
            if _copy_tree_if_empty(src, dest):
                break
        if folder_name == "templates" and not _has_payroll_templates(dest):
            seed_templates_directory(dest)


def ensure_app_data_dirs() -> Path:
    data = app_data_dir()
    for name in (
        "output",
        "employees",
        "월별보고",
        "급여차이내역",
        "연차사용대장",
        "templates",
        "output/logs",
        "maintenance",
        "bidding",
        "accounting",
        "users",
        "workspace",
        "workflow",
        "compliance_docs",
    ):
        (data / name).mkdir(parents=True, exist_ok=True)
    if is_frozen():
        seed_templates_directory(data / "templates")
        migrate_legacy_data_paths()
    return data


def initialize_runtime_paths() -> None:
    """모듈 상수(excel_writer 등)를 현재 실행 환경 경로로 맞춥니다."""
    ensure_app_data_dirs()
    out = output_dir()
    tpl = templates_dir()
    emp = employees_dir()
    diff = payroll_diff_dir()
    leave = leave_usage_ledger_dir()
    monthly = monthly_reports_dir()

    import excel_writer as ew

    ew.OUTPUT_DIR = out
    ew.TEMPLATES_DIR = tpl
    ew.BASE_DIR = tpl.parent

    import payroll_builder as pb

    pb.TEMPLATES_DIR = tpl
    pb.BASE_DIR = tpl.parent
    pb.EMPLOYEES_DIR = emp

    import payroll_comparison as pc

    pc.PAYROLL_DIFF_DIR = diff
    pc.BASE_DIR = diff.parent

    import leave_usage_ledger as lul

    lul.LEAVE_USAGE_LEDGER_DIR = leave
    lul.BASE_DIR = leave.parent

    import core.config as cfg

    cfg.MONTHLY_REPORTS_DIR = monthly

    import main as main_mod

    main_mod.EMPLOYEES_DIR = emp
