"""
tests/test_reflector_node.py
Unit tests for src/nodes/reflector_node.py
"""

import json
import pytest
from src.nodes.reflector_node import (
    _format_search_results_for_reflect,
    _build_critique_text,
    should_continue,
    reflector_node,
)


# ============================================================
# _format_search_results_for_reflect
# ============================================================

class TestFormatSearchResultsForReflect:
    def test_dict_items(self):
        data = [
            {"title": "Source A", "url": "https://a.com", "content": "Content A"},
            {"title": "Source B", "url": "https://b.com", "content": "Content B"},
        ]
        result = _format_search_results_for_reflect(data)
        assert len(result) == 2
        assert "Reference [1]" in result[0]
        assert "Source: Source A" in result[0]
        assert "Content: Content A" in result[0]
        assert "Reference [2]" in result[1]

    def test_string_items(self):
        data = ["Plain text content"]
        result = _format_search_results_for_reflect(data)
        assert len(result) == 1
        assert "Reference [1]" in result[0]
        assert "Content: Plain text content" in result[0]
        assert "未知来源" in result[0]

    def test_empty_list(self):
        assert _format_search_results_for_reflect([]) == []

    def test_missing_fields(self):
        data = [{"content": "Only content"}]
        result = _format_search_results_for_reflect(data)
        assert "未知来源" in result[0]
        assert "Content: Only content" in result[0]


# ============================================================
# _build_critique_text
# ============================================================

class TestBuildCritiqueText:
    def test_sorts_by_severity(self):
        errors = [
            {"severity": "minor", "type": "format_violation", "location": "table",
             "description": "wrong format", "fix_suggestion": "fix it"},
            {"severity": "critical", "type": "hallucination_risk", "location": "para 1",
             "description": "made up data", "fix_suggestion": "remove"},
            {"severity": "major", "type": "data_missing", "location": "para 2",
             "description": "missing revenue", "fix_suggestion": "add data"},
        ]
        text = _build_critique_text(errors, "Needs work")
        lines = text.split("\n")
        # Critical should come before major, major before minor
        crit_pos = text.index("CRITICAL")
        major_pos = text.index("MAJOR")
        minor_pos = text.index("MINOR")
        assert crit_pos < major_pos < minor_pos

    def test_overall_assessment_included(self):
        text = _build_critique_text([], "All good")
        assert "All good" in text

    def test_empty_errors_still_has_header(self):
        text = _build_critique_text([], "Assessment")
        assert "总体评价" in text
        assert "结构化错误清单" in text

    def test_fix_suggestion_optional(self):
        errors = [
            {"severity": "minor", "type": "data_missing", "location": "para 1",
             "description": "something", "fix_suggestion": ""},
        ]
        text = _build_critique_text(errors, "ok")
        # fix_suggestion is empty, so "修复:" line should NOT appear
        assert "修复: " not in text or "修复: \n" not in text


# ============================================================
# should_continue
# ============================================================

