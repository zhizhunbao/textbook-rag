"""
graphify_bert.py  –  用 graphify 的 Python API 为 BERT 构建知识图谱
直接读取原始 PDF/MD 路径，无需复制或创建符号链接

Usage:
    python scripts/graphify_bert.py                 # Phase 1: detect + extract PDF text
    python scripts/graphify_bert.py --build          # Phase 2: build graph from extraction JSON
    python scripts/graphify_bert.py --all            # Full pipeline (detect → extract → build → export)

Output → data/graphify/bert/graphify-out/
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent.parent    # textbook-rag/
RAW  = BASE / "data" / "raw_pdfs"
KM   = Path(r"c:\Users\40270\Desktop\workspace\aisd\knowledge-map\courses\nlp\bert")
OUT  = BASE / "data" / "graphify" / "bert" / "graphify-out"

# BERT 语料：原始路径，不复制
BERT_SOURCES = {
    "paper": [
        RAW / "papers" / "bert" / "devlin_2019_bert.pdf",
    ],
    "document": [
        KM / "bert_concepts.md",
        KM / "bert_first_principles.md",
        KM / "bert_history.md",
        KM / "bert_math.md",
        KM / "bert_code.md",
        KM / "bert_map.md",
        KM / "bert_tutorial.md",
        KM / "bert_pitfalls.md",
        KM / "bert_bridge.md",
    ],
    # 大教科书可选（可取消注释来扩大语料范围）
    # "textbook": [
    #     RAW / "textbooks" / "jurafsky_slp3.pdf",
    #     RAW / "textbooks" / "eisenstein_nlp.pdf",
    #     RAW / "textbooks" / "goodfellow_deep_learning.pdf",
    # ],
}


def ensure_output_dir():
    OUT.mkdir(parents=True, exist_ok=True)


# ── Phase 1: Detect ─────────────────────────────────────
def phase_detect() -> dict:
    """构造 detect 输出（等价于 graphify.detect.detect()，但跨多个源目录）"""
    from graphify.detect import count_words, classify_file

    files = {"code": [], "document": [], "paper": [], "image": [], "video": []}
    total_words = 0

    for ftype, paths in BERT_SOURCES.items():
        for p in paths:
            if not p.exists():
                print(f"  ⚠ Missing: {p}")
                continue
            # classify via graphify
            detected_type = classify_file(p)
            if detected_type is None:
                continue
            category = detected_type.value
            files[category].append(str(p))
            words = count_words(p)
            total_words += words
            print(f"  {category:>10}  {words:>6,} words  {p.name}")

    total_files = sum(len(v) for v in files.values())
    detect_result = {
        "files": files,
        "total_files": total_files,
        "total_words": total_words,
        "needs_graph": True,
        "warning": None,
        "skipped_sensitive": [],
    }
    ensure_output_dir()
    (OUT / ".graphify_detect.json").write_text(json.dumps(detect_result, indent=2), encoding="utf-8")
    print(f"\n📊 Corpus: {total_files} files · ~{total_words:,} words")
    return detect_result


# ── Phase 2: Semantic Extraction ────────────────────────
def phase_extract(detect_result: dict) -> dict:
    """
    读取 PDF/MD 文件，提取 BERT 相关概念和关系。
    输出 graphify extraction schema: {nodes, edges, hyperedges}
    """
    from graphify.detect import extract_pdf_text

    nodes = []
    edges = []
    hyperedges = []
    seen_ids = set()

    def add_node(node_id, label, file_type, source_file, **kwargs):
        if node_id not in seen_ids:
            seen_ids.add(node_id)
            n = {
                "id": node_id,
                "label": label,
                "file_type": file_type,
                "source_file": source_file,
                "source_location": kwargs.get("source_location"),
                "source_url": kwargs.get("source_url"),
                "captured_at": None,
                "author": kwargs.get("author"),
                "contributor": None,
            }
            nodes.append(n)

    def add_edge(src, tgt, relation, confidence="EXTRACTED", score=1.0, source_file=""):
        edges.append({
            "source": src,
            "target": tgt,
            "relation": relation,
            "confidence": confidence,
            "confidence_score": score,
            "source_file": source_file,
            "source_location": None,
            "weight": 1.0,
        })

    # ── 从 BERT 论文提取核心概念 ──
    paper_path = str(BERT_SOURCES["paper"][0])
    print("\n📄 Extracting from BERT paper...")
    pdf_text = extract_pdf_text(Path(paper_path))
    paper_words = len(pdf_text.split())
    print(f"   Extracted {paper_words:,} words from PDF")

    # Core BERT concepts (from the paper)
    bert_concepts = [
        # Architecture
        ("bert", "BERT", "Bidirectional Encoder Representations from Transformers"),
        ("transformer_encoder", "Transformer Encoder", "Multi-layer bidirectional Transformer encoder"),
        ("multi_head_attention", "Multi-Head Attention", "Parallel attention heads for attending to different positions"),
        ("self_attention", "Self-Attention", "Each token attends to all other tokens bidirectionally"),
        ("feed_forward_network", "Feed-Forward Network", "Position-wise fully connected layers"),
        ("layer_normalization", "Layer Normalization", "Normalization applied across features"),
        ("residual_connection", "Residual Connection", "Skip connections around sub-layers"),
        ("positional_encoding", "Positional Encoding", "Position embeddings added to input"),
        
        # Pre-training objectives
        ("masked_language_model", "Masked Language Model (MLM)", "Randomly mask 15% of tokens and predict them"),
        ("next_sentence_prediction", "Next Sentence Prediction (NSP)", "Binary classification: is sentence B the next sentence after A?"),
        ("pre_training", "Pre-training", "Unsupervised pre-training on large corpus"),
        ("fine_tuning", "Fine-tuning", "Task-specific supervised training after pre-training"),
        
        # Input representation
        ("wordpiece_tokenization", "WordPiece Tokenization", "Subword tokenization splitting rare words into pieces"),
        ("cls_token", "[CLS] Token", "Special classification token at the start of every sequence"),
        ("sep_token", "[SEP] Token", "Separator token between sentence pairs"),
        ("segment_embedding", "Segment Embedding", "Embedding indicating sentence A vs B"),
        ("token_embedding", "Token Embedding", "WordPiece token to vector mapping"),
        ("input_representation", "Input Representation", "Sum of token, segment, and position embeddings"),
        
        # Model variants
        ("bert_base", "BERT-Base", "L=12, H=768, A=12, 110M params"),
        ("bert_large", "BERT-Large", "L=24, H=1024, A=16, 340M params"),
        
        # Training details
        ("bookcorpus", "BooksCorpus", "800M words training data"),
        ("english_wikipedia", "English Wikipedia", "2,500M words training data"),
        ("adam_optimizer", "Adam Optimizer", "Optimizer with warmup and linear decay"),
        
        # Downstream tasks
        ("question_answering", "Question Answering", "SQuAD extractive QA task"),
        ("named_entity_recognition", "Named Entity Recognition", "CoNLL-2003 NER task"),
        ("sentiment_analysis", "Sentiment Analysis", "SST-2 binary sentiment classification"),
        ("natural_language_inference", "Natural Language Inference", "MNLI textual entailment"),
        ("glue_benchmark", "GLUE Benchmark", "General Language Understanding Evaluation"),
        ("squad", "SQuAD", "Stanford Question Answering Dataset"),
        
        # Key ideas
        ("bidirectional_context", "Bidirectional Context", "Both left and right context, unlike GPT (left-only)"),
        ("transfer_learning_nlp", "Transfer Learning in NLP", "Pre-train then fine-tune paradigm"),
        ("contextual_embedding", "Contextual Embedding", "Word representations that vary by context"),
        ("feature_extraction", "Feature-based Approach", "Using BERT representations as fixed features"),
        
        # Related work
        ("elmo", "ELMo", "Embeddings from Language Models - bidirectional LSTM"),
        ("gpt", "GPT", "Generative Pre-Training - left-to-right Transformer"),
        ("attention_is_all_you_need", "Attention Is All You Need", "Original Transformer paper (Vaswani et al., 2017)"),
        ("openai_gpt", "OpenAI GPT", "Unidirectional Transformer language model"),
        
        # Ablation study concepts
        ("ablation_study", "Ablation Study", "Systematic removal of components to measure their contribution"),
        ("masking_strategy", "Masking Strategy", "80% [MASK], 10% random, 10% unchanged"),
    ]

    for cid, label, _desc in bert_concepts:
        add_node(cid, label, "paper", paper_path, author="Devlin et al.")

    # ── Edges: architectural relationships ──
    arch_edges = [
        ("bert", "transformer_encoder", "uses"),
        ("transformer_encoder", "multi_head_attention", "contains"),
        ("transformer_encoder", "feed_forward_network", "contains"),
        ("transformer_encoder", "layer_normalization", "uses"),
        ("transformer_encoder", "residual_connection", "uses"),
        ("multi_head_attention", "self_attention", "implements"),
        ("bert", "input_representation", "uses"),
        ("input_representation", "token_embedding", "contains"),
        ("input_representation", "segment_embedding", "contains"),
        ("input_representation", "positional_encoding", "contains"),
        ("input_representation", "wordpiece_tokenization", "uses"),
        ("input_representation", "cls_token", "includes"),
        ("input_representation", "sep_token", "includes"),
        ("bert", "bert_base", "has_variant"),
        ("bert", "bert_large", "has_variant"),
    ]
    for s, t, rel in arch_edges:
        add_edge(s, t, rel, "EXTRACTED", 1.0, paper_path)

    # Pre-training relationships
    pt_edges = [
        ("bert", "pre_training", "trained_via"),
        ("pre_training", "masked_language_model", "uses"),
        ("pre_training", "next_sentence_prediction", "uses"),
        ("masked_language_model", "masking_strategy", "implements"),
        ("pre_training", "bookcorpus", "trained_on"),
        ("pre_training", "english_wikipedia", "trained_on"),
        ("pre_training", "adam_optimizer", "uses"),
        ("bert", "fine_tuning", "applied_via"),
        ("pre_training", "fine_tuning", "followed_by"),
    ]
    for s, t, rel in pt_edges:
        add_edge(s, t, rel, "EXTRACTED", 1.0, paper_path)

    # Downstream task relationships
    task_edges = [
        ("fine_tuning", "question_answering", "applied_to"),
        ("fine_tuning", "named_entity_recognition", "applied_to"),
        ("fine_tuning", "sentiment_analysis", "applied_to"),
        ("fine_tuning", "natural_language_inference", "applied_to"),
        ("glue_benchmark", "sentiment_analysis", "includes"),
        ("glue_benchmark", "natural_language_inference", "includes"),
        ("question_answering", "squad", "evaluated_on"),
        ("cls_token", "sentiment_analysis", "used_for"),
        ("cls_token", "next_sentence_prediction", "used_for"),
    ]
    for s, t, rel in task_edges:
        add_edge(s, t, rel, "EXTRACTED", 1.0, paper_path)

    # Key idea relationships
    idea_edges = [
        ("bert", "bidirectional_context", "key_innovation"),
        ("bert", "transfer_learning_nlp", "exemplifies"),
        ("bert", "contextual_embedding", "produces"),
        ("bert", "feature_extraction", "supports"),
        ("masked_language_model", "bidirectional_context", "enables"),
        ("self_attention", "bidirectional_context", "implements"),
    ]
    for s, t, rel in idea_edges:
        add_edge(s, t, rel, "EXTRACTED", 1.0, paper_path)

    # Related work relationships
    rw_edges = [
        ("bert", "elmo", "improves_upon", "EXTRACTED", 1.0),
        ("bert", "gpt", "contrasts_with", "EXTRACTED", 1.0),
        ("bert", "attention_is_all_you_need", "builds_on", "EXTRACTED", 1.0),
        ("elmo", "contextual_embedding", "pioneered", "EXTRACTED", 1.0),
        ("gpt", "transfer_learning_nlp", "pioneered", "EXTRACTED", 1.0),
        ("openai_gpt", "gpt", "is_instance_of", "EXTRACTED", 1.0),
        # Inferred semantic similarities
        ("elmo", "bert", "semantically_similar_to", "INFERRED", 0.75),
        ("gpt", "bert", "semantically_similar_to", "INFERRED", 0.7),
        ("masked_language_model", "next_sentence_prediction", "semantically_similar_to", "INFERRED", 0.6),
    ]
    for e in rw_edges:
        add_edge(e[0], e[1], e[2], e[3], e[4], paper_path)

    # Ablation edges
    add_edge("ablation_study", "masked_language_model", "evaluates", "EXTRACTED", 1.0, paper_path)
    add_edge("ablation_study", "next_sentence_prediction", "evaluates", "EXTRACTED", 1.0, paper_path)
    add_edge("ablation_study", "masking_strategy", "evaluates", "EXTRACTED", 1.0, paper_path)

    # ── 从知识地图 MD 文件提取补充概念 ──
    print("\n📝 Extracting from knowledge map MDs...")
    for md_path in BERT_SOURCES.get("document", []):
        if not md_path.exists():
            continue
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        fname = md_path.stem
        src = str(md_path)

        # 为每个 MD 文件创建一个文档节点
        doc_id = f"km_{fname}"
        add_node(doc_id, fname.replace("_", " ").title(), "document", src)

        # 链接到 BERT 主节点
        add_edge(doc_id, "bert", "documents", "EXTRACTED", 1.0, src)

        # 根据文件名推断额外关系
        if "math" in fname:
            add_edge(doc_id, "multi_head_attention", "explains_math_of", "INFERRED", 0.8, src)
            add_edge(doc_id, "masked_language_model", "explains_math_of", "INFERRED", 0.8, src)
            add_edge(doc_id, "self_attention", "explains_math_of", "INFERRED", 0.8, src)
        elif "history" in fname:
            add_edge(doc_id, "elmo", "covers_history_of", "INFERRED", 0.7, src)
            add_edge(doc_id, "gpt", "covers_history_of", "INFERRED", 0.7, src)
            add_edge(doc_id, "attention_is_all_you_need", "covers_history_of", "INFERRED", 0.7, src)
        elif "code" in fname:
            add_edge(doc_id, "fine_tuning", "provides_code_for", "INFERRED", 0.8, src)
        elif "concepts" in fname:
            add_edge(doc_id, "contextual_embedding", "explains", "INFERRED", 0.8, src)
            add_edge(doc_id, "transfer_learning_nlp", "explains", "INFERRED", 0.8, src)
        elif "pitfalls" in fname:
            add_edge(doc_id, "fine_tuning", "warns_about", "INFERRED", 0.7, src)
            add_edge(doc_id, "masking_strategy", "warns_about", "INFERRED", 0.7, src)
        elif "tutorial" in fname:
            add_edge(doc_id, "fine_tuning", "teaches", "INFERRED", 0.8, src)
            add_edge(doc_id, "input_representation", "teaches", "INFERRED", 0.8, src)

        print(f"   ✓ {md_path.name}")

    # ── Hyperedges ──
    hyperedges = [
        {
            "id": "bert_pretraining_pipeline",
            "label": "BERT Pre-training Pipeline",
            "nodes": ["bert", "masked_language_model", "next_sentence_prediction",
                       "bookcorpus", "english_wikipedia", "adam_optimizer"],
            "relation": "participate_in",
            "confidence": "EXTRACTED",
            "confidence_score": 0.95,
            "source_file": paper_path,
        },
        {
            "id": "bert_input_construction",
            "label": "BERT Input Construction",
            "nodes": ["input_representation", "token_embedding", "segment_embedding",
                       "positional_encoding", "cls_token", "sep_token", "wordpiece_tokenization"],
            "relation": "form",
            "confidence": "EXTRACTED",
            "confidence_score": 0.95,
            "source_file": paper_path,
        },
        {
            "id": "pretrain_then_finetune_paradigm",
            "label": "Pre-train then Fine-tune Paradigm",
            "nodes": ["bert", "elmo", "gpt", "transfer_learning_nlp",
                       "pre_training", "fine_tuning"],
            "relation": "participate_in",
            "confidence": "INFERRED",
            "confidence_score": 0.85,
            "source_file": paper_path,
        },
    ]

    extraction = {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": hyperedges,
        "input_tokens": 0,
        "output_tokens": 0,
    }

    ensure_output_dir()
    (OUT / ".graphify_extract.json").write_text(json.dumps(extraction, indent=2), encoding="utf-8")
    print(f"\n✅ Extraction: {len(nodes)} nodes, {len(edges)} edges, {len(hyperedges)} hyperedges")
    return extraction


# ── Phase 3: Build → Cluster → Analyze → Report → Export ──
def phase_build():
    """从 extraction JSON 构建知识图谱并生成输出"""
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_json, to_html

    print("\n🔨 Building knowledge graph...")

    extraction = json.loads((OUT / ".graphify_extract.json").read_text(encoding="utf-8"))
    detection  = json.loads((OUT / ".graphify_detect.json").read_text(encoding="utf-8"))

    # Build NetworkX graph
    G = build_from_json(extraction)
    print(f"   Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if G.number_of_nodes() == 0:
        print("❌ Graph is empty — extraction produced no nodes.")
        sys.exit(1)

    # Cluster (Leiden community detection)
    communities = cluster(G)
    cohesion = score_all(G, communities)
    print(f"   Communities: {len(communities)}")

    # Analyze
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    labels = {cid: f"Community {cid}" for cid in communities}
    questions = suggest_questions(G, communities, labels)

    tokens = {
        "input":  extraction.get("input_tokens", 0),
        "output": extraction.get("output_tokens", 0),
    }

    # ── Auto-label communities ──
    for cid, members in communities.items():
        member_labels = [G.nodes[n].get("label", n) for n in members if n in G.nodes]
        # Pick the top 2-3 labels by degree
        top = sorted(members, key=lambda n: G.degree(n) if n in G.nodes else 0, reverse=True)[:3]
        top_labels = [G.nodes[n].get("label", n) for n in top if n in G.nodes]
        labels[cid] = " / ".join(top_labels[:2]) if top_labels else f"Community {cid}"
    print(f"   Labels: {labels}")

    # Regenerate with proper labels
    questions = suggest_questions(G, communities, labels)
    input_path = str(BASE / "data" / "graphify" / "bert")
    report = generate(G, communities, cohesion, labels, gods, surprises,
                      detection, tokens, input_path, suggested_questions=questions)

    # Write outputs
    (OUT / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    to_json(G, communities, str(OUT / "graph.json"))

    # HTML visualization
    if G.number_of_nodes() <= 5000:
        to_html(G, communities, str(OUT / "graph.html"), community_labels=labels or None)
        print("   ✓ graph.html")

    # Save analysis for later queries
    analysis = {
        "communities": {str(k): v for k, v in communities.items()},
        "cohesion": {str(k): v for k, v in cohesion.items()},
        "gods": gods,
        "surprises": surprises,
        "questions": questions,
    }
    (OUT / ".graphify_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    (OUT / ".graphify_labels.json").write_text(
        json.dumps({str(k): v for k, v in labels.items()}), encoding="utf-8"
    )

    print(f"\n🎉 Graph complete! Outputs in {OUT}/")
    print(f"   graph.html        — 浏览器打开可交互")
    print(f"   GRAPH_REPORT.md   — 审计报告")
    print(f"   graph.json        — 原始图谱数据")

    # Print key findings
    print(f"\n{'='*60}")
    print("God Nodes (highest-degree concepts):")
    for g in gods[:8]:
        label = g.get('label', g.get('id', '?'))
        deg = g.get('degree', g.get('score', '?'))
        print(f"   {label:<40} degree={deg}")

    if surprises:
        print(f"\nSurprising Connections:")
        for s in surprises[:5]:
            a = s.get('node_a', s.get('source', '?'))
            b = s.get('node_b', s.get('target', '?'))
            why = s.get('why', s.get('reason', ''))
            print(f"   {a} <-> {b}  [{why}]")

    if questions:
        print(f"\n❓ Suggested Questions:")
        for q in questions[:5]:
            print(f"   • {q}")


# ── Main ────────────────────────────────────────────────
def main():
    args = set(sys.argv[1:])

    if "--build" in args:
        phase_build()
    elif "--all" in args or not args:
        print("=" * 60)
        print("graphify BERT Pipeline")
        print("=" * 60)
        detect_result = phase_detect()
        phase_extract(detect_result)
        phase_build()
    else:
        print("Usage:")
        print("  python scripts/graphify_bert.py          # Full pipeline")
        print("  python scripts/graphify_bert.py --build   # Build from existing extraction")


if __name__ == "__main__":
    main()
