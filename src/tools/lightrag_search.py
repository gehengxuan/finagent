import os
import requests
import json
from typing import List, Dict, Any, Optional

# --- 辅助函数：如果未来同学又改回复杂格式，这个还能兜底 ---
def clean_content_text(text: str) -> str:
    """简单的文本清洗，防止内容包含过多的换行或无用空格"""
    if not text:
        return ""
    # 如果未来内容里又出现了 "Document Chunks" 这种复杂标记，可以在这里加逻辑
    # 目前看来直接返回即可，最多去掉首尾空格
    return text.strip()

class LightRAGSearch:
    """LightRAG 搜索客户端封装 (适配 /query/retrieval/report 接口)"""
    
    def __init__(self, 
                 base_url: str = "https://514efd9e.r25.cpolar.top", 
                 api_key: Optional[str] = None,
                 # [更新] 默认接口路径改为你测试成功的路径
                 endpoint: str = "/query/retrieval/report"): 
        
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}{endpoint}"
        self.api_key = api_key
        
        print(f"  [LightRAG] 初始化完成")
        print(f"  - 目标接口: {self.api_url}")

    def search(self, query: str, max_results: int = 5, timeout: int = 60) -> List[Dict[str, Any]]:
        """
        执行搜索
        Args:
            query: 搜索词
            max_results: 返回数量 (对应参数 k)
        """
        # [更新] 参数构造：根据 curl 命令，使用 'k' 而非 'top_k'
        payload = {
            "query": query,
            "k": max_results
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # 鉴权处理：如果环境变量或初始化时提供了 Key，则添加
        if self.api_key and self.api_key != "no-key-needed":
             headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            print(f"  > [LightRAG] 正在请求: {query[:15]}... (k={max_results})")
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=timeout
            )
            
            if response.status_code != 200:
                print(f"  > [LightRAG Error] 状态码 {response.status_code}: {response.text[:200]}")
                return []

            # 解析返回的 JSON 数据
            return self._parse_response(response.json())

        except Exception as e:
            print(f"  > [LightRAG Exception] 连接失败: {str(e)}")
            return []

    def _parse_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        解析并标准化返回结果
        """
        results = []
        raw_items = []

        # 1. 结构归一化：确保 raw_items 是一个列表
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            # 兼容性处理：如果包裹在 {"data": ...} 或 {"results": ...} 里
            if "results" in data and isinstance(data["results"], list):
                raw_items = data["results"]
            elif "data" in data and isinstance(data["data"], list):
                raw_items = data["data"]
            else:
                # 假如返回的是单个对象
                raw_items = [data]

        print(f"  > [LightRAG] 收到 {len(raw_items)} 条原始数据，正在格式化...")

        # 2. 遍历清洗
        for item in raw_items:
            # 容错：确保 item 是字典
            if not isinstance(item, dict):
                continue
                
            # 提取字段 (优先取 content, 其次 text)
            raw_content = item.get("content") or item.get("text") or ""
            
            # 如果内容太短，可能是无效数据
            if len(raw_content) < 10:
                continue

            # 标准化对象结构
            standard_item = {
                "title": str(item.get("title", "LightRAG 检索文档")),
                # 标记来源为 lightrag，方便后续 Prompt 识别
                "url": str(item.get("url", "lightrag_source")), 
                "content": clean_content_text(raw_content),
                "score": float(item.get("score", 0.0))
            }
            results.append(standard_item)

        print(f"  > [LightRAG] 成功解析 {len(results)} 条有效内容")
        return results
def light_rag_search(query: str, max_results: int = 5, timeout: int = 60, 
                     api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    便捷的 LightRAG 搜索函数
    Args:
        query: 搜索词
        max_results: 返回数量
        timeout: 超时时间
        api_key: 可选的 API Key
    Returns:
        标准化的搜索结果列表
    """
    client = LightRAGSearch(api_key=api_key)
    return client.search(query=query, max_results=max_results, timeout=timeout)
# ==========================================
# 自测代码 (直接运行此文件可测试)
# ==========================================
if __name__ == "__main__":
    # 测试连接
    client = LightRAGSearch()
    # 模拟查询
    test_results = client.search("宁德时代产能", max_results=3)
    
    print("\n=== 测试结果展示 ===")
    for i, res in enumerate(test_results, 1):
        print(f"\n[结果 {i}]")
        print(f"标题: {res['title']}")
        print(f"内容摘要: {res['content'][:1000]}...")