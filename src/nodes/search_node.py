import json
from langchain_core.messages import SystemMessage, HumanMessage
from ..state.state import SectionState
from ..tools.lightrag_search import LightRAGSearch
from ..prompts.prompts import SYSTEM_PROMPT_FIRST_SEARCH
from ..utils import load_config

config = load_config()
rag_tool = LightRAGSearch()

def search_node(state: SectionState, llm):
    """
    搜索节点：支持【初次意图生成】和【反思补搜】两种模式
    """
    query_to_search = ""
    search_reasoning = ""
    
    # --- 修改点 1：使用字典方式访问 section_def ---
    section_def = state["section_def"]
    # 确保 section_def 是字典
    if not isinstance(section_def, dict):
        # 兼容性处理：如果是对象则转字典，或者直接报错
        try:
            section_def = section_def.__dict__
        except:
            pass

    # A. 反思后的补搜
    if state.get("feedback_search_query"):
        query_to_search = state["feedback_search_query"]
        search_reasoning = f"响应反思修改: {state.get('critique')}"
        print(f"🔍 [Search] 执行补搜: {query_to_search}")
        
    # B. 初次搜索
    else:
        print(f"🔍 [Search] 正在生成初次搜索词...")
        query_to_search, search_reasoning = _generate_initial_query(state, llm)
        print(f"  > 生成查询: {query_to_search}")

    # 执行搜索
    try:
        results = rag_tool.search(query_to_search, max_results=5)
    except Exception as e:
        print(f"  > [Error] 搜索工具调用失败: {e}")
        results = []

    # 格式化结果
    new_info = []
    if results:
        print(f"  > 获得 {len(results)} 条结果")
        for res in results:
            snippet = {
                "title": res.get('title', '未知标题'), # <--- 加上这一行！
                "content": f"【来源: {res.get('title', '未知')}】\n{res.get('content', '')}",
                "url": res.get("url", ""),
                "query": query_to_search
            }
            new_info.append(snippet)
    else:
        print("  > ⚠️ 未搜索到有效信息")

    current_results = state.get("search_results", [])
    updated_results = current_results + new_info
    
    return {
        "search_results": updated_results,
        "feedback_search_query": None
    }

def _generate_initial_query(state: SectionState, llm):
    """
    辅助函数：调用 LLM 生成搜索词
    """
    # --- 修改点 2：使用字典方式访问 ---
    section_def = state["section_def"]
    section_title = section_def["title"]   # 之前是 .title
    instruction = section_def["content"]   # 之前是 .content
    
    input_data = {
        "title": section_title,
        "content": instruction
    }
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_FIRST_SEARCH),
        HumanMessage(content=json.dumps(input_data, ensure_ascii=False))
    ]
    
    try:
        response = llm.invoke(messages, response_format={"type": "json_object"})
        result = json.loads(response.content)
        
        query = result.get("search_query", state["query"])
        reasoning = result.get("reasoning", "")
        
        if state["query"] not in query:
            query = f"{state['query']} {query}"
            
        return query, reasoning
        
    except Exception as e:
        print(f"  > [Error] 搜索意图生成失败: {e}")
        fallback = f"{state['query']} {section_title}"
        return fallback, "生成失败，使用兜底查询"