"""

services/archive_browser.py - 월별 자료함 계층 탐색 (COSS → 계열사 → 사업장 → 월 → 파일)

"""



from __future__ import annotations



from dataclasses import dataclass

from pathlib import Path

from typing import Any

import time



from core.brand_display import company_name_line
from core.config import APP_CONFIG

from core.org_config import (
    canonical_scope_workplace,
    list_config_affiliates,
    list_config_workplaces,
    scope_workplaces_match,
)

from leave_usage_ledger import ensure_leave_usage_ledger_dir, get_leave_usage_ledger_path

from payroll_archive import format_period_display

from services.archive_storage import (

    PAYROLL_OUTPUT_NAMES,

    invoice_file_path,

    load_scope_manifest,

    payroll_file_path,

    period_has_payroll_outputs,

)

from services.monthly_leave_manager import scope_leave_export_path

from services.org_registry import ALL_LABEL, OrgSelection

from services.payroll_scope import PayrollScope, discover_scopes, resolve_output_dir



PARENT_ID = "__parent__"





@dataclass(frozen=True)

class ArchiveNavContext:

    level: str  # group | affiliate | workplace | period

    affiliate: str = ""

    workplace: str = ""

    period: str = ""





@dataclass

class ArchiveEntry:

    entry_id: str

    name: str

    kind: str  # parent | group | affiliate | workplace | period | payroll | invoice | leave

    navigable: bool

    path: Path | None = None

    period: str = ""

    affiliate: str = ""

    workplace: str = ""

    hint: str = ""





