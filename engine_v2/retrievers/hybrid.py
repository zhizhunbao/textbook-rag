"""HybridRetriever — BM25 + Vector → RRF fusion with metadata filtering.

Aligns with llama_index.core.retrievers.QueryFusionRetriever.
Combines:
    - VectorIndexRetriever (from ChromaVectorStore, with MetadataFilters)
    - BM25Retriever (from llama-index-retrievers-bm25)
    - TrackedQueryFusionRetriever with RECIPROCAL_RANK fusion
      + retrieval_source provenance (EV2-T1-01)

Filtering:
    - Vector retriever uses ChromaDB native where clause via MetadataFilters
    - BM25 results are post-filtered by a FilterPostprocessor since BM25
      doesn't support metadata filtering natively

Provenance (Sprint EV2):
    After RRF fusion each NodeWithScore.metadata["retrieval_source"] is set
    to "vector" | "bm25" | "both" depending on which sub-retriever(s)
    returned that chunk.  Zero additional LLM calls.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    TOP_K,
)

# ============================================================
# Thread-safe ChromaDB client singleton
# ============================================================
# ChromaDB PersistentClient uses SQLite internally. On Windows,
# creating multiple PersistentClient instances concurrently from
# different threads causes SQLite lock contention, resulting in
# "Could not connect to tenant default_tenant" errors.
# A single shared client + lock prevents this.
_chroma_client: chromadb.ClientAPI | None = None
_chroma_lock = threading.Lock()


def _get_shared_chroma_client() -> chromadb.ClientAPI:
    """Return (or create) the process-wide ChromaDB PersistentClient."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client
    with _chroma_lock:
        # Double-checked locking
        if _chroma_client is not None:
            return _chroma_client
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB shared client initialised: {}", CHROMA_PERSIST_DIR)
        return _chroma_client


def _build_metadata_filters(
    book_id_strings: list[str] | None = None,
) -> MetadataFilters | None:
    """Build LlamaIndex MetadataFilters from filter parameters.

    These filters are pushed down to the ChromaDB vector store so only
    matching chunks are retrieved, preventing cross-book contamination.

    Args:
        book_id_strings: List of book directory names to restrict search to.

    Returns:
        MetadataFilters or None (if no filters specified).
    """
    if not book_id_strings:
        return None

    if len(book_id_strings) == 1:
        # Single book — simple equality filter
        return MetadataFilters(
            filters=[
                MetadataFilter(
                    key="book_id",
                    value=book_id_strings[0],
                    operator=FilterOperator.EQ,
                ),
            ],
        )

    # Multiple books — OR condition
    return MetadataFilters(
        filters=[
            MetadataFilter(
                key="book_id",
                value=bid,
                operator=FilterOperator.EQ,
            )
            for bid in book_id_strings
        ],
        condition=FilterCondition.OR,
    )


