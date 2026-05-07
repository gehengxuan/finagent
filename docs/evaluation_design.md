# 评测系统设计说明

## 1. 设计背景

本项目参考了两篇金融研报生成评测 benchmark 的研究论文：

- **FinDeepResearch** (arXiv: 2510.13936)：提出 HisRubric（历史可溯评分标准），从**结构严谨性 (Structural Rigor)** 和**信息精确性 (Information Precision)** 两个维度评价金融深度研报。
- **DEER** (arXiv: 2512.17776)：设计了基于固定评分标准 + 专家指导的评价框架，强调**报告级 claim 验证**——对研报中的事实性陈述逐条回溯至源证据。

本项目的评测系统采取"**低成本先行、渐进扩展**"策略：第一版只执行纯静态、不依赖 LLM judge 和人工标注的自动评分，避免引入额外 API 开销，同时确保评测本身可复现且对毕业设计答辩足够可用。

---

## 2. 评测体系总览

评测系统由三个模块组成，位于 `evaluation/` 目录下：

| 文件 | 职责 |
|------|------|
| `cases.py` | 定义 benchmark case（公司名称、查询、10-K 文件路径、预期章节结构） |
| `metrics.py` | 实现静态评分逻辑（结构、引用、claim 三个维度） |
| `runner.py` | CLI 入口，支持生成+评测或仅对已有报告评测 |

---

## 3. 评分维度与计算方式

### 3.1 结构完整性评分 (Structure Score)

评价报告是否遵循了预期的章节结构。

**预期章节**（个股深度研报模式，共 6 章）：

1. 核心结论与预期差
2. 公司近况深度跟踪
3. 核心投资逻辑
4. 财务质量分析
5. 调研问题大纲
6. 风险提示

**子指标**：

| 子指标 | 含义 | 计算方式 |
|--------|------|----------|
| `section_coverage` | 章节覆盖率 | 实际出现的预期章节数 / 预期章节总数 |
| `order_score` | 章节顺序正确性 | 预期章节在报告中的出现顺序是否与定义一致（0 或 1） |
| `financial_table_score` | 财务分析表格 | "4. 财务质量分析" 章节中是否包含 Markdown 表格（0 或 1） |

**结构总分** = 三个子指标的算术平均值。

### 3.2 引用一致性评分 (Citation Score)

评价正文中的引用标记与文末参考资料列表之间的一致性。

**解析方式**：
- 文末参考资料通过 `### 参考资料 / References` 标题分割。
- 正文引用支持 `[[N]]`（双括号）和 `[N]`（单括号）两种格式。
- 参考资料条目通过 `- [N] 标题` 格式解析。

**子指标**：

| 子指标 | 含义 | 计算方式 |
|--------|------|----------|
| `citation_valid_rate` | 引用有效率 | 正文中引用编号在参考资料中有对应条目的比例 |
| `reference_presence_score` | 参考资料存在性 | 是否至少有一条参考资料（0 或 1） |
| `duplicate_penalty_score` | 重复引用惩罚 | 1 − (相邻重复引用数 / 总引用数)，越接近 1 越好 |

**引用总分** = 三个子指标的算术平均值。

### 3.3 数据引证评分 (Claim Score)

评价含数字的事实性陈述是否附带了引用标记。

**识别规则**：
- 扫描正文所有行（排除标题行、表格行、分隔符行）。
- 一行中含有至少一个数字字符的，认定为"数值型 claim"。
- 检查该行是否包含 `[[N]]` 或 `[N]` 格式的引用。

**数据引证分** = 带引用的数值型 claim 行数 / 数值型 claim 总行数。

### 3.4 综合评分 (Overall Score)

$$\text{Overall} = 0.5 \times \text{Structure} + 0.3 \times \text{Citation} + 0.2 \times \text{Claim}$$

权重设计理由：
- **结构 (0.5)**：对投研研报来说，章节完整性是最基本的质量门槛。
- **引用 (0.3)**：信息可溯源是金融报告区别于一般 AI 生成文本的核心要求。
- **数据引证 (0.2)**：更细粒度的事实溯源检查，覆盖含数字的 claim。

---

## 4. Benchmark Cases

