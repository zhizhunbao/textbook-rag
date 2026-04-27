# 📁 scripts/ — 自动化脚本

> **v2 架构**: 数据存储已迁移至 PostgreSQL (Payload CMS)。原 SQLite 相关脚本已清理。
> 核心入库管道由 `engine_v2/ingestion/pipeline.py` 驱动。

---

## 目录结构

```
scripts/
├── _paths.py                           # 共享路径解析（所有脚本可用）
│
├── acquire/                            # ① 数据获取：下载 PDF 原材料
│   ├── download_free_books.py          #   下载开源教科书 PDF
│   ├── download_ecdev_pdfs.py          #   下载 Ottawa 经济发展报告
│   ├── search_github_books.py          #   GitHub 搜索免费教科书链接
│   └── explore_sources.py              #   Playwright 爬虫发现新 PDF 源
│
├── ingest/                             # ② PDF 解析：MinerU 结构化
│   └── batch_mineru.py                 #   批量 PDF → Markdown/JSON
│
├── db/                                 # ③ 索引：文件级索引构建
│   └── rebuild_topic_index.py          #   跨书主题词索引 → topic_index.json
│
├── vectors/                            # ④ 向量：ChromaDB 维护
│   └── patch_chroma_chapter_keys.py    #   回填 chunk 的 chapter_key 元数据
│
├── cms/                                # ⑤ CMS：Payload 数据同步
│   ├── batch_ingest_real_estate.py     #   房地产报告批量入库
│   ├── batch_reingest_ecdev.py         #   经济发展报告重入库（LaTeX 清洗）
│   ├── backfill_ingest_tasks.py        #   修复/填充 ingest-tasks 状态
│   └── update_file_sizes.py            #   回填 PDF 文件大小到 CMS
│
├── reports/                            # ⑥ 报告：Word/PPTX 生成
│   ├── build_final_report.py           #   生成项目最终报告 (Word)
│   ├── fill_final_report.py            #   填充 Word 报告模板
│   ├── gen_final_presentation.py       #   生成项目演示幻灯片 (PPTX)
│   ├── generate_ppt.py                 #   补充版演示文稿
│   └── graphify_bert.py                #   BERT 知识图谱可视化
│
└── diagnostics/                        # ⑦ 诊断：状态检查
    └── check_tasks.py                  #   查看 Payload ingest-tasks 状态
```

---

## CRUD 操作指南

### 📥 添加新书 (Create)

**场景**: 拿到一本新教科书 PDF，需要入库到系统中。

```bash
# Step 1: 把 PDF 放到正确目录
#   教科书 → data/raw_pdfs/textbooks/
#   经济报告 → data/raw_pdfs/ecdev/
#   房地产 → data/raw_pdfs/real_estate/

# Step 2: 用 MinerU 解析 PDF
uv run python scripts/ingest/batch_mineru.py --category textbooks

# Step 3: 通过 Payload CMS UI 创建 Book 记录
#   打开 http://localhost:3001/admin/collections/books/create
#   填写 title, engineBookId (= 文件名去掉 .pdf), category

# Step 4: 触发入库管道（会自动嵌入到 ChromaDB + 更新 CMS 状态）
#   方式 A: 在 UI 点击 "Ingest" 按钮
#   方式 B: 调用 Engine API
curl -X POST http://localhost:8001/engine/ingest \
  -H "Content-Type: application/json" \
  -d '{"book_id": 42, "title": "my_book_id", "category": "textbook"}'

# Step 5 (可选): 回填章节元数据
uv run python scripts/vectors/patch_chroma_chapter_keys.py --book my_book_id
```

### 📥 批量添加 (Batch Create)

```bash
# 下载开源教科书
uv run python scripts/acquire/download_free_books.py

# 下载经济发展报告
uv run python scripts/acquire/download_ecdev_pdfs.py

# 批量 MinerU 解析
uv run python scripts/ingest/batch_mineru.py

# 批量入库房地产数据
uv run python scripts/cms/batch_ingest_real_estate.py

# 批量重入库经济报告（含 LaTeX 清洗）
uv run python scripts/cms/batch_reingest_ecdev.py
```

### 🔍 查看状态 (Read)

```bash
# 检查 Payload CMS 中 ingest-tasks 和 books 状态
uv run python scripts/diagnostics/check_tasks.py
# → 输出到 scripts/check_tasks_output.txt
```

### 🔧 修复/更新 (Update)

```bash
# 回填 ChromaDB 中缺失的 chapter_key 元数据
uv run python scripts/vectors/patch_chroma_chapter_keys.py
uv run python scripts/vectors/patch_chroma_chapter_keys.py --book my_book --force
uv run python scripts/vectors/patch_chroma_chapter_keys.py --dry-run

# 修复 Payload 中缺失的 ingest-tasks 记录
uv run python scripts/cms/backfill_ingest_tasks.py

# 回填 PDF 文件大小到 CMS
uv run python scripts/cms/update_file_sizes.py

# 重建跨书主题索引
uv run python scripts/db/rebuild_topic_index.py
```

### 🗑️ 删除 (Delete)

> 删除操作直接通过 Payload CMS Admin UI 完成：
> - http://localhost:3001/admin/collections/books
> - http://localhost:3001/admin/collections/chunks

---

## 环境依赖

| 服务 | 地址 | 用途 |
|------|------|------|
| Payload CMS | `http://localhost:3001` | PostgreSQL 数据管理 |
| Engine API | `http://localhost:8001` | 后端 RAG 引擎 |
| ChromaDB | `data/chroma_persist/` | 向量数据库（本地文件） |
| Ollama | `http://127.0.0.1:11434` | 本地 LLM（可选） |
| MinerU | Python 包 | PDF 结构化解析 |

### 认证信息

脚本中使用的 Payload CMS 凭证从 `.env` 读取：

```env
PAYLOAD_ADMIN_EMAIL=402707192@qq.com
PAYLOAD_ADMIN_PASSWORD=123123
PAYLOAD_API_KEY=BHTdK273zAnTBPDayNmb97OLNsavV8yyGWqhhtkM8Kw
```

---

## 开发笔记

- **核心入库管道** 在 `engine_v2/ingestion/pipeline.py`，走 LlamaIndex 原生流程：
  `MinerUReader → IngestionPipeline → ChromaDB + Payload CMS`
- **`_paths.py`** 通过搜索 `pyproject.toml` 定位项目根目录，子目录下的脚本无需手动修 path
- 报告类脚本 (`reports/`) 仅用于课程项目提交，日常运维不需要
