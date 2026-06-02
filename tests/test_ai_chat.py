"""
tests/test_ai_chat.py - Personal AI 단위 테스트 (실제 API 호출 없음)

실행:
  cd 급여프로그램
  python -m unittest tests.test_ai_chat -v

수동 통합 테스트 (API 키 필요):
  set OPENAI_API_KEY=sk-...
  set OPENAI_MODEL=gpt-5.5
  python main.py
  → 사이드바 「Personal AI」 → 질문 전송
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.ai_assistant import (
    _MAX_MESSAGE_LEN,
    ask_assistant,
    chat_with_agent,
)
from services.ai_safety_policy import assess_ai_request_safety
from services.openai_client import OpenAIKeyMissingError
from services.openai_settings_store import resolve_openai_model


class TestWorkContextDate(unittest.TestCase):
    @patch("services.work_ai_context.ws.list_todos", return_value=[])
    @patch("services.work_ai_context.ws.list_calendar_events", return_value=[])
    @patch("services.work_ai_context.ws.unread_mail_count", return_value=0)
    @patch("services.work_ai_context.ws.list_mail", return_value=[])
    @patch("services.work_ai_context.ws.list_message_threads", return_value=[])
    @patch("services.work_ai_context.ws.list_company_bulletins", return_value=[])
    def test_section_personal_uses_date_not_str(
        self,
        _b,
        _mt,
        _mail,
        _unread,
        _cal,
        _todo,
    ) -> None:
        from core.session_service import UserSession
        from services.work_ai_context import _section_personal

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="테스트",
            role="admin",
        )
        text = _section_personal(sess, ["general"])
        self.assertIn("개인 업무함", text)


class TestSafetyPolicy(unittest.TestCase):
    def test_blocks_platform_modify(self) -> None:
        r = assess_ai_request_safety("플랫폼 설정 변경해줘")
        self.assertTrue(r.blocked)

    def test_allows_payroll_query(self) -> None:
        r = assess_ai_request_safety("5월 급여 합계 알려줘")
        self.assertFalse(r.blocked)


class TestQuotaError(unittest.TestCase):
    def test_detects_quota_message(self) -> None:
        from services.openai_errors import is_quota_error

        exc = Exception(
            "Error code: 429 - insufficient_quota - You exceeded your current quota"
        )
        self.assertTrue(is_quota_error(exc))

    @patch("services.ai_assistant._call_openai_with_fallback")
    @patch("services.ai_assistant.try_handle_agent_actions")
    @patch("services.ai_assistant.try_handle_workspace_actions")
    @patch("services.ai_assistant.build_work_context")
    @patch("services.ai_assistant.load_openai_settings")
    @patch("services.ai_assistant.assess_ai_request_safety")
    @patch("services.ai_assistant.enforce_session_tenant_access")
    def test_ask_assistant_quota_falls_back_local(
        self,
        mock_enforce,
        mock_safety,
        mock_settings,
        mock_ctx,
        mock_ws,
        mock_agent,
        mock_openai,
    ) -> None:
        from core.session_service import UserSession
        from services.ai_assistant import ask_assistant
        from services.openai_errors import OpenAIQuotaError, QUOTA_USER_MESSAGE
        from services.work_ai_context import WorkContextResult

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="테스트",
            role="admin",
        )
        mock_enforce.return_value = sess
        mock_safety.return_value = type("S", (), {"blocked": False})()
        mock_settings.return_value = {"api_key": "sk-" + "x" * 40, "model": "gpt-4o-mini", "enabled": True}
        mock_ctx.return_value = WorkContextResult(
            context_text="ctx",
            direct_answer=None,
            intents=["general"],
        )
        mock_ws.return_value = type("W", (), {"changed": False, "summary_text": ""})()
        mock_agent.return_value = type("A", (), {"changed": False, "summary_lines": [], "attachment_paths": [], "context_appendix": ""})()
        mock_openai.side_effect = OpenAIQuotaError(QUOTA_USER_MESSAGE)

        result = ask_assistant("이번 분기 경영 전략을 정리해줘", session=sess)
        self.assertIn("한도", result.answer)
        self.assertIn("빗트윈", result.answer)
        self.assertEqual(result.api_mode, "local_quota_fallback")


class TestLocalDialogue(unittest.TestCase):
    def test_greeting_offline(self) -> None:
        from core.session_service import UserSession
        from services.local_agent_dialogue import try_casual_reply

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="홍길동",
            role="admin",
        )
        reply = try_casual_reply("안녕!", sess)
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertIn("반가", reply)
        self.assertIn("빗트윈", reply)

    def test_work_question_not_casual(self) -> None:
        from services.local_agent_dialogue import try_casual_reply
        from core.session_service import UserSession

        sess = UserSession(
            user_id="u",
            tenant_id="t",
            username="u",
            display_name="테스트",
            role="admin",
        )
        self.assertIsNone(try_casual_reply("5월 급여 알려줘", sess))


class TestApiKeySanitize(unittest.TestCase):
    def test_rejects_chat_paste(self) -> None:
        from services.openai_settings_store import sanitize_api_key, validate_api_key_input

        bad = "ℹ API 설정이 저장되었습니다. (OpenAI 연동됨.)"
        self.assertEqual(sanitize_api_key(bad), "")
        _clean, err = validate_api_key_input(bad)
        self.assertTrue(err)

    def test_accepts_sk_key(self) -> None:
        from services.openai_settings_store import sanitize_api_key

        key = "sk-" + "a" * 40
        self.assertEqual(sanitize_api_key(key), key)


class TestModelResolve(unittest.TestCase):
    def test_default_model(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            self.assertEqual(resolve_openai_model(None), "gpt-4o-mini")

    def test_env_overrides_user(self) -> None:
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-test-env"}):
            self.assertEqual(resolve_openai_model("gpt-user"), "gpt-test-env")


class TestChatWithAgentValidation(unittest.TestCase):
    def test_empty_message(self) -> None:
        with self.assertRaises(ValueError):
            chat_with_agent("   ")

    def test_message_too_long(self) -> None:
        with self.assertRaises(ValueError):
            chat_with_agent("x" * (_MAX_MESSAGE_LEN + 1))


class TestAskAssistantMocked(unittest.TestCase):
    @patch("services.ai_assistant._build_developer_prompt", return_value="system prompt")
    @patch("services.ai_assistant.load_openai_settings")
    @patch("services.ai_assistant.enforce_session_tenant_access")
    @patch("services.ai_assistant.require_session")
    @patch("services.ai_assistant._call_openai_with_fallback")
    @patch("services.ai_assistant.try_handle_workspace_actions")
    @patch("services.ai_assistant.try_handle_agent_actions")
    @patch("services.ai_assistant.build_work_context")
    @patch("services.ai_assistant.save_chat_turn")
    def test_openai_path_returns_answer(
        self,
        _save,
        mock_work,
        mock_agent,
        mock_ws,
        mock_openai,
        mock_req,
        mock_enforce,
        mock_settings,
        _prompt,
    ) -> None:
        sess = MagicMock(user_id="u1", tenant_id="t1", display_name="Test")
        mock_req.return_value = sess
        mock_enforce.return_value = sess
        mock_settings.return_value = {
            "api_key": "sk-test",
            "model": "gpt-5.5",
            "enabled": True,
        }
        bundle = MagicMock()
        bundle.context_text = "ctx"
        bundle.direct_answer = None
        bundle.intents = ["general"]
        mock_work.return_value = bundle
        mock_openai.return_value = ("분석 결과입니다.", "resp_123", "chat_completions")

        from services.ai_workspace_actions import WorkspaceActionResult
        from services.ai_agent_actions import AgentActionResult

        mock_ws.return_value = WorkspaceActionResult()
        mock_agent.return_value = AgentActionResult()

        result = ask_assistant("이번 분기 경영 전략을 정리해줘", session=sess)
        self.assertIn("분석 결과입니다", result.answer)
        self.assertEqual(result.api_mode, "chat_completions")
        mock_openai.assert_called_once()

    @patch("services.ai_assistant.load_openai_settings")
    @patch("services.ai_assistant.enforce_session_tenant_access")
    @patch("services.ai_assistant.require_session")
    def test_no_key_greeting_dialogue(self, mock_req, mock_enforce, mock_settings) -> None:
        sess = MagicMock(user_id="u1", tenant_id="t1", display_name="홍길동")
        mock_req.return_value = sess
        mock_enforce.return_value = sess
        mock_settings.return_value = {"api_key": "", "model": "gpt-4o-mini", "enabled": True}

        with patch("services.ai_assistant.try_handle_workspace_actions") as ws:
            with patch("services.ai_assistant.try_handle_agent_actions") as ag:
                with patch("services.ai_assistant.build_work_context") as bw:
                    from services.ai_workspace_actions import WorkspaceActionResult
                    from services.ai_agent_actions import AgentActionResult

                    ws.return_value = WorkspaceActionResult()
                    ag.return_value = AgentActionResult()
                    bw.return_value = MagicMock(
                        context_text="", direct_answer=None, intents=["general"], sections={}
                    )
                    with patch("services.ai_assistant.save_chat_turn"):
                        result = ask_assistant("안녕!", session=sess)
        self.assertEqual(result.api_mode, "local_casual")
        self.assertIn("빗트윈", result.answer)

    @patch("services.ai_assistant.load_openai_settings")
    @patch("services.ai_assistant.enforce_session_tenant_access")
    @patch("services.ai_assistant.require_session")
    def test_no_key_local_mode(self, mock_req, mock_enforce, mock_settings) -> None:
        sess = MagicMock(user_id="u1", tenant_id="t1", display_name="Test")
        mock_req.return_value = sess
        mock_enforce.return_value = sess
        mock_settings.return_value = {"api_key": "", "model": "gpt-5.5", "enabled": True}

        with patch("services.ai_assistant.try_handle_workspace_actions") as ws:
            with patch("services.ai_assistant.try_handle_agent_actions") as ag:
                with patch("services.ai_assistant.build_work_context") as bw:
                    from services.ai_workspace_actions import WorkspaceActionResult
                    from services.ai_agent_actions import AgentActionResult

                    ws.return_value = WorkspaceActionResult()
                    ag.return_value = AgentActionResult()
                    bundle = MagicMock()
                    bundle.context_text = "local ctx"
                    bundle.direct_answer = None
                    bundle.intents = ["payroll"]
                    bundle.sections = {"payroll": "급여월 2026-05"}
                    bw.return_value = bundle

                    with patch("services.ai_assistant.save_chat_turn"):
                        result = ask_assistant("급여", session=sess)
        self.assertEqual(result.api_mode, "local")
        self.assertIn("오프라인", result.answer)


class TestOpenAIKeyMissing(unittest.TestCase):
    @patch("services.ai_assistant.load_openai_settings")
    @patch("services.ai_assistant.enforce_session_tenant_access")
    @patch("services.ai_assistant.require_session")
    @patch("services.ai_assistant.build_work_context")
    def test_chat_with_agent_no_key(
        self, mock_work, mock_req, mock_enforce, mock_settings
    ) -> None:
        sess = MagicMock(user_id="u1", tenant_id="t1")
        mock_req.return_value = sess
        mock_enforce.return_value = sess
        mock_settings.return_value = {"api_key": "", "enabled": True}
        mock_work.return_value = MagicMock(
            context_text="c", intents=["general"]
        )
        with self.assertRaises(OpenAIKeyMissingError):
            chat_with_agent("hi", session=sess)


if __name__ == "__main__":
    unittest.main()
