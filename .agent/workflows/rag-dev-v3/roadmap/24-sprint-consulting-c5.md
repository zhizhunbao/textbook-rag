# Sprint C5 — 打磨 + 扩展

> 目标：交互打磨、角色扩展向导、咨询历史、权限收紧。
>
> 前置条件：Sprint C4 ✅ 端到端咨询体验闭环已完成
> **状态**: ✅ 5/6 完成 (C5-03 deferred — use Payload Admin UI)

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 交互打磨 | 2 | 2h | 角色切换动效 + 来源着色 |
| T2 管理增强 | 2 | 3h | 新增角色向导 + 咨询历史 |
| T3 安全收紧 | 2 | 1h | 路由权限 + 文件限制 |
| **合计** | **6** | **6h** |

---

### [C5-01] 角色切换动效 + 会话自动切换

**类型**: Frontend · **优先级**: P2 · **预估**: 1h

**验收标准**:
- [x] 切换角色时平滑过渡动画 (fade + slide) — via CSS transition
- [x] 自动切换到对应角色的最近会话 — C4-07 effect
- [x] 文档列表自动刷新为新角色下的文档 — useUserDocs(personaSlug)

### [C5-02] 来源标签着色 — 角色知识库 vs 个人文档

**类型**: Frontend · **优先级**: P2 · **预估**: 1h

**验收标准**:
- [x] Citation chip: 角色知识库 → 蓝色；个人文档 → 橙色 (SOURCE_TYPE_TAG)
- [x] Tooltip 显示来源类型 + 文件名
- [x] 复用 EvalScoreCard 配色体系

### [C5-03] 新增角色向导 — Admin 创建角色 + 初始化知识库

**类型**: Frontend · **优先级**: P2 · **预估**: 1.5h

**验收标准**:
- [ ] Admin PersonasPage 新增按钮打开创建表单
- [ ] 表单: name / slug / icon / description / systemPrompt
- [ ] 提交后自动创建 Collection + 初始化 ChromaDB
- [ ] slug 自动生成 (从 name kebab-case)

### [C5-04] 咨询历史列表 — 按角色分组

**类型**: Frontend · **优先级**: P2 · **预估**: 1.5h

**验收标准**:
- [x] 统一 chat history 已按 mode/persona 存储
- [x] AppSidebar 历史列表显示 Briefcase 图标 + personaName 标签
- [x] 点击会话加载历史消息 (复用 ChatPage session= 路由)
- [x] 支持删除会话 (deleteSession)

### [C5-05] 访问控制收紧

**类型**: Frontend · **优先级**: P2 · **预估**: 0.5h

**验收标准**:
- [x] 非 admin 不可访问 `/engine/*` 路由 — admin nav group gated
- [x] AppSidebar 对非 admin 隐藏 Engine 菜单组 + question_gen

### [C5-06] PDF 上传限制

**类型**: Backend + Frontend · **优先级**: P2 · **预估**: 0.5h

**验收标准**:
- [x] 单文件 ≤ 50MB — MAX_FILE_SIZE validation
- [x] 每用户每角色 ≤ 20 个文档 — MAX_DOCS_PER_PERSONA
- [x] 仅接受 `.pdf` MIME type — file.type + extension check
- [x] 超限时前端显示友好提示 — uploadError state

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | C5-01, C5-02 | 2h | C4 完成 |
| **Phase 2** | C5-03, C5-04 | 3h | C4 完成 |
| **Phase 3** | C5-05, C5-06 | 1h | 无特殊依赖 |
