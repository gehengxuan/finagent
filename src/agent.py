import asyncio
import operator
from typing import Annotated, List, Dict, TypedDict, Optional, Any
from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send

# 引入组件
from .state import SectionState, SectionMetadata
from .nodes.structure_node import generate_structure_node
from .nodes.writer_node import write_section_node
from .nodes.reflector_node import reflector_node, should_continue
from .nodes.search_node import search_node 
from .llms.qwen_llm import QwenLLM
from .utils import load_config

# ==========================================
# 1. 定义 Reducer
# ==========================================

def reduce_query(left: Optional[str], right: Optional[str]) -> str:
    return left or right

def reduce_list(left: Optional[list], right: Optional[list]) -> list:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

class AgentState(TypedDict):
    query: Annotated[str, reduce_query] 
    sections: List[SectionMetadata]
    completed_sections: Annotated[List[str], reduce_list]
    
    # 【新增】用于汇总所有子节点的搜索结果，最后统一生成参考文献
    aggregate_references: Annotated[List[Dict[str, Any]], reduce_list]
    
    final_report: str

# ==========================================
# 2. 构建图逻辑
# ==========================================
def _build_graph():
    config = load_config()
    llm = QwenLLM(api_key=config.dashscope_api_key)

    # --- 定义子图 (Section Worker) ---
    workflow_sec = StateGraph(SectionState)
    
    workflow_sec.add_node("search", lambda s: search_node(s, llm))
    workflow_sec.add_node("write", lambda s: write_section_node(s, llm))
    workflow_sec.add_node("reflect", lambda s: reflector_node(s, llm))
    
    # [修改点 1]：format_output 不再生成 Reference 文本
    def format_output(state: SectionState):
        section_def = state['section_def']
        title = section_def['title'] if isinstance(section_def, dict) else section_def.title
        
        # 只保留正文，不拼接参考资料
        formatted = f"## {title}\n\n{state['current_content']}"
        
        # 提取当前节点的搜索结果，准备向上合并
        current_refs = state.get('search_results', [])
        
        return {
            "completed_sections": [formatted],
            # 将原始搜索数据传给主图的 aggregate_references
            "aggregate_references": current_refs
        }
    
    workflow_sec.add_node("format_output", format_output)
    
    # 子图连线
    workflow_sec.add_edge(START, "search")
    workflow_sec.add_edge("search", "write")
    workflow_sec.add_edge("write", "reflect")
    
    workflow_sec.add_conditional_edges(
        "reflect", 
        should_continue, 
        {
            "end": "format_output",
            "search": "search",
            "rewrite": "write"
        }
    )
    workflow_sec.add_edge("format_output", END)
    
    section_subgraph = workflow_sec.compile()

    # --- 定义主图 (Main Graph) ---
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_structure", lambda s: generate_structure_node(s, llm))
    workflow.add_node("section_worker", section_subgraph)
    
    # [修改点 2]：在编译阶段统一生成参考文献
    def compile_report(state):
        content_list = state.get("completed_sections", [])
        all_refs = state.get("aggregate_references", [])
        
        # 1. 拼接正文
        if not content_list:
            body = "⚠️ 生成失败：未能收集到任何段落内容。"
        else:
            body = f"# {state.get('query', '研究报告')}\n\n" + "\n\n---\n\n".join(content_list)
            
        # 2. 处理参考文献（去重 + 格式化）
        ref_section = ""
        if all_refs:
            # 简单去重：根据 url 或 title
            unique_refs = {}
            for ref in all_refs:
                # 优先用 URL 去重，没有 URL 用 Title
                key = ref.get('url') if ref.get('url') and ref.get('url') != "本地检索" else ref.get('title')
                if key:
                    unique_refs[key] = ref
            
            # 生成列表文本
            if unique_refs:
                ref_section = "\n\n# 参考资料 / References\n\n"
                for i, ref in enumerate(unique_refs.values(), 1):
                    title = ref.get('title', '未知来源')
                    url = ref.get('url', '')
                    
                    line = f"{i}. {title}"
                    if url and url != "本地检索":
                        line += f"  \n   链接: {url}"
                    ref_section += line + "\n"

        final_md = body + ref_section
            
        return {"final_report": final_md}

    workflow.add_node("compile", compile_report)

    # 主流程连线
    workflow.add_edge(START, "generate_structure")
    
    workflow.add_conditional_edges(
        "generate_structure",
        lambda state: [Send("section_worker", {
            "section_def": sec, 
            "query": state["query"], 
            "iteration_count": 0, 
            "search_results": [], 
            "current_content": "", 
            "is_satisfactory": False,
            "completed_sections": [],
            "aggregate_references": [] # 初始化
        }) for sec in state["sections"]],
        ["section_worker"]
    )
    
    workflow.add_edge("section_worker", "compile")
    workflow.add_edge("compile", END)

    return workflow.compile()

# ==========================================
# 3. 包装类
# ==========================================
class StructuredReportAgent:
    def __init__(self):
        self.graph = _build_graph()
        print("✅ StructuredReportAgent 初始化完成 (全局引用版)")

    async def run(self, query: str):
        inputs = {
            "query": query,
            "sections": [],
            "completed_sections": [],
            "aggregate_references": []
        }
        
        final_output = None
        print(f"🚀 开始执行: {query}")
        
        async for event in self.graph.astream(inputs, config={"recursion_limit": 50}):
            for node_name, value in event.items():
                if node_name == "generate_structure":
                    print(f"  📋 [大纲] 已生成 {len(value['sections'])} 个段落任务")
                elif node_name == "section_worker":
                    if "completed_sections" in value:
                        print(f"  ✍️ [进度] 一个段落撰写完成")
                elif node_name == "compile":
                    final_output = value["final_report"]
                    
        return final_output

    def generate_report(self, query: str):
        return asyncio.run(self.run(query))