"""
src/state/state.py
定义 Agent 运行过程中的共享状态结构
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from dataclasses import dataclass, field


# =================================================================
# Reducer 函数 (LangGraph 状态合并用)
# =================================================================

def reduce_query(left: Optional[str], right: Optional[str]) -> str:
    """Query reducer: 优先使用新值，否则保留旧值"""
    if right is not None:
        return right
    if left is not None:
        return left
    return ""


def reduce_list(left: Optional[list], right: Optional[list]) -> list:
    """List reducer: 合并两个列表"""
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right


# =================================================================
# 数据结构定义
# =================================================================

class SectionOutput(TypedDict):
    """Worker 与 Compiler 之间传递的段落输出"""
    title: str
    content: str                     # Markdown 文本
    local_refs: List[Dict[str, Any]] # 该段落用到的原始搜索结果


class SectionState(TypedDict):
    """
    子图 (SectionWorker) 的状态对象
    """
    # --- 初始输入 (Input) ---
    query: str                                  # 研报主题
    section_def: Dict[str, Any]                 # 当前段落定义 (dict 格式: {title, content})

    # --- 信息收集 (Context) ---
    search_results: List[Dict[str, Any]]        # 搜索到的原始数据

    # --- 内容生成 (Generation) ---
    current_content: str                        # 当前生成的段落 Markdown 内容

    # --- 质量控制 (Quality Control) ---
    critique: Optional[str]                     # Reflector 给出的修改意见 (结构化文本)
    iteration_count: int                        # 当前迭代次数 (防止死循环)
    is_satisfactory: bool                       # 质量是否达标
    reflection_errors: Optional[List[Dict[str, Any]]]  # 结构化错误清单

    # --- 输出 ---
    completed_sections: Optional[List[SectionOutput]]
    feedback_search_query: Optional[str]


class AgentState(TypedDict):
    """
    主图 (MainGraph) 的状态对象
    """
    query: Annotated[str, reduce_query]
    sections: List[Dict[str, Any]]              # 报告结构 (dict 列表)
    completed_sections: Annotated[List[SectionOutput], reduce_list]
    final_report: str