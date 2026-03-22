# Step 9: 本地部署 (VSCode)

## 阶段信息

- **阶段**: `deployment` - 本地开发部署
- **Skill**: `dev-senior_devops`
- **输入**: `backend/`, `engine/`, `payload/`, `.vscode/`
- **产出物**: `docs/v2.0/deployment.md`、更新后的 `.vscode/tasks.json` / `.vscode/launch.json`

---

## 执行步骤

### 1. 加载上下文

读取并分析：

- `docs/v2.0/architecture/system-architecture.md` - 服务拓扑
- `docs/v2.0/review-report.md` - 确认已通过审查
- `.vscode/tasks.json` - 现有 VSCode Tasks
- `.vscode/launch.json` - 现有 Launch 配置
- `.env.example` - 环境变量需求

---

### 2. 前置检查

#### 2.1 环境变量

确认 `.env` 文件存在且包含必要配置：

```bash
# 检查 .env 是否存在
Test-Path .env

# 对照 .env.example 检查缺失变量
Get-Content .env.example | Where-Object { $_ -match "^[A-Z]" } | ForEach-Object {
    $key = ($_ -split "=")[0]
    if (-not (Get-Content .env -ErrorAction SilentlyContinue | Select-String "^$key=")) {
        Write-Warning "缺失: $key"
    }
}
```

必须存在的变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URI` | Payload PostgreSQL 连接 | `postgresql://user:pass@localhost:5432/textbook` |
| `PAYLOAD_SECRET` | Payload JWT 密钥 | 随机 32 字符串 |
| `ENGINE_URL` | Engine FastAPI 地址 | `http://127.0.0.1:8001` |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化路径 | `./data/chroma` |
| `OLLAMA_BASE_URL` | Ollama API 地址 | `http://localhost:11434` |

#### 2.2 依赖服务检查

```powershell
# PostgreSQL 是否运行
Test-NetConnection -ComputerName localhost -Port 5432

# Ollama 是否运行
Invoke-RestMethod http://localhost:11434/api/tags -ErrorAction SilentlyContinue

# ChromaDB 数据目录是否存在
Test-Path ./data/chroma
```

---

### 3. 更新 `.vscode/tasks.json`

基于 v2.0 架构（Payload + Engine 两个服务），更新 Tasks：

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Engine API",
      "type": "shell",
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-Command",
        "$conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue; if ($conn) { $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }; uv run uvicorn engine.api.app:app --reload --host 127.0.0.1 --port 8001"
      ],
      "options": { "cwd": "${workspaceFolder}" },
      "isBackground": true,
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "clear": true,
        "group": "textbook-rag"
      }
    },
    {
      "label": "Start Payload CMS",
      "type": "shell",
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-Command",
        "$conn = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue; if ($conn) { $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }; npm run dev"
      ],
      "options": { "cwd": "${workspaceFolder}/payload" },
      "isBackground": true,
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "clear": true,
        "group": "textbook-rag"
      }
    },
    {
      "label": "🚀 Start All (Engine + Payload)",
      "dependsOn": ["Start Engine API", "Start Payload CMS"],
      "dependsOrder": "parallel",
      "problemMatcher": [],
      "group": {
        "kind": "build",
        "isDefault": true
      }
    },
    {
      "label": "Ruff Lint",
      "type": "shell",
      "command": "uv run ruff check engine/ backend/ nlp/",
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": [],
      "group": "test"
    },
    {
      "label": "Payload Build Check",
      "type": "shell",
      "command": "npm run build",
      "options": { "cwd": "${workspaceFolder}/payload" },
      "problemMatcher": ["$tsc"],
      "group": "test"
    }
  ]
}
```

**写入路径**: `.vscode/tasks.json`

---

### 4. 更新 `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Engine API",
      "type": "node-terminal",
      "request": "launch",
      "command": "powershell -NoProfile -Command \"$conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue; if ($conn) { $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }; uv run uvicorn engine.api.app:app --reload --host 127.0.0.1 --port 8001\"",
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Payload CMS",
      "type": "node-terminal",
      "request": "launch",
      "command": "npm run dev",
      "cwd": "${workspaceFolder}/payload"
    }
  ],
  "compounds": [
    {
      "name": "🚀 Start All (Engine + Payload)",
      "configurations": ["Engine API", "Payload CMS"],
      "stopAll": true
    }
  ]
}
```

**写入路径**: `.vscode/launch.json`

---

### 5. 启动验证

按顺序启动并验证：

#### 5.1 启动 Engine API

```powershell
# 方式 1: VSCode 任务 (Ctrl+Shift+B → "Start Engine API")
# 方式 2: 命令行
uv run uvicorn engine.api.app:app --reload --host 127.0.0.1 --port 8001
```

验证：

```powershell
# 健康检查
Invoke-RestMethod http://127.0.0.1:8001/engine/health

