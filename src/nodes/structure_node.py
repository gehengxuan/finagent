# src/nodes/structure_node.py

import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import SectionState
from src.utils import load_config

# 1. 导入公共 Schema
from src.prompts.prompts import output_schema_report_structure

# 2. 导入 个股 Prompt (Set A)
from src.prompts.company_prompt import (
    SYSTEM_PROMPT_REPORT_STRUCTURE,
    LOGICAL_PROMPT_INSTRUCTION,
    FINANCIAL_PROMPT_INSTRUCTION,
    QUESTION_PROMPT_INSTRUCTION
)

# 3. 导入 行业 Prompt (Set B)
from src.prompts.industry_prompt import (
    SYSTEM_PROMPT_REPORT_STRUCTURE_INDUSTRY,
    MARKET_SPACE_PROMPT_INSTRUCTION,
    COMPETITIVE_LANDSCAPE_INSTRUCTION,
    CHAIN_ANALYSIS_INSTRUCTION
)

def generate_structure_node(state: SectionState, llm):
    """
    第一步：生成报告结构 (支持 个股/行业 双模式切换)
    """
    config = load_config()
    query = state["query"]
    
    print(f"--- 生成报告结构 [{config.report_type}模式]: {query} ---")

    json_schema_str = json.dumps(output_schema_report_structure, indent=2, ensure_ascii=False)

    # ==========================
    # 逻辑分流
    # ==========================
    if config.report_type == "industry":
        # === 行业一页纸模式 ===
        formatted_system_prompt = SYSTEM_PROMPT_REPORT_STRUCTURE_INDUSTRY.format(
            query=query,
            chain_instruction=CHAIN_ANALYSIS_INSTRUCTION.replace('\n', ' '),
            market_space_instruction=MARKET_SPACE_PROMPT_INSTRUCTION.replace('\n', ' '),
            competitive_instruction=COMPETITIVE_LANDSCAPE_INSTRUCTION.replace('\n', ' '),
            json_schema=json_schema_str
        )
    else:
        # === 默认：个股深度模式 ===
        formatted_system_prompt = SYSTEM_PROMPT_REPORT_STRUCTURE.format(
            query=query,
            logical_instruction=LOGICAL_PROMPT_INSTRUCTION.replace('\n', ' '),
            financial_instruction=FINANCIAL_PROMPT_INSTRUCTION.replace('\n', ' '),
            question_instruction=QUESTION_PROMPT_INSTRUCTION.replace('\n', ' '),
            json_schema=json_schema_str
        )

    # 下面代码保持不变
    messages = [
        SystemMessage(content=formatted_system_prompt),
        HumanMessage(content=f"请为目标生成报告结构：{query}")
    ]
    
    try:
        response = llm.invoke(messages, response_format={"type": "json_object"})
        content = json.loads(response.content)
        
        if isinstance(content, dict) and "items" in content:
            sections = content["items"]
        elif isinstance(content, list):
            sections = content
        else:
            sections = content.get("sections", [])
            
        return {"sections": sections}
        
    except Exception as e:
        print(f"❌ 结构解析失败: {e}")
        return {"sections": []}