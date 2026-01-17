

🚀 DeepSearchAgent - 智能投研搜索智能体

DeepSearchAgent 是一个基于多智能体架构（Multi-Agent）的自动化投研报告生成系统。它结合了 **LightRAG** 的深度检索能力和 **Qwen (通义千问)** 的大模型推理能力，能够自动搜集信息、整理数据并生成专业的金融研报。

## ✨ 核心特性

- **🔍 混合检索增强 (LightRAG)**: 集成了 LightRAG 框架，支持对本地文档和知识图谱的深度检索，拒绝“幻觉”。
- **🧠 强大的 LLM 支持**: 内置 Qwen (通义千问) 模型适配，支持高并发推理。
- **🛡️ 企业级数据安全**: 敏感配置（如 API Key）与代码完全分离，支持 `.env` 环境变量管理。
- **📊 自动化研报**: 一键生成结构化的金融研究报告（支持 Markdown/PDF）。
 🛠️ 安装指南

1. 克隆项目
bash
git clone git@github.com:gehengxuan/finagent.git
cd finagent
2. 安装依赖
建议使用 Conda 创建独立环境：
Bash
conda create -n deepsearch python=3.10
conda activate deepsearch
pip install -r requirements.txt

3. 配置密钥
注意： 请不要直接修改 config.py。
复制示例配置文件并填入你的 Key：
Bash
cp config.py.example config.py
编辑  config.py  或创建  .env  文件：
Python
TAVILY_API_KEY = "你的Tavily_Key"
LIGHTRAG_API_KEY = "你的LightRAG_Key"

🚀 快速开始
运行基础 Demo，生成一份关于“宁德时代”的研报：
Bash
python examples/basic_usage.py
📂 项目结构
 src/agent.p  y : 智能体核心逻辑
 src/tools/l  ightrag_search.py : LightRAG 搜索客户端
 src/llms/qw  en_llm.py : Qwen 模型适配器
 reports/ :生成的研报存放位置
📝 版本历史
v0.2.0: 集成 LightRAG 混合检索与 Qwen 模型支持；优化配置安全。
v0.1.0: 初始版本，支持 Tavily 搜索。
📄 License
MIT License