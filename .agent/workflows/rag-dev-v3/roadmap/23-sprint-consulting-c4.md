# Sprint C4 — 双库联合检索 + 会话绑定

> 目标：对话时自动绑定 角色知识库 + 用户私有库 进行联合检索，角色人设 Prompt 注入，会话持久化。
>
> 前置条件：Sprint C2 ✅ (角色知识库) + Sprint C3 ✅ (用户私有文档)
> **状态**: ✅ 7/7 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 数据层 | 1 | 1h | ConsultingSessions Collection |
| T2 Engine 双库检索 | 3 | 6.5h | 双库检索器 + 人设注入 + 咨询 API |
| T3 前端咨询页 | 3 | 4.5h | ConsultingChatPage + 侧栏集成 + 会话管理 |
| **合计** | **7** | **12h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 双库并行 | 从 `persona_{slug}` + `user_{userId}_{slug}` 并行检索 → RRF 融合 |
| G2 | 人设注入 | systemPrompt 从 ConsultingPersonas 读取，注入 response_synthesizer |
| G3 | 来源区分 | 检索结果标记 `source_type: "persona" | "user_doc"` |

---

## [C4-T1] 数据层

### [C4-01] 新建 ConsultingSessions Collection

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**Schema**:
```
ConsultingSessions {
  user: relationship → users (required, index)
  persona: relationship → consulting-personas (required, index)
  title: text (required)
}
```

**验收标准**:
- [x] 新文件 `collections/ConsultingSessions.ts`
- [x] Access: 用户只读自己的会话
- [x] Admin group: `Consulting`
- [x] payload.config.ts 注册

---

## [C4-T2] Engine 双库检索

### [C4-02] 双库检索器 — persona + user_doc 并行检索 + RRF 融合

**类型**: Backend · **优先级**: P0 · **预估**: 3h

**描述**: 同时从角色知识库和用户私有库检索，通过 RRF 融合排序，标记来源类型。

**实现方案**:
```python
def get_consulting_retriever(persona_slug, user_id):
    persona_retriever = get_hybrid_retriever(collection=f"persona_{persona_slug}")
    user_retriever = get_hybrid_retriever(collection=f"user_{user_id}_{persona_slug}")
    # QueryFusionRetriever 融合两个 retriever
    # 结果中标记 source_type 区分来源
```

**验收标准**:
- [x] 并行检索两个 collection → RRF 融合
- [x] 每个 source 标记 `source_type: "persona" | "user_doc"`
- [x] 用户私有库为空时，仅从角色库检索 (不报错)
- [x] 角色库为空时，仅从用户库检索 (不报错)

**文件**: `engine_v2/retrievers/consulting.py` (新增)

### [C4-03] 人设 Prompt 注入

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 查询时从 Payload 读取角色的 systemPrompt，注入到 response_synthesizer。

**验收标准**:
- [x] 从 Payload `/api/consulting-personas?where[slug][equals]={slug}` 读取 systemPrompt
- [x] 注入到 TreeSummarize / CompactAndRefine 的 system_prompt 参数
- [x] 缓存角色 Prompt (进程级 dict cache，避免每次查询都读 DB)

**文件**: `engine_v2/response_synthesizers/consulting.py` (新增)

### [C4-04] Engine API: POST /engine/consulting/query/stream

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 咨询专用 SSE 流式查询端点。

**请求**:
```json
{
  "question": "劳动合同解除需要什么条件？",
  "user_id": 1,
  "persona_slug": "lawyer",
  "top_k": 5
}
```

**SSE 事件序列**: 复用现有 retrieval_done → token → done 模式

**验收标准**:
- [x] 新路由 `POST /engine/consulting/query/stream`
- [x] 自动绑定双库检索器 + 人设 Prompt
- [x] 来源标记 source_type
- [x] 复用现有 SSE 事件格式

**文件**: `engine_v2/api/routes/consulting.py` (新增)

---

## [C4-T3] 前端咨询页

### [C4-05] ConsultingChatPage — 咨询对话界面

**类型**: Frontend · **优先级**: P0 · **预估**: 2.5h

**描述**: 咨询专用对话页面，复用 ChatPage 布局，数据源改为咨询会话 + 咨询 API。

**验收标准**:
- [x] 咨询模式集成到统一 ChatPanel (mode=consulting)
- [x] SSE 流式显示回答 (queryConsultingStream)
- [x] Citation chips 区分来源 (source_type)
- [x] `/consulting` 路由 → redirect `/chat?mode=consulting`

### [C4-06] 侧栏集成 — UserDocsPanel + PersonaSelectorPanel

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: 咨询页面右侧栏集成文档管理和角色切换。

**验收标准**:
- [x] 右侧栏 ConsultingSidebar 包含 UserDocsPanel
- [x] 切换角色后自动触发 sidebar 刷新
- [x] 可折叠侧栏 (onClose)

### [C4-07] 会话自动创建/续接

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: 进入咨询页时自动创建或恢复最近会话。

**验收标准**:
- [x] 进入 consulting 模式 → 自动查询最近同 persona 会话
- [x] 无会话 → 首次提问时自动创建 (ChatPanel.createSession)
- [x] 有会话 → 加载历史消息
- [x] 新消息关联到 chat-sessions (mode=consulting)

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | C4-01 | 1h | C2+C3 完成 |
| **Phase 2** | C4-02, C4-03 | 4.5h | Phase 1 |
| **Phase 3** | C4-04 | 2h | Phase 2 |
| **Phase 4** | C4-05, C4-06, C4-07 | 4.5h | Phase 3 |
