"""
src/state.py
定义 Agent 运行过程中的共享状态结构
"""

from typing import TypedDict, List, Optional, Dict, Any,Annotated
from dataclasses import dataclass, field

@dataclass
class SectionMetadata:
    """
    段落元数据类
    用于定义每个段落的静态属性
    """
    key: str                # 唯一标识符，例如 'financial_analysis'
    title: str              # 显示标题，例如 '财务分析'
    description: str        # 任务描述
    prompt_template: str    # 对应的 Prompt 模板
    required_tools: List[str] = field(default_factory=list)
    priority: int = 1

def reduce_query(left: Optional[str], right: Optional[str]) -> str:
    return left or right

def reduce_list(left: Optional[list], right: Optional[list]) -> list:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

# [新增] 定义一个结构，用来在 Worker 和 Compiler 之间传递完整数据
class SectionOutput(TypedDict):
    title: str
    content: str  # Markdown 文本
    local_refs: List[Dict[str, Any]] # 该段落用到的原始搜索结果

# [新增] 专门的 reducer，处理列表合并
def reduce_list(left: Optional[list], right: Optional[list]) -> list:
    if left is None: left = []
    if right is None: right = []
    return left + right

def reduce_overwrite(left, right):
    return left if left is not None else right
class SectionState(TypedDict):
    """
    SectionState
    LangGraph 图中流转的核心状态对象
    """
    
    # --- 初始输入 (Input) ---
    query: str                      # 研报的主题 (e.g. "宁德时代投资价值分析")
    section_def: SectionMetadata    # 当前正在处理的段落定义对象

    # --- 信息收集 (Context) ---
    # 存储搜索到的原始数据，通常是列表，包含 content, url 等
    search_results: List[Dict[str, Any]] 
    
    # --- 内容生成 (Generation) ---
    current_content: str            # 当前生成的段落 Markdown 内容
    
    # --- 质量控制 (Quality Control) ---
    critique: Optional[str]         # Reflector 给出的具体修改意见 (None 代表无意见/通过)
    iteration_count: int            # 当前是第几次迭代 (用于防止死循环)
    is_satisfactory: bool           # 最终质量是否达标的标志位

    # 这里的类型变了，变成了 SectionOutput 的列表
    completed_sections: Optional[List[SectionOutput]] 
    feedback_search_query: Optional[str]
    # 【核心修复】：必须在这里定义这个字段，Worker 才能把它传给主 Agent！
    aggregate_references: Optional[List[Dict[str, Any]]]

class AgentState(TypedDict):
    query: Annotated[str, reduce_query] 
    sections: List[SectionMetadata]
    # [核心修改] 这里存储的是结构化对象，不仅仅是字符串
    completed_sections: Annotated[List[SectionOutput], reduce_list]
    
    # 【新增】用于汇总所有子节点的搜索结果，最后统一生成参考文献
    aggregate_references: Annotated[List[Dict[str, Any]], reduce_list]
    
    final_report: str