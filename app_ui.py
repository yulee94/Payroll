"""
app_ui.py - 급여 관리 대시보드 (월별 자료함 · 요약 · 파일 열람)
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk

from dnd_support import enable_invoice_drop
from excel_writer import OUTPUT_DIR, TEMPLATES_DIR
from leave_usage_ledger import LEAVE_USAGE_LEDGER_DIR
from main import process_invoice, show_personnel_mismatch_dialog
from payroll_builder import ROSTER_FILENAME, get_templates_roster_path
from services.employee_roster_store import roster_exists, roster_updated_display
from payroll_comparison import PAYROLL_DIFF_DIR
from payroll_archive import (
    MonthSummary,
    collect_files_for_period,
    format_period_display,
    list_payroll_periods,
)
from core.tenant_data_scope import build_month_summary_for_tenant, discover_scopes_for_tenant
from core.config import (
    APP_CONFIG,
    BASE_DIR as APP_BASE,
    MONTHLY_REPORTS_DIR,
)
from core.version_display import app_version_label, log_startup_version
from services.archive_storage import ensure_scope_manifest
from services.auto_update import (
    UpdateCheckResult,
    apply_update,
    check_for_update,
    download_update,
    format_update_message,
    should_check_updates,
)
from ui.preview_panel import FilePreviewPanel
from ui.user_display import (
    format_result_summary,
    format_save_success,
    format_validation_error,
    friendly_document_title,
    friendly_error,
)
from core.theme_store import load_user_theme, set_saved_theme_id
from ui.theme import (
    COLORS,
    FONT,
    FONT_BODY,
    FONT_NAV,
    FONT_STAT,
    FONT_SUBTITLE,
    FONT_TITLE,
    SIDEBAR_WIDTH,
    WINDOW_DEFAULT,
    WINDOW_MIN,
    add_theme_listener,
    apply_theme,
    get_current_theme_id,
)
from services.executive_analytics import build_executive_analytics
from services.monthly_report import (
    build_report_bundle,
    export_monthly_report_excel,
    get_or_create_report_path,
)
from core.org_access import (
    can_access_payroll_settings,
    can_access_platform,
    can_manage_org,
    can_manage_tenant_settings,
    has_permission,
)
from core.org_positions import PERM_USER_ROLES
from core.access_control import (
    can_view_executive_reports,
    load_records_for_period_secured,
    require_executive_payroll_access,
    session_role,
)
from core.session_service import get_session, is_logged_in, logout, session_tenant_id
from services.org_registry import ALL_LABEL, OrgSelection, filter_records, summarize_records
from services.payroll_scope import PayrollScope, discover_scopes, resolve_output_dir
from services.upload_undo import (
    build_undo_final_confirm_message,
    build_undo_warning_message,
    can_undo,
    peek_undo,
    scope_from_undo,
    undo_last_upload,
)
from ui.ai_assistant_dialog import open_ai_assistant
from ui.archive_folder_panel import ArchiveFolderPanel
from ui.archive_records_panel import ArchiveRecordsPanel
from ui.archive_leave_panel import ArchiveLeavePanel
from ui.wheel_scroll import bind_local_wheel, install_global_wheel
from ui.executive_dashboard import ExecutiveDashboardPanel
from ui.workflow_hub_panel import WorkflowHubPanel
from ui.module_hub_panel import (
    ModuleHubPanel,
    build_accounting_hub,
    build_bidding_hub,
    build_maintenance_hub,
    build_recruitment_hub,
)
from ui.org_filter_bar import OrgFilterBar
from ui.reports_dashboard import ReportsDashboardPanel
from ui.revision_history_panel import RevisionHistoryPanel
from core.brand_display import app_window_title, company_name_line
from core.platforms import PLATFORMS, get_platform
from core.session_service import add_session_listener, clear_session_for_tenant_change, try_restore_session
from core.tenant_store import get_active_tenant_id
from core.i18n import (
    add_locale_listener,
    init_i18n,
    t,
    tf,
)
from ui.hr_hub_panel import build_hr_hub
from ui.kpi_hub_panel import build_kpi_hub
from ui.front_page import FrontPagePanel
from ui.login_page import LoginPagePanel
from ui.onboarding_wizard import show_tenant_onboarding_if_needed
from ui.platform_launcher import PlatformLauncherPanel
from ui.nav_icons import nav_item_icon, section_accent, section_icon
from ui.sidebar_nav import NavItemDef, NavSectionDef, SidebarNavigator, create_scrollable_nav_area
from ui.tenant_admin_panel import TenantAdminPanel
from ui.payroll_settings_panel import PayrollSettingsPanel
from ui.group_settings_panel import GroupSettingsPanel
from ui.org_admin_panel import OrgAdminPanel
from ui.user_permissions_panel import UserPermissionsPanel
from ui.upload_confirm_dialog import UploadConfirmDialog, suggest_upload_scope
from validator import PayrollValidationError

_brand = APP_CONFIG.brand


def _open_path(path: Path) -> None:
    if not path.exists():
        messagebox.showwarning("파일 없음", "요청한 파일을 찾을 수 없습니다.")
        return
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except OSError:
        subprocess.run(["explorer", str(path)], check=False)


class PayrollDashboard(tk.Tk):
    """월별 급여 관리 대시보드."""

    def __init__(self) -> None:
        from core.paths import initialize_runtime_paths

        initialize_runtime_paths()
        super().__init__()
        self.title(_brand.product_name)
        self.geometry(WINDOW_DEFAULT)
        self.minsize(*WINDOW_MIN)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        load_user_theme()
        self.configure(bg=COLORS["bg"])

        # Launcher panels branch on is_logged_in() at build time — restore session first.
        try_restore_session()

        self._current_page = tk.StringVar(value="login")
        self._active_platform: str | None = None
        self._selected_period = tk.StringVar()
        self._range_enabled = tk.BooleanVar(value=False)
        self._range_from = tk.StringVar(value="")
        self._range_to = tk.StringVar(value="")
        self._payroll_scopes: list[PayrollScope] = []
        self._period_choices: list[str] = []
        self._period_choice_scope_keys: list[str] = []
        self._refresh_job: str | None = None
        self._last_process_info: dict | None = None
        self._brand_photo_refs: list[tk.PhotoImage] = []
        self.workflow_hub_panel: WorkflowHubPanel | None = None
        self.maintenance_hub_panel: ModuleHubPanel | None = None
        self.bidding_hub_panel: ModuleHubPanel | None = None
        self.accounting_hub_panel: ModuleHubPanel | None = None
        self.recruitment_hub_panel: ModuleHubPanel | None = None
        self.kpi_hub_panel: object | None = None
        self._last_logged_in: bool | None = None
        self._theme_refreshing = False
        self._nav_active_override: str | None = None
        self._invoice_busy = False
        self._month_records_cache: dict[str, list] = {}

        self._setup_styles()
        self._build_layout()
        install_global_wheel(self)
        self._refresh_period_list()
        self._route_initial_page()
        add_session_listener(self._apply_login_visibility)
        self._apply_login_visibility()
        add_locale_listener(self._on_locale_changed)
        add_theme_listener(self._on_theme_changed)
        self.after(1500, self._refresh_stale_payroll_outputs)
        self.after(800, self._schedule_update_check)

    def _auth_public_page_keys(self) -> frozenset[str]:
        """로그인 전에만 허용되는 전체 화면."""
        return frozenset({"login", "front"})

    def _route_initial_page(self) -> None:
        if is_logged_in():
            self.show_page("launcher")
        elif self._login_gate_enabled():
            self.show_page("login")
        else:
            self.show_page("launcher")

    def _schedule_update_check(self) -> None:
        if not should_check_updates():
            return

        def worker() -> None:
            result = check_for_update()
            if result.has_update:
                self.after(0, lambda: self._prompt_update(result))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_stale_payroll_outputs(self) -> None:
        """산출 기준 변경 시 저장 청구서로 급여대장·명세서·지급내역을 자동 갱신."""

        def worker() -> None:
            try:
                from services.payroll_output_refresh import refresh_stale_payroll_outputs

                result = refresh_stale_payroll_outputs(interactive_parent=None)
            except Exception:
                return
            refreshed = result.get("refreshed") or []
            if not refreshed:
                return

            def _done() -> None:
                self._refresh_period_list()
                page = self._current_page.get()
                if page in self._payroll_page_keys:
                    self.show_page(page)

            self.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _prompt_update(self, result: UpdateCheckResult) -> None:
        if not result.manifest:
            return
        msg = format_update_message(result)
        if result.manifest.mandatory:
            ok = messagebox.askokcancel("필수 업데이트", msg)
            if not ok:
                self.destroy()
                return
        elif not messagebox.askyesno("업데이트", msg):
            return
        self._run_update(result)

    def _run_update(self, result: UpdateCheckResult) -> None:
        manifest = result.manifest
        if not manifest:
            return
        wait = tk.Toplevel(self)
        wait.title("업데이트")
        wait.geometry("360x120")
        wait.transient(self)
        wait.grab_set()
        tk.Label(wait, text="업데이트 파일을 받는 중입니다…", font=("맑은 고딕", 10)).pack(expand=True)
        wait.update_idletasks()

        def worker() -> None:
            try:
                installer = download_update(manifest)
                self.after(0, lambda: (wait.destroy(), apply_update(installer, manifest=manifest)))
            except Exception as exc:
                self.after(0, lambda: (wait.destroy(), messagebox.showerror("업데이트 실패", friendly_error(exc))))

        threading.Thread(target=worker, daemon=True).start()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Main.TFrame", background=COLORS["bg"])
        style.configure("Content.TFrame", background=COLORS["bg"])
        style.configure("Header.TFrame", background=COLORS["header_bg"])
        style.configure(
            "Title.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=FONT_TITLE,
        )
        style.configure(
            "HeaderTitle.TLabel",
            background=COLORS["header_bg"],
            foreground=COLORS["text"],
            font=FONT_TITLE,
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["muted"],
            font=FONT_SUBTITLE,
        )
        style.configure(
            "HeaderSubtitle.TLabel",
            background=COLORS["header_bg"],
            foreground=COLORS["muted"],
            font=FONT_SUBTITLE,
        )
        style.configure("Treeview", rowheight=32, font=FONT_BODY)
        style.configure(
            "Treeview.Heading",
            font=(FONT, 10, "bold"),
            background=COLORS["table_head"],
            foreground=COLORS["table_head_fg"],
        )
        style.map("Treeview.Heading", background=[("active", COLORS["accent_hover"])])
        style.configure("TCombobox", font=FONT_BODY, padding=4)
        style.configure("TButton", font=FONT_BODY, padding=(12, 6))
        style.configure("TLabelframe", font=(FONT, 10, "bold"))
        style.configure("TLabelframe.Label", foreground=COLORS["text"])

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 사이드바 (밝은 배경 → COSS 로고 색상과 조화) ---
        self._sidebar_wrap = tk.Frame(self, bg=COLORS["sidebar_border"], width=SIDEBAR_WIDTH + 1)
        self._sidebar_wrap.grid(row=0, column=0, sticky="ns")
        self._sidebar_wrap.grid_propagate(False)

        self._sidebar = tk.Frame(self._sidebar_wrap, bg=COLORS["sidebar"], width=SIDEBAR_WIDTH)
        self._sidebar.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sidebar = self._sidebar

        self._sidebar_divider = tk.Frame(sidebar, bg=COLORS.get("sidebar_border", COLORS["border"]), height=1)
        self._sidebar_divider.pack(fill=tk.X, padx=14, pady=(14, 6))

        self._nav_buttons: dict[str, object] = {}
        self._payroll_page_keys = (
            "home",
            "archive",
            "summary",
            "monthly_report",
            "reports",
            "settings",
        )
        self._page_to_section: dict[str, str] = {}

        nav_host, _nav_canvas = create_scrollable_nav_area(sidebar)
        self._nav_host = nav_host

        self._sidebar_nav = SidebarNavigator(self._nav_host)
        self._sidebar_nav.build_sections(self._build_sidebar_sections())
        self._nav_buttons = self._sidebar_nav.nav_buttons
        self._page_to_section = self._build_page_section_map()

        self._sidebar_footer = tk.Frame(sidebar, bg=COLORS["sidebar"])
        self._sidebar_footer.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 14))
        footer = self._sidebar_footer
        tk.Frame(footer, bg=COLORS.get("sidebar_border", COLORS["border"]), height=1).pack(
            fill=tk.X, pady=(0, 10)
        )
        tk.Label(
            footer,
            text=app_version_label(),
            bg=COLORS["sidebar"],
            fg=COLORS.get("nav_accent", COLORS["sidebar_footer"]),
            font=(FONT, 8, "bold"),
        ).pack(anchor=tk.W)
        self._footer_brand_label = tk.Label(
            footer,
            text=app_window_title(),
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_footer"],
            font=(FONT, 8),
        )
        self._footer_brand_label.pack(anchor=tk.W, pady=(4, 0))

        # --- 메인 ---
        self.main = ttk.Frame(self, style="Main.TFrame", padding=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self._header_shell = tk.Frame(self.main, bg=COLORS["header_border"])
        self._header_shell.grid(row=0, column=0, sticky="ew")
        self._header_shell.grid_columnconfigure(0, weight=1)

        header_inner = tk.Frame(self._header_shell, bg=COLORS["header_bg"])
        header_inner.pack(fill=tk.X)
        self._header_inner = header_inner

        self.header = ttk.Frame(header_inner, padding=(28, 20, 28, 16), style="Header.TFrame")
        self.header.pack(fill=tk.X)

        tk.Frame(self._header_shell, bg=COLORS["header_border"], height=1).pack(fill=tk.X)

        self.header.grid_columnconfigure(0, weight=1)

        title_box = ttk.Frame(self.header, style="Header.TFrame")
        title_box.grid(row=0, column=0, sticky=tk.W)

        title_row = ttk.Frame(title_box, style="Header.TFrame")
        title_row.pack(anchor=tk.W)

        self._page_accent_bar = tk.Frame(title_row, width=4, bg=COLORS["accent"], height=36)
        self._page_accent_bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        title_text = ttk.Frame(title_row, style="Header.TFrame")
        title_text.pack(side=tk.LEFT)

        self.page_breadcrumb = ttk.Label(
            title_text, text="", style="HeaderSubtitle.TLabel", font=(FONT, 9)
        )
        self.page_breadcrumb.pack(anchor=tk.W)
        self.page_title = ttk.Label(title_text, text="", style="HeaderTitle.TLabel")
        self.page_title.pack(anchor=tk.W)
        self.page_subtitle = ttk.Label(title_text, text="", style="HeaderSubtitle.TLabel")
        self.page_subtitle.pack(anchor=tk.W, pady=(4, 0))

        toolbar = ttk.Frame(self.header, style="Header.TFrame")
        toolbar.grid(row=0, column=1, sticky=tk.E)
        self._period_toolbar_label = ttk.Label(
            toolbar, text="급여 대상", font=(FONT, 10, "bold")
        )
        self._global_period_combo = ttk.Combobox(
            toolbar,
            state="disabled",
            width=36,
            font=FONT_BODY,
        )
        self._global_period_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_scope_combo_changed())
        self._period_refresh_btn = ttk.Button(
            toolbar, text="새로고침", command=self._on_period_refresh, width=10
        )

        # 기간 범위(요약 화면에서 사용): 2026-01 ~ 2026-05
        self._range_toggle = ttk.Checkbutton(
            toolbar,
            text="기간 범위",
            variable=self._range_enabled,
            command=self._on_range_toggle,
        )
        self._range_from_combo = ttk.Combobox(toolbar, state="disabled", width=10, font=FONT_BODY)
        self._range_to_combo = ttk.Combobox(toolbar, state="disabled", width=10, font=FONT_BODY)
        self._range_sep = ttk.Label(toolbar, text=" ~ ", font=FONT_BODY)
        self._range_from_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_range_changed())
        self._range_to_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_range_changed())

        self._period_toolbar_pages = frozenset(
            {"archive", "summary", "monthly_report", "reports"}
        )

        self._org_filter_wrap = ttk.Frame(toolbar, style="Main.TFrame")
        self._org_filter = OrgFilterBar(
            self._org_filter_wrap,
            on_change=lambda _sel: self._on_org_filter_changed(),
            show_hint=False,
        )
        self._org_filter.pack(side=tk.LEFT)
        self._org_pages = frozenset({"archive", "summary", "monthly_report", "reports"})

        self.content = ttk.Frame(self.main, padding=(20, 4, 20, 16), style="Content.TFrame")
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages: dict[str, ttk.Frame] = {}
        for key in (
            "front",
            "login",
            "launcher",
            "tenant",
            "permissions",
            "org",
            "group_settings",
            "home",
            "archive",
            "summary",
            "monthly_report",
            "reports",
            "settings",
            "workflow",
            "hr",
            "recruitment",
            "kpi",
            "maintenance",
            "bidding",
            "accounting",
        ):
            frame = ttk.Frame(self.content)
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            self.pages[key] = frame

        self._build_login_page()
        try:
            self._build_front_page()
        except Exception:
            traceback.print_exc()
        self._build_launcher_page()
        self._build_tenant_page()
        self._build_permissions_page()
        self._build_org_page()
        self._build_group_settings_page()
        self._build_home_page()
        self._build_archive_page()
        self._build_summary_page()
        self._build_monthly_report_page()
        self._build_reports_page()
        self._build_settings_page()
        self._build_workflow_page()
        self._build_hr_page()
        self._build_recruitment_page()
        self._build_kpi_page()
        self._build_maintenance_page()
        self._build_bidding_page()
        self._build_accounting_page()

    def _build_sidebar_sections(self) -> tuple[NavSectionDef, ...]:
        platform_items = (
            NavItemDef(
                "launcher",
                t("nav.home", default="플랫폼 홈"),
                lambda: self.show_page("launcher"),
                icon=nav_item_icon("launcher"),
            ),
            NavItemDef(
                "tenant",
                t("nav.tenant", default="법인 관리"),
                lambda: self.show_page("tenant"),
                icon=nav_item_icon("tenant"),
            ),
            NavItemDef(
                "permissions",
                t("nav.permissions", default="사용자 권한"),
                lambda: self.show_page("permissions"),
                icon=nav_item_icon("permissions"),
            ),
            NavItemDef(
                "org",
                t("nav.org", default="조직 · 계정"),
                lambda: self.show_page("org"),
                icon=nav_item_icon("org"),
            ),
            NavItemDef(
                "group_settings",
                t("nav.group_settings", default="그룹 · 결재 설정"),
                lambda: self.show_page("group_settings"),
                icon=nav_item_icon("group_settings"),
            ),
            NavItemDef(
                "ai",
                t("nav.personal_ai", default="Personal AI"),
                lambda: open_ai_assistant(self),
                icon=nav_item_icon("ai"),
            ),
        )
        sections: list[NavSectionDef] = [
            NavSectionDef(
                "platform",
                t("nav.platform", default="플랫폼"),
                platform_items,
                default_expanded=True,
                icon=section_icon("platform"),
                accent=section_accent("platform"),
            ),
        ]

        wf_plat = get_platform("workflow")
        gw_items: list[NavItemDef] = []
        if wf_plat and wf_plat.enabled:
            gw_items.append(
                NavItemDef(
                    "workflow",
                    tf("workflow", "title", "전자결재"),
                    command=lambda: self._open_platform("workflow"),
                    enabled=True,
                    icon=nav_item_icon("workflow"),
                )
            )
        gw_items.append(
            NavItemDef(
                "org",
                t("nav.org", default="조직도"),
                lambda: self.show_page("org"),
                icon=nav_item_icon("org"),
            )
        )
        sections.append(
            NavSectionDef(
                "groupware",
                "그룹웨어",
                tuple(gw_items),
                default_expanded=True,
                icon="◎",
                accent="#2563EB",
                status_label="GW 대응",
            )
        )
        payroll_nav = [
            ("home", t("nav.payroll.home", default="급여 산출")),
            ("archive", t("nav.payroll.archive", default="월별 자료함")),
            ("summary", t("nav.payroll.summary", default="월별 요약")),
            ("monthly_report", t("nav.payroll.monthly_report", default="월별 보고")),
            ("reports", t("nav.payroll.reports", default="급여 보고")),
            ("settings", t("nav.payroll.settings", default="급여 설정")),
        ]
        payroll_plat = get_platform("payroll")
        payroll_items = tuple(
            NavItemDef(
                key,
                label,
                command=lambda k=key: self._open_payroll_page(k),
                enabled=True,
                icon=nav_item_icon(key),
            )
            for key, label in payroll_nav
        )
        sections.append(
            NavSectionDef(
                "payroll",
                tf("payroll", "title", payroll_plat.title if payroll_plat else "급여"),
                payroll_items,
                default_expanded=True,
                icon=payroll_plat.icon_glyph if payroll_plat else section_icon("payroll"),
                accent=payroll_plat.accent if payroll_plat else section_accent("payroll"),
                status_label=payroll_plat.status_label if payroll_plat else "",
            )
        )

        for plat in PLATFORMS:
            if plat.id in ("payroll", "workflow") or not plat.enabled or not plat.entry_page:
                continue
            if plat.nav_tabs:
                plat_items = tuple(
                    NavItemDef(
                        f"{plat.id}_{tab_id}",
                        label,
                        command=lambda pid=plat.id, tid=tab_id: self._open_platform_tab(pid, tid),
                        enabled=True,
                        icon=nav_item_icon(f"{plat.id}_{tab_id}"),
                    )
                    for tab_id, label in plat.nav_tabs
                )
            else:
                plat_items = (
                    NavItemDef(
                        plat.id,
                        tf(plat.id, "title", plat.title),
                        command=lambda pid=plat.id: self._open_platform(pid),
                        enabled=True,
                        icon=nav_item_icon(plat.id),
                    ),
                )
            sections.append(
                NavSectionDef(
                    plat.id,
                    tf(plat.id, "title", plat.title),
                    plat_items,
                    default_expanded=False,
                    status_label=plat.status_label,
                    icon=plat.icon_glyph,
                    accent=plat.accent,
                )
            )
        return tuple(sections)

    def _rebuild_sidebar_nav(self) -> None:
        """언어 변경 시 사이드바 섹션·라벨을 재생성합니다."""
        host = getattr(self, "_nav_host", None)
        if host is None:
            return
        for w in host.winfo_children():
            w.destroy()
        self._sidebar_nav = SidebarNavigator(host)
        self._sidebar_nav.build_sections(self._build_sidebar_sections())
        self._nav_buttons = self._sidebar_nav.nav_buttons
        self._page_to_section = self._build_page_section_map()
        self._apply_login_visibility()
        self._highlight_nav(self._current_page.get())

    def _on_locale_changed(self, _locale: str) -> None:
        if hasattr(self, "_appearance_panel"):
            self._appearance_panel.refresh_i18n()
        self._rebuild_sidebar_nav()
        self.show_page(self._current_page.get())

    def _on_theme_selected(self, theme_id: str) -> None:
        set_saved_theme_id(theme_id)
        apply_theme(theme_id)

    def _on_theme_changed(self, _theme_id: str) -> None:
        if self._theme_refreshing:
            return
        self._theme_refreshing = True
        try:
            self._setup_styles()
            self._apply_shell_colors()
            self._rebuild_sidebar_nav()
            self._recolor_settings_bars()
            self._remount_launcher_page()
            if self._current_page.get() == "login":
                self._build_login_page()
            page = self._current_page.get()
            if page == "workflow":
                self.workflow_hub_panel = None
            elif page == "maintenance":
                self.maintenance_hub_panel = None
            elif page == "bidding":
                self.bidding_hub_panel = None
            elif page == "accounting":
                self.accounting_hub_panel = None
            elif page == "hr":
                self.hr_hub_panel = None
            elif page == "recruitment":
                self.recruitment_hub_panel = None
            elif page == "kpi":
                self.kpi_hub_panel = None
            self.show_page(page)
        finally:
            self._theme_refreshing = False

    def _apply_shell_colors(self) -> None:
        self.configure(bg=COLORS["bg"])
        if hasattr(self, "_sidebar_wrap"):
            self._sidebar_wrap.configure(bg=COLORS["sidebar_border"])
        if hasattr(self, "_sidebar"):
            self._sidebar.configure(bg=COLORS["sidebar"])
        if hasattr(self, "_sidebar_divider"):
            self._sidebar_divider.configure(bg=COLORS["border"])
        if hasattr(self, "_sidebar_footer"):
            self._sidebar_footer.configure(bg=COLORS["sidebar"])
            for w in self._sidebar_footer.winfo_children():
                if isinstance(w, tk.Label):
                    w.configure(bg=COLORS["sidebar"], fg=COLORS["sidebar_footer"])
        if hasattr(self, "_header_shell"):
            self._header_shell.configure(bg=COLORS["header_border"])
        if hasattr(self, "_header_inner"):
            self._header_inner.configure(bg=COLORS["header_bg"])
        if hasattr(self, "_page_accent_bar"):
            self._page_accent_bar.configure(bg=COLORS["accent"])

    def _recolor_settings_bars(self) -> None:
        panel = getattr(self, "_appearance_panel", None)
        if panel is not None:
            try:
                panel.refresh_card_style()
            except tk.TclError:
                pass

    def _build_page_section_map(self) -> dict[str, str]:
        mapping = {
            "front": "platform",
            "login": "platform",
            "launcher": "platform",
            "tenant": "platform",
            "permissions": "platform",
            "org": "platform",
            "group_settings": "platform",
            "ai": "platform",
        }
        for key in self._payroll_page_keys:
            mapping[key] = "payroll"
        mapping["workflow"] = "workflow"
        for plat in PLATFORMS:
            if plat.enabled and plat.entry_page and plat.id not in ("payroll", "workflow"):
                mapping[plat.entry_page] = plat.id
                for tab_id, _label in plat.nav_tabs:
                    mapping[f"{plat.id}_{tab_id}"] = plat.id
        return mapping

    def _highlight_nav(self, active: str) -> None:
        key = self._nav_active_override or active
        if key in self._nav_buttons:
            nav_key = key
        elif active in self._nav_buttons:
            nav_key = active
        elif active in ("maintenance", "bidding", "accounting", "hr", "recruitment", "kpi"):
            plat = get_platform(active)
            if plat and plat.nav_tabs:
                nav_key = f"{active}_{plat.nav_tabs[0][0]}"
            else:
                nav_key = active
        else:
            nav_key = key
        self._sidebar_nav.set_active(nav_key if nav_key in self._nav_buttons else None)
        self._sidebar_nav.expand_for_page(nav_key, self._page_to_section)
        self._nav_active_override = None

    def _login_gate_enabled(self) -> bool:
        return APP_CONFIG.require_login

    def _coerce_page_for_session(self, page: str) -> str:
        """미로그인 시 플랫폼 홈·급여 등 모든 화면을 로그인으로 보냅니다."""
        if self._login_gate_enabled() and not is_logged_in():
            if page not in self._auth_public_page_keys():
                return "login"
        return page

    def _payroll_access_allowed(self) -> bool:
        if not self._login_gate_enabled():
            return True
        return is_logged_in()

    def _gated_page_keys(self) -> frozenset[str]:
        return frozenset(
            {
                *self._payroll_page_keys,
                "tenant",
                "permissions",
                "org",
                "group_settings",
                "ai",
                "workflow",
                "hr",
                "recruitment",
                "kpi",
                "maintenance",
                "bidding",
                "accounting",
            }
        )

    def _nav_platform_for_key(self, key: str) -> str | None:
        if key in self._payroll_page_keys:
            return "payroll"
        if key == "workflow":
            return "workflow"
        if key == "maintenance" or key.startswith("maintenance_"):
            return "maintenance"
        if key == "bidding" or key.startswith("bidding_"):
            return "bidding"
        if key == "accounting" or key.startswith("accounting_"):
            return "accounting"
        if key == "hr" or key.startswith("hr_"):
            return "hr"
        if key == "recruitment" or key.startswith("recruitment_"):
            return "recruitment"
        if key == "kpi" or key.startswith("kpi_"):
            return "kpi"
        return None

    def _user_can_access_nav(self, key: str) -> bool:
        if not is_logged_in():
            return False
        if key == "org" or key == "group_settings":
            return can_manage_org()
        if key == "tenant":
            return can_manage_tenant_settings()
        if key == "permissions":
            return has_permission(PERM_USER_ROLES) or can_manage_org()
        if key == "settings":
            return can_access_payroll_settings()
        plat = self._nav_platform_for_key(key)
        if plat:
            return can_access_platform(plat)
        return True

    def _apply_login_visibility(self) -> None:
        """로그인 전에는 로그인 화면만 사용 가능."""
        if not self._login_gate_enabled():
            self._update_shell_chrome()
            return

        logged_in = is_logged_in()
        prev = self._last_logged_in
        if prev is not None and prev != logged_in:
            load_user_theme()
        self._last_logged_in = logged_in
        coming_soon = self._sidebar_nav.coming_soon_keys
        for key, btn in self._nav_buttons.items():
            if key in coming_soon:
                continue
            if not logged_in:
                enabled = False
            else:
                enabled = self._user_can_access_nav(key)
            btn.configure(state=tk.NORMAL if enabled else tk.DISABLED)

        self._refresh_period_list()
        if not logged_in:
            current = self._current_page.get()
            if current not in self._auth_public_page_keys():
                self.show_page("login")

        self._update_shell_chrome()
        self._refresh_sidebar_user_context()

    def _update_shell_chrome(self) -> None:
        """로그인 전 인증 화면에서는 사이드바를 숨깁니다."""
        if not hasattr(self, "_sidebar_wrap") or not hasattr(self, "main"):
            return
        if not self._login_gate_enabled():
            self._sidebar_wrap.grid(row=0, column=0, sticky="ns")
            self.main.grid(row=0, column=1, sticky="nsew")
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            return

        logged_in = is_logged_in()
        page = self._current_page.get()
        auth_shell = not logged_in and page in ("login", "front")

        if auth_shell:
            self._sidebar_wrap.grid_remove()
            self.main.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
        else:
            self._sidebar_wrap.grid(row=0, column=0, sticky="ns")
            self.main.grid(row=0, column=1, sticky="nsew")
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)

    def _refresh_sidebar_user_context(self) -> None:
        pass

    def _open_platform(self, platform_id: str) -> None:
        if self._login_gate_enabled() and not is_logged_in():
            messagebox.showinfo(
                "로그인 필요",
                "업무 플랫폼을 이용하려면 로그인해 주세요.",
                parent=self,
            )
            return
        plat = get_platform(platform_id)
        if not plat:
            return
        if not plat.enabled or not plat.entry_page:
            messagebox.showinfo(
                "준비 중",
                f"「{plat.title}」 플랫폼은 현재 준비 중입니다.\n오픈 후 이용하실 수 있습니다.",
                parent=self,
            )
            return
        try:
            from core.org_access import require_platform_access

            require_platform_access(platform_id)
        except PermissionError as exc:
            messagebox.showwarning("접근 제한", str(exc), parent=self)
            return
        self._active_platform = platform_id
        self.show_page(plat.entry_page)

    def _open_platform_tab(self, platform_id: str, tab_id: str) -> None:
        if self._login_gate_enabled() and not is_logged_in():
            messagebox.showinfo(
                "로그인 필요",
                "업무 플랫폼을 이용하려면 로그인해 주세요.",
                parent=self,
            )
            return
        plat = get_platform(platform_id)
        if not plat or not plat.enabled or not plat.entry_page:
            return
        try:
            from core.org_access import require_platform_access

            require_platform_access(platform_id)
        except PermissionError as exc:
            messagebox.showwarning("접근 제한", str(exc), parent=self)
            return
        self._active_platform = platform_id
        self._nav_active_override = f"{platform_id}_{tab_id}"
        self.show_page(plat.entry_page)
        panel = getattr(self, f"{platform_id}_hub_panel", None)
        if panel is not None and hasattr(panel, "select_tab"):
            try:
                panel.select_tab(tab_id)
            except Exception as exc:
                messagebox.showerror(
                    "화면 오류",
                    f"「{tab_id}」 탭을 열지 못했습니다.\n{exc}",
                    parent=self,
                )

    def _open_payroll_page(self, page: str) -> None:
        if not self._payroll_access_allowed():
            messagebox.showinfo(
                "로그인 필요",
                "급여 기능은 로그인 후 이용할 수 있습니다.",
                parent=self,
            )
            return
        try:
            from core.org_access import require_platform_access

            require_platform_access("payroll")
            if page == "settings":
                from core.org_access import can_access_payroll_settings

                if not can_access_payroll_settings():
                    messagebox.showwarning(
                        "접근 제한",
                        "급여 설정은 팀장 이상 또는 재무·관리자만 변경할 수 있습니다.",
                        parent=self,
                    )
                    return
        except PermissionError as exc:
            messagebox.showwarning("접근 제한", str(exc), parent=self)
            return
        self._active_platform = "payroll"
        self.show_page(page)

    def _build_launcher_page(self) -> None:
        self._mount_launcher_page()

    def _build_front_page(self) -> None:
        p = self.pages["front"]
        for w in p.winfo_children():
            w.destroy()
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        FrontPagePanel(
            p,
            on_login=lambda: self.show_page("login"),
            on_continue=(lambda: self.show_page("launcher")) if not APP_CONFIG.require_login else None,
        ).grid(row=0, column=0, sticky="nsew")

    def _build_login_page(self) -> None:
        if not hasattr(self, "pages") or "login" not in self.pages:
            return
        p = self.pages["login"]
        for w in p.winfo_children():
            w.destroy()
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        try:
            LoginPagePanel(
                p,
                on_success=self._on_login_success,
            ).grid(row=0, column=0, sticky="nsew")
        except Exception:
            traceback.print_exc()
            tk.Label(
                p,
                text="로그인 화면을 불러오지 못했습니다. 프로그램을 다시 시작해 주세요.",
                bg=COLORS["bg"],
                fg=COLORS["text"],
                font=(FONT, 11),
                wraplength=480,
                justify=tk.LEFT,
            ).grid(row=0, column=0, padx=32, pady=32, sticky="nw")

    def _mount_launcher_page(self) -> None:
        p = self.pages["launcher"]
        for w in p.winfo_children():
            w.destroy()
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.launcher_panel = PlatformLauncherPanel(
            p,
            on_open=self._open_platform,
            host=self,
            on_login=lambda: self.show_page("login"),
            on_logout=self._do_logout_to_login,
            on_theme_select=self._on_theme_selected,
            on_open_payroll_page=self._open_payroll_page,
            on_open_compliance_docs=lambda: self._open_platform_tab("hr", "compliance_docs"),
        )
        self.launcher_panel.pack(fill=tk.BOTH, expand=True)
        self.launcher_panel.keep_photos_on(self)
        self._appearance_panel = self.launcher_panel.appearance_panel

    def _remount_launcher_page(self) -> None:
        """테마·언어 변경 시 홈 배너·카드 색상을 현재 팔레트로 다시 그립니다."""
        if not hasattr(self, "pages") or "launcher" not in self.pages:
            return
        self._mount_launcher_page()

    def _build_tenant_page(self) -> None:
        p = self.pages["tenant"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.tenant_admin_panel = TenantAdminPanel(
            p,
            on_tenant_changed=self.refresh_tenant_branding,
        )
        self.tenant_admin_panel.grid(row=0, column=0, sticky="nsew")

    def _build_permissions_page(self) -> None:
        p = self.pages["permissions"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.user_permissions_panel = UserPermissionsPanel(p)
        self.user_permissions_panel.grid(row=0, column=0, sticky="nsew")

    def _build_org_page(self) -> None:
        p = self.pages["org"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.org_admin_panel = OrgAdminPanel(p, on_changed=self._apply_login_visibility)
        self.org_admin_panel.grid(row=0, column=0, sticky="nsew")

    def _build_group_settings_page(self) -> None:
        p = self.pages["group_settings"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.group_settings_panel = GroupSettingsPanel(p, on_changed=self._apply_login_visibility)
        self.group_settings_panel.grid(row=0, column=0, sticky="nsew")

    def _on_launcher_session_changed(self) -> None:
        self._refresh_period_list()

    def _on_login_success(self) -> None:
        def _enter_launcher() -> None:
            self._mount_launcher_page()
            self.refresh_tenant_branding_after_login()
            self.show_page("launcher")

        if show_tenant_onboarding_if_needed(self, on_complete=_enter_launcher):
            return
        _enter_launcher()

    def refresh_tenant_branding_after_login(self) -> None:
        """로그인 후 세션 테넌트 기준 UI 갱신 (사이드바·런처)."""
        self.title(app_window_title())
        if hasattr(self, "_footer_brand_label"):
            self._footer_brand_label.configure(text=app_window_title())
        self._apply_login_visibility()

    def _do_logout_to_login(self) -> None:
        logout(clear_saved=True)
        self._build_login_page()
        self.show_page("login")

    def refresh_tenant_branding(self) -> None:
        """활성 고객사 변경 후 로고·회사명 UI 갱신."""
        clear_session_for_tenant_change()
        self.title(app_window_title())
        if hasattr(self, "_footer_brand_label"):
            self._footer_brand_label.configure(text=app_window_title())

        try_restore_session()
        if hasattr(self, "launcher_panel"):
            self.launcher_panel.destroy()
        self._mount_launcher_page()
        self._route_initial_page()

        if self._current_page.get() == "tenant" and hasattr(self, "tenant_admin_panel"):
            self.tenant_admin_panel.refresh()

    def show_page(self, page: str) -> None:
        page = self._coerce_page_for_session(page)
        self._current_page.set(page)
        self._highlight_nav(page)
        for key, frame in self.pages.items():
            frame.tkraise() if key == page else None
        for key, frame in self.pages.items():
            if key == page:
                frame.tkraise()

        if page in ("front", "login", "launcher", "tenant", "permissions", "org", "group_settings"):
            self._header_shell.grid_remove()
        else:
            self._header_shell.grid()

        section_titles = {
            "platform": t("nav.platform", default="플랫폼"),
            "workflow": tf("workflow", "title", "업무 · 전자결재"),
            "payroll": tf("payroll", "title", "급여"),
        }
        for plat in PLATFORMS:
            section_titles[plat.id] = tf(plat.id, "title", plat.title)

        titles = {
            "front": ("", ""),
            "login": ("", ""),
            "launcher": ("", ""),
            "tenant": ("법인 관리", "Bitween 이용 법인·로고·아이디를 등록하고 활성 법인을 전환합니다."),
            "permissions": ("사용자 권한", "재무팀·관리자 권한을 설정합니다. 임원 급여는 재무팀만 조회할 수 있습니다."),
            "org": (
                "조직 · 계정",
                "조직도를 구성하고 팀·직위별 계정을 생성합니다. 팀별 플랫폼 접근 범위를 지정할 수 있습니다.",
            ),
            "group_settings": (
                "그룹 · 결재 설정",
                "법인·계열사, 결재선 템플릿, 구매~회계 연동 단계를 그룹 메인 계정에서 조정합니다.",
            ),
            "home": (
                "급여 산출",
                f"{company_name_line()} — 도급비 청구서 업로드로 급여대장·명세서·지급내역을 생성합니다.",
            ),
            "roster": (
                "직원 명부",
                "근로자 명부를 확인·수정합니다. 저장한 내용은 급여 산출 시 자동 반영됩니다.",
            ),
            "archive": (
                "월별 자료함",
                "급여·청구서·연차대장을 탐색합니다. 연차 마스터·휴가 신청은 「인사 · 노무」에서 관리합니다.",
            ),
            "summary": ("월별 요약", "선택한 계열사·사업장·급여월 기준 인원·급여·연차 현황입니다."),
            "monthly_report": (
                "월별 보고",
                "인도급 급여 요약 — 당월 KPI·연간(1~당월) 총급여 추이·전월 대비 차이를 확인하고 Excel로 저장합니다.",
            ),
            "reports": (
                "급여 보고",
                "계열사·사업장별 급여차이·무급 현황을 확인하고 보고서를 엽니다.",
            ),
            "settings": (
                t("pages.settings.title", default="급여 설정"),
                t(
                    "pages.settings.subtitle",
                    default="휴업수당 지급률·사업장별 월 기본근로시간(209 고정 / 청구서 근태 반영 등)을 설정합니다.",
                ),
            ),
            "workflow": (
                "업무 · 전자결재",
                "기안·근태·구매·지출결의, 결재, 실행업무, 사업장·임원 대시보드, 월마감 (Bitween ERP MVP).",
            ),
            "maintenance": (
                "정비 사업부",
                "작업지시·설비·예방정비·부품재고 (Fiix·SAP PM형 CMMS MVP).",
            ),
            "bidding": (
                "입찰",
                "공고·견적·제출일정·낙찰 이력 (나라장터·Procore형 MVP).",
            ),
            "accounting": (
                "회계 · 경리",
                "전표·세무일정·자금계획·결산 보고 (더존·SAP FI형 MVP).",
            ),
            "hr": (
                "인사 · 노무",
                "직원 명부, 연차·휴가, 근태, 근로계약, 증명서, 노무·징계, 입·퇴사 (Bitween HR MVP).",
            ),
            "recruitment": (
                "채용 · 마당",
                "법인 채용공고·플랫폼 채용마당·지원 접수·고용24·SNS 채널 상태 (API 연동 준비).",
            ),
            "kpi": (
                "KPI · 경영",
                "법인·사업장·개인 KPI · 경영 지도 · 손익 · 이슈 알림 (회계·급여·인사 연동 예정).",
            ),
        }
        page_title, page_sub = titles.get(page, ("", ""))
        section_id = self._page_to_section.get(page, "")
        section_title = section_titles.get(section_id, "")
        if section_title and page_title:
            self.page_breadcrumb.configure(text=f"{section_title}  ›")
        else:
            self.page_breadcrumb.configure(text="")
        self.page_title.configure(text=page_title)
        self.page_subtitle.configure(text=page_sub)
        plat_for_section = get_platform(section_id) if section_id else None
        if section_id == "platform":
            accent = section_accent("platform")
        elif plat_for_section:
            accent = plat_for_section.accent
        elif section_id:
            accent = section_accent(section_id)
        else:
            accent = COLORS["accent"]
        if hasattr(self, "_page_accent_bar"):
            self._page_accent_bar.configure(bg=accent)
        self._toggle_period_toolbar(page in self._period_toolbar_pages)
        self._toggle_org_filter(page in self._org_pages)
        self._refresh_org_filter_options()

        if page in self._payroll_page_keys and page != "launcher":
            self._active_platform = "payroll"
        elif page == "hr":
            self._active_platform = "hr"

        if page == "launcher":
            if hasattr(self, "_appearance_panel") and self._appearance_panel is not None:
                self._appearance_panel.set_theme_selection(get_current_theme_id())
                self._appearance_panel.refresh_i18n()
        elif page == "home":
            self._refresh_home_roster_hint()
        elif page == "hr":
            self._ensure_module_hub("hr")
        elif page == "archive":
            self._refresh_archive()
        elif page == "summary":
            self._refresh_summary()
        elif page == "monthly_report":
            self._refresh_monthly_report()
        elif page == "reports":
            self._refresh_reports()
        elif page == "settings":
            self.payroll_settings_panel.refresh()
        elif page == "tenant":
            self.tenant_admin_panel.refresh()
        elif page == "permissions":
            self.user_permissions_panel.refresh()
        elif page == "org":
            self.org_admin_panel.refresh()
        elif page == "group_settings":
            self.group_settings_panel.refresh()
        elif page == "workflow":
            self._ensure_workflow_hub()
            if self.workflow_hub_panel is not None:
                self.workflow_hub_panel.refresh()
        elif page == "maintenance":
            self._ensure_module_hub("maintenance")
        elif page == "bidding":
            self._ensure_module_hub("bidding")
        elif page == "accounting":
            self._ensure_module_hub("accounting")
        elif page == "recruitment":
            self._ensure_module_hub("recruitment")
        elif page == "kpi":
            self._ensure_kpi_hub()

        self._update_shell_chrome()

    def _ensure_kpi_hub(self) -> None:
        panel = getattr(self, "kpi_hub_panel", None)
        try:
            if panel is not None and not panel.winfo_exists():
                panel = None
        except tk.TclError:
            panel = None
        if panel is None:
            self._build_kpi_page()
            panel = getattr(self, "kpi_hub_panel", None)
        if panel is not None and hasattr(panel, "refresh"):
            panel.refresh()

    def _ensure_module_hub(self, platform_id: str) -> None:
        attr = f"{platform_id}_hub_panel"
        panel = getattr(self, attr, None)
        try:
            if panel is not None and not panel.winfo_exists():
                panel = None
        except tk.TclError:
            panel = None
        if panel is None:
            builders = {
                "maintenance": self._build_maintenance_page,
                "bidding": self._build_bidding_page,
                "accounting": self._build_accounting_page,
                "hr": self._build_hr_page,
                "recruitment": self._build_recruitment_page,
            }
            builders[platform_id]()
            panel = getattr(self, attr, None)
        if panel is not None:
            panel.refresh()

    def _ensure_workflow_hub(self) -> None:
        """워크플로우 패널이 없거나 파괴된 경우 다시 생성합니다."""
        panel = getattr(self, "workflow_hub_panel", None)
        try:
            if panel is not None and panel.winfo_exists():
                return
        except tk.TclError:
            panel = None
        self._build_workflow_page()

    def _build_workflow_page(self) -> None:
        p = self.pages["workflow"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.workflow_hub_panel = WorkflowHubPanel(p, COLORS)
        self.workflow_hub_panel.grid(row=0, column=0, sticky="nsew")

    def _build_hr_page(self) -> None:
        p = self.pages["hr"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.hr_hub_panel = build_hr_hub(
            p,
            on_roster_saved=self._refresh_home_roster_hint,
        )
        self.hr_hub_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_recruitment_page(self) -> None:
        p = self.pages["recruitment"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.recruitment_hub_panel = build_recruitment_hub(p)
        self.recruitment_hub_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_kpi_page(self) -> None:
        p = self.pages["kpi"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.kpi_hub_panel = build_kpi_hub(p)
        self.kpi_hub_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_maintenance_page(self) -> None:
        p = self.pages["maintenance"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.maintenance_hub_panel = build_maintenance_hub(p)
        self.maintenance_hub_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_bidding_page(self) -> None:
        p = self.pages["bidding"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        self.bidding_hub_panel = build_bidding_hub(p)
        self.bidding_hub_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _build_accounting_page(self) -> None:
        p = self.pages["accounting"]
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)
        for child in p.winfo_children():
            child.destroy()
        banner = tk.Frame(p, bg="#EFF6FF")
        banner.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        tk.Label(
            banner,
            text="EDI 4대보험료: 급여 설정 → 「EDI 보험료 조회」에서 CSV·수동 등록 후 급여 반영",
            bg="#EFF6FF",
            fg="#1E40AF",
            font=(FONT, 9),
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=10, pady=8)
        tk.Button(
            banner,
            text="급여 설정 열기",
            bg="#2563EB",
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: self.show_page("settings"),
        ).pack(side=tk.RIGHT, padx=10, pady=6)
        self.accounting_hub_panel = build_accounting_hub(p)
        self.accounting_hub_panel.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

    def _selected_scope(self) -> PayrollScope | None:
        return PayrollScope.try_parse_key(self._selected_period.get())

    def _selected_month(self) -> str:
        """드롭다운에 표시된 급여월(YYYY-MM). scope 키가 저장돼 있어도 월 단위로 집계합니다."""
        scope = self._selected_scope()
        if scope:
            return scope.period
        raw = self._selected_period.get()
        if raw and "\x1f" in str(raw):
            parsed = PayrollScope.try_parse_key(raw)
            if parsed:
                return parsed.period
        return raw or ""

    def _on_scope_combo_changed(self) -> None:
        idx = self._global_period_combo.current()
        if 0 <= idx < len(self._period_choice_scope_keys):
            self._selected_period.set(self._period_choice_scope_keys[idx])
        self._on_period_changed()

    def _month_summary(self, period: str) -> MonthSummary:
        tid = session_tenant_id()
        sess = get_session()
        if tid and sess:
            from core.access_control import build_month_summary_secured

            return build_month_summary_secured(period, tid, session=sess)
        if tid:
            return build_month_summary_for_tenant(period, tid)
        return MonthSummary(period=period, files=[], has_output=False)

    def _refresh_period_list(self) -> None:
        tid = session_tenant_id()
        self._payroll_scopes = discover_scopes_for_tenant(tid) if tid else []
        for scope in self._payroll_scopes:
            ensure_scope_manifest(scope)

        # “월” 단위로 중복 제거해서 드롭다운을 단순화합니다.
        by_period: dict[str, list[PayrollScope]] = {}
        for s in self._payroll_scopes:
            by_period.setdefault(s.period, []).append(s)

        sel = self._org_selection()
        self._period_choices = []
        self._period_choice_scope_keys = []

        periods = sorted(by_period.keys(), reverse=True)
        if not periods:
            periods = sorted({s.period for s in discover_scopes()}, reverse=True)
            for period in periods:
                scopes_for_period = [s for s in discover_scopes() if s.period == period]
                if scopes_for_period:
                    chosen = sorted(scopes_for_period, key=lambda c: (c.affiliate, c.workplace))[0]
                    self._period_choices.append(period)
                    self._period_choice_scope_keys.append(chosen.key)
            labels = [format_period_display(p) for p in self._period_choices]
            if hasattr(self, "_global_period_combo"):
                self._global_period_combo.configure(
                    values=labels,
                    state="readonly" if labels else "disabled",
                )
            if hasattr(self, "_range_from_combo"):
                state = "readonly" if self._period_choices else "disabled"
                self._range_from_combo.configure(values=self._period_choices, state=state)
                self._range_to_combo.configure(values=self._period_choices, state=state)
            if self._period_choices:
                try:
                    idx = 0
                    self._global_period_combo.current(idx)
                    if len(self._period_choice_scope_keys) > idx:
                        self._selected_period.set(self._period_choice_scope_keys[idx])
                except Exception:
                    pass
            return

        for period in periods:
            candidates = by_period.get(period) or []

            def _matches(x: PayrollScope) -> bool:
                if sel.affiliate != ALL_LABEL and x.affiliate != sel.affiliate:
                    return False
                if sel.workplace != ALL_LABEL:
                    from core.org_config import scope_workplaces_match

                    if not scope_workplaces_match(sel.workplace, x.workplace):
                        return False
                return True

            chosen = next((c for c in candidates if _matches(c)), None)
            if not chosen:
                # org filter 매칭이 없으면 determinism용으로 정렬 후 첫 scope를 선택
                chosen = sorted(candidates, key=lambda c: (c.affiliate, c.workplace))[0] if candidates else None

            if chosen:
                self._period_choices.append(period)
                self._period_choice_scope_keys.append(chosen.key)

        labels = [format_period_display(p) for p in self._period_choices]
        if hasattr(self, "_global_period_combo"):
            self._global_period_combo.configure(
                values=labels,
                state="readonly" if labels else "disabled",
            )
        # 범위 콤보는 YYYY-MM 원값을 그대로 노출합니다.
        if hasattr(self, "_range_from_combo"):
            state = "readonly" if self._period_choices else "disabled"
            self._range_from_combo.configure(values=self._period_choices, state=state)
            self._range_to_combo.configure(values=self._period_choices, state=state)
        current = self._selected_scope()
        current_period = current.period if current else None
        if not current_period and self._last_process_info:
            scope = self._last_process_info.get("scope")
            if isinstance(scope, PayrollScope):
                current_period = scope.period

        if self._period_choices:
            try:
                idx = self._period_choices.index(current_period) if current_period else 0
            except ValueError:
                idx = 0
            self._global_period_combo.current(idx)
            if 0 <= idx < len(self._period_choice_scope_keys):
                self._selected_period.set(self._period_choice_scope_keys[idx])

        # 범위 기본값(최초 1회): 가장 오래된 ~ 가장 최근
        if self._period_choices and not (self._range_from.get() or self._range_to.get()):
            self._range_from.set(self._period_choices[-1])
            self._range_to.set(self._period_choices[0])
            try:
                self._range_from_combo.set(self._range_from.get())
                self._range_to_combo.set(self._range_to.get())
            except Exception:
                pass

    def _on_period_refresh(self) -> None:
        if not self._payroll_access_allowed():
            return
        self._refresh_period_list()
        self._refresh_active_page_data(force=True)

    def _refresh_active_page_data(self, *, force: bool = False) -> None:
        """현재 화면·급여월 기준 데이터 갱신 (디바운스 우회 시 force=True)."""
        self._refresh_org_filter_options()
        if not force:
            self._schedule_refresh()
            return
        page = self._current_page.get()
        if page == "archive":
            self._refresh_archive()
        elif page == "summary":
            self._refresh_summary()
        elif page == "monthly_report":
            self._refresh_monthly_report()
        elif page == "reports":
            self._refresh_reports()
        elif page == "settings" and hasattr(self, "payroll_settings_panel"):
            self.payroll_settings_panel.refresh()
        elif page == "workflow":
            self._ensure_workflow_hub()
            if self.workflow_hub_panel is not None:
                self.workflow_hub_panel.refresh()
        elif page == "tenant" and hasattr(self, "tenant_admin_panel"):
            self.tenant_admin_panel.refresh()
        elif page == "permissions" and hasattr(self, "user_permissions_panel"):
            self.user_permissions_panel.refresh()
        elif page == "org" and hasattr(self, "org_admin_panel"):
            self.org_admin_panel.refresh()
        elif page == "group_settings" and hasattr(self, "group_settings_panel"):
            self.group_settings_panel.refresh()
        elif page == "hr":
            self._ensure_module_hub("hr")
            panel = getattr(self, "hr_hub_panel", None)
            if panel is not None and hasattr(panel, "refresh"):
                panel.refresh()
        elif page == "home":
            self._refresh_home_roster_hint()

    def _toggle_period_toolbar(self, visible: bool) -> None:
        """급여 산출(홈)은 청구서 업로드 시 월을 정하므로 상단 월 선택 숨김."""
        if visible:
            self._period_toolbar_label.pack(side=tk.LEFT, padx=(0, 8))
            self._global_period_combo.pack(side=tk.LEFT)
            self._period_refresh_btn.pack(side=tk.LEFT, padx=(8, 0))
        else:
            self._period_toolbar_label.pack_forget()
            self._global_period_combo.pack_forget()
            self._period_refresh_btn.pack_forget()

        # 범위 선택은 요약(summary)에서만 노출
        if visible and self._current_page.get() == "summary":
            self._range_toggle.pack(side=tk.LEFT, padx=(16, 0))
            if self._range_enabled.get():
                self._range_from_combo.pack(side=tk.LEFT, padx=(10, 0))
                self._range_sep.pack(side=tk.LEFT)
                self._range_to_combo.pack(side=tk.LEFT)
            else:
                self._range_from_combo.pack_forget()
                self._range_sep.pack_forget()
                self._range_to_combo.pack_forget()
        else:
            self._range_toggle.pack_forget()
            self._range_from_combo.pack_forget()
            self._range_sep.pack_forget()
            self._range_to_combo.pack_forget()

    def _toggle_org_filter(self, visible: bool) -> None:
        if visible:
            self._org_filter_wrap.pack(side=tk.LEFT, padx=(16, 0))
        else:
            self._org_filter_wrap.pack_forget()

    def _on_range_toggle(self) -> None:
        # UI 반영 + refresh
        self._toggle_period_toolbar(self._current_page.get() in self._period_toolbar_pages)
        self._on_range_changed()

    def _on_range_changed(self) -> None:
        # 콤보 선택값을 변수에 반영
        if hasattr(self, "_range_from_combo"):
            v = str(self._range_from_combo.get() or "").strip()
            if v:
                self._range_from.set(v)
        if hasattr(self, "_range_to_combo"):
            v = str(self._range_to_combo.get() or "").strip()
            if v:
                self._range_to.set(v)
        self._schedule_refresh()

    def _selected_month_range(self) -> tuple[str, str, list[str]]:
        """(from, to, months[]) - summary 페이지에서 사용."""
        months = sorted(set(self._period_choices))
        if not months:
            return "", "", []
        start = self._range_from.get() or months[0]
        end = self._range_to.get() or months[-1]
        if start > end:
            start, end = end, start
        picked = [m for m in months if start <= m <= end]
        return start, end, picked

    def _org_selection(self) -> OrgSelection:
        return self._org_filter.get_selection()

    def _refresh_org_filter_options(self) -> None:
        self._org_filter.set_records(
            load_records_for_period_secured(self._selected_month(), session=get_session())
        )

    def _filtered_records(self, scope_key: str) -> list:
        return filter_records(
            load_records_for_period_secured(scope_key, session=get_session()),
            self._org_selection(),
        )

    def _apply_record_totals(self, ms: MonthSummary, records: list) -> MonthSummary:
        sm = summarize_records(records)
        return MonthSummary(
            period=ms.period,
            employee_count=sm.employee_count,
            total_gross=sm.total_gross,
            total_net=sm.total_net,
            total_deduction=sm.total_deduction,
            leave_users=sm.leave_users,
            absence_users=sm.absence_users,
            has_output=ms.has_output,
            has_comparison=ms.has_comparison,
            files=ms.files,
        )

    def _on_org_filter_changed(self) -> None:
        self._schedule_refresh()

    def _on_period_changed(self) -> None:
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        # 드롭다운/필터를 빠르게 바꿀 때 연속 갱신이 겹치면 Tk Treeview/Excel 미리보기 로딩이 누적되어 렉이 생깁니다.
        # after() 디바운스로 “마지막 입력”만 반영합니다.
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
        self._refresh_job = self.after(120, self._run_refresh)

    def _run_refresh(self) -> None:
        self._refresh_job = None
        self._refresh_active_page_data(force=True)

    # ------------------------------------------------------------------ home
    def _build_home_page(self) -> None:
        p = self.pages["home"]
        p.grid_rowconfigure(0, weight=0)
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        card = tk.Frame(p, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        pad = tk.Frame(card, bg=COLORS["card"], padx=24, pady=22)
        pad.pack(fill=tk.X)

        tk.Label(pad, text="도급비 청구서 업로드", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 14, "bold")).pack(
            anchor=tk.W
        )
        tk.Label(
            pad,
            text="청구서(.xlsx) → 급여대장 · 급여명세서 · 지급내역 · 연차대장 · 급여차이 보고 자동 생성",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONT_BODY,
        ).pack(anchor=tk.W, pady=(6, 14))

        self.drop_zone = tk.Frame(
            pad,
            bg=COLORS["accent_light"],
            highlightbackground=COLORS["nav_accent"],
            highlightthickness=2,
            height=120,
        )
        self.drop_zone.pack(fill=tk.X, pady=(0, 14))
        self.drop_zone.pack_propagate(False)
        dz_inner = tk.Frame(self.drop_zone, bg=COLORS["accent_light"])
        dz_inner.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.drop_hint = tk.Label(
            dz_inner,
            text="여기에 청구서(.xlsx)를 드래그 앤 드롭",
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 12, "bold"),
        )
        self.drop_hint.pack()
        tk.Label(
            dz_inner,
            text="또는 아래 버튼으로 파일 선택",
            bg=COLORS["accent_light"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(pady=(6, 0))

        self._dnd_active = enable_invoice_drop(
            self.drop_zone,
            on_file=self._run_invoice,
            on_error=lambda msg: messagebox.showwarning("드롭 불가", msg),
        )
        if self._dnd_active:
            enable_invoice_drop(
                pad,
                on_file=self._run_invoice,
                on_error=lambda msg: messagebox.showwarning("드롭 불가", msg),
            )
        else:
            self.drop_hint.configure(
                text="드래그 앤 드롭 미지원 — 버튼으로 파일 선택",
                fg=COLORS["muted"],
            )

        btn_row = tk.Frame(pad, bg=COLORS["card"])
        btn_row.pack(anchor=tk.W)
        self._upload_btn = tk.Button(
            btn_row,
            text="  청구서 선택 및 급여 산출  ",
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            font=(FONT, 12, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=10,
            cursor="hand2",
            command=self._on_upload,
        )
        self._upload_btn.pack(side=tk.LEFT)

        tk.Button(
            btn_row,
            text="  마지막 산출 되돌리기  ",
            command=self._undo_last_upload,
            bg=COLORS["border"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            font=(FONT, 10),
            padx=12,
            pady=10,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="대기 중 — 청구서를 선택해 주세요.")
        tk.Label(pad, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["nav_accent"], font=FONT_BODY).pack(
            anchor=tk.W, pady=(14, 0)
        )

        self._roster_hint_var = tk.StringVar(value="")
        roster_row = tk.Frame(pad, bg=COLORS["card"])
        roster_row.pack(anchor=tk.W, pady=(6, 0))
        tk.Label(
            roster_row,
            textvariable=self._roster_hint_var,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(side=tk.LEFT)
        tk.Button(
            roster_row,
            text="명부 관리",
            command=lambda: self._open_platform_tab("hr", "roster"),
            bg=COLORS["card"],
            fg=COLORS["accent"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["accent_hover"],
            relief=tk.FLAT,
            font=(FONT, 9, "underline"),
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(8, 0))
        self._refresh_home_roster_hint()

        self.result_card = tk.Frame(p, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        self.result_card.grid(row=1, column=0, sticky="nsew")
        self.result_card.grid_rowconfigure(0, weight=1)
        self.result_card.grid_columnconfigure(0, weight=1)
        self.result_inner = tk.Frame(self.result_card, bg=COLORS["card"], padx=24, pady=18)
        self.result_inner.pack(fill=tk.BOTH, expand=True)
        self.result_inner.grid_rowconfigure(1, weight=1)
        self.result_inner.grid_columnconfigure(0, weight=1)

        tk.Label(self.result_inner, text="최근 처리 결과", bg=COLORS["card"], fg=COLORS["text"], font=(FONT, 12, "bold")).grid(
            row=0, column=0, sticky=tk.W
        )
        text_frame = tk.Frame(self.result_inner, bg=COLORS["card"])
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        self.result_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=FONT_BODY,
            bg="#FAFBFC",
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=12,
            pady=12,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self.result_text.yview)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.result_text.insert("1.0", "아직 처리 이력이 없습니다.\n청구서를 업로드하면 결과가 여기에 표시됩니다.")
        self.result_text.configure(state=tk.DISABLED)
        self.result_btn_row = tk.Frame(self.result_inner, bg=COLORS["card"])
        self.result_btn_row.grid(row=2, column=0, sticky=tk.W, pady=(12, 0))

    def _undo_last_upload(self) -> None:
        if not can_undo():
            messagebox.showinfo("안내", "되돌릴 산출 내역이 없습니다.")
            return
        data = peek_undo()
        scope = scope_from_undo(data)
        if not scope:
            messagebox.showwarning("안내", "되돌릴 산출 정보를 확인할 수 없습니다.")
            return

        if not messagebox.askokcancel(
            "되돌리기 — 영구 삭제 안내",
            build_undo_warning_message(scope, data),
            icon=messagebox.WARNING,
        ):
            return
        if not messagebox.askyesno(
            "마지막 산출 되돌리기 — 최종 확인",
            build_undo_final_confirm_message(scope),
            icon=messagebox.WARNING,
        ):
            return
        try:
            scope = undo_last_upload()
            self._last_process_info = None
            self._refresh_period_list()
            self.status_var.set(f"되돌림 완료 — {scope.display_label()}")
            messagebox.showinfo(
                "완료",
                f"{scope.display_label()} 산출을 되돌렸습니다.\n\n"
                "삭제된 파일은 복구할 수 없습니다. 필요 시 해당 월 청구서로 다시 산출해 주세요.",
            )
        except OSError as exc:
            messagebox.showerror("되돌리기 실패", friendly_error(exc))

    def _show_payroll_audit(self, audit: dict) -> None:
        from ui.payroll_audit_dialog import PayrollAuditDialog

        PayrollAuditDialog(self, audit)

    def _update_result_panel(self, info: dict) -> None:
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        scope = info.get("scope")
        self.result_text.insert("1.0", format_result_summary(info))
        self.result_text.configure(state=tk.DISABLED)

        for child in self.result_btn_row.winfo_children():
            child.destroy()
        btn_row = self.result_btn_row
        scope_key = scope.key if isinstance(scope, PayrollScope) else self._selected_period.get()
        out_dir = scope.output_dir() if isinstance(scope, PayrollScope) else info["paths"]["ledger"].parent
        tk.Button(
            btn_row,
            text="월별 자료함",
            command=lambda: (self._selected_period.set(scope_key), self.show_page("archive")),
            bg=COLORS["border"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            btn_row,
            text="월별 보고",
            command=lambda: (self._selected_period.set(scope_key), self.show_page("monthly_report")),
            bg=COLORS["border"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            btn_row,
            text="되돌리기",
            command=self._undo_last_upload,
            bg=COLORS["border"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            btn_row,
            text="자료 폴더 열기",
            command=lambda: _open_path(out_dir),
            bg=COLORS["border"],
            relief=tk.FLAT,
            font=(FONT, 9),
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        audit = info.get("payroll_audit") or {}
        if audit.get("rows"):
            tk.Button(
                btn_row,
                text="자동검열",
                command=lambda a=audit: self._show_payroll_audit(a),
                bg=COLORS["nav_accent"],
                fg="white",
                activebackground=COLORS["nav_accent"],
                activeforeground="white",
                relief=tk.FLAT,
                font=(FONT, 9, "bold"),
                padx=12,
                pady=6,
                cursor="hand2",
            ).pack(side=tk.LEFT)

    def _run_invoice(self, path: Path) -> None:
        """청구서 경로로 급여 산출 (파일 선택 · 드래그앤드롭 공통)."""
        if self._invoice_busy:
            return
        if not self._payroll_access_allowed():
            messagebox.showinfo(
                "로그인 필요",
                "급여 산출은 로그인 후 이용할 수 있습니다.",
                parent=self,
            )
            return
        if path.suffix.lower() != ".xlsx":
            messagebox.showwarning("파일 형식", "도급비 청구서(.xlsx)만 처리할 수 있습니다.")
            return
        if not path.is_file():
            messagebox.showwarning("파일 없음", "선택한 파일을 찾을 수 없습니다.")
            return

        org = self._org_selection()
        suggested = suggest_upload_scope(
            path,
            default_affiliate="" if org.affiliate == ALL_LABEL else org.affiliate,
            default_workplace="" if org.workplace == ALL_LABEL else org.workplace,
        )
        dialog = UploadConfirmDialog(self, path.name, suggested)
        if not dialog.scope:
            return
        scope = dialog.scope

        out_dir = scope.output_dir()
        if out_dir.exists() and any(out_dir.iterdir()):
            if not messagebox.askyesno(
                "덮어쓰기 확인",
                f"{scope.display_label()} 급여 데이터가 이미 있습니다.\n"
                "다시 산출하면 기존 파일을 덮어씁니다.\n\n계속하시겠습니까?",
            ):
                return

        self._start_invoice_processing(path, scope)

    def _set_invoice_ui_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        if hasattr(self, "_upload_btn"):
            self._upload_btn.configure(state=state)

    def _invalidate_month_records_cache(self, *months: str) -> None:
        if not months:
            self._month_records_cache.clear()
            return
        for m in months:
            self._month_records_cache.pop(m, None)

    def _records_for_month(self, month: str) -> list:
        if not month:
            return []
        if month not in self._month_records_cache:
            self._month_records_cache[month] = load_records_for_period_secured(
                month, session=get_session()
            )
        return self._month_records_cache[month]

    def _start_invoice_processing(self, path: Path, scope: PayrollScope) -> None:
        if self._invoice_busy:
            return
        self._invoice_busy = True
        self._set_invoice_ui_busy(True)
        if hasattr(self, "drop_hint"):
            self.drop_hint.configure(text=f"처리 중: {path.name}")
        self.status_var.set(f"처리 중 — {scope.display_label()}")

        def worker() -> None:
            err: Exception | None = None
            info: dict | None = None
            try:
                info = process_invoice(path, scope, interactive_parent=None)
            except Exception as exc:
                err = exc

            def finish() -> None:
                self._invoice_busy = False
                self._set_invoice_ui_busy(False)
                if hasattr(self, "drop_hint"):
                    self.drop_hint.configure(text="여기에 청구서(.xlsx)를 드래그 앤 드롭")
                if err is not None:
                    if isinstance(err, PayrollValidationError):
                        self.status_var.set("검증 오류")
                        messagebox.showerror("검증 오류", format_validation_error(err))
                    else:
                        self.status_var.set("오류")
                        messagebox.showerror("오류", friendly_error(err))
                        traceback.print_exc()
                    return
                assert info is not None
                self._last_process_info = info
                self._invalidate_month_records_cache(scope.period)
                self._refresh_period_list()
                self._selected_period.set(scope.key)
                self.status_var.set(f"완료 — {scope.display_label()} {info['count']}명")
                self._update_result_panel(info)
                personnel_diff = (info.get("roster") or {}).get("personnel_diff") or {}
                if personnel_diff.get("has_mismatch"):
                    show_personnel_mismatch_dialog(self, personnel_diff)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _on_upload(self) -> None:
        path = filedialog.askopenfilename(
            title="도급비 청구서 선택",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")],
        )
        if not path:
            return
        self._run_invoice(Path(path))

    # ---------------------------------------------------------------- archive
    def _refresh_home_roster_hint(self) -> None:
        if not hasattr(self, "_roster_hint_var"):
            return
        if roster_exists():
            self._roster_hint_var.set(
                f"근로자 명부 준비됨 ✓  (최종 갱신 {roster_updated_display()})"
            )
        else:
            self._roster_hint_var.set("근로자 명부가 없습니다 — 「인사 · 노무 › 직원 명부」에서 등록·저장하세요.")

    def _build_archive_page(self) -> None:
        p = self.pages["archive"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)

        paned = ttk.Panedwindow(p, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self._archive_notebook = ttk.Notebook(left)
        self._archive_notebook.grid(row=0, column=0, sticky="nsew")

        files_tab = ttk.Frame(self._archive_notebook, padding=4)
        self._archive_notebook.add(files_tab, text="  자료 탐색  ")
        files_tab.grid_rowconfigure(0, weight=1)
        files_tab.grid_columnconfigure(0, weight=1)

        self.archive_folder = ArchiveFolderPanel(
            files_tab,
            on_file_select=self._on_archive_file_select,
        )
        self.archive_folder.grid(row=0, column=0, sticky="nsew")

        btn_row = ttk.Frame(files_tab)
        btn_row.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Button(btn_row, text="파일 열기", command=self._open_archive_file).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="폴더 열기", command=self._open_archive_folder).pack(side=tk.LEFT)

        records_tab = ttk.Frame(self._archive_notebook, padding=4)
        self._archive_notebook.add(records_tab, text="  월별·사업장 내역  ")
        records_tab.grid_rowconfigure(0, weight=1)
        records_tab.grid_columnconfigure(0, weight=1)
        self.archive_records = ArchiveRecordsPanel(records_tab)
        self.archive_records.grid(row=0, column=0, sticky="nsew")

        leave_tab = ttk.Frame(self._archive_notebook, padding=4)
        self._archive_notebook.add(leave_tab, text="  연차·결근  ")
        leave_tab.grid_rowconfigure(0, weight=1)
        leave_tab.grid_columnconfigure(0, weight=1)
        self.archive_leave = ArchiveLeavePanel(leave_tab, on_synced=self._on_archive_leave_synced)
        self.archive_leave.grid(row=0, column=0, sticky="nsew")

        self.archive_preview = FilePreviewPanel(paned, COLORS)
        paned.add(self.archive_preview, weight=4)
        self._wire_preview_replace(self.archive_preview)
        self._archive_preview_entry = None

    def _on_archive_file_select(self, entry) -> None:
        self._archive_preview_entry = entry
        period = entry.period if entry else self._selected_period.get()
        scope = self._selected_scope()
        self.archive_preview.set_period(period or "")
        self.archive_preview.set_scope(scope)
        if entry and entry.path:
            self.archive_preview.schedule_show_file(entry.path)
        else:
            self.archive_preview.show_file(None)

    def _wire_preview_replace(self, panel: FilePreviewPanel) -> None:
        panel.set_on_replaced(self._on_file_replaced)

    def _on_file_replaced(self, revision) -> None:
        self._refresh_revision_panels(revision.scope)
        messagebox.showinfo(
            "수정 완료",
            f"「{revision.file_label}」이(가) 수정본으로 대체되었습니다.\n\n"
            f"변경: {revision.change_summary}\n\n"
            "수정 전·후 파일과 사유는 「Excel 수정 이력」에서 확인할 수 있습니다.",
        )

    def _refresh_revision_panels(self, scope: PayrollScope | None = None) -> None:
        scope = scope or self._selected_scope()
        if hasattr(self, "monthly_revision_history"):
            self.monthly_revision_history.load(scope)
        if hasattr(self, "reports_revision_history"):
            self.reports_revision_history.load(scope)

    def _on_archive_leave_synced(self) -> None:
        scope_key = self._selected_period.get()
        self.archive_folder.refresh(self._org_selection(), period=scope_key)

    def _refresh_archive(self) -> None:
        scope = self._selected_scope()
        scope_key = self._selected_period.get()
        month = self._selected_month()
        records = load_records_for_period_secured(month, session=get_session())
        self.archive_records.load(month, records, self._org_selection())
        self.archive_leave.load(month, records, self._org_selection())
        self.archive_folder.refresh(self._org_selection(), period=scope_key)
        self.archive_preview.set_scope(scope)
        self._refresh_revision_panels(scope)

    def _open_archive_file(self) -> None:
        self.archive_folder.open_selected_file()

    def _open_archive_folder(self) -> None:
        self.archive_folder.open_current_folder()

    # ---------------------------------------------------------------- summary
    def _build_summary_page(self) -> None:
        p = self.pages["summary"]
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        self.stats_frame = tk.Frame(p, bg=COLORS["bg"])
        self.stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._stat_labels: dict[str, tk.Label] = {}
        stat_defs = [
            ("count", "인원"),
            ("gross", "총지급액"),
            ("net", "실수령액"),
            ("leave", "연차 사용자"),
            ("absence", "무급/결근"),
        ]
        for i, (key, lbl) in enumerate(stat_defs):
            card = tk.Frame(
                self.stats_frame,
                bg=COLORS["card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
            )
            card.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="nsew")
            self.stats_frame.grid_columnconfigure(i, weight=1)
            inner = tk.Frame(card, bg=COLORS["card"], padx=18, pady=16)
            inner.pack(fill=tk.BOTH, expand=True)
            tk.Label(inner, text=lbl, bg=COLORS["card"], fg=COLORS["muted"], font=(FONT, 9)).pack(anchor=tk.W)
            val = tk.Label(inner, text="-", bg=COLORS["card"], fg=COLORS["text"], font=FONT_STAT)
            val.pack(anchor=tk.W, pady=(6, 0))
            self._stat_labels[key] = val

        table_frame = ttk.LabelFrame(p, text="  인원별 현황  ", padding=8)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("name", "affiliate", "workplace", "gross", "net", "leave", "unpaid")
        self.summary_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c, h, w in [
            ("name", "성명", 88),
            ("affiliate", "계열사", 88),
            ("workplace", "사업장", 96),
            ("gross", "총지급", 108),
            ("net", "실수령", 108),
            ("leave", "연차", 56),
            ("unpaid", "무급/결근", 80),
        ]:
            self.summary_tree.heading(c, text=h)
            self.summary_tree.column(c, width=w, minwidth=64, anchor=tk.E if c != "name" else tk.W)
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scroll.set)
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.summary_tree.bind("<MouseWheel>", self._on_summary_tree_mousewheel)

        # 범위 모드: 월별 한눈에 보기
        self._range_table_frame = ttk.LabelFrame(p, text="  기간 요약(월별)  ", padding=8)
        self._range_table_frame.grid(row=1, column=0, sticky="nsew")
        self._range_table_frame.grid_rowconfigure(0, weight=1)
        self._range_table_frame.grid_columnconfigure(0, weight=1)
        rcols = ("period", "count", "gross", "net", "leave", "absence")
        self.range_tree = ttk.Treeview(self._range_table_frame, columns=rcols, show="headings")
        for c, h, w in [
            ("period", "월", 72),
            ("count", "인원", 72),
            ("gross", "총지급", 120),
            ("net", "실수령", 120),
            ("leave", "연차", 72),
            ("absence", "무급/결근", 90),
        ]:
            self.range_tree.heading(c, text=h)
            self.range_tree.column(c, width=w, minwidth=64, anchor=tk.E if c != "period" else tk.W)
        rscroll = ttk.Scrollbar(self._range_table_frame, orient=tk.VERTICAL, command=self.range_tree.yview)
        self.range_tree.configure(yscrollcommand=rscroll.set)
        self.range_tree.grid(row=0, column=0, sticky="nsew")
        rscroll.grid(row=0, column=1, sticky="ns")
        self.range_tree.bind("<MouseWheel>", lambda e: (self.range_tree.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
        # 기본은 단일 월 모드
        self._range_table_frame.grid_remove()

        action_row = ttk.Frame(p)
        action_row.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Button(action_row, text="월별 보고 만들기", command=lambda: self.show_page("monthly_report")).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(action_row, text="월별 자료함", command=lambda: self.show_page("archive")).pack(side=tk.LEFT)

    def _fmt_won(self, n: int) -> str:
        return f"{n:,}"

    def _on_summary_tree_mousewheel(self, event) -> str:
        self.summary_tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _refresh_summary(self) -> None:
        month = self._selected_month()
        # 테이블 초기화
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        if hasattr(self, "range_tree"):
            for item in self.range_tree.get_children():
                self.range_tree.delete(item)

        # 범위 모드
        if self._range_enabled.get():
            self._range_table_frame.grid()
            self.summary_tree.master.grid_remove()
            start, end, months = self._selected_month_range()
            if not months:
                for lbl in self._stat_labels.values():
                    lbl.configure(text="-")
                return

            tot_count = tot_gross = tot_net = tot_leave = tot_abs = 0
            for m in months:
                ms = self._month_summary(m)
                recs = filter_records(
                    self._records_for_month(m),
                    self._org_selection(),
                )
                fms = self._apply_record_totals(ms, recs)
                tot_count += int(fms.employee_count or 0)
                tot_gross += int(fms.total_gross or 0)
                tot_net += int(fms.total_net or 0)
                tot_leave += int(fms.leave_users or 0)
                tot_abs += int(fms.absence_users or 0)
                self.range_tree.insert(
                    "",
                    tk.END,
                    values=(
                        m,
                        f"{int(fms.employee_count or 0)}명",
                        self._fmt_won(int(fms.total_gross or 0)),
                        self._fmt_won(int(fms.total_net or 0)),
                        f"{int(fms.leave_users or 0)}명",
                        f"{int(fms.absence_users or 0)}명",
                    ),
                )

            self._stat_labels["count"].configure(text=f"{tot_count}명")
            self._stat_labels["gross"].configure(text=self._fmt_won(tot_gross))
            self._stat_labels["net"].configure(text=self._fmt_won(tot_net))
            self._stat_labels["leave"].configure(text=f"{tot_leave}명")
            self._stat_labels["absence"].configure(text=f"{tot_abs}명")
            return

        # 단일 월 모드(기존)
        self._range_table_frame.grid_remove()
        self.summary_tree.master.grid()
        if not month:
            for lbl in self._stat_labels.values():
                lbl.configure(text="-")
            return

        ms = self._month_summary(month)
        records = filter_records(
            self._records_for_month(month),
            self._org_selection(),
        )
        fms = self._apply_record_totals(ms, records)
        self._stat_labels["count"].configure(text=f"{fms.employee_count}명")
        self._stat_labels["gross"].configure(text=self._fmt_won(fms.total_gross))
        self._stat_labels["net"].configure(text=self._fmt_won(fms.total_net))
        self._stat_labels["leave"].configure(text=f"{fms.leave_users}명")
        self._stat_labels["absence"].configure(text=f"{fms.absence_users}명")

        if not records:
            return

        for r in sorted(records, key=lambda x: (str(x.get("workplace") or ""), str(x.get("name") or ""))):
            self.summary_tree.insert(
                "",
                tk.END,
                values=(
                    r.get("name", ""),
                    r.get("affiliate", ""),
                    r.get("workplace", ""),
                    self._fmt_won(int(r.get("gross_pay") or 0)),
                    self._fmt_won(int(r.get("net_pay") or 0)),
                    r.get("leave_days", 0),
                    r.get("unpaid_days", 0),
                ),
            )

    # ---------------------------------------------------------- monthly report
    def _build_monthly_report_page(self) -> None:
        p = self.pages["monthly_report"]
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        btn_row = ttk.Frame(p)
        btn_row.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Button(btn_row, text="보고서 Excel 생성/갱신", command=self._export_monthly_report).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="Excel 미리보기", command=self._show_monthly_excel_preview).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="보고 폴더", command=lambda: _open_path(MONTHLY_REPORTS_DIR)).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="월별 요약", command=lambda: self.show_page("summary")).pack(side=tk.LEFT)

        scroll_host = ttk.Frame(p)
        scroll_host.grid(row=1, column=0, sticky="nsew")
        scroll_host.grid_rowconfigure(0, weight=1)
        scroll_host.grid_columnconfigure(0, weight=1)

        self._monthly_scroll_canvas = tk.Canvas(scroll_host, bg=COLORS["bg"], highlightthickness=0)
        monthly_yscroll = ttk.Scrollbar(scroll_host, orient=tk.VERTICAL, command=self._monthly_scroll_canvas.yview)
        self._monthly_scroll_canvas.configure(yscrollcommand=monthly_yscroll.set)
        self._monthly_scroll_canvas.grid(row=0, column=0, sticky="nsew")
        monthly_yscroll.grid(row=0, column=1, sticky="ns")

        self._monthly_scroll_body = tk.Frame(self._monthly_scroll_canvas, bg=COLORS["bg"])
        self._monthly_scroll_win = self._monthly_scroll_canvas.create_window(
            (0, 0), window=self._monthly_scroll_body, anchor=tk.NW
        )

        def _on_monthly_scroll_configure(_event=None) -> None:
            self._monthly_scroll_canvas.configure(scrollregion=self._monthly_scroll_canvas.bbox("all"))
            cw = self._monthly_scroll_canvas.winfo_width()
            if cw > 1:
                self._monthly_scroll_canvas.itemconfigure(self._monthly_scroll_win, width=cw)

        self._on_monthly_scroll_configure = _on_monthly_scroll_configure
        self._monthly_scroll_body.bind("<Configure>", _on_monthly_scroll_configure)
        self._monthly_scroll_canvas.bind("<Configure>", _on_monthly_scroll_configure)
        bind_local_wheel(self._monthly_scroll_body, self._monthly_scroll_canvas)
        bind_local_wheel(self._monthly_scroll_canvas, self._monthly_scroll_canvas)

        self._monthly_status_label = tk.Label(
            self._monthly_scroll_body,
            text="",
            bg=COLORS["bg"],
            fg=COLORS["warn"],
            font=(FONT, 10),
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=960,
        )
        self._monthly_status_label.pack(fill=tk.X, pady=(0, 6))

        self.monthly_executive_dashboard = ExecutiveDashboardPanel(
            self._monthly_scroll_body,
            COLORS,
            page_scroll=True,
            wheel_scroll_target=self._monthly_scroll_canvas,
        )
        self.monthly_executive_dashboard.pack(fill=tk.X, anchor=tk.NW)
        self.monthly_executive_dashboard.bind(
            "<<ExecutiveDashboardLayout>>",
            lambda _e: self._on_monthly_scroll_configure(),
        )

        self.monthly_revision_history = RevisionHistoryPanel(self._monthly_scroll_body)
        self.monthly_revision_history.pack(fill=tk.X, pady=(8, 0))

        self._monthly_preview_win: tk.Toplevel | None = None
        self._monthly_preview_panel: FilePreviewPanel | None = None

    def _monthly_report_path(self, period: str) -> Path:
        return get_or_create_report_path(period, MONTHLY_REPORTS_DIR)

    def _export_monthly_report(self) -> None:
        try:
            require_executive_payroll_access(get_session())
        except PermissionError as exc:
            messagebox.showwarning("권한", str(exc))
            return
        period = self._selected_month()
        if not period:
            messagebox.showinfo("안내", "선택된 급여월이 없습니다.")
            return
        ms = self._month_summary(period)
        if not ms.has_output:
            messagebox.showinfo("안내", "해당 월 급여 산출 데이터가 없습니다. 먼저 급여를 산출해 주세요.")
            return
        try:
            _, records = build_report_bundle(period, ms)
            out = export_monthly_report_excel(period, ms, records, self._monthly_report_path(period))
            messagebox.showinfo("완료", format_save_success(out))
            self._refresh_monthly_report()
        except OSError as exc:
            messagebox.showerror("저장 실패", friendly_error(exc))

    def _show_monthly_excel_preview(self) -> None:
        try:
            require_executive_payroll_access(get_session())
        except PermissionError as exc:
            messagebox.showwarning("권한", str(exc))
            return
        period = self._selected_month()
        if not period:
            messagebox.showinfo("안내", "선택된 급여월이 없습니다.")
            return
        path = self._monthly_report_path(period)
        if not path.is_file():
            messagebox.showinfo(
                "안내",
                "저장된 Excel 보고서가 없습니다.\n「보고서 Excel 생성/갱신」을 먼저 실행해 주세요.",
            )
            return
        if self._monthly_preview_win is not None and self._monthly_preview_win.winfo_exists():
            self._monthly_preview_win.lift()
            self._monthly_preview_win.focus_force()
        else:
            win = tk.Toplevel(self)
            win.title(f"{format_period_display(period)} — Excel 보고서 미리보기")
            win.geometry("960x640")
            win.minsize(720, 480)
            panel = FilePreviewPanel(win, COLORS)
            panel.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            scope = self._selected_scope()
            panel.set_period(period)
            panel.set_scope(scope)
            self._wire_preview_replace(panel)
            self._monthly_preview_win = win
            self._monthly_preview_panel = panel
            win.protocol("WM_DELETE_WINDOW", self._close_monthly_preview)

        scope = self._selected_scope()
        self._monthly_preview_panel.set_period(period)
        self._monthly_preview_panel.set_scope(scope)
        self._monthly_preview_panel.schedule_show_file(path)

    def _close_monthly_preview(self) -> None:
        if self._monthly_preview_win is not None:
            try:
                self._monthly_preview_win.destroy()
            except tk.TclError:
                pass
        self._monthly_preview_win = None
        self._monthly_preview_panel = None

    def _set_monthly_report_status(self, message: str = "") -> None:
        if not hasattr(self, "_monthly_status_label"):
            return
        self._monthly_status_label.configure(text=message)
        if message:
            self._monthly_status_label.grid()
        else:
            self._monthly_status_label.grid_remove()

    def _refresh_monthly_report(self) -> None:
        scope = self._selected_scope()
        period = self._selected_month()
        self._refresh_revision_panels(scope)
        dash = getattr(self, "monthly_executive_dashboard", None)

        def _clear_dashboard(empty_message: str = "") -> None:
            self._set_monthly_report_status(empty_message)
            if dash is not None:
                dash.load(None, empty_message=empty_message or None)

        if not period:
            _clear_dashboard()
            if self._monthly_preview_panel is not None:
                self._monthly_preview_panel.show_file(None)
            return
        if not can_view_executive_reports(session_role(get_session())):
            _clear_dashboard(
                "월별 경영 보고는 재무팀 또는 관리자 권한이 필요합니다. 권한 변경은 관리자에게 요청하세요."
            )
            if self._monthly_preview_panel is not None:
                self._monthly_preview_panel.show_file(None)
            return
        records = filter_records(
            load_records_for_period_secured(period, session=get_session()),
            self._org_selection(),
        )
        if not records:
            _clear_dashboard("해당 월 급여 산출 데이터가 없습니다. 먼저 급여를 산출해 주세요.")
            if self._monthly_preview_panel is not None:
                self._monthly_preview_panel.show_file(None)
            return

        self._set_monthly_report_status("")
        ms = self._month_summary(period)
        fms = self._apply_record_totals(ms, records)
        if dash is not None:
            analytics = build_executive_analytics(period, summary=fms, records=records)
            dash.load(analytics)
        if hasattr(self, "_on_monthly_scroll_configure"):
            self._on_monthly_scroll_configure()
        if self._monthly_preview_panel is not None and self._monthly_preview_panel.winfo_exists():
            report_path = self._monthly_report_path(period)
            if report_path.is_file():
                self._monthly_preview_panel.set_period(period)
                self._monthly_preview_panel.set_scope(scope)
                self._monthly_preview_panel.schedule_show_file(report_path)

    # ---------------------------------------------------------------- reports
    def _build_reports_page(self) -> None:
        p = self.pages["reports"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)

        paned = ttk.Panedwindow(p, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.LabelFrame(paned, text="  보고 · 연차  ", padding=8)
        paned.add(left, weight=2)
        left.grid_rowconfigure(0, weight=2)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.reports_dashboard = ReportsDashboardPanel(left, COLORS)
        self.reports_dashboard.grid(row=0, column=0, sticky="nsew")

        btn_row = ttk.Frame(left)
        btn_row.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Button(btn_row, text="급여차이 열기", command=self._open_comparison_report).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="연차대장 열기", command=self._open_leave_ledger).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="미리보기", command=self._preview_comparison_report).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="보고서 폴더", command=lambda: _open_path(PAYROLL_DIFF_DIR)).pack(side=tk.LEFT)

        self.reports_revision_history = RevisionHistoryPanel(left)
        self.reports_revision_history.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

        self.reports_preview = FilePreviewPanel(paned, COLORS)
        paned.add(self.reports_preview, weight=3)
        self._wire_preview_replace(self.reports_preview)

    def _build_settings_page(self) -> None:
        p = self.pages["settings"]
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.payroll_settings_panel = PayrollSettingsPanel(p)
        self.payroll_settings_panel.grid(row=0, column=0, sticky="nsew")

    def _comparison_status_text(self, period: str, ms) -> str:
        path = self._comparison_report_path(period)
        if path:
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            return (
                f"생성됨 ({modified}) — 오른쪽 미리보기에서 확인 · "
                "「급여차이 열기」로 Excel 실행"
            )
        return "아직 없습니다. (첫 달은 전월 데이터가 없을 수 있습니다)"

    def _refresh_reports(self) -> None:
        scope = self._selected_scope()
        period = self._selected_month()
        self.reports_preview.set_period(period)
        self.reports_preview.set_scope(scope)
        self._refresh_revision_panels(scope)
        if not period:
            self.reports_dashboard.load("", None, [], self._org_selection(), "처리된 급여월이 없습니다.")
            self.reports_preview.show_file(None)
            return
        ms = self._month_summary(period)
        records = load_records_for_period_secured(period, session=get_session())
        status = self._comparison_status_text(period, ms)
        self.reports_dashboard.load(period, ms, records, self._org_selection(), status)
        self._preview_comparison_report(show_message=False)

    def _comparison_report_path(self, period: str) -> Path | None:
        scope = self._selected_scope()
        p = scope.period if scope else period

        candidates: list[Path] = []
        if scope:
            out_dir = resolve_output_dir(scope)
            candidates.extend(list(out_dir.glob(f"{p}_전월대비*.xlsx")))
        if PAYROLL_DIFF_DIR.is_dir():
            candidates.extend(list(PAYROLL_DIFF_DIR.glob(f"{p}_전월대비*.xlsx")))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]

    def _preview_comparison_report(self, show_message: bool = True) -> None:
        scope = self._selected_scope()
        period = scope.period if scope else self._selected_period.get()
        if not period:
            if show_message:
                messagebox.showinfo("안내", "선택된 급여월이 없습니다.")
            return
        path = self._comparison_report_path(period)
        if path:
            self.reports_preview.show_file(path)
        elif show_message:
            messagebox.showinfo("안내", "해당 월의 급여차이 보고서가 없습니다.")
            self.reports_preview.show_file(None)
        else:
            self.reports_preview.show_file(None)

    def _open_comparison_report(self) -> None:
        scope = self._selected_scope()
        period = scope.period if scope else self._selected_period.get()
        if not period:
            return
        path = self._comparison_report_path(period)
        if path:
            _open_path(path)
        else:
            messagebox.showinfo("안내", "해당 월의 급여차이 보고서가 없습니다.")

    def _open_leave_ledger(self) -> None:
        from ui.leave_ledger_panel import show_leave_ledger_viewer

        period = self._selected_month()
        records = load_records_for_period_secured(period, session=get_session()) if period else []
        show_leave_ledger_viewer(
            self,
            period=period or "",
            records=records,
            selection=self._org_selection(),
        )


def run_dashboard() -> None:
    MONTHLY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    init_i18n()
    log_startup_version()
    PayrollDashboard().mainloop()
