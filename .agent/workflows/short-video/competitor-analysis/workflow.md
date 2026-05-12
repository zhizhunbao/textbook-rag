---
description: 竞品短视频模式提取工作流 — 发现 → 标注 → 归纳 → 应用
name: competitor-analysis
version: 1.0.0
trigger: /competitor
---

# 竞品短视频模式提取工作流

从跨领域高转化短视频中提炼**结构 × 布局 × 视觉**三维模式，反哺 Remotion 生产流水线。

## 核心理念

> **提取模式，不抄内容。**
> 好的钩子节奏、表格呈现、配色方案是跨领域通用的。
> 不关心视频讲什么，只关心**怎么讲、怎么排、怎么看起来高级**。

### 提取四维度

| 维度 | 提取什么 | 反哺到 |
|------|---------|--------|
| **结构模式** | 钩子类型、slide 数、节奏、CTA | `workflow.md` 生产参数 |
| **布局模式** | 居中/左对齐/分栏、表格比例、留白 | Layout Lab 5 套布局 |
| **视觉风格** | 配色(暗/亮)、字重、装饰元素 | `templates.js` 5 套配色 |
| **字幕风格** | 位置、高亮方式、字号、同步效果 | `SubtitleBar.tsx` 渲染参数 |

### 注意事项

- **幸存者偏差**: 只看到成功视频，同模式的失败视频看不到 → 模式要用 A/B 测试验证
- **样本量**: 单轮至少分析 20-30 个视频，10 个以下不可靠
- **平台差异**: YouTube 的模式不一定适用于视频号 → 标注时记录平台

---

## Step 0: 搜索关键词规划

Agent 收到分析请求后，确认搜索方向：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 平台 | YouTube | 数据最公开、yt-dlp 最稳定 |
| 数量 | 30 个候选 → 下载 top 20 | 足够样本量 |
| 时长筛选 | 30-120 秒 | 匹配短视频格式 |
| 语言 | 中文 + 英文 | 双语取样避免文化偏差 |

### 搜索关键词库（按提取目标）

> ⚠️ 目标是提取**风格/布局/结构模式**，不限于任何内容领域。

| 提取目标 | 搜索关键词 | 为什么 |
|---------|-----------|--------|
| 视觉风格 | `infographic shorts`, `数据可视化 短视频` | 找视觉做得最好的 |
| 布局参考 | `知识科普 热门`, `science explainer shorts` | 找信息编排最清晰的 |
| 主题配色 | `dark mode design`, `neon UI animation` | 找配色和装饰灵感 |
| 节奏/钩子 | `viral shorts hook`, `3秒钩子 技巧` | 找开场最抓人的 |
| 表格呈现 | `comparison video`, `对比测评 短视频` | 找数据展示最有效的 |
| CTA 设计 | `engagement shorts`, `互动引导` | 找互动转化最好的 |

### 完成条件

- 搜索关键词列表确认（至少覆盖 3 个提取目标）
- 平台和数量参数确认

---

## Step 1: 自动发现 + 筛选

**执行脚本**: `discover.py`

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/competitor-analysis/scripts/discover.py \
  --keyword "infographic shorts" \
  --platform youtube \
  --limit 30 \
  --min-likes 500 \
  --duration 30-120 \
  --output data/competitor-analysis/{round}/
```

### 脚本功能

1. 按关键词搜索视频列表（yt-dlp `--flat-playlist`）
2. 提取元数据：标题、时长、播放、点赞、评论、发布时间
3. 计算互动率 = (赞+评) / 播放
4. 下载缩略图用于快速预览
5. 按评分排序输出

### 筛选规则

| 指标 | 保留 | 过滤掉 |
|------|------|--------|
| 互动率 | ≥ 2% | < 1% |
| 时长 | 30-120s | 太短或太长 |
| 类型 | 信息/数据/知识 | 直播回放、广告、纯口播 |
| 点赞 | ≥ 500 | 太少（推荐偏差） |

### 产出

```
data/competitor-analysis/{round}/
├── candidates.json        # 候选列表 + 指标
└── thumbnails/            # 封面图
```

### 完成条件

- `candidates.json` 存在，≥ 20 个候选
- 每个候选有 URL + 互动指标
- 按互动率排序

---

## Step 2: 批量下载

**执行脚本**: `batch_download.py`

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/competitor-analysis/scripts/batch_download.py \
  --candidates data/competitor-analysis/{round}/candidates.json \
  --top 20 \
  --output data/competitor-analysis/{round}/videos/
```

### 产出

```
data/competitor-analysis/{round}/videos/
├── 001_video-slug.mp4
├── 002_video-slug.mp4
└── ...
```

### 完成条件

- ≥ 20 个视频下载成功
- 文件名含序号便于标注引用

---

## Step 3: 人工标注（Agent 辅助）

