---
description: textbook-rag v3 开发工作流 — 基于 rag-dev-v3/ 四文档体系的精简工作流。使用 /rag-dev-v3 启动。
---
# Textbook RAG v3 开发工作流

// turbo-all

---

## 📖 文档体系（Single Source of Truth）

**所有结构、模板、清单、状态均在 `rag-dev-v3/` 中维护，本工作流只做编排。**

| 文档                                                   | 内容                                         | 何时查阅           |
| ------------------------------------------------------ | -------------------------------------------- | ------------------ |
| [project-structure.md](./rag-dev-v3/project-structure.md) | 目录结构 · 命名规则 · 依赖方向 · 跨层对齐 | 新建文件前         |
| [file-templates.md](./rag-dev-v3/file-templates.md)       | Python / Payload / React 全部文件模板        | 写代码时复制模板   |
| [module-manifest.md](./rag-dev-v3/module-manifest.md)     | 模块清单 (Layout/UI/UX/Func/Noun) + 文件列表 | 确认模块边界和命名 |
| [module-roadmap.md](./rag-dev-v3/module-roadmap.md)     | 功能实现状态 (✅/❌) + 待建清单              | 选择开发目标       |

## 🎯 Sprint 设计哲学（以终为始，上线收费）

**核心原则：不写没有商业价值的代码，不定义无法闭环的 Sprint。**

1. **以终为始 (Start with the End)**:
   - 每个 Sprint 必须对应一个**可感知的用户价值点**（例如：从"实现检索"改为"实现律师角色咨询能力"）。
   - 定义 Sprint 前必问：用户愿意为这个 Sprint 的产出付费吗？如果不能，它是否是付费功能的必要前提？

2. **端到端闭环 (End-to-End Loop)**:
   - 拒绝"纯后端"或"纯前端" Sprint。
   - 每个 Sprint 必须包含 `Engine (逻辑) + Payload (数据) + UI (交互)` 的完整路径，确保完成后即可进行产品 Demo 或小规模交付。

3. **收费点导向 (Monetization Hooks)**:
   - 优先开发与"价值产出"直接相关的模块（如：高质量回答、专业报告生成、多角色切换）。
   - 关注**确定性**：收费用户对错误率的容忍度极低。每个 Sprint 必须包含配套的**评估闭环** (Evaluation) 以确保质量达标。

4. **拒绝过度工程**:
   - 如果用户不为"可配置性"买单，就直接硬编码。
   - 如果用户不为"高性能架构"买单（且当前性能不影响体验），就用最简单的实现。

> ⚠️ **不在工作流中重复 rag-dev-v3/ 内容。** 如果需要查阅，直接 `view_file` 对应文档。

---

## 🌍 全局规则

### Windows PowerShell

| 操作        | ✅ 用                       | ❌ 禁止              |
| ----------- | --------------------------- | -------------------- |
| 安装包      | `uv add package`          | `pip install`      |
| 运行 Python | `uv run python script.py` | `python script.py` |
| 列文件      | `dir` / `Get-ChildItem` | `ls`               |
| 删除        | `Remove-Item`             | `rm`               |
| 切目录      | `cwd` 参数                | `cd`               |
| 链接命令    | `;`                       | `&&`               |

### 代码质量

- 函数 ≤ 50 行，文件 ≤ 800 行，嵌套 ≤ 4 层
- 无 magic number，无 console.log，无硬编码密钥
- Python: `from __future__ import annotations` + loguru
- TypeScript: 语义 Tailwind token (`bg-card` 不是 `bg-gray-800`)
- **图标只用 SVG**（lucide-react 或 inline `<svg>`），禁止使用 emoji 字符（跨平台渲染不一致）
- 文件头注释格式见 `file-templates.md` § 四

### Surgical Changes（精准修改）

- **只改请求相关的代码** — 每一行 diff 都必须能追溯到用户需求
- 不"顺手改进"相邻代码、注释、格式
- 不重构没坏的东西
- 匹配现有代码风格，即使你会写得不一样
- 发现无关死代码 → **提一嘴，不要删**
- 你的改动产生的孤立 import/变量/函数 → **必须清理**
- 改动前已存在的死代码 → **不清理，除非被要求**

### Simplicity First（简洁优先）

