---
description: 短视频生产工作流 v6 — Marp + Qwen3-TTS
name: short-video
version: 6.0.0
trigger: /short-video
---

# 短视频生产工作流 v6

从 RAG 知识库一键生成微信视频号竖屏短视频。

**架构**: Logic-First + Marp slides + Qwen3-TTS 声音克隆

```
定题 → 故事线 (Skill) → RAG引用 (Script) → AI 设计 slides.md
  → 提取口播脚本 script.txt → Marp 渲染 PNG (Script)
  → TTS (Script) → 视频组装 (Script)
```

**核心特点**:
- **视觉层**: Marp 幻灯片（纯 .md，AI 自由设计样式/布局/配色）
- **TTS**: Qwen3-TTS 声音克隆（降级: Edge TTS）
- **字幕**: 解耦架构 — 底部独立字幕条，不遮挡幻灯片内容

---

## Step 0: 定题

Agent 收到主题后，确认参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 画面比例 | 16:9 landscape | 横屏视频号 |
| 时长 | 30-60s | 目标时长 |
| 受众 | 华人移民/留学 | 内容定位 |
| TTS | Qwen3-TTS 声音克隆 | 降级: Edge TTS |

---

## Step 1: 叙事线设计 → `storyline.md`

**触发 Skill**: `video-storyline`

Agent 基于主题和自身知识构建叙事逻辑:
1. 定义核心问题（视频要回答什么）
2. 构建逻辑节点链（钩子 → 解释 → 洞察 → 行动 → 收尾）
3. 在每个数据断言处标注 `[需要引用: 描述]`
4. 生成引用需求清单

### 完成条件
- `storyline.md` 存在
- 逻辑节点因果链完整（无跳跃）
- 所有数据断言有 `[需要引用]` 标记

---

## Step 2: RAG 引用查找 → `sources.json`

**执行脚本**: `cite_rag.py`

从 storyline.md 的 `[需要引用]` 标记提取查询 → 精确搜索 RAG → 获取来源 URL。

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --persona live-study-immigration `
  --output data/short-videos/{slug}/sources.json
```

### 完成条件
- `sources.json` 存在
- 每个 `[需要引用]` 标记都有对应来源（或标记为"未找到"）

---

## Step 3: AI 设计 Marp Slides → `slides/slides.md`

**执行者**: AI Agent（无固定模板，自由发挥）

Agent 基于 `storyline.md` + `sources.json` 设计 Marp 幻灯片：
1. 将 storyline 的每个逻辑节点转化为一页 slide
2. **AI 自行决定**样式、配色、字体、布局
3. 横屏 16:9 尺寸 (`size: 1920x1080`)
4. 有 RAG 来源的 slide 在页脚添加来源 URL 小字水印
5. 总页数 **8–15 页**（对应 30–60 秒视频）

### slides.md 基本约束

```markdown
---
marp: true
size: 1920x1080
# 其余主题/样式由 AI 自由设计
---

第1页内容

---

第2页内容

---
...
```

### 设计参考（非强制，仅供灵感）
- 深色渐变背景（如 `#0a0a1a → #1a1040`）
- 高亮标题用金色 `#ffd700` 或蓝色 `#64b5f6`
- 中文字体 `Microsoft YaHei UI` / `PingFang SC`

### 内容规范（强制）
1. **禁止 emoji** — 标题、表格、正文不加任何 emoji 图标
2. **缩写词必须解释** — 首次出现用 `EE（快速通道）`、`PNP（省提名）` 格式
3. **禁止未解释术语** — “交叉分”“NOC 00/0” 等必须换成大白话
4. **来源 URL 完整** — 必须是完整 URL（`https://www.canada.ca/en/...`），禁止缩写
5. **来源水印位置** — `position: absolute; top: 20px; right: 40px`（右上角）
6. **一页一个概念** — 每个加分项/策略单独一页，不合并
7. **先讲前提** — 涉及资格要求时，先讲门槛再讲加分
8. **CTA 和预告分页** — 评论区互动和下期预告各占一页

