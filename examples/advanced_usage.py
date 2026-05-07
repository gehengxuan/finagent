"""高级使用示例。

演示如何通过显式 Config 注入的方式运行多次研报生成，
而不依赖修改根目录下的 config.py。
"""

import os
import sys
import hashlib
import re
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import Config, StructuredReportAgent
from src.utils.config import print_config


def build_custom_config(output_dir: str) -> Config:
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
    else:
        provider = "qwen"

    return Config(
        default_llm_provider=provider,
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        qwen_model="qwen-plus",
        openai_model="gpt-4o-mini",
        max_search_results=5,
        max_reflections=2,
        max_content_length=15000,
        output_dir=output_dir,
        save_intermediate_states=False,
        enable_online_search=False,
        local_files=[],
        report_type="company",
    )


def build_stable_report_name(index: int, query: str) -> str:
    # 用 query 的稳定哈希构造可复现文件名，避免 Python 进程级 hash 随机化。
    query_hash = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", query.lower()).strip("-")
    slug = slug[:30] if slug else "report"
    return f"report_{index:02d}_{slug}_{query_hash}.md"


def save_report(output_dir: Path, index: int, query: str, report: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = build_stable_report_name(index=index, query=query)
    report_path = output_dir / filename
    report_path.write_text(report, encoding="utf-8")
    return report_path


def advanced_example():
    print("=" * 60)
    print("StructuredReportAgent - 高级使用示例")
    print("=" * 60)

    config = build_custom_config(output_dir="custom_reports")
    if not config.validate():
        print("配置验证失败，请先设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")
        return

    print_config(config)
    agent = StructuredReportAgent(config=config)

    queries = [
        "分析苹果公司在 AI 终端生态中的竞争优势、财务质量与主要风险。",
        "分析英伟达在 AI 芯片与数据中心平台中的竞争优势、财务质量与主要风险。",
    ]

    output_dir = Path(config.output_dir)
    for index, query in enumerate(queries, start=1):
        print(f"\n{'=' * 60}")
        print(f"执行任务 {index}/{len(queries)}: {query}")
        print(f"{'=' * 60}")

        start_time = time.time()
        try:
            report = agent.generate_report(query)
            report_path = save_report(output_dir, index, query, report)
            elapsed = time.time() - start_time

            print(f"✅ 任务完成，用时 {elapsed:.1f}s")
            print(f"📄 报告长度: {len(report)} 字符")
            print(f"📂 保存路径: {report_path}")
        except Exception as exc:
            print(f"❌ 任务失败: {exc}")


if __name__ == "__main__":
    advanced_example()
