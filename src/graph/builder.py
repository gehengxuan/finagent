"""
src/graph/builder.py
图构建器 - 负责组装 LangGraph
"""
from ..llms.qwen_llm import QwenLLM
from typing import Any, Callable, Dict, List
from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send
import re

from .graph_config import SUBGRAPH_TOPOLOGY, MAIN_GRAPH_TOPOLOGY, EXECUTION_CONFIG
from ..state import SectionState, AgentState
from ..nodes.structure_node import generate_structure_node
from ..nodes.writer_node import write_section_node
from ..nodes.reflector_node import reflector_node, should_continue
from ..nodes.search_node import search_node
from ..utils import load_config


class SubGraphBuilder:
    """子图构建器"""
    
    def __init__(self, llm):
        self.llm = llm
        self.config = SUBGRAPH_TOPOLOGY
    
    def build(self) -> Any:
        """
        构建子图
        
        拓扑:
            START → search → write → reflect → format_output → END
                      ↑                ↓
                      └────────────────┘ (条件循环)
        """
        print("🔨 构建子图 (SectionWorker)...")
        
        workflow = StateGraph(SectionState)
        
        # 添加节点
        self._add_nodes(workflow)
        
        # 添加边
        self._add_edges(workflow)
        
        # 添加条件边
        self._add_conditional_edges(workflow)
        
        subgraph = workflow.compile()
        print("✅ 子图构建完成")
        return subgraph
    
    def _add_nodes(self, workflow: StateGraph):
        """添加所有节点"""
        workflow.add_node("search", lambda s: search_node(s, self.llm))
        workflow.add_node("write", lambda s: write_section_node(s, self.llm))
        workflow.add_node("reflect", lambda s: reflector_node(s, self.llm))
        workflow.add_node("format_output", self._create_format_output_node())
    
    def _add_edges(self, workflow: StateGraph):
        """添加普通边"""
        workflow.add_edge(START, "search")
        workflow.add_edge("search", "write")
        workflow.add_edge("write", "reflect")
        workflow.add_edge("format_output", END)
    
    def _add_conditional_edges(self, workflow: StateGraph):
        """添加条件边"""
        workflow.add_conditional_edges(
            "reflect",
            should_continue,  # 使用既有的条件函数
            {
                "end": "format_output",
                "search": "search",
                "rewrite": "write"
            }
        )
    
    def _create_format_output_node(self) -> Callable:
        """
        创建 format_output 节点
        
        作用: 把段落内容和搜索结果打包成 SectionOutput
        """
        def format_output(state: SectionState):
            section_def = state['section_def']
            title = (
                section_def['title'] 
                if isinstance(section_def, dict) 
                else section_def.title
            )
            
            output_data = {
                "title": title,
                "content": state['current_content'],
                "local_refs": state.get('search_results', [])
            }
            
            return {
                "completed_sections": [output_data]
            }
        
        return format_output


