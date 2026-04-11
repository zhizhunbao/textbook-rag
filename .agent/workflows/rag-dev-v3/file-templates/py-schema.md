# 1.4 `engine_v2/schema.py` — 领域模型

> 本文件已固定，不可新增。模板仅供参考。

```python
"""schema — 领域模型 (Pydantic BaseModel 定义).

Usage:
    from engine_v2.schema import BookMeta, RAGResponse
"""


from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================
# Domain models
# ============================================================
class <ModelName>(BaseModel):
    """<ModelName> — <一句话描述>."""

    id: str = Field(..., description="<描述>")
    # TODO: define fields
```
