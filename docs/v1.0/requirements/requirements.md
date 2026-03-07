# AI Textbook Q&A System — Requirements Document

> **Author**: Alice (Product Manager)
> **Phase**: 1/11 — Requirements Analysis
> **Date**: 2026-03-04
> **Assignment**: CST8507 Assignment 2 — NLP
> **Team**: Wang, Peng · Yoo, Hye Ran

---

## 1. Project Overview

### 1.1 Background

Students studying AI, machine learning, and NLP must frequently navigate across many textbooks to locate relevant concepts, definitions, and examples. Traditional keyword search breaks down when questions use paraphrased terms, and manual browsing is time-consuming. There is no single tool that allows students to ask a **natural language question** and receive a grounded answer backed by exact source references across a multi-book library.

This project is part of CST8507 (Natural Language Processing) Assignment 2 and CST8504 (Applying AI) Assignment 3. It is structured in two parts:

- **Part 1** — Build a standalone RAG-based Q&A system with a Streamlit UI (the primary focus, 65% weight).
- **Part 2** — Convert the system into a ROS 2 node for vocal interaction (25% weight).

### 1.2 Goals

| #   | Goal                                                      | Success Metric                                                        |
| --- | --------------------------------------------------------- | --------------------------------------------------------------------- |
| G1  | Answer educational questions grounded in textbook content | ≥80% accuracy on 20-question evaluation set                           |
| G2  | Provide deep source tracing to exact book/page/region     | Every answer includes clickable references with PDF bbox highlighting |
| G3  | Preserve document structure (tables, formulas, figures)   | Layout-aware chunking verified on 5+ sample documents                 |
| G4  | Run entirely locally with minimal resources               | Total model memory <1.5 GB (Ollama qwen2.5:0.5b ≈ 0.4 GB)             |
| G5  | Support interactive multi-turn sessions via Streamlit UI  | Users can ask multiple questions in a single session                  |
| G6  | Convert to ROS 2 node for robot vocal interaction         | Successful pipeline: Whisper → RAG → gTTS                             |

### 1.3 Scope

**In scope:**

- PDF preprocessing pipeline using MinerU (magic-pdf) with DocLayout-YOLO
- Dual indexing: SQLite FTS5 (BM25) + ChromaDB (sentence-transformers)
- PageIndex tree generation for LLM-reasoning-based retrieval
- Four retrieval methods + Reciprocal Rank Fusion (RRF)
- Ollama integration with qwen2.5:0.5b model
- Streamlit UI with source tracing and PDF bbox highlighting
- Object-Oriented codebase ready for ROS 2 conversion
- 20-question evaluation with 3-level manual scoring

**Out of scope (v1):**

- Online/cloud model deployment
- Multi-language question support (English only for v1)
- Real-time streaming answers
- User accounts or conversation history persistence
- Training or fine-tuning custom models

---

## 2. Target Users

### 2.1 User Personas

| Persona           | Description                                                                          | Primary Need                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **Student Sarah** | 2nd-year AI/ML student at Algonquin College. Studies across 5+ textbooks per course. | Quickly find authoritative answers to concept questions with exact source references for further reading        |
| **Professor Ali** | CST8507 instructor evaluating the system.                                            | Verify that answers are grounded in document content (no hallucination), and that source tracing is transparent |
| **Robot User**    | (Part 2) A user interacting via voice with the iRobot Create 3.                      | Ask spoken questions and receive spoken answers derived from the knowledge base                                 |

### 2.2 User Scenarios

**Scenario 1 — Concept Lookup**
Sarah is studying for her NLP exam and wants to understand "What is the difference between precision and recall?" She types the question into the Streamlit interface. The system retrieves relevant chunks from SLP3 (Jurafsky) and ISLR, generates a concise answer, and shows clickable references. She clicks a reference and sees the original PDF page with the relevant paragraph highlighted in yellow.

**Scenario 2 — Formula Lookup**
Sarah wants to see "the Adam optimizer update rule." The system retrieves the exact formula from Goodfellow's Deep Learning Chapter 8.5, displays the LaTeX rendering, and highlights the formula's bounding box on the original PDF page.

