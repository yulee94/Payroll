"""
main.py - 급여 자동 산출 프로그램 (GUI)

도급비 청구서 업로드 → 급여대장·급여명세서·지급내역 생성
"""

from __future__ import annotations

import re
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk

from excel_writer import OUTPUT_DIR, TEMPLATES_DIR, write_all_outputs
from payroll_comparison import ensure_payroll_diff_dir, generate_payroll_comparison
from core.config import MONTHLY_REPORTS_DIR
from invoice_parser import attendance_name_warnings, extract_invoice_data
from logger_util import get_logger
from annual_leave_manager import (
    annual_leave_roster_warnings,
    count_auto_annual_leave_usage,
    default_leave_split_for_case,
    find_deficit_leave_usage_cases,
)
from roster_constants import norm_name_key
from deficit_leave_dialog import show_deficit_leave_decision_dialog
from leave_usage_ledger import (
    LEAVE_USAGE_LEDGER_DIR,
    ensure_leave_usage_ledger_dir,
    get_leave_usage_ledger_path,
    save_leave_usage_ledger_entries,
)
from payroll_builder import (
    ROSTER_FILENAME,
    build_payroll_records,
    compare_roster_invoice_personnel,
    format_personnel_mismatch_message,
    get_templates_roster_path,
    load_payment_master,
    load_payslip_master,
    load_employee_roster,
    resolve_roster_path,
    roster_hourly_apply_stats,
)
from services.archive_storage import save_period_invoice
from services.payroll_scope import PayrollScope, resolve_output_dir
from services.upload_undo import record_upload
from validator import PayrollValidationError, validate_invoice_rows

BASE_DIR = Path(__file__).resolve().parent
EMPLOYEES_DIR = BASE_DIR / "employees"


def show_personnel_mismatch_dialog(parent: tk.Misc, diff: dict) -> None:
    """
    인원 불일치 시 이름 목록을 보여 주는 전용 창.

    Windows 기본 messagebox는 한글·여러 줄 본문이 잘리는 경우가 있어
    Text 위젯으로 표시합니다.
    """
    if not diff.get("has_mismatch"):
        return

    body = format_personnel_mismatch_message(diff)

    win = tk.Toplevel(parent)
    win.title("명부·청구서 인원 불일치")
    win.transient(parent)
    win.grab_set()
    win.minsize(400, 260)

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame,
        text="아래 인원이 서로 맞지 않습니다.",
        font=("맑은 고딕", 10, "bold"),
    ).pack(anchor=tk.W, pady=(0, 8))

    text = tk.Text(frame, wrap=tk.WORD, font=("맑은 고딕", 10), height=14, width=46)
    scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    text.insert("1.0", body)
    text.configure(state=tk.DISABLED)

    btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
    btn_row.pack(fill=tk.X)
    ttk.Button(btn_row, text="확인", command=win.destroy, width=12).pack()

    win.update_idletasks()
    px = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
    win.geometry(f"+{max(px, 0)}+{max(py, 0)}")
    win.wait_window()


def _period_from_filename(path: Path) -> str | None:
    """파일명 '26년05월...' → '2026-05' 추출."""
    m = re.search(r"(\d{2})년(\d{1,2})월", path.stem)
    if m:
        year = 2000 + int(m.group(1))
        month = int(m.group(2))
        return f"{year}-{month:02d}"
    return None


