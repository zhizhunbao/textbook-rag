# 1.7 `engine_v2/api/routes/<resource>.py` — API 路由

```python
"""<resource> routes — <Resource> CRUD endpoints.

Endpoints:
    GET    /api/<resource>          — list all
    GET    /api/<resource>/{id}     — get by id
    POST   /api/<resource>          — create
"""


from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from engine_v2.api.deps import <dependency>
from engine_v2.schema import <Schema>

# ============================================================
# Router
# ============================================================
router = APIRouter(prefix="/<resource>", tags=["<resource>"])

# ============================================================
# Endpoints
# ============================================================
@router.get("/")
async def list_<resource>() -> list[<Schema>]:
    """List all <resource>."""
    logger.info("Listing <resource>")
    # TODO: implement
    logger.debug("Listed {} <resource>", len(result))
    ...


@router.get("/{<resource>_id}")
async def get_<resource>(<resource>_id: str) -> <Schema>:
    """Get a single <resource> by ID."""
    logger.info("Fetching <resource> {}", <resource>_id)
    # TODO: implement
    ...
```
