# Sprint GO-MU — 多用户加固 (Multi-User Hardening)

> 目标：让产品从"单人开发环境"变成"多用户可安全使用"。
>
> 前置条件：C4 咨询闭环基本完成
> **状态**: ✅ 10/10 已完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 用户注册 | 3 | 3h | RegisterForm + 注册路由 + Users ACL |
| T2 Engine API 认证 | 4 | 5h | JWT 验证中间件 + user_id 服务端注入 |
| T3 Collection ACL 收紧 | 2 | 2h | 10+ 个 Collection read 权限修正 |
| T4 Rate Limiting | 1 | 2h | 基础限流中间件 |
| **合计** | **10** | **12h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 无匿名访问 | 未登录用户只能访问 /login 和 /register |
| G2 | Engine API 安全 | curl 无 token 调 /engine/consulting/query 返回 401 |
| G3 | 数据隔离 | 用户 A 无法通过任何路径读取用户 B 的私有文档/会话 |
| G4 | 自助注册 | 新用户可以 注册 → 登录 → 选角色 → 开始咨询 |

---

## [GO-MU-T1] 用户自助注册

### [GO-MU-01] RegisterForm 组件

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**描述**: 创建注册表单，复用 LoginForm 的设计语言。

**验收标准**:
- [ ] 新文件 `features/auth/RegisterForm.tsx`
- [ ] 字段: email + password + confirmPassword + displayName (可选)
- [ ] 调用 Payload `POST /api/users` 创建账号
- [ ] 创建成功后自动登录，重定向到 /onboarding
- [ ] 密码校验: 最少 6 位，两次一致
- [ ] 错误处理: 邮箱已存在 → 提示去登录

### [GO-MU-02] 注册路由 + 双向链接

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**验收标准**:
- [ ] 新文件 `app/(frontend)/register/page.tsx` — 薄壳渲染 RegisterForm
- [ ] LoginForm 底部加 "没有账号? 立即注册" 链接 → /register
- [ ] RegisterForm 底部加 "已有账号? 去登录" 链接 → /login
- [ ] i18n messages 补充注册相关翻译

### [GO-MU-03] Users Collection 注册权限

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: 允许匿名用户创建账号，但限制可设置的字段。

**验收标准**:
- [ ] `Users.access.create` 改为 `() => true`
- [ ] 新增 `beforeChange` hook: 非 admin 创建时强制 `role: 'reader'`, `isOnboarded: false`
- [ ] 防止注册时设置 role/isOnboarded/selectedPersona 等敏感字段

**文件**: `collections/Users.ts` + `hooks/users/beforeChange.ts` (新增)

---

## [GO-MU-T2] Engine API 认证

### [GO-MU-04] JWT 验证中间件

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 2h

**描述**: 验证请求中的 Payload JWT token，提取 user_id 注入 request state。

**实现方案**:
```python
# engine_v2/api/middleware/auth.py
# 1. 从 Cookie (payload-token) 或 Authorization Bearer 提取 JWT
# 2. 验证签名 (PAYLOAD_SECRET)
# 3. 解码 user_id, role 注入 request.state.user
# 4. 内部调用 (Payload→Engine) 用 API Key 旁路
```

**验收标准**:
- [ ] 新文件 `engine_v2/api/middleware/auth.py`
- [ ] 支持两种认证方式: JWT Cookie + API Key Header
- [ ] 无 token 请求 → 401 Unauthorized
- [ ] 无效 token → 401
- [ ] 有效 token → `request.state.user = {id, role}`

### [GO-MU-05] 注册 Auth 中间件到 FastAPI

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 0.5h

**验收标准**:
- [ ] `app.py` 添加 auth middleware (或 Depends 全局依赖)
- [ ] 白名单: `/engine/health` 免认证
- [ ] 所有其他端点要求认证

### [GO-MU-06] Consulting 路由 user_id 改为服务端注入

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 1.5h

**描述**: 咨询端点不再从 request body 读 user_id，改从 auth middleware 获取。

