"""默认 benchmark case 定义。"""

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BENCHMARK_DATA_DIR = ROOT_DIR / "benchmark_10k_edgar"

DEFAULT_COMPANY_SECTION_TITLES = (
    "1. 核心结论与预期差",
    "2. 公司近况深度跟踪",
    "3. 核心投资逻辑",
    "4. 财务质量分析",
    "5. 调研问题大纲",
    "6. 风险提示",
)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    company_name: str
    ticker: str
    query: str
    local_files: tuple[str, ...]
    expected_sections: tuple[str, ...] = DEFAULT_COMPANY_SECTION_TITLES
    report_type: str = "company"

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "company_name": self.company_name,
            "ticker": self.ticker,
            "query": self.query,
            "local_files": list(self.local_files),
            "expected_sections": list(self.expected_sections),
            "report_type": self.report_type,
        }


def _benchmark_file(filename: str) -> str:
    return str((BENCHMARK_DATA_DIR / filename).resolve())


DEFAULT_COMPANY_BENCHMARK_CASES = (
    BenchmarkCase(
        case_id="apple",
        company_name="Apple",
        ticker="AAPL",
        query="分析苹果公司在 AI 终端生态中的竞争优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Apple_10K_2025-10-31.txt"),),
    ),
    BenchmarkCase(
        case_id="microsoft",
        company_name="Microsoft",
        ticker="MSFT",
        query="分析微软在企业软件与 AI 基础设施浪潮中的竞争优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Microsoft_10K_2025-07-30.txt"),),
    ),
    BenchmarkCase(
        case_id="amazon",
        company_name="Amazon",
        ticker="AMZN",
        query="分析亚马逊在电商与云计算双轮驱动下的竞争优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Amazon_10K_2026-02-06.txt"),),
    ),
    BenchmarkCase(
        case_id="alphabet",
        company_name="Alphabet",
        ticker="GOOGL",
        query="分析 Alphabet 在搜索广告与 AI 平台竞争中的优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Google_10K_2026-02-05.txt"),),
    ),
    BenchmarkCase(
        case_id="meta",
        company_name="Meta",
        ticker="META",
        query="分析 Meta 在广告平台、AI 投入与 Reality Labs 布局中的优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Meta_10K_2026-01-29.txt"),),
    ),
    BenchmarkCase(
        case_id="nvidia",
        company_name="NVIDIA",
        ticker="NVDA",
        query="分析英伟达在 AI 芯片与数据中心平台中的竞争优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Nvidia_10K_2026-02-25.txt"),),
    ),
    BenchmarkCase(
        case_id="tesla",
        company_name="Tesla",
        ticker="TSLA",
        query="分析特斯拉在智能电动车、自动驾驶与储能业务中的竞争优势、财务质量与主要风险。",
        local_files=(_benchmark_file("Tesla_10K_2026-01-29.txt"),),
    ),
    BenchmarkCase(
        case_id="jpmorgan",
        company_name="JPMorgan Chase",
        ticker="JPM",
        query="分析摩根大通在大型银行竞争格局中的优势、财务质量与主要风险。",
        local_files=(_benchmark_file("JPMorgan_10K_2026-02-13.txt"),),
    ),
)


def get_default_cases() -> list[BenchmarkCase]:
    return list(DEFAULT_COMPANY_BENCHMARK_CASES)


def get_case_by_id(case_id: str) -> BenchmarkCase:
    normalized = case_id.strip().lower()
    for case in DEFAULT_COMPANY_BENCHMARK_CASES:
        if case.case_id == normalized:
            return case
    raise KeyError(f"未找到 benchmark case: {case_id}")