"""本地文件搜索工具。

将 config.local_files 指定的本地文件按段落分块，以搜索结果的形式返回，
使 search_node 能像使用在线搜索一样消费本地 10-K 等文档。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_file_text(file_path: str) -> str:
    """读取单个文本文件。"""
    path = Path(file_path)
    if not path.exists():
        print(f"  > [LocalFile] 文件不存在: {file_path}")
        return ""
    if not path.is_file():
        print(f"  > [LocalFile] 路径不是文件: {file_path}")
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  > [LocalFile] 读取失败 {file_path}: {e}")
        return ""


def _chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """将长文本按段落边界分块。"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # 尝试按双换行（段落）切分
    paragraphs = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # 如果单段就超了，按字符硬切
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i : i + chunk_size])
            else:
                current = para
                continue
            current = ""

    if current:
        chunks.append(current)

    return chunks


def _score_chunk(chunk: str, query: str) -> float:
    """对 chunk 做极简 keyword 相关性打分（0-1），用于排序。"""
    if not query:
        return 0.0
    keywords = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
    if not keywords:
        return 0.0
    chunk_lower = chunk.lower()
    hit = sum(1 for kw in keywords if kw in chunk_lower)
    return round(hit / len(keywords), 4)


class LocalFileSearch:
    """基于本地文件的搜索工具。"""

    def __init__(self, file_paths: Optional[List[str]] = None, chunk_size: int = 1500):
        if file_paths is None:
            from ..utils import load_config
            config = load_config()
            file_paths = config.local_files or []

        self.file_paths = file_paths
        self.chunk_size = chunk_size
        self._chunks: List[Dict[str, Any]] | None = None  # lazy
        print(f"  [LocalFile] 初始化完成, 文件数: {len(self.file_paths)}")

    def _ensure_loaded(self) -> None:
        if self._chunks is not None:
            return
        self._chunks = []
        for fp in self.file_paths:
            text = _read_file_text(fp)
            if not text:
                continue
            fname = Path(fp).name
            for idx, chunk in enumerate(_chunk_text(text, self.chunk_size)):
                self._chunks.append({
                    "title": f"{fname} (段落 {idx + 1})",
                    "url": f"local://{fp}#chunk{idx + 1}",
                    "content": chunk,
                    "source_file": fp,
                })
        print(f"  > [LocalFile] 共加载 {len(self._chunks)} 个文本段落")

    def search(self, query: str, max_results: int = 5, **_kwargs) -> List[Dict[str, Any]]:
        """按关键词相关性返回 top-k 最相关段落。"""
        self._ensure_loaded()
        if not self._chunks:
            print("  > [LocalFile] 没有可用的本地文档")
            return []

        scored = []
        for chunk in self._chunks:
            score = _score_chunk(chunk["content"], query)
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk in scored[:max_results]:
            results.append({
                "title": chunk["title"],
                "url": chunk["url"],
                "content": f"【来源: {chunk['title']}】\n{chunk['content']}",
                "score": score,
            })
        print(f"  > [LocalFile] 返回 {len(results)} 条结果 (最高相关度: {scored[0][0]:.2f})")
        return results
