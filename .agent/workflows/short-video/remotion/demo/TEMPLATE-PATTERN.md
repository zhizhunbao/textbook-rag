# Short Video Template Pattern — 短视频模板模式规范

> **用途**: Agent 生成新视频时的数据结构 + 视觉模板 + 布局规范参考。
> **最后更新**: 2026-05-12

---

## 1. 架构总览

```
storyline.md
    ↓ (Agent 将叙事拆分为 slides)
slides.json          ← 本文件定义的 SlideData[]
    ↓
render.mjs           ← 注入 timestamps, 构建 input-props.json
    ↓
Remotion render      ← 最终输出 final.mp4
    ↓
demo/                ← 浏览器预览 (Layout Lab)
```

### 文件角色

| 文件 | 职责 |
|------|------|
| `data.js` | `DEMO_SLIDES[]` — 幻灯片内容数组 (演示数据) |
| `templates.js` | `TEMPLATES{}` — 配色+排版+装饰方案 (6套) |
| `template-renders.js` | 渲染器 — 每套模板的封面+内容页 HTML 生成 |
| `themes.js` | `THEMES{}` — 旧版配色 (兼容用) |
| `app.js` | Layout Lab 预览控制器 |
| `input-props.json` | Remotion 渲染用的完整 props |

---

## 2. Slide 数据结构 (`SlideData`)

每个 slide 是一个 JS/JSON 对象，`type` 字段决定渲染方式。

### 2.1 Slide Types (幻灯片类型)

| type | 用途 | 必要字段 | 可选字段 |
|------|------|----------|----------|
| `cover` | 封面 / Hook 页 | `title` | `subtitle`, `hookNumber`, `hookUnit`, `hookCaption` |
| `evidence` | 数据论证页 | `title`, `table` | `citation` |
| `argument` | 观点阐述页 | `title`, `table` | `citation` |
| `summary` | 要点回顾页 | `title`, `points` | — |
| `cta` | 行动号召页 | `title`, `content` | — |
| `preview` | 下期预告页 | `title`, `content` | — |

### 2.2 通用字段

所有 slide 必须包含:

```jsonc
{
  "type": "cover|evidence|argument|summary|cta|preview",
  "title": "标题 (≤12个中文字)",
  "source": "https://official-source-url...",           // 官方来源 URL
  "_subtitle_text": "字幕区文本 (≤15个中文字)"          // 底部字幕
}
```

### 2.3 各类型 Slide 详细 Schema

#### Cover (封面)

```jsonc
{
  "type": "cover",
  "title": "选错路 多等半年",           // 核心冲击标题
  "subtitle": "省提名两条路，到底怎么选？",   // 副标题
  // Data Hook (可选，competitor 布局专用)
  "hookNumber": "600",                // 大数字冲击
  "hookUnit": "额外CRS加分",           // 数字单位
  "hookCaption": "拿到省提名 = 直接碾压邀请线", // 解释行
  "source": "https://...",
  "_subtitle_text": "省提名加600分 选错路多等半年"
}
```

#### Evidence (数据论证)

```jsonc
{
  "type": "evidence",
  "title": "省提名直接加600分",
  "table": {
    "headers": ["对比项", "通用轮次", "省提名轮次"],
    "rows": [
      ["邀请线", "**508**", "**742**（含+600）"],
      ["你需要的裸分", "**508**", "**110-189**"],
      ["竞争人数", "23.4万人池", "264-423人"]
    ]
  },
  // `**text**` 语法 → 渲染为 accent 色高亮
  "citation": "Provincial or territorial nomination: 600 additional points.",  // 可选
  "source": "https://...",
  "_subtitle_text": "省提名加600分 碾压通用线"
}
```

#### Argument (观点阐述)

```jsonc
{
  "type": "argument",
  "title": "600分什么概念？",
  "table": {
    "headers": ["CRS项目", "最高分"],
    "rows": [
      ["核心分（年龄+学历+语言+工作）", "500"],
      ["技能转化分", "100"],
      ["附加分 — **省提名**", "**600**"]
    ]
  },
  "source": "https://...",
  "_subtitle_text": "CRS满分500 省提名加600"
}
```