**验收标准**:
- [ ] `PersonaQueryRequest` 移除 `user_id` 字段
- [ ] `/engine/consulting/query` 和 `/query/stream` 从 `request.state.user.id` 取
- [ ] `/engine/consulting/user-doc/ingest` 同理
- [ ] `/engine/consulting/user-doc/list` 的 `user_id` query param 改为从 auth 取
- [ ] `/engine/consulting/user-doc/{doc_id}` 验证 doc 属于当前用户
- [ ] 前端 api.ts 移除手动传 user_id 的逻辑

### [GO-MU-07] 创建 deps.py get_current_user 依赖

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [ ] `engine_v2/api/deps.py` 新增 `get_current_user` FastAPI Depends
- [ ] 返回 `UserContext(id, role)` Pydantic model
- [ ] admin 角色的用户可以传 `?as_user_id=X` 做用户模拟 (调试用)

---

## [GO-MU-T3] Collection 访问控制收紧

### [GO-MU-08] 管理数据 Collection 限 admin/editor

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: 系统管理类 Collection 不应对终端用户暴露。

**修改清单**:

| Collection | 当前 read | 目标 read |
|-----------|----------|-----------|
| Books | `() => true` | `isEditorOrAdmin` |
| Chunks | `() => true` | `isAdmin` |
| Chapters | `() => true` | `isAdmin` |
| Questions | `() => true` | `isEditorOrAdmin` |
| QuestionSets | `() => true` | `isEditorOrAdmin` |
| DataSources | `() => true` | `isAdmin` |
| PdfUploads | `() => true` | `isAdmin` |
| IngestTasks | — | `isAdmin` |

**验收标准**:
- [ ] 上述 Collection 的 `read` 权限已修改
- [ ] reader 角色用户无法通过 Payload REST API 读取这些数据
- [ ] 前端功能不受影响 (这些页面本身就是 admin 页面)

### [GO-MU-09] 功能数据 Collection 限已登录用户

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**修改清单**:

| Collection | 当前 read | 目标 read |
|-----------|----------|-----------|
| Media | `() => true` | `isLoggedIn` |
| Llms | `() => true` | `isLoggedIn` |
| Prompts | `() => true` | `isLoggedIn` |
| ConsultingPersonas | (检查) | `isLoggedIn` |
| GoldenDataset | (检查) | `isAdmin` |
| Evaluations | `isAdmin` | `isAdmin` (保持，后续加用户维度) |

**新增 access 函数**:
- [ ] `access/isLoggedIn.ts`: `({ req: { user } }) => !!user`

**验收标准**:
- [ ] 未登录用户无法读取任何 Collection
- [ ] 已登录用户可以读取 Personas/Llms/Media/Prompts (产品功能需要)

---

## [GO-MU-T4] Rate Limiting

### [GO-MU-10] 基础 Rate Limiting 中间件

**类型**: Backend (Engine) · **优先级**: P1 · **预估**: 2h

**描述**: 内存级 rate limiter，防止单用户刷爆 LLM API。

**规则**:
```
query 类端点: 20 次/小时/用户 (MVP 阶段)
ingest 类端点: 5 次/小时/用户
其他端点: 60 次/分钟/用户
```

**验收标准**:
- [ ] 新文件 `engine_v2/api/middleware/rate_limit.py`
- [ ] 基于 user_id + endpoint 的内存计数器 (dict + TTL)
- [ ] 超限返回 429 Too Many Requests + Retry-After header
- [ ] admin 角色不受限制

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | GO-MU-01, GO-MU-02, GO-MU-03 | 3h | 无 |
| **Phase 2** | GO-MU-04, GO-MU-05, GO-MU-07 | 3.5h | Phase 1 |
| **Phase 3** | GO-MU-06 | 1.5h | Phase 2 |
| **Phase 4** | GO-MU-08, GO-MU-09 | 2h | Phase 1 |
| **Phase 5** | GO-MU-10 | 2h | Phase 2 |
