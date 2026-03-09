import json
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts.prompts import SYSTEM_PROMPT_FIRST_SUMMARY, SYSTEM_PROMPT_REWRITE
from ..state.state import SectionState
from ..utils.text_processing import deduplicate_search_results

def write_section_node(state: SectionState, llm):
    """
    写作节点
    - 首稿模式：使用 SYSTEM_PROMPT_FIRST_SUMMARY，从搜索结果生成初稿
    - 重写模式：使用 SYSTEM_PROMPT_REWRITE，基于质控反馈在现有草稿上修改
    """
    section_def = state["section_def"]
    section_title = section_def["title"]
    instruction = section_def["content"]
    
    search_data = state.get("search_results", [])
    
    # ============================================================
    # 【源头去重】：对 search_results 进行二次去重（防御性编程）
    # ============================================================
    search_data = deduplicate_search_results(search_data)
    
    # ============================================================
    # 标准化搜索结果格式，带上 [ID]
    # ============================================================
    formatted_context_list = []
    # 如果 search_data 是字符串列表（兼容旧数据），先转一下
    if search_data and isinstance(search_data[0], str):
         # 简单处理，假设是旧格式
         pass 
         
    for i, item in enumerate(search_data, 1):
        # 容错处理
        if isinstance(item, str):
            content = item
            source = "未知来源"
            url = ""
        else:
            content = item.get('content', '')
            source = item.get('title', '未知来源')
            url = item.get('url', '')
            
        # 构造带编号的引用块
        ref_block = (
            f"Reference [{i}]\n"
            f"Source: {source}\n"
            f"URL: {url}\n"
            f"Content: {content}\n"
        )
        formatted_context_list.append(ref_block)
        
    # 拼成一个大的上下文字符串
    context_str = "\n".join(formatted_context_list)

    # ============================================================
    # 针对"财务/表格"类任务的指令增强
    # ============================================================
    # 如果指令里明确要求了"表格"或者标题包含"财务"，强制注入格式要求
    special_formatting_instruction = ""
    if "表格" in instruction or "财务" in section_title:
        special_formatting_instruction = (
            "\n\n【强格式约束】\n"
            "1. 本章节必须包含 Markdown 表格。\n"
            "2. 严禁使用纯文本列表代替表格。\n"
            '3. 如果数据缺失，表格单元格中填写"N/A"或"未披露"。'
        )

    # ============================================================
    # 分流：首稿 vs 重写
    # ============================================================
    critique = state.get("critique")
    if critique:
        # === 重写模式 ===
        iteration = state.get("iteration_count", 0)
        errors = state.get("reflection_errors", [])
        
        # 按严重程度排序 (critical → major → minor)
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        sorted_errors = sorted(
            errors,
            key=lambda e: severity_order.get(e.get("severity", "minor"), 9)
        )
        
        critical_count = sum(1 for e in errors if e.get("severity") == "critical")
        major_count = sum(1 for e in errors if e.get("severity") == "major")
        print(f"✍️ [Writer] 正在根据反思意见重写: {section_title} "
              f"(迭代 {iteration}, {critical_count} critical, {major_count} major)")
        
        input_data = {
            "title": section_title,
            "content": instruction + special_formatting_instruction,
            "paragraph_latest_state": state.get("current_content", ""),
            "search_results": [context_str],
            "errors": sorted_errors,
        }
        system_prompt = SYSTEM_PROMPT_REWRITE
    else:
        # === 首稿模式 ===
        print(f"✍️ [Writer] 正在撰写初稿: {section_title}")
        
        input_data = {
            "title": section_title,
            "content": instruction + special_formatting_instruction,
            "search_query": state["query"],
            "search_results": [context_str],
        }
        system_prompt = SYSTEM_PROMPT_FIRST_SUMMARY
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(input_data, ensure_ascii=False))
    ]
    
    try:
        response = llm.invoke(messages, response_format={"type": "json_object"})
        content = json.loads(response.content)
        draft = content.get("paragraph_latest_state", "")
        
        return {
            "current_content": draft,
            "iteration_count": state["iteration_count"] + 1
        }
        
    except Exception as e:
        print(f"  > [Error] 写作失败: {e}")
        return {"current_content": "生成失败，请检查日志。"}
