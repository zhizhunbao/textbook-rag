"""
split_collections.py — 将 JSON/PDF 数据文件从 ca_federal 迁移到 ca_federal_data
==============================================================================
把 book_id 以 "content/dam/" 开头的 chunks 从 ca_federal 移到 ca_federal_data，
保留官网页面 (book_id 以 "en/" 开头) 在 ca_federal。

用法:
  uv run python scripts/diag/split_collections.py --dry-run   # 预览
  uv run python scripts/diag/split_collections.py              # 执行
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_persist"
SRC_COLLECTION = "ca_federal"
DST_COLLECTION = "ca_federal_data"

# book_id 前缀 → 归属
DATA_PREFIXES = ["content/dam/"]


def main():
    p = argparse.ArgumentParser(description="Split ca_federal into web + data collections")
    p.add_argument("--dry-run", action="store_true", help="只预览，不执行")
    args = p.parse_args()

    logger.remove()
    logger.add(sys.stderr, format="{message}", level="INFO")

    import chromadb
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    src = client.get_collection(SRC_COLLECTION)
    logger.info(f"Source: {SRC_COLLECTION} ({src.count()} chunks)")

    # Phase 1: 扫描哪些 book_ids 需要移动
    total = src.count()
    batch_size = 5000
    offset = 0
    to_move: dict[str, int] = Counter()
    to_keep: dict[str, int] = Counter()
    move_ids: list[str] = []

    logger.info("Scanning book_ids...")
    while offset < total:
        r = src.get(limit=batch_size, offset=offset, include=["metadatas"])
        if not r["ids"]:
            break
        for chunk_id, meta in zip(r["ids"], r["metadatas"]):
            bid = meta.get("book_id", "")
            is_data = any(bid.startswith(prefix) for prefix in DATA_PREFIXES)
            if is_data:
                to_move[bid] += 1
                move_ids.append(chunk_id)
            else:
                to_keep[bid] += 1
        offset += len(r["ids"])

    logger.info(f"\n--- Summary ---")
    logger.info(f"Keep in {SRC_COLLECTION} (web pages): {len(to_keep)} book_ids, {sum(to_keep.values())} chunks")
    logger.info(f"Move to {DST_COLLECTION} (data files): {len(to_move)} book_ids, {sum(to_move.values())} chunks")
    logger.info(f"\nData book_ids to move:")
    for bid, cnt in sorted(to_move.items(), key=lambda x: -x[1])[:20]:
        logger.info(f"  {cnt:>6} chunks: {bid[:80]}")

    if args.dry_run:
        logger.info("\n[DRY RUN] No changes made.")
        return

    if not move_ids:
        logger.info("Nothing to move.")
        return

    # Phase 2: 创建目标 collection 并复制数据
    dst = client.get_or_create_collection(
        DST_COLLECTION,
        metadata=src.metadata,
    )
    logger.info(f"\nDest: {DST_COLLECTION} (existing: {dst.count()} chunks)")

    # 分批读取完整数据并写入
    logger.info(f"Copying {len(move_ids)} chunks...")
    copy_batch = 500
    copied = 0
    for i in range(0, len(move_ids), copy_batch):
        batch_ids = move_ids[i:i + copy_batch]
        r = src.get(
            ids=batch_ids,
            include=["metadatas", "documents", "embeddings"],
        )
        if r["ids"]:
            dst.add(
                ids=r["ids"],
                metadatas=r["metadatas"],
                documents=r["documents"],
                embeddings=r["embeddings"],
            )
            copied += len(r["ids"])
            logger.info(f"  Copied {copied}/{len(move_ids)}")

    # Phase 3: 从源 collection 删除
    logger.info(f"Deleting {len(move_ids)} chunks from {SRC_COLLECTION}...")
    del_batch = 500
    for i in range(0, len(move_ids), del_batch):
        batch_ids = move_ids[i:i + del_batch]
        src.delete(ids=batch_ids)

    logger.info(f"\nDone!")
    logger.info(f"  {SRC_COLLECTION}: {src.count()} chunks (web pages only)")
    logger.info(f"  {DST_COLLECTION}: {dst.count()} chunks (data files)")


if __name__ == "__main__":
    main()
