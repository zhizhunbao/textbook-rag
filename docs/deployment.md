# 部署文档

## 环境要求

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | 3.12+ | 后端运行时 |
| uv | latest | Python 包管理 |
| Node.js | 20+ | 前端构建 |
| Ollama | latest | 本地 LLM 推理 |
| SQLite | 3.35+ | 数据库（FTS5 支持） |

## 快速启动

### 1. 安装依赖

```powershell
# 后端
uv sync --all-extras

# 前端
cd frontend
npm install
cd ..
```

### 2. 配置环境

```powershell
Copy-Item .env.example .env
# 按需编辑 .env
```

主要配置项（均有默认值，可不改）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| DATABASE_PATH | data/textbook_rag.sqlite3 | SQLite 数据库路径 |
| CHROMA_PERSIST_DIR | data/chroma_persist | ChromaDB 持久化目录 |
| OLLAMA_BASE_URL | http://127.0.0.1:11434 | Ollama 服务地址 |
| OLLAMA_MODEL | llama3.2:3b | 默认生成模型 |
| CORS_ORIGINS | http://localhost:5173 | 允许的前端源 |

### 3. 准备 Ollama

```powershell
# 启动 Ollama 服务（如未运行）
ollama serve

# 拉取模型
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 4. 构建数据库（首次）

```powershell
uv run python scripts/rebuild_db.py
```

### 5. 启动服务

#### 方式 A：VS Code 任务（推荐）

在 VS Code 中按 `Ctrl+Shift+P` → `Tasks: Run Task` → `Start Full`

将同时启动：
- 后端 API：http://127.0.0.1:8000
- 前端 Web：http://127.0.0.1:5173

#### 方式 B：手动启动

```powershell
# 终端 1：后端
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2：前端
cd frontend
npm run dev
```

### 6. 验证

```powershell
# 健康检查
Invoke-RestMethod http://127.0.0.1:8000/health

# API 文档
Start-Process http://127.0.0.1:8000/docs
```

## VS Code 集成

### 任务 (.vscode/tasks.json)

| 任务 | 说明 |
|---|---|
| Start Backend API | 启动 FastAPI 后端（端口 8000，自动 reload） |
| Start Frontend Web | 启动 Vite 开发服务器（端口 5173） |
| Start Full | 同时启动前后端 |

### 调试 (.vscode/launch.json)

| 配置 | 说明 |
|---|---|
| Backend API | 启动后端（带终端调试） |
| Frontend Web | 启动前端开发服务器 |
| Start Full | 复合配置，同时启动两者 |

## 项目结构

```
textbook-rag/
├── backend/app/          # FastAPI 后端
│   ├── config.py         # 环境配置
│   ├── database.py       # SQLite 连接
│   ├── main.py           # 应用入口
│   ├── repositories/     # 数据访问层
│   ├── routers/          # API 路由
│   ├── schemas/          # Pydantic 模型
│   └── services/         # 业务逻辑层
├── backend/tests/        # pytest 测试
├── frontend/src/         # React 前端
├── data/                 # 数据目录
│   ├── textbook_rag.sqlite3  # SQLite 数据库
│   ├── chroma_persist/       # ChromaDB 向量库
│   └── mineru_output/        # MinerU 解析结果
├── textbooks/            # 原始教材 PDF
├── .env.example          # 环境变量模板
└── .vscode/              # VS Code 配置
```

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| GET | /api/v1/books | 获取书籍列表 |
| GET | /api/v1/books/{id} | 获取书籍详情 |
| GET | /api/v1/books/{id}/pdf | 获取 PDF 文件 |
| POST | /api/v1/query | RAG 问答查询 |

## 故障排查

| 问题 | 解决方案 |
|---|---|
| Ollama 推理慢 | 确认未加载大模型：`ollama stop qwen3.5:27b` |
| 端口被占用 | VS Code 任务会自动杀死旧进程 |
| 数据库不存在 | 运行 `uv run python scripts/rebuild_db.py` |
| FTS5 查询报错 | 特殊字符会被自动清理，检查 SQLite 版本 ≥ 3.35 |
