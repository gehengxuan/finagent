"""
tests/conftest.py
Shared fixtures for all test modules.

IMPORTANT: We mock heavy external dependencies (langgraph, langchain_core, openai)
before any src.* imports happen, because src/__init__.py triggers the full import chain.
"""

import sys
import os
import json
import types
import pytest
from unittest.mock import MagicMock

# ==============================================================
# Pre-import mocking of heavy/missing dependencies
# ==============================================================
# These mocks must happen BEFORE any `from src.*` import.

def _ensure_mock_module(name):
    """Register a MagicMock as a sys.modules entry if the real module is missing."""
    if name not in sys.modules:
        sys.modules[name] = MagicMock()

# langgraph
_ensure_mock_module("langgraph")
_ensure_mock_module("langgraph.graph")
_ensure_mock_module("langgraph.constants")

# langchain_core
_ensure_mock_module("langchain_core")
_ensure_mock_module("langchain_core.messages")

# We need real-ish SystemMessage / HumanMessage for nodes that construct them
class _FakeMessage:
    def __init__(self, content=""):
        self.content = content

# Patch into the mock so `from langchain_core.messages import SystemMessage` works
lc_messages = sys.modules["langchain_core.messages"]
lc_messages.SystemMessage = type("SystemMessage", (_FakeMessage,), {"type": "system"})
lc_messages.HumanMessage = type("HumanMessage", (_FakeMessage,), {"type": "human"})
lc_messages.AIMessage = type("AIMessage", (_FakeMessage,), {"type": "ai"})

# openai (for LLM subclass __init__ that creates OpenAI client)
_ensure_mock_module("openai")

# Ensure project root is on sys.path so `src.*` imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================
# Mock LLM
# ==============================================================

class MockLLMResponse:
    """Lightweight stand-in for LLMResponse."""
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content


class MockLLM:
    """
    A configurable mock LLM that returns pre-set JSON responses.
    Captures the last invocation's messages and kwargs for test assertions.

    Usage:
        llm = MockLLM(response_content='{"key": "value"}')
        result = llm.invoke(messages)
        assert result.content == '{"key": "value"}'
        assert llm.last_messages is not None  # inspect what was sent
    """

    def __init__(self, response_content: str = "{}"):
        self._response = response_content
        self.last_messages = None
        self.last_kwargs = None
        self.call_count = 0

    def set_response(self, content: str):
        self._response = content

    def invoke(self, messages, **kwargs):
        self.last_messages = messages
        self.last_kwargs = kwargs
        self.call_count += 1
        return MockLLMResponse(self._response)


@pytest.fixture
def mock_llm():
    """Provide a MockLLM instance (default empty JSON)."""
    return MockLLM()


# ==============================================================
# Common state fixtures
# ==============================================================

@pytest.fixture
def sample_section_state():
    """A minimal SectionState dict suitable for node tests."""
    return {
        "query": "比亚迪 (002594) 深度研究",
        "section_def": {
            "title": "1. 核心结论与预期差",
            "content": "请从短期和长期两个维度分析比亚迪的投资逻辑。"
        },
        "search_results": [
            {
                "title": "比亚迪2024年报",
                "content": "2024年比亚迪营收达到6023亿元，同比增长33.3%。",
                "url": "https://example.com/byd-2024"
            },
            {
                "title": "新能源汽车行业报告",
                "content": "比亚迪在新能源汽车市场占有率约为35%。",
                "url": "https://example.com/nev-report"
            }
        ],
        "current_content": "## 核心结论\n\n比亚迪2024年营收达到6023亿元 [[1]]，市占率约35% [[2]]。",
        "critique": None,
        "iteration_count": 0,
        "is_satisfactory": False,
        "reflection_errors": [],
        "completed_sections": [],
        "feedback_search_query": None,
    }


@pytest.fixture
def sample_search_results():
    """A list of search result dicts for dedup / formatting tests."""
    return [
        {"title": "Doc A", "content": "Content A", "url": "https://a.com/1"},
        {"title": "Doc B", "content": "Content B", "url": "https://b.com/2"},
        {"title": "Doc A", "content": "Content A duplicate", "url": "https://a.com/1"},
        {"title": "Doc C", "content": "Content C", "url": ""},
    ]