当前版本内置 8 个公司级 benchmark case，均对应 `benchmark_10k_edgar/` 目录下的美股 10-K 年报文本：

| Case ID | 公司 | Ticker | 10-K 文件 |
|---------|------|--------|-----------|
| apple | Apple | AAPL | Apple_10K_2025-10-31.txt |
| microsoft | Microsoft | MSFT | Microsoft_10K_2025-07-30.txt |
| amazon | Amazon | AMZN | Amazon_10K_2026-02-06.txt |
| alphabet | Alphabet | GOOGL | Google_10K_2026-02-05.txt |
| meta | Meta | META | Meta_10K_2026-01-29.txt |
| nvidia | NVIDIA | NVDA | Nvidia_10K_2026-02-25.txt |
| tesla | Tesla | TSLA | Tesla_10K_2026-01-29.txt |
| jpmorgan | JPMorgan Chase | JPM | JPMorgan_10K_2026-02-13.txt |

每个 case 定义了：
- `query`：提交给 Agent 的研报生成指令。
- `local_files`：绑定的本地 10-K 文件路径（runner 会自动注入到 config 中）。
- `expected_sections`：评测时使用的预期章节标题。

---

## 5. 使用方式

### 5.1 对已有报告做静态评测

```bash
python -m evaluation.runner --evaluate-report reports/company_reports/report_xxx.md
```

此模式不需要 LLM API Key、不需要搜索服务，纯本地解析。

### 5.2 运行 benchmark case（生成 + 评测）

```bash
# 列出所有可用 case
python -m evaluation.runner --list-cases

# 运行单个 case
python -m evaluation.runner --case microsoft --output-dir evaluation_outputs

# 运行所有 case
python -m evaluation.runner --all-cases --output-dir evaluation_outputs
```

### 5.3 输出文件

每个 case 运行后在输出目录中生成：

```
evaluation_outputs/
├── microsoft/
│   ├── config_snapshot.json   # 运行时的完整配置快照
│   ├── report.md              # 生成的研报
│   └── evaluation.json        # 评测结果（含各维度得分和详细诊断信息）
└── summary.json               # 批量运行时的汇总
```

---

## 6. 评分示例

以下是对已有 6 份公司研报的实际评测结果：

| 报告文件 | Overall | Structure | Citation | Claim |
|----------|---------|-----------|----------|-------|
| report_1772898725 | 0.9600 | 1.0000 | 1.0000 | 0.8000 |
| report_1769929873 | 0.9176 | 1.0000 | 1.0000 | 0.5882 |
| report_1769931082 | 0.9091 | 1.0000 | 1.0000 | 0.5455 |
| report_1769344304 | 0.8914 | 1.0000 | 0.9969 | 0.4615 |
| report_1769933164 | 0.8900 | 1.0000 | 1.0000 | 0.4500 |
| report_1769343706 | 0.7538 | 1.0000 | 0.3333 | 0.7692 |

**分析**：
- 结构分几乎满分：说明 Prompt 工程在控制章节结构方面效果显著。
- Claim 分差异最大（0.45–0.80）：反映了不同运行中 Agent 对"数字必须引用"这一规则的遵守程度不一致，是后续优化的重点方向。
- 引用分一般很高，但 report_1769343706 出现了低分（0.33），排查发现是正文引用编号与参考资料列表不匹配（孤儿引用）。

---

## 7. 局限性与后续扩展

| 当前局限 | 已规划的扩展方向 |
|----------|------------------|
| 仅做静态文本解析，不验证引用内容与源文档的语义一致性 | 参考 DEER 论文，加入 claim→source 的文本匹配验证 |
| 不依赖 LLM judge，无法评估行文质量和分析深度 | 后续可引入 LLM-as-a-judge 对分析深度和专业性打分 |
| claim 粒度是行级别，可能遗漏表格内的数字 claim | 扩展到表格单元格级别的 claim 检测 |
| 仅支持 company 模式的六章结构 | 扩展支持 industry 模式的行业一页纸结构 |
| 没有基线对照（如弱 prompt / 无反思的消融实验） | 支持同一 benchmark case 的消融实验和结果对比 |