class TestShouldContinue:
    def _make_state(self, iteration=0, is_satisfactory=False, errors=None,
                    feedback_query=None):
        return {
            "query": "test",
            "section_def": {"title": "T", "content": "C"},
            "search_results": [],
            "current_content": "draft",
            "critique": "some critique" if not is_satisfactory else None,
            "iteration_count": iteration,
            "is_satisfactory": is_satisfactory,
            "reflection_errors": errors or [],
            "completed_sections": [],
            "feedback_search_query": feedback_query,
        }

    def test_max_iterations_returns_end(self):
        state = self._make_state(iteration=10)
        assert should_continue(state) == "end"

    def test_satisfactory_returns_end(self):
        state = self._make_state(is_satisfactory=True)
        assert should_continue(state) == "end"

    def test_feedback_query_returns_search(self):
        state = self._make_state(feedback_query="补搜 比亚迪")
        assert should_continue(state) == "search"

    def test_no_query_returns_rewrite(self):
        state = self._make_state(
            errors=[{"severity": "major", "type": "data_missing"}]
        )
        assert should_continue(state) == "rewrite"

    def test_only_minor_after_2_iterations_returns_end(self):
        state = self._make_state(
            iteration=2,
            errors=[
                {"severity": "minor", "type": "format_violation"},
                {"severity": "minor", "type": "data_missing"},
            ]
        )
        assert should_continue(state) == "end"

    def test_critical_after_2_iterations_continues(self):
        state = self._make_state(
            iteration=2,
            errors=[
                {"severity": "critical", "type": "hallucination_risk"},
                {"severity": "minor", "type": "format_violation"},
            ]
        )
        # Has critical error + no feedback_search_query → rewrite
        assert should_continue(state) == "rewrite"

    def test_minor_only_at_iteration_1_continues(self):
        """Only-minor shortcut requires iteration >= 2."""
        state = self._make_state(
            iteration=1,
            errors=[{"severity": "minor", "type": "format_violation"}]
        )
        assert should_continue(state) == "rewrite"


# ============================================================
# reflector_node (integration with mock LLM)
# ============================================================

class TestReflectorNode:
    def test_satisfactory_response(self, mock_llm, sample_section_state):
        mock_llm.set_response(json.dumps({
            "is_satisfactory": True,
            "errors": [],
            "search_queries": [],
            "overall_assessment": "Quality is good."
        }))
        result = reflector_node(sample_section_state, mock_llm)
        assert result["is_satisfactory"] is True
        assert result["critique"] is None
        assert result["reflection_errors"] == []

    def test_unsatisfactory_response_with_errors(self, mock_llm, sample_section_state):
        mock_llm.set_response(json.dumps({
            "is_satisfactory": False,
            "errors": [
                {
                    "type": "data_missing",
                    "severity": "major",
                    "location": "paragraph 1",
                    "description": "Revenue growth rate not cited",
                    "fix_suggestion": "Add 33.3% growth figure"
                }
            ],
            "search_queries": [],
            "overall_assessment": "Needs more data."
        }))
        result = reflector_node(sample_section_state, mock_llm)
        assert result["is_satisfactory"] is False
        assert result["critique"] is not None
        assert "MAJOR" in result["critique"]
        assert len(result["reflection_errors"]) == 1

    def test_with_search_query(self, mock_llm, sample_section_state):
        mock_llm.set_response(json.dumps({
            "is_satisfactory": False,
            "errors": [
                {"type": "data_missing", "severity": "critical", "location": "all",
                 "description": "Missing competitor data", "fix_suggestion": "Search for it"}
            ],
            "search_queries": ["比亚迪 竞品分析 2024"],
            "overall_assessment": "Needs competitor data."
        }))
        result = reflector_node(sample_section_state, mock_llm)
        assert result["feedback_search_query"] == "比亚迪 竞品分析 2024"

    def test_handles_exception(self, mock_llm, sample_section_state):
        """If LLM raises, reflector_node should return error gracefully."""
        class ErrorLLM:
            def invoke(self, messages, **kwargs):
                raise RuntimeError("API down")

        result = reflector_node(sample_section_state, ErrorLLM())
        assert result["is_satisfactory"] is False
        assert "异常" in result["critique"]

    def test_empty_search_results(self, mock_llm):
        """reflector_node should work even with no search results."""
        state = {
            "query": "test",
            "section_def": {"title": "T", "content": "C"},
            "search_results": [],
            "current_content": "Some draft.",
            "critique": None,
            "iteration_count": 0,
            "is_satisfactory": False,
            "reflection_errors": [],
            "completed_sections": [],
            "feedback_search_query": None,
        }
        mock_llm.set_response(json.dumps({
            "is_satisfactory": True,
            "errors": [],
            "search_queries": [],
            "overall_assessment": "OK"
        }))
        result = reflector_node(state, mock_llm)
        assert result["is_satisfactory"] is True
