"""
tests/test_state.py
Unit tests for src/state/state.py — reducer functions.
"""

import pytest
from src.state.state import reduce_query, reduce_list


# ============================================================
# reduce_query
# ============================================================

class TestReduceQuery:
    def test_right_overrides_left(self):
        assert reduce_query("old", "new") == "new"

    def test_right_none_keeps_left(self):
        assert reduce_query("old", None) == "old"

    def test_both_none_returns_empty(self):
        assert reduce_query(None, None) == ""

    def test_left_none_right_set(self):
        assert reduce_query(None, "right") == "right"

    def test_empty_right_overrides(self):
        """Empty string is not None — should override."""
        assert reduce_query("old", "") == ""


# ============================================================
# reduce_list
# ============================================================

class TestReduceList:
    def test_merges_two_lists(self):
        assert reduce_list([1, 2], [3, 4]) == [1, 2, 3, 4]

    def test_left_none(self):
        assert reduce_list(None, [1, 2]) == [1, 2]

    def test_right_none(self):
        assert reduce_list([1, 2], None) == [1, 2]

    def test_both_none(self):
        assert reduce_list(None, None) == []

    def test_empty_lists(self):
        assert reduce_list([], []) == []

    def test_preserves_order(self):
        assert reduce_list(["a", "b"], ["c"]) == ["a", "b", "c"]

    def test_does_not_deduplicate(self):
        """reduce_list is a simple concat — duplicates are allowed."""
        assert reduce_list([1], [1]) == [1, 1]
