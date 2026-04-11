# 1.8 `engine_v2/api/middleware/<concern>.py` — 中间件

```python
"""<concern> middleware — <一句话描述>.

Handles: <横切关注点说明>
"""


from __future__ import annotations

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ============================================================
# Middleware
# ============================================================
class <Concern>Middleware(BaseHTTPMiddleware):
    """<Concern> — <一句话描述>."""

    async def dispatch(self, request: Request, call_next) -> Response:

        # ======================================================
        # Before
        # ======================================================
        logger.debug("{} {}", request.method, request.url.path)

        response = await call_next(request)

        # ======================================================
        # After
        # ======================================================
        logger.debug("Response status: {}", response.status_code)
        return response
```
