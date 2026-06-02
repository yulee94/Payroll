"""
rebuild_payroll_from_saved_invoices.py

output/ 아래 저장된 '도급비청구서' 파일을 기준으로 급여 산출 결과를 재생성합니다.

사용 예)
  python tools/rebuild_payroll_from_saved_invoices.py --from 2026-01 --to 2026-05
  python tools/rebuild_payroll_from_saved_invoices.py --tenant-scope "(주)코스" --workplace "한국앰코" --from 2026-01 --to 2026-05
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from excel_writer import OUTPUT_DIR
from services.payroll_output_refresh import iter_saved_invoice_scopes, refresh_scope_from_saved_invoice
from services.payroll_scope import PayrollScope

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class InvoiceHit:
    invoice_path: Path
    scope: PayrollScope


def _iter_invoice_hits() -> list[InvoiceHit]:
    return list(iter_saved_invoice_scopes())


def _period_in_range(period: str, start: str | None, end: str | None) -> bool:
    if not _PERIOD_RE.match(period):
        return False
    if start and period < start:
        return False
    if end and period > end:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default=None, help="시작 월 (YYYY-MM)")
    ap.add_argument("--to", dest="end", default=None, help="종료 월 (YYYY-MM)")
    ap.add_argument("--tenant-scope", dest="affiliate", default=None, help="계열사/고객사 폴더명 (예: (주)코스)")
    ap.add_argument("--workplace", dest="workplace", default=None, help="사업장 폴더명 (예: 한국앰코)")
    ap.add_argument("--dry-run", action="store_true", help="실제 재생성 없이 대상만 출력")
    args = ap.parse_args()

    hits = _iter_invoice_hits()
    if args.affiliate:
        hits = [h for h in hits if h.scope.affiliate == args.affiliate]
    if args.workplace:
        hits = [h for h in hits if h.scope.workplace == args.workplace]
    if args.start or args.end:
        hits = [h for h in hits if _period_in_range(h.scope.period, args.start, args.end)]

    if not hits:
        print("대상이 없습니다. output/ 아래에 '도급비청구서.xlsx'가 있는지 확인하세요.")
        return 2

    print(f"대상 {len(hits)}건")
    for h in hits:
        print(f"- {h.scope.key}  <=  {h.invoice_path}")

    if args.dry_run:
        return 0

    ok = 0
    fail = 0
    for h in hits:
        try:
            refresh_scope_from_saved_invoice(h.scope, invoice_path=h.invoice_path)
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"[FAIL] {h.scope.key}: {exc}")

    print(f"완료: 성공 {ok} / 실패 {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