> **Evidence vs Argument**: Evidence 侧重展示原始数据，Argument 侧重解读和推理。视觉无差异但语义不同。

#### Summary (要点回顾)

```jsonc
{
  "type": "summary",
  "title": "本期要点回顾",
  "points": [
    "省提名 = 额外 **+600 CRS**",
    "裸分只需 **110-189** 即可获邀",
    "2026 配额 **91,500**（+66%）",
    "EE路约 **7 个月**，$1,590 起",
    "Quebec 和 Nunavut **没有 PNP**"
  ],
  "source": "https://...",
  "_subtitle_text": "五个核心要点 记住就够了"
}
```

#### CTA (行动号召)

```jsonc
{
  "type": "cta",
  "title": "你在哪个省？",
  "content": "你的职业在不在那个省的提名清单上？评论区告诉我。",
  "source": "https://...",
  "_subtitle_text": "评论区告诉我你在哪个省"
}
```

#### Preview (下期预告)

```jsonc
{
  "type": "preview",
  "title": "下期预告",
  "content": "哪些省的提名不需要Job Offer",
  "source": "https://...",
  "_subtitle_text": "下期：哪些省不要Job Offer"
}
```

---

## 3. 表格规则 (Table)

```jsonc
{
  "headers": ["col1", "col2", ...],   // 2-5 列
  "rows": [                           // 2-4 行 (推荐)
    ["cell", "**highlighted**", ...],  // **bold** → accent 色
    ...
  ]
}
```

| 规则 | 说明 |
|------|------|
| 列数 ≤ 5 | >5 列触发 `dense` 模式 (缩小字号) |
| 行数 ≤ 4 | >4 行触发 `dense` 模式 |
| `**text**` | 渲染为 `accentLight` 色 + `font-weight:800` |
| 居中对齐 | 所有单元格默认居中 |

---

## 4. 视频结构模式 (Slide Sequence)

### 4.1 标准序列 (推荐 8-10 slides)

```
cover → evidence → argument → evidence → argument → evidence → argument → summary → cta → preview
```

| 位置 | 类型 | 目的 |
|------|------|------|
| 0 | `cover` | 数据冲击 Hook，吸引停留 |
| 1-2 | `evidence` / `argument` 交替 | 正题论证 (核心数据 + 解读) |
| 3-4 | `evidence` / `argument` 交替 | 深入论证 (原始轮次 + 分析) |
| 5-6 | `evidence` / `argument` 交替 | 扩展论证 (申请方法 + 建议) |
| 7 | `summary` | 要点回顾 (3-5 个 bullet) |
| 8 | `cta` | 引导互动 (评论/点赞/关注) |
| 9 | `preview` | 下期预告 (钩子留存) |

### 4.2 内容密度规则

- 每页 **1 个核心信息点**，不堆叠
- `_subtitle_text` ≤ **15 个中文字** (字幕区宽度限制)
- `title` ≤ **12 个中文字** (标题冲击力)
- 表格每格 ≤ **15 个字** (含强调标记)

---

## 5. 模板系统 (Template)

### 5.1 模板结构

```jsonc
{
  "id": "template-id",
  "name": "显示名 Name",
  "description": "一句话描述",
  "coverStyle": "neon|frost|ember|ocean|minimal|competitor",
  "contentStyle": "neon|frost|ember|ocean|minimal|competitor",
  "palette": { /* 完整配色 */ },
  "typography": { /* 字体覆写 */ },
  "decorations": { /* 装饰元素开关 */ }
}
```

### 5.2 Palette (配色方案)

每套配色包含以下 token:

