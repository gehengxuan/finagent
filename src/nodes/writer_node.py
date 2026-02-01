import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.prompts.prompts import SYSTEM_PROMPT_FIRST_SUMMARY
from src.state import SectionState

def write_section_node(state: SectionState, llm):
    """
    写作节点 (修复版)
    """
    section_def = state["section_def"]
    section_title = section_def["title"]
    instruction = section_def["content"]
    
    search_data = state.get("search_results", [])
    
    # ============================================================    # 【源头去重 2】：对 search_results 进行二次去重（防御性编程）
    # ============================================================
    def deduplicate_search_results(results):
        """对搜索结果进行去重"""
        seen_keys = set()
        deduplicated = []
        
        for item in results:
            # 生成唯一键
            url = item.get('url', '') if isinstance(item, dict) else ''
            title = item.get('title', '') if isinstance(item, dict) else ''
            
            key = url if (url and len(url) > 5 and '本地' not in url) else title
            
            if key not in seen_keys:
                deduplicated.append(item)
                seen_keys.add(key)
        
        return deduplicated
    
    # 在写作前去重
    search_data = deduplicate_search_results(search_data)
    
    # ============================================================    # 修复点 1：标准化搜索结果格式，带上 [ID]
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
    # 修复点 2：针对“财务/表格”类任务的指令增强
    # ============================================================
    # 如果指令里明确要求了“表格”或者标题包含“财务”，强制注入格式要求
    special_formatting_instruction = ""
    if "表格" in instruction or "财务" in section_title:
        special_formatting_instruction = (
            "\n\n【强格式约束】\n"
            "1. 本章节必须包含 Markdown 表格。\n"
            "2. 严禁使用纯文本列表代替表格。\n"
            "3. 如果数据缺失，表格单元格中填写“N/A”或“未披露”。"
        )

    # 构造输入
    input_data = {
        "title": section_title,
        "content": instruction + special_formatting_instruction, # 注入增强指令
        "search_query": state["query"],
        "search_results": [context_str] 
    }
    
    # 处理反思后的重写
    critique = state.get("critique")
    if critique:
        print(f"✍️ [Writer] 正在根据意见重写: {section_title} (迭代 {state['iteration_count']})")
        # 将修改意见也加进去
        input_data["content"] += f"\n\n【修改意见】请针对以下问题进行修改：{critique}"
    else:
        print(f"✍️ [Writer] 正在撰写初稿: {section_title}")
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_FIRST_SUMMARY),
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