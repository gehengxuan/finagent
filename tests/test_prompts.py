"""
tests/test_prompts.py
Smoke tests to verify prompt schemas and system prompts are well-formed.
"""

import json
import pytest
from src.prompts.prompts import (
    output_schema_report_structure,
    input_schema_first_search,
    output_schema_first_search,
    input_schema_first_summary,
    output_schema_first_summary,
    input_schema_reflection,
    output_schema_reflection,
    input_schema_reflection_summary,
    output_schema_reflection_summary,
    input_schema_rewrite,
    input_schema_report_formatting,
    SYSTEM_PROMPT_FIRST_SEARCH,
    SYSTEM_PROMPT_FIRST_SUMMARY,
    SYSTEM_PROMPT_REWRITE,
    SYSTEM_PROMPT_REFLECTION,
    SYSTEM_PROMPT_REFLECTION_SUMMARY,
    SYSTEM_PROMPT_REPORT_FORMATTING,
)


# ============================================================
# Schema validation
# ============================================================

ALL_SCHEMAS = [
    ("output_schema_report_structure", output_schema_report_structure),
    ("input_schema_first_search", input_schema_first_search),
    ("output_schema_first_search", output_schema_first_search),
    ("input_schema_first_summary", input_schema_first_summary),
    ("output_schema_first_summary", output_schema_first_summary),
    ("input_schema_reflection", input_schema_reflection),
    ("output_schema_reflection", output_schema_reflection),
    ("input_schema_reflection_summary", input_schema_reflection_summary),
    ("output_schema_reflection_summary", output_schema_reflection_summary),
    ("input_schema_rewrite", input_schema_rewrite),
    ("input_schema_report_formatting", input_schema_report_formatting),
]


class TestSchemas:
    @pytest.mark.parametrize("name,schema", ALL_SCHEMAS)
    def test_is_dict(self, name, schema):
        assert isinstance(schema, (dict, list)), f"{name} should be a dict or list"

    @pytest.mark.parametrize("name,schema", ALL_SCHEMAS)
    def test_has_type(self, name, schema):
        if isinstance(schema, dict):
            assert "type" in schema, f"{name} should have a 'type' key"

    @pytest.mark.parametrize("name,schema", ALL_SCHEMAS)
    def test_json_serializable(self, name, schema):
        """Schemas must be JSON-serializable (used in f-strings for prompts)."""
        serialized = json.dumps(schema, ensure_ascii=False)
        assert len(serialized) > 0


class TestReflectionSchema:
    """Deeper checks on the reflection output schema (our new structured format)."""

    def test_has_is_satisfactory(self):
        props = output_schema_reflection["properties"]
        assert "is_satisfactory" in props
        assert props["is_satisfactory"]["type"] == "boolean"

    def test_has_errors_array(self):
        props = output_schema_reflection["properties"]
        assert "errors" in props
        assert props["errors"]["type"] == "array"

    def test_error_item_has_severity(self):
        error_props = output_schema_reflection["properties"]["errors"]["items"]["properties"]
        assert "severity" in error_props
        assert "critical" in error_props["severity"]["enum"]
        assert "major" in error_props["severity"]["enum"]
        assert "minor" in error_props["severity"]["enum"]

    def test_error_item_has_type_enum(self):
        error_props = output_schema_reflection["properties"]["errors"]["items"]["properties"]
        assert "type" in error_props
        expected_types = [
            "data_missing", "format_violation", "logic_gap",
            "instruction_ignored", "hallucination_risk",
            "citation_missing", "data_underuse"
        ]
        for t in expected_types:
            assert t in error_props["type"]["enum"]

    def test_has_search_queries(self):
        props = output_schema_reflection["properties"]
        assert "search_queries" in props

    def test_has_overall_assessment(self):
        props = output_schema_reflection["properties"]
        assert "overall_assessment" in props

    def test_reflection_input_has_search_results(self):
        props = input_schema_reflection["properties"]
        assert "search_results" in props


# ============================================================
# Prompt string validation
# ============================================================