```jsonc
{
  // 背景
  "bgPrimary": "#0f0f1a",           // 主背景色
  "bgSecondary": "#1a1a2e",         // 次背景色
  "bgGradient": "linear-gradient(...)",  // 内容页背景渐变
  "bgCover": "linear-gradient(...)",     // 封面专用背景

  // 强调色
  "accent": "#FFD700",              // 主强调色 (金色/霓虹色等)
  "accentLight": "#FFE44D",         // 亮色变体 (高亮文本)
  "accentSecondary": "#00D2FF",     // 辅助强调色 (链接/装饰)
  "accentMuted": "#a0a0b0",        // 静默色 (次要信息)

  // 文本
  "textPrimary": "#ffffff",         // 主文本
  "textSecondary": "rgba(...,0.85)", // 次文本
  "textMuted": "rgba(...,0.25)",    // 弱文本

  // 表格
  "tableHeaderBg": "rgba(...,0.12)",  // 表头背景
  "tableHeaderText": "#FFE44D",       // 表头文字
  "tableRowOdd": "rgba(...,0.04)",    // 奇数行背景
  "tableRowEven": "rgba(...,0.03)",   // 偶数行背景

  // 引用
  "citationBg": "rgba(...,0.06)",
  "citationBorder": "rgba(...,0.5)",
  "citationText": "rgba(...,0.7)",

  // 字幕
  "subtitleBg": "#0f0f1a",
  "subtitleText": "#ffffff",
  "subtitleHighlight": "#FFD700",    // 可选: 字幕高亮色

  // 来源
  "sourceText": "rgba(...,0.4)"
}
```

### 5.3 Typography (排版)

```jsonc
{
  "titleWeight": 800,               // 标题字重 (300-900)
  "coverTitleSize": 72,             // 封面标题字号 (px)
  "coverSubtitleSize": 28,          // 封面副标题字号
  "bodyFontFamily": "'Inter', 'Noto Sans SC', system-ui, sans-serif"
}
```

### 5.4 Decorations (装饰元素)

每套模板的特色装饰 (true/false):

| 模板 | 装饰项 | 效果 |
|------|--------|------|
| Neon Pulse | `scanlines`, `glowBorder`, `cornerMarks` | 扫描线 + 发光边 + 四角标 |
| Frost Glass | `glassPanels`, `blurOrbs`, `softShadows` | 毛玻璃 + 光球 + 柔阴影 |
| Ember Glow | `warmGlow`, `grainTexture`, `gradientBorders` | 暖光 + 纹理 + 渐变边 |
| Ocean Depth | `caustics`, `wavePattern`, `depthFade` | 水纹 + 波浪 + 深度渐变 |
| Competitor Gold | `goldAccentLine`, `subtleGlow`, `dataFocus` | 金线 + 微光 + 数据优先 |
| Minimal Ink | `verticalLine`, `redDot`, `wideSpacing` | 竖线 + 红点 + 大留白 |

---

## 6. 布局系统 (Layout)

6 种布局风格，可与任意配色方案混搭。

### 6.1 布局列表

| Layout Key | 名称 | 封面特征 | 内容页特征 |
|------------|------|----------|------------|
| `neon` | 居中堆叠+角标 | 居中标题 + 四角装饰 + 分割线 | 边框容器 + 角标 + 居中 |
| `frost` | 毛玻璃卡片 | 光球 + 玻璃卡片 + 居中 | 标题外+内容卡片 + 光球 |
| `ember` | 左对齐社论风 | 左对齐 + 渐变装饰线 + 菱形 | 渐变左边框 + 左对齐 |
| `ocean` | 顶栏分离式 | 水平波纹 + 居中 + 竖线 | 标题栏/内容区/底部引用 三段 |
| `minimal` | 竖线左排版 | 红点 + 居中 + 大留白 | 竖线+红点左侧 + 右侧内容 |
| `competitor` | 数据优先 | Data Hook 大数字 + 居中 + 无装饰 | 标题+表格 + URL右上水印 |

### 6.2 Competitor 布局特殊规则

- **无 citation**: 不渲染英文引用块
- **URL 水印**: 右上角绝对定位，`font-size:18px`，完整显示不省略
- **Data Hook**: 封面独有 `hookNumber` → `120px / font-weight:900 / accent 色`
- **来源**: patterns.json 竞品分析驱动设计，深色背景差异化

---

## 7. 画布尺寸规范 (Canvas Spec)

```
总画布:   1920 × 1080 px
├── 幻灯片区: 1920 × 880 px   (padding: 60px top, 80px sides, 24px bottom)
├── 字幕区:   1920 × 200 px   (居中, padding: 0 80px)
安全区:     80px 左右, 60px 上

字号参考:
  封面标题:   64-80px  (由模板 typography.coverTitleSize 决定)
  内容标题:   46-52px
  表头:       20-24px (dense 时更小)
  表格内容:   24-30px
  字幕文字:   52px, font-weight:700
  来源 URL:   16-18px, monospace
  引用块:     22px, italic
```

