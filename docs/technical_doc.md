# 项目技术说明文档

## 1. 项目概述

DeepSearchAgent 是一个基于 LangGraph 多智能体工作流的自动化投研报告生成系统。系统能够根据用户输入的研报主题，自动完成信息搜集、结构规划、章节撰写、自我反思修改和全文编译，最终输出带引用溯源的 Markdown 格式深度研报。

本项目在开源 Agent 框架基础上进行了**金融垂直领域的深度定制**，核心改造工作包括：金融专用 Prompt 体系重构、Qwen 模型适配、混合检索系统构建、以及轻量化自动评测框架。

---

## 2. 系统架构

### 2.1 整体流水线

```
用户输入 query
    │
    ▼
┌──────────────────┐
│ generate_structure│   ← 根据 query + Prompt 模板生成六章大纲
│  (结构规划节点)    │     输出: sections[]
└────────┬─────────┘
         │  Send (并行分发)
         ▼
┌──────────────────────────────────────┐
│         section_worker (子图)         │  ← 每个章节独立并行
│  ┌─────────┐  ┌───────┐  ┌────────┐ │
│  │ search  │→│ write  │→│reflect │ │
│  └────┬────┘  └───────┘  └───┬────┘ │
│       │                      │       │
│       └──────────────────────┘       │
│       (不达标时循环: 补搜/重写)        │
└────────────────┬─────────────────────┘
                 │  完成所有章节
                 ▼
         ┌──────────────┐
         │   compile     │  ← 合并章节、全局引用重编号、去重
         │  (编译节点)    │     输出: final_report (Markdown)
         └──────────────┘
```

### 2.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| Agent 入口 | `src/agent.py` | `StructuredReportAgent` 类，提供 `generate_report()` 同步接口和 `run()` 异步接口 |
| 图构建器 | `src/graph/builder.py` | `GraphFactory` / `SubGraphBuilder` / `MainGraphBuilder`，负责组装 LangGraph 状态图 |
| 图配置 | `src/graph/graph_config.py` | 子图和主图的拓扑定义、执行参数（如 `recursion_limit`） |
| 结构规划节点 | `src/nodes/structure_node.py` | 调用 LLM 生成报告大纲，支持个股/行业双模式 |
| 搜索节点 | `src/nodes/search_node.py` | 按配置自动路由搜索后端（本地文件 / Tavily / LightRAG），结果去重 |
| 写作节点 | `src/nodes/writer_node.py` | 根据搜索结果生成章节内容，首稿和重写两种模式 |
| 反思节点 | `src/nodes/reflector_node.py` | 对草稿做交叉审查，输出结构化错误清单，决定通过/补搜/重写 |
| 编译节点 | `src/graph/builder.py` 内 | 合并所有章节，构建全局引用映射，去重连续重复引用 |
| 状态定义 | `src/state/state.py` | `SectionState`（子图状态）和 `AgentState`（主图状态） |

---

## 3. Prompt 工程体系

### 3.1 设计原则

Prompt 体系的设计目标是**让通用 LLM 输出符合专业投研研报标准的结构化内容**。

核心设计决策：
1. **强制结构化输出**：大纲生成阶段要求 LLM 输出 JSON schema 格式，确保下游节点可以程序化解析。
2. **金融术语对齐**：Prompt 中显式要求使用 ROE、CAGR、PE/PB Band 等标准术语，避免口语化表述。
3. **角色约束**：使用"你是一位资深买方分析师"等角色设定，限制 LLM 的输出风格。
4. **引用强制**：写作 Prompt 中要求每一条关键结论都必须附带 `[[N]]` 引用标记。

### 3.2 Prompt 模块组织

| 文件 | 用途 |
|------|------|
| `src/prompts/prompts.py` | 公共 Prompt（搜索意图生成、写作、反思、输出 schema） |
| `src/prompts/company_prompt.py` | 个股深度模式专用（投资逻辑、财务分析、调研问题、风险提示指令） |
| `src/prompts/industry_prompt.py` | 行业一页纸模式专用（市场空间、竞争格局、产业链分析指令） |

### 3.3 报告模式

| 模式 | 配置值 | 典型章节 |
|------|--------|----------|
| 个股深度 | `report_type="company"` | 核心结论与预期差 → 公司近况 → 投资逻辑 → 财务分析 → 调研问题 → 风险提示 |
| 行业一页纸 | `report_type="industry"` | 市场空间 → 竞争格局 → 产业链分析 |

---

## 4. 搜索系统

### 4.1 多后端路由

搜索节点 (`search_node.py`) 根据配置自动选择搜索后端，同时启用时结果合并：

