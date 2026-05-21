# 多平台发布指南

> 本文档是 `workflow.md` Step 7 的详细参考。流程概要见 [workflow.md](../workflow.md)。

---

## 平台合规铁律

> ⚠️ **Content compliance = account safety. Violating these rules may cause throttling, demotion, or ban.**

### 敏感词替换表

| ❌ Banned Word (CN) | ✅ Safe Replacement | Reason |
|------------|-----------|------|
| immigration (yi-min) | newcomer, friends who just landed | Triggers "immigration agent" risk control |
| immigration consultant/agent (yi-min gu-wen/zhong-jie) | ❌ Fully banned | Requires licensed qualification |
| visa (qian-zheng) | visa (English), entry preparation | Triggers proxy-service risk control |
| proxy/agent (dai-ban/dai-li) | ❌ Fully banned | Suspected agency service |
| DM me/add me/consult (si-xin/jia-wo/zi-xun) | ❌ Fully banned | Private traffic diversion |
| PR/permanent residency application | PR (use English directly) | Reduces sensitivity |
| IRCC (said as abbreviation) | Canada official website | Avoid over-association with immigration |
| new immigrant (xin yi-min, in narration/tables) | newcomer | English doesn't trigger risk control; also official bank terminology |
| rental agent (zu-fang zhong-jie) | broker | Avoids "agent" trigger |

> 💡 **Keep "newcomer" in English in bank product names**, e.g. "BMO NewStart Program".
> Keep "immigrant/newcomer" as-is in citation blocks (inside quotes, does not trigger risk control).

### 频道名规则

- All storyline `**作者**:` fields must use **海外生活指南**
- Channel name must NOT contain words for immigration/consultant/study-abroad in Chinese

### 标签合规

| ❌ Banned Tags | ✅ Safe Tags |
|------------|----------|
| #Canada-immigration (CN) | #加拿大生活 |
| #immigration-guide (CN) | #海外生活攻略 |
| #study-abroad-visa (CN) | #留学生活 |
| #immigration-consultant (CN) | #生活指南 |

### 内容定位话术

- ✅ "Teach you to read government websites"
- ✅ "Official data interpretation"
- ✅ "Overseas life encyclopedia"
- ❌ "Help you get a visa" (CN)
- ❌ "Immigration consulting" (CN)
- ❌ "Step-by-step immigration application" (CN)

---

## 内容规范（在 storyline.md 中遵守）

1. **论点+证据配对** — `[argument]` 后可紧跟 `[evidence]`
2. **每页必须有 `**来源**`** — 完整 URL
3. **禁止 emoji** — 标题、表格、台词不加 emoji
4. **缩写词必须解释** — 首次出现用 `EE（快速通道）` 格式
5. **文本中可用 `**加粗**`** — 渲染时变为金色高亮
6. **内容合规** — 遵守上方「平台合规铁律」，禁止使用敏感词

---

## v1: 中文平台发布

**执行脚本**: `scripts/publish_all.py`（统一入口） + `scripts/publish_weixin.py`（视频号专用）

**底层依赖**: [social-auto-upload](https://github.com/dreammis/social-auto-upload) (`.github/social-auto-upload/`)

| 优先级 | 平台 | 变现方式 | 登录方式 | Cookie 存储 |
|--------|------|---------|---------|-------------|
| 🥇 | 小红书 | 品牌合作（蒲公英） | 扫码 | `.github/social-auto-upload/cookies/xiaohongshu_creator.json` |
| 🥉 | 抖音 | 星图广告 + 创作者基金 | 扫码 | `.github/social-auto-upload/cookies/douyin_creator.json` |
| 4 | B站 | 创作激励 + 花火 | 扫码 | `.github/social-auto-upload/cookies/bilibili_creator.json` |
| 5 | 快手 | 磁力金牛 | 扫码 | `.github/social-auto-upload/cookies/kuaishou_creator.json` |
| 6 | 视频号 | 创作者分成 | 扫码 | `.agent/workflows/short-video/browser-data/weixin-channels/` |

```powershell
# 登录（每个平台只需一次，Cookie 有效 ~30 天）
uv run .agent/workflows/short-video/scripts/publish_all.py --login xiaohongshu
uv run .agent/workflows/short-video/scripts/publish_all.py --login douyin
uv run .agent/workflows/short-video/scripts/publish_all.py --login bilibili
uv run .agent/workflows/short-video/scripts/publish_all.py --login kuaishou
uv run .agent/workflows/short-video/scripts/publish_all.py --login weixin

# 发布
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md
```

---

## v2: 国际平台发布（TikTok / YouTube / LinkedIn / Instagram）

**执行脚本**: `publish/publish_all.py`（config-driven 统一入口）

**配置文件**: `publish/config.yaml`

| 优先级 | 平台 | 引擎 | 登录方式 | Session 存储 |
|--------|------|------|---------|-------------|
| 🥇 | TikTok | Playwright | 手动登录（只需一次） | `publish/credentials/tiktok/browser-data/` |
| 🥈 | YouTube | Playwright | 手动登录（只需一次） | `publish/credentials/youtube/browser-data/` |
| 🥉 | LinkedIn | Playwright | 邮箱+密码登录（只需一次） | `publish/credentials/linkedin/browser-data/` |
| 4 | Instagram | Playwright | 手动登录（只需一次） | `publish/credentials/instagram/browser-data/` |

```powershell
# 首次登录（每平台只需一次，persistent context 保持 session）
# cwd: textbook-rag/
uv run .agent/workflows/short-video/publish/publish_all.py --login tiktok
uv run .agent/workflows/short-video/publish/publish_all.py --login youtube
uv run .agent/workflows/short-video/publish/publish_all.py --login linkedin
uv run .agent/workflows/short-video/publish/publish_all.py --login instagram

# 发布到所有国际平台
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md

# 发布到指定平台
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms tiktok,youtube
```

> 💡 **v2 架构特点**:
> - Config-driven：平台配置在 `config.yaml`，新增平台只需加配置 + 平台模块
> - Playwright persistent context：登录一次，session 自动保持
> - 反自动化检测：`--disable-blink-features=AutomationControlled`
> - 标题/描述/标签从 `storyline.md` 自动提取

> ⚠️ **注意事项**:
> - LinkedIn 反自动化较严，登录时可能需要多次尝试或验证码
> - TikTok 上传后视频需要平台审核，发布成功不代表立即可见
> - YouTube 上传后默认为 Public，可在 config.yaml 中调整
> - Instagram 反自动化较严，使用持久化浏览器 context 保持登录态
> - Instagram Reels 支持 16:9 横屏视频
> - 所有平台均通过浏览器自动化实现，非官方 API
> - 平台页面结构更新可能导致选择器失效，需更新对应平台模块

### 单独发布视频号（兼容旧流程）

```powershell
# 仅发布到视频号
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/publish_weixin.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --tags "#加拿大生活 #海外生活攻略 #生活指南"
```

---

## 发布规范

- **标题**: 钩子句式，带数字
- **封面**: 大字+数字，高对比度
- **标签**: `#加拿大生活` `#海外生活攻略` + 主题标签（禁止使用含"移民"的标签）
- **系列标记**: 如 "加拿大生活常识 2/7"

---

## 发布后追踪

| 指标      | 目标值 | 不达标动作           |
| --------- | ------ | -------------------- |
| 3s 播放率 | ≥ 50% | 换钩子/封面重发      |
| 完播率    | ≥ 25% | 缩短时长或删减信息点 |
| 互动率    | > 0    | 加强互动引导         |