---

## 8. input-props.json 完整结构

这是 Remotion 渲染的输入格式:

```jsonc
{
  "slides": [
    // SlideData[] — 参见 §2
  ],
  "timestamps": [
    {
      "index": 1,            // 句子序号 (1-based)
      "start": 0.15,         // 开始时间 (秒)
      "end": 2.31,           // 结束时间 (秒)
      "text": "CRS不够怎么办",  // 字幕文本
      "slide_index": 0       // 对应 slides[] 的索引
    }
    // ...
  ],
  "audioUrl": "/public/audio.wav"
}
```

### timestamps 规则

- `slide_index` 决定该时间段显示哪张 slide
- 同一 `slide_index` 可对应多个 timestamp (一张 slide 上多句话)
- `text` 用于底部字幕逐字高亮

---

## 9. 生成清单 (Checklist)

Agent 生成新视频时需产出:

- [ ] `slides.json` — 符合 §2 的 `SlideData[]`
- [ ] `script.txt` — 旁白脚本 (每行一句，`|` 标记换页)
- [ ] `narration/timestamps.json` — TTS 后的时间轴
- [ ] `narration/narration.wav` — TTS 音频文件
- [ ] 选择模板: `competitor-gold` (默认) 或其他 §5 中的模板
- [ ] 确保 `_subtitle_text` ≤ 15 字
- [ ] 确保 `title` ≤ 12 字
- [ ] 确保每张 slide 有 `source` URL
- [ ] 确保 `**text**` 语法仅用于关键数据

---

## 10. 快速参考: 创建新视频数据

```javascript
// 最小可用 data.js 模板
const DEMO_SLIDES = [
  // 0: 封面 — 数据冲击 Hook
  {
    type: 'cover',
    title: '【标题 ≤12字】',
    subtitle: '【副标题】',
    hookNumber: '【大数字】',       // 可选
    hookUnit: '【单位】',           // 可选
    hookCaption: '【一句话解释】',   // 可选
    source: 'https://...',
    _subtitle_text: '【≤15字】',
  },

  // 1-N: evidence / argument 交替
  {
    type: 'evidence',   // 或 'argument'
    title: '【标题 ≤12字】',
    table: {
      headers: ['列1', '列2', '列3'],
      rows: [
        ['数据A', '**高亮B**', '数据C'],
        ['数据D', '数据E', '**高亮F**'],
      ],
    },
    source: 'https://...',
    _subtitle_text: '【≤15字】',
  },

  // N+1: 要点回顾
  {
    type: 'summary',
    title: '本期要点回顾',
    points: [
      '要点1 **高亮数据**',
      '要点2 **高亮数据**',
      '要点3',
    ],
    source: 'https://...',
    _subtitle_text: '【≤15字】',
  },

  // N+2: 行动号召
  {
    type: 'cta',
    title: '【引导互动的问题】',
    content: '【具体引导语】',
    source: 'https://...',
    _subtitle_text: '【≤15字】',
  },

  // N+3: 下期预告
  {
    type: 'preview',
    title: '下期预告',
    content: '【预告内容】',
    source: 'https://...',
    _subtitle_text: '【≤15字】',
  },
];
```

---

## 11. 可用模板速查

| 模板 ID | 风格 | 推荐场景 |
|---------|------|----------|
| `neon-pulse` | 赛博霓虹 | 科技类、编程类 |
| `frost-glass` | 毛玻璃质感 | 通用、商务类 |
| `ember-glow` | 烬火流光 | 情感类、故事类 |
| `ocean-depth` | 深海蔚蓝 | 教育类、学术类 |
| `competitor-gold` ⭐ | 竞品金 (默认) | 数据类、政策类、移民类 |
| `minimal-ink` | 极简水墨 | 文化类、哲学类 |

> ⭐ **默认模板**: `competitor-gold` — 基于 10 个竞品帧级分析，深靛蓝底+金色强调，已验证高转化。
