import json
from langchain_core.messages import SystemMessage, HumanMessage
from ..state.state import SectionState
from ..prompts.prompts import SYSTEM_PROMPT_REFLECTION

def reflector_node(state: SectionState, llm):
    """
    反思节点
    """
    # --- 修改点：使用字典访问 ---
    section_def = state["section_def"]
    section_title = section_def["title"] # .title -> ["title"]
    instruction = section_def["content"] # .content -> ["content"]
    
    current_draft = state["current_content"]
    
    input_data = {
        "title": section_title,
        "content": instruction,
        "paragraph_latest_state": current_draft
    }
    
    print(f"🧐 [Reflector] 正在审阅段落: 【{section_title}】")

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT_REFLECTION),
            HumanMessage(content=json.dumps(input_data, ensure_ascii=False))
        ]
        
        response = llm.invoke(messages, response_format={"type": "json_object"})
        result_json = json.loads(response.content)
        
        search_query = result_json.get("search_query", "")
        reasoning = result_json.get("reasoning", "")
        
        if search_query and search_query.strip() != "":
            print(f"  > ⚠️ 发现缺陷: {reasoning}")
            print(f"  > 🔍 提出补搜: {search_query}")
            return {
                "critique": reasoning,
                "feedback_search_query": search_query,
                "is_satisfactory": False
            }
        else:
            print(f"  > ✅ 质量达标")
            return {
                "critique": None,
                "feedback_search_query": None,
                "is_satisfactory": True
            }

    except Exception as e:
        print(f"  > [Error] 反思解析失败: {e}")
        return {
            "critique": None,
            "is_satisfactory": True
        }
# should_continue 函数保持不变
def should_continue(state: SectionState):
    is_satisfactory = state.get("is_satisfactory", False)
    iteration = state.get("iteration_count", 0)
    # 最大迭代次数，避免死循环
    if iteration >= 3:
        return "end"
    
    if is_satisfactory:
        return "end"
    
    if state.get("feedback_search_query"):
        return "search"
    else:
        return "rewrite"