"""translate routes — Bidirectional translation (EN↔ZH).

Detects the source language automatically:
  - CJK content → translate to English
  - Non-CJK content → translate to Simplified Chinese
"""

from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from engine_v2.llms.resolver import resolve_llm

router = APIRouter(tags=["translate"])

class TranslateRequest(BaseModel):
    text: str


def _contains_cjk(text: str) -> bool:
    """Return True if text contains CJK characters."""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


@router.post("/translate")
async def translate_text(req: TranslateRequest):
    """Translate text bidirectionally: EN→ZH or ZH→EN."""
    is_cjk = _contains_cjk(req.text)
    target = "English" if is_cjk else "Simplified Chinese"
    logger.info("Translating text (len={}, target={})", len(req.text), target)
    
    # Use qwen3:1.7b — smallest Qwen3 that handles translation well (~1.4GB)
    llm = resolve_llm(model="qwen3:1.7b", provider="ollama")
    # /no_think disables Qwen3's internal reasoning chain → faster output
    prompt = (
        f"/no_think\n"
        f"Translate to {target}. Output ONLY the translation.\n"
        f"IMPORTANT: Keep all [N] citation markers (like [1], [2], [3]) "
        f"exactly where they are. Do NOT add, remove, or move any [N] markers.\n\n"
        f"{req.text}"
    )
    
    response = await llm.acomplete(prompt)
    translated = str(response)
    # Strip any <think>...</think> wrapper that might leak through
    translated = re.sub(r"<think>.*?</think>\s*", "", translated, flags=re.DOTALL).strip()
    return {"translation": translated}

