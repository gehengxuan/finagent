"""
tests/test_llm_base.py
Unit tests for src/llms/base.py — LLMResponse, _normalize_messages, validate_response, generate.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.llms.base import (
    LLMResponse,
    BaseLLM,
    LLMError,
    APIError,
    RateLimitError,
    InvalidResponseError,
)


# ============================================================
# LLMResponse
# ============================================================

class TestLLMResponse:
    def test_content_attribute(self):
        r = LLMResponse("hello")
        assert r.content == "hello"

    def test_str(self):
        r = LLMResponse("hello")
        assert str(r) == "hello"

    def test_repr_short(self):
        r = LLMResponse("short")
        assert "short" in repr(r)

    def test_repr_long_truncated(self):
        long_text = "a" * 200
        r = LLMResponse(long_text)
        assert "..." in repr(r)
        assert len(repr(r)) < 200

    def test_empty_content(self):
        r = LLMResponse("")
        assert r.content == ""
        assert str(r) == ""


# ============================================================
# Concrete subclass for testing BaseLLM abstract methods
# ============================================================

class ConcreteLLM(BaseLLM):
    """Minimal concrete implementation for testing BaseLLM."""

    def __init__(self):
        super().__init__(api_key="test-key", model_name="test-model")

    def get_default_model(self):
        return "test-model"

    def invoke(self, messages, **kwargs):
        return LLMResponse("mock response")

    def get_model_info(self):
        return {"provider": "Test", "model": "test-model"}


# ============================================================
# _normalize_messages
# ============================================================

class TestNormalizeMessages:
    def setup_method(self):
        self.llm = ConcreteLLM()

    def test_dict_messages_pass_through(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        result = self.llm._normalize_messages(messages)
        assert result == messages

    def test_langchain_system_message(self):
        msg = MagicMock()
        msg.content = "System prompt"
        msg.type = "system"
        result = self.llm._normalize_messages([msg])
        assert result == [{"role": "system", "content": "System prompt"}]

    def test_langchain_human_message(self):
        msg = MagicMock()
        msg.content = "User question"
        msg.type = "human"
        result = self.llm._normalize_messages([msg])
        assert result == [{"role": "user", "content": "User question"}]

    def test_langchain_ai_message(self):
        msg = MagicMock()
        msg.content = "AI reply"
        msg.type = "ai"
        result = self.llm._normalize_messages([msg])
        assert result == [{"role": "assistant", "content": "AI reply"}]

    def test_unknown_type_defaults_to_user(self):
        msg = MagicMock()
        msg.content = "Something"
        msg.type = "unknown_type"
        result = self.llm._normalize_messages([msg])
        assert result[0]["role"] == "user"

    def test_plain_string_fallback(self):
        result = self.llm._normalize_messages(["just a string"])
        assert result == [{"role": "user", "content": "just a string"}]

    def test_mixed_types(self):
        dict_msg = {"role": "system", "content": "sys"}
        lc_msg = MagicMock()
        lc_msg.content = "user_msg"
        lc_msg.type = "human"

        result = self.llm._normalize_messages([dict_msg, lc_msg])
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"


# ============================================================
# validate_response
# ============================================================

class TestValidateResponse:
    def setup_method(self):
        self.llm = ConcreteLLM()

    def test_strips_whitespace(self):
        assert self.llm.validate_response("  hello  ") == "hello"

    def test_none_returns_empty(self):
        assert self.llm.validate_response(None) == ""

    def test_empty_string(self):
        assert self.llm.validate_response("") == ""


# ============================================================
# generate (simple wrapper)
# ============================================================

class TestGenerate:
    def test_calls_invoke_and_returns_content(self):
        llm = ConcreteLLM()
        result = llm.generate("test prompt")
        assert result == "mock response"


# ============================================================
# Utility methods / properties
# ============================================================

class TestBaseLLMUtils:
    def test_str(self):
        llm = ConcreteLLM()
        s = str(llm)
        assert "Test" in s
        assert "test-model" in s

    def test_repr(self):
        llm = ConcreteLLM()
        r = repr(llm)
        assert "ConcreteLLM" in r

    def test_supports_native_tools_default_false(self):
        llm = ConcreteLLM()
        assert llm.supports_native_tools() is False

    def test_generate_with_tools_warns(self, capsys):
        llm = ConcreteLLM()
        result = llm.generate_with_tools("prompt", tools=[])
        captured = capsys.readouterr()
        assert "未实现" in captured.out or "warning" in captured.out.lower() or "警告" in captured.out
        assert result["content"] == ""
        assert result["tool_calls"] == []


# ============================================================
# Exception hierarchy
# ============================================================

class TestExceptions:
    def test_llm_error_is_exception(self):
        assert issubclass(LLMError, Exception)

    def test_api_error_inherits(self):
        assert issubclass(APIError, LLMError)

    def test_rate_limit_inherits(self):
        assert issubclass(RateLimitError, LLMError)

    def test_invalid_response_inherits(self):
        assert issubclass(InvalidResponseError, LLMError)
