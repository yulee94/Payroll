#!/usr/bin/env python3
"""
베스텍 밀양공장 2026-01~04 급여 배치: 근태 xlsx + 명부·연차대장 + 참조 급여대장 검증.

사용:
  python tools/run_bestec_milyang_payroll.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.paths import initialize_runtime_paths

initialize_runtime_paths()

from excel_writer import TEMPLATES_DIR, write_all_outputs
from payroll_builder import (
    build_payroll_records,
    load_payment_master,
    load_payslip_master,
)
from services.attendance_event_import import (
    aggregate_attendance_month,
    attendance_to_invoice_overrides,
    column_mapping_doc,
)
from services.bestec_leave_import import apply_leave_days_to_invoices
from services.bestec_reference_ledger import (
    build_roster_from_reference,
    compare_records,
    load_reference_ledger,
    reference_to_invoice_row,
)
from services.bestec_upload_discovery import (
    apply_leave_days_to_invoices as apply_roster_leave_to_invoices,
    bestec_template_dir,
    expected_upload_doc,
    install_uploads,
    load_bestec_leave_for_period,
    load_bestec_roster,
    monthly_leave_days_from_roster,
    scan_uploads,
)
from services.payroll_scope import PayrollScope
from roster_constants import norm_name_key

AFFILIATE = "㈜베스텍"
WORKPLACE = "밀양공장"
TOLERANCE = 1

KAKAO_DIR = Path(r"c:\Users\MY\Documents\카카오톡 받은 파일")

ROSTER_SOURCE = KAKAO_DIR / "(주)베스텍 재직증명서(2026).xlsx"
LEAVE_SOURCE = next(KAKAO_DIR.glob("*연차관리*"), None)

ATTENDANCE_FILES = {
    "2026-01": Path(r"c:\Users\MY\Downloads\1월 근태.xlsx"),
    "2026-02": Path(r"c:\Users\MY\Downloads\2월 근태.xlsx"),
    "2026-03": Path(r"c:\Users\MY\Downloads\3월 근태.xlsx"),
    "2026-04": Path(r"c:\Users\MY\Downloads\4월 근태.xlsx"),
}

REFERENCE_FILES = {
    "2026-01": Path(r"c:\Users\MY\Downloads\(주)베스텍01월급여대장 (3).xls"),
    "2026-02": Path(r"c:\Users\MY\Downloads\(주)베스텍02월급여대장03.05최종저장.xls"),
    "2026-03": Path(r"c:\Users\MY\Downloads\(주)베스텍3월급여대장04.03최종저장. (4).xls"),
    "2026-04": Path(r"c:\Users\MY\Downloads\(주)베스텍4월급여대장05.06최종저장.xls"),
}

# 이전 검증(명부·연차 미반영) 기준치
PRIOR_GROSS_MATCH = {
    "2026-01": (19, 62, 30.6),
    "2026-02": (20, 60, 33.3),
    "2026-03": (19, 60, 31.7),
    "2026-04": (15, 58, 25.9),
}
PRIOR_NET_MATCH = {p: (0, PRIOR_GROSS_MATCH[p][1], 0.0) for p in PRIOR_GROSS_MATCH}


def _ensure_milyang_hours_policy() -> None:
    """밀양공장 월 209시간 고정 (참조 대장과 동일)."""
    from services.payroll_settings_store import save_workplace_hours_policy

    save_workplace_hours_policy(
        WORKPLACE, mode="fixed", hours=209, tenant_id="bestec"
    )


def _apply_leave_auto_processing(
    invoice_rows: list[dict],
    roster: dict,
    period: str,
) -> tuple[dict, int, int]:
    from annual_leave_manager import (
        count_auto_annual_leave_usage,
        default_leave_split_for_case,
        find_deficit_leave_usage_cases,
    )

    leave_usage_decisions: dict = {}
    auto_n = 0
    deficit_n = 0
    if not roster:
        return leave_usage_decisions, auto_n, deficit_n

    auto_n = count_auto_annual_leave_usage(invoice_rows, roster, period)
    deficit_cases = find_deficit_leave_usage_cases(invoice_rows, roster, period)
    if deficit_cases:
        deficit_n = len(deficit_cases)
        leave_usage_decisions = {
            c["name_key"]: default_leave_split_for_case(c) for c in deficit_cases
        }
        case_by_key = {c["name_key"]: c for c in deficit_cases}
        for inv in invoice_rows:
            key = norm_name_key(inv.get("name"))
            if key in case_by_key:
                inv["_leave_available_before"] = case_by_key[key].get("available")
    return leave_usage_decisions, auto_n, deficit_n


def process_month(period: str, upload_scan) -> dict:
    ref_path = REFERENCE_FILES[period]
    att_path = ATTENDANCE_FILES[period]
    reference = load_reference_ledger(ref_path, period)
    ref_roster = build_roster_from_reference(reference)

    roster, roster_source = load_bestec_roster(
        upload_scan,
        period,
        reference_fallback=ref_roster,
        reference=reference,
    )

    invoice_rows = [reference_to_invoice_row(emp) for emp in reference.values()]

    ref_hours = {
        k: (e.work_hours if e.work_hours > 0 else 209.0)
        for k, e in reference.items()
    }

    leave_by_key, leave_roster_n = load_bestec_leave_for_period(
        upload_scan, period, roster
    )

    leave_from_ledger = apply_leave_days_to_invoices(
        invoice_rows,
        leave_by_key,
        reference_hours=ref_hours,
        standard_hours=209.0,
    )

    sheet_leave = monthly_leave_days_from_roster(roster, period)
    leave_from_roster_sheet = apply_roster_leave_to_invoices(
        invoice_rows, sheet_leave
    )

    leave_decisions, auto_leave_n, deficit_leave_n = _apply_leave_auto_processing(
        invoice_rows, roster, period
    )

    att_summary = {}
    att_employees = 0
    if att_path.is_file():
        att_summary = aggregate_attendance_month(att_path, period=period)
        att_employees = len(att_summary)
        overrides = attendance_to_invoice_overrides(att_summary)
        for inv in invoice_rows:
            key = norm_name_key(inv["name"])
            if key in overrides:
                inv.update(overrides[key])

    payment_master = load_payment_master(TEMPLATES_DIR / "지급내역양식.xlsx")
    payslip_master = load_payslip_master(TEMPLATES_DIR / "급여명세서양식.xlsx")
    records, warnings = build_payroll_records(
        invoice_rows,
        payment_master,
        payslip_master,
        roster,
        payroll_period=period,
        leave_usage_decisions=leave_decisions or None,
    )

    scope = PayrollScope(AFFILIATE, WORKPLACE, period)
    out_dir = scope.output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_all_outputs(records, TEMPLATES_DIR, out_dir, period_label=period)

    comp = compare_records(records, reference, tolerance=TOLERANCE)

    from utils import safe_number as _sn

    gross_matches = 0
    net_matches = 0
    active_ref = 0
    gen_by = {norm_name_key(r["name"]): r for r in records}
    for key, ref_emp in reference.items():
        if ref_emp.gross <= 0:
            continue
        active_ref += 1
        gen = gen_by.get(key)
        if not gen:
            continue
        if abs(_sn(gen.get("gross_pay")) - ref_emp.gross) <= TOLERANCE:
            gross_matches += 1
        if abs(_sn(gen.get("net_pay")) - ref_emp.net) <= TOLERANCE:
            net_matches += 1

    return {
        "period": period,
        "output_dir": str(out_dir),
        "roster_source": roster_source,
        "roster_count": len({k for k in roster if not str(k).isdigit()}),
        "leave_roster_applied": leave_roster_n,
        "leave_days_from_ledger": leave_from_ledger,
        "leave_days_from_roster_sheet": leave_from_roster_sheet,
        "auto_leave_processed": auto_leave_n,
        "deficit_leave_cases": deficit_leave_n,
        "reference_count": comp["reference_count"],
        "generated_count": comp["generated_count"],
        "attendance_employees": att_employees,
        "match_rate": comp["match_rate"],
        "reference_active_count": active_ref,
        "gross_match_count": gross_matches,
        "gross_match_rate": round(100.0 * gross_matches / active_ref, 1) if active_ref else 0.0,
        "net_match_count": net_matches,
        "net_match_rate": round(100.0 * net_matches / active_ref, 1) if active_ref else 0.0,
        "mismatches": comp["mismatches"],
        "only_in_reference": comp["only_in_reference"],
        "only_in_generated": comp["only_in_generated"],
        "warnings": warnings,
    }


def write_korean_report(
    results: list[dict],
    report_path: Path,
    upload_scan,
) -> None:
    lines = [
        "# 베스텍 밀양공장 급여 검증 보고서",
        "",
        f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 업로드 파일 (명부·연차)",
        "",
    ]

    lines.append("### 사용한 원본 파일")
    lines.append(f"- **명부(재직증명서)**: `{ROSTER_SOURCE}`")
    if LEAVE_SOURCE:
        lines.append(f"- **연차관리대장**: `{LEAVE_SOURCE}`")
    else:
        lines.append("- **연차관리대장**: 파일을 찾지 못했습니다.")
    for period, att in ATTENDANCE_FILES.items():
        lines.append(f"- **근태 {period}**: `{att}`")
    for period, ref in REFERENCE_FILES.items():
        lines.append(f"- **참조 급여대장 {period}**: `{ref}`")

    lines.append("")
    if upload_scan.installed:
        lines.append("### templates/bestec/ 설치 파일")
        for p in upload_scan.installed:
            lines.append(f"- `{p}`")
    if upload_scan.notes:
        for n in upload_scan.notes:
            lines.append(f"- {n}")
    lines.extend(["", expected_upload_doc(), ""])

    lines.extend(
        [
            "## 근태 파일 열 매핑",
            "",
            column_mapping_doc(),
            "",
            "## 월별 요약 (명부·연차 반영 후)",
            "",
            "| 급여월 | 명부 출처 | 명부 인원 | 연차(통합→청구) | 자동연차 | 무급분할 | 참조(지급>0) | 근태 인원 | 총지급 일치 | 실수령 일치 |",
            "|--------|----------|----------|----------------|---------|---------|-------------|----------|------------|------------|",
        ]
    )

    for r in results:
        lines.append(
            f"| {r['period']} | {r['roster_source'][:40]} | {r['roster_count']} | "
            f"{r['leave_days_from_ledger']}명 | {r['auto_leave_processed']} | "
            f"{r['deficit_leave_cases']} | {r.get('reference_active_count', r['reference_count'])} | "
            f"{r['attendance_employees']} | "
            f"{r['gross_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('gross_match_rate', 0)}%) | "
            f"{r['net_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('net_match_rate', 0)}%) |"
        )

    lines.extend(
        [
            "",
            "## 이전 대비 (명부·연차 반영 전 → 후)",
            "",
            "| 급여월 | 총지급 일치 (전) | 총지급 일치 (후) | 실수령 (전) | 실수령 (후) |",
            "|--------|-----------------|-----------------|------------|------------|",
        ]
    )
    for r in results:
        p = r["period"]
        pg = PRIOR_GROSS_MATCH.get(p, (0, 0, 0))
        pn = PRIOR_NET_MATCH.get(p, (0, 0, 0))
        lines.append(
            f"| {p} | {pg[0]}/{pg[1]} ({pg[2]}%) | "
            f"{r['gross_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('gross_match_rate', 0)}%) | "
            f"{pn[0]}/{pn[1]} ({pn[2]}%) | "
            f"{r['net_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('net_match_rate', 0)}%) |"
        )

    lines.extend(
        [
            "",
            "## 적용한 처리",
            "",
            "- **명부**: `(주)베스텍 재직증명서(2026).xlsx` 근로자명부(입사일·부서·직책) + 참조 급여대장(시급·소득세·4대보험).",
            "- **연차**: `○ 연차관리(호민)_'23.xlsx` 통합 시트 당월 '사용' 열 → `leave_days` (1월·4월 각 1명).",
            "- **근태**: 카드 출퇴근 xlsx → `_attendance_*` 메타 기록.",
            f"- **{WORKPLACE}** 월 기본근로 209h 고정.",
            "- 참조 대장: seq행(소득세·건강·국민) + detail행(지방·장기·고용) 명부 고정액 반영.",
            "",
            "## 월별 불일치 (1원 초과)",
            "",
        ]
    )

    for r in results:
        lines.append(f"### {r['period']}")
        if r["only_in_reference"]:
            lines.append(
                f"- 참조에만 있음 ({len(r['only_in_reference'])}명): "
                + ", ".join(r["only_in_reference"][:15])
                + (" …" if len(r["only_in_reference"]) > 15 else "")
            )
        if r["only_in_generated"]:
            lines.append(
                f"- 산출에만 있음 ({len(r['only_in_generated'])}명): "
                + ", ".join(r["only_in_generated"][:15])
            )
        by_cat: dict[str, list] = {}
        for m in r["mismatches"]:
            by_cat.setdefault(m["category"], []).append(m)
        for cat, items in sorted(by_cat.items()):
            lines.append(f"- **{cat}** 불일치 {len(items)}건 (상위 10건):")
            for m in items[:10]:
                lines.append(
                    f"  - {m['name']} {m['field']}: 참조 {m['reference']:,.0f} / "
                    f"산출 {m['generated']:,.0f} (차이 {m['delta']:+,.0f})"
                )
        if r["attendance_employees"] < r["reference_count"] * 0.5:
            lines.append(
                f"- ⚠ 근태 파일 직원 수({r['attendance_employees']})가 참조 대비 현저히 적습니다."
            )
        lines.append("")

    lines.extend(
        [
            "## 실수령액 차이가 나는 주요 원인",
            "",
            "1. 참조 대장 고용보험·장기요양은 총지급 기준 재계산과 차이가 날 수 있습니다.",
            "2. 임원·연봉직(시급 0)은 별도 급여 체계로 총지급 불일치가 남을 수 있습니다.",
            "3. 2·4월 근태 export 불완전 시 근무시간 검증만 제한됩니다.",
            "",
            "## 생성 파일",
            "",
        ]
    )

    for r in results:
        od = Path(r["output_dir"])
        lines.append(f"- **{r['period']}**: `{od / '급여대장.xlsx'}`")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    _ensure_milyang_hours_policy()

    leave_path = LEAVE_SOURCE if LEAVE_SOURCE and LEAVE_SOURCE.is_file() else None
    scan = scan_uploads(root=ROOT, extra_dirs=[KAKAO_DIR])
    scan = install_uploads(
        scan,
        explicit_roster=ROSTER_SOURCE if ROSTER_SOURCE.is_file() else None,
        explicit_leave=leave_path,
    )

    results = []
    for period in ("2026-01", "2026-02", "2026-03", "2026-04"):
        print(f"Processing {period}…")
        results.append(process_month(period, scan))

    report_dir = ROOT / "output" / AFFILIATE / WORKPLACE
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "베스텍_밀양_검증보고서.md"
    write_korean_report(results, report_path, scan)

    json_path = report_dir / "베스텍_밀양_검증결과.json"
    meta = {
        "sources": {
            "roster": str(ROSTER_SOURCE),
            "leave": str(LEAVE_SOURCE) if LEAVE_SOURCE else None,
            "attendance": {k: str(v) for k, v in ATTENDANCE_FILES.items()},
            "reference": {k: str(v) for k, v in REFERENCE_FILES.items()},
        },
        "prior_gross_match": PRIOR_GROSS_MATCH,
        "upload_scan": {
            "roster_certificate": str(scan.roster_certificate) if scan.roster_certificate else None,
            "roster_canonical": str(scan.roster_canonical) if scan.roster_canonical else None,
            "leave_standalone": str(scan.leave_standalone) if scan.leave_standalone else None,
            "installed": scan.installed,
            "notes": scan.notes,
        },
        "months": results,
    }
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"\nReport: {report_path}")
    for r in results:
        p = r["period"]
        pg = PRIOR_GROSS_MATCH.get(p, (0, 0, 0))
        print(
            f"  {r['period']}: gross {pg[0]}/{pg[1]}({pg[2]}%) → "
            f"{r['gross_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('gross_match_rate', 0)}%) | "
            f"net 0/{pg[1]}(0%) → "
            f"{r['net_match_count']}/{r.get('reference_active_count', r['reference_count'])} "
            f"({r.get('net_match_rate', 0)}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
