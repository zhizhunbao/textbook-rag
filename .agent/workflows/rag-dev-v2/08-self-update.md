---
description: rag-dev-v2 工作流自更新规则 — 开发过程中自动保持工作流与项目同步
---

# 🔄 v2 工作流自更新规则

## 何时触发自更新

在以下情况下，AI 助手应主动检查并更新 rag-dev-v2 工作流文件：

1. **新增 engine_v2 子包** → 更新 `01-project-structure.md` + `02-architecture.md` 三层对齐表
2. **新增 Engine API 路由** → 更新 `01-project-structure.md` routes 列表
3. **新增 Payload Collection** → 更新 `01-project-structure.md` collections 列表
4. **新增 features/engine/ 子模块** → 更新 `01-project-structure.md` + `02-architecture.md`
5. **新增前端页面** → 更新 `01-project-structure.md` 的 engine/ 子页列表
6. **修改核心规则/约定** → 更新 `03-core-rules.md`
7. **修改启动/运行方式** → 更新 `05-run-and-debug.md`
8. **新增 LlamaIndex 依赖** → 更新 `06-llamaindex-reference.md`
9. **新增侧边栏导航** → 更新 `01-project-structure.md` + 提醒更新 i18n

## 更新方式

### 自动触发（推荐）

每次 v2 开发任务结束、代码提交前，AI 应执行以下检查：

```
检查清单:
□ 是否新增了 engine_v2/ 下的子目录？→ 更新 01 + 02
□ 是否新增了 engine_v2/api/routes/ 下的文件？→ 更新 01
□ 是否新增了 payload-v2/src/collections/ 下的文件？→ 更新 01
□ 是否新增了 features/engine/ 下的子目录？→ 更新 01 + 02
□ 是否新增了 app/(frontend)/engine/ 下的页面？→ 更新 01
□ 是否引入了新的 LlamaIndex 组件？→ 更新 06
□ 是否引入了新的开发规则或约定？→ 更新 03
□ 是否修改了启动命令或环境配置？→ 更新 05
□ 是否修改了端口号？→ 更新 05 端口速查表
```

### 手动触发

用户可以说：
- "更新 rag-dev-v2 工作流" 或 "/rag-dev-v2 update"
- AI 会扫描项目目录，对比工作流文件，自动修正不一致之处

## 更新原则

1. **只更新事实性内容**（目录树、文件列表、路由列表、三层对齐表）
2. **不修改设计决策**（核心规则、约定、路线图方向）
3. **保持格式一致**（与现有 md 文件风格一致）
4. **保持三层同步** — 新增子模块时必须同时更新 01 (目录树) 和 02 (对齐表)
5. **在 commit message 中注明** — `chore: update rag-dev-v2 workflow (auto-sync)`

## 示例：新增 engine_v2/postprocessor/ 后的自更新

```diff
# 01-project-structure.md
 │   ├── retrievers/            # ← llama_index.core.retrievers
 │   │   └── hybrid.py
+│   ├── postprocessor/         # ← llama_index.core.postprocessor
+│   │   └── similarity_filter.py  # SimilarityPostprocessor wrapper

# 02-architecture.md 三层对齐表
+│ llama_index.core.postprocessor│ engine_v2/postprocessor/ │ features/engine/postprocessor│
```
