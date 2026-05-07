# DeepSearchAgent — 基于多智能体工作流的自动化投研报告生成系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Workflow-LangGraph-orange)](https://github.com/langchain-ai/langgraph)
[![LLM](https://img.shields.io/badge/LLM-Qwen-purple)](https://tongyi.aliyun.com/)

## 项目简介

DeepSearchAgent 是一个面向金融投研场景的自动化研报生成系统。系统基于 **LangGraph** 构建多智能体工作流，通过 **结构规划 → 信息检索 → 章节写作 → 自我反思 → 全文编译** 的完整流水线，自动生成带引用溯源的深度研究报告。

核心改造工作：
- **金融专用 Prompt 体系**：强制 Agent 遵循专业投研研报结构（核心结论、投资逻辑、财务分析、风险提示等），使用 ROE/CAGR/PE 等标准术语。
- **Qwen 模型深度适配**：自定义 LLM 适配器，支持 Qwen/DeepSeek/OpenAI 多模型切换。
- **混合检索系统**：支持本地文件检索、Tavily 网络搜索、LightRAG 图谱检索，按配置自动路由和合并。
- **自我反思机制**：反思节点对草稿做结构化审查，自动触发补搜或重写，提升研报质量。
- **轻量化自动评测**：内置 benchmark 框架，支持对生成研报进行结构、引用、数据引证三维度自动评分。

---

## 快速开始

### 1. 环境准备

```bash
conda create -n deepsearch python=3.10
conda activate deepsearch
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.py.example config.py
```

编辑 `config.py`，填入 API 密钥：

```python
DASHSCOPE_API_KEY = "sk-xxxxxx"        # Qwen (必填)
tavily_api_key = "tvly-xxxxxx"          # Tavily 网络搜索 (可选)
DEFAULT_LLM_PROVIDER = "qwen"           # 可选: qwen / deepseek / openai
ENABLE_ONLINE_SEARCH = False            # 是否启用网络搜索
TARGET_FILES = []                       # 本地文件路径列表
REPORT_TYPE = "company"                 # company (个股深度) / industry (行业一页纸)
```

### 3. 生成研报

```bash
python examples/basic_usage.py
```

或以代码方式调用：

```python
from src import Config, StructuredReportAgent

agent = StructuredReportAgent()
report = agent.generate_report("分析宁德时代在新能源汽车产业链中的竞争优势")
```

支持运行时注入配置（不修改 config.py）：

```python
config = Config(
    default_llm_provider="qwen",
    dashscope_api_key="your_key",
    report_type="company",
    local_files=["/path/to/Apple_10K.txt"],
    enable_online_search=True,
    tavily_api_key="tvly-xxx",
    output_dir="my_reports",
)
agent = StructuredReportAgent(config=config)
report = agent.generate_report("分析苹果公司的竞争优势与财务质量")
```

---

## 系统架构

```
query → 结构规划 → [并行] 搜索→写作→反思(循环) → 编译 → Markdown 研报
```

| 节点 | 职责 |
|------|------|
| `generate_structure` | 根据 query + Prompt 模板生成六章大纲 |
| `search` | 按配置路由搜索后端，获取参考素材 |
| `write` | 基于搜索结果撰写章节（首稿 / 重写） |
| `reflect` | 交叉审查草稿，输出结构化错误清单 |
| `compile` | 合并章节，全局引用重编号，输出最终报告 |

详细技术文档见 [docs/technical_doc.md](docs/technical_doc.md)。

---

## 自动评测

### 评测已有报告

```bash
python -m evaluation.runner --evaluate-report reports/company_reports/report_xxx.md
```

### Benchmark 评测

```bash
# 列出所有 case (8 家美股公司, 基于 10-K 年报)
python -m evaluation.runner --list-cases

# 运行单个 case
python -m evaluation.runner --case microsoft --output-dir evaluation_outputs

# 运行所有 case
python -m evaluation.runner --all-cases --output-dir evaluation_outputs
```

### 评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| Structure | 0.5 | 章节覆盖率 + 顺序 + 财务表格 |
| Citation | 0.3 | 引用有效率 + 参考资料存在性 + 去重质量 |
| Claim | 0.2 | 含数字的事实性陈述带引用的比例 |

详细评测设计见 [docs/evaluation_design.md](docs/evaluation_design.md)。

---

## 项目结构

```
DeepSearchAgent/
├── src/                       # 核心源码
│   ├── agent.py               # Agent 入口
│   ├── graph/                 # LangGraph 图构建
│   ├── nodes/                 # 图节点 (搜索/写作/反思/结构)
│   ├── llms/                  # LLM 适配器 (Qwen/DeepSeek/OpenAI)
│   ├── tools/                 # 搜索工具 (本地文件/Tavily/LightRAG)
│   ├── prompts/               # Prompt 模板 (个股/行业)
│   ├── state/                 # 状态定义
│   └── utils/                 # 配置管理 + 文本处理
├── evaluation/                # 自动评测框架
├── benchmark_10k_edgar/       # 10-K 年报评测数据集
├── reports/                   # 生成的研报
├── examples/                  # 使用示例
├── tests/                     # 214 个自动化测试
└── docs/                      # 技术文档 + 评测文档
```

---

## 测试

```bash
python -m pytest -q
```

---

## License

[MIT License](LICENSE)