class MainGraphBuilder:
    """主图构建器"""
    
    def __init__(self, llm, subgraph: Any):
        self.llm = llm
        self.subgraph = subgraph
        self.config = MAIN_GRAPH_TOPOLOGY
    
    def build(self) -> Any:
        """
        构建主图
        
        拓扑:
            START → generate_structure → [Send] section_worker → compile → END
        """
        print("🔨 构建主图 (MainGraph)...")
        
        workflow = StateGraph(AgentState)
        
        # 添加节点
        self._add_nodes(workflow)
        
        # 添加边
        self._add_edges(workflow)
        
        # 添加条件边
        self._add_conditional_edges(workflow)
        
        main_graph = workflow.compile()
        print("✅ 主图构建完成")
        return main_graph
    
    def _add_nodes(self, workflow: StateGraph):
        """添加所有节点"""
        workflow.add_node("generate_structure", lambda s: generate_structure_node(s, self.llm))
        workflow.add_node("section_worker", self.subgraph)
        workflow.add_node("compile", self._create_compile_node())
    
    def _add_edges(self, workflow: StateGraph):
        """添加普通边"""
        workflow.add_edge(START, "generate_structure")
        workflow.add_edge("section_worker", "compile")
        workflow.add_edge("compile", END)
    
    def _add_conditional_edges(self, workflow: StateGraph):
        """添加条件边"""
        workflow.add_conditional_edges(
            "generate_structure",
            self._map_sections_to_workers,
            ["section_worker"]
        )
    
    def _create_compile_node(self) -> Callable:
        """
        创建 compile_report 节点
        
        作用: 汇总所有段落，生成全局引用映射，替换本地引用为��局引用
        """
        def compile_report(state: AgentState):
            sections_data = state.get("completed_sections", [])
            
            # --- 阶段 1: 构建全局引用库 ---
            global_refs = []
            url_to_global_id = {}
            
            # 遍历所有段落，收集所有引用
            for sec in sections_data:
                local_refs = sec.get("local_refs", [])
                
                for ref in local_refs:
                    url = ref.get('url', '')
                    title = ref.get('title', '未知')
                    
                    # 生成唯一键
                    unique_key = (
                        url 
                        if url and len(url) > 5 and "本地" not in url 
                        else title
                    )
                    
                    # 去重
                    if unique_key not in url_to_global_id:
                        new_id = len(global_refs) + 1
                        url_to_global_id[unique_key] = new_id
                        global_refs.append(ref)
            
            # --- 阶段 2: 重写正文中的引用 ID ---
            final_content_parts = []
            
            for sec in sections_data:
                original_text = sec["content"]
                local_refs = sec.get("local_refs", [])
                
                # 建立局部 ID → 全局 ID 映射
                local_id_map = {}
                for i, ref in enumerate(local_refs, 1):
                    url = ref.get('url', '')
                    title = ref.get('title', '未知')
                    
                    unique_key = (
                        url 
                        if url and len(url) > 5 and "本地" not in url 
                        else title
                    )
                    
                    if unique_key in url_to_global_id:
                        global_id = url_to_global_id[unique_key]
                        local_id_map[i] = global_id
                
                # 正则替换: [1] → [3] (例如)
                def replace_match(match):
                    local_num = int(match.group(1))
                    global_num = local_id_map.get(local_num, local_num)
                    return f"[{global_num}]"
                
                fixed_text = re.sub(r'\[(\d+)\]', replace_match, original_text)
                
                # 对正文中的重复引用进行去重处理
                fixed_text = self._deduplicate_consecutive_citations(fixed_text)
                
                final_content_parts.append(f"## {sec['title']}\n\n{fixed_text}")
            
            # --- 阶段 3: 生成最终报告 ---
            body = (
                f"# {state.get('query', '研究报告')}\n\n" +
                "\n\n---\n\n".join(final_content_parts)
            )
            
            # 生成文末引用列表
            ref_section = ""
            if global_refs:
                ref_section = "\n\n### 参考资料 / References\n"
                for i, ref in enumerate(global_refs, 1):
                    title = ref.get('title', '未知来源')
                    url = ref.get('url', '')
                    
                    line = f"- [{i}] {title}"
                    if url and "本地" not in url:
                        line += f"  ([链接]({url}))"
                    
                    ref_section += line + "\n"
            
            return {"final_report": body + ref_section}
        
        return compile_report
    
    def _deduplicate_consecutive_citations(self, text: str) -> str:
        """
        去重连续出现的相同引用号
        
        处理以下情况：
        - [[1]] [[1]] [[2]] → [[1]] [[2]]
        - [[4]]、[[4]]、[[9]] → [[4]]、[[9]]  (保留分隔符)
        - [1] [1] [2] → [1] [2]
        - [[4]] [[5]] [[7]] [[4]] → [[4]] [[5]] [[7]]（去除交错重复）
        
        Args:
            text: 原始文本
            
        Returns:
            去重后的文本
        """
        
        def deduplicate_double_bracket_consecutive(text):
            """处理 [[1]] [[1]] 格式的连续重复"""
            prev_text = ""
            max_iterations = 10
            iteration = 0
            
            while text != prev_text and iteration < max_iterations:
                prev_text = text
                iteration += 1
                
                # 匹配 [[N]]、[[N]] 或 [[N]] [[N]] 这样的相邻重复模式
                pattern = r'\[\[(\d+)\]\]([\s、，,]*)\[\[(\d+)\]\]'
                
                def replace_func(match):
                    num1 = match.group(1)
                    separator = match.group(2)
                    num2 = match.group(3)
                    
                    # 如果两个数字相同，去掉第一个
                    if num1 == num2:
                        return f"[[{num1}]]"
                    else:
                        # 不相同，保留原样
                        return match.group(0)
                
                text = re.sub(pattern, replace_func, text)
            
            return text
        
        def deduplicate_single_bracket_consecutive(text):
            """处理 [1] [1] 格式的连续重复"""
            prev_text = ""
            max_iterations = 10
            iteration = 0
            
            while text != prev_text and iteration < max_iterations:
                prev_text = text
                iteration += 1
                
                # 匹配 [N]、[N] 或 [N] [N] 这样的相邻重复模式
                pattern = r'\[(\d+)\]([\s、，,]*)\[(\d+)\]'
                
                def replace_func(match):
                    num1 = match.group(1)
                    separator = match.group(2)
                    num2 = match.group(3)
                    
                    # 如果两个数字相同，去掉第一个
                    if num1 == num2:
                        return f"[{num1}]"
                    else:
                        # 不相同，保留原样
                        return match.group(0)
                
                text = re.sub(pattern, replace_func, text)
            
            return text
        
        # 先处理 [[N]] 格式（连续相邻的重复）
        text = deduplicate_double_bracket_consecutive(text)
        
        # 再处理 [[N]] 格式（引用序列块中的交错重复）
        # 在一个"引用序列块"（一连串引用，中间仅有空格或分隔符）中去重
        pattern = r'\[\[\d+\]\](?:[\s、，,]+\[\[\d+\]\])*'
        
        def deduplicate_block(match):
            block = match.group(0)
            
            # 提取所有引用号
            citation_pattern = r'\[\[(\d+)\]\]'
            citations = re.findall(citation_pattern, block)
            
            # 如果没有重复，返回原样
            if len(set(citations)) == len(citations):
                return block
            
            # 去重但保持顺序
            seen = set()
            unique = []
            for c in citations:
                if c not in seen:
                    seen.add(c)
                    unique.append(c)
            
            # 获取分隔符
            sep_match = re.search(r'\]\]([\s、，,]+)\[\[', block)
            if sep_match:
                sep = sep_match.group(1)
            else:
                sep = ' '
            
            # 重建
            return sep.join([f"[[{c}]]" for c in unique])
        
        text = re.sub(pattern, deduplicate_block, text)
        
        # 最后处理 [N] 格式
        text = deduplicate_single_bracket_consecutive(text)
        
        return text
    
    def _map_sections_to_workers(self, state: AgentState) -> List:
        """
        映射段落到 worker 任务
        
        为每个段落创建一个独立的 Send 任务，实现并行处理
        """
        sections = state.get("sections", [])
        query = state.get("query", "")
        
        print(f"📋 映射 {len(sections)} 个段落到 worker...")
        
        tasks = []
        for sec in sections:
            task = Send("section_worker", {
                "section_def": sec,
                "query": query,
                "iteration_count": 0,
                "search_results": [],
                "current_content": "",
                "is_satisfactory": False,
                "completed_sections": []
            })
            tasks.append(task)
        
        return tasks


class GraphFactory:
    """图工厂 - 统一管理图的创建"""
    
    @staticmethod
    def create_graph() -> Any:
        """创建完整的图（子图 + 主图）"""
        # 初始化 LLM
        config = load_config()
        llm = QwenLLM(api_key=config.dashscope_api_key)
        
        # 构建子图
        subgraph_builder = SubGraphBuilder(llm)
        subgraph = subgraph_builder.build()
        
        # 构建主图
        main_graph_builder = MainGraphBuilder(llm, subgraph)
        main_graph = main_graph_builder.build()
        
        return main_graph