- 不加没被要求的功能、抽象、"灵活性"、"可配置性"
- 单次使用的逻辑不抽象
- 不为不可能的场景写错误处理
- 200 行能变 50 行 → 重写
- 检验标准：高级工程师会说"过度设计"吗？会 → 简化

### 数据流方向

> **前端查数据一律走 Payload CMS，不直接调 Engine API 读数据。**

```
Engine (Python)  →  处理数据 → 写入 Payload DB (via REST API)
Payload CMS      →  存储数据 → 前端读取 (via /api/* REST)
Frontend (React) →  只读 Payload /api/*，不直接调 Engine
```

- 前端 `api.ts` 中的 fetch 目标必须是 `/api/\<collection\>`（Payload REST），不允许直接请求 `ENGINE_URL`
- Engine 产生的数据（解析结果、向量状态等）必须先写回 Payload 的 Collection，前端再从 Collection 读
- 唯一例外：Engine 的 `/engine/query` 等实时查询接口（需要 LLM 推理的），可以直接调用

### 多用户安全（上线必须）

> **多用户隔离是上线收费的硬前提。每一行涉及用户数据的代码都必须验证归属。**

| 规则 | ✅ 正确 | ❌ 禁止 |
|------|---------|--------|
| user_id 来源 | 从 auth middleware / JWT 解码获取 | 从 request body / query param 传入 |
| Collection read | `isOwnerOrAdmin` 或 `isLoggedIn` | `() => true` (全公开) |
| Engine API 认证 | JWT Cookie / API Key Header 验证 | 无认证裸跑 |
| ChromaDB 用户数据 | `user_{userId}_{slug}` 隔离 collection | 共用 collection 无隔离 |
| 新 Collection 默认 | `read: isLoggedIn`, `create: isLoggedIn` | `read: () => true` |

### 代码溯源

1. **模板优先**: 新建文件从 `file-templates/` 复制对应模板，模板是唯一的结构标准
2. **参考仓库辅助**: 开发具体功能时，可查阅 `.github/references/` 下对应的参考仓库代码
3. **教科书注释**: 涉及算法/设计模式时，标注来源 `# Ref: Author, Book, ChN — concept`

---

## 🔧 开发流程

### Phase 0 — 需求确认（商业价值优先）

1. **价值定位** — 明确本功能在"收费链路"中的位置（是核心卖点、交付物、还是基础基建？）。
2. **静默调研** — 读相关模块代码 + `module-roadmap.md` 中的状态。
3. **给方案（端到端）**：
   - **用户旅程**：用户如何从 UI 触发，数据如何流转，最终得到什么价值。
   - **技术思路**：Engine + Payload + Frontend 的改动点。
   - **质量保障**：如何验证这个功能达到了"可上线/可收费"的标准（评估指标）。
4. **等确认** — "以上方案符合商业闭环？确认后开始。"

> 没有价值逻辑和用户确认，禁止编码。

### Phase 1 — 开发

**新增模块完整流程:**

1. 查 `module-manifest.md` 确认模块的 Noun 集和文件列表
2. 查 `project-structure.md` 确认目录约束和跨层对齐
3. **编码前约束检查（禁止跳过）：**

   **依赖方向 — 逐条验证每个 import：**
   ```
   feature → shared       ✅  允许
   feature → providers    ✅  允许
   shared  → feature      ❌  禁止
   feature → feature      ❌  禁止 (通过 shared 或 providers 中转)
   layout  → shared       ✅  允许
   layout  → providers    ✅  允许
   engine/<A> → engine/<B>  ❌  禁止 (子模块间不互相依赖)
   ```
   > 如果需要调用另一个 engine 子模块的 API/类型，必须：
   > - 将共享部分提升到 `shared/` 层，或
   > - 在本模块的 `api.ts` 中直接调用 Payload/Engine REST API

   **命名规范 — 新文件必须匹配：**
   | 文件类型 | 命名规则 | 示例 |
   |---------|---------|------|
   | 页面组件 | `<Name>Page.tsx` | `QuestionsPage.tsx` |
   | 面板组件 | `<Name>Panel.tsx` | `GenerationPanel.tsx` |
   | 卡片组件 | `<Item>Card.tsx` | `QuestionCard.tsx` |
   | 自定义 hook | `use<Name>.ts` | `useBooks.ts` |
   | Context | `<Name>Context.tsx` | `ModelContext.tsx` |
   | barrel | `index.ts` | 每个模块必须有 |

   **数据获取 — 必须用 hook 封装：**
   - 每个数据源（API 调用 + 状态管理）必须独立为 `use<Name>.ts`
   - 禁止在组件中直接写 `useEffect + fetch`（inline fetching）
   - hook 返回 `{ data, loading, error, refetch }` 标准形状

