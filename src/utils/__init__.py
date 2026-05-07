"""
工具函数模块
提供文本处理、JSON解析、搜索结果去重等辅助功能
"""

from .text_processing import (
    clean_json_tags,
    clean_markdown_tags, 
    remove_reasoning_from_output,
    extract_clean_response,
    format_search_results_for_prompt,
    get_doc_key,
    deduplicate_search_results,
)

from .config import Config, load_config, set_config, clear_config_cache

__all__ = [
    "clean_json_tags",
    "clean_markdown_tags",
    "remove_reasoning_from_output", 
    "extract_clean_response",
    "format_search_results_for_prompt",
    "get_doc_key",
    "deduplicate_search_results",
    "Config",
    "load_config",
    "set_config",
    "clear_config_cache"
]
