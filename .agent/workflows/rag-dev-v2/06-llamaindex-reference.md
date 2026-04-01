---
description: LlamaIndex 参考速查 — 常用 API、基类、组合模式
---

# 📚 LlamaIndex 参考速查

> 本地源码: `.github/references/llama_index/llama-index-core/llama_index/core/`

## 常用基类 & 接口

### BaseReader (`readers/base.py`)

```python
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

class MyReader(BaseReader):
    def lazy_load_data(self, **kwargs) -> Iterable[Document]:
        yield Document(text="...", metadata={...})
```

**engine_v2 用法**: `readers/mineru_reader.py` → `MinerUReader(BaseReader)`

### TransformComponent (`schema.py`)

```python
from llama_index.core.schema import BaseNode, TransformComponent

class MyTransform(TransformComponent):
    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        # modify node metadata, text, etc.
        return nodes
```

**engine_v2 用法**: `ingestion/transformations.py` → `BBoxNormalizer(TransformComponent)`

### IngestionPipeline (`ingestion/pipeline.py`)

```python
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.chroma import ChromaVectorStore

pipeline = IngestionPipeline(
    transformations=[MyTransform(), Settings.embed_model],
    vector_store=vector_store,  # auto-upsert
)
nodes = pipeline.run(documents=documents, show_progress=True)
```

**engine_v2 用法**: `ingestion/pipeline.py` → `ingest_book()`

### QueryFusionRetriever (`retrievers/fusion_retriever.py`)

```python
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES

hybrid = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    retriever_weights=[0.5, 0.5],
    similarity_top_k=5,
    num_queries=1,
    mode=FUSION_MODES.RECIPROCAL_RANK,
)
nodes = hybrid.retrieve("query")
```

**engine_v2 用法**: `retrievers/hybrid.py` → `get_hybrid_retriever()`

### get_response_synthesizer (`response_synthesizers/factory.py`)

```python
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.core.prompts import PromptTemplate

synthesizer = get_response_synthesizer(
    response_mode=ResponseMode.COMPACT,
    text_qa_template=my_prompt,
    refine_template=my_refine_prompt,
    streaming=False,
)
```

**ResponseMode 选项:**
- `COMPACT` — stuff chunks, 1 LLM call (default, 推荐)
- `REFINE` — iterate chunk-by-chunk
- `TREE_SUMMARIZE` — recursive merge-summarise
- `SIMPLE_SUMMARIZE` — one-shot all chunks
- `NO_TEXT` — return sources only

**engine_v2 用法**: `response_synthesizers/citation.py` → `get_citation_synthesizer()`

### RetrieverQueryEngine (`query_engine/retriever_query_engine.py`)

```python
from llama_index.core.query_engine import RetrieverQueryEngine

engine = RetrieverQueryEngine(
    retriever=my_retriever,
    response_synthesizer=my_synthesizer,
)
response = engine.query("question")
# response.source_nodes → list[NodeWithScore]
# str(response) → answer text
```

**engine_v2 用法**: `query_engine/citation.py` → `get_query_engine()`

### Evaluators (`evaluation/`)

```python
from llama_index.core.evaluation import (
    FaithfulnessEvaluator,   # answer grounded in context?
    RelevancyEvaluator,      # context relevant to query?
    CorrectnessEvaluator,    # factually correct? (needs reference)
    BatchEvalRunner,         # parallel eval
)

faith = FaithfulnessEvaluator()
result = await faith.aevaluate_response(query=q, response=resp)
# result.score → float, result.feedback → str
```

**engine_v2 用法**: `evaluation/evaluator.py`

### Settings Singleton (`settings.py`)

```python
from llama_index.core.settings import Settings

# 全局配置 (一次性)
Settings.llm = my_llm
Settings.embed_model = my_embed_model

# 所有子模块自动使用:
# - IngestionPipeline 自动用 Settings.embed_model
# - get_response_synthesizer 自动用 Settings.llm
# - Evaluators 自动用 Settings.llm
```

**engine_v2 用法**: `settings.py` → `init_settings()`

## LLM Integrations

```python
# Ollama (local)
from llama_index.llms.ollama import Ollama
llm = Ollama(model="llama3.2:3b", base_url="http://127.0.0.1:11434")

# Azure OpenAI
from llama_index.llms.azure_openai import AzureOpenAI
llm = AzureOpenAI(engine="gpt-4o-mini", azure_endpoint=..., api_key=...)
```

**engine_v2 用法**: `llms/resolver.py` → `resolve_llm()`

## Embedding Integrations

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
embed = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
```

## Vector Store Integrations

```python
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex

client = chromadb.PersistentClient(path="data/chroma_persist")
collection = client.get_or_create_collection("textbook_chunks")
vector_store = ChromaVectorStore(chroma_collection=collection)

# Build index from existing store
index = VectorStoreIndex.from_vector_store(vector_store)
retriever = index.as_retriever(similarity_top_k=5)
```

## BM25 Retriever

```python
from llama_index.retrievers.bm25 import BM25Retriever

bm25 = BM25Retriever.from_defaults(index=index, similarity_top_k=5)
nodes = bm25.retrieve("query")
```

## 关键 Schema 类型

```python
from llama_index.core.schema import (
    Document,       # text + metadata, input to pipeline
    TextNode,       # text chunk with embedding
    BaseNode,       # base class for all nodes
    NodeWithScore,  # node + relevancy score (from retriever)
)
```

## 查找更多 API

```powershell
# 搜索 llama_index 源码
rg "class.*Retriever" .github/references/llama_index/llama-index-core/ --include "*.py" -l
rg "def.*evaluate" .github/references/llama_index/llama-index-core/ --include "*.py" -l
```
