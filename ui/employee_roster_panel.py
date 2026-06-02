"""
ui/employee_roster_panel.py - 직원 명부 조회·수정·저장 (비동기 로드·캐시)
"""

from __future__ import annotations

import copy
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from core.access_control import load_roster_rows_secured
from core.session_service import get_session
from services.employee_roster_store import (
    canonical_roster_path,
    import_roster_from_file,
    roster_exists,
    roster_updated_display,
    save_roster_rows,
)
from bank_account import apply_bank_account_to_record, enrich_roster_bank_info, format_bank_account_display
from disability_employment import (
    DISABILITY_FILTER_CHOICES,
    FILTER_DISABILITY_ALL,
    apply_disability_to_record,
    disability_flag_display,
    format_affiliate_disability_summary,
    is_disabled_employee,
)
from employment_type import (
    FILTER_ALL,
    FILTER_UNSET,
    TYPE_REGULAR_HOURLY,
    EMPLOYMENT_FILTER_CHOICES,
    apply_employment_type_to_record,
    count_employment_stats,
    distinct_affiliates,
    normalize_employment_type,
    record_matches_roster_filters,
)
from employment_succession import (
    apply_succession_to_record,
    format_succession_path,
    group_first_hire_date,
)
from senior_internship import (
    FILTER_SENIOR_ALL,
    FILTER_SENIOR_EXCLUDED,
    SENIOR_FILTER_CHOICES,
    apply_senior_internship_display,
    classify_senior_internship_job,
    count_senior_internship_stats,
    normalize_senior_internship_status,
    parse_roster_date_input,
    senior_internship_help_text,
    senior_internship_mark,
    senior_internship_period_text,
    status_from_mark_input,
)
from ui.theme import COLORS, FONT
from utils import round_won

ROSTER_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("성명", "성명", 88),
    ("업무", "업무", 72),
    ("사번", "사번", 52),
    ("고용형태", "고용형태", 92),
    ("근무지", "근무지", 140),
    ("계열사", "계열사", 88),
    ("장애인", "장애인", 52),
    ("장애등급", "장애등급", 64),
    ("_group_first_hire_display", "최초입사일", 88),
    ("_succession_path_display", "승계경로", 260),
    ("입사일", "현재입사일", 80),
    ("기본시급", "기본시급", 72),
    ("통상시급", "통상시급", 72),
    ("수당", "수당", 56),
    ("국민연금", "국민연금", 72),
    ("건강보험", "건강보험", 72),
    ("소득세", "소득세", 64),
    ("휴대폰", "휴대폰", 100),
    ("예금주", "예금주", 72),
    ("은행명", "은행명", 88),
    ("계좌번호", "계좌번호", 120),
    ("_bank_account_display", "은행·계좌", 200),
    ("발생연차", "발생", 48),
    ("사용연차", "사용", 48),
    ("잔여연차", "잔여", 48),
    ("다음발생", "_next_accrual_display", 92),
    ("_senior_internship_mark", "시니어인턴십(만60)", 52),
    ("_senior_internship_period", "시니어지원기간", 300),
)

SENIOR_MARK_FIELD = "_senior_internship_mark"
SENIOR_PERIOD_FIELD = "_senior_internship_period"
GROUP_HIRE_FIELD = "_group_first_hire_display"
SUCCESSION_PATH_FIELD = "_succession_path_display"
BANK_ACCOUNT_FIELDS = frozenset({"예금주", "계좌번호", "은행명", "은행코드"})
BANK_DISPLAY_FIELD = "_bank_account_display"
EMPLOYMENT_TYPE_FIELD = "고용형태"
DISABILITY_FLAG_FIELD = "장애인"
DISABILITY_GRADE_FIELD = "장애등급"

NUMERIC_FIELDS = frozenset(
    {
        "기본시급",
        "통상시급",
        "수당",
        "국민연금",
        "건강보험",
        "소득세",
        "발생연차",
        "사용연차",
        "잔여연차",
        "예상발생연차",
    }
)

WON_FIELDS = frozenset(
    {
        "기본시급",
        "통상시급",
        "수당",
        "국민연금",
        "건강보험",
        "소득세",
    }
)


