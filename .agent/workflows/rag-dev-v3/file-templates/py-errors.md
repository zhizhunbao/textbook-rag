# 1.5 `engine_v2/errors.py` — 自定义异常层级

> 本文件已固定，不可新增。模板仅供参考。

```python
"""errors — 自定义异常层级.

All engine exceptions inherit from EngineError.
"""


# ============================================================
# Base
# ============================================================
class EngineError(Exception):
    """Base exception for all engine errors."""


# ============================================================
# Subclasses
# ============================================================
class <Specific>Error(EngineError):
    """<一句话描述>."""
```
