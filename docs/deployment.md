# 本地部署指南 — Textbook RAG v2.0

- **版本**: 2.0
- **部署方式**: 本地 VSCode（开发环境）
- **生成日期**: 2026-03-22

---

## 服务架构

```
┌─────────────────────────────────────────────────────────┐
│  用户浏览器                                              │
│  http://localhost:3000  (Next.js 页面)                   │
│  http://localhost:3000/admin  (Payload Admin Panel)      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────┐
│  Payload CMS + Next.js  (Node.js, port 3000)            │
│  payload/                                                │
│  连接 PostgreSQL  ←──────────────── localhost:5432       │
└────────────────────┬────────────────────────────────────┘
                     │ Internal HTTP (127.0.0.1 only)
┌────────────────────▼────────────────────────────────────┐
│  Engine FastAPI  (Python/uv, port 8001)                 │
│  engine/                                                 │
│  连接 ChromaDB  ←───────────────── ./data/chroma_persist │
│  连接 SQLite    ←───────────────── ./data/textbook_rag.sqlite3 │
│  连接 Ollama    ←───────────────── localhost:11434       │
└─────────────────────────────────────────────────────────┘
```

---

## 服务端口总览

| 服务 | 地址 | 说明 |
|------|------|------|
| Payload CMS + Next.js | `http://localhost:3000` | 前端页面 + REST API |
| Payload Admin Panel | `http://localhost:3000/admin` | 管理后台 |
| Engine FastAPI | `http://127.0.0.1:8001` | RAG 引擎（仅内网） |
| Engine Swagger | `http://127.0.0.1:8001/docs` | API 交互文档 |
| Ollama | `http://localhost:11434` | 本地 LLM 服务 |
| ChromaDB | `./data/chroma_persist` | 向量存储（本地文件） |
| PostgreSQL | `localhost:5432` | Payload 数据库 |

---

## 前置要求

| 组件 | 版本 | 安装方法 |
|------|------|---------|
| Python | 3.12+ | [python.org](https://python.org) |
| uv | latest | `pip install uv` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| PostgreSQL | 15+ | [postgresql.org](https://postgresql.org) |
| Ollama | latest | [ollama.com](https://ollama.com) |

---

## 快速启动

### 1. 配置环境变量

```powershell
# 复制模板
Copy-Item .env.example .env
# 编辑 .env，至少填写：
#   DATABASE_URI=postgresql://postgres:your_password@localhost:5432/textbook_rag
#   PAYLOAD_SECRET=your-random-32-char-string
```

### 2. 安装依赖

```powershell
# Python 依赖（在项目根目录）
uv sync

# Node.js 依赖
cd payload; npm install; cd ..
```

### 3. 初始化数据库

```powershell
# 确保 PostgreSQL 已启动，然后 Payload 首次运行会自动建表
# 如需手动创建数据库:
# psql -U postgres -c "CREATE DATABASE textbook_rag;"
```

### 4. 启动服务

**方式 A — VSCode 任务（推荐）**

```
Ctrl+Shift+B  →  🚀 Start All (Engine + Payload)
```

同时启动 Engine API (port 8001) 和 Payload CMS (port 3000)。

**方式 B — VSCode 调试面板**

```
F5 / Run → 🚀 Start All (Engine + Payload)
```

**方式 C — 命令行（分两个终端）**

```powershell
# 终端 1: Engine API
uv run uvicorn engine.api.app:app --reload --host 127.0.0.1 --port 8001

# 终端 2: Payload CMS
cd payload; npm run dev
```

### 5. 访问服务

- 主界面: **http://localhost:3000**
- 管理后台: **http://localhost:3000/admin**
- Engine API 文档: **http://127.0.0.1:8001/docs**

---

## 健康检查

```powershell
# Engine 健康
Invoke-RestMethod http://127.0.0.1:8001/engine/health
# 期望: { "status": "ok", "version": "2.0.0" }

# Engine 策略列表
Invoke-RestMethod http://127.0.0.1:8001/engine/strategies

# Payload API
Invoke-RestMethod http://localhost:3000/api/health
```

---

## 常用命令

```powershell
# Ruff 代码检查
uv run ruff check engine/ nlp/

# Payload TypeScript 检查
Set-Location payload; npx tsc --noEmit; Set-Location ..

# Payload 构建验证
Set-Location payload; npm run build; Set-Location ..

# 更新 Python 依赖
uv sync

# 更新 Node 依赖
Set-Location payload; npm install; Set-Location ..
```

---

## VSCode 任务说明

| 任务 | 快捷键 | 说明 |
|------|--------|------|
| 🚀 Start All (Engine + Payload) | `Ctrl+Shift+B` | 并行启动两个服务 |
| Ruff Lint | Terminal → Run Task | Python 代码检查 |
| Payload Build Check | Terminal → Run Task | TS 构建验证 |

---

## 注意事项

1. **Engine 仅监听 127.0.0.1**，不对外暴露，只有 Payload 服务器端可以访问
2. **Ollama 需提前启动**并拉取模型：`ollama pull llama3.2:3b`
3. **PostgreSQL 需提前启动**，Payload 首次启动会自动创建表结构
4. **ChromaDB 数据**存在 `./data/chroma_persist/`，首次索引书籍后自动建立
5. **Azure 功能可选**，不填写 AZURE_* 变量时自动回退到 Ollama
