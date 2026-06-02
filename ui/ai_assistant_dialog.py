"""
ui/ai_assistant_dialog.py - Personal AI Assistant (ChatGPT)
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from typing import Callable

from core.session_service import get_session, is_logged_in, require_session
from services.ai_assistant import (
    AssistantResponse,
    ask_assistant,
    clear_chat_history,
    load_chat_history,
    predict_assistant_status,
)
from services.age_benefit_advisor import format_proactive_benefit_message, scan_roster_age_benefits
from services.openai_client import OpenAIKeyMissingError
from services.openai_settings_store import (
    DEFAULT_MODEL,
    has_api_key,
    load_openai_settings,
    save_openai_settings,
    validate_api_key_input,
)
from ui.login_dialog import LoginDialog
from ui.theme import COLORS, FONT, FONT_BODY, add_theme_listener, remove_theme_listener

OnDataChanged = Callable[[], None]


class AiAssistantDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_changed: OnDataChanged | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        self._photo_refs: list[tk.PhotoImage] = []
        self.title("Personal AI Agent")
        self.geometry("720x640")
        self.minsize(520, 440)
        self.configure(bg=COLORS["bg"])

        if not is_logged_in():
            messagebox.showinfo(
                "로그인 필요",
                "Personal AI는 로그인한 본인 계정에서만 사용할 수 있습니다.",
                parent=self,
            )
            self.after(100, self.destroy)
            return

        head = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=12)
        head.pack(fill=tk.X)
        tk.Label(
            head,
            text="✨ Personal AI",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        ).pack(side=tk.LEFT)
        sess = get_session()
        if sess:
            tk.Label(
                head,
                text=f"{sess.display_name} · Bitween 급여 데이터 연동",
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(side=tk.LEFT, padx=(12, 0))

        btn_row = tk.Frame(head, bg=COLORS["bg"])
        btn_row.pack(side=tk.RIGHT)
        tk.Button(
            btn_row,
            text="API 설정",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 9),
            command=self._open_settings,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            btn_row,
            text="대화 지우기",
            relief=tk.FLAT,
            bg="#F1F5F9",
            font=(FONT, 9),
            command=self._clear_chat,
        ).pack(side=tk.LEFT, padx=2)

        hint = tk.Label(
            self,
            text="급여·보고·기안·양식 검색·할 일·일정·연령별 혜택·국가지원 — 사내 데이터·차트·Excel을 활용해 업무를 돕습니다.",
            bg=COLORS["accent_light"],
            fg=COLORS["accent"],
            font=(FONT, 9),
            padx=12,
            pady=8,
            anchor=tk.W,
        )
        hint.pack(fill=tk.X, padx=16, pady=(0, 8))

        self._chat = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            font=FONT_BODY,
            state=tk.DISABLED,
            height=18,
            bg=COLORS["card"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self._chat.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
        self._configure_chat_tags()
        self._on_theme_change = lambda _tid: self._configure_chat_tags()
        add_theme_listener(self._on_theme_change)
        self.bind("<Destroy>", self._on_destroy, add="+")

        self._attach_bar = tk.Frame(self, bg=COLORS["bg"])
        self._attach_bar.pack(fill=tk.X, padx=16, pady=(0, 4))

        self._append_api_status_hint()
        self._load_history()
        threading.Thread(target=self._load_age_benefit_prompt_async, daemon=True).start()

        foot = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=12)
        foot.pack(fill=tk.X)
        self._input = tk.Text(foot, height=3, font=FONT_BODY, wrap=tk.WORD)
        self._input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._input.bind("<Return>", self._on_input_return)
        self._input.bind("<KP_Enter>", self._on_input_return)
        self._input.bind("<Control-Return>", self._on_input_return)
        self._send_btn = tk.Button(
            foot,
            text="전송",
            bg=COLORS["accent"],
            fg="#FFFFFF",
            relief=tk.FLAT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            command=self._send,
        )
        self._send_btn.pack(side=tk.LEFT, padx=(8, 0))
        status_row = tk.Frame(self, bg=COLORS["bg"], padx=16)
        status_row.pack(fill=tk.X, pady=(0, 8))
        self._status = tk.StringVar(value="")
        tk.Label(status_row, textvariable=self._status, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 8)).pack(
            side=tk.LEFT, anchor=tk.W
        )
        tk.Label(
            status_row,
            text="Enter 전송 · Shift+Enter 줄바꿈",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).pack(side=tk.RIGHT, anchor=tk.E)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            remove_theme_listener(self._on_theme_change)

    def _configure_chat_tags(self) -> None:
        """사용자(나) / AI 메시지 구분 — theme.COLORS 기반."""
        # chip_bg는 accent_light와 동일하게 잡히므로 AI 말풍선은 bg(중립) 사용
        user_bg = COLORS.get("accent_light", "#E0F4FD")
        bot_bg = COLORS.get("sidebar", COLORS.get("bg", "#F1F5F9"))
        bubble_pad = {"lmargin1": 10, "lmargin2": 10, "rmargin": 10, "spacing1": 8, "spacing3": 8}
        user_bubble = {**bubble_pad, "background": user_bg, "justify": "right"}
        bot_bubble = {**bubble_pad, "background": bot_bg, "justify": "left"}

        self._chat.tag_configure(
            "user_prefix",
            foreground=COLORS["accent"],
            font=(FONT, 10, "bold"),
            **user_bubble,
        )
        self._chat.tag_configure(
            "user_body",
            foreground=COLORS["accent"],
            font=FONT_BODY,
            **user_bubble,
        )
        self._chat.tag_configure(
            "bot_prefix",
            foreground=COLORS.get("nav_accent", COLORS["accent"]),
            font=(FONT, 10, "bold"),
            **bot_bubble,
        )
        self._chat.tag_configure(
            "bot_body",
            foreground=COLORS["text"],
            font=FONT_BODY,
            **bot_bubble,
        )
        self._chat.tag_configure("sys", foreground=COLORS["muted"], font=(FONT, 9))
        self._chat.tag_configure("attach", foreground=COLORS["muted"], font=(FONT, 9))

    def _on_input_return(self, event: tk.Event) -> str | None:
        """Enter: 전송, Shift+Enter: 줄바꿈."""
        if event.state & 0x0001:
            return None
        self._send()
        return "break"

    def _append_attachments(self, paths: list[str]) -> None:
        for child in self._attach_bar.winfo_children():
            child.destroy()
        if not paths:
            return
        tk.Label(
            self._attach_bar,
            text="첨부·생성 자료:",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=(FONT, 8),
        ).pack(side=tk.LEFT)
        for raw in paths[:6]:
            p = Path(raw)
            if not p.is_file():
                continue
            tk.Button(
                self._attach_bar,
                text=p.name,
                relief=tk.FLAT,
                bg="#F1F5F9",
                font=(FONT, 8),
                command=lambda path=p: self._open_path(path),
            ).pack(side=tk.LEFT, padx=2)
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                self._append_chart_preview(p)

    def _append_chart_preview(self, path: Path) -> None:
        try:
            img = tk.PhotoImage(file=str(path))
            max_w = 480
            if img.width() > max_w:
                scale = max(1, img.width() // max_w)
                img = img.subsample(scale, scale)
            self._photo_refs.append(img)
            self._chat.configure(state=tk.NORMAL)
            self._chat.image_create(tk.END, image=img)
            self._chat.insert(tk.END, f"\n📊 {path.name}\n\n", "attach")
            self._chat.configure(state=tk.DISABLED)
            self._chat.see(tk.END)
        except tk.TclError:
            pass

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError:
            subprocess.run(["explorer", str(path.parent)], check=False)

    def _append_system(self, text: str) -> None:
        self._chat.configure(state=tk.NORMAL)
        self._chat.insert(tk.END, f"ℹ {text}\n\n", "sys")
        self._chat.configure(state=tk.DISABLED)
        self._chat.see(tk.END)

    def _append_message(self, role: str, text: str) -> None:
        self._chat.configure(state=tk.NORMAL)
        if role == "user":
            self._chat.insert(tk.END, "나: ", "user_prefix")
            self._chat.insert(tk.END, f"{text}\n\n", "user_body")
        else:
            self._chat.insert(tk.END, "AI: ", "bot_prefix")
            self._chat.insert(tk.END, f"{text}\n\n", "bot_body")
        self._chat.configure(state=tk.DISABLED)
        self._chat.see(tk.END)

    def _load_history(self) -> None:
        for m in load_chat_history(limit=10):
            self._append_message(m["role"], m["content"])

    def _load_age_benefit_prompt_async(self) -> None:
        """대화 기록이 없을 때 명부 기반 연령별 혜택·지원 안내 (백그라운드)."""
        if load_chat_history(limit=1):
            return
        sess = get_session()
        if not sess:
            return
        try:
            scan = scan_roster_age_benefits(sess.tenant_id, session=sess)
            msg = format_proactive_benefit_message(scan, session=sess)
            if msg:
                self.after(0, lambda m=msg: self._append_message("assistant", m))
        except Exception:
            pass

    def _maybe_show_age_benefit_prompt(self) -> None:
        """호환용 — 동기 로드는 사용하지 않음."""
        threading.Thread(target=self._load_age_benefit_prompt_async, daemon=True).start()

    def _clear_chat(self) -> None:
        if messagebox.askyesno("대화 지우기", "이 계정의 AI 대화 기록을 삭제할까요?", parent=self):
            clear_chat_history()
            self._chat.configure(state=tk.NORMAL)
            self._chat.delete("1.0", tk.END)
            self._chat.configure(state=tk.DISABLED)
            self._append_system("대화 기록을 비웠습니다.")

    def _append_api_status_hint(self) -> None:
        settings = load_openai_settings()
        base = (
            "Personal AI Agent: 급여·명부·월별보고·플랫폼 양식·자료함을 자동 탐색해 기안·보고 초안을 작성합니다. "
            "「5월 월별보고 기안」, 「급여대장 양식 찾아줘」, 「할일에 ○○ 추가」 등으로 요청하세요. "
        )
        if settings.get("key_invalid_stored"):
            self._append_system(
                base
                + "저장된 API 키가 잘못되었습니다(채팅 내용이 들어갔을 수 있음). "
                "「API 설정」에서 sk-... 키만 다시 입력하세요."
            )
        elif has_api_key():
            self._append_system(base + "OpenAI 연동됨.")
        else:
            self._append_system(
                base
                + "오프라인 대화 모드 — 「안녕」처럼 인사·일상 대화와 급여·할 일·기안 등 업무 질문 모두 가능. "
                "(ChatGPT 연결 시 문장·보고 초안이 더 자연스러워집니다.)"
            )

    def _open_settings(self) -> None:
        settings = load_openai_settings()
        if settings.get("key_invalid_stored"):
            messagebox.showwarning(
                "API 키 확인",
                "저장된 값이 OpenAI API 키가 아닙니다.\n"
                "platform.openai.com 에서 발급한 sk-... 키만 입력하세요.\n"
                "(채팅·안내 문구를 붙여넣지 마세요.)",
                parent=self,
            )
        key = simpledialog.askstring(
            "OpenAI API 키",
            "sk- 로 시작하는 API 키만 입력 (platform.openai.com).\n"
            "비우고 확인하면 키를 삭제합니다.\n"
            "※ 채팅 내용·ℹ 안내 문구는 붙여넣지 마세요.",
            parent=self,
            show="•",
        )
        if key is None:
            return
        clean_key, key_err = validate_api_key_input(key)
        if key_err:
            messagebox.showerror("API 키 오류", key_err, parent=self)
            return
        model = simpledialog.askstring(
            "모델",
            f"모델 이름 (권장: {DEFAULT_MODEL}, 예: gpt-4o, gpt-4o-mini)\n"
            "존재하지 않는 모델명이면 API 오류가 납니다.",
            initialvalue=settings.get("model") or DEFAULT_MODEL,
            parent=self,
        )
        if model is None:
            return
        try:
            save_openai_settings(
                api_key=clean_key,
                model=(model or DEFAULT_MODEL).strip(),
            )
        except ValueError as exc:
            messagebox.showerror("저장 실패", str(exc), parent=self)
            return
        self._append_system(
            "API 설정이 저장되었습니다. (" + ("OpenAI 연동됨." if has_api_key() else "API 미등록.") + ")"
        )
        messagebox.showinfo(
            "저장됨",
            "API 설정이 이 로그인 계정에만 저장되었습니다.",
            parent=self,
        )

    def _schedule_worker_result(
        self,
        *,
        answer: AssistantResponse | str | None = None,
        error: str | None = None,
    ) -> None:
        """백그라운드 스레드 → 메인 스레드 (except 변수 클로저 버그 방지)."""

        def on_main() -> None:
            if error is not None:
                self._on_error(error)
            elif answer is not None:
                self._on_answer(answer)
            else:
                self._on_error("알 수 없는 오류가 발생했습니다.")

        self.after(0, on_main)

    def _send(self) -> None:
        if str(self._send_btn.cget("state")) == tk.DISABLED:
            return
        text = self._input.get("1.0", tk.END).strip()
        if not text:
            return
        self._input.delete("1.0", tk.END)
        self._append_message("user", text)
        self._send_btn.configure(state=tk.DISABLED)
        settings = load_openai_settings()
        has_key = bool(settings.get("api_key") and settings.get("enabled", True))
        self._status.set(predict_assistant_status(text, has_api_key=has_key))

        def worker() -> None:
            try:
                require_session()
                result = ask_assistant(text)
                self._schedule_worker_result(answer=result)
            except OpenAIKeyMissingError as exc:
                self._schedule_worker_result(error=str(exc))
            except Exception as exc:
                self._schedule_worker_result(error=str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_answer(self, result: AssistantResponse | str) -> None:
        if isinstance(result, AssistantResponse):
            self._append_message("assistant", result.answer)
            self._append_attachments(result.attachment_paths)
        else:
            self._append_message("assistant", str(result))
        self._send_btn.configure(state=tk.NORMAL)
        self._status.set("")
        if self._on_changed:
            self._on_changed()

    def _on_error(self, msg: str) -> None:
        self._append_message("assistant", f"오류: {msg}")
        self._send_btn.configure(state=tk.NORMAL)
        self._status.set("")


def open_ai_assistant(
    parent: tk.Misc,
    *,
    on_login_needed: Callable[[], None] | None = None,
    on_changed: OnDataChanged | None = None,
) -> None:
    if not is_logged_in():
        if on_login_needed:
            LoginDialog(parent, on_success=lambda _s: on_login_needed())
        else:
            LoginDialog(parent)
        if not is_logged_in():
            return

    def _refresh_workspace() -> None:
        if on_changed:
            on_changed()
            return
        panel = getattr(parent, "launcher_panel", None)
        hub = getattr(panel, "workspace_hub", None) if panel else None
        if hub is not None and hasattr(hub, "refresh"):
            hub.refresh()

    AiAssistantDialog(parent, on_changed=_refresh_workspace)