### 样式一致性规范（强制）
1. **总结/重点行必须用 `>` 引用** — 所有表格下方的总结文字、行动号召、提示信息统一用 blockquote 格式，不用裸文本或 `**bold**`
2. **大表格用 `dense` 类** — 超过 6 行的表格加 `<!-- _class: dense -->`，缩小 padding/字体防溢出
3. **禁止裸文本段落** — 幻灯片中所有信息必须装在组件内（标题/表格/列表/引用），不留裸的 `<p>` 段落

### 完成条件
- `slides/slides.md` 存在
- slide 页数 8–15 页
- 含 Marp frontmatter (`marp: true`, `size: 1920x1080`)

---

## Step 4: 提取口播脚本 → `script.txt`

**执行者**: Agent 直接编写（无 Skill 依赖）

Agent 从 `slides/slides.md` 提取每页的核心信息，编写 TTS 口播旁白：

### 编写规则
1. slides.md 的**每页 slide = 一行口播**
2. **句间必须有衔接** — 每句话开头要有过渡词/引导词，形成自然对话流，禁止信息点硬切。示例：
   - "先来搞懂…"、"那这个分怎么算呢？"、"不过先别急"
   - "为什么这么低？"、"那怎么办？"、"还有一招"
   - "另外提醒一下"、"所以总结一下"、"下期咱们聊"
3. **说清楚、说明白** — 宁可多几个字也不要含糊。观点必须有结论，误区必须说清"错在哪、对的是什么"
4. **关键论点带原因** — 雅思口语风格：结论 + 简短原因，但不重复已知信息。`别为了加分去读博，因为硕士博士只差十五分` ✅ 。`加六百分，为什么这么猛？因为总分直接破千` ❌（废话）
5. 语气自然、口语化，像在跟朋友聊天
5. 有 RAG 来源的行标注 `[来源:URL]`（从 `sources.json` 取）
6. 无来源的常识行不标注
7. 行数 = slides 页数（8–15 行）

### TTS 友好规范（强制）
1. **数字写中文** — `1200` → `一千两百`、`600` → `六百`、`40` → `四十`。TTS 读阿拉伯数字断句不稳定
2. **口语数字** — 用"两"不用"二"：`两百` ✅ `二百` ❌；`一千两百` ✅ `一千二百` ❌
3. **英文缩写加空格** — 中英文之间必须有空格：`搞懂 CRS 是什么` ✅ `搞懂CRS是什么` ❌
4. **用句号控制停顿** — 长句拆短句用句号，不要全用逗号：`入池是有门槛的。至少一年工作经验` ✅
5. **冒号改句号** — 冒号断句不稳定，改用句号：`有门槛的。至少…` ✅ `有门槛的：至少…` ❌

### 禁止事项
- ❌ 信息点罗列式旁白（"策略一…策略二…策略三…" 无衔接）
- ❌ 含糊结论（"常见误区：A和B" → 没说误区是什么）
- ❌ 问隐私信息（不要让用户在评论区分享年龄/学历/成绩）
- ❌ 阿拉伯数字出现在旁白文本中（slides 上可以用数字，但 script.txt 必须写中文）

### script.txt 格式

```
# 主题名
旁白文本 | [钩子]
旁白文本 | [来源:https://www.canada.ca/en/...]
旁白文本 | [数据]
旁白文本 | [洞察]
旁白文本 | [要点]
旁白文本 | [结尾]
旁白文本 | [互动]
旁白文本 | [预告]
```

标签说明：`[钩子]` 开场、`[来源:URL]` RAG引用、`[数据]` 数据展示、`[洞察]` 分析、`[要点]` 重点、`[结尾]` 总结、`[互动]` 评论区引导、`[预告]` 下期预告

### 完成条件
- `script.txt` 存在
- 行数 = slides.md 页数
- 格式: `旁白文本 | [视觉提示]`
- 每句开头有衔接词，整体读起来像一段连贯的口播

---

## Step 5: Marp 渲染 PNG

**执行脚本**: `compose_marp.py`

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/compose_marp.py `
  --slides data/short-videos/{slug}/slides/slides.md
```

### 完成条件
- `slides/slides.001.png` ~ `slides.0XX.png` 存在
- PNG 数量 = slides.md 页数

---

## Step 6: TTS 语音合成 → `narration/`

**执行脚本**: `synthesize.py`

