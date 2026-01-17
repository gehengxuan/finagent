
# 🚀 DeepSearchAgent - 智能投研搜索智能体

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![RAG](https://img.shields.io/badge/RAG-LightRAG-green)](https://github.com/HKUDS/LightRAG)
[![LLM](https://img.shields.io/badge/Model-Qwen-purple)](https://tongyi.aliyun.com/)

**DeepSearchAgent** 是一个基于多智能体架构（Multi-Agent）的自动化投研报告生成系统。

本项目在开源社区 Agent 框架的基础上进行了**深度的金融垂直领域定制**。通过结合 **LightRAG** 的图谱增强检索能力与 **Qwen (通义千问)** 的强大推理能力，解决了传统 Agent 在金融场景下“专业性不足”和“事实幻觉”的两大痛点，实现了从信息搜集、逻辑推演到研报撰写的全流程自动化。

---

## 🌟 核心贡献与技术创新

本项目不仅仅是简单的框架调用，而是在以下三个核心维度进行了深度的二次开发与优化：

### 1. 📊 金融垂直领域的 Prompt 工程重构
针对通用 Agent 生成内容泛泛而谈的问题，我们重新设计了整套 **Prompt 体系**，使其符合专业买方/卖方研报的写作逻辑：
- **结构化思维链 (CoT)**: 强制 Agent 遵循“宏观环境 -> 行业格局 -> 公司基本面 -> 财务分析 -> 估值与风险”的标准投研框架。
- **专业术语对齐**: 优化了 Prompt 中的指令约束，确保输出包含准确的金融指标（如 ROE, CAGR, PE/PB Band 等），而非通俗口语。
- **反思机制**: 引入 Self-Reflection 节点，专门用于检查研报中的逻辑漏洞和数据缺失，并自动触发补充搜索。

### 2. 🧠 Qwen (通义千问) 模型深度适配
为了获得更好的中文理解能力和更低的推理成本，我们重写了底层 LLM 接口：
- **自定义适配器**: 开发了 `src/llms/qwen_llm.py`，实现了对 Qwen API 的原生支持，替代了默认的 OpenAI 接口。
- **高并发支持**: 针对研报生成中海量 Token 的吞吐需求，优化了上下文管理与请求并发逻辑。
- **长文本处理**: 充分利用 Qwen 模型在长窗口（Context Window）上的优势，支持读取长篇财报而不丢失关键信息。

### 3. 🔍 混合检索增强：本地知识库 + LightRAG
为了解决传统搜索引擎无法覆盖私有数据（如本地 PDF 财报）的问题，构建了混合检索系统：
- **引入 LightRAG**: 集成了最新的基于图神经网络的检索增强生成（GraphRAG）技术。相比传统向量检索，它能更好地理解实体间的复杂关系（如“宁德时代”与“麒麟电池”的技术关联）。
- **本地存储融合**: 实现了 `LightRAGSearch` 工具类，支持对本地存储的非结构化数据（PDF/TXT）进行深度索引。
- **双路召回策略**: 
    - **Tavily**: 负责获取实时新闻、行业动态等广域互联网信息。
    - **LightRAG**: 负责获取本地知识库中的深度事实、财报细节与实体关系，大幅降低幻觉率。

---

## ✨ 核心特性

- **多智能体协作**: 规划师（Planner）、搜集员（Researcher）、分析师（Analyst）与写作员（Writer）各司其职。
- **拒绝幻觉**: 每一条关键结论均强制要求溯源（Citation），链接至具体的财报段落或新闻链接。
- **企业级安全**: 敏感配置（API Keys）与业务代码物理分离，完全基于环境变量管理，防止密钥泄露。
- **多格式输出**: 支持一键生成 Markdown 源码及渲染后的 PDF 报告。

---

## 🛠️ 安装指南

### 1. 克隆项目
```bash
git clone git@github.com:gehengxuan/finagent.git
cd finagent

```

### 2. 环境准备

建议使用 Conda 创建独立的 Python 3.10 环境：

```bash
conda create -n deepsearch python=3.10
conda activate deepsearch
pip install -r requirements.txt

```

### 3. 密钥配置

**⚠️ 安全提示**：请勿直接修改源码中的 `config.py`。

我们提供了配置模板，请复制并重命名：

```bash
cp config.py.example config.py

```

编辑 `config.py` 或在项目根目录创建 `.env` 文件，填入您的密钥：

```python
# 互联网实时搜索
TAVILY_API_KEY = "tvly-xxxxxx"

# LightRAG 知识图谱服务 (如使用自建服务请填写对应 URL/Key)
LIGHTRAG_API_KEY = "your-lightrag-key"
LIGHTRAG_BASE_URL = "http://localhost:8000"

# 大模型服务
DASHSCOPE_API_KEY = "sk-xxxxxx" # 通义千问 Key

```

---

## 🚀 快速开始

生成一份关于 **“宁德时代 (300750)”** 的深度投资价值分析报告：

```bash
python examples/basic_usage.py

```

运行成功后，您将在 `reports/` 目录下看到生成的报告文件。

---

## 📂 项目结构

```text
finagent/
├── src/
│   ├── agent.py               # 智能体核心调度逻辑 (Graph 编排)
│   ├── llms/
│   │   └── qwen_llm.py        # [创新] Qwen 模型适配层
│   ├── tools/
│   │   ├── search.py          # 基础搜索工具接口
│   │   └── lightrag_search.py # [创新] LightRAG 本地图谱检索客户端
│   ├── prompts/               # [创新] 金融垂直领域 Prompt 库
│   └── nodes/                 # 各个功能节点 (Planner, Writer 等)
├── examples/
│   └── basic_usage.py         # 启动脚本 Demo
├── reports/                   # 产出物存放目录
├── config.py.example          # 配置模板 (安全)
├── requirements.txt           # 项目依赖
└── README.md                  # 项目文档

```

## 📝 版本历史

* **v0.2.0 (Current)**
* ✨ **Feature**: 集成 LightRAG，支持基于知识图谱的本地文档检索。
* ✨ **Feature**: 完成 Qwen (通义千问) 模型的全量适配。
* 🔒 **Security**: 重构配置管理模块，实现密钥与代码分离。


* **v0.1.0**
* Initial Release: 搭建基础多智能体框架，支持 Tavily 联网搜索。



## 📄 License

本项目采用 [MIT License](https://www.google.com/search?q=LICENSE) 开源。

---

*Created by Ge Hengxuan, powered by LLM & GraphRAG technology.*

```

```