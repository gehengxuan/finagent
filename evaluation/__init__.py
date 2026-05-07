"""轻量化 benchmark 与报告自动评分模块。"""

from .cases import DEFAULT_COMPANY_BENCHMARK_CASES, DEFAULT_COMPANY_SECTION_TITLES, get_case_by_id
from .metrics import evaluate_report

__all__ = [
    "DEFAULT_COMPANY_BENCHMARK_CASES",
    "DEFAULT_COMPANY_SECTION_TITLES",
    "get_case_by_id",
    "evaluate_report",
]