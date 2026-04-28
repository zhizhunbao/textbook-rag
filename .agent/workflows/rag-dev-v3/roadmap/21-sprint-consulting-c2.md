# Sprint C2 — 角色管理 + 角色知识库

> 目标：管理员可管理咨询角色，每个角色绑定独立 ChromaDB 知识库，支持 PDF 批量灌入。
>
> 前置条件：Sprint C1 ✅ ConsultingPersonas 集合 + Users 扩展已完成
> **状态**: ✅ 7/7 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Engine 角色知识库 | 3 | 4.5h | personas 模块 + 灌入 API + 统计 API |
| T2 Admin 管理页面 | 2 | 4h | PersonasPage + PersonaIngestPanel |
| T3 用户角色切换 | 2 | 1.5h | PersonaSelectorPanel + afterChange hook |
| **合计** | **7** | **10h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | Engine: `engine_v2/personas/`；Frontend: `features/engine/personas/` |
| G2 | 数据流方向 | Engine 处理 PDF → 写 ChromaDB + 写状态到 Payload；前端从 Payload 读 |
| G3 | 复用管线 | 灌入复用 `readers/` + `chunking/` + `embeddings/` + `ingestion/` |
| G4 | 隔离保证 | 每个角色一个 ChromaDB collection：`persona_{slug}` |
| G5 | 文件格式 | 仅支持 PDF |

---

## [C2-T1] Engine 角色知识库

### [C2-01] Engine personas/ 模块 — 角色知识库注册逻辑

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 新模块管理角色知识库生命周期：创建 ChromaDB collection、统计元数据、删除。

**验收标准**:
- [x] 新文件 `engine_v2/personas/__init__.py`, `engine_v2/personas/registry.py`
- [x] `ensure_persona_collection(slug)` 幂等创建 ChromaDB collection
- [x] `get_persona_stats(slug)` 返回 chunk_count / doc_count
- [x] collection 名 = `persona_{slug}`

### [C2-02] Engine API: POST /engine/personas/{slug}/ingest

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 管理员上传 PDF 到角色知识库。复用现有 ingestion 管线，目标 collection 为 `persona_{slug}`。

**验收标准**:
- [x] 端点已存在于 `engine_v2/api/routes/consulting.py`（POST /engine/consulting/ingest）
- [x] 上传 PDF → 切片 → 向量化 → 写入 `persona_{slug}` collection
- [x] 返回 `{ status, chunk_count, doc_name }`
- [x] 复用现有 readers / chunking / embeddings；仅接受 PDF

### [C2-03] Engine API: GET /engine/personas/{slug}/stats

**类型**: Backend · **优先级**: P1 · **预估**: 1h

**描述**: 返回角色知识库统计信息 (chunk_count, doc_count, embedding_dim, status)。

**验收标准**:
- [x] collection 不存在时返回 `{ status: "empty", chunk_count: 0 }`
- [x] 复用 `engine_v2/personas/registry.py`

---

## [C2-T2] Admin 管理页面

### [C2-04] PersonasPage — 角色列表 + 状态面板

**类型**: Frontend · **优先级**: P1 · **预估**: 2h

**描述**: Engine 控制面板下的角色管理页，展示所有角色及其知识库状态。

**验收标准**:
- [x] 新目录 `features/engine/personas/` 含 index.ts / types.ts / api.ts / usePersonaAdmin.ts
- [x] PersonaCard: icon + name + description + status badge + chunk_count
- [x] status badge: Ready (绿) / Empty (灰) / Processing (黄)

### [C2-05] PersonaIngestPanel — PDF 上传到角色知识库

**类型**: Frontend · **优先级**: P1 · **预估**: 2h

**描述**: 管理员选择 PDF 上传到角色知识库，显示进度和结果。

**验收标准**:
- [x] 文件选择器仅接受 `.pdf`
- [x] 调用 `POST /engine/consulting/ingest`
- [x] 上传进度条 + 完成后显示 chunk 统计
- [x] 支持多文件顺序上传

---

## [C2-T3] 用户角色切换

### [C2-06] PersonaSelectorPanel — 角色切换组件

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: 可复用角色选择下拉组件。

**验收标准**:
- [x] 新文件 `features/shared/components/PersonaSelectorPanel.tsx`
- [x] 下拉菜单展示启用角色 (icon + name)
- [x] 选中后 PATCH `/api/users/{id}` 更新 `selectedPersona`

### [C2-07] ConsultingPersonas afterChange hook — 自动初始化 ChromaDB

**类型**: Backend (Payload) · **优先级**: P1 · **预估**: 0.5h

**描述**: 创建新角色时自动调 Engine API 初始化 ChromaDB collection。

**验收标准**:
- [x] 新文件 `hooks/consulting-personas/afterChange.ts`
- [x] 创建角色 → 自动初始化 ChromaDB collection
- [x] 失败时 log 不阻塞

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | C2-01 | 1.5h | C1 完成 |
| **Phase 2** | C2-02, C2-03 | 3h | Phase 1 |
| **Phase 3** | C2-04, C2-05 | 4h | Phase 2 |
| **Phase 4** | C2-06, C2-07 | 1.5h | Phase 1 |
