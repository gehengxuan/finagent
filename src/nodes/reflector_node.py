import json
from langchain_core.messages import SystemMessage, HumanMessage
from ..state.state import SectionState
from ..prompts.prompts import SYSTEM_PROMPT_REFLECTION
from ..utils.text_processing import deduplicate_search_results


def _format_search_results_for_reflect(search_data: list) -> list:
    """
    把 search_results 格式化为与 writer 一致的带编号文本列表，
    让 reflector 能与草稿中的 [[idx]] 引用一一对应。
    """
    formatted = []
    for i, item in enumerate(search_data, 1):
        if isinstance(item, str):
            content = item
            source = "未知来源"
            url = ""
        else:
            content = item.get('content', '')
            source = item.get('title', '未知来源')
            url = item.get('url', '')

        ref_block = (
            f"Reference [{i}]\n"
            f"Source: {source}\n"
            f"URL: {url}\n"
            f"Content: {content}\n"
        )
        formatted.append(ref_block)
    return formatted


def reflector_node(state: SectionState, llm):
    """
    反思节点 — 拿参考素材与草稿做交叉审查，输出结构化错误清单。
    """
    section_def = state["section_def"]
    section_title = section_def["title"]
    instruction = section_def["content"]

    current_draft = state["current_content"]

    # --- 核心改动：传入 search_results ---
    search_data = state.get("search_results", [])
    search_data = deduplicate_search_results(search_data)
    formatted_refs = _format_search_results_for_reflect(search_data)

    input_data = {
        "title": section_title,
        "content": instruction,
        "paragraph_latest_state": current_draft,
        "search_results": formatted_refs
    }

    print(f"🧐 [Reflector] 正在审阅段落: 【{section_title}】 (参考素材 {len(formatted_refs)} 条)")

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_REFLECTION),
            HumanMessage(content=json.dumps(input_data, ensure_ascii=False))
        ]

        response = llm.invoke(messages, response_format={"type": "json_object"})
        result_json = json.loads(response.content)

        # --- 解析结构化输出 ---
        is_satisfactory = result_json.get("is_satisfactory", False)
        errors = result_json.get("errors", [])
        search_queries = result_json.get("search_queries", [])
        overall_assessment = result_json.get("overall_assessment", "")

        # 统计各严重等级
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        for err in errors:
            sev = err.get("severity", "minor")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if is_satisfactory or not errors:
            print(f"  > ✅ 质量达标: {overall_assessment}")
            return {
                "critique": None,
                "feedback_search_query": None,
                "is_satisfactory": True,
                "reflection_errors": []
            }
        else:
            # 打印每条错误
            print(f"  > ⚠️ 发现 {len(errors)} 个问题 "
                  f"(critical={severity_counts['critical']}, "
                  f"major={severity_counts['major']}, "
                  f"minor={severity_counts['minor']})")
            print(f"  > 总评: {overall_assessment}")
            for i, err in enumerate(errors, 1):
                print(f"    [{i}] [{err.get('severity', '?').upper()}] "
                      f"{err.get('type', '?')}: {err.get('description', '')[:80]}")

            # 取第一条补搜查询（如果有的话）
            primary_search_query = search_queries[0] if search_queries else None

            # 构造给 writer 的结构化 critique
            critique_text = _build_critique_text(errors, overall_assessment)

            return {
                "critique": critique_text,
                "feedback_search_query": primary_search_query,
                "is_satisfactory": False,
                "reflection_errors": errors
            }

    except Exception as e:
        print(f"  > [Error] 反思解析失败: {e}")
        return {
            "critique": f"反思节点异常: {e}",
            "feedback_search_query": None,
            "is_satisfactory": False,
            "reflection_errors": []
        }


def _build_critique_text(errors: list, overall_assessment: str) -> str:
    """
    将结构化错误清单转换为给 writer 的文本格式修改意见。
    按 severity 排序: critical → major → minor。
    """
    severity_order = {"critical": 0, "major": 1, "minor": 2}
    sorted_errors = sorted(errors, key=lambda e: severity_order.get(e.get("severity", "minor"), 9))

    lines = [f"【总体评价】{overall_assessment}", ""]
    lines.append("【结构化错误清单】")

    for i, err in enumerate(sorted_errors, 1):
        severity = err.get("severity", "unknown").upper()
        err_type = err.get("type", "unknown")
        location = err.get("location", "未指定位置")
        description = err.get("description", "")
        fix = err.get("fix_suggestion", "")

        lines.append(f"{i}. [{severity}] {err_type}")
        lines.append(f"   位置: {location}")
        lines.append(f"   问题: {description}")
        if fix:
            lines.append(f"   修复: {fix}")
        lines.append("")

    return "\n".join(lines)


def should_continue(state: SectionState):
    """
    条件路由函数：根据反思结果和错误严重等级决定下一步。

    路由逻辑:
        iteration >= max → end (硬停)
        is_satisfactory   → end
        有补搜查询        → search
        有错误但无需补搜   → rewrite
    """
    is_satisfactory = state.get("is_satisfactory", False)
    iteration = state.get("iteration_count", 0)

    from ..graph.graph_config import EXECUTION_CONFIG
    max_iterations = EXECUTION_CONFIG.get("max_iterations_per_section", 3)

    if iteration >= max_iterations:
        return "end"

    if is_satisfactory:
        return "end"

    # 基于 severity 的快速放行：如果只剩 minor 且已经迭代过一次，放行
    errors = state.get("reflection_errors", [])
    if errors and iteration >= 2:
        has_serious = any(
            e.get("severity") in ("critical", "major") for e in errors
        )
        if not has_serious:
            return "end"

    if state.get("feedback_search_query"):
        return "search"
    else:
        return "rewrite"