# ============================================================
# TrackedQueryFusionRetriever — RRF with retrieval_source tags
# ============================================================
class TrackedQueryFusionRetriever(QueryFusionRetriever):
    """QueryFusionRetriever that tags each fused node with its source strategy.

    After RRF fusion, every NodeWithScore gets:
        metadata["retrieval_source"] = "vector" | "bm25" | "both"
        metadata["vector_score"]     = raw cosine similarity (0~1)
        metadata["bm25_score"]       = raw BM25 Okapi score (0~∞)

    Implementation:
        1. Override _run_sync_queries() to capture per-retriever IDs + raw scores.
        2. Override _retrieve() to inject tags and raw scores after fusion.

    The first retriever (index 0) is always Vector; the second (index 1),
    when present, is BM25.  In vector-only mode all nodes are tagged
    "vector".
    """

    _vector_ids: set[str]
    _bm25_ids: set[str]
    _vector_scores: dict[str, float]  # node_id → raw cosine score
    _bm25_scores: dict[str, float]    # node_id → raw BM25 score

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_ids = set()
        self._bm25_ids = set()
        self._vector_scores = {}
        self._bm25_scores = {}
        # "hybrid" when both retrievers present, else "vector_only"
        self.retrieval_mode: str = (
            "hybrid" if len(self._retrievers) > 1 else "vector_only"
        )

    # -- capture per-retriever IDs + raw scores during sync execution --
    def _run_sync_queries(
        self, queries: List[QueryBundle],
    ) -> Dict[Tuple[str, int], List[NodeWithScore]]:
        results = super()._run_sync_queries(queries)

        self._vector_ids = set()
        self._bm25_ids = set()
        self._vector_scores = {}
        self._bm25_scores = {}

        for (_, retriever_idx), nodes in results.items():
            for n in nodes:
                nid = n.node.id_
                raw = float(n.score) if n.score is not None else 0.0
                if retriever_idx == 0:     # Vector
                    self._vector_ids.add(nid)
                    self._vector_scores[nid] = raw
                elif retriever_idx == 1:   # BM25
                    self._bm25_ids.add(nid)
                    self._bm25_scores[nid] = raw

        return results

    # -- inject retrieval_source + raw scores after fusion --
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        fused = super()._retrieve(query_bundle)

        for nws in fused:
            nid = nws.node.id_
            in_vector = nid in self._vector_ids
            in_bm25 = nid in self._bm25_ids

            if in_vector and in_bm25:
                source = "both"
            elif in_bm25:
                source = "bm25"
            else:
                source = "vector"

            nws.node.metadata["retrieval_source"] = source
            # Raw scores — the honest numbers
            nws.node.metadata["vector_score"] = self._vector_scores.get(nid, 0.0)
            nws.node.metadata["bm25_score"] = self._bm25_scores.get(nid, 0.0)

        # Log distribution + sample scores for debugging
        counts = {"vector": 0, "bm25": 0, "both": 0}
        for nws in fused:
            counts[nws.node.metadata.get("retrieval_source", "vector")] += 1
        if fused:
            top = fused[0]
            logger.debug(
                "Retrieval provenance: {} (mode={}) | top node: "
                "vec={:.4f} bm25={:.4f} rrf={:.6f}",
                counts, self.retrieval_mode,
                top.node.metadata.get("vector_score", 0),
                top.node.metadata.get("bm25_score", 0),
                float(top.score) if top.score else 0,
            )

        return fused


# ============================================================
# BM25 Retriever Cache (UEP-T1-02)
# ============================================================
_BM25_CACHE: OrderedDict[str, tuple[BM25Retriever, float]] = OrderedDict()
_BM25_CACHE_MAX = 5  # max cached retrievers (LRU eviction)
_BM25_CACHE_TTL = 3600  # 1 hour TTL


def _cache_key(collection_name: str, book_id_strings: list[str] | None) -> str:
    """Build a stable cache key from collection + book filter."""
    books = tuple(sorted(book_id_strings)) if book_id_strings else ()
    return f"{collection_name}::{books}"


def _get_cached_bm25(
    collection_name: str, book_id_strings: list[str] | None,
) -> BM25Retriever | None:
    """Return cached BM25Retriever if available and not expired."""
    key = _cache_key(collection_name, book_id_strings)
    entry = _BM25_CACHE.get(key)
    if entry is None:
        return None
    retriever, ts = entry
    if time.monotonic() - ts > _BM25_CACHE_TTL:
        _BM25_CACHE.pop(key, None)
        logger.debug("BM25 cache expired for key={}", key)
        return None
    # Move to end (most recently used)
    _BM25_CACHE.move_to_end(key)
    logger.debug("BM25 cache HIT for key={}", key)
    return retriever


def _put_cached_bm25(
    collection_name: str,
    book_id_strings: list[str] | None,
    retriever: BM25Retriever,
) -> None:
    """Store a BM25Retriever in cache with LRU eviction."""
    key = _cache_key(collection_name, book_id_strings)
    _BM25_CACHE[key] = (retriever, time.monotonic())
    _BM25_CACHE.move_to_end(key)
    while len(_BM25_CACHE) > _BM25_CACHE_MAX:
        evicted_key, _ = _BM25_CACHE.popitem(last=False)
        logger.debug("BM25 cache evicted key={}", evicted_key)