```
config.local_files 有值？ ──yes──→ LocalFileSearch (本地文件分块检索)
         │
         no
         │
config.enable_online_search=True？ ──yes──→ TavilySearch (网络实时搜索)
         │
         no
         │
         └──→ LightRAGSearch (知识图谱检索，兜底)
```

### 4.2 搜索工具对比

| 工具 | 文件 | 数据源 | 适用场景 |
|------|------|--------|----------|
| `LocalFileSearch` | `src/tools/local_file_search.py` | 本地 TXT/PDF 文件按段落分块，关键词匹配排序 | Benchmark 评测（使用 10-K 年报） |
| `TavilySearch` | `src/tools/tavily_search.py` | Tavily API 实时网络搜索 | 需要最新信息的研报生成 |
| `LightRAGSearch` | `src/tools/lightrag_search.py` | 自建 LightRAG 图谱服务 | 企业内部知识库检索 |

### 4.3 搜索意图生成

首次搜索时，搜索节点会先调用 LLM 根据章节定义生成搜索查询词（而非直接用章节标题搜索），提升检索相关性。反思补搜时则直接使用 reflector 输出的建议查询词。

---

## 5. 反思机制 (Self-Reflection)

反思节点是本项目区别于简单 RAG 生成的核心设计。

### 5.1 工作流程

1. 接收当前章节草稿 + 搜索素材。
2. 调用 LLM 按结构化 schema 输出审查意见。
3. 根据审查结果决定下一步动作：

| 输出 | 条件 | 动作 |
|------|------|------|
| `is_satisfactory=True` | 无错误或仅 minor 级 | → `format_output` → 完成 |
| `search_queries` 不为空 | 需要补充信息 | → `search` → 补搜 |
| `errors` 非空且无需补搜 | 需要修改文本 | → `write` → 重写 |

### 5.2 错误分类体系

反思 Prompt 定义了以下错误类型：

| 类型 | 说明 |
|------|------|
| `data_missing` | 缺少关键数据支撑 |
| `format_violation` | 格式不符合要求（如缺少表格） |
| `logic_gap` | 逻辑推理存在跳跃或矛盾 |
| `instruction_ignored` | 未按写作指令执行 |
| `hallucination_risk` | 可能存在无中生有 |
| `citation_missing` | 关键结论缺少引用标记 |
| `data_underuse` | 搜索素材未被充分利用 |

每个错误附带严重等级 (`critical` / `major` / `minor`)，只有 critical 或 major 级错误会触发重写。

### 5.3 循环控制

通过 `max_reflections` 配置（默认 2）限制最大反思次数，防止死循环。

---

## 6. LLM 适配层

### 6.1 多模型支持

| Provider | 适配器 | 配置字段 |
|----------|--------|----------|
| Qwen (通义千问) | `src/llms/qwen_llm.py` | `DASHSCOPE_API_KEY` + `QWEN_MODEL` |
| DeepSeek | `src/llms/deepseek.py` | `DEEPSEEK_API_KEY` + `DEEPSEEK_MODEL` |
| OpenAI | `src/llms/openai_llm.py` | `OPENAI_API_KEY` + `OPENAI_MODEL` |

所有适配器继承 `BaseLLM`，统一提供 `invoke(messages, response_format)` 接口。

### 6.2 JSON 输出

结构规划和反思节点要求 LLM 返回 JSON 格式。通过 `response_format={"type": "json_object"}` 参数强制 LLM 输出可解析的 JSON，下游节点直接 `json.loads` 使用。

---

## 7. 配置系统

### 7.1 配置加载

配置管理模块 (`src/utils/config.py`) 支持三种配置来源：

1. **Python 文件** (`config.py`)：通过 `importlib` 动态导入。
2. **环境变量文件** (`.env`)：按 `KEY=VALUE` 格式解析。
3. **运行时注入**：通过 `Config` dataclass 直接构造并传入 `StructuredReportAgent(config=...)`。

全局采用单例缓存模式，避免重复加载。`set_config()` 和 `clear_config_cache()` 允许 benchmark 场景下临时注入不同配置。

### 7.2 关键配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `default_llm_provider` | `"qwen"` | LLM 提供商 |
| `report_type` | `"company"` | 报告模式：`company` / `industry` |
| `enable_online_search` | `False` | 是否启用 Tavily 网络搜索 |
| `local_files` | `[]` | 本地文件路径列表 |
| `max_reflections` | `2` | 最大反思次数 |
| `max_search_results` | `3` | 每次搜索返回结果数 |
| `max_content_length` | `20000` | 搜索内容最大字符数 |

---

## 8. 编译与引用系统

### 8.1 全局引用重编号

