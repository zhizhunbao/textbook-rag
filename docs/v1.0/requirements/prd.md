# AI Textbook Q&A System — Product Requirements Document (PRD)

## Document Info

- **Version**: 1.0
- **Author**: Alice (Product Manager)
- **Date**: 2026-03-04
- **Status**: Draft
- **Input**: `docs/requirements/requirements.md`

---

## 1. Product Overview

### 1.1 Product Vision

A **local-first, RAG-based educational Q&A system** that lets students ask natural language questions about AI/ML concepts and receive accurate, grounded answers with **deep source tracing** — pinpointing the exact textbook page and spatial region where each piece of evidence was found, rendered as a highlighted bounding box on the original PDF.

### 1.2 Target Users

| Persona             | Role                                     | Key Need                                                                     |
| ------------------- | ---------------------------------------- | ---------------------------------------------------------------------------- |
| Student Sarah       | AI/ML student                            | Find authoritative answers across multiple textbooks with verifiable sources |
| Professor Ali       | Course instructor evaluating submissions | Verify grounded, non-hallucinated answers with transparent tracing           |
| Robot User (Part 2) | Voice interaction via iRobot Create 3    | Spoken Q&A powered by the same RAG pipeline                                  |

### 1.3 Core Value Proposition

1. **Deep source tracing** — pixel-level traceability, not just page numbers
2. **Layout-aware parsing** — tables, formulas, and figures remain intact
3. **Hybrid retrieval** — 4 complementary methods fused via RRF for maximum recall
4. **Low resource** — runs entirely local on <1.5 GB total model memory

---

## 2. User Stories

### 2.1 Epic List

| Epic | Description                   | Stories         |
| ---- | ----------------------------- | --------------- |
| E1   | Document Processing Pipeline  | US-001 – US-004 |
| E2   | Indexing & Retrieval          | US-005 – US-010 |
| E3   | Answer Generation             | US-011 – US-012 |
| E4   | Streamlit UI & Source Tracing | US-013 – US-017 |
| E5   | Evaluation                    | US-018 – US-019 |
| E6   | ROS 2 Integration (Part 2)    | US-020 – US-022 |

### 2.2 User Story Details

---

#### Epic 1: Document Processing Pipeline

**US-001: PDF Layout Analysis**
As a system operator,
I want MinerU (magic-pdf) to detect document regions (text, tables, formulas, figures) with bounding box coordinates,
so that the system can process each content type appropriately.

_Acceptance Criteria:_

- Given a PDF textbook is provided
- When the layout analysis runs
- Then each page produces a list of detected regions with types (text / table / formula / figure / title) and bbox coordinates
- And the DocLayout-YOLO model runs on GPU if available, falling back to CPU

**US-002: Specialized Content Extraction**
As a system operator,
I want text to be extracted as plain text, tables as HTML, formulas as LaTeX, and figures as image + caption,
so that document structure is preserved for accurate retrieval.

_Acceptance Criteria:_

- Given layout analysis has detected regions on a page
- When extraction runs
- Then text regions produce plain text, table regions produce HTML, formula regions produce LaTeX, figure regions produce an image file + caption text
- And each extracted element retains its source metadata (book_key, page, bbox)

**US-003: Layout-Aware Chunking**
As a system operator,
I want the system to chunk documents intelligently — keeping tables and formulas intact as single chunks,
so that retrieval returns coherent, complete pieces of information.

_Acceptance Criteria:_

- Given extracted content from a textbook
- When chunking runs
- Then tables and formulas are never split across chunks
- And each chunk carries metadata: book_key, chapter, section, page_number, content_type, bbox
- And text chunks are ≤ 512 tokens with ≈ 50-token overlap

**US-004: Batch Processing**
As a system operator,
I want to process all 30+ textbook PDFs in batch with progress tracking,
so that the full dataset can be indexed efficiently.

_Acceptance Criteria:_