def get_hybrid_retriever(
    similarity_top_k: int = TOP_K,
    collection_name: str = CHROMA_COLLECTION,
    book_id_strings: list[str] | None = None,
) -> TrackedQueryFusionRetriever:
    """Build a hybrid BM25 + Vector retriever with RRF fusion.

    Architecture:
        QueryFusionRetriever (RRF, k=60)
        ├── VectorIndexRetriever (ChromaDB cosine similarity + MetadataFilters)
        └── BM25Retriever (rank_bm25 on docstore nodes)

    Both retrievers share the same VectorStoreIndex so they operate
    on the same set of nodes.

    Falls back to vector-only retrieval when the collection is empty
    (no documents ingested yet) to avoid BM25 crash on empty corpus.

    Args:
        similarity_top_k: Number of results to return.
        collection_name: ChromaDB collection name.
        book_id_strings: Optional list of book directory names to filter on.
            When provided, only chunks from these books are retrieved.

    Returns:
        QueryFusionRetriever ready for use in a QueryEngine.
    """
    # Connect to existing ChromaDB collection (shared singleton)
    client = _get_shared_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    vector_store = ChromaVectorStore(chroma_collection=collection)

    # Build VectorStoreIndex from existing store
    index = VectorStoreIndex.from_vector_store(vector_store)

    # Build MetadataFilters for book scoping
    metadata_filters = _build_metadata_filters(book_id_strings)

    # Vector retriever — applies metadata filters at the ChromaDB level
    vector_retriever = index.as_retriever(
        similarity_top_k=similarity_top_k,
        filters=metadata_filters,
    )

    filter_desc = f", book_filter={book_id_strings}" if book_id_strings else ""
    logger.info(
        "Vector retriever ready (top_k={}{})", similarity_top_k, filter_desc
    )

    # Build BM25 retriever from ChromaDB text (not empty docstore)
    #
    # 背景：IngestionPipeline 入库时只往 ChromaDB 写向量+文本，
    # 不会填充 LlamaIndex docstore。而 BM25Retriever.from_defaults(index=index)
    # 从 docstore 读文本，所以永远拿到空列表。
    #
    # 修法：直接从 ChromaDB 按 book_id 拉文本，构造 TextNode 列表，
    # 传给 BM25Retriever.from_defaults(nodes=nodes)。
    # 有 book_id 过滤时只加载几千条（可控），无过滤时跳过 BM25 避免 OOM。
    doc_count = collection.count()
    retrievers_list = [vector_retriever]
    weights = [1.0]

    if doc_count > 0:
        # Check BM25 cache first (UEP-T1-02)
        cached_bm25 = _get_cached_bm25(collection_name, book_id_strings)
        if cached_bm25 is not None:
            retrievers_list.append(cached_bm25)
            weights = [0.5, 0.5]
            scope = f"books={book_id_strings}" if book_id_strings else "all-books"
            logger.info("BM25 retriever from cache ({})", scope)
        else:
            try:
                from llama_index.core.schema import TextNode

                # Build where clause: None for all-books, filter for specific books
                where_clause: dict | None = None
                if book_id_strings:
                    if len(book_id_strings) == 1:
                        where_clause = {"book_id": book_id_strings[0]}
                    else:
                        where_clause = {"$or": [{"book_id": bid} for bid in book_id_strings]}

                # Safety cap to prevent OOM on large collections
                MAX_BM25_NODES = 20000
                BATCH_SIZE = 5000  # ChromaDB recommended batch for get()

                bm25_nodes: list[TextNode] = []
                offset = 0

                # Batch-fetch nodes from ChromaDB
                while len(bm25_nodes) < MAX_BM25_NODES:
                    remaining = MAX_BM25_NODES - len(bm25_nodes)
                    batch_limit = min(BATCH_SIZE, remaining)

                    get_kwargs: dict[str, Any] = {
                        "limit": batch_limit,
                        "offset": offset,
                        "include": ["documents", "metadatas"],
                    }
                    if where_clause is not None:
                        get_kwargs["where"] = where_clause

                    chroma_results = collection.get(**get_kwargs)

                    batch_ids = chroma_results["ids"]
                    if not batch_ids:
                        break  # No more documents

                    for doc_id, doc_text, doc_meta in zip(
                        batch_ids,
                        chroma_results["documents"],
                        chroma_results["metadatas"],
                    ):
                        if doc_text and len(doc_text.strip()) > 0:
                            node = TextNode(
                                text=doc_text,
                                id_=doc_id,
                                metadata=doc_meta or {},
                            )
                            bm25_nodes.append(node)

                    offset += len(batch_ids)

                    # If we got fewer than requested, we've exhausted the collection
                    if len(batch_ids) < batch_limit:
                        break

                if bm25_nodes:
                    # ── Language-aware BM25 config ──
                    # Detect language from first few nodes
                    sample_text = " ".join(
                        n.text[:200] for n in bm25_nodes[:5]
                    )
                    cjk_ratio = sum(
                        1 for c in sample_text if '\u4e00' <= c <= '\u9fff'
                    ) / max(len(sample_text), 1)
                    is_chinese = cjk_ratio > 0.3

                    bm25_kwargs: dict[str, Any] = {
                        "nodes": bm25_nodes,
                        "similarity_top_k": similarity_top_k,
                    }

                    if is_chinese:
                        # Chinese: jieba word segmentation
                        import jieba
                        def _tokenize_zh(text: str) -> list[str]:
                            """Segment Chinese text with jieba, remove stop words."""
                            _ZH_STOP = {
                                '的', '了', '在', '是', '我', '有', '和',
                                '就', '不', '人', '都', '一', '一个', '上',
                                '也', '很', '到', '说', '要', '去', '你',
                                '会', '着', '没有', '看', '好', '自己',
                                '这', '他', '她', '它', '们', '那', '些',
                                '什么', '怎么', '如何', '哪', '吗', '吧',
                                '啊', '呢', '呀', '嗯', '哦', '哈',
                                '与', '及', '或', '但', '而', '虽', '因',
                                '为', '所以', '如果', '因为', '但是',
                            }
                            tokens = jieba.lcut(text)
                            return [t for t in tokens
                                    if t.strip() and t not in _ZH_STOP
                                    and len(t.strip()) > 0]
                        bm25_kwargs["tokenizer"] = _tokenize_zh
                        lang_label = "zh"
                    else:
                        # English: stemmer + built-in stop word removal
                        import Stemmer
                        stemmer = Stemmer.Stemmer("english")
                        bm25_kwargs["language"] = "en"       # 去停用词
                        bm25_kwargs["stemmer"] = stemmer     # 词干化
                        lang_label = "en"

                    bm25_retriever = BM25Retriever.from_defaults(**bm25_kwargs)
                    retrievers_list.append(bm25_retriever)
                    weights = [0.5, 0.5]
                    # Cache for reuse
                    _put_cached_bm25(collection_name, book_id_strings, bm25_retriever)
                    scope = f"books={book_id_strings}" if book_id_strings else "all-books"
                    logger.info(
                        "BM25 retriever built from {} ChromaDB nodes ({}, lang={})",
                        len(bm25_nodes), scope, lang_label,
                    )
                else:
                    logger.warning(
                        "No text nodes found in ChromaDB (books={})",
                        book_id_strings or "all",
                    )

            except Exception as exc:
                logger.warning("BM25 retriever unavailable, vector-only mode: {}", exc)
    else:
        logger.warning(
            "Collection '{}' is empty — using vector-only retrieval. "
            "Run ingestion to enable hybrid BM25+Vector mode.",
            collection_name,
        )

    # Fuse with Reciprocal Rank Fusion (k=60, industry standard)
    # TrackedQueryFusionRetriever adds retrieval_source provenance (EV2-T1-01)
    hybrid_retriever = TrackedQueryFusionRetriever(
        retrievers=retrievers_list,
        retriever_weights=weights,
        similarity_top_k=similarity_top_k,
        num_queries=1,  # no query augmentation, just fuse the two retrievers
        mode=FUSION_MODES.RECIPROCAL_RANK,
        use_async=False,
    )

    mode = "hybrid BM25+Vector" if len(retrievers_list) > 1 else "vector-only"
    logger.info(
        "HybridRetriever ready: {} → RRF (top_k={}{}, retrieval_mode={})",
        mode, similarity_top_k, filter_desc, hybrid_retriever.retrieval_mode,
    )
    return hybrid_retriever


