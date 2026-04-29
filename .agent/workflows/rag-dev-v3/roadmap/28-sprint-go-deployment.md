# Sprint GO-DEPLOY — 部署上线

> 目标：从 localhost 到公网可访问、可收费。
>
> 前置条件：Sprint GO-MU ✅ + Sprint GO-MON ✅ (或并行)
> **状态**: ❌ 0/7 未开始

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 容器化 | 2 | 4h | Dockerfile + Docker Compose |
| T2 云部署 | 3 | 5h | 云平台 + 域名 + HTTPS |
| T3 运维基础 | 2 | 3h | 健康检查 + 日志 + 错误报警 |
| **合计** | **7** | **12h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 公网可访问 | `https://your-domain.com` 可打开登录页 |
| G2 | 数据持久 | 重启容器后数据不丢失 |
| G3 | HTTPS | SSL 证书有效，浏览器无安全警告 |
| G4 | 可恢复 | 服务宕机后自动重启 |

---

## [GO-DEPLOY-T1] 容器化

### [GO-DEPLOY-01] Dockerfile (Engine + Payload)

**类型**: DevOps · **优先级**: P0 · **预估**: 2h

**验收标准**:
- [ ] `engine_v2/Dockerfile`: Python 3.11 + uv + MinerU 依赖
- [ ] `payload-v2/Dockerfile`: Node 20 + npm build
- [ ] 多阶段构建: build stage + production stage
- [ ] 镜像大小 < 1.5GB (Engine), < 500MB (Payload)

### [GO-DEPLOY-02] Docker Compose 全栈编排

**类型**: DevOps · **优先级**: P0 · **预估**: 2h

**验收标准**:
- [ ] `docker-compose.yml`: engine + payload + postgres + chromadb
- [ ] Volume mounts: postgres data + chroma persist + user uploads
- [ ] Environment variables 从 `.env.production` 读取
- [ ] 健康检查 (healthcheck) 配置
- [ ] `docker compose up -d` 一键启动全栈
- [ ] (可选) Ollama 服务容器或外部 GPU 连接

---

## [GO-DEPLOY-T2] 云部署

### [GO-DEPLOY-03] 云平台部署

**类型**: DevOps · **优先级**: P0 · **预估**: 2h

**方案选项** (根据预算选一):
- A) Railway / Render — 简单，~$30/月
- B) VPS (Contabo/Hetzner) — 便宜，~$10/月，需自己配 nginx
- C) AWS EC2 / GCP VM — 灵活，按用量付费

**验收标准**:
- [ ] 所有服务在云上运行
- [ ] PostgreSQL 持久化存储
- [ ] ChromaDB 持久化存储
- [ ] 用户上传文件持久化存储

### [GO-DEPLOY-04] 域名 + HTTPS

**类型**: DevOps · **优先级**: P0 · **预估**: 1.5h

**验收标准**:
- [ ] 域名解析到服务器 IP
- [ ] Let's Encrypt SSL 自动续签 (或 Cloudflare proxy)
- [ ] HTTP → HTTPS 自动重定向
- [ ] CORS 配置更新为生产域名

### [GO-DEPLOY-05] .env.production 环境变量

**类型**: DevOps · **优先级**: P0 · **预估**: 1.5h

**验收标准**:
- [ ] `.env.production.example` 模板文件 (不含真实密钥)
- [ ] 关键变量: DATABASE_URL, PAYLOAD_SECRET, STRIPE_SECRET_KEY, OPENAI_API_KEY
- [ ] 敏感变量不入 Git (`.gitignore`)
- [ ] 生产环境 CORS_ORIGINS 限制为具体域名

---

## [GO-DEPLOY-T3] 运维基础

### [GO-DEPLOY-06] 健康检查 + 自动重启

**类型**: DevOps · **优先级**: P1 · **预估**: 1.5h

**验收标准**:
- [ ] Engine: `GET /engine/health` 返回 200 + 版本号 + 依赖状态
- [ ] Payload: 内置 health check
- [ ] Docker restart policy: `unless-stopped`
- [ ] (可选) 外部监控: UptimeRobot / Healthchecks.io

### [GO-DEPLOY-07] 日志 + 错误报警

**类型**: DevOps · **优先级**: P1 · **预估**: 1.5h

**验收标准**:
- [ ] 日志输出到 stdout (Docker 默认采集)
- [ ] loguru 配置: 生产环境 JSON 格式
- [ ] (可选) Sentry 集成: 未捕获异常自动上报
- [ ] 关键事件邮件通知: 支付成功/失败, 服务宕机

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | GO-DEPLOY-01, GO-DEPLOY-02 | 4h | GO-MU ✅ |
| **Phase 2** | GO-DEPLOY-03, GO-DEPLOY-04, GO-DEPLOY-05 | 5h | Phase 1 |
| **Phase 3** | GO-DEPLOY-06, GO-DEPLOY-07 | 3h | Phase 2 |
