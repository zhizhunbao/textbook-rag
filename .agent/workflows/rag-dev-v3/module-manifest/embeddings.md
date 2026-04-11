# `embeddings` — 向量嵌入

> 纯后端模块，无前端 UI。

```
Func
模型加载
批量编码
维度配置
缓存复用

Noun
Embedding
Model
Vector
Batch
Cache
Dimension
```

```
embeddings
└── engine_v2/embeddings/
    ├── __init__.py                         re-export 公共 API
    └── resolver.py                         嵌入模型解析 + 加载
```