**Scenario 3 — Cross-Book Synthesis**
Sarah asks "Compare gradient descent variants discussed in different textbooks." The system retrieves chunks from multiple books (Goodfellow, Bishop, ISLR), synthesizes a comparison, and lists all sources.

**Scenario 4 — Robot Voice Interaction (Part 2)**
A user speaks to the robot: "What is overfitting?" The Whisper STT node converts speech to text, the RAG node retrieves relevant content, generates an answer, and publishes it. The gTTS node speaks the answer aloud.

---

## 3. Functional Requirements

### 3.1 Core Functions

| ID  | Function                               | Description                                                                                                                           | Priority |
| --- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| F1  | **PDF Layout Analysis**                | Use MinerU (magic-pdf) with DocLayout-YOLO to detect document regions (text, tables, formulas, figures) with bounding box coordinates | MUST     |
| F2  | **Specialized Content Extraction**     | Extract text → plain text, tables → HTML, formulas → LaTeX, figures → image + caption                                                 | MUST     |
| F3  | **Layout-Aware Chunking**              | Intelligent chunking that keeps tables and formulas intact; each chunk carries metadata (book, chapter, page, section, bbox)          | MUST     |
| F4  | **Dual Index — SQLite FTS5**           | Full-text search index with BM25 ranking for exact keyword matching                                                                   | MUST     |
| F5  | **Dual Index — ChromaDB Vector Store** | Embedding-based index using sentence-transformers (all-MiniLM-L6-v2) for semantic similarity retrieval                                | MUST     |
| F6  | **PageIndex Tree Generation**          | Build hierarchical table-of-contents trees per book for LLM-driven top-down section navigation                                        | MUST     |
| F7  | **Keyword Search (BM25)**              | SQLite FTS5 keyword search as retrieval method ①                                                                                      | MUST     |
| F8  | **Semantic Search**                    | ChromaDB vector search as retrieval method ②                                                                                          | MUST     |
| F9  | **PageIndex Tree Search**              | LLM navigates TOC tree to locate relevant sections as retrieval method ③                                                              | MUST     |
| F10 | **Metadata Filter Search**             | Structured filtering by book/chapter/page/content-type as retrieval method ④                                                          | MUST     |
| F11 | **Reciprocal Rank Fusion (RRF)**       | Combine results from all four methods into a single ranked list                                                                       | MUST     |
| F12 | **LLM Answer Generation**              | Generate answers using Ollama (qwen2.5:0.5b) grounded in retrieved context                                                            | MUST     |
| F13 | **Deep Source Tracing**                | Each answer includes source references (book, chapter, page, bbox). Clicking a reference renders the PDF page with highlighted region | MUST     |
| F14 | **Streamlit UI**                       | Interactive web interface: question input, answer display, source reference list, PDF viewer with bbox overlay                        | MUST     |
| F15 | **Multi-Turn Sessions**                | Support asking multiple questions within a single session                                                                             | MUST     |

### 3.2 Auxiliary Functions

| ID  | Function                      | Description                                                                                          | Priority |
| --- | ----------------------------- | ---------------------------------------------------------------------------------------------------- | -------- |
| A1  | **OOP Code Structure**        | Code written in object-oriented style, ready for ROS 2 conversion                                    | SHOULD   |
| A2  | **ROS 2 Node Conversion**     | Convert RAG pipeline into a ROS 2 node subscribing to `words` topic and publishing to `ollama_reply` | SHOULD   |
| A3  | **Batch Processing Pipeline** | Process all 30+ PDFs in batch with progress tracking                                                 | SHOULD   |
| A4  | **Content Type Badges**       | Visual indicators in UI for content type (text / table / formula / figure)                           | COULD    |
| A5  | **Query History**             | Display recent queries in sidebar for quick re-access within session                                 | COULD    |

### 3.3 Future Extensions (Out of Scope for v1)