- Given a directory of PDF files
- When batch processing is triggered
- Then each PDF is processed sequentially (or in parallel if resources allow)
- And progress is logged (e.g., "Processing 5/32: bishop_prml.pdf")
- And failures on one book do not halt the entire batch

---

#### Epic 2: Indexing & Retrieval

**US-005: SQLite FTS5 Index**
As a system operator,
I want all chunks indexed in a SQLite database with FTS5 full-text search,
so that exact keyword matching with BM25 ranking is available.

_Acceptance Criteria:_

- Given processed chunks with metadata
- When indexing runs
- Then a SQLite database is created with an FTS5 virtual table
- And each row contains: chunk_id, book_key, chapter, page, section, content_type, bbox_json, text_content
- And BM25 ranking is configured

**US-006: ChromaDB Vector Index**
As a system operator,
I want all chunks embedded and stored in ChromaDB using sentence-transformers (all-MiniLM-L6-v2),
so that semantic similarity retrieval is available.

_Acceptance Criteria:_

- Given processed chunks
- When embedding and indexing runs
- Then embeddings are generated using all-MiniLM-L6-v2 (≈ 80 MB model)
- And stored in a persistent ChromaDB collection
- And each document carries the same metadata as the SQLite index

**US-007: PageIndex Tree Generation**
As a system operator,
I want a hierarchical table-of-contents tree generated for each textbook,
so that the LLM can navigate the tree to locate relevant sections.

_Acceptance Criteria:_

- Given a processed textbook with detected title/heading regions
- When tree generation runs
- Then a JSON tree structure is produced with nodes: {title, level, page_start, page_end, children[]}
- And the tree can be serialized for LLM prompting

**US-008: BM25 Keyword Search**
As a student,
I want to search for exact keywords across all textbooks,
so that I can find specific terms, definitions, and named concepts.

_Acceptance Criteria:_

- Given a user query containing specific terms (e.g., "Adam optimizer")
- When BM25 search executes
- Then results are ranked by BM25 score
- And each result contains chunk text + metadata (book, chapter, page, bbox)
- And query latency < 100ms

**US-009: Semantic Search**
As a student,
I want to search using natural language that may not match exact keywords,
so that I can find conceptually related content even with paraphrased queries.

_Acceptance Criteria:_

- Given a user query (e.g., "how does the model avoid overfitting?")
- When semantic search executes via ChromaDB
- Then results are ranked by cosine similarity
- And conceptually related chunks are returned even without exact keyword overlap

**US-010: PageIndex Tree Search**
As a student,
I want the system to reason about which textbook sections are most relevant by navigating the TOC tree,
so that retrieval mimics how humans search through textbooks.

_Acceptance Criteria:_

- Given a user query
- When PageIndex tree search executes
- Then the LLM receives the top-level TOC nodes and selects the most relevant branches
- And the LLM drills down into selected branches to find specific sections
- And the final selected sections' chunks are returned as results

---

#### Epic 3: Answer Generation

**US-011: RRF Fusion**
As a student,
I want results from all four retrieval methods combined into a single ranked list,
so that I receive the best possible set of evidence chunks.

_Acceptance Criteria:_

- Given results from BM25, Semantic, PageIndex, and Metadata Filter searches
- When RRF fusion executes
- Then results are combined using the formula: `score(d) = Σ 1/(k + rank_i(d))` with k=60
- And duplicate chunks (same chunk_id) are merged, keeping the highest fused score
- And the top-N chunks (N configurable, default 5) are passed to the LLM

**US-012: LLM Answer Generation**
As a student,
I want the system to generate a concise, grounded answer using the retrieved context,
so that I receive an accurate response backed by textbook content.

_Acceptance Criteria:_

- Given top-N retrieved chunks and the user's question
- When the LLM (Ollama qwen2.5:0.5b) generates an answer
- Then the answer references only information present in the provided context
- And the answer includes inline citations (e.g., [1], [2]) mapping to specific source chunks
- And if no relevant context is found, the system responds: "I could not find relevant information in the textbooks"

