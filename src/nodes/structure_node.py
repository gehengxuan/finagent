# src/nodes/structure_node.py

import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import SectionState
from src.prompts.prompts import (
    SYSTEM_PROMPT_REPORT_STRUCTURE,
    LOGICAL_PROMPT_INSTRUCTION,
    FINANCIAL_PROMPT_INSTRUCTION,
    QUESTION_PROMPT_INSTRUCTION,
    output_schema_report_structure  # <--- 记得引入这个 Schema 对象
)

def generate_structure_node(state: SectionState, llm):
    """
    第一步：生成报告结构
    """
    query = state["query"]
    print(f"--- 生成报告结构: {query} ---")

    # 1. 动态生成 JSON Schema 字符串
    json_schema_str = json.dumps(output_schema_report_structure, indent=2, ensure_ascii=False)

    # 2. 填充 Prompt 中的所有变量
    formatted_system_prompt = SYSTEM_PROMPT_REPORT_STRUCTURE.format(
        query=query,
        logical_instruction=LOGICAL_PROMPT_INSTRUCTION.replace('\n', ' '),
        financial_instruction=FINANCIAL_PROMPT_INSTRUCTION.replace('\n', ' '),
        question_instruction=QUESTION_PROMPT_INSTRUCTION.replace('\n', ' '),
        json_schema=json_schema_str  # <--- 在这里注入 JSON 字符串
    )

    # 3. 调用 LLM
    messages = [
        SystemMessage(content=formatted_system_prompt),
        HumanMessage(content=f"请为目标生成报告结构：{query}")
    ]
    
    try:
        # 强制输出 JSON
        response = llm.invoke(messages, response_format={"type": "json_object"})
        
        # 4. 解析结果
        content = json.loads(response.content)
        
        # 兼容性处理：提取 list
        if isinstance(content, dict) and "items" in content:
            sections = content["items"]
        elif isinstance(content, list):
            sections = content
        else:
            sections = content.get("sections", [])
            
        return {"sections": sections}
        
    except Exception as e:
        print(f"❌ 结构解析失败: {e}")
        # 返回空列表防止后续 Crash
        return {"sections": []}