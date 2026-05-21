# 主题分层研究规范

> 本文档是 `workflow.md` Step 0.3 的详细参考。流程概要见 [workflow.md](../workflow.md)。

## 研究范围（4 层之前必须先定）

```markdown
## 研究范围
- **覆盖**: 本次研究覆盖什么（如：PNP 联邦总览级别）
- **不覆盖**: 明确排除什么（如：各省具体 stream 细节）
- **深度**: 概览 / 对比 / 单省深入
- **数据源**: 用哪些 ChromaDB collection（如 ca_federal, ca_fcac）+ 官网
```

> ⚠️ 范围不清就开始研究 = 越写越发散 = 写完自己都凌乱。
> 像 PNP 这种各省规则不同的主题，必须先界定是"联邦总览"还是"单省深入"。

---

## 5 步逻辑链骨架

> ⚠️ **研究结构必须直接映射到 storyline 逻辑链。**
> 围绕「数据 → 问题 → 原因 → 风险 → 方案」组织，不要先收集百科再提炼。

```
S1 数据采集 (按实体拆分，每条瞄准 1 个数据点)
  ├── S1.1 核心数字  → 用产品/项目真名 + 目标数据点
  │     ❌ "EE latest data numbers 2025 2026 statistics"（关键词堆砌）
  │     ✅ "Express Entry CEC invitation rounds 2026 minimum CRS score"
  ├── S1.2 分布/构成 → 指定要查的维度
  │     ❌ "{X} breakdown distribution by category type"
  │     ✅ "Express Entry Category-Based Selection healthcare STEM French 2026"
  ├── S1.3 历史对比  → 指定时间范围 + 对比维度
  │     ✅ "Express Entry CRS cutoff trend 2020 2021 2022 2023 2024 general rounds"
  └── S1.4 池子/竞争 → 用具体术语
        ✅ "Express Entry pool candidates profile CRS score distribution"

S2 问题发现 (Agent 独立推导，不走 RAG)
  ├── S2.1 数据里有什么反直觉/不对劲的？
  ├── S2.2 哪些数字看着"好"但实际藏着坑？
  └── S2.3 不同人群面对这些数据处境有何不同？

S3 原因分析 (2-3 条 RAG 查询)
  ├── S3.1 机制  → 用官方术语描述机制
  │     ✅ "Provincial Nominee Program two streams paper-based Express Entry enhanced"
  ├── S3.2 政策  → 引用具体政策名/日期
  │     ✅ "IRCC LMIA points removal March 2025 CRS calculation change"
  └── S3.3 因果  → 指向具体因果关系
        ✅ "Express Entry general rounds cancelled 2025 Category-Based Selection only"

S4 风险预测 (Agent 推导，可用 RAG 辅助)
  ├── S4.1 当前趋势持续会怎样？
  ├── S4.2 哪些因素可能导致情况变好/变差？
  └── S4.3 最坏情况是什么？

S5 方案建议 (1-2 条 RAG 查询)
  ├── S5.1 方案  → 用具体替代路径名
  │     ✅ "Provincial Nominee Program Ontario HCP stream international student eligible"
  └── S5.2 时机  → 用具体窗口/截止日
        ✅ "Ontario HCP stream intake 2026 application deadline processing time"
```

> **S2 和 S4 是 Agent 必须独立完成的推导。**
> 写不出 S2（发现问题），说明数据理解不够，必须回头补研究。

---

## 研究流程

```
Step 1: Agent 写 {slug}-research.md 骨架（含 5 步逻辑链 + RAG 查询表）
Step 2: cite_rag.py --queries {slug}-research.md --collection <collections> → sources.json（脚本跑，零 token）
Step 3: Agent 读 sources.json 片段，回填 S1/S3/S5 数据
Step 4: Agent 独立完成 S2（问题发现）和 S4（风险预测）的推导
```

> 产出只有 2 个文件: `{slug}-research.md` + `sources.json`

---

## 研究规范

1. **每个主题必须有来源** — `.md` 路径 + 完整官网 URL（不简写）
2. **引用原文** — 关键数据必须附官网英文原文 blockquote
3. **标注缺失** — 没有 RAG 数据的主题标注 `❌ 未入库` + 建议入库命令
4. **S2/S4 必须有推导过程** — 不能只写结论，必须写出"因为A所以B"的推理链

---

## 防跑偏铁律（RAG 查询纪律）

> ⚠️ **查询跑偏 = 视频跑偏 = 完播率归零。**

1. **主题锁定** — 每条查询必须能直接回答视频 H1 标题的问题。
   H1 = "留学一年花多少钱" → 每条查询必须关于「花了多少」「费用是多少」「金额是多少」
   如果一条查询的答案不包含具体金额/费用，就是跑偏，**立即删掉**。
2. **反向检验** — 写完查询表后，逐条问自己：「这条查询的结果会出现在视频里吗？」
   如果答案是「不会」或「可能作为背景」，直接删。
3. **每主题 2-3 条** — 同一个费用主题从不同角度查（金额 / 构成 / 对比），提高命中率。
4. **个人数据单独标注** — 来自个人经历/截图的数据标注 📌，不浪费 RAG 查询。
5. **禁止关联发散** — 严禁「既然查了学签费用，顺便查一下申请流程/打工权限/入境文件」。
   这些是**其他视频**的主题，不是本视频的。

---

## 查询工程铁律（检索质量）