---

#### Epic 4: Streamlit UI & Source Tracing

**US-013: Question Input**
As a student,
I want a text input field where I can type natural language questions,
so that I can interact with the system easily.

_Acceptance Criteria:_

- Given the Streamlit app is running
- When I type a question and press Enter or click "Ask"
- Then the query is sent to the RAG pipeline
- And a loading indicator is shown during processing

**US-014: Answer Display**
As a student,
I want the generated answer displayed clearly with inline citations,
so that I can read the response and trace each claim to its source.

_Acceptance Criteria:_

- Given an answer has been generated
- When it is displayed
- Then the answer text is shown with numbered inline citations [1], [2], etc.
- And a source reference list appears below the answer

**US-015: Source Reference List**
As a student,
I want a list of source references showing book title, chapter, page number, and content type for each citation,
so that I know exactly where each piece of information came from.

_Acceptance Criteria:_

- Given citations [1], [2], … in the answer
- When the reference list is displayed
- Then each reference shows: citation number, book title, chapter, page number, content type badge (text/table/formula/figure)
- And each reference is clickable

**US-016: PDF Page Viewer with Bbox Highlighting**
As a student,
I want to click a source reference and see the original PDF page with the relevant region highlighted,
so that I can verify the answer against the original material.

_Acceptance Criteria:_

- Given I click a source reference
- When the PDF viewer opens
- Then the original PDF page is rendered
- And a yellow bounding box highlights the exact region (text block / table / formula) that was used
- And I can zoom in/out on the page

**US-017: Multi-Turn Session**
As a student,
I want to ask multiple questions in a single session,
so that I can explore related topics without restarting the app.

_Acceptance Criteria:_

- Given I have asked a question and received an answer
- When I type a new question
- Then the previous Q&A remains visible in the chat history
- And the new query is processed independently (no conversation memory required for v1)

---

#### Epic 5: Evaluation

**US-018: 20-Question Evaluation Set**
As a course instructor,
I want 20 domain-specific evaluation questions spanning multiple textbooks,
so that the system's accuracy can be measured objectively.

_Acceptance Criteria:_

- Given 20 questions are prepared covering ML, NLP, math, RL, CV, Python topics
- When each question is run through the system
- Then the answer and top-3 retrieved chunks are recorded
- And each answer is scored: 1 (correct), 0.5 (partially correct), 0 (incorrect)
- And each retrieved chunk is marked as relevant or not relevant

**US-019: Accuracy Report**
As a course instructor,
I want an accuracy report summarizing the evaluation results,
so that system performance is documented for the final report.

_Acceptance Criteria:_

- Given all 20 questions have been evaluated
- When the report is generated
- Then it includes: average accuracy score, per-question breakdown, retrieval relevance statistics
- And the target is ≥ 80% average accuracy

---

#### Epic 6: ROS 2 Integration (Part 2)

**US-020: OOP Refactoring**
As a developer,
I want the RAG pipeline code refactored into an OOP class structure,
so that it can be easily wrapped as a ROS 2 node.

_Acceptance Criteria:_

- Given the RAG pipeline functions
- When refactored
- Then the core logic is encapsulated in a class (e.g., `RAGEngine`) with methods: `load_index()`, `query(question: str) -> Answer`
- And the class is importable without side effects

**US-021: ROS 2 Node**
As a robot developer,
I want a ROS 2 node (`ollama_publisher`) that subscribes to `words` topic and publishes to `ollama_reply`,
so that the RAG pipeline integrates into the vocal interaction architecture.

_Acceptance Criteria:_

- Given the ROS 2 node is running
- When a String message arrives on the `words` topic
- Then the RAG pipeline processes the question
- And publishes the answer as a String on `ollama_reply`
- And the model name and knowledge path are configurable via ROS 2 parameters

