"""Custom transformations for the ingestion pipeline.

Aligns with llama_index.core.schema.TransformComponent interface.
Each transform implements __call__(nodes) -> nodes.
"""

from __future__ import annotations

from typing import Any, Sequence

from llama_index.core.schema import BaseNode, TransformComponent


class BBoxNormalizer(TransformComponent):
    """Flatten bbox and sanitise metadata for ChromaDB.

    ChromaDB requires all metadata values to be flat (str, int, float, None).
    This transform:
      1. Splits bbox list [x0, y0, x1, y1] into 4 separate float fields
      2. Converts any remaining list/dict metadata to JSON strings
    """

    @classmethod
    def class_name(cls) -> str:
        return "BBoxNormalizer"

    def __call__(
        self, nodes: Sequence[BaseNode], **kwargs: Any
    ) -> Sequence[BaseNode]:
        for node in nodes:
            meta = node.metadata

            # Flatten bbox [x0, y0, x1, y1] → 4 separate float fields
            bbox = meta.pop("bbox", None)
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                meta["bbox_x0"] = float(bbox[0])
                meta["bbox_y0"] = float(bbox[1])
                meta["bbox_x1"] = float(bbox[2])
                meta["bbox_y1"] = float(bbox[3])
            else:
                meta["bbox_x0"] = 0.0
                meta["bbox_y0"] = 0.0
                meta["bbox_x1"] = 0.0
                meta["bbox_y1"] = 0.0

            # Sanitise: convert any remaining non-flat values to strings
            import json
            for key, val in list(meta.items()):
                if isinstance(val, (list, dict, tuple)):
                    meta[key] = json.dumps(val, ensure_ascii=False)

        return nodes

