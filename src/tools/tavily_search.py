"""Tavily 网络搜索客户端封装。"""

from typing import Any, Dict, List, Optional


class TavilySearch:
    """Tavily 实时网络搜索。"""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            from ..utils import load_config
            config = load_config()
            api_key = config.tavily_api_key

        if not api_key:
            raise ValueError("Tavily API Key 未配置，请在 config.py 中设置 tavily_api_key")

        from tavily import TavilyClient
        self.client = TavilyClient(api_key=api_key)
        print("  [Tavily] 初始化完成")

    def search(self, query: str, max_results: int = 5, timeout: int = 60) -> List[Dict[str, Any]]:
        """执行网络搜索并返回标准化结果。"""
        try:
            print(f"  > [Tavily] 正在搜索: {query[:40]}... (max_results={max_results})")
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
            )
            results = []
            for item in response.get("results", []):
                content = item.get("content", "")
                if len(content) < 10:
                    continue
                results.append({
                    "title": item.get("title", "网络搜索结果"),
                    "url": item.get("url", ""),
                    "content": f"【来源: {item.get('title', '未知')}】\n{content}",
                    "score": item.get("score", 0.0),
                })
            print(f"  > [Tavily] 返回 {len(results)} 条有效结果")
            return results
        except Exception as e:
            print(f"  > [Tavily Exception] 搜索失败: {e}")
            return []