def process_invoice(
    invoice_path: Path,
    scope: PayrollScope,
    interactive_parent: tk.Misc | None = None,
) -> dict:
    """
    청구서 1건 처리 → 3종 Excel 출력 (계열사/사업장/월별 폴더).
    """
    from core.file_save import stage_readable_copy

    log = get_logger()
    log.info("처리 시작: %s → %s", invoice_path.name, scope.breadcrumb())

    work_invoice = invoice_path
    try:
        work_invoice = stage_readable_copy(invoice_path)
    except OSError:
        log.warning("청구서 임시 복사 실패 — 원본 경로로 처리: %s", invoice_path)

    invoice_rows = extract_invoice_data(work_invoice)
    row_warnings = validate_invoice_rows(invoice_rows)
    for w in row_warnings:
        log.warning(w)
    for w in attendance_name_warnings(invoice_path, invoice_rows):
        row_warnings.append(w)
        log.warning(w)

    payment_master = load_payment_master(TEMPLATES_DIR / "지급내역양식.xlsx")
    payslip_master = load_payslip_master(TEMPLATES_DIR / "급여명세서양식.xlsx")

    period = scope.period
    roster_path, roster_source = resolve_roster_path(invoice_path, period=period)
    employee_roster: dict = {}
    roster_info: dict = {"path": None, "source": "", "stats": {}, "personnel_diff": {}}
    if roster_path is not None:
        employee_roster = load_employee_roster(roster_path, period_hint=period)
        roster_info["path"] = roster_path
        roster_info["source"] = roster_source
        try:
            from services.employee_roster_store import roster_updated_display

            roster_info["updated_at"] = roster_updated_display()
        except ImportError:
            roster_info["updated_at"] = ""
        log.info(
            "근로자 명부: %s (%s, 갱신 %s)",
            roster_path.name,
            roster_source,
            roster_info.get("updated_at") or "-",
        )
    else:
        row_warnings.append(
            "근로자 명부를 찾지 못했습니다. 연차·시급 반영이 되지 않을 수 있습니다."
        )

    personnel_diff = compare_roster_invoice_personnel(invoice_rows, employee_roster)
    roster_info["personnel_diff"] = personnel_diff
    if personnel_diff["has_mismatch"]:
        log.warning(
            "명부·청구서 인원 불일치: 청구서만 %s, 명부만 %s",
            personnel_diff["only_in_invoice"],
            personnel_diff["only_in_roster"],
        )

    leave_usage_decisions: dict[str, str] = {}
    if employee_roster:
        auto_leave_n = count_auto_annual_leave_usage(
            invoice_rows, employee_roster, period
        )
        if auto_leave_n:
            log.info("잔여연차 있음 → 연차 자동 처리: %d명", auto_leave_n)

        deficit_cases = find_deficit_leave_usage_cases(
            invoice_rows, employee_roster, period
        )
        if deficit_cases:
            if interactive_parent is not None:
                chosen = show_deficit_leave_decision_dialog(
                    interactive_parent, deficit_cases
                )
                if chosen is None:
                    raise PayrollValidationError(
                        "잔여연차 없음 상태의 연차 사용 처리가 취소되어 "
                        "급여 산출을 중단했습니다."
                    )
                leave_usage_decisions = chosen
            else:
                leave_usage_decisions = {
                    c["name_key"]: default_leave_split_for_case(c) for c in deficit_cases
                }
                log.info(
                    "잔여연차 부족 연차 사용 %d명 → 비대화형 기본 분할(잔여만큼 유급·초과 무급)",
                    len(deficit_cases),
                )

            case_by_key = {c["name_key"]: c for c in deficit_cases}
            for inv in invoice_rows:
                key = norm_name_key(inv.get("name"))
                if key in case_by_key:
                    inv["_leave_available_before"] = case_by_key[key].get("available")

    leave_ledger_entries: list = []
    monthly_leave_summaries: list = []
    records, allowance_warnings = build_payroll_records(
        invoice_rows,
        payment_master,
        payslip_master,
        employee_roster,
        leave_ledger_entries=leave_ledger_entries,
        monthly_leave_summaries=monthly_leave_summaries,
        payroll_period=period,
        leave_usage_decisions=leave_usage_decisions,
    )
    for w in allowance_warnings[:10]:
        row_warnings.append(w)
        log.warning(w)
    if len(allowance_warnings) > 10:
        row_warnings.append(f"※ 명부 수당 조정 외 {len(allowance_warnings) - 10}건")

    payroll_audit: dict = {}
    try:
        from core.payroll.invoice_audit import audit_invoice_payroll, format_audit_summary_text

        payroll_audit = audit_invoice_payroll(
            invoice_rows,
            records,
            workplace=scope.workplace,
        )
        audit_summary = format_audit_summary_text(payroll_audit)
        log.info("자동검열: %s", audit_summary.replace("\n", " "))
        if payroll_audit.get("warn_count", 0) > 0:
            row_warnings.append(
                f"자동검열: 확인 필요 {payroll_audit['warn_count']}명 "
                f"(정상 {payroll_audit.get('pass_count', 0)}명)"
            )
    except Exception as exc:
        log.warning("자동검열 실패: %s", exc)

    leave_saved_count = 0
    leave_ledger_info: dict = {}
    try:
        ensure_leave_usage_ledger_dir()
        leave_ledger_info = save_leave_usage_ledger_entries(
            leave_ledger_entries,
            period,
            roster_path_for_migration=roster_path,
            monthly_summaries=monthly_leave_summaries,
        )
        leave_saved_count = int(leave_ledger_info.get("written") or 0)
        monthly_saved_count = int(leave_ledger_info.get("monthly_written") or 0)
        roster_info["leave_saved"] = leave_saved_count > 0 or monthly_saved_count > 0
        roster_info["leave_ledger_path"] = leave_ledger_info.get("path")
        roster_info["leave_ledger_purged"] = leave_ledger_info.get("purged", 0)
        roster_info["leave_ledger_migrated"] = leave_ledger_info.get("migrated", 0)
        log.info(
            "연차사용대장 갱신: 상세 %d건 · 월별현황 %d건 → %s (5년 초과 삭제 %d건)",
            leave_saved_count,
            monthly_saved_count,
            get_leave_usage_ledger_path().name,
            leave_ledger_info.get("purged", 0),
        )
        if leave_ledger_info.get("migrated"):
            log.info(
                "명부 연차대장 시트에서 %d건 이관",
                leave_ledger_info["migrated"],
            )
    except OSError as exc:
        row_warnings.append("연차사용대장 저장에 실패했습니다. 파일이 열려 있는지 확인해 주세요.")
        log.error("연차사용대장 저장 실패: %s", exc)

    try:
        from services.monthly_leave_manager import export_scope_leave_workbook

        leave_export = export_scope_leave_workbook(scope, period, records)
        log.info("연차·결근 현황 저장: %s", leave_export.name)
    except OSError as exc:
        row_warnings.append("당월 연차·결근 현황 Excel 저장에 실패했습니다.")
        log.warning("연차결근 현황 Excel 저장 실패: %s", exc)

    for w in annual_leave_roster_warnings(invoice_rows, employee_roster):
        row_warnings.append(w)
        log.warning(w)

    if employee_roster:
        try:
            from core.payroll.employment_insurance_65 import collect_ei_65_payroll_warnings

            for w in collect_ei_65_payroll_warnings(
                invoice_rows,
                employee_roster,
                payroll_period=period,
            ):
                if w not in row_warnings:
                    row_warnings.append(w)
                    log.warning(w)
        except Exception as exc:
            log.warning("만65 고용보험 확인 경고 생성 실패: %s", exc)

    if employee_roster:
        stats = roster_hourly_apply_stats(invoice_rows, employee_roster, records)
        roster_info["stats"] = stats
        log.info(
            "명부 시급 반영: %d/%d명 (명부 매칭 %d명)",
            stats["hourly_applied"],
            stats["total"],
            stats["matched"],
        )
        if stats["hourly_in_roster"] > 0 and stats["hourly_applied"] < stats["hourly_in_roster"]:
            row_warnings.append(
                f"명부 시급이 일부만 반영되었습니다 ({stats['hourly_applied']}/{stats['hourly_in_roster']}명). "
                "성명이 청구서와 명부에서 동일한지 확인하세요."
            )
    elif roster_path is None:
        pass
    elif not employee_roster:
        row_warnings.append("명부 파일을 읽었으나 등록된 직원이 없습니다.")

    out_dir = scope.output_dir()
    paths = write_all_outputs(records, TEMPLATES_DIR, out_dir, period)

    try:
        from services.payroll_output_refresh import stamp_manifest_engine_version

        stamp_manifest_engine_version(scope)
    except Exception:
        pass

    created: list[Path] = [paths["ledger"], paths["payslip"], paths["payment"]]
    created.extend(paths.get("ledger_extra") or [])

    try:
        save_src = work_invoice if work_invoice.is_file() else invoice_path
        invoice_saved = save_period_invoice(
            save_src,
            scope,
            records,
            original_name=invoice_path.name,
        )
        paths["invoice"] = invoice_saved
        created.append(invoice_saved)
        log.info("청구서 원본 저장: %s", invoice_saved.name)
    except OSError as exc:
        row_warnings.append("청구서 원본 저장에 실패했습니다.")
        log.error("청구서 원본 저장 실패: %s", exc)

    comparison_info: dict = {}
    try:
        comparison_info = generate_payroll_comparison(records, scope)
        paths["comparison"] = comparison_info["path"]
        created.append(comparison_info["path"])
        if comparison_info.get("snapshot_xlsx"):
            created.append(comparison_info["snapshot_xlsx"])
        if comparison_info.get("snapshot_csv"):
            created.append(comparison_info["snapshot_csv"])
        snap_path = out_dir / "payroll_snapshot.json"
        if snap_path.is_file():
            created.append(snap_path)
        log.info("급여차이 보고: %s", comparison_info["path"].name)
        if comparison_info.get("warning"):
            row_warnings.append(comparison_info["warning"])
            log.warning(comparison_info["warning"])
    except OSError as exc:
        row_warnings.append("급여차이 보고서 생성에 실패했습니다.")
        log.error("급여차이 보고서 생성 실패: %s", exc)

    log.info("처리 완료: %d명 → %s", len(records), out_dir)
    record_upload(scope, created, invoice_path.name)
    return {
        "records": records,
        "paths": paths,
        "count": len(records),
        "warnings": row_warnings,
        "roster": roster_info,
        "roster_leave_update_count": leave_saved_count,
        "leave_ledger": leave_ledger_info,
        "comparison": comparison_info,
        "scope": scope,
        "payroll_audit": payroll_audit,
    }


def main() -> None:
    # UI 문자열은 저장된 locale 기준으로 로딩합니다.
    from core.bootstrap_accounts import ensure_bootstrap_user_data
    from core.i18n import init_i18n
    from core.paths import initialize_runtime_paths

    initialize_runtime_paths()
    ensure_bootstrap_user_data()
    from core.bootstrap_org import ensure_coss_org_bootstrap

    ensure_coss_org_bootstrap()
    from core.bootstrap_group import ensure_coss_group

    ensure_coss_group()
    init_i18n()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EMPLOYEES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_leave_usage_ledger_dir()
    ensure_payroll_diff_dir()
    MONTHLY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    required = [
        TEMPLATES_DIR / "급여대장양식.xlsx",
        TEMPLATES_DIR / "급여명세서양식.xlsx",
        TEMPLATES_DIR / "지급내역양식.xlsx",
        TEMPLATES_DIR / ROSTER_FILENAME,
    ]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        messagebox.showwarning(
            "양식 없음",
            "프로그램 실행에 필요한 Excel 양식이 없습니다.\n"
            "설치 폴더의 templates 안에 급여·지급·명부 양식을 넣어 주세요.",
        )

    from app_ui import run_dashboard

    run_dashboard()


if __name__ == "__main__":
    main()