**US-022: Full Pipeline Test**
As a robot developer,
I want to verify the full vocal interaction pipeline: Whisper → RAG → gTTS,
so that end-to-end functionality is confirmed.

_Acceptance Criteria:_

- Given all nodes are running (recording_publisher, words_publisher, ollama_publisher, speak_client, speak)
- When a user speaks a question
- Then the spoken answer is heard within 60 seconds
- And the answer is grounded in the knowledge base content

---

## 3. Functional Requirements (MoSCoW)

### 3.1 Must Have (P0)

| ID     | Feature                             | Stories         |
| ------ | ----------------------------------- | --------------- |
| F1     | PDF layout analysis with MinerU     | US-001          |
| F2     | Specialized content extraction      | US-002          |
| F3     | Layout-aware chunking with metadata | US-003          |
| F4     | SQLite FTS5 index (BM25)            | US-005          |
| F5     | ChromaDB vector index               | US-006          |
| F6     | PageIndex tree generation           | US-007          |
| F7–F10 | Four retrieval methods              | US-008 – US-010 |
| F11    | RRF fusion                          | US-011          |
| F12    | LLM answer generation (Ollama)      | US-012          |
| F13    | Deep source tracing with PDF bbox   | US-016          |
| F14    | Streamlit UI                        | US-013 – US-015 |
| F15    | Multi-turn sessions                 | US-017          |

### 3.2 Should Have (P1)

| ID  | Feature                        | Stories        |
| --- | ------------------------------ | -------------- |
| A1  | OOP code structure             | US-020         |
| A2  | ROS 2 node conversion          | US-021         |
| A3  | Batch processing with progress | US-004         |
| A4  | 20-question evaluation         | US-018, US-019 |

### 3.3 Could Have (P2)

| ID  | Feature                    | Description                                     |
| --- | -------------------------- | ----------------------------------------------- |
| A4  | Content type badges in UI  | Visual indicators for text/table/formula/figure |
| A5  | Query history sidebar      | Recent queries for quick re-access              |
| A6  | Metadata filter search (④) | Structured filtering by book/chapter/page/type  |

### 3.4 Won't Have (Future)

- Multi-language question support
- Conversation memory across sessions
- Cloud deployment
- Custom model fine-tuning
- Automated LLM-as-judge evaluation

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Metric                                 | Target                     |
| -------------------------------------- | -------------------------- |
| Query latency (retrieval + generation) | < 30s on CPU               |
| BM25 query latency                     | < 100ms                    |
| Indexing throughput                    | All 30+ books in < 2 hours |
| Model memory                           | qwen2.5:0.5b ≈ 0.4 GB      |
| Total memory (all models)              | < 1.5 GB                   |

### 4.2 Security

- All models run locally (no data leaves machine)
- No hardcoded credentials; use environment variables
- Input sanitization to prevent prompt injection

### 4.3 Compatibility

- Python 3.10+
- Windows / Ubuntu (development on Windows, ROS 2 on Ubuntu)
- GPU optional (CUDA for DocLayout-YOLO acceleration; CPU fallback)

---

## 5. Acceptance Criteria Summary

### 5.1 Functional Acceptance

| #   | Criterion                                                   | User Story     |
| --- | ----------------------------------------------------------- | -------------- |
| AC1 | ≥80% accuracy on 20 evaluation questions                    | US-018, US-019 |
| AC2 | Every answer has ≥1 source reference with book/chapter/page | US-014, US-015 |
| AC3 | Clicking source shows PDF page with highlighted bbox        | US-016         |
| AC4 | Tables, formulas, figures preserved in chunking             | US-002, US-003 |
| AC5 | All four retrieval methods contribute to RRF                | US-008–US-011  |
| AC6 | Total model memory < 1.5 GB                                 | US-012         |
| AC7 | Multi-turn session supports 5+ sequential queries           | US-017         |
| AC8 | Answers grounded in documents (no hallucination)            | US-012         |

