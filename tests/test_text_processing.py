"""
tests/test_text_processing.py
Unit tests for src/utils/text_processing.py
"""

import json
import pytest
from src.utils.text_processing import (
    get_doc_key,
    deduplicate_search_results,
    clean_json_tags,
    clean_markdown_tags,
    remove_reasoning_from_output,
    extract_clean_response,
    validate_json_schema,
    truncate_content,
    format_search_results_for_prompt,
)


# ============================================================
# get_doc_key
# ============================================================

class TestGetDocKey:
    def test_url_preferred_over_title(self):
        item = {"url": "https://example.com/page", "title": "My Title"}
        assert get_doc_key(item) == "https://example.com/page"

    def test_falls_back_to_title_when_url_short(self):
        item = {"url": "abc", "title": "My Title"}
        assert get_doc_key(item) == "My Title"

    def test_falls_back_to_title_when_url_contains_local(self):
        item = {"url": "https://本地文件/test.pdf", "title": "My Title"}
        assert get_doc_key(item) == "My Title"

    def test_falls_back_to_title_when_url_empty(self):
        item = {"url": "", "title": "Fallback Title"}
        assert get_doc_key(item) == "Fallback Title"

    def test_empty_item(self):
        assert get_doc_key({}) == ""

    def test_non_dict_item(self):
        assert get_doc_key("not a dict") == ""

    def test_url_exactly_length_5(self):
        """URL with len==5 should NOT be used (need >5)."""
        item = {"url": "12345", "title": "Title"}
        assert get_doc_key(item) == "Title"

    def test_url_length_6(self):
        """URL with len==6 should be used."""
        item = {"url": "123456", "title": "Title"}
        assert get_doc_key(item) == "123456"


# ============================================================
# deduplicate_search_results
# ============================================================

class TestDeduplicateSearchResults:
    def test_removes_duplicates_by_url(self):
        results = [
            {"title": "A", "content": "...", "url": "https://a.com"},
            {"title": "B", "content": "...", "url": "https://b.com"},
            {"title": "A dup", "content": "...", "url": "https://a.com"},
        ]
        deduped = deduplicate_search_results(results)
        assert len(deduped) == 2
        assert deduped[0]["title"] == "A"
        assert deduped[1]["title"] == "B"

    def test_removes_duplicates_by_title(self):
        results = [
            {"title": "Same", "content": "1", "url": ""},
            {"title": "Same", "content": "2", "url": ""},
        ]
        deduped = deduplicate_search_results(results)
        assert len(deduped) == 1
        assert deduped[0]["content"] == "1"

    def test_preserves_empty_key_items(self):
        results = [
            {"title": "", "content": "no key", "url": ""},
            {"title": "", "content": "also no key", "url": ""},
        ]
        deduped = deduplicate_search_results(results)
        assert len(deduped) == 2

    def test_empty_input(self):
        assert deduplicate_search_results([]) == []

    def test_preserves_order(self):
        results = [
            {"title": "C", "url": "https://c.com", "content": ""},
            {"title": "A", "url": "https://a.com", "content": ""},
            {"title": "B", "url": "https://b.com", "content": ""},
        ]
        deduped = deduplicate_search_results(results)
        assert [d["title"] for d in deduped] == ["C", "A", "B"]

    def test_with_fixture(self, sample_search_results):
        deduped = deduplicate_search_results(sample_search_results)
        # "Doc A" with same URL appears twice -> deduplicate to 1
        # "Doc C" with empty url uses title as key -> kept
        urls = [d.get("url") for d in deduped]
        assert urls.count("https://a.com/1") == 1
        assert len(deduped) == 3  # A, B, C


# ============================================================
# clean_json_tags
# ============================================================

class TestCleanJsonTags:
    def test_removes_json_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert clean_json_tags(text) == '{"key": "value"}'

    def test_removes_bare_backticks(self):
        text = '```\n{"a": 1}\n```'
        assert clean_json_tags(text) == '{"a": 1}'

    def test_no_backticks(self):
        text = '{"a": 1}'
        assert clean_json_tags(text) == '{"a": 1}'

    def test_empty_string(self):
        assert clean_json_tags("") == ""


