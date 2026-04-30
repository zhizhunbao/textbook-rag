# Sprint 4 — 基建补全（约 2 周）

## 概览

| Epic | Story 数 | 预估总工时 |
|------|----------|-----------|
| chunking 前端 | 3 | 8h |
| embeddings 前端 | 3 | 8h |
| llms 增强 | 2 | 5h |
| access 权限 UI | 3 | 8h |
| **合计** | **11** | **29h** |

## 质量门禁（每个 Story 交付前必做）

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | **模块归属判断** | 同 Sprint 1。重点：`chunking` / `embeddings` / `access` 均为全新模块，严格遵循 `features/engine/<module>/` 骨架；`llms` 增强在现有目录内扩展 |
| G2 | **文件注释合规** | 同 Sprint 1。重点：新模块每个文件（index.ts §3.20、types.ts §3.21、api.ts §3.22、页面 §3.25）均需完整模板注释；Python API 路由用 §1.7 |

---

## Epic: chunking 前端 (P3)

### [S4-BE-01] chunking API 路由

**类型**: Backend · **优先级**: P3 · **预估**: 2h

**描述**: 分块 CRUD + 参数配置 API。

**验收标准**:
- [ ] 创建 `engine_v2/api/routes/chunking.py`
- [ ] GET /engine/chunking/{book_id} 返回分块结果
- [ ] POST /engine/chunking/config 更新分块参数
- [ ] G1 ✅ 路由在 `engine_v2/api/routes/`
- [ ] G2 ✅ 文件头注释符合 §1.7 API 路由模板

**依赖**: readers ✅
**文件**: `engine_v2/api/routes/chunking.py`

### [S4-FE-01] chunking 模块骨架

**类型**: Frontend · **优先级**: P3 · **预估**: 2h

**描述**: 新建 chunking 前端模块骨架。

**验收标准**:
- [ ] 创建 `features/engine/chunking/index.ts`
- [ ] 创建 `features/engine/chunking/types.ts`
- [ ] 创建 `features/engine/chunking/api.ts`
- [ ] G1 ✅ 遵循 `features/engine/<module>/` 标准结构
- [ ] G2 ✅ index.ts §3.20，types.ts §3.21，api.ts §3.22

**依赖**: 无
**文件**: `features/engine/chunking/index.ts`, `features/engine/chunking/types.ts`, `features/engine/chunking/api.ts`

### [S4-FE-02] 分块预览 + 参数调节页

**类型**: Frontend · **优先级**: P3 · **预估**: 4h

**描述**: 可视化分块结果 + 参数调整面板。

**验收标准**:
- [ ] 创建 `features/engine/chunking/components/ChunkingPage.tsx`
- [ ] 分块结果列表 + 文本预览
- [ ] 参数调节 (chunk_size, overlap, strategy)
- [ ] G1 ✅ 在 `features/engine/chunking/components/`
- [ ] G2 ✅ 页面符合 §3.25 Engine 页面模板

**依赖**: [S4-BE-01], [S4-FE-01]
**文件**: `features/engine/chunking/components/ChunkingPage.tsx`

---

## Epic: embeddings 前端 (P3)

### [S4-BE-02] embeddings API 路由

**类型**: Backend · **优先级**: P3 · **预估**: 2h

**描述**: 嵌入模型管理 + 缓存状态 API。

**验收标准**:
- [ ] 创建 `engine_v2/api/routes/embeddings.py`
- [ ] GET /engine/embeddings/models 返回可用模型
- [ ] GET /engine/embeddings/cache 返回缓存状态
- [ ] G1 ✅ 路由在 `engine_v2/api/routes/`
- [ ] G2 ✅ 文件头注释符合 §1.7 API 路由模板

**依赖**: llms ✅
**文件**: `engine_v2/api/routes/embeddings.py`

### [S4-FE-03] embeddings 模块骨架

**类型**: Frontend · **优先级**: P3 · **预估**: 2h

**描述**: 新建 embeddings 前端模块骨架。