### 5.2 Non-Functional Acceptance

| #   | Criterion                                          | Verification              |
| --- | -------------------------------------------------- | ------------------------- |
| NF1 | Query latency < 30s                                | Timed test with 5 queries |
| NF2 | Single-command startup: `streamlit run app.py`     | Manual verification       |
| NF3 | Graceful errors for missing Ollama / empty results | Manual test               |

---

## 6. Milestones

### 6.1 MVP Scope (Week 1–2)

- PDF processing pipeline (MinerU)
- Dual indexing (SQLite FTS5 + ChromaDB)
- Basic BM25 + semantic retrieval
- Simple LLM query via Ollama

### 6.2 V1.0 Scope (Week 3–4)

- All four retrieval methods + RRF fusion
- PageIndex tree generation and search
- Full Streamlit UI with deep source tracing
- 20-question evaluation with accuracy report

### 6.3 Future (Week 5+)

- ROS 2 node conversion and full pipeline test
- Final report and presentation

---

## 7. Risks & Dependencies

### 7.1 Risk List

| #   | Risk                                                    | Impact                         | Probability | Mitigation                                                               |
| --- | ------------------------------------------------------- | ------------------------------ | ----------- | ------------------------------------------------------------------------ |
| R1  | MinerU struggles with scanned/image-heavy PDFs          | Tables/formulas lost           | Medium      | Use pre-processed markdown from existing data/mineru_output if available |
| R2  | qwen2.5:0.5b too weak for complex reasoning             | Low answer quality             | Medium      | Test early; consider qwen2.5:1.5b if memory budget allows                |
| R3  | ChromaDB indexing slow on 30+ books                     | Delays Week 2 milestone        | Low         | Index books incrementally; parallelize if possible                       |
| R4  | PageIndex tree search adds too much latency             | Query > 30s                    | Medium      | Make PageIndex search optional; skip if latency budget exceeded          |
| R5  | Bounding box coordinates misaligned after PDF rendering | Source highlighting inaccurate | Medium      | Validate bbox on 5 sample pages before full pipeline                     |

### 7.2 External Dependencies

| Dependency            | Version     | Purpose                            |
| --------------------- | ----------- | ---------------------------------- |
| Ollama                | 0.14+       | Local LLM serving                  |
| MinerU (magic-pdf)    | Latest      | PDF layout analysis                |
| ChromaDB              | Latest      | Vector store                       |
| sentence-transformers | Latest      | Embedding model (all-MiniLM-L6-v2) |
| Streamlit             | Latest      | Web UI framework                   |
| SQLite                | 3.35+       | FTS5 support                       |
| ROS 2 (Part 2)        | Humble/Iron | Robot integration                  |

---

## 8. Appendix

### 8.1 Glossary

| Term      | Definition                                                                          |
| --------- | ----------------------------------------------------------------------------------- |
| RAG       | Retrieval-Augmented Generation — augments LLM with retrieved context                |
| RRF       | Reciprocal Rank Fusion — score-based method to combine multiple ranked lists        |
| FTS5      | Full-Text Search version 5 — SQLite's built-in full-text search extension           |
| BM25      | Best Matching 25 — probabilistic ranking function for information retrieval         |
| PageIndex | Hierarchical TOC tree used for LLM-driven section navigation                        |
| bbox      | Bounding box — rectangular coordinates (x0, y0, x1, y1) defining a region on a page |
| MinerU    | Layout-aware PDF parsing tool using DocLayout-YOLO for region detection             |

### 8.2 Reference Documents

- Requirements: `docs/requirements/requirements.md`
- Assignment brief: `nlp/assignment2/CST8507_Assignment2_W26.md`
- Proposal: `nlp/assignment2/assignment2_proposal.md`
- PageIndex: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)
