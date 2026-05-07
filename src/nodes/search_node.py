import json
from langchain_core.messages import SystemMessage, HumanMessage
from ..state.state import SectionState
from ..prompts.prompts import SYSTEM_PROMPT_FIRST_SEARCH
from ..utils import load_config
from ..utils.text_processing import get_doc_key


# ---------------------------------------------------------------------------
# 搜索后端路由
# ---------------------------------------------------------------------------

def _build_search_backends(config):
    """根据配置构建搜索后端列表，按优先级排列。"""
    backends = []

    # 1. 本地文件（如果配置了 local_files）
    if config.local_files:
        from ..tools.local_file_search import LocalFileSearch
        backends.append(("local", LocalFileSearch(file_paths=config.local_files)))

    # 2. 在线搜索（Tavily）
    if config.enable_online_search and config.tavily_api_key:
        from ..tools.tavily_search import TavilySearch
        backends.append(("tavily", TavilySearch(api_key=config.tavily_api_key)))

    # 3. LightRAG（兜底，如果以上都没配就尝试）
    if not backends:
        try:
            from ..tools.lightrag_search import LightRAGSearch
            backends.append(("lightrag", LightRAGSearch()))
        except Exception as e:
            print(f"  > [Warning] LightRAG 初始化失败: {e}")

    return backends


def search_node(state: SectionState, llm):
    """
    搜索节点：支持【初次意图生成】和【反思补搜】两种模式。

    搜索后端按配置自动选择：
      - config.local_files 有值 → 本地文件检索
      - config.enable_online_search=True → Tavily 网络搜索
      - 以上都没配 → 回退到 LightRAG
    多个后端同时存在时结果合并。
    """
    config = load_config()
    backends = _build_search_backends(config)

    if not backends:
        print("  > ⚠️ 没有可用的搜索后端，请检查 config")
        return {"search_results": state.get("search_results", []), "feedback_search_query": None}

    query_to_search = ""
    search_reasoning = ""
    
    section_def = state["section_def"]
    if not isinstance(section_def, dict):
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

    # 从所有后端收集结果
    max_per_backend = config.max_search_results or 5
    new_info = []
    for backend_name, backend in backends:
        try:
            results = backend.search(query_to_search, max_results=max_per_backend)
        except Exception as e:
            print(f"  > [Error] {backend_name} 搜索失败: {e}")
            results = []

        for res in results:
            snippet = {
                "title": res.get("title", "未知标题"),
                "content": res.get("content", ""),
                "url": res.get("url", ""),
                "query": query_to_search,
            }
            new_info.append(snippet)

    if new_info:
        print(f"  > 获得 {len(new_info)} 条结果")
    else:
        print("  > ⚠️ 未搜索到有效信息")

    # ============================================================
    # 【源头去重】：合并到现有结果前先去重
    # ============================================================
    current_results = state.get("search_results", [])
    
    # 记录已有的文档
    existing_keys = {get_doc_key(item) for item in current_results}
    
    # 只添加新的、未重复的搜索结果
    deduplicated_new_info = []
    for item in new_info:
        key = get_doc_key(item)
        if key not in existing_keys:
            deduplicated_new_info.append(item)
            existing_keys.add(key)
        else:
            print(f"  > [去重] 跳过重复文档: {item.get('title', '未知')[:30]}...")
    
    updated_results = current_results + deduplicated_new_info
    print(f"  > 累计搜索结果: {len(updated_results)} 条（去重后）")
    
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