**验收标准**:
- [ ] 创建 `features/engine/embeddings/index.ts`
- [ ] 创建 `features/engine/embeddings/types.ts`
- [ ] 创建 `features/engine/embeddings/api.ts`
- [ ] G1 ✅ 遵循 `features/engine/<module>/` 标准结构
- [ ] G2 ✅ index.ts §3.20，types.ts §3.21，api.ts §3.22

**依赖**: 无
**文件**: `features/engine/embeddings/index.ts`, `features/engine/embeddings/types.ts`, `features/engine/embeddings/api.ts`

### [S4-FE-04] 嵌入管理 UI

**类型**: Frontend · **优先级**: P3 · **预估**: 4h

**描述**: 模型切换 + 维度配置 + 缓存监控页面。

**验收标准**:
- [ ] 创建 `features/engine/embeddings/components/EmbeddingsPage.tsx`
- [ ] 模型切换下拉 + 维度配置
- [ ] 缓存命中率/大小/清理按钮
- [ ] G1 ✅ 在 `features/engine/embeddings/components/`
- [ ] G2 ✅ 页面符合 §3.25 Engine 页面模板

**依赖**: [S4-BE-02], [S4-FE-03]
**文件**: `features/engine/embeddings/components/EmbeddingsPage.tsx`

---

## Epic: llms 增强 (P4)

### [S4-FE-05] 令牌统计

**类型**: Frontend · **优先级**: P4 · **预估**: 3h

**描述**: token 用量统计面板。

**验收标准**:
- [ ] 更新 `features/engine/llms/` 增加统计组件
- [ ] 按模型/时间段统计 token 用量
- [ ] G1 ✅ 在现有 `features/engine/llms/` 内扩展
- [ ] G2 ✅ 新组件注释符合 §3.12

**依赖**: 无
**文件**: `features/engine/llms/components/`

### [S4-BE-03] 故障降级

**类型**: Backend · **优先级**: P4 · **预估**: 2h

**描述**: LLM 自动 fallback 机制。

**验收标准**:
- [ ] 更新 `engine_v2/llms/resolver.py` 增加 fallback 逻辑
- [ ] 主模型超时/错误时自动切换备选
- [ ] G1 ✅ 在现有 `engine_v2/llms/` 内扩展
- [ ] G2 ✅ 注释更新符合 §1.2 模块实现模板

**依赖**: 无
**文件**: `engine_v2/llms/resolver.py`

---

## Epic: access 权限 UI (P4)

### [S4-FE-06] access 模块骨架

**类型**: Frontend · **优先级**: P4 · **预估**: 2h

**描述**: 新建 access 前端模块骨架。

**验收标准**:
- [ ] 创建 `features/access/index.ts`
- [ ] 创建 `features/access/types.ts`
- [ ] G1 ✅ 独立功能模块在 `features/access/`（非 engine 子模块）
- [ ] G2 ✅ index.ts 符合 §3.20，types.ts 符合 §3.19

**依赖**: auth ✅
**文件**: `features/access/index.ts`, `features/access/types.ts`

### [S4-FE-07] 权限矩阵 UI

**类型**: Frontend · **优先级**: P4 · **预估**: 4h

**描述**: 角色列表 + 权限矩阵可视化。

**验收标准**:
- [ ] 创建 `features/access/AccessPage.tsx`
- [ ] 角色列表 (admin/editor/viewer)
- [ ] 权限矩阵复选框表格
- [ ] G1 ✅ 在 `features/access/`
- [ ] G2 ✅ 页面符合 §3.18 功能页面模板

**依赖**: [S4-FE-06]
**文件**: `features/access/AccessPage.tsx`

### [S4-FE-08] 角色管理

**类型**: Frontend · **优先级**: P4 · **预估**: 2h

**描述**: 角色 CRUD + 用户角色分配。

**验收标准**:
- [ ] 角色创建/编辑/删除
- [ ] 用户角色分配下拉
- [ ] G1 ✅ 在 `features/access/`
- [ ] G2 ✅ 注释符合已有模板

**依赖**: [S4-FE-07]
**文件**: `features/access/`
