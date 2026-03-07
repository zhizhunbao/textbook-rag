# Deployment Guide

## Scope

This project is deployed as a local assignment application, not as a split frontend/backend web service.

Runtime shape:

- one Python UI process (`Streamlit`, `Gradio`, or `NiceGUI`)
- one local Ollama service
- local textbook and index data on disk
- later, one ROS 2 node wrapping the same `RAGEngine`

This matches the assignment requirements in:

- `nlp/assignment2/CST8507_Assignment2_W26.md`
- `docs/requirements/requirements.md`
- `docs/requirements/prd.md`

## Prerequisites

- Windows or Ubuntu
- Python 3.10+
- `uv`
- Ollama installed
- textbook source files under `textbooks/`
- MinerU outputs under `data/mineru_output/`
- built indexes under `backend/data/`

Recommended local model:

- `qwen2.5:0.5b`

## Runtime Configuration

Primary runtime settings live in [backend/config.yaml](/c:/Users/40270/OneDrive/Desktop/workspace/textbook-rag/backend/config.yaml).

Important fields:

- `ollama.host`
- `ollama.model`
- `paths.mineru_output`
- `paths.textbooks_dir`
- `paths.sqlite_db`
- `paths.chroma_db`
- `paths.pageindex_trees`

Reference environment values are documented in [.env.example](/c:/Users/40270/OneDrive/Desktop/workspace/textbook-rag/.env.example).

## Local Setup

### 1. Install Python dependencies

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv sync --extra dev
```

### 2. Start Ollama

```powershell
ollama serve
```

In another terminal, pull the model if needed:

```powershell
ollama pull qwen2.5:0.5b
```

### 3. Verify local data

Expected local assets:

- `textbooks/`
- `data/mineru_output/`
- `backend/data/textbook_qa.db`
- `backend/data/chroma_db/`
- `backend/data/pageindex_trees/`

### 4. Validate the repository layout

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv run python .agent/scripts/env_check.py --files
```

## Launch Options

Choose one Python UI entrypoint.

### Streamlit

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv run streamlit run frontend/src/app.py
```

### Gradio

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv run python frontend/src/app_gradio.py
```

### NiceGUI

```powershell
$env:UV_CACHE_DIR=".uv-cache"
uv run python frontend/src/app_nicegui.py
```

## Smoke Test

After launch:

1. Ask a question such as `What is the Adam optimizer?`
2. Confirm an answer is returned.
3. Confirm source references are shown.
4. Confirm source tracing or source metadata is visible.
5. Stop and fix the environment if Ollama is unavailable or indexes are missing.

## Failure Recovery

Common issues:

- Ollama not running
  - Fix: start `ollama serve`
- model missing
  - Fix: run `ollama pull qwen2.5:0.5b`
- index files missing
  - Fix: rebuild or restore `backend/data/`
- textbook or MinerU paths wrong
  - Fix: correct `backend/config.yaml`
- sandbox pytest temp cleanup fails on Windows
  - Fix: use a dedicated `--basetemp` or run outside the restricted sandbox

## Rollback

This assignment project is local-first, so rollback is configuration and artifact based:

1. Stop the current UI process.
2. Restore the previous `backend/config.yaml` if it was changed.
3. Restore previous index artifacts under `backend/data/` if they were replaced.
4. Relaunch the last known-good UI entrypoint.

## ROS 2 Handoff

Part 2 does not require the Part 1 UI.

The handoff target is a ROS 2 node that wraps the same RAG logic:

- subscribe: `words`
- publish: `ollama_reply`

The assignment reference is in [CST8507_Assignment2_W26.md](/c:/Users/40270/OneDrive/Desktop/workspace/textbook-rag/nlp/assignment2/CST8507_Assignment2_W26.md).

Recommended sequence for Part 2:

1. Keep `RAGEngine` importable without UI side effects.
2. Move or adapt query orchestration into `ollama_publisher.py`.
3. Load model/path parameters via ROS 2 parameters.
4. Run `colcon build`.
5. Start the speaking and hearing nodes in separate terminals.

## Deliverable Position

For this repository, deployment means:

- the local environment can be reproduced
- one supported UI launcher can be started
- Ollama and local indexes are documented
- ROS 2 integration handoff is documented

It does not require:

- FastAPI
- cloud hosting
- a separate JavaScript frontend build
- public web deployment
