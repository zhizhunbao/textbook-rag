# Sprint C3 — 用户私有文档管理

> 目标：用户可上传个人 PDF 文档，自动入库到隔离的私有向量空间 (按用户×角色维度隔离)。
>
> 前置条件：Sprint C1 ✅ + Sprint C2 ✅
> **状态**: ✅ 7/7 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 数据层 | 2 | 1.5h | UserDocuments Collection + Access Control |
| T2 Engine 用户文档模块 | 3 | 3.5h | user_docs 模块 + upload/stats/delete API |
| T3 前端文档面板 | 2 | 4h | UserDocsPanel + 文件上传 |
| **合计** | **7** | **9h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 隔离保证 | 用户私有库 collection 名 = `user_{userId}_{personaSlug}` |
| G2 | 数据隔离 | Users 只能 read/update/delete 自己的文档 |
| G3 | 文件格式 | 仅支持 PDF |

---

## [C3-T1] 数据层

### [C3-01] 新建 UserDocuments Collection

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**Schema**:
```
UserDocuments {
  user: relationship → users (required, index)
  persona: relationship → consulting-personas (required, index)
  fileName: text (required)
  fileUrl: text (required) — 存储路径
  status: select [pending, processing, ready, error] (default: pending)
  chromaCollection: text — "user_{userId}_{personaSlug}"
  chunkCount: number (default: 0)
  errorMessage: text (optional)
}
```

**验收标准**:
- [x] `collections/UserDocuments.ts` 已存在
- [x] Admin group: `Consulting`
- [x] payload.config.ts 已注册
- [x] Access: 用户只读自己的，admin 读全部

### [C3-02] UserDocuments Access Control

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 0.5h

**验收标准**:
- [x] `read`: 用户只读 `{ user: { equals: user.id } }`，admin 读全部
- [x] `create`: 已认证用户
- [x] `update/delete`: 仅 owner 或 admin

---

## [C3-T2] Engine 用户文档模块

### [C3-03] Engine user_docs/ 模块 — 用户文档入库逻辑

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 管理用户私有文档的 ChromaDB collection 生命周期。

**验收标准**:
- [x] 新文件 `engine_v2/user_docs/__init__.py`, `engine_v2/user_docs/manager.py`
- [x] `ensure_user_collection(user_id, persona_slug)` 幂等创建
- [x] `user_collection_name(user_id, persona_slug)` 構建 collection 名
- [x] collection 名 = `user_{userId}_{personaSlug}`
- [x] 复用 readers / chunking / embeddings

### [C3-04] Engine API: POST /engine/user-docs/upload + GET stats

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**请求**: `POST /engine/user-docs/upload` (multipart: file + userId + personaSlug)

**验收标准**:
- [x] 端点已实现在 `engine_v2/api/routes/consulting.py`
- [x] 上传 PDF → 异步入库 (立即返回 pending 状态)
- [x] `GET /engine/consulting/user-doc/list` 返回统计
- [x] 仅接受 PDF

### [C3-05] Engine API: DELETE /engine/user-docs/{docId}

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**验收标准**:
- [x] 删除文档 + 从 ChromaDB 清理对应向量
- [x] 更新 Payload UserDocuments 状态

---

## [C3-T3] 前端文档面板

### [C3-06] UserDocsPanel — 文件上传区 + 文档列表

**类型**: Frontend · **优先级**: P0 · **预估**: 2.5h

**Layout**:
```
┌──────────────────────────────────┐
│ 我的文档 (法律顾问)              │
├──────────────────────────────────┤
│ [拖拽 PDF 或 点击上传]           │
│                                  │
│  ✅ 劳动合同.pdf     234 chunks  │
│  🔄 公司章程.pdf     处理中...   │
│  ❌ 损坏文件.pdf     解析失败    │
│                                  │
│ 总计: 234 chunks                 │
└──────────────────────────────────┘
```

**验收标准**:
- [x] 新目录 `features/consulting/user-docs/`
- [x] 新文件 `UserDocsPanel.tsx`, `useUserDocs.ts`, `index.ts`
- [x] PDF 拖拽上传 + 文件选择
- [x] 文档列表 + status badge (pending/processing/indexed/error)
- [x] 删除按钮 + 确认弹窗

### [C3-07] useUserDocs hook — 数据获取

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**验收标准**:
- [x] 从 `/api/user-documents` 读取用户文档列表 (自动按当前用户过滤)
- [x] `upload(file)` 调用 Engine API
- [x] `remove(docId)` 调用 Engine API
- [x] 返回 `{ docs, loading, error, upload, remove, refetch }`

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | C3-01, C3-02 | 1.5h | C1+C2 完成 |
| **Phase 2** | C3-03, C3-04, C3-05 | 3.5h | Phase 1 |
| **Phase 3** | C3-06, C3-07 | 4h | Phase 2 |