4. **先改注释，再改代码（禁止跳过）：**
   - 新建文件：从 `file-templates.md` 复制模板，先填写文件头注释，再写实现
   - 修改文件：先检查文件头注释是否符合 `file-templates.md`，不符合则先修正，再改代码
   - 注释格式以 `file-templates.md` 为唯一标准

5. 写实现代码
6. 更新 barrel export + i18n + AppSidebar（如需）
7. 更新 `module-roadmap.md` 中对应功能点的状态 (❌ → ✅)

**日常改 bug / 改功能:** 直接改代码，跳过 1-3。注释规则（步骤 4）和约束检查仍适用。

### Phase 2 — 验证

```powershell
# Python
uv run ruff check engine_v2/

# TypeScript
npx tsc --noEmit   # cwd: payload-v2
```

---

## 🚀 启动速查

| 服务       | 端口           | 命令                                                                                     |
| ---------- | -------------- | ---------------------------------------------------------------------------------------- |
| Engine v2  | **8001** | `uv run python -m uvicorn engine_v2.api.app:app --reload --host 127.0.0.1 --port 8001` |
| Payload v2 | **3001** | `npm run dev -- --port 3001` (cwd: `payload-v2`)                                     |
| PostgreSQL | 5432           | `postgresql://payload:payload@127.0.0.1:5432/payload`                                  |
| Ollama     | 11434          | `http://127.0.0.1:11434`                                                               |

> ⚠️ **热部署**：Engine (`--reload`) 和 Payload (`npm run dev`) 均为热部署模式，代码保存后自动重载，**不需要手动重启服务**。禁止在工作流中执行 stop/restart 操作。

---

## 🌐 部署 (Go-Live)

| 环境 | 配置 | 说明 |
|------|------|------|
| **开发** | `.env` + `npm run dev` + `uvicorn --reload` | 本地热部署 |
| **生产** | `.env.production` + `docker compose up -d` | 容器化全栈部署 |

**生产必须项**:
- `PAYLOAD_SECRET`: 生产环境独立密钥 (用于 JWT 签发和验证)
- `DATABASE_URL`: 生产 PostgreSQL 连接串
- `CORS_ORIGINS`: 限制为生产域名 (不允许 `*`)
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`: Stripe 支付密钥
- HTTPS: Let's Encrypt 或 Cloudflare proxy
- Volume: postgres_data + chroma_persist + user_uploads 必须持久化

> 部署 Sprint 详见 `roadmap/28-sprint-go-deployment.md`

---

## ⚡ 已知坑

| 坑                                | 解决                                               |
| --------------------------------- | -------------------------------------------------- |
| BM25 空语料崩溃                   | `hybrid.py` 已加 `collection.count()` 前置检查 |
| 前端 404 路由不匹配               | URL 必须含 router prefix，见 rag-dev-v2 路由映射表 |
| `NEXT_PUBLIC_ENGINE_URL` 未设置 | 默认 `http://localhost:8001`                     |
| Engine API 无认证                 | Sprint GO-MU 修复: JWT 中间件 + API Key 旁路      |
| 10+ Collection read 全公开        | Sprint GO-MU 修复: ACL 收紧到 isLoggedIn/isAdmin   |

---

## 📦 Git 提交

```
feat: add pipeline dashboard with book selector
fix: move Ready badge to bottom-right of BookCard
refactor: extract PipelineDashboard to features/pipeline
docs: update module-roadmap status for readers
```

提交前: `npx tsc --noEmit` + `uv run ruff check engine_v2/` + roadmap 状态已更新。

---

## 🔄 文档同步规则

开发完成后检查:

- 新增文件 → `module-manifest.md` 的 Files 树是否需要更新
- 功能完成 → `module-roadmap.md` 的 ❌ → ✅
- 新增模块 → `project-structure.md` 是否已覆盖
- 新文件类型 → `file-templates.md` 是否需要新模板
