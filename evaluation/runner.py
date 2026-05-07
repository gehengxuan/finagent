"""批量运行 company benchmark case，并输出自动评分结果。"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, replace
from pathlib import Path

from .cases import BenchmarkCase, get_case_by_id, get_default_cases
from .metrics import evaluate_report


def _import_agent_deps():
    """惰性导入 agent 和 config，避免 --evaluate-report 等纯评测路径
    因 langgraph 等重依赖缺失而报错。"""
    from src import StructuredReportAgent  # noqa: F811
    from src.utils import Config, load_config  # noqa: F811
    return StructuredReportAgent, Config, load_config


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_case_config(base_config, case: BenchmarkCase, case_output_dir: Path):
    return replace(
        base_config,
        report_type=case.report_type,
        local_files=list(case.local_files),
        output_dir=str(case_output_dir),
        save_intermediate_states=False,
    )


def _print_case_summary(result: dict) -> None:
    scores = result["evaluation"]["scores"]
    structure = result["evaluation"]["structure"]
    citations = result["evaluation"]["citations"]
    print(
        f"[{result['case']['case_id']}] overall={scores['overall_score']:.4f} "
        f"structure={scores['structure_score']:.4f} "
        f"citation={scores['citation_score']:.4f} "
        f"claims={scores['claim_score']:.4f}"
    )
    if structure["missing_sections"]:
        print(f"  缺失章节: {', '.join(structure['missing_sections'])}")
    if citations["orphan_citations"]:
        print(f"  孤儿引用: {citations['orphan_citations']}")


def run_case(case: BenchmarkCase, base_config, output_root: Path) -> dict:
    StructuredReportAgent, _, _ = _import_agent_deps()

    case_output_dir = output_root / case.case_id
    case_output_dir.mkdir(parents=True, exist_ok=True)

    config = _build_case_config(base_config, case, case_output_dir)
    _write_json(case_output_dir / "config_snapshot.json", asdict(config))

    start_time = time.perf_counter()
    agent = StructuredReportAgent(config=config)
    report_text = agent.generate_report(case.query)
    duration_seconds = round(time.perf_counter() - start_time, 3)

    report_path = case_output_dir / "report.md"
    report_path.write_text(report_text, encoding="utf-8")

    evaluation = evaluate_report(report_text, expected_sections=case.expected_sections)
    result = {
        "case": case.to_dict(),
        "execution": {
            "duration_seconds": duration_seconds,
            "report_path": str(report_path),
            "output_dir": str(case_output_dir),
        },
        "evaluation": evaluation,
    }
    _write_json(case_output_dir / "evaluation.json", result)
    return result


def evaluate_existing_report(report_path: Path, output_root: Path) -> dict:
    report_text = report_path.read_text(encoding="utf-8")
    evaluation = evaluate_report(report_text)
    result = {
        "report_path": str(report_path.resolve()),
        "evaluation": evaluation,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / f"{report_path.stem}_evaluation.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 DeepSearchAgent 的轻量 benchmark")
    parser.add_argument("--case", dest="case_ids", action="append", help="只运行指定 case_id，可重复传入")
    parser.add_argument("--all-cases", action="store_true", help="运行所有默认 company case")
    parser.add_argument("--evaluate-report", help="只对已有 Markdown 报告做静态评分")
    parser.add_argument("--config-file", default="config.py", help="生成报告时使用的配置文件")
    parser.add_argument("--output-dir", default="evaluation_outputs", help="评测结果输出目录")
    parser.add_argument("--list-cases", action="store_true", help="列出所有默认 case")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_cases:
        for case in get_default_cases():
            print(f"{case.case_id}: {case.company_name} ({case.ticker})")
        return

    output_root = Path(args.output_dir).resolve()

    if args.evaluate_report:
        result = evaluate_existing_report(Path(args.evaluate_report), output_root)
        scores = result["evaluation"]["scores"]
        print(
            f"existing-report overall={scores['overall_score']:.4f} "
            f"structure={scores['structure_score']:.4f} "
            f"citation={scores['citation_score']:.4f} "
            f"claims={scores['claim_score']:.4f}"
        )
        return

    if not args.all_cases and not args.case_ids:
        raise SystemExit("请通过 --case、--all-cases 或 --evaluate-report 指定运行目标")

    _, _, load_config = _import_agent_deps()
    base_config = load_config(config_file=args.config_file, force_reload=True)
    cases = get_default_cases() if args.all_cases else [get_case_by_id(case_id) for case_id in args.case_ids]

    output_root.mkdir(parents=True, exist_ok=True)
    summary = []
    for case in cases:
        result = run_case(case, base_config, output_root)
        summary.append(result)
        _print_case_summary(result)

    _write_json(output_root / "summary.json", {"results": summary})


if __name__ == "__main__":
    main()