# ============================================================
# Multi-collection hybrid retrieval + RRF merge
# ============================================================

_MULTI_RRF_K = 60


def _retrieve_from_collection(
    question: str,
    collection_name: str,
    origin_tag: str,
    top_k: int,
) -> list[NodeWithScore]:
    """Retrieve nodes from one ChromaDB collection via hybrid BM25+Vector."""
    try:
        retriever = get_hybrid_retriever(
            similarity_top_k=top_k,
            collection_name=collection_name,
        )
        nodes = retriever.retrieve(question)

        for nws in nodes:
            nws.node.metadata["retrieval_origin"] = origin_tag

        logger.debug(
            "Hybrid-retrieved {} nodes from {} ({})",
            len(nodes), collection_name, origin_tag,
        )
        return nodes
    except Exception as exc:
        logger.warning("Retrieval from {} failed: {}", collection_name, exc)
        return []


def _merge_n_with_rrf(
    ranked_lists: list[list[NodeWithScore]],
    top_k: int,
    boost_map: dict[str, float] | None = None,
) -> list[NodeWithScore]:
    """Merge N ranked node lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: Per-collection ranked results.
        top_k: Max results to return.
        boost_map: Optional mapping of collection_name → weight multiplier.
            Collections with higher weight (e.g. 1.5) get boosted RRF scores.
            Default weight is 1.0 for any collection not in the map.
    """
    scored: dict[str, tuple[float, NodeWithScore]] = {}

    for nodes in ranked_lists:
        for rank, nws in enumerate(nodes, start=1):
            node_id = nws.node.id_
            # Apply collection boost if available
            origin = nws.node.metadata.get("retrieval_origin", "")
            boost = (boost_map or {}).get(origin, 1.0)
            rrf_score = boost / (_MULTI_RRF_K + rank)
            if node_id in scored:
                existing_score, existing_node = scored[node_id]
                scored[node_id] = (existing_score + rrf_score, existing_node)
            else:
                scored[node_id] = (rrf_score, nws)

    merged = sorted(scored.values(), key=lambda item: item[0], reverse=True)[:top_k]
    result: list[NodeWithScore] = []
    for rrf_score, nws in merged:
        nws.score = rrf_score
        result.append(nws)

    if boost_map:
        logger.debug("RRF merge with boosts: {}", boost_map)

    return result


