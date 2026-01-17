# """
# 报告结构生成节点
# 负责根据查询生成报告的整体结构
# """

# import json
# from typing import Dict, Any, List
# from json.decoder import JSONDecodeError

# from .base_node import StateMutationNode
# from ..state.state import State
# from ..prompts import SYSTEM_PROMPT_REPORT_STRUCTURE
# from ..utils.text_processing import (
#     remove_reasoning_from_output,
#     clean_json_tags,
#     extract_clean_response
# )


# class ReportStructureNode(StateMutationNode):
#     """生成报告结构的节点"""
    
#     def __init__(self, llm_client, query: str):
#         """
#         初始化报告结构节点
        
#         Args:
#             llm_client: LLM客户端
#             query: 用户查询
#         """
#         super().__init__(llm_client, "ReportStructureNode")
#         self.query = query
    
#     def validate_input(self, input_data: Any) -> bool:
#         """验证输入数据"""
#         return isinstance(self.query, str) and len(self.query.strip()) > 0
    
#     def run(self, input_data: Any = None, **kwargs) -> List[Dict[str, str]]:
#         """
#         调用LLM生成报告结构
        
#         Args:
#             input_data: 输入数据（这里不使用，使用初始化时的query）
#             **kwargs: 额外参数
            
#         Returns:
#             报告结构列表
#         """
#         try:
#             self.log_info(f"正在为查询生成报告结构: {self.query}")
            
#             # 调用LLM
#             response = self.llm_client.invoke(SYSTEM_PROMPT_REPORT_STRUCTURE, self.query)
            
#             # 处理响应
#             processed_response = self.process_output(response)
            
#             self.log_info(f"成功生成 {len(processed_response)} 个段落结构")
#             return processed_response
            
#         except Exception as e:
#             self.log_error(f"生成报告结构失败: {str(e)}")
#             raise e
    
#     def process_output(self, output: str) -> List[Dict[str, str]]:
#         """
#         处理LLM输出，提取报告结构
        
#         Args:
#             output: LLM原始输出
            
#         Returns:
#             处理后的报告结构列表
#         """
#         try:
#             # 清理响应文本
#             cleaned_output = remove_reasoning_from_output(output)
#             cleaned_output = clean_json_tags(cleaned_output)
            
#             # 解析JSON
#             try:
#                 report_structure = json.loads(cleaned_output)
#             except JSONDecodeError:
#                 # 使用更强大的提取方法
#                 report_structure = extract_clean_response(cleaned_output)
#                 if "error" in report_structure:
#                     raise ValueError("JSON解析失败")
            
#             # 验证结构
#             if not isinstance(report_structure, list):
#                 raise ValueError("报告结构应该是一个列表")
            
#             # 验证每个段落
#             validated_structure = []
#             for i, paragraph in enumerate(report_structure):
#                 if not isinstance(paragraph, dict):
#                     continue
                
#                 title = paragraph.get("title", f"段落 {i+1}")
#                 content = paragraph.get("content", "")
                
#                 validated_structure.append({
#                     "title": title,
#                     "content": content
#                 })
            
#             return validated_structure
            
#         except Exception as e:
#             self.log_error(f"处理输出失败: {str(e)}")
#             # 返回默认结构
#             return [
#                 {
#                     "title": "概述",
#                     "content": f"对'{self.query}'的总体概述和背景介绍"
#                 },
#                 {
#                     "title": "详细分析", 
#                     "content": f"深入分析'{self.query}'的相关内容"
#                 }
#             ]
    
#     def mutate_state(self, input_data: Any = None, state: State = None, **kwargs) -> State:
#         """
#         将报告结构写入状态
        
#         Args:
#             input_data: 输入数据
#             state: 当前状态，如果为None则创建新状态
#             **kwargs: 额外参数
            
#         Returns:
#             更新后的状态
#         """
#         if state is None:
#             state = State()
        
#         try:
#             # 生成报告结构
#             report_structure = self.run(input_data, **kwargs)
            
#             # 设置查询和报告标题
#             state.query = self.query
#             if not state.report_title:
#                 state.report_title = f"关于'{self.query}'的深度研究报告"
            
#             # 添加段落到状态
#             for paragraph_data in report_structure:
#                 state.add_paragraph(
#                     title=paragraph_data["title"],
#                     content=paragraph_data["content"]
#                 )
            
#             self.log_info(f"已将 {len(report_structure)} 个段落添加到状态中")
#             return state
            
#         except Exception as e:
#             self.log_error(f"状态更新失败: {str(e)}")
#             raise e
"""
报告结构生成节点
负责规划报告的章节结构
"""

import json
from typing import Dict, Any, List

from .base_node import BaseNode
# 引入我们在 prompts.py 中定义的指令常量
from ..prompts.prompts import (
    LOGICAL_PROMPT_INSTRUCTION,
    FINANCIAL_PROMPT_INSTRUCTION,
    QUESTION_PROMPT_INSTRUCTION
)

class ReportStructureNode(BaseNode):
    """生成报告结构的节点"""
    
    def __init__(self, llm_client, query: str = ""):
        """
        初始化
        Args:
            llm_client: LLM客户端 (此模式下其实不需要，但为了兼容性保留)
            query: 初始查询
        """
        super().__init__(llm_client, "ReportStructureNode")
        self.query = query
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        覆盖原有的 LLM 生成逻辑，直接返回固定的投研报告结构
        """
        self.log_info(f"正在构建标准投研报告结构: {self.query}")
        
        # 这里的 input_data 通常是 query 字符串，或者包含 query 的字典
        if isinstance(input_data, dict):
            query = input_data.get("query", self.query)
        else:
            query = str(input_data)

        # === 硬编码固定结构 (不再调用 LLM) ===
        # 这样可以 100% 避免 JSON 解析错误，并确保每个指令都完整传递
        
        fixed_structure = [
            {
                "title": "1. 核心结论与预期差",
                "content": f"用一句话概括推荐逻辑，对比市场预期vs实际情况。重点寻找反直觉的信息。不要超过100字。针对目标：{query}。"
            },
            {
                "title": "2. 公司近况深度跟踪",
                "content": f"分析目标({query})最近的边际变化（新产品、新产能、管理层变动）。直言不讳地指出经营痛点。"
            },
            {
                "title": "3. 核心投资逻辑",
                "content": f"{LOGICAL_PROMPT_INSTRUCTION} 针对目标：{query}。"
            },
            {
                "title": "4. 财务质量分析",
                "content": f"{FINANCIAL_PROMPT_INSTRUCTION} 针对目标：{query}。"
            },
            {
                "title": "5. 调研问题大纲",
                "content": f"{QUESTION_PROMPT_INSTRUCTION} 针对目标：{query}。"
            },
            {
                "title": "6. 风险提示",
                "content": f"列出核心杀逻辑风险（不仅仅是宏观风险，要是公司特有的）。针对目标：{query}。"
            }
        ]

        self.log_info(f"成功构建 {len(fixed_structure)} 个标准投研段落")
        
        return {
            "report_structure": fixed_structure
        }

    def mutate_state(self, state: Any) -> Any:
        """
        更新状态
        """
        # 获取结构
        # 这里传入 state.query 确保使用的是最新的查询
        result = self.run({"query": state.query})
        structure = result["report_structure"]
        
        # 将生成的段落添加到状态中
        for item in structure:
            state.add_paragraph(item["title"], item["content"])
            
        return state