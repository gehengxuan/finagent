"""
src/graph/graph_config.py
图的拓扑配置 - 集中管理所有图结构定义
"""

from typing import Dict, List, Tuple, Any

# ==========================================
# 子图 (Section Worker) 配置
# ==========================================

SUBGRAPH_TOPOLOGY = {
    "name": "SectionWorker",
    "description": "单个段落的工作流：搜索 → 写作 → 反思 → 格式化",
    "nodes": ["search", "write", "reflect", "format_output"],
    "edges": [
        ("START", "search"),
        ("search", "write"),
        ("write", "reflect"),
        ("reflect", "format_output"),  # 条件边会覆盖这个
        ("format_output", "END"),
    ],
    "conditional_edges": [
        {
            "source": "reflect",
            "condition_func": "should_continue",
            "branches": {
                "end": "format_output",
                "search": "search",
                "rewrite": "write"
            }
        }
    ]
}

# ==========================================
# 主图 (Main Graph) 配置
# ==========================================

MAIN_GRAPH_TOPOLOGY = {
    "name": "MainGraph",
    "description": "主报告生成流程：生成结构 → 并行段落处理 → 编译",
    "nodes": ["generate_structure", "section_worker", "compile"],
    "edges": [
        ("START", "generate_structure"),
        ("section_worker", "compile"),
        ("compile", "END"),
    ],
    "conditional_edges": [
        {
            "source": "generate_structure",
            "condition_func": "map_sections_to_workers",
            "branches_to": ["section_worker"]
        }
    ]
}

# ==========================================
# 执行配置
# ==========================================

EXECUTION_CONFIG = {
    "recursion_limit": 50,
    "max_iterations_per_section": 3,
    "timeout_per_section": 300,  # 单个段落超时（秒）
    "timeout_total": 600,  # 总超时（秒）
}

# ==========================================
# 节点参数配置
# ==========================================

NODE_PARAMS = {
    "search": {
        "max_results": 5,
        "timeout": 30
    },
    "write": {
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "reflect": {
        "temperature": 0.5,
        "max_tokens": 500
    },
    "structure": {
        "temperature": 0.5,
        "max_tokens": 1000
    }
}
def visualize_topology():
    """可视化图拓扑"""
    print("\n" + "="*60)
    print("📊 子图拓扑")
    print("="*60)
    print(f"名称: {SUBGRAPH_TOPOLOGY['name']}")
    print(f"描述: {SUBGRAPH_TOPOLOGY['description']}")
    print("节点:", " → ".join(SUBGRAPH_TOPOLOGY['nodes']))
    
    print("\n" + "="*60)
    print("📊 主图拓扑")
    print("="*60)
    print(f"名称: {MAIN_GRAPH_TOPOLOGY['name']}")
    print(f"描述: {MAIN_GRAPH_TOPOLOGY['description']}")
    print("节点:", " → ".join(MAIN_GRAPH_TOPOLOGY['nodes']))
    
    print("\n" + "="*60)
    print("⚙️ 执行配置")
    print("="*60)
    for key, value in EXECUTION_CONFIG.items():
        print(f"  {key}: {value}")