# ── Default collection boost weights ──
# Federal material is the primary authority for immigration/study questions.
# Provincial material is supplementary (relevant mainly for PNP).
# Education material is narrowest scope (school-specific info).
DEFAULT_COLLECTION_BOOSTS: dict[str, float] = {
    "ca_federal": 1.5,
    # All ca_prov_* default to 1.0 (no entry needed)
    # All ca_edu_* get a slight penalty
    "ca_edu_algonquin": 0.8,
}


def multi_collection_retrieve(
    question: str,
    collection_names: list[str],
    top_k: int = TOP_K,
    boost_map: dict[str, float] | None = None,
) -> list[NodeWithScore]:
    """Retrieve from multiple ChromaDB collections in parallel, merge via RRF.

    Each collection uses hybrid BM25+Vector retrieval internally.
    Federal collections are boosted by default to prioritize authoritative sources.

    Args:
        question: User query string.
        collection_names: List of ChromaDB collection names to search.
        top_k: Number of merged results to return.
        boost_map: Optional per-collection RRF weight overrides.
            If None, uses DEFAULT_COLLECTION_BOOSTS.

    Returns:
        Merged and ranked list of NodeWithScore.
    """
    from concurrent.futures import ThreadPoolExecutor

    effective_boosts = boost_map if boost_map is not None else DEFAULT_COLLECTION_BOOSTS

    with ThreadPoolExecutor(max_workers=len(collection_names)) as executor:
        futures = [
            executor.submit(
                _retrieve_from_collection,
                question,
                coll_name,
                coll_name,
                top_k,
            )
            for coll_name in collection_names
        ]
        ranked_lists = [f.result() for f in futures]

    merged = _merge_n_with_rrf(ranked_lists, top_k, boost_map=effective_boosts)
    counts = {name: len(nodes) for name, nodes in zip(collection_names, ranked_lists)}
    logger.info(
        "Multi-collection hybrid RRF: {} → {} merged (boosts={})",
        counts, len(merged), effective_boosts,
    )
    return merged
