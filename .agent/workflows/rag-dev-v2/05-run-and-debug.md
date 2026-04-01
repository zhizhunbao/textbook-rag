---
description: textbook-rag v2 启动运行与调试技巧
---

# 🚀 v2 启动 / 运行

## 一键启动 (VS Code Task)

```
Ctrl+Shift+P → Tasks: Run Task → 🚀 RAG v2: Start All (Engine + Payload)
```

这会并行启动:
- **Engine v2**: port 8001 (uvicorn + reload)
- **Payload v2**: port 3001 (next dev)

## 手动启动 Engine v2 (FastAPI)

```powershell
# cwd: textbook-rag (项目根目录)
uv run python -m uvicorn engine_v2.api.app:app --reload --host 127.0.0.1 --port 8001
```

**首次启动会:**
1. 调用 `init_settings()` → 初始化 `Settings.llm` + `Settings.embed_model`
2. 加载 HuggingFace embedding model (首次会下载 ~80MB)
3. 连接 Ollama 或 Azure OpenAI

## 手动启动 Payload v2 (Next.js)

```powershell
# cwd: textbook-rag/payload-v2
npm install        # 首次或依赖变更后
npm run dev -- --port 3001
```

**前置条件:**
- PostgreSQL 运行在 `127.0.0.1:5432`
- 数据库 `payload` 已创建
- 用户 `payload` / 密码 `payload`

```powershell
# 快速创建 PostgreSQL 数据库 (如需要)
psql -U postgres -c "CREATE USER payload WITH PASSWORD 'payload';"
psql -U postgres -c "CREATE DATABASE payload OWNER payload;"
```

## 环境检查

```powershell
# Engine v2 health
Invoke-WebRequest -Uri 'http://localhost:8001/engine/health' -UseBasicParsing | Select-Object StatusCode
# 期望: 200, body: {"status":"ok","version":"2.0.0"}

# Engine v2 LLM 状态
Invoke-WebRequest -Uri 'http://localhost:8001/engine/llms/providers' -UseBasicParsing

# Engine v2 模型信息
Invoke-WebRequest -Uri 'http://localhost:8001/engine/llms/models' -UseBasicParsing

# Payload v2 health (需要先 seed)
Invoke-WebRequest -Uri 'http://localhost:3001/api/books?limit=1' -UseBasicParsing
```

## 数据初始化 / 重建

### 初始化 Payload v2 数据 (Seed)

通过浏览器访问: `http://localhost:3001/seed`

或者使用 API:
```powershell
Invoke-WebRequest -Uri 'http://localhost:3001/api/seed' -Method POST -UseBasicParsing
```

### 向量重建 (ChromaDB)

```powershell
# 触发单本书摄入
$body = '{"book_id": 1, "file_url": "textbook_name.pdf", "category": "textbook"}'
Invoke-WebRequest -Uri 'http://localhost:8001/engine/ingest' -Method POST -Body $body -ContentType 'application/json' -UseBasicParsing
```

### 同步引擎数据到 Payload

通过 Payload endpoint:
```powershell
Invoke-WebRequest -Uri 'http://localhost:3001/api/sync-engine' -Method POST -UseBasicParsing
```

---

# 🔍 调试技巧

## Engine v2 调试

### 检索质量调试 (retrieve-only)

```powershell
# 只检索，不生成 — 直接查看 retriever 返回的 chunks
$body = '{"question": "What is normalization?", "top_k": 5}'
Invoke-WebRequest -Uri 'http://localhost:8001/engine/retrievers/search' -Method POST -Body $body -ContentType 'application/json' -UseBasicParsing | Select-Object -ExpandProperty Content
```

### 评估 RAG 质量

```powershell
# 单条评估 (faithfulness + relevancy)
$body = '{"question": "What is the difference between L1 and L2 regularization?"}'
Invoke-WebRequest -Uri 'http://localhost:8001/engine/evaluation/single' -Method POST -Body $body -ContentType 'application/json' -UseBasicParsing
```

### Python 类型检查

```powershell
# cwd: textbook-rag
uv run python -m pyright engine_v2/
```

### 互动式调试

```python
# 在 Python REPL 中测试
from engine_v2.settings import init_settings
init_settings()

# 测试检索
from engine_v2.retrievers.hybrid import get_hybrid_retriever
retriever = get_hybrid_retriever(similarity_top_k=3)
nodes = retriever.retrieve("What is gradient descent?")
for n in nodes:
    print(f"[{n.score:.3f}] {n.node.metadata.get('book_id')} p{n.node.metadata.get('page_idx')}")
    print(f"  {n.node.get_content()[:200]}")

# 测试完整查询
from engine_v2.query_engine.citation import query
result = query("Explain backpropagation")
print(result.answer)
print(f"Sources: {len(result.sources)}")
```

## Payload v2 调试

### TypeScript 类型检查

```powershell
# cwd: textbook-rag/payload-v2
npx tsc --noEmit
```

### 构建检查

```powershell
# cwd: textbook-rag/payload-v2
npm run build
```

### 查看 Payload 数据

```powershell
# 列出所有 books
Invoke-WebRequest -Uri 'http://localhost:3001/api/books?limit=100' -UseBasicParsing

# 查看特定 collection
Invoke-WebRequest -Uri 'http://localhost:3001/api/chunks?limit=5' -UseBasicParsing
```

### Payload Admin 面板

访问 `http://localhost:3001/admin` — Payload 自动生成的管理后台。

## 端口速查

| 服务 | 端口 | 备注 |
|------|------|------|
| Engine v1 | 8000 | v1 遗留 |
| Engine v2 | **8001** | LlamaIndex-native |
| Payload v1 | 3000 | SQLite adapter |
| Payload v2 | **3001** | PostgreSQL |
| PostgreSQL | 5432 | Payload v2 数据库 |
| Ollama | 11434 | 本地 LLM |