> ⚠️ **这一步是人工的。** Agent 负责生成标注模板、记录用户口述、整理结构化数据。
> 人眼 10 分钟能提取的信息，OCR 折腾一天也不一定准。

### 标注流程

```
用户: 打开 001_video-slug.mp4 看一遍
用户: 告诉 Agent 看到了什么
Agent: 结构化记录到 analyses/001.md
```

### 单视频标注模板

Agent 为每个视频生成 `analyses/{num}.md`：

```markdown
## 视频分析: {title}

### 基本信息
- URL: {url}
- 创作者: {creator}
- 平台: {platform}
- 时长: {duration}s
- 播放/赞/评: {views} / {likes} / {comments}
- 互动率: {engagement}%

---

### 🎯 结构模式

#### 钩子 (前 3 秒)
- 类型: [反直觉数据 / 痛点提问 / 损失厌恶 / 身份代入 / 视觉冲击 / 其他]
- 原文/描述: "..."

#### Slide 编排
| # | 时间段 | 类型 | 内容概要 | 停留秒数 |
|---|--------|------|---------|---------|
| 1 | 0-3s | 钩子 | ... | 3s |
| 2 | 3-12s | 论点 | ... | 9s |
| ... | | | | |

#### 节奏
- 总 slide 数: __
- 平均每页停留: __s
- 信息密度: [高/中/低]

#### 互动设计
- CTA 类型: [评论引导 / 关注 / 收藏 / 无]
- CTA 原文: "..."
- 下集预告: [有/无]

---

### 🎨 布局模式

- 文字对齐: [居中 / 左对齐 / 右对齐]
- 表格: [有/无] → 几列 × 几行
- 数字高亮: [有/无] → 颜色/加粗/放大
- 对比结构: [有/无] → A vs B / 表格对比
- 留白比例: [多/中/少]
- 字幕区位置: [底部固定 / 无字幕 / 画面内嵌]
- 最接近我们哪套布局: [neon / frost / ember / ocean / minimal / 新布局]

---

### 🌈 视觉风格

- 整体色调: [深色 / 浅色 / 渐变]
- 主色: {hex 或描述}
- 强调色: {hex 或描述}
- 字体风格: [粗重 / 常规 / 纤细]
- 装饰元素: [边框 / 光效 / 毛玻璃 / 阴影 / 无]
- 最接近我们哪套配色: [neon-pulse / frost-glass / ember-glow / ocean-depth / minimal-ink / 新配色]

---

### 💬 字幕风格

- 位置: [底部独立区 / 画面底部叠加 / 画面中央 / 无字幕]
- 高亮方式: [逐词变色 / 逐句出现 / 卡拉OK滚动 / 无高亮]
- 当前词颜色: {描述，如 金色/白色/主题色}
- 未读词颜色: {描述，如 灰色/半透明}
- 字号: [大(50px+) / 中(36-50px) / 小(<36px)]
- 字体: [粗 / 常规 / 与画面一致]
- 背景: [纯色底条 / 半透明 / 无背景 / 与画面融合]
- 动画: [淡入淡出 / 弹出 / 无]
- 每屏字数: [一句话 / 半句 / 逐词]

---

### 💡 学到什么

- 可复用的模式:
- 我们缺的:
- 避坑:
```

### 完成条件

- ≥ 20 个 `analyses/{num}.md` 存在
- 每个文件三维度（结构/布局/视觉）都已填写
- "学到什么"不为空

---

## Step 4: 模式归纳

**执行者**: Agent 自动归纳

Agent 读取所有 `analyses/*.md`，统计归纳出共性模式。

### 产出 1: `patterns.json`

```json
{
  "round": "2026-05",
  "analyzed_count": 20,
  "platforms": {"youtube": 15, "bilibili": 5},

  "structure": {
    "hook_type_distribution": {
      "反直觉数据": 9, "痛点提问": 5, "视觉冲击": 4, "身份代入": 2
    },
    "best_hook_type": "反直觉数据",
    "avg_slides": 8,
    "avg_duration_sec": 72,
    "avg_time_per_slide_sec": 9,
    "common_sequences": [
      "cover → argument → evidence → argument → evidence → summary → cta",
      "hook → data → data → comparison → takeaway → cta"
    ],
    "cta_has_comment_prompt": 0.85,
    "cta_has_next_episode": 0.65
  },

  "layout": {
    "alignment_distribution": {"center": 12, "left": 6, "split": 2},
    "best_alignment": "center",
    "has_table": 0.75,
    "table_avg_cols": 3,
    "table_avg_rows": 3,
    "has_comparison": 0.55,
    "subtitle_position": "bottom_fixed",
    "closest_layouts": {"neon": 8, "frost": 5, "ember": 3, "ocean": 2, "minimal": 2}
  },

  "visual": {
    "dark_theme_ratio": 0.85,
    "common_accents": ["#00f0ff", "#818cf8", "#f97316"],
    "font_weight_distribution": {"bold": 14, "regular": 4, "thin": 2},
    "has_decorations": 0.70,
    "decoration_types": {"glow": 8, "border": 5, "glass": 4},
    "closest_palettes": {"neon-pulse": 7, "frost-glass": 5, "ember-glow": 3, "ocean-depth": 3, "minimal-ink": 2}
  },

  "subtitle": {
    "position_distribution": {"底部独立区": 12, "画面底部叠加": 5, "无字幕": 3},
    "best_position": "底部独立区",
    "highlight_distribution": {"逐词变色": 10, "逐句出现": 6, "卡拉OK": 2, "无高亮": 2},
    "best_highlight": "逐词变色",
    "active_color": "金色/主题强调色",
    "inactive_color": "灰色/半透明白",
    "avg_font_size": "大(50px+)",
    "has_background": 0.60,
    "background_style": "半透明深色"
  }
}
```

