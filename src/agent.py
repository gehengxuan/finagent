# 
"""
src/agent.py
Agent 主类 - 简单的包装器
"""

import asyncio
from typing import Optional

from .graph.builder import GraphFactory
from .utils import load_config


class StructuredReportAgent:
    """
    结构化报告生成智能体
    
    使用方式:
        agent = StructuredReportAgent()
        report = agent.generate_report("宁德时代投资价值分析")
    """
    
    def __init__(self):
        """初始化 Agent"""
        self.graph = GraphFactory.create_graph()
        self._invoke_config = GraphFactory.get_invoke_config()
        print("✅ StructuredReportAgent 初始化完成")
    
    async def run(self, query: str) -> str:
        """
        异步执行报告生成
        
        Args:
            query: 查询/主题文本
        
        Returns:
            生成的 Markdown 报告
        """
        inputs = {
            "query": query,
            "sections": [],
            "completed_sections": []
        }
        
        final_output = None
        print(f"🚀 开始执行: {query}")
        
        # 流式处理图事件
        async for event in self.graph.astream(
            inputs,
            config=self._invoke_config
        ):
            for node_name, value in event.items():
                # 大纲生成
                if node_name == "generate_structure":
                    sections_count = len(value.get('sections', []))
                    print(f"  📋 [大纲] 已生成 {sections_count} 个段落任务")
                
                # 段落处理进度
                elif node_name == "section_worker":
                    if "completed_sections" in value:
                        completed = len(value.get('completed_sections', []))
                        print(f"  ✍️ [进度] 已完成 {completed} 个段落")
                
                # 报告编译完成
                elif node_name == "compile":
                    final_output = value.get("final_report")
                    print(f"  📝 [编译] 报告已生成 ({len(final_output)} 字)")
        
        return final_output
    
    def generate_report(self, query: str) -> str:
        """
        同步方法：生成报告
        
        Args:
            query: 查询/主题文本
        
        Returns:
            生成的 Markdown 报告
        """
        return asyncio.run(self.run(query))


# 便利函数
def create_agent() -> StructuredReportAgent:
    """创建 Agent 实例"""
    return StructuredReportAgent()