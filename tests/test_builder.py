"""
tests/test_builder.py
Unit tests for builder.py — specifically _deduplicate_consecutive_citations.
"""

import pytest
from src.graph.builder import MainGraphBuilder


class TestDeduplicateConsecutiveCitations:
    """
    Test the citation dedup method on MainGraphBuilder.
    We instantiate it with dummy args since we only need the method.
    """

    def setup_method(self):
        # MainGraphBuilder.__init__ just assigns attributes — safe with None
        self.builder = MainGraphBuilder.__new__(MainGraphBuilder)

    # --- Double bracket [[N]] format ---

    def test_double_bracket_adjacent_dup(self):
        text = "数据显示 [[1]] [[1]] [[2]] 增长强劲"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert "[[1]] [[2]]" in result
        assert result.count("[[1]]") == 1

    def test_double_bracket_with_separator(self):
        text = "来源 [[4]]、[[4]]、[[9]]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.count("[[4]]") == 1
        assert "[[9]]" in result

    def test_double_bracket_interleaved_dup(self):
        text = "数据 [[4]] [[5]] [[7]] [[4]] 显示"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.count("[[4]]") == 1
        assert "[[5]]" in result
        assert "[[7]]" in result

    def test_double_bracket_no_dups(self):
        text = "引用 [[1]] [[2]] [[3]]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result == text

    # --- Single bracket [N] format ---

    def test_single_bracket_adjacent_dup(self):
        text = "见 [1] [1] [2]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.count("[1]") == 1
        assert "[2]" in result

    def test_single_bracket_no_dups(self):
        text = "见 [1] [2] [3]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result == text

    # --- Mixed / edge cases ---

    def test_no_citations(self):
        text = "This is plain text without any citations."
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result == text

    def test_empty_string(self):
        result = self.builder._deduplicate_consecutive_citations("")
        assert result == ""

    def test_single_citation(self):
        text = "Only [[1]] here."
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result == text

    def test_triple_duplicate(self):
        text = "[[3]] [[3]] [[3]]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.count("[[3]]") == 1

    def test_comma_separated_dups(self):
        text = "数据 [[2]], [[2]], [[5]]"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.count("[[2]]") == 1
        assert "[[5]]" in result

    def test_preserves_surrounding_text(self):
        text = "前文 [[1]] [[1]] 后文"
        result = self.builder._deduplicate_consecutive_citations(text)
        assert result.startswith("前文")
        assert result.endswith("后文")
        assert result.count("[[1]]") == 1
