# ⚠️ DEPRECATED — v1.1 遗留后端

> **本目录已废弃，请勿修改。**
>
> v2.0 已将核心代码迁移到 `engine/` 目录：
> - `backend/app/core/` → `engine/rag/`
> - `backend/app/routers/` → `engine/api/routes/`
> - `backend/app/repositories/` → `engine/adapters/` + SQLite 直连
>
> 保留此目录仅供历史参考，未来版本将彻底移除。

## 迁移对照表

| v1.1 backend/app/ | v2.0 engine/ |
|---|---|
| `core/rag_core.py` | `rag/core.py` |
| `core/config.py` | `rag/config.py` |
| `core/types.py` | `rag/types.py` |
| `core/retrieval.py` | `rag/retrieval.py` |
| `core/fusion.py` | `rag/fusion.py` |
| `core/generation.py` | `rag/generation.py` |
| `core/citation.py` | `rag/citation.py` |
| `core/quality.py` | `rag/quality.py` |
| `core/trace.py` | `rag/trace.py` |
| `core/strategies/*` | `rag/strategies/*` |
| `routers/*` | `api/routes/*` |
| `main.py` | `api/app.py` |