各章节并行写作时使用局部引用编号 `[1], [2], ...`。编译节点在合并时：

1. 收集所有章节的搜索结果，按 URL 去重构建全局引用库。
2. 建立局部编号 → 全局编号的映射表。
3. 对每个章节正文中的引用标记执行正则替换。
4. 在文末生成统一的 `### 参考资料 / References` 列表。

### 8.2 连续重复引用去重

编译阶段还会处理 LLM 有时产生的冗余引用模式（如 `[[1]] [[1]] [[2]]` → `[[1]] [[2]]`），通过多轮正则匹配消除连续重复。

---

## 9. 测试体系

项目包含 214 个自动化测试用例，覆盖：

| 测试文件 | 覆盖范围 |
|----------|----------|
| `tests/test_agent.py` | Agent 初始化、配置注入 |
| `tests/test_builder.py` | 图构建逻辑 |
| `tests/test_evaluation_metrics.py` | 评测指标解析和评分计算 |
| `tests/test_graph_config.py` | 图拓扑配置 |
| `tests/test_llm_base.py` | LLM 适配器基类 |
| `tests/test_prompts.py` | Prompt 模板完整性 |
| `tests/test_reflector_node.py` | 反思节点逻辑 |
| `tests/test_state.py` | 状态定义和 reducer |
| `tests/test_text_processing.py` | 文本处理工具函数 |
| `tests/test_writer_node.py` | 写作节点逻辑 |

运行方式：

```bash
python -m pytest -q
```

---

## 10. 项目目录结构

```
DeepSearchAgent/
├── config.py                  # 运行时配置（不入库）
├── config.py.example          # 配置模板
├── requirements.txt           # Python 依赖
├── pytest.ini                 # 测试配置
│
├── src/                       # 核心源码
│   ├── agent.py               # Agent 入口类
│   ├── __init__.py            # 公共导出
│   ├── graph/                 # LangGraph 图构建
│   │   ├── builder.py         # 图工厂 + 子图/主图构建器
│   │   └── graph_config.py    # 图拓扑与执行参数
│   ├── nodes/                 # 图节点实现
│   │   ├── structure_node.py  # 大纲生成
│   │   ├── search_node.py     # 搜索路由
│   │   ├── writer_node.py     # 章节写作
│   │   └── reflector_node.py  # 自我反思
│   ├── llms/                  # LLM 适配层
│   │   ├── base.py            # BaseLLM 抽象类
│   │   ├── qwen_llm.py       # Qwen 适配器
│   │   ├── deepseek.py        # DeepSeek 适配器
│   │   └── openai_llm.py     # OpenAI 适配器
│   ├── tools/                 # 搜索工具
│   │   ├── local_file_search.py  # 本地文件分块检索
│   │   ├── tavily_search.py      # Tavily 网络搜索
│   │   └── lightrag_search.py    # LightRAG 图谱检索
│   ├── prompts/               # Prompt 模板
│   │   ├── prompts.py         # 公共 Prompt
│   │   ├── company_prompt.py  # 个股模式 Prompt
│   │   └── industry_prompt.py # 行业模式 Prompt
│   ├── state/                 # 状态定义
│   │   └── state.py           # SectionState / AgentState
│   └── utils/                 # 工具函数
│       ├── config.py          # 配置管理
│       └── text_processing.py # 文本处理
│
├── evaluation/                # 自动评测框架
│   ├── cases.py               # Benchmark case 定义
│   ├── metrics.py             # 静态评分逻辑
│   └── runner.py              # CLI 评测入口
│
├── benchmark_10k_edgar/       # 评测数据集（8 家公司 10-K 年报）
│
├── reports/                   # 生成的研报输出
│   ├── company_reports/
│   └── industry_reports/
│
├── examples/                  # 使用示例
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   └── streamlit_app.py
│
├── tests/                     # 自动化测试
│
└── docs/                      # 项目文档
    ├── evaluation_design.md   # 评测系统设计说明
    └── technical_doc.md       # 本文档
```

---

## 11. 技术栈

| 组件 | 技术选型 | 版本要求 |
|------|----------|----------|
| 工作流引擎 | LangGraph | ≥ 0.2.0 |
| LLM 消息协议 | LangChain Core | ≥ 0.3.0 |
| 默认 LLM | Qwen (通义千问) | qwen-plus / qwen-max / qwen3-max |
| 网络搜索 | Tavily | tavily-python ≥ 0.5.0 |
| 知识图谱检索 | LightRAG | 自建服务（可选） |
| Web UI | Streamlit | ≥ 1.28.0（可选） |
| 测试框架 | pytest | ≥ 7.0.0 |
| 运行环境 | Python | ≥ 3.10 |
