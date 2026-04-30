# Sprint GO-DEPLOY — ngrok 本地公网发布

> 目标：不做云/VPS/Docker 上线，先用本机服务 + ngrok HTTPS 隧道完成可访问、可演示、可试收费的公网发布。
>
> 前置条件：Sprint GO-MU ✅ + Sprint GO-MON ✅
> **状态**: 🚧 4/7 进行中 (ngrok 方案文档 + 环境模板 + 健康检查路径 + 恢复手册)

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 本地运行基线 | 2 | 2h | Engine + Payload 本地服务固定端口 |
| T2 ngrok 公网入口 | 3 | 3h | ngrok HTTPS + 环境变量 + Stripe webhook |
| T3 运维基础 | 2 | 2h | 健康检查 + 本地日志/恢复手册 |
| **合计** | **7** | **7h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 公网可访问 | `https://<ngrok-domain>` 可打开首页/登录页 |
| G2 | HTTPS | ngrok HTTPS URL 浏览器无安全警告 |
| G3 | 付费回调 | Stripe webhook 指向 ngrok URL 并能命中 Payload |
| G4 | 数据持久 | 本地 PostgreSQL / ChromaDB / uploads 重启后数据不丢失 |
| G5 | 可恢复 | 断线后能按文档重新启动 Engine / Payload / ngrok |

---

## [GO-DEPLOY-T1] 本地运行基线

### [GO-DEPLOY-01] 固定本地服务端口

**类型**: DevOps · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [x] Engine 使用 `127.0.0.1:8001`
- [x] Payload 使用 `localhost:3001`
- [x] 启动命令写入 `docs/deployment/ngrok-local.md`
- [ ] 启动前检查端口占用并给出处理方式

### [GO-DEPLOY-02] 本地数据持久化确认

**类型**: DevOps · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [ ] PostgreSQL 连接串使用本地持久化数据库
- [ ] ChromaDB 使用 `data/chroma_persist`
- [ ] 用户上传文件目录使用本地持久化路径
- [ ] 重启 Payload / Engine 后书籍、会话、上传文件仍可访问

---

## [GO-DEPLOY-T2] ngrok 公网入口

### [GO-DEPLOY-03] ngrok HTTPS 隧道

**类型**: DevOps · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [x] 文档记录 `ngrok http 3001`
- [ ] ngrok HTTPS URL 可打开 `/`
- [ ] ngrok HTTPS URL 可打开 `/pricing`
- [ ] 若使用免费 URL，文档说明每次重启后需要更新配置

### [GO-DEPLOY-04] ngrok 环境变量模板

**类型**: DevOps · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [x] `.env.ngrok.example` 模板文件，不含真实密钥
- [x] `.env.ngrok` 已加入 `.gitignore`
- [x] 模板包含 `PAYLOAD_PUBLIC_SERVER_URL`, `NEXT_PUBLIC_ENGINE_URL`, `ENGINE_URL`, `CORS_ORIGINS`
- [ ] 实际 `.env` 更新为当前 ngrok URL

### [GO-DEPLOY-05] Stripe webhook 指向 ngrok

**类型**: DevOps · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [x] 文档记录 webhook URL: `https://<ngrok-domain>/api/stripe/webhooks`
- [ ] Stripe Dashboard 已配置 ngrok webhook endpoint
- [ ] Stripe webhook secret 写入 `.env`
- [ ] 测试支付成功/失败回调可被 Payload 接收

---

## [GO-DEPLOY-T3] 运维基础

### [GO-DEPLOY-06] 健康检查

**类型**: DevOps · **优先级**: P1 · **预估**: 1h

**验收标准**:
- [x] Engine: `GET /engine/health` 返回 200 + 版本号
- [x] 文档记录本地 health check 命令
- [ ] Payload 首页通过 ngrok 返回 200
- [ ] `/pricing` 通过 ngrok 返回 200

### [GO-DEPLOY-07] 本地日志 + 恢复手册

**类型**: DevOps · **优先级**: P1 · **预估**: 1h

**验收标准**:
- [x] 文档说明 Engine / Payload 终端日志是主要排障来源
- [x] 文档记录常见故障：端口占用、ngrok URL 变更、CORS、Stripe webhook secret 不匹配
- [x] 演示前检查清单完成
- [x] 断线后可按文档 5 分钟内恢复公网 URL

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | GO-DEPLOY-01, GO-DEPLOY-02 | 2h | GO-MU ✅ |
| **Phase 2** | GO-DEPLOY-03, GO-DEPLOY-04, GO-DEPLOY-05 | 3h | Phase 1 |
| **Phase 3** | GO-DEPLOY-06, GO-DEPLOY-07 | 2h | Phase 2 |