ALL_PROMPTS = [
    ("SYSTEM_PROMPT_FIRST_SEARCH", SYSTEM_PROMPT_FIRST_SEARCH),
    ("SYSTEM_PROMPT_FIRST_SUMMARY", SYSTEM_PROMPT_FIRST_SUMMARY),
    ("SYSTEM_PROMPT_REWRITE", SYSTEM_PROMPT_REWRITE),
    ("SYSTEM_PROMPT_REFLECTION", SYSTEM_PROMPT_REFLECTION),
    ("SYSTEM_PROMPT_REFLECTION_SUMMARY", SYSTEM_PROMPT_REFLECTION_SUMMARY),
    ("SYSTEM_PROMPT_REPORT_FORMATTING", SYSTEM_PROMPT_REPORT_FORMATTING),
]


class TestPromptStrings:
    @pytest.mark.parametrize("name,prompt", ALL_PROMPTS)
    def test_non_empty(self, name, prompt):
        assert isinstance(prompt, str)
        assert len(prompt.strip()) > 50, f"{name} should be a substantial prompt"

    @pytest.mark.parametrize("name,prompt", ALL_PROMPTS)
    def test_contains_json_schema(self, name, prompt):
        """All prompts should embed at least one JSON schema."""
        assert "JSON" in prompt or "json" in prompt

    def test_reflection_prompt_mentions_cross_audit(self):
        assert "交叉审查" in SYSTEM_PROMPT_REFLECTION

    def test_reflection_prompt_mentions_severity(self):
        assert "critical" in SYSTEM_PROMPT_REFLECTION
        assert "major" in SYSTEM_PROMPT_REFLECTION
        assert "minor" in SYSTEM_PROMPT_REFLECTION

    def test_reflection_prompt_mentions_search_results(self):
        assert "search_results" in SYSTEM_PROMPT_REFLECTION


class TestRewriteSchema:
    """Validate the rewrite input schema structure."""

    def test_has_paragraph_latest_state(self):
        props = input_schema_rewrite["properties"]
        assert "paragraph_latest_state" in props

    def test_has_errors_array(self):
        props = input_schema_rewrite["properties"]
        assert "errors" in props
        assert props["errors"]["type"] == "array"

    def test_error_item_has_severity_enum(self):
        error_props = input_schema_rewrite["properties"]["errors"]["items"]["properties"]
        assert "severity" in error_props
        assert set(error_props["severity"]["enum"]) == {"critical", "major", "minor"}

    def test_error_item_has_type_enum(self):
        error_props = input_schema_rewrite["properties"]["errors"]["items"]["properties"]
        assert "type" in error_props
        expected = [
            "data_missing", "format_violation", "logic_gap",
            "instruction_ignored", "hallucination_risk",
            "citation_missing", "data_underuse"
        ]
        for t in expected:
            assert t in error_props["type"]["enum"]

    def test_has_search_results(self):
        props = input_schema_rewrite["properties"]
        assert "search_results" in props

    def test_has_content(self):
        props = input_schema_rewrite["properties"]
        assert "content" in props


class TestRewritePrompt:
    """Validate SYSTEM_PROMPT_REWRITE content."""

    def test_mentions_modification_principles(self):
        assert "修改原则" in SYSTEM_PROMPT_REWRITE

    def test_mentions_preserve_good_content(self):
        assert "保留优点" in SYSTEM_PROMPT_REWRITE

    def test_mentions_priority_order(self):
        assert "critical" in SYSTEM_PROMPT_REWRITE
        assert "major" in SYSTEM_PROMPT_REWRITE
        assert "minor" in SYSTEM_PROMPT_REWRITE

    def test_mentions_all_error_types(self):
        for err_type in [
            "data_missing", "data_underuse", "hallucination_risk",
            "citation_missing", "instruction_ignored", "format_violation",
            "logic_gap"
        ]:
            assert err_type in SYSTEM_PROMPT_REWRITE, f"{err_type} not in rewrite prompt"

    def test_mentions_fix_suggestion(self):
        assert "fix_suggestion" in SYSTEM_PROMPT_REWRITE

    def test_contains_json_schema(self):
        assert "INPUT JSON SCHEMA" in SYSTEM_PROMPT_REWRITE
        assert "OUTPUT JSON SCHEMA" in SYSTEM_PROMPT_REWRITE

    def test_output_uses_paragraph_latest_state(self):
        assert "paragraph_latest_state" in SYSTEM_PROMPT_REWRITE

    def test_distinct_from_first_summary(self):
        """Rewrite prompt should NOT contain first-draft-only markers."""
        assert "核心写作规范" not in SYSTEM_PROMPT_REWRITE
