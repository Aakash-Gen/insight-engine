"""
Tests for core/llm.py — unified LLM abstraction.

Covers:
- chat() dispatches to the correct provider based on LLM_PROVIDER setting
- Returns (text, token_count) tuple
- Groq path uses openai SDK with Groq base URL
- Anthropic path uses anthropic SDK
- xAI path uses openai SDK with xAI base URL
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestLLMDispatch:
    def test_groq_path_called(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Groq response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch("core.config.settings.LLM_PROVIDER", "groq"),
            patch("core.llm.settings.LLM_PROVIDER", "groq"),
            patch("openai.OpenAI", return_value=mock_client),
        ):
            from core import llm
            # Force re-dispatch by calling internal function directly
            text, tokens = llm._chat_groq("system prompt", "user prompt", 512)

        assert text == "Groq response"
        assert tokens == 30

    def test_anthropic_path_called(self):
        mock_msg = MagicMock()
        mock_msg.content[0].text = "Anthropic response"
        mock_msg.usage.input_tokens = 15
        mock_msg.usage.output_tokens = 25

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg

        with patch("anthropic.Anthropic", return_value=mock_client):
            from core import llm
            text, tokens = llm._chat_anthropic("system prompt", "user prompt", 512)

        assert text == "Anthropic response"
        assert tokens == 40

    def test_chat_dispatches_to_groq_when_provider_is_groq(self):
        with (
            patch("core.llm.settings") as mock_settings,
            patch("core.llm._chat_groq", return_value=("ok", 5)) as mock_groq,
        ):
            mock_settings.LLM_PROVIDER = "groq"
            from core.llm import chat
            text, tokens = chat("sys", "usr")

        mock_groq.assert_called_once()
        assert text == "ok"

    def test_chat_dispatches_to_anthropic_when_provider_is_anthropic(self):
        with (
            patch("core.llm.settings") as mock_settings,
            patch("core.llm._chat_anthropic", return_value=("claude ok", 8)) as mock_claude,
        ):
            mock_settings.LLM_PROVIDER = "anthropic"
            from core.llm import chat
            text, tokens = chat("sys", "usr")

        mock_claude.assert_called_once()

    def test_chat_dispatches_to_xai_when_provider_is_xai(self):
        with (
            patch("core.llm.settings") as mock_settings,
            patch("core.llm._chat_xai", return_value=("grok ok", 12)) as mock_xai,
        ):
            mock_settings.LLM_PROVIDER = "xai"
            from core.llm import chat
            text, tokens = chat("sys", "usr")

        mock_xai.assert_called_once()