def _parse_won_input(text: str) -> int | None:
    try:
        return round_won(float(text.replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _format_cell(field: str, val: Any) -> str:
    if val is None or val == "":
        return ""
    if field in WON_FIELDS:
        try:
            return f"{round_won(float(val)):,}"
        except (TypeError, ValueError):
            return str(val)
    if field in NUMERIC_FIELDS:
        try:
            n = float(val)
            if n == int(n):
                return str(int(n))
            return f"{n:g}"
        except (TypeError, ValueError):
            return str(val)
    return str(val)


def _normalize_won_in_record(rec: dict[str, Any]) -> None:
    """명부 금액 필드 — 내부값도 원 단위 반올림."""
    for field in WON_FIELDS:
        val = rec.get(field)
        if val is None or val == "":
            continue
        try:
            rec[field] = float(round_won(float(val)))
        except (TypeError, ValueError):
            pass


def _format_row_tuple(rec: dict[str, Any]) -> tuple[str, ...]:
    apply_succession_to_record(rec)
    apply_bank_account_to_record(rec)
    apply_employment_type_to_record(rec)
    apply_disability_to_record(rec)
    apply_senior_internship_display(rec)
    cells: list[str] = []
    for field, _title, _width in ROSTER_COLUMNS:
        if field == SENIOR_MARK_FIELD:
            cells.append(senior_internship_mark(rec))
        elif field == SENIOR_PERIOD_FIELD:
            cells.append(senior_internship_period_text(rec))
        elif field == GROUP_HIRE_FIELD:
            cells.append(group_first_hire_date(rec))
        elif field == SUCCESSION_PATH_FIELD:
            cells.append(format_succession_path(rec))
        elif field == BANK_DISPLAY_FIELD:
            cells.append(format_bank_account_display(rec))
        else:
            cells.append(_format_cell(field, rec.get(field, "")))
    return tuple(cells)


class EmployeeRosterPanel(ttk.Frame):
    """근로자 명부 편집 — 저장 시 templates/근로자명부.xlsx 갱신."""

    def __init__(self, parent, on_saved=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._on_saved = on_saved
        self._rows: list[dict[str, Any]] = []
        self._display: list[tuple[str, ...]] = []
        self._dirty = False
        self._loaded_mtime: float = 0.0
        self._loading = False
        self._load_token = 0
        self._load_thread: threading.Thread | None = None

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        self._btn_reload = ttk.Button(toolbar, text="새로고침", command=lambda: self.reload(force=True))
        self._btn_reload.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="저장", command=self._save).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="행 추가", command=self._add_row).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="선택 삭제", command=self._delete_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
        ttk.Button(toolbar, text="엑셀에서 가져오기", command=self._import_excel).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="명부 파일 열기", command=self._open_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="고용승계…", command=self._edit_succession_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="지급계좌…", command=self._edit_bank_account_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="장애인 현황…", command=self._show_disability_summary).pack(side=tk.LEFT)

        filter_bar = ttk.LabelFrame(self, text="명부 미리보기 필터", padding=(8, 6))
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        self._filter_employment = tk.StringVar(value=FILTER_ALL)
        self._filter_affiliate = tk.StringVar(value=FILTER_ALL)
        self._filter_senior = tk.StringVar(value=FILTER_SENIOR_ALL)
        self._filter_disability = tk.StringVar(value=FILTER_DISABILITY_ALL)
        self._filter_name = tk.StringVar(value="")

        ttk.Label(filter_bar, text="고용형태", font=(FONT, 9)).grid(row=0, column=0, padx=(0, 4), sticky=tk.W)
        self._filter_employment_combo = ttk.Combobox(
            filter_bar,
            textvariable=self._filter_employment,
            values=list(EMPLOYMENT_FILTER_CHOICES),
            state="readonly",
            width=14,
        )
        self._filter_employment_combo.grid(row=0, column=1, padx=(0, 12), sticky=tk.W)
        self._filter_employment_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Label(filter_bar, text="계열사", font=(FONT, 9)).grid(row=0, column=2, padx=(0, 4), sticky=tk.W)
        self._filter_affiliate_combo = ttk.Combobox(
            filter_bar,
            textvariable=self._filter_affiliate,
            values=[FILTER_ALL],
            state="readonly",
            width=16,
        )
        self._filter_affiliate_combo.grid(row=0, column=3, padx=(0, 12), sticky=tk.W)
        self._filter_affiliate_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Label(filter_bar, text="성명 검색", font=(FONT, 9)).grid(row=0, column=4, padx=(0, 4), sticky=tk.W)
        self._filter_name_entry = ttk.Entry(filter_bar, textvariable=self._filter_name, width=14)
        self._filter_name_entry.grid(row=0, column=5, padx=(0, 8), sticky=tk.W)
        self._filter_name.trace_add("write", self._on_filter_changed)

        ttk.Label(filter_bar, text="시니어인턴십", font=(FONT, 9)).grid(
            row=0, column=6, padx=(8, 4), sticky=tk.W
        )
        self._filter_senior_combo = ttk.Combobox(
            filter_bar,
            textvariable=self._filter_senior,
            values=list(SENIOR_FILTER_CHOICES),
            state="readonly",
            width=18,
        )
        self._filter_senior_combo.grid(row=0, column=7, padx=(0, 8), sticky=tk.W)
        self._filter_senior_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Label(filter_bar, text="장애인", font=(FONT, 9)).grid(row=0, column=8, padx=(8, 4), sticky=tk.W)
        self._filter_disability_combo = ttk.Combobox(
            filter_bar,
            textvariable=self._filter_disability,
            values=list(DISABILITY_FILTER_CHOICES),
            state="readonly",
            width=10,
        )
        self._filter_disability_combo.grid(row=0, column=9, padx=(0, 8), sticky=tk.W)
        self._filter_disability_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Button(filter_bar, text="필터 초기화", command=self._reset_filters, width=10).grid(
            row=0, column=10, padx=(4, 0), sticky=tk.W
        )

        self._filter_summary = ttk.Label(filter_bar, text="", font=(FONT, 8))
        self._filter_summary.grid(row=1, column=0, columnspan=11, sticky=tk.W, pady=(6, 0))

        self._disability_summary = ttk.Label(filter_bar, text="", font=(FONT, 8))
        self._disability_summary.grid(row=2, column=0, columnspan=11, sticky=tk.W, pady=(2, 0))

        self._status = tk.Label(
            self,
            text="명부 탭을 열면 데이터를 불러옵니다.",
            anchor=tk.W,
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=12,
            pady=8,
            wraplength=900,
            justify=tk.LEFT,
        )
        self._status.pack(fill=tk.X, pady=(0, 8))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        col_ids = [c[0] for c in ROSTER_COLUMNS]
        self.tree = ttk.Treeview(table_wrap, columns=col_ids, show="headings", selectmode="extended")
        for field, title, width in ROSTER_COLUMNS:
            self.tree.heading(field, text=title)
            if field in (SENIOR_MARK_FIELD, DISABILITY_FLAG_FIELD):
                anchor = tk.CENTER
            elif field == "업무":
                anchor = tk.W
            elif field in NUMERIC_FIELDS or field in WON_FIELDS:
                anchor = tk.E
            else:
                anchor = tk.W
            self.tree.column(field, width=width, minwidth=40, anchor=anchor)

        yscroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_wrap, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.tag_configure(
            "senior_excluded",
            background="#F1F5F9",
            foreground="#64748B",
        )
        self.tree.tag_configure(
            "disability_yes",
            background="#EEF2FF",
        )

        note = tk.Label(
            self,
            text=(
                "셀 더블클릭으로 수정 · 저장한 명부는 다음 청구서 업로드 시 급여대장·명세서·지급내역·보고서 산출에 자동 반영됩니다.  "
                "·  고용승계: 최초입사일·승계경로 표시 · 「고용승계…」 또는 승계경로 더블클릭으로 편집  "
                "·  고용형태: 일용직 / 정규직(시급) / 정규직(연봉) · 필터로 명부 미리보기  "
                "·  시니어인턴십: 경비·미화 등 단순노무는 「제외」  "
                "·  장애인: 예/아니오 · 「장애인 현황…」으로 계열사(법인)별 보유 인원"
            ),
            anchor=tk.W,
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=900,
        )
        note.pack(fill=tk.X, pady=(8, 0))

    def _file_mtime(self) -> float:
        path = canonical_roster_path()
        try:
            return path.stat().st_mtime if path.is_file() else 0.0
        except OSError:
            return 0.0

    def _set_loading_ui(self, loading: bool, message: str = "") -> None:
        self._loading = loading
        state = tk.DISABLED if loading else tk.NORMAL
        try:
            self._btn_reload.configure(state=state)
        except tk.TclError:
            pass
        if message:
            self._status.configure(text=message)

    def _row_tags(self, rec: dict[str, Any] | None) -> tuple[str, ...]:
        if not rec:
            return ()
        tags: list[str] = []
        if rec.get("_senior_job_excluded"):
            tags.append("senior_excluded")
        if is_disabled_employee(rec):
            tags.append("disability_yes")
        return tuple(tags)

    def _insert_tree_row(self, idx: int, values: tuple[str, ...], rec: dict[str, Any] | None = None) -> None:
        self.tree.insert("", tk.END, iid=str(idx), values=values, tags=self._row_tags(rec))

    def _active_filters(self) -> tuple[str, str, str, str, str]:
        return (
            self._filter_employment.get(),
            self._filter_affiliate.get(),
            self._filter_name.get(),
            self._filter_senior.get(),
            self._filter_disability.get(),
        )

    def _row_passes_filter(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self._rows):
            return False
        emp_f, aff_f, name_q, senior_f, dis_f = self._active_filters()
        return record_matches_roster_filters(
            self._rows[idx],
            employment_filter=emp_f,
            affiliate_filter=aff_f,
            name_query=name_q,
            senior_filter=senior_f,
            disability_filter=dis_f,
        )

    def _visible_row_count(self) -> int:
        return sum(1 for i in range(len(self._rows)) if self._row_passes_filter(i))

    def _filters_active(self) -> bool:
        emp_f, aff_f, name_q, senior_f, dis_f = self._active_filters()
        return (
            emp_f != FILTER_ALL
            or aff_f != FILTER_ALL
            or senior_f != FILTER_SENIOR_ALL
            or dis_f != FILTER_DISABILITY_ALL
            or bool(str(name_q or "").strip())
        )

    def _refresh_filter_affiliate_values(self) -> None:
        values = [FILTER_ALL] + distinct_affiliates(self._rows)
        self._filter_affiliate_combo.configure(values=values)
        if self._filter_affiliate.get() not in values:
            self._filter_affiliate.set(FILTER_ALL)

    def _update_filter_summary(self) -> None:
        emp = count_employment_stats(self._rows)
        senior = count_senior_internship_stats(self._rows)
        parts = [
            f"전체 {emp['total']}명",
            f"만60세 {senior['age_60_plus']}",
            f"지원가능 {senior['program_eligible']}",
            f"단순노무제외 {senior['job_excluded']}",
        ]
        visible = self._visible_row_count()
        if self._filters_active():
            parts.append(f"—  표시 {visible}명")
        self._filter_summary.configure(text="  ·  ".join(parts))
        self._disability_summary.configure(
            text=format_affiliate_disability_summary(self._rows)
        )

    def _on_filter_changed(self, *_args) -> None:
        if self._loading or not self._rows:
            return
        self._redraw_tree_view()
        self._update_filter_summary()
        self._update_status()

    def _reset_filters(self) -> None:
        self._filter_employment.set(FILTER_ALL)
        self._filter_affiliate.set(FILTER_ALL)
        self._filter_senior.set(FILTER_SENIOR_ALL)
        self._filter_disability.set(FILTER_DISABILITY_ALL)
        self._filter_name.set("")
        self._on_filter_changed()

    def _update_status(self) -> None:
        if roster_exists():
            stats = count_senior_internship_stats(self._rows)
            extra = ""
            if stats["age_60_plus"]:
                extra = (
                    f"  ·  시니어 만60세 {stats['age_60_plus']}명"
                    f" (지원가능 {stats['program_eligible']} · 제외 {stats['job_excluded']}"
                    f" · O {stats['can_apply']} △ {stats['in_progress']} X {stats['completed']})"
                )
            total = len(self._rows)
            visible = self._visible_row_count()
            count_text = f"등록 {total}명"
            if self._filters_active() and visible != total:
                count_text = f"표시 {visible}명 / 전체 {total}명"
            self._status.configure(
                text=(
                    f"최종 갱신: {roster_updated_display()}  ·  "
                    + count_text
                    + extra
                    + ("  ·  저장되지 않은 변경 있음" if self._dirty else "")
                )
            )
            self._update_filter_summary()
        else:
            self._status.configure(
                text="명부 파일이 없습니다. 「행 추가」 또는 「엑셀에서 가져오기」로 등록한 뒤 저장하세요."
            )

    def reload(self, *, force: bool = False) -> None:
        if self._loading:
            return

        mtime = self._file_mtime()
        if not force and self._rows and not self._dirty and self._loaded_mtime == mtime:
            self._update_status()
            return

        self._load_token += 1
        token = self._load_token
        self._set_loading_ui(True, "명부를 불러오는 중…")

        def work() -> None:
            try:
                if force:
                    from core.access_control import invalidate_executive_index
                    from services.employee_roster_store import load_roster_rows

                    load_roster_rows(force=True)
                    invalidate_executive_index()
                rows = load_roster_rows_secured(session=get_session())
                err: str | None = None
            except OSError as exc:
                rows = []
                err = str(exc)

            def finish() -> None:
                if token != self._load_token:
                    return
                if err:
                    self._set_loading_ui(False)
                    messagebox.showerror("불러오기 실패", err)
                    return
                self._apply_loaded(rows, mtime=self._file_mtime())

            root = self.winfo_toplevel()
            if root.winfo_exists():
                root.after(0, finish)

        self._load_thread = threading.Thread(target=work, daemon=True)
        self._load_thread.start()

    def _apply_loaded(self, rows: list[dict[str, Any]], *, mtime: float) -> None:
        for rec in rows:
            _normalize_won_in_record(rec)
            apply_succession_to_record(rec)
            apply_bank_account_to_record(rec)
            apply_employment_type_to_record(rec)
            apply_disability_to_record(rec)
            raw = rec.get("시니어인턴십상태")
            if raw is not None and str(raw).strip():
                rec["시니어인턴십상태"] = normalize_senior_internship_status(raw)
        enrich_roster_bank_info(rows)
        self._rows = rows
        self._display = [_format_row_tuple(rec) for rec in rows]
        self._dirty = False
        self._loaded_mtime = mtime
        self._refresh_filter_affiliate_values()
        self._redraw_tree_view()
        self._set_loading_ui(False)
        self._update_status()

    def _redraw_tree_view(self) -> None:
        self.tree.configure(selectmode="none")
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for idx, values in enumerate(self._display):
            if self._row_passes_filter(idx):
                self._insert_tree_row(idx, values, self._rows[idx])
        self.tree.configure(selectmode="extended")

    def _redraw_tree_full(self) -> None:
        self._redraw_tree_view()

    def _refresh_row(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._rows):
            return
        self._display[idx] = _format_row_tuple(self._rows[idx])
        iid = str(idx)
        if self._row_passes_filter(idx):
            tags = self._row_tags(self._rows[idx])
            if self.tree.exists(iid):
                self.tree.item(iid, values=self._display[idx], tags=tags)
            else:
                self._insert_tree_row(idx, self._display[idx], self._rows[idx])
        elif self.tree.exists(iid):
            self.tree.delete(iid)

    def _reindex_tree_after_delete(self) -> None:
        """행 삭제 후 iid·표시 캐시 재정렬."""
        self._display = [_format_row_tuple(rec) for rec in self._rows]
        self._redraw_tree_view()

    def _add_row(self) -> None:
        if self._loading:
            return
        self._rows.append({"성명": "신규", "_row": None, "고용형태": TYPE_REGULAR_HOURLY})
        self._display.append(_format_row_tuple(self._rows[-1]))
        idx = len(self._rows) - 1
        if self._row_passes_filter(idx):
            self._insert_tree_row(idx, self._display[idx], self._rows[idx])
            self.tree.selection_set(str(idx))
            self.tree.see(str(idx))
        self._dirty = True
        self._refresh_filter_affiliate_values()
        self._update_status()

    def _delete_selected(self) -> None:
        if self._loading:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("선택 없음", "삭제할 행을 선택하세요.")
            return
        if not messagebox.askyesno(
            "삭제 확인",
            f"선택한 {len(sel)}명을 목록에서 제거할까요?\n(저장 시 명부에서 삭제됩니다)",
        ):
            return
        indices = sorted((int(i) for i in sel), reverse=True)
        for i in indices:
            if 0 <= i < len(self._rows):
                self._rows.pop(i)
        self._dirty = True
        self._reindex_tree_after_delete()
        self._refresh_filter_affiliate_values()
        self._update_status()

    def _on_double_click(self, event) -> None:
        if self._loading:
            return
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        try:
            idx = int(row_id)
        except ValueError:
            return
        if idx < 0 or idx >= len(self._rows):
            return
        col_num = int(col_id.replace("#", "")) - 1
        if col_num < 0 or col_num >= len(ROSTER_COLUMNS):
            return
        field = ROSTER_COLUMNS[col_num][0]
        rec = self._rows[idx]
        title = ROSTER_COLUMNS[col_num][1]

        if field in (GROUP_HIRE_FIELD, SUCCESSION_PATH_FIELD):
            self._open_succession_editor(idx, rec)
            return
        if field in BANK_ACCOUNT_FIELDS or field == BANK_DISPLAY_FIELD:
            self._open_bank_account_editor(idx, rec)
            return
        if field == EMPLOYMENT_TYPE_FIELD:
            self._edit_employment_type(idx, rec)
            return
        if field == DISABILITY_FLAG_FIELD:
            self._edit_disability_flag(idx, rec)
            return
        if field == SENIOR_MARK_FIELD:
            self._edit_senior_mark(idx, rec, title)
            return
        if field == SENIOR_PERIOD_FIELD:
            self._edit_senior_period(idx, rec, title)
            return

        current = rec.get(field, "")
        if current is None:
            current = ""
        initial = (
            _format_cell(field, current)
            if field in WON_FIELDS and current != ""
            else str(current)
        )
        new_val = simpledialog.askstring(
            "셀 수정",
            f"{rec.get('성명', '')} — {title}",
            initialvalue=initial,
            parent=self.winfo_toplevel(),
        )
        if new_val is None:
            return
        new_val = new_val.strip()
        if field in WON_FIELDS and new_val:
            parsed = _parse_won_input(new_val)
            if parsed is None:
                messagebox.showwarning("입력 오류", "숫자 형식으로 입력해 주세요.")
                return
            rec[field] = float(parsed)
        elif field in NUMERIC_FIELDS and new_val:
            try:
                rec[field] = float(new_val.replace(",", ""))
            except ValueError:
                messagebox.showwarning("입력 오류", "숫자 형식으로 입력해 주세요.")
                return
        elif new_val == "":
            rec[field] = None
        else:
            rec[field] = new_val
        if field in BANK_ACCOUNT_FIELDS or field == "계좌":
            apply_bank_account_to_record(rec)
        if field == EMPLOYMENT_TYPE_FIELD:
            apply_employment_type_to_record(rec)
        if field in (DISABILITY_FLAG_FIELD, DISABILITY_GRADE_FIELD):
            apply_disability_to_record(rec)
        self._dirty = True
        self._refresh_row(idx)
        self.tree.selection_set(row_id)
        self._update_status()

    def _show_disability_summary(self) -> None:
        if self._loading:
            return
        if not self._rows:
            messagebox.showinfo("명부 없음", "불러온 명부가 없습니다.", parent=self.winfo_toplevel())
            return
        from ui.disability_summary_dialog import show_disability_summary_dialog

        show_disability_summary_dialog(self.winfo_toplevel(), self._rows)

    def _edit_disability_flag(self, idx: int, rec: dict[str, Any]) -> None:
        from ui.disability_pick_dialog import pick_disability_flag

        apply_disability_to_record(rec)
        initial = disability_flag_display(rec)
        picked = pick_disability_flag(
            self.winfo_toplevel(),
            initial=initial,
            employee_name=str(rec.get("성명") or ""),
        )
        if picked is None:
            return
        rec["장애인"] = picked or None
        apply_disability_to_record(rec)
        self._dirty = True
        self._refresh_row(idx)
        self._update_filter_summary()
        self._update_status()

    def _edit_employment_type(self, idx: int, rec: dict[str, Any]) -> None:
        from ui.employment_type_pick_dialog import pick_employment_type

        initial = normalize_employment_type(rec.get("고용형태"))
        picked = pick_employment_type(
            self.winfo_toplevel(),
            initial=initial,
            employee_name=str(rec.get("성명") or ""),
        )
        if picked is None:
            return
        rec["고용형태"] = normalize_employment_type(picked) or None
        self._dirty = True
        self._refresh_row(idx)
        self._update_filter_summary()
        self._update_status()

    def _edit_bank_account_selected(self) -> None:
        if self._loading:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("선택 없음", "지급 계좌를 편집할 직원을 선택하세요.")
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if 0 <= idx < len(self._rows):
            self._open_bank_account_editor(idx, self._rows[idx])

    def _open_bank_account_editor(self, idx: int, rec: dict[str, Any]) -> None:
        from ui.bank_account_edit_dialog import open_bank_account_editor

        def on_apply(_rec: dict[str, Any]) -> None:
            self._dirty = True
            self._refresh_row(idx)
            self._update_status()

        open_bank_account_editor(self.winfo_toplevel(), rec, on_apply=on_apply)

    def _edit_succession_selected(self) -> None:
        if self._loading:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("선택 없음", "고용승계를 편집할 직원을 선택하세요.")
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if 0 <= idx < len(self._rows):
            self._open_succession_editor(idx, self._rows[idx])

    def _open_succession_editor(self, idx: int, rec: dict[str, Any]) -> None:
        from ui.succession_edit_dialog import open_succession_editor

        def on_apply(_rec: dict[str, Any]) -> None:
            self._dirty = True
            self._refresh_row(idx)
            self._update_status()

        open_succession_editor(self.winfo_toplevel(), rec, on_apply=on_apply)

    def _edit_senior_mark(self, idx: int, rec: dict[str, Any], title: str) -> None:
        apply_senior_internship_display(rec)
        excluded, reason = classify_senior_internship_job(rec)
        if excluded:
            messagebox.showinfo(
                "시니어 인턴십 지원 불가",
                f"{rec.get('성명', '')} — {senior_internship_help_text()}\n\n"
                f"판정: 단순노무 ({reason}) · 업무: {rec.get('업무') or '-'}",
                parent=self.winfo_toplevel(),
            )
            return
        initial = senior_internship_mark(rec) or ""
        new_val = simpledialog.askstring(
            "시니어 인턴십",
            f"{rec.get('성명', '')} — {title}\n\nO: 신청 가능  ·  △: 진행중  ·  X: 지원 완료\n"
            f"(만 60세 미만·단순노무 직종은 비움)",
            initialvalue=initial,
            parent=self.winfo_toplevel(),
        )
        if new_val is None:
            return
        new_val = new_val.strip()
        if new_val and new_val.upper() not in ("O", "X", "△", "▲", "○", "×") and new_val not in (
            "진행중",
            "완료",
        ):
            messagebox.showwarning(
                "입력 오류",
                "O, △, X 중 하나를 입력하거나 비워 두세요.",
            )
            return
        status = status_from_mark_input(new_val)
        rec["시니어인턴십상태"] = status or None
        self._dirty = True
        self._refresh_row(idx)
        self._update_status()

    def _edit_senior_period(self, idx: int, rec: dict[str, Any], title: str) -> None:
        start_initial = rec.get("시니어인턴십지원일") or ""
        end_initial = rec.get("시니어인턴십재직충족일") or ""
        start_val = simpledialog.askstring(
            "시니어 지원기간",
            f"{rec.get('성명', '')} — 지원일자 (YYYY.MM.DD)\n비우면 0000.00.00",
            initialvalue=str(start_initial),
            parent=self.winfo_toplevel(),
        )
        if start_val is None:
            return
        end_val = simpledialog.askstring(
            "시니어 지원기간",
            f"{rec.get('성명', '')} — 재직충족 기간 (YYYY.MM.DD)\n비우면 0000.00.00",
            initialvalue=str(end_initial),
            parent=self.winfo_toplevel(),
        )
        if end_val is None:
            return
        parsed_start = parse_roster_date_input(start_val)
        parsed_end = parse_roster_date_input(end_val)
        if start_val.strip() and parsed_start is None:
            messagebox.showwarning("입력 오류", "지원일자 형식을 확인해 주세요. (예: 2024.03.15)")
            return
        if end_val.strip() and parsed_end is None:
            messagebox.showwarning("입력 오류", "재직충족일 형식을 확인해 주세요. (예: 2025.03.14)")
            return
        rec["시니어인턴십지원일"] = parsed_start
        rec["시니어인턴십재직충족일"] = parsed_end
        self._dirty = True
        self._refresh_row(idx)
        self._update_status()

    def _save(self) -> None:
        if self._loading:
            return
        cleaned: list[dict[str, Any]] = []
        for rec in self._rows:
            name = str(rec.get("성명") or "").strip()
            if not name or name == "신규":
                continue
            row_copy = copy.deepcopy(rec)
            _normalize_won_in_record(row_copy)
            apply_bank_account_to_record(row_copy)
            apply_employment_type_to_record(row_copy)
            cleaned.append(row_copy)
        if not cleaned:
            if not messagebox.askyesno("확인", "등록된 직원이 없습니다. 빈 명부로 저장할까요?"):
                return
        self._set_loading_ui(True, "명부를 저장하는 중…")

        def work() -> None:
            err: str | None = None
            count = 0
            try:
                count = save_roster_rows(cleaned, note="UI 저장")
            except OSError as exc:
                err = str(exc)

            def finish() -> None:
                self._set_loading_ui(False)
                if err:
                    messagebox.showerror("저장 실패", f"명부를 저장하지 못했습니다.\n\n{err}")
                    return
                self._dirty = False
                self._loaded_mtime = self._file_mtime()
                self._update_status()
                messagebox.showinfo(
                    "저장 완료",
                    f"근로자 명부 {count}명을 저장했습니다.\n다음 청구서 산출부터 반영됩니다.",
                )
                if self._on_saved:
                    self._on_saved()

            self.winfo_toplevel().after(0, finish)

        threading.Thread(target=work, daemon=True).start()

    def _import_excel(self) -> None:
        if self._loading:
            return
        path = filedialog.askopenfilename(
            title="명부 엑셀 가져오기",
            filetypes=[("Excel", "*.xlsx"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "가져오기 확인",
            f"「{Path(path).name}」 내용으로\n{canonical_roster_path().name} 을(를) 덮어씁니다.\n계속할까요?",
        ):
            return
        self._set_loading_ui(True, "엑셀을 가져오는 중…")

        def work() -> None:
            err: str | None = None
            count = 0
            try:
                count = import_roster_from_file(Path(path))
            except OSError as exc:
                err = str(exc)

            def finish() -> None:
                if err:
                    self._set_loading_ui(False)
                    messagebox.showerror("가져오기 실패", err)
                    return
                self.reload(force=True)
                messagebox.showinfo("가져오기 완료", f"명부 {count}명을 불러왔습니다.")
                if self._on_saved:
                    self._on_saved()

            self.winfo_toplevel().after(0, finish)

        threading.Thread(target=work, daemon=True).start()

    def _open_file(self) -> None:
        path = canonical_roster_path()
        if not path.is_file():
            messagebox.showinfo("파일 없음", "저장된 명부가 없습니다. 먼저 저장하거나 가져오기를 실행하세요.")
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError:
            subprocess.run(["explorer", str(path)], check=False)