- Multi-language question support
- Conversation memory across sessions
- Cloud deployment option
- Custom model fine-tuning on educational Q&A pairs
- Automated evaluation with LLM-as-judge

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Metric                                 | Target                             | Rationale                                                                       |
| -------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------- |
| Query latency (retrieval + generation) | < 30 seconds on CPU                | Usable interactive experience                                                   |
| Indexing throughput                    | Process all 30+ books in < 2 hours | One-time setup cost                                                             |
| Total model memory                     | < 1.5 GB                           | Part 2 constraint: Whisper + Ollama + gTTS run simultaneously on robot hardware |
| Embedding model size                   | all-MiniLM-L6-v2 (≈ 80 MB)         | Lightweight, widely benchmarked                                                 |

### 4.2 Security

| Requirement              | Implementation                                                        |
| ------------------------ | --------------------------------------------------------------------- |
| No external API calls    | All models run locally via Ollama; no data leaves the machine         |
| No hardcoded credentials | Use environment variables for any config values                       |
| Input validation         | Sanitize user queries before passing to LLM; prevent prompt injection |

### 4.3 Usability

| Requirement              | Implementation                                                                            |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| Single-command startup   | `streamlit run app.py` launches the full system                                           |
| Clear source attribution | Every chunk displayed with book title, chapter, page number                               |
| Error handling           | Graceful errors when Ollama is unavailable, index is missing, or query returns no results |
| Responsive layout        | Streamlit components adjust to different screen widths                                    |

### 4.4 Maintainability

| Requirement              | Implementation                                                       |
| ------------------------ | -------------------------------------------------------------------- |
| Modular architecture     | Separate modules: preprocessing, indexing, retrieval, generation, UI |
| OOP design               | Class-based design for easy ROS 2 conversion                         |
| Configuration management | Central config file (YAML/JSON) for model names, paths, parameters   |
| Logging                  | Structured logging with configurable verbosity                       |
| Type hints               | Python type hints throughout for IDE support and static analysis     |

---

## 5. Constraints

### 5.1 Technical Constraints

| Constraint       | Detail                                 |
| ---------------- | -------------------------------------- |
| Language         | Python 3.10+                           |
| LLM Framework    | Ollama (local only)                    |
| LLM Model        | qwen2.5:0.5b (≈ 0.4 GB)                |
| Embedding Model  | sentence-transformers all-MiniLM-L6-v2 |
| Vector Store     | ChromaDB                               |
| Full-Text Search | SQLite FTS5                            |
| PDF Parser       | MinerU (magic-pdf) with DocLayout-YOLO |
| UI Framework     | Streamlit                              |
| Part 2 Framework | ROS 2 (Humble/Iron)                    |

### 5.2 Business Constraints

| Constraint       | Detail                                                      |
| ---------------- | ----------------------------------------------------------- |
| Team size        | 2 members (Wang, Peng + Yoo, Hye Ran)                       |
| Timeline         | 5 weeks (Mar 3 – Apr 3, 2026)                               |
| Budget           | $0 — all tools and models must be free/open-source          |
| Textbook sources | Open-access editions or legally obtained educational copies |

### 5.3 Time Constraints

| Week                  | Milestone       | Deliverables                                                                |
| --------------------- | --------------- | --------------------------------------------------------------------------- |
| Week 1 (Mar 3–9)      | Infrastructure  | MinerU setup, PDF pipeline, SQLite + ChromaDB schema                        |
| Week 2 (Mar 10–16)    | Indexing        | Chunking, embedding, FTS5 + ChromaDB indexes, PageIndex trees               |
| Week 3 (Mar 17–23)    | RAG Pipeline    | Four retrieval methods, RRF fusion, Ollama integration, end-to-end pipeline |
| Week 4 (Mar 24–30)    | UI + Evaluation | Streamlit UI with source tracing, 20-question evaluation                    |
| Week 5 (Mar 31–Apr 3) | Integration     | ROS 2 node conversion, final report, presentation                           |

---

## 6. Acceptance Criteria

### 6.1 Part 1 — RAG System (65% weight)