class ArchiveBrowser:

    """자료함 폴더 트리 — 더블클릭으로 하위·상위 이동."""



    def __init__(self) -> None:

        self._stack: list[ArchiveNavContext] = [ArchiveNavContext(level="group")]

        self._entries: dict[str, ArchiveEntry] = {}

        self._selection = OrgSelection()



    @property

    def context(self) -> ArchiveNavContext:

        return self._stack[-1]



    def breadcrumb(self) -> str:

        parts = [company_name_line()]

        ctx = self.context

        if ctx.affiliate:

            parts.append(ctx.affiliate)

        if ctx.workplace:

            parts.append(ctx.workplace)

        if ctx.period:

            parts.append(format_period_display(ctx.period))

        return "  >  ".join(parts)



    def reset(self, selection: OrgSelection | None = None) -> None:

        self._selection = selection or OrgSelection()

        self._stack = [ArchiveNavContext(level="group")]

        if not _is_all(self._selection.affiliate):

            self._stack = [

                ArchiveNavContext(level="affiliate", affiliate=self._selection.affiliate)

            ]

            if not _is_all(self._selection.workplace):

                self._stack.append(

                    ArchiveNavContext(

                        level="workplace",

                        affiliate=self._selection.affiliate,

                        workplace=self._selection.workplace,

                    )

                )



    def can_go_up(self) -> bool:

        return len(self._stack) > 1



    def go_up(self) -> None:

        if self.can_go_up():

            self._stack.pop()



    def enter(self, entry: ArchiveEntry) -> None:

        ctx = self.context

        if entry.kind == "affiliate":

            self._stack.append(ArchiveNavContext(level="affiliate", affiliate=entry.name))

        elif entry.kind == "workplace":

            self._stack.append(

                ArchiveNavContext(

                    level="workplace",

                    affiliate=entry.affiliate or ctx.affiliate,

                    workplace=entry.name,

                )

            )

        elif entry.kind == "period":

            self._stack.append(

                ArchiveNavContext(

                    level="period",

                    affiliate=entry.affiliate or ctx.affiliate,

                    workplace=entry.workplace or ctx.workplace,

                    period=entry.period,

                )

            )



    def list_entries(self) -> list[ArchiveEntry]:

        self._entries.clear()

        items: list[ArchiveEntry] = []

        if self.can_go_up():

            items.append(

                ArchiveEntry(

                    entry_id=PARENT_ID,

                    name="..",

                    kind="parent",

                    navigable=True,

                    hint="상위 폴더",

                )

            )

        ctx = self.context

        if ctx.level == "group":

            items.extend(self._list_affiliates())

            items.extend(self._list_global_leave_files())

        elif ctx.level == "affiliate":

            items.extend(self._list_workplaces(ctx.affiliate))

        elif ctx.level == "workplace":

            items.extend(self._list_periods(ctx.affiliate, ctx.workplace))

        elif ctx.level == "period":

            items.extend(self._list_period_files(ctx))

        for e in items:

            self._entries[e.entry_id] = e

        return items



    def get_entry(self, entry_id: str) -> ArchiveEntry | None:

        return self._entries.get(entry_id)



    def _list_global_leave_files(self) -> list[ArchiveEntry]:

        """최상위에서 연차사용대장(통합) 바로 열람."""

        out: list[ArchiveEntry] = []

        ensure_leave_usage_ledger_dir()

        ledger = get_leave_usage_ledger_path()

        if ledger.is_file():

            out.append(

                ArchiveEntry(

                    entry_id="leave:global:ledger",

                    name="연차사용대장",

                    kind="leave",

                    navigable=False,

                    path=ledger,

                    hint="통합 연차·무급 관리 (전체)",

                )

            )

        return out



    def _list_affiliates(self) -> list[ArchiveEntry]:

        names: set[str] = set(list_config_affiliates())

        for manifest in _all_manifests():

            aff = str(manifest.get("affiliate") or "").strip()

            if aff:

                names.add(aff)

        if not _is_all(self._selection.affiliate):

            names = {self._selection.affiliate}

        out: list[ArchiveEntry] = []

        for name in sorted(names):

            out.append(

                ArchiveEntry(

                    entry_id=f"aff:{name}",

                    name=name,

                    kind="affiliate",

                    navigable=True,

                    affiliate=name,

                    hint="계열사",

                )

            )

        return out



    def _list_workplaces(self, affiliate: str) -> list[ArchiveEntry]:

        names: set[str] = set(list_config_workplaces(affiliate))

        for manifest in _all_manifests():

            if manifest.get("affiliate") != affiliate:

                continue

            wp = str(manifest.get("workplace") or "").strip()

            if wp:

                names.add(canonical_scope_workplace(wp))

        if not _is_all(self._selection.workplace):

            names = {self._selection.workplace}

        out: list[ArchiveEntry] = []

        for name in sorted(names):

            out.append(

                ArchiveEntry(

                    entry_id=f"wp:{affiliate}:{name}",

                    name=name,

                    kind="workplace",

                    navigable=True,

                    affiliate=affiliate,

                    workplace=name,

                    hint="사업장",

                )

            )

        return out



    def _list_periods(self, affiliate: str, workplace: str) -> list[ArchiveEntry]:

        by_period: dict[str, list[PayrollScope]] = {}

        for scope in discover_scopes():

            if scope.affiliate != affiliate:

                continue

            if not scope_workplaces_match(workplace, scope.workplace):

                continue

            if not period_has_payroll_outputs(scope.period, scope):

                continue

            by_period.setdefault(scope.period, []).append(scope)



        out: list[ArchiveEntry] = []

        for period in sorted(by_period.keys(), reverse=True):

            scope = _pick_best_scope(by_period[period])

            out.append(

                ArchiveEntry(

                    entry_id=f"per:{scope.key}",

                    name=format_period_display(scope.period),

                    kind="period",

                    navigable=True,

                    period=scope.period,

                    affiliate=affiliate,

                    workplace=scope.workplace,

                    hint="급여월",

                )

            )

        return out



    def _scope_from_ctx(self, ctx: ArchiveNavContext) -> PayrollScope:

        return PayrollScope(ctx.affiliate, ctx.workplace, ctx.period)



    def _list_period_files(self, ctx: ArchiveNavContext) -> list[ArchiveEntry]:

        scope = self._scope_from_ctx(ctx)

        period = scope.period

        out: list[ArchiveEntry] = []



        labels = {

            "급여대장.xlsx": "급여대장",

            "급여명세서.xlsx": "급여명세서",

            "지급내역.xlsx": "지급내역",

        }

        for filename in PAYROLL_OUTPUT_NAMES:

            path = payroll_file_path(scope, filename)

            if path is None:

                continue

            out.append(

                ArchiveEntry(

                    entry_id=f"file:{scope.key}:{filename}",

                    name=labels.get(filename, filename),

                    kind="payroll",

                    navigable=False,

                    path=path,

                    period=period,

                    hint="급여 산출",

                )

            )



        inv = invoice_file_path(scope)

        if inv is not None:

            manifest = load_scope_manifest(scope)

            original = str(manifest.get("invoice_original_name") or "").strip()

            hint = "청구서 원본"

            if original and original != inv.name:

                hint = f"원본: {original}"

            out.append(

                ArchiveEntry(

                    entry_id=f"file:{scope.key}:invoice",

                    name="도급비 청구서",

                    kind="invoice",

                    navigable=False,

                    path=inv,

                    period=period,

                    hint=hint,

                )

            )



        leave_path = scope_leave_export_path(scope, period)

        if leave_path.is_file():

            out.append(

                ArchiveEntry(

                    entry_id=f"leave:{scope.key}:monthly",

                    name="당월 연차·결근 현황",

                    kind="leave",

                    navigable=False,

                    path=leave_path,

                    period=period,

                    hint="Excel",

                )

            )



        ledger = get_leave_usage_ledger_path()

        if ledger.is_file():

            out.append(

                ArchiveEntry(

                    entry_id=f"leave:{scope.key}:ledger",

                    name="연차사용대장",

                    kind="leave",

                    navigable=False,

                    path=ledger,

                    period=period,

                    hint="통합 연차·무급 (전사)",

                )

            )



        return out





def _is_all(value: str) -> bool:

    return not value or value == ALL_LABEL





def _scope_period_score(scope: PayrollScope) -> tuple[int, int, int]:

    inv = 1 if invoice_file_path(scope) else 0

    nested = 1 if scope.output_dir().is_dir() and period_has_payroll_outputs(scope.period, scope) else 0

    snap = resolve_output_dir(scope) / "payroll_snapshot.json"

    try:

        sz = snap.stat().st_size if snap.is_file() else 0

    except OSError:

        sz = 0

    return (inv, nested, sz)





def _pick_best_scope(candidates: list[PayrollScope]) -> PayrollScope:

    return max(candidates, key=_scope_period_score)





def _all_manifests() -> list[dict[str, Any]]:

    global _MANIFEST_CACHE

    now = time.monotonic()

    ttl_s = 1.2

    if _MANIFEST_CACHE and (now - _MANIFEST_CACHE["t"]) <= ttl_s:

        return _MANIFEST_CACHE["items"]

    items = [load_scope_manifest(s) for s in discover_scopes()]

    _MANIFEST_CACHE = {"t": now, "items": items}

    return items





_MANIFEST_CACHE: dict[str, Any] = {}