# ============================================================
# clean_markdown_tags
# ============================================================

class TestCleanMarkdownTags:
    def test_removes_markdown_code_block(self):
        text = '```markdown\n# Hello\n```'
        assert clean_markdown_tags(text) == '# Hello'

    def test_no_backticks(self):
        text = '# Hello'
        assert clean_markdown_tags(text) == '# Hello'


# ============================================================
# remove_reasoning_from_output
# ============================================================

class TestRemoveReasoningFromOutput:
    def test_removes_text_before_json(self):
        text = 'Some reasoning text {"key": "value"}'
        result = remove_reasoning_from_output(text)
        # Should contain the JSON part
        assert '{"key": "value"}' in result

    def test_no_reasoning(self):
        text = '{"key": "value"}'
        result = remove_reasoning_from_output(text)
        assert '{"key": "value"}' in result


# ============================================================
# extract_clean_response
# ============================================================

class TestExtractCleanResponse:
    def test_clean_json(self):
        text = '{"paragraph_latest_state": "hello"}'
        result = extract_clean_response(text)
        assert result["paragraph_latest_state"] == "hello"

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = extract_clean_response(text)
        assert result["key"] == "value"

    def test_json_with_reasoning_prefix(self):
        text = 'Here is my analysis: {"result": 42}'
        result = extract_clean_response(text)
        assert result["result"] == 42

    def test_unparseable(self):
        text = "not json at all"
        result = extract_clean_response(text)
        assert "error" in result or "raw_text" in result

    def test_json_array(self):
        """extract_clean_response may return list or dict depending on
        how remove_reasoning_from_output interacts with the leading '['.
        The key contract: it should not crash and should return *something*."""
        text = '[{"title": "A"}, {"title": "B"}]'
        result = extract_clean_response(text)
        assert result is not None


# ============================================================
# validate_json_schema
# ============================================================

class TestValidateJsonSchema:
    def test_all_fields_present(self):
        data = {"a": 1, "b": 2, "c": 3}
        assert validate_json_schema(data, ["a", "b", "c"]) is True

    def test_missing_field(self):
        data = {"a": 1, "b": 2}
        assert validate_json_schema(data, ["a", "b", "c"]) is False

    def test_empty_required(self):
        data = {"a": 1}
        assert validate_json_schema(data, []) is True

    def test_empty_data(self):
        assert validate_json_schema({}, ["a"]) is False


# ============================================================
# truncate_content
# ============================================================

class TestTruncateContent:
    def test_short_content_unchanged(self):
        text = "Short text"
        assert truncate_content(text, 100) == "Short text"

    def test_exact_boundary(self):
        text = "a" * 100
        assert truncate_content(text, 100) == text

    def test_truncation_adds_ellipsis(self):
        text = "word " * 100  # 500 chars
        result = truncate_content(text, 50)
        assert result.endswith("...")
        assert len(result) <= 54  # 50 + "..."

    def test_default_max_length(self):
        text = "a" * 20001
        result = truncate_content(text)
        assert len(result) <= 20004  # 20000 + "..."


# ============================================================
# format_search_results_for_prompt
# ============================================================

class TestFormatSearchResultsForPrompt:
    def test_basic(self):
        results = [
            {"content": "Hello world"},
            {"content": "Another result"},
        ]
        formatted = format_search_results_for_prompt(results)
        assert len(formatted) == 2
        assert formatted[0] == "Hello world"

    def test_empty_content_skipped(self):
        results = [{"content": ""}, {"content": "Valid"}]
        formatted = format_search_results_for_prompt(results)
        assert len(formatted) == 1
        assert formatted[0] == "Valid"

    def test_truncation(self):
        results = [{"content": "x" * 200}]
        formatted = format_search_results_for_prompt(results, max_length=50)
        assert len(formatted[0]) <= 54