| #   | Criterion                                                                  | Verification                                                       |
| --- | -------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| AC1 | System answers 20 evaluation questions with ≥80% accuracy                  | Manual 3-level scoring (1 / 0.5 / 0) averaged across all questions |
| AC2 | Every answer includes at least 1 source reference with book, chapter, page | Visual inspection of Streamlit output                              |
| AC3 | Clicking a source reference shows original PDF page with highlighted bbox  | UI interaction test                                                |
| AC4 | Tables, formulas, and figures are preserved in chunking                    | Sample chunks from PRML tables and Goodfellow formulas are intact  |
| AC5 | All four retrieval methods contribute to RRF fusion                        | Log output shows results from each method                          |
| AC6 | System runs locally with total model memory < 1.5 GB                       | Monitor memory usage during query                                  |
| AC7 | Multiple questions can be asked in a single session                        | Test 5+ sequential queries                                         |
| AC8 | Answers are grounded in document content (no hallucination outside domain) | Manual review of 20 evaluation answers                             |

### 6.2 Part 2 — ROS 2 Integration (25% weight)

| #    | Criterion                                                  | Verification                                   |
| ---- | ---------------------------------------------------------- | ---------------------------------------------- |
| AC9  | RAG code converted to OOP class structure                  | Code inspection                                |
| AC10 | ROS 2 node subscribes to `words` topic                     | `ros2 topic echo /words` shows data            |
| AC11 | ROS 2 node publishes to `ollama_reply` topic               | `ros2 topic echo /ollama_reply` shows response |
| AC12 | Full pipeline works: speech → Whisper → RAG → gTTS → audio | End-to-end demonstration                       |

### 6.3 Report & Presentation (10% weight)

| #    | Criterion                                                                     | Verification                  |
| ---- | ----------------------------------------------------------------------------- | ----------------------------- |
| AC13 | Final report is 6–10 pages with all required sections                         | Document review               |
| AC14 | 10-minute presentation covers intro, method, evaluation, outcomes, discussion | Slide count and content check |

---

## 7. Appendix

### 7.1 Textbook Inventory

30+ canonical textbooks in PDF format covering:

| Domain                 | Count | Key Books                                                                 |
| ---------------------- | ----- | ------------------------------------------------------------------------- |
| Machine Learning       | 7     | ISLR, ESL, PRML, Deep Learning (Goodfellow), PML (Murphy)                 |
| Mathematics            | 5     | MML (Deisenroth), Convex Optimization (Boyd), Information Theory (MacKay) |
| NLP                    | 3     | SLP3 (Jurafsky), Intro to IR (Manning), NLP Notes (Eisenstein)            |
| Reinforcement Learning | 1     | RL: An Introduction (Sutton & Barto)                                      |
| Computer Vision        | 1     | Computer Vision (Szeliski)                                                |
| Python Programming     | 3     | Fluent Python, Python Cookbook, Think Python                              |

Total dataset: ~500 MB of PDF documents.

### 7.2 Technology Stack Summary

```
┌─────────────────────────────────────────────┐
│               Streamlit UI                   │
│  [Question Input] [Answer] [Source Viewer]   │
├─────────────────────────────────────────────┤
│           LLM Answer Generation              │
│         Ollama (qwen2.5:0.5b)               │
├─────────────────────────────────────────────┤
│        Reciprocal Rank Fusion (RRF)          │
├──────────┬──────────┬──────────┬────────────┤
│ SQLite   │ ChromaDB │ PageIndex│ Metadata   │
│ FTS5     │ Vector   │ Tree     │ Filter     │
│ (BM25)   │ Search   │ Search   │ Search     │
├──────────┴──────────┴──────────┴────────────┤
│     Layout-Aware Chunking + Metadata         │
├─────────────────────────────────────────────┤
│   MinerU (magic-pdf) + DocLayout-YOLO        │
│   PDF Layout Analysis & Content Extraction   │
├─────────────────────────────────────────────┤
│          30+ Canonical Textbooks             │
└─────────────────────────────────────────────┘
```

### 7.3 Reference Documents

- Assignment brief: `nlp/assignment2/CST8507_Assignment2_W26.md`
- Proposal: `nlp/assignment2/assignment2_proposal.md`
- Architecture diagram: `nlp/assignment2/CST8507_Assignment2_W26_images/page10_img1.png`
- PageIndex reference: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)