默认使用 Qwen3-TTS 声音克隆，句间停顿 1 秒:

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend qwen `
  --voice-sample .agent/workflows/short-video/voice/voice-sample.wav
```

降级方案（无 GPU）:
```powershell
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend edge
```

### 音频参数
- **句间停顿**: 默认 1000ms（`--gap 1000`），可调
- **前置静音**: 自动加 150ms 防止 MP3 编码器截掉开头
- **拼接方式**: `-c copy` 直接拼接，不做重新编码

### 完成条件
- `narration/narration.mp3` 存在
- `narration/timestamps.json` 存在

---

## Step 7: 视频组装 → `output/final.mp4`

**执行脚本**: `assemble_video.py`

三步分离式组装（字幕与幻灯片完全解耦）：
1. 幻灯片 concat → 纯视频轨（无音频） + **底部 200px 字幕条**
2. 视频 + 音频 → 中间文件（无字幕）
3. ASS 字幕渲染到底部字幕条 → 最终 MP4

> **字幕解耦架构**: 幻灯片保持原始尺寸完整不动，底部加 200px 深色字幕条（一条蓝色细线分隔）。字幕使用 ASS 格式精确定位，**FontSize=64**，永远不会遮挡幻灯片内容。

### 幻灯片切换
- 幻灯片在音频停顿期间**保持显示**，不插入暗场帧
- 停顿结束后直接切换到下一张，与下一句语音同步开始

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/assemble_video.py `
  data/short-videos/{slug}/
```

> ⚠️ 目录结构约定:
> ```
> {slug}/
> ├── script.txt
> ├── narration/
> │   ├── narration.mp3
> │   └── timestamps.json
> └── slides/
>     ├── slides.001.png
>     ├── slides.002.png
>     └── ...
> ```

### 完成条件
- `output/final.mp4` 存在
- 时长 60-180 秒

---

## Step 8: 检查 & 发布

```powershell
# // turbo
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 `
  data/short-videos/{slug}/output/final.mp4
```

- [ ] 时长 30-60 秒
- [ ] 声音是克隆声音
- [ ] 来源 URL 水印正确
- [ ] 字幕同步无偏移

上传微信视频号 → 标签 `#加拿大移民` `#程序员移民`

---

## 架构说明

### Skills (Agent 智能层)

| Skill | 职责 |
|-------|------|
| `video-storyline` | 叙事线设计 + 逻辑链构建 + 引用需求标注 |

> **Note**: `slides.md` 和 `script.txt` 均由 Agent 直接编写（规则内联于 Step 3/4），无独立 Skill。

### Scripts (自动化工具)

| 脚本 | 输入 | 输出 |
|------|------|------|
| `cite_rag.py` | storyline.md | sources.json (引用URL) |
| `synthesize.py` | script.txt + voice-sample.wav | narration.mp3 + timestamps.json |
| `compose_marp.py` | slides.md (AI 写的) | slides/*.png |
| `assemble_video.py` | script.txt + slides/ + narration/ | final.mp4 |

**脚本间零依赖** — 每个脚本独立运行，通过文件系统通信。

---

## 文件结构

```text
data/short-videos/{slug}/
├── storyline.md                 # Step 1: 叙事逻辑 (Skill)
├── sources.json                 # Step 2: RAG 引用 URL (Script)
├── slides/                      # Step 3-5: Marp 幻灯片
│   ├── slides.md                #   AI 自由设计的 Marp 源文件 (Step 3)
│   ├── slides.001.png           #   渲染后的 slide 图片 (Step 5)
│   └── ...
├── script.txt                   # Step 4: 口播脚本 (从 slides 提取)
├── narration/                   # Step 6: TTS
│   ├── narration.mp3
│   └── timestamps.json
└── output/                      # Step 7: 最终视频
    ├── final.mp4
    └── subtitles.srt
```

---

## 依赖

```powershell
npm install -g @marp-team/marp-cli   # Marp 渲染 (或 npx 自动安装)
pip install qwen-tts                 # Qwen3-TTS (GPU, 推荐)
pip install edge-tts                 # Edge TTS (降级方案)
pip install loguru                   # 日志
# ffmpeg 必须在 PATH 中
```


