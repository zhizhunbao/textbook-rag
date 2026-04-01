"""Custom transformations for the ingestion pipeline.

Aligns with llama_index.core.schema.TransformComponent interface.
Each transform implements __call__(nodes) -> nodes.
"""

from __future__ import annotations

from typing import Any, Sequence

from llama_index.core.schema import BaseNode, TransformComponent


class BBoxNormalizer(TransformComponent):
    """Ensure bbox metadata is a flat list of 4 floats.

    MinerU sometimes produces malformed bboxes. This transform
    normalises them to [x0, y0, x1, y1] in PDF points.
    """

    @classmethod
    def class_name(cls) -> str:
        return "BBoxNormalizer"

    def __call__(
        self, nodes: Sequence[BaseNode], **kwargs: Any
    ) -> Sequence[BaseNode]:
        for node in nodes:
            bbox = node.metadata.get("bbox")
            if bbox is None:
                node.metadata["bbox"] = [0.0, 0.0, 0.0, 0.0]
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                node.metadata["bbox"] = [float(v) for v in bbox[:4]]
            else:
                node.metadata["bbox"] = [0.0, 0.0, 0.0, 0.0]
        return nodes
