"""低成本自动评测指标。

第一版只做不依赖人工标注和 LLM judge 的静态评分：
- 结构完整性
- 引用与参考资料一致性
- 数值型 claim 的带引比例
"""

from __future__ import annotations

import re
from typing import Iterable

from .cases import DEFAULT_COMPANY_SECTION_TITLES


REFERENCE_HEADING = "### 参考资料 / References"
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
REFERENCE_ITEM_PATTERN = re.compile(r"^\s*-\s*\[(\d+)\]\s+(.+)$", re.MULTILINE)
DOUBLE_CITATION_PATTERN = re.compile(r"\[\[(\d+)\]\]")
SINGLE_CITATION_PATTERN = re.compile(r"(?<!\[)\[(\d+)\](?!\(|\])")
ADJACENT_DUPLICATE_PATTERN = re.compile(r"(?<!\[)\[(\d+)\](?:[\s、，,]+)\[\1\]")


def split_report(report_text: str) -> tuple[str, str]:
    if REFERENCE_HEADING not in report_text:
        return report_text, ""

    body, references = report_text.split(REFERENCE_HEADING, 1)
    return body, references


def extract_sections(report_text: str) -> list[str]:
    body, _ = split_report(report_text)
    return [match.group(1).strip() for match in SECTION_PATTERN.finditer(body)]


def extract_section_bodies(report_text: str) -> dict[str, str]:
    body, _ = split_report(report_text)
    matches = list(SECTION_PATTERN.finditer(body))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip()

    return sections


def extract_reference_ids(report_text: str) -> list[int]:
    _, references = split_report(report_text)
    return [int(match.group(1)) for match in REFERENCE_ITEM_PATTERN.finditer(references)]


def extract_citation_ids(report_text: str) -> list[int]:
    body, _ = split_report(report_text)
    double_ids = [int(value) for value in DOUBLE_CITATION_PATTERN.findall(body)]
    body_without_double = DOUBLE_CITATION_PATTERN.sub("", body)
    single_ids = [int(value) for value in SINGLE_CITATION_PATTERN.findall(body_without_double)]
    return double_ids + single_ids


def has_markdown_table(section_text: str) -> bool:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    pipe_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]

    if len(pipe_lines) < 2:
        return False

    return any(re.fullmatch(r"\|?[\s:-]+(?:\|[\s:-]+)+\|?", line) for line in pipe_lines)


def find_numeric_claim_lines(report_text: str) -> list[str]:
    body, _ = split_report(report_text)
    lines = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("|"):
            continue
        if re.fullmatch(r"[-:|\s]+", line):
            continue
        if re.search(r"\d", line):
            lines.append(line)

    return lines


def _line_has_citation(line: str) -> bool:
    return bool(DOUBLE_CITATION_PATTERN.search(line) or SINGLE_CITATION_PATTERN.search(line))


def _average(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(items) / len(items), 4)


def evaluate_report(report_text: str, expected_sections: tuple[str, ...] = DEFAULT_COMPANY_SECTION_TITLES) -> dict:
    sections = extract_sections(report_text)
    section_bodies = extract_section_bodies(report_text)
    reference_ids = extract_reference_ids(report_text)
    citation_ids = extract_citation_ids(report_text)

    expected_present = [title for title in expected_sections if title in sections]
    missing_sections = [title for title in expected_sections if title not in sections]
    unexpected_sections = [title for title in sections if title not in expected_sections]
    ordered_sections = [title for title in sections if title in expected_sections]
    ordered_correctly = ordered_sections == expected_present

    financial_body = section_bodies.get("4. 财务质量分析", "")
    financial_table_present = has_markdown_table(financial_body)

    section_coverage = round(len(expected_present) / len(expected_sections), 4) if expected_sections else 1.0
    order_score = 1.0 if ordered_correctly else 0.0
    financial_table_score = 1.0 if financial_table_present else 0.0
    structure_score = _average([section_coverage, order_score, financial_table_score])

    reference_id_set = set(reference_ids)
    unique_citations = sorted(set(citation_ids))
    orphan_citations = sorted(citation for citation in unique_citations if citation not in reference_id_set)
    valid_citation_count = sum(1 for citation in citation_ids if citation in reference_id_set)
    citation_valid_rate = round(valid_citation_count / len(citation_ids), 4) if citation_ids else 0.0
    reference_presence_score = 1.0 if reference_ids else 0.0
    duplicate_adjacent_count = len(ADJACENT_DUPLICATE_PATTERN.findall(split_report(report_text)[0]))
    duplicate_penalty_score = round(max(0.0, 1 - (duplicate_adjacent_count / max(len(citation_ids), 1))), 4)
    citation_score = _average([citation_valid_rate, reference_presence_score, duplicate_penalty_score])

    numeric_claim_lines = find_numeric_claim_lines(report_text)
    cited_numeric_claim_lines = [line for line in numeric_claim_lines if _line_has_citation(line)]
    uncited_numeric_claim_lines = [line for line in numeric_claim_lines if not _line_has_citation(line)]
    numeric_claim_citation_rate = round(
        len(cited_numeric_claim_lines) / len(numeric_claim_lines), 4
    ) if numeric_claim_lines else 1.0

    overall_score = round(
        structure_score * 0.5 + citation_score * 0.3 + numeric_claim_citation_rate * 0.2,
        4,
    )

    return {
        "structure": {
            "expected_sections": list(expected_sections),
            "found_sections": sections,
            "missing_sections": missing_sections,
            "unexpected_sections": unexpected_sections,
            "section_coverage": section_coverage,
            "ordered_correctly": ordered_correctly,
            "financial_table_present": financial_table_present,
            "structure_score": structure_score,
        },
        "citations": {
            "reference_count": len(reference_ids),
            "reference_ids": reference_ids,
            "citation_count": len(citation_ids),
            "unique_citation_ids": unique_citations,
            "orphan_citations": orphan_citations,
            "citation_valid_rate": citation_valid_rate,
            "duplicate_adjacent_count": duplicate_adjacent_count,
            "citation_score": citation_score,
        },
        "claims": {
            "numeric_claim_count": len(numeric_claim_lines),
            "cited_numeric_claim_count": len(cited_numeric_claim_lines),
            "uncited_numeric_claim_count": len(uncited_numeric_claim_lines),
            "numeric_claim_citation_rate": numeric_claim_citation_rate,
            "uncited_numeric_claim_examples": uncited_numeric_claim_lines[:5],
        },
        "scores": {
            "overall_score": overall_score,
            "structure_score": structure_score,
            "citation_score": citation_score,
            "claim_score": numeric_claim_citation_rate,
        },
    }