### 产出 2: `insights.md`

人话版洞察 + 行动建议:

```markdown
## 第 N 轮竞品分析洞察

### 📊 关键发现
1. **钩子**: 45% 用反直觉数据开场 → 我们应该优先用这种
2. **节奏**: 最佳模式 = 8 slides × 9s/slide = 72s 总时长
3. **布局**: 60% 居中堆叠 → neon 布局是安全选择
4. **配色**: 85% 暗色主题 → 继续用深色

### 🔧 建议调整 (反哺 workflow.md)
| 参数 | 当前值 | 建议改为 | 依据 |
|------|--------|---------|------|
| slides 数 | 8-12 | 7-9 | 均值 8，超过 10 完播率下降 |
| 每页停留 | 无约束 | ~9s | 竞品均值 |
| 钩子类型 | 随意 | 优先反直觉数据 | 45% 高互动视频用这种 |
| 默认模板 | neon-pulse | neon-pulse | 居中+暗色最主流 |

### ⚠️ 与上一轮对比 (如果非首轮)
- 变化:
- 新趋势:
- 稳定不变:
```

### 完成条件

- `patterns.json` 存在，三维度统计完整
- `insights.md` 存在，含行动建议表
- 每个建议有数据支撑（占比/均值）

---

## Step 5: 模式应用

**执行者**: 人工决策 + Agent 执行

### 5.1 更新 workflow.md 参数

根据 `insights.md` 的建议，修改 `short-video/workflow.md` 中的默认参数。

### 5.2 调整 Remotion 模板

如果发现新的布局/配色模式不在现有 5 套中：
- 在 `templates.js` 新增模板
- 在 Layout Lab 预览确认

### 5.3 验证（最重要）

> **模式是否有效，只有发布后的数据能证明。**

用新模式制作 1 条视频 → 发布 → 72 小时后看数据：

| 指标 | 对比基线 | 有效 | 无效 |
|------|---------|------|------|
| 3s 播放率 | 上一条视频 | ↑ 10%+ | ↓ 或持平 |
| 完播率 | 上一条视频 | ↑ 5%+ | ↓ 或持平 |
| 互动率 | 上一条视频 | ↑ | ↓ |

### 完成条件

- workflow.md 参数已更新（如果有需要修改的）
- 至少 1 条视频用新模式制作并发布
- 发布 72h 后记录数据到 `results.md`

---

## 文件结构

```
data/competitor-analysis/{round}/
├── candidates.json              # Step 1: 候选列表 + 指标
├── thumbnails/                  # Step 1: 封面图
├── videos/                      # Step 2: 下载的视频
│   ├── 001_xxx.mp4
│   └── ...
├── analyses/                    # Step 3: 单视频标注
│   ├── 001.md
│   └── ...
├── patterns.json                # Step 4: 归纳的模式
├── insights.md                  # Step 4: 行动建议
└── results.md                   # Step 5: 验证结果

.agent/workflows/short-video/competitor-analysis/
├── workflow.md                  # 本文件
└── scripts/
    ├── discover.py              # Step 1: 搜索+筛选
    └── batch_download.py        # Step 2: 批量下载
```

---

## 迭代节奏

```
首轮 (建立基线):
  Step 0-4: 3-4 小时 (含 2h 人工看视频)
  Step 5: 持续 1 周验证

后续轮次 (每月/每季):
  只补增量 — 搜新视频 → 标注差异 → 更新 patterns
  重点看: 趋势变化 > 绝对数值
```

> **关键决策点**: 如果首轮验证显示新模式无效（数据没提升），
> 说明要么样本有偏、要么平台差异大，需要换平台重新取样。

---

## 依赖

```toml
# 仅需 yt-dlp，无 ML 模型依赖
[project.optional-dependencies]
competitor = ["yt-dlp>=2024.0"]
```
