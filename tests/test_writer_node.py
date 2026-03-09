"""
tests/test_writer_node.py
Unit tests for src/nodes/writer_node.py

Tests cover:
- First draft path (uses SYSTEM_PROMPT_FIRST_SUMMARY)
- Rewrite path (uses SYSTEM_PROMPT_REWRITE with structured errors + previous draft)
- Table/financial formatting injection
- Error handling
- Edge cases (string search results, deduplication, empty errors)
"""

import json
import pytest
from src.nodes.writer_node import write_section_node


class TestWriteSectionNode:
    def _make_state(self, critique=None, errors=None, iteration=0,
                    current_content=""):
        return {
            "query": "比亚迪 (002594) 深度研究",
            "section_def": {
                "title": "1. 核心结论",
                "content": "分析比亚迪的投资逻辑。"
            },
            "search_results": [
                {"title": "Report", "content": "Revenue 6023亿", "url": "https://x.com/1"},
            ],
            "current_content": current_content,
            "critique": critique,
            "iteration_count": iteration,
            "is_satisfactory": False,
            "reflection_errors": errors or [],
            "completed_sections": [],
            "feedback_search_query": None,
        }

    # ============================================================
    # First draft path
    # ============================================================

    def test_first_draft(self, mock_llm):
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "## 核心结论\n\n比亚迪表现优异。"
        }))
        state = self._make_state()
        result = write_section_node(state, mock_llm)
        assert result["current_content"] == "## 核心结论\n\n比亚迪表现优异。"
        assert result["iteration_count"] == 1

    def test_first_draft_uses_first_summary_prompt(self, mock_llm):
        """First draft should use SYSTEM_PROMPT_FIRST_SUMMARY (not rewrite)."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "draft"}))
        state = self._make_state()
        write_section_node(state, mock_llm)
        system_content = mock_llm.last_messages[0].content
        # SYSTEM_PROMPT_FIRST_SUMMARY contains "核心写作规范", rewrite does not
        assert "核心写作规范" in system_content
        assert "修改原则" not in system_content

    def test_first_draft_input_has_search_query(self, mock_llm):
        """First draft input should have search_query, not errors/paragraph."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "draft"}))
        state = self._make_state()
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "search_query" in input_data
        assert "errors" not in input_data
        assert "paragraph_latest_state" not in input_data

    # ============================================================
    # Rewrite path
    # ============================================================

    def test_rewrite_with_critique(self, mock_llm):
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "## 核心结论（修改版）"
        }))
        state = self._make_state(
            critique="【总体评价】需要更多数据",
            errors=[{"severity": "major", "type": "data_missing",
                     "location": "全文", "description": "缺少营收数据",
                     "fix_suggestion": "补充6023亿营收"}],
            iteration=1,
            current_content="## 核心结论\n\n旧草稿内容。",
        )
        result = write_section_node(state, mock_llm)
        assert result["current_content"] == "## 核心结论（修改版）"
        assert result["iteration_count"] == 2

    def test_rewrite_uses_rewrite_prompt(self, mock_llm):
        """Rewrite should use SYSTEM_PROMPT_REWRITE (not first summary)."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        state = self._make_state(
            critique="需要修改",
            errors=[{"severity": "major", "type": "data_missing"}],
            current_content="old draft",
        )
        write_section_node(state, mock_llm)
        system_content = mock_llm.last_messages[0].content
        # SYSTEM_PROMPT_REWRITE contains "修改原则", first summary does not
        assert "修改原则" in system_content
        assert "核心写作规范" not in system_content

    def test_rewrite_passes_previous_draft(self, mock_llm):
        """Rewrite input should include the current draft as paragraph_latest_state."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        old_draft = "## 核心结论\n\n旧草稿，需要补充数据。"
        state = self._make_state(
            critique="需要修改",
            errors=[{"severity": "minor", "type": "citation_missing"}],
            current_content=old_draft,
        )
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert input_data["paragraph_latest_state"] == old_draft

    def test_rewrite_passes_structured_errors(self, mock_llm):
        """Rewrite input should include the structured errors list."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        errors = [
            {"severity": "critical", "type": "hallucination_risk",
             "location": "第三段", "description": "数据无来源",
             "fix_suggestion": "删除或替换"},
            {"severity": "minor", "type": "citation_missing",
             "location": "第一段", "description": "缺少引用"},
        ]
        state = self._make_state(
            critique="需要修改",
            errors=errors,
            current_content="some draft",
        )
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "errors" in input_data
        assert len(input_data["errors"]) == 2
        # Verify error structure preserved
        assert input_data["errors"][0]["type"] == "hallucination_risk"

    def test_rewrite_sorts_errors_by_severity(self, mock_llm):
        """Errors should be sorted critical -> major -> minor in the input."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        errors = [
            {"severity": "minor", "type": "citation_missing"},
            {"severity": "critical", "type": "hallucination_risk"},
            {"severity": "major", "type": "data_missing"},
            {"severity": "minor", "type": "format_violation"},
        ]
        state = self._make_state(
            critique="需要修改",
            errors=errors,
            current_content="draft",
        )
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        severities = [e["severity"] for e in input_data["errors"]]
        assert severities == ["critical", "major", "minor", "minor"]

    def test_rewrite_no_search_query_in_input(self, mock_llm):
        """Rewrite input should NOT have search_query (that's first-draft only)."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        state = self._make_state(
            critique="需要修改",
            errors=[],
            current_content="draft",
        )
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "search_query" not in input_data

    def test_rewrite_empty_errors_still_uses_rewrite_prompt(self, mock_llm):
        """Even with empty errors list (e.g. reflector exception), rewrite prompt is used."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "fixed"}))
        state = self._make_state(
            critique="反思节点异常: timeout",
            errors=[],
            current_content="draft",
        )
        write_section_node(state, mock_llm)
        system_content = mock_llm.last_messages[0].content
        assert "修改原则" in system_content

    # ============================================================
    # Table / financial injection (both paths)
    # ============================================================

    def test_table_instruction_injection(self, mock_llm):
        """If instruction mentions 表格, special formatting should be appended."""
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "| 指标 | 值 |\n|---|---|\n| 营收 | 6023亿 |"
        }))
        state = self._make_state()
        state["section_def"]["content"] = "请使用表格展示财务数据。"
        result = write_section_node(state, mock_llm)
        assert result["current_content"] is not None
        # Verify the formatting constraint is in the input
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "强格式约束" in input_data["content"]

    def test_financial_title_injection(self, mock_llm):
        """If title contains 财务, special formatting should be injected."""
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "Content with table"
        }))
        state = self._make_state()
        state["section_def"]["title"] = "3. 财务分析"
        result = write_section_node(state, mock_llm)
        assert result["current_content"] == "Content with table"
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "强格式约束" in input_data["content"]

    def test_table_injection_in_rewrite(self, mock_llm):
        """Table formatting constraint should also apply in rewrite mode."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "table draft"}))
        state = self._make_state(
            critique="需要表格",
            errors=[{"severity": "major", "type": "format_violation"}],
            current_content="old draft without table",
        )
        state["section_def"]["content"] = "请使用表格展示数据。"
        write_section_node(state, mock_llm)
        input_data = json.loads(mock_llm.last_messages[1].content)
        assert "强格式约束" in input_data["content"]

    # ============================================================
    # Error handling
    # ============================================================

    def test_handles_exception(self):
        """If LLM raises, should return error message."""
        class ErrorLLM:
            def invoke(self, messages, **kwargs):
                raise RuntimeError("API down")

        state = self._make_state()
        result = write_section_node(state, ErrorLLM())
        assert "失败" in result["current_content"]

    # ============================================================
    # Edge cases
    # ============================================================

    def test_string_search_results(self, mock_llm):
        """Should handle legacy string-format search results."""
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "Draft content"
        }))
        state = self._make_state()
        state["search_results"] = ["plain text result"]
        result = write_section_node(state, mock_llm)
        assert result["current_content"] == "Draft content"

    def test_deduplication_applied(self, mock_llm):
        """Duplicate search results should be deduplicated before formatting."""
        mock_llm.set_response(json.dumps({
            "paragraph_latest_state": "Draft"
        }))
        state = self._make_state()
        state["search_results"] = [
            {"title": "A", "content": "C1", "url": "https://a.com"},
            {"title": "A", "content": "C1 dup", "url": "https://a.com"},
        ]
        result = write_section_node(state, mock_llm)
        # We can't directly observe dedup in the output, but we verify no crash
        assert result["current_content"] == "Draft"

    def test_call_count_tracking(self, mock_llm):
        """MockLLM should track call count correctly."""
        mock_llm.set_response(json.dumps({"paragraph_latest_state": "d"}))
        state = self._make_state()
        write_section_node(state, mock_llm)
        assert mock_llm.call_count == 1
