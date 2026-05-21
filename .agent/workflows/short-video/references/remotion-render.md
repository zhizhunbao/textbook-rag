# Remotion 渲染指南

> 本文档是 `workflow.md` Step 6 的详细参考。流程概要见 [workflow.md](../workflow.md)。

---

## 渲染命令

```powershell
# // turbo
# cwd: textbook-rag/
node .agent/workflows/short-video/remotion/render.mjs --data data/short-videos/{slug}
```

---

## 组件架构

```
1920×1080 总画布
┌─────────────────────────────────┐
│  章节时间轴 ChapterTimeline (48px)  │  ← B站风格章节进度条
├─────────────────────────────────┤
│  幻灯片区 (1920×832)              │  ← 顶部对齐，标题永远可见
│  - CoverSlide: 封面（金色渐变）    │
│  - ContentSlide: 表格/列表/正文  │
├─────────────────────────────────┤
│  字幕条 (1920×200)                │  ← 自动换行，最多两行
│                    品牌水印 →  │  ← 右下角 30%透明度
└─────────────────────────────────┘
```

### 章节时间轴 (ChapterTimeline)

- **数据来源**: storyline.md 中的 `**章节**:` 字段（作者手动定义）
- **回退**: 无 `**章节**` 字段时自动计算（跳过引用/预告页，合并同前缀连续 slide）
- **显示**: 每个章节按时长比例分配宽度，当前章节金色高亮 + 进度填充
- **建议 8-12 个章节**，太多会导致标签截断

> 章节标签建议 ≤8 个字，超长会被截断加 …

---

## 字号规范（手机端优先）

> ⚠️ 所有字号针对 1920×1080 画布，手机竖屏观看时等效缩小约 50%。

### CoverSlide（封面页）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 钩子大数字 hookNumber | 200 | 900 | CoverSlide.tsx:34 |
| 钩子单位 hookUnit | 32 | 600 | CoverSlide.tsx:46 |
| 主标题 title | 80 | 800 | CoverSlide.tsx:55 |
| 副标题 subtitle | 32 | 400 | CoverSlide.tsx:66 |

### ContentSlide（内容页）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 标题 heading | 56 | 800 | theme.ts:82 |
| 列表要点 points | 38 | — | ContentSlide.tsx:34 |
| 正文 (CTA/preview) | 48 | 700 | ContentSlide.tsx:49 |
| 正文 (非CTA) | 42 | 400 | ContentSlide.tsx:49 |
| 引用块 citation | 28 | italic | ContentSlide.tsx:69 |

### 表格自适应密度（5 级）

> 密度级别自动选择：从 normal 开始试，放不下就逐级降到更密的级别。

| 密度 | 触发条件 | 表头 | 表体 | 行间距(padV padH) |
|------|---------|------|------|--------|
| normal | 默认 | 32 | 36 | 16px 28px |
| dense | 估算高度超出 | 30 | 34 | 10px 18px |
| xDense | 估算高度超出 | 26 | 30 | 6px 12px |
| xxDense | 估算高度超出 | 22 | 26 | 4px 10px |
| **xxxDense** | **估算高度超出** | **20** | **22** | **2px 8px** |

> slide 区域 832px，padding 60+24=84px，标题 ~95px，表格可用 ~650px。
> xxxDense 专为引用来源等 URL 密集表设计，保证 8-10 行 URL 表格不溢出。
> URL 列单元格字号额外 -4px（最小 16px），启用 `word-break: break-all`。

### SubtitleBar（字幕条）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 字幕文字 | 44（固定） | 700 | SubtitleBar.tsx:20 |
| 品牌水印 | 20 | — | ShortVideo.tsx:50 (字幕区右下角, 30%透明) |

> 字幕固定 44px，不随文字长度缩放。长句自动换行（`word-break: keep-all`），最多两行。
> 台词每句 ≤40 字符（R3），超长会溢出字幕卡。

### 全局

| 元素 | 值 | 文件:行 |
|------|-----|---------| 
| 字体族 fontFamily | `'Inter', 'Noto Sans SC', system-ui, sans-serif` | theme.ts:42 |
| 画布宽 | 1920px | theme.ts:45 |
| 画布高 | 1080px | theme.ts:46 |
| 章节时间轴高 | 48px | theme.ts:47 |
| 幻灯片区高 | 832px | theme.ts:48 |
| 字幕条高 | 200px | theme.ts:49 |
