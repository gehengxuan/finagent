"""evaluation.metrics 的轻量单元测试。"""

from evaluation.cases import DEFAULT_COMPANY_BENCHMARK_CASES, get_case_by_id
from evaluation.metrics import (
    evaluate_report,
    extract_citation_ids,
    extract_reference_ids,
    extract_sections,
    has_markdown_table,
)


SAMPLE_REPORT = """# 测试报告

## 1. 核心结论与预期差

2025年公司营收达到100亿元 [1]，净利润同比增长20% [2]。

## 2. 公司近况深度跟踪

公司近期完成新产品发布，市场反馈积极 [2]。

## 3. 核心投资逻辑

短期看，产品周期与费用率改善共同推动盈利修复 [1]。

## 4. 财务质量分析

| 指标 | 2024 | 2025 |
| --- | --- | --- |
| 营业收入(亿元) | 80 | 100 |
| 归母净利润(亿元) | 10 | 12 |

## 5. 调研问题大纲

1. 管理层如何看待明年毛利率趋势？

## 6. 风险提示

需求不及预期可能影响收入增长节奏 [2]。

### 参考资料 / References
- [1] 公司年报
- [2] 券商行业跟踪
"""


ORPHAN_CITATION_REPORT = SAMPLE_REPORT.replace("市场反馈积极 [2]", "市场反馈积极 [3]")


class TestEvaluationParsing:
    def test_extract_sections(self):
        sections = extract_sections(SAMPLE_REPORT)
        assert sections[0] == "1. 核心结论与预期差"
        assert sections[-1] == "6. 风险提示"
        assert len(sections) == 6

    def test_extract_reference_ids(self):
        assert extract_reference_ids(SAMPLE_REPORT) == [1, 2]

    def test_extract_citation_ids(self):
        citation_ids = extract_citation_ids(SAMPLE_REPORT)
        assert citation_ids.count(1) >= 1
        assert citation_ids.count(2) >= 1

    def test_has_markdown_table(self):
        assert has_markdown_table("| A | B |\n| --- | --- |\n| 1 | 2 |") is True
        assert has_markdown_table("普通段落，没有表格") is False


class TestEvaluateReport:
    def test_complete_report_scores_well(self):
        result = evaluate_report(SAMPLE_REPORT)
        assert result["structure"]["missing_sections"] == []
        assert result["structure"]["financial_table_present"] is True
        assert result["citations"]["orphan_citations"] == []
        assert result["scores"]["overall_score"] > 0.8

    def test_orphan_citation_is_detected(self):
        result = evaluate_report(ORPHAN_CITATION_REPORT)
        assert result["citations"]["orphan_citations"] == [3]
        assert result["scores"]["citation_score"] < 1.0

    def test_uncited_numeric_claim_reduces_claim_score(self):
        report = SAMPLE_REPORT.replace("净利润同比增长20% [2]", "净利润同比增长20%")
        result = evaluate_report(report)
        assert result["claims"]["uncited_numeric_claim_count"] >= 1
        assert result["scores"]["claim_score"] < 1.0


class TestBenchmarkCases:
    def test_case_catalog_contains_microsoft(self):
        case = get_case_by_id("microsoft")
        assert case.ticker == "MSFT"
        assert case.report_type == "company"

    def test_default_cases_have_local_files(self):
        assert all(case.local_files for case in DEFAULT_COMPANY_BENCHMARK_CASES)