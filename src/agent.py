import asyncio
import operator
from typing import Annotated, List, Dict, TypedDict, Optional, Any
from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send
import re
# 引入组件
from .state import SectionState, SectionMetadata, SectionOutput, reduce_list, reduce_overwrite,AgentState
from .nodes.structure_node import generate_structure_node
from .nodes.writer_node import write_section_node
from .nodes.reflector_node import reflector_node, should_continue
from .nodes.search_node import search_node 
from .llms.qwen_llm import QwenLLM
from .utils import load_config

# ==========================================
# 1. 定义 Reducer
# ==========================================

# def reduce_query(left: Optional[str], right: Optional[str]) -> str:
#     return left or right

# def reduce_list(left: Optional[list], right: Optional[list]) -> list:
#     if left is None:
#         left = []
#     if right is None:
#         right = []
#     return left + right

# class AgentState(TypedDict):
#     query: Annotated[str, reduce_query] 
#     sections: List[SectionMetadata]
#     completed_sections: Annotated[List[str], reduce_list]
    
#     # 【新增】用于汇总所有子节点的搜索结果，最后统一生成参考文献
#     aggregate_references: Annotated[List[Dict[str, Any]], reduce_list]
    
#     final_report: str

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
    # [修改点 1] 升级打包逻辑
    def format_output(state: SectionState):
        section_def = state['section_def']
        title = section_def['title'] if isinstance(section_def, dict) else section_def.title
        
        # 我们不在这里拼接 Reference，而是把元数据传出去
        output_data: SectionOutput = {
            "title": title,
            "content": state['current_content'],
            "local_refs": state.get('search_results', [])
        }
        
        return {
            "completed_sections": [output_data]
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
    
    # [修改点 2] 核心修复：全局重映射与文本替换
    def compile_report(state):
        sections_data = state.get("completed_sections", [])
        
        # --- 第一阶段：构建全局引用库 ---
        global_refs = []     # 存储最终的去重后引用列表
        url_to_global_id = {} # 辅助去重映射: url -> global_id
        
        # 遍历所有段落
        for sec in sections_data:
            local_refs = sec.get("local_refs", [])
            # 遍历该段落的每一个引用
            for ref in local_refs:
                url = ref.get('url', '')
                title = ref.get('title', '未知')
                
                # 生成唯一键 (优先用URL，没有URL用标题)
                unique_key = url if url and len(url) > 5 and "本地" not in url else title
                
                # 如果这个引用还没收录过，就收录进去
                if unique_key not in url_to_global_id:
                    new_id = len(global_refs) + 1
                    url_to_global_id[unique_key] = new_id
                    global_refs.append(ref)

        # --- 第二阶段：正文 ID 重写 ---
        final_content_parts = []
        
        for sec in sections_data:
            original_text = sec["content"]
            local_refs = sec.get("local_refs", [])
            
            # 构建当前段落的映射表: Local_ID -> Global_ID
            # Worker 生成的引用是按顺序的 [1], [2]... 对应 local_refs[0], local_refs[1]...
            local_id_map = {}
            for i, ref in enumerate(local_refs, 1): # i 是局部ID (1, 2...)
                url = ref.get('url', '')
                title = ref.get('title', '未知')
                unique_key = url if url and len(url) > 5 and "本地" not in url else title
                
                # 找到它在全局库里的 ID
                if unique_key in url_to_global_id:
                    global_id = url_to_global_id[unique_key]
                    local_id_map[i] = global_id
            
            # 定义正则替换函数
            def replace_match(match):
                # 捕获到的数字，例如 [14] 中的 14
                local_num = int(match.group(1))
                # 查找映射，如果找不到（极少情况），保留原数字
                global_num = local_id_map.get(local_num, local_num)
                return f"[{global_num}]"
            
            # 执行正则替换：把 [14] 变成 [3]
            # 匹配模式：\[(\d+)\]  --> 匹配方括号内的数字
            fixed_text = re.sub(r'\[(\d+)\]', replace_match, original_text)
            
            # 加上标题
            final_content_parts.append(f"## {sec['title']}\n\n{fixed_text}")

        # --- 第三阶段：生成最终报告 ---
        body = f"# {state.get('query', '研究报告')}\n\n" + "\n\n---\n\n".join(final_content_parts)
        
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
            "completed_sections": [] 
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
        print("✅ StructuredReportAgent 初始化完成 (全局重映射引用版)")

    async def run(self, query: str):
        inputs = {
            "query": query,
            "sections": [],
            "completed_sections": []
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