# 期望响应
# { "status": "ok", "chroma": "ok", "ollama": "ok" }

# 策略列表
Invoke-RestMethod http://127.0.0.1:8001/engine/strategies
```

#### 5.2 启动 Payload CMS

```powershell
# 方式 1: VSCode 任务 (Ctrl+Shift+B → "Start Payload CMS")
# 方式 2: 命令行
cd payload; npm run dev
```

验证：

```powershell
# Payload API 健康检查
Invoke-RestMethod http://localhost:3000/api/health

# Admin Panel 可访问
Start-Process "http://localhost:3000/admin"
```

#### 5.3 冒烟测试

```powershell
# 测试 Query 端点（通过 Payload 转发到 Engine）
$body = @{ query = "What is backpropagation?"; bookId = $null; strategy = "vector" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:3000/api/ask -Method Post -Body $body -ContentType "application/json"
```

---

### 6. 服务端口总览

| 服务 | 地址 | 说明 |
|------|------|------|
| Payload CMS + Next.js | `http://localhost:3000` | 前端页面 + REST API |
| Payload Admin | `http://localhost:3000/admin` | 管理后台 |
| Engine FastAPI | `http://127.0.0.1:8001` | RAG 引擎（仅内网） |
| Engine Swagger | `http://127.0.0.1:8001/docs` | API 文档 |
| Ollama | `http://localhost:11434` | LLM 服务 |
| ChromaDB | 本地文件 `./data/chroma` | 向量存储 |
| PostgreSQL | `localhost:5432` | Payload 数据库 |

---

### 7. 生成部署文档

创建 `docs/v2.0/deployment.md`，内容包含：

```markdown
# 本地部署指南 (v2.0)

## 快速启动

1. 复制环境变量: `cp .env.example .env` 并填写各项值
2. 安装依赖:
   - Python: `uv sync`
   - Payload: `cd payload && npm install`
3. 确保 PostgreSQL 和 Ollama 已在本地运行
4. VSCode 中按 `Ctrl+Shift+B` → 选择 **🚀 Start All (Engine + Payload)**
5. 访问 http://localhost:3000

## 服务说明

（表格同上）

## 常用命令

- Ruff 检查: `uv run ruff check engine/ backend/`
- Payload 构建验证: `cd payload && npm run build`
- Engine 交互文档: http://127.0.0.1:8001/docs
```

---

## 完成检查

- [ ] `.env` 配置完整
- [ ] Engine API 健康检查通过 (`/engine/health`)
- [ ] Payload Admin Panel 可登录
- [ ] 冒烟测试 Query 有响应
- [ ] `.vscode/tasks.json` 已更新
- [ ] `.vscode/launch.json` 已更新
- [ ] `docs/v2.0/deployment.md` 已生成

## 状态更新

```yaml
phases:
  deployment:
    status: completed
    completed_at: "{current_time}"
    output: "docs/v2.0/deployment.md"
```

## 下一步

🎉 全部阶段完成！

```
✓ Phase 1:  需求分析
✓ Phase 2:  产品需求文档
✓ Phase 3:  系统架构
✓ Phase 4:  任务分解
✓ Phase 5:  数据库设计
✓ Phase 6:  后端开发
✓ Phase 7:  前端开发
✓ Phase 8:  代码审查
✓ Phase 9:  本地部署
```
