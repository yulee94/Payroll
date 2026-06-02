"""
End-to-end 테스트 — 실제 청구서 또는 샘플로 3종 출력 검증
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from main import process_invoice
from services.payroll_scope import PayrollScope

REAL_INVOICE = Path(r"c:\Users\MY\Documents\카카오톡 받은 파일\26년05월도급비청구서.xlsx")


def run_test() -> None:
    invoice = REAL_INVOICE if REAL_INVOICE.exists() else None
    if invoice is None:
        raise FileNotFoundError("테스트용 청구서 파일을 찾을 수 없습니다.")

    print(f"청구서: {invoice}")
    scope = PayrollScope("(주)코스", "한국앰코생산", "2026-05")
    info = process_invoice(invoice, scope)
    records = info["records"]
    paths = info["paths"]

    print(f"\n=== {len(records)}명 ===")
    for r in records[:3]:
        print(f"  {r['name']}: 총지급 {r['gross_pay']:,} → 실수령 {r['net_pay']:,}")
    if len(records) > 3:
        print(f"  ... 외 {len(records) - 3}명")

    print("\n=== 출력 ===")
    output_files = [paths["ledger"], paths["payslip"], paths["payment"]]
    output_files.extend(paths.get("ledger_extra") or [])
    for p in output_files:
        print(f"  {p.name}: {p} [{'OK' if p.exists() else 'MISSING'}]")

    assert len(records) > 0
    for p in output_files:
        assert p.exists()
    print("\n[E2E] OK")


if __name__ == "__main__":
    run_test()
