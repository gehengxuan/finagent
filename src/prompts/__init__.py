"""
Prompt模块
定义Deep Search Agent各个阶段使用的系统提示词
"""

from .prompts import (
    SYSTEM_PROMPT_FIRST_SEARCH,
    SYSTEM_PROMPT_FIRST_SUMMARY,
    SYSTEM_PROMPT_REFLECTION,
    SYSTEM_PROMPT_REFLECTION_SUMMARY,
    SYSTEM_PROMPT_REPORT_FORMATTING,
    output_schema_report_structure,
    output_schema_first_search,
    output_schema_first_summary,
    output_schema_reflection,
    output_schema_reflection_summary,
    input_schema_report_formatting,
    
)
from .industry_prompt import (
    SYSTEM_PROMPT_REPORT_STRUCTURE_INDUSTRY,
    MARKET_SPACE_PROMPT_INSTRUCTION,
    COMPETITIVE_LANDSCAPE_INSTRUCTION,
    CHAIN_ANALYSIS_INSTRUCTION  
)   
from .company_prompt import (
    LOGICAL_PROMPT_INSTRUCTION,
    QUESTION_PROMPT_INSTRUCTION,
    FINANCIAL_PROMPT_INSTRUCTION,
    SYSTEM_PROMPT_REPORT_STRUCTURE
)

__all__ = [
    "SYSTEM_PROMPT_REPORT_STRUCTURE",
    "SYSTEM_PROMPT_FIRST_SEARCH", 
    "SYSTEM_PROMPT_FIRST_SUMMARY",
    "SYSTEM_PROMPT_REFLECTION",
    "SYSTEM_PROMPT_REFLECTION_SUMMARY",
    "SYSTEM_PROMPT_REPORT_FORMATTING",
    "output_schema_report_structure",
    "output_schema_first_search",
    "output_schema_first_summary", 
    "output_schema_reflection",
    "output_schema_reflection_summary",
    "input_schema_report_formatting",
    "SYSTEM_PROMPT_REPORT_STRUCTURE_INDUSTRY",
    "MARKET_SPACE_PROMPT_INSTRUCTION",
    "COMPETITIVE_LANDSCAPE_INSTRUCTION",
    "CHAIN_ANALYSIS_INSTRUCTION",
    "LOGICAL_PROMPT_INSTRUCTION",
    "QUESTION_PROMPT_INSTRUCTION",
    "FINANCIAL_PROMPT_INSTRUCTION", 
]