> ⚠️ **查询不精准 = 检索噪声 = 数据回填全靠猜 = 准确率归零。**
> RAG 检索不消耗 token，查询数量不受限，但每条查询的**精准度**决定数据质量。

### 6 条规则

| # | 规则 | 说明 |
|---|------|------|
| Q1 | **用产品/项目真名** | BM25 靠精确词匹配，用官网上的产品名命中率翻倍 |
| Q2 | **每条查询瞄准 1 个数据点** | 「免费期多久」和「月费多少」是两条查询，不要塞一条里 |
| Q3 | **同主题查询用不同维度词拉开差异** | 同一银行：新移民计划 / 资格窗口 / 学生条件 / 月费金额 / 低成本档 / 转账费 — 6 个维度 = 6 条查询 |
| Q4 | **零重复词** | 同一条查询中不出现语义重复词（如 newcomer + new immigrant, banking + bank） |
| Q5 | **按实体拆分** | 5 家银行 = 5 组查询，每组内部按维度拆。不要写 1 条查询覆盖所有银行 |
| Q6 | **数量不限，精度优先** | RAG 查询不花 token，宁可多查也不要因为省查询数而写模糊查询 |

### 反模式对照表

| ❌ 错误写法 | 问题 | ✅ 正确写法 |
|------------|------|------------|
| `"newcomer banking account open bank Canada new immigrant"` | 关键词堆砌：newcomer/new immigrant 重复，banking/bank 重复，BM25 TF-IDF 被稀释 | `"no-cost account eligible newcomer first year Canada bank"` |
| `"newcomer new to Canada program banking account offer BMO"` | 没用产品名：BMO 官网写的是 "NewStart Program"，这条查询匹配不上 | `"BMO NewStart Program newcomer chequing fee waiver two years"` |
| `"chequing account monthly fee plan waive minimum balance RBC"` (5 家银行只换名字) | 同质化：5 条查询只换银行名，返回 chunk 高度重叠 | 每家按维度拆：月费金额 / 免月费余额 / 低成本档 / 学生条件 — 不同查询打不同页面 |
| `"big five banks Canada RBC TD BMO Scotiabank CIBC"` | 太泛：所有页面都能匹配，等于没查 | 删掉，改为按银行逐个查具体产品 |
| `"e-Transfer Interac fee ATM withdrawal non-BMO transaction charge BMO"` | 一条塞了 3 个数据点（e-Transfer + ATM + 交易费） | 拆成：`"BMO Interac e-Transfer send receive fee included"` + `"BMO non-BMO ATM withdrawal charge"` |

### 分组规则

> 查询表按**实体**分组（每家银行一组），不按功能维度分组。
> 每组内按数据点维度排列，保证同组查询之间有明确差异。

```
❌ 旧分组（按功能）:           ✅ 新分组（按实体）:
 D. 五大行新移民产品             C. BMO（新移民+学生+费用）
   10. BMO 新移民                  8. BMO NewStart 免费期
   11. RBC 新移民                  9. BMO NewStart 资格窗口
   12. TD 新移民                   10. BMO 学生账户
 E. 五大行费用                     11. BMO 月费条件
   15. BMO 费用                    12. BMO 低成本档
   16. RBC 费用                    13. BMO 转账费
 F. 五大行转账费                 D. CIBC（新移民+学生+费用）
   21. BMO 转账                    ...
   22. RBC 转账
```

---

## 从研究到子弹

研究完成后，Agent 从 5 步中提取"子弹"（短视频选题）：

- **1 个主题 = 1 颗子弹 = 1 条视频**
- 每颗子弹必须有完整的 S1→S2→S3→S4→S5 链条
- 链条断了的主题不出视频，回 research 补研究

---

## 执行 RAG 检索

> research.md 里的查询表直接作为 cite_rag.py 的输入，不需要单独的 queries.md。

```powershell
# // turbo
# cwd: textbook-rag/
# 单 collection（移民政策类）
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --collection ca_federal `
  --output data/short-videos/{slug}/sources.json

# 多 collection（银行/金融类需要 ca_fcac）
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --collection ca_federal ca_fcac `
  --output data/short-videos/{slug}/sources.json
```

### Collection 选择指南

| 主题类别 | Collection(s) |
|---------|---------------|
| 移民/签证/EE/PNP | `ca_federal` |
| 银行/信用卡/金融（监管层） | `ca_federal ca_fcac` |
| 银行/信用卡/金融（五大行产品） | `ca_federal ca_fcac ca_bank_bmo ca_bank_cibc ca_bank_rbc ca_bank_scotiabank ca_bank_td` |
| 税务/TFSA/GIC 税率 | `ca_cra` |
| 存款保险/CDIC | `ca_cdic` |
| 省移民项目 | `ca_federal ca_ontario` / `ca_bc` 等 |

> ⚠️ ChromaDB 数据全部英文（来自 canada.ca），中文查询命中率极低。**必须用英文查询。**

---

## 数据不足时入库

如果 RAG 检索结果不足以覆盖某个主题，**必须先入库再继续**：

```powershell
# 单页入库
uv run python scripts/ingest/ingest_urls.py `
  --category federal-ircc --collection ca_federal --force `
  "https://www.canada.ca/en/..."

# EE 轮次 JSON 数据入库
uv run python scripts/ingest/ingest_urls.py `
  --ee-rounds --category federal-ircc --collection ca_federal --force
```

入库后重新执行 RAG 检索，直到 12 个主题全部有数据。
