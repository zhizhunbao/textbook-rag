"""Frontend behavior tests for the Python UI entrypoints.

Refs:
- Okken, Python Testing with pytest: test observable behavior with fake
  collaborators instead of coupling tests to UI framework internals.
- Software Engineering at Google: keep tests focused on stable contracts such
  as state transitions and error handling.
- Krug, Don't Make Me Think: UI flows should preserve user context and recover
  clearly from failures.
- Norman, The Design of Everyday Things: session state and feedback paths should
  maintain a consistent conceptual model for the user.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.models import Chunk, QueryResult, SourceReference  # noqa: E402


def _load_module(module_name: str, relative_path: str, injected_modules: dict | None = None):
    """Load a frontend module from source with optional injected dependencies."""
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    original_modules: dict[str, object] = {}

    for name, injected in (injected_modules or {}).items():
        original_modules[name] = sys.modules.get(name)
        sys.modules[name] = injected

    try:
        assert spec is not None
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _make_chunk(content_type: str = "text") -> Chunk:
    return Chunk(
        chunk_id="chunk-1",
        book_key="book",
        book_title="Book Title",
        chapter="Chapter 1",
        section="",
        page_number=12,
        content_type=content_type,
        text="Chunk text",
        bbox=[0, 0, 1, 1],
    )


class _SessionState(dict):
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value) -> None:
        self[name] = value


class _FakeStreamlit(types.SimpleNamespace):
    def __init__(self) -> None:
        super().__init__()
        self.session_state = _SessionState()
        self.errors: list[str] = []

    def set_page_config(self, **kwargs) -> None:
        self.page_config = kwargs

    def markdown(self, *args, **kwargs) -> None:
        self.last_markdown = (args, kwargs)

    def error(self, message: str) -> None:
        self.errors.append(message)


class _FakeOllamaClient:
    models: list[dict[str, str]] = []

    def __init__(self, host: str) -> None:
        self.host = host

    def list(self) -> dict[str, list[dict[str, str]]]:
        return {"models": list(self.models)}


class _DummyPage:
    def __call__(self, fn):
        return fn


class _FakeUI(types.SimpleNamespace):
    def page(self, route: str):
        self.last_route = route
        return _DummyPage()


class _FakeConfig:
    @staticmethod
    def load(path: Path):
        return {"path": path}


class _FakeBook:
    def __init__(self, book_key: str, book_title: str, total_chunks: int) -> None:
        self.book_key = book_key
        self.book_title = book_title
        self.total_chunks = total_chunks


class _FakeEngine:
    def __init__(self) -> None:
        self.query_calls: list[dict] = []

    def query(self, **kwargs) -> QueryResult:
        self.query_calls.append(kwargs)
        return QueryResult(
            answer="Grounded answer",
            sources=[
                SourceReference(
                    citation_id=1,
                    chunk=_make_chunk("table"),
                    relevance_score=0.875,
                )
            ],
            retrieval_stats={"bm25": "2 hits"},
        )

    def get_available_books(self) -> list[_FakeBook]:
        return [_FakeBook("book", "Book Title", 42)]

    def check_health(self) -> dict[str, bool]:
        return {"sqlite": True, "ollama": False}


def test_gradio_handle_query_preserves_history_when_engine_missing(monkeypatch) -> None:
    """Error handling should keep chat state consistent for the next turn."""
    module = _load_module("frontend_app_gradio_error", "frontend/src/app_gradio.py")
    monkeypatch.setattr(module, "get_engine", lambda: None)

    history = [{"role": "assistant", "content": "ready"}]
    chatbot_history, sources_md, stats_md, state = module.handle_query(
        question="What is retrieval?",
        selected_books=["book"],
        show_text=True,
        show_table=False,
        show_formula=False,
        show_figure=False,
        history=history,
    )

    assert sources_md == ""
    assert stats_md == ""
    assert chatbot_history == state
    assert chatbot_history[-2:] == [
        {"role": "user", "content": "What is retrieval?"},
        {
            "role": "assistant",
            "content": "⚠️ RAG Engine not available. Check system status.",
        },
    ]


def test_gradio_handle_query_formats_sources_and_passes_filters(monkeypatch) -> None:
    """The query handler should pass user filters through and render source metadata."""
    module = _load_module("frontend_app_gradio_success", "frontend/src/app_gradio.py")
    engine = _FakeEngine()
    monkeypatch.setattr(module, "get_engine", lambda: engine)

    chatbot_history, sources_md, stats_md, state = module.handle_query(
        question="Explain embeddings",
        selected_books=["book"],
        show_text=True,
        show_table=True,
        show_formula=False,
        show_figure=False,
        history=[],
    )

    assert engine.query_calls == [
        {
            "question": "Explain embeddings",
            "book_filter": ["book"],
            "content_type_filter": ["text", "table"],
        }
    ]
    assert chatbot_history == state
    assert chatbot_history[-1]["content"] == "Grounded answer"
    assert "**[1]**" in sources_md
    assert "Table" in sources_md
    assert "Relevance: 0.875" in sources_md
    assert "- **bm25**: 2 hits" in stats_md


def test_streamlit_init_session_sets_defaults_and_keeps_existing_values() -> None:
    """Session initialization should fill only missing keys."""
    fake_streamlit = _FakeStreamlit()
    fake_streamlit.session_state.history = [{"question": "existing"}]

    module = _load_module(
        "frontend_app_streamlit_init",
        "frontend/src/app.py",
        {"streamlit": fake_streamlit},
    )
    module.init_session()

    assert fake_streamlit.session_state.engine is None
    assert fake_streamlit.session_state.history == [{"question": "existing"}]
    assert fake_streamlit.session_state.selected_source is None


def test_streamlit_get_badge_class_uses_stable_defaults() -> None:
    """Unknown content types should degrade to the text badge class."""
    fake_streamlit = _FakeStreamlit()
    module = _load_module(
        "frontend_app_streamlit_badges",
        "frontend/src/app.py",
        {"streamlit": fake_streamlit},
    )

    assert module.get_badge_class("figure") == "badge-figure"
    assert module.get_badge_class("unknown") == "badge-text"


def test_streamlit_summarize_book_library_reports_counts_by_category() -> None:
    """Sidebar summaries should expose library size and domain distribution."""
    fake_streamlit = _FakeStreamlit()
    module = _load_module(
        "frontend_app_streamlit_library_summary",
        "frontend/src/app.py",
        {"streamlit": fake_streamlit},
    )
    books = [
        _FakeBook("goodfellow_deep_learning", "Deep Learning", 120),
        _FakeBook("jurafsky_slp3", "Speech and Language Processing", 80),
        _FakeBook("ramalho_fluent_python", "Fluent Python", 60),
        _FakeBook("unknown_book", "Unknown", 10),
    ]

    total_books, total_chunks, category_counts = module.summarize_book_library(
        books,
        {
            "goodfellow_deep_learning": "ml",
            "jurafsky_slp3": "nlp",
            "ramalho_fluent_python": "python",
        },
    )

    assert total_books == 4
    assert total_chunks == 270
    assert category_counts == [
        ("Machine Learning", 1),
        ("Natural Language Processing", 1),
        ("Other", 1),
        ("Python", 1),
    ]


def test_streamlit_load_book_domains_reads_textbook_registry() -> None:
    """Book classification should come from the textbook registry file."""
    fake_streamlit = _FakeStreamlit()
    module = _load_module(
        "frontend_app_streamlit_book_domains",
        "frontend/src/app.py",
        {"streamlit": fake_streamlit},
    )
    module.load_book_domains.cache_clear()
    mapping_path = REPO_ROOT / "frontend" / ".tmp-textbook-skill-mapping.yaml"
    try:
        mapping_path.write_text(
            """
textbooks:
  goodfellow_deep_learning:
    domain: ml
  jurafsky_slp3:
    domain: nlp
""".strip(),
            encoding="utf-8",
        )

        domains = module.load_book_domains(mapping_path)

        assert domains == {
            "goodfellow_deep_learning": "ml",
            "jurafsky_slp3": "nlp",
        }
    finally:
        mapping_path.unlink(missing_ok=True)


def test_streamlit_describe_query_scope_summarizes_scope_and_stages() -> None:
    """Users should see the search scope before the slow query starts."""
    fake_streamlit = _FakeStreamlit()
    module = _load_module(
        "frontend_app_streamlit_query_scope",
        "frontend/src/app.py",
        {"streamlit": fake_streamlit},
    )
    books = [
        _FakeBook("book-1", "Book 1", 10),
        _FakeBook("book-2", "Book 2", 20),
    ]

    lines = module.describe_query_scope(
        selected_books=[],
        content_types=["text", "table"],
        available_books=books,
    )

    assert lines == [
        "Scope: all 2 indexed books",
        "Content types: text, table",
        "Stages: retrieve -> fuse -> generate answer",
    ]


def test_streamlit_resolve_ollama_model_auto_switches_to_local_fallback() -> None:
    """Missing configured models should fall back to an installed local model."""
    fake_streamlit = _FakeStreamlit()
    _FakeOllamaClient.models = [
        {"model": "llama3.2:3b"},
        {"model": "nomic-embed-text:latest"},
    ]
    module = _load_module(
        "frontend_app_streamlit_model_switch",
        "frontend/src/app.py",
        {
            "streamlit": fake_streamlit,
            "ollama": types.SimpleNamespace(Client=_FakeOllamaClient),
        },
    )

    model, notice = module.resolve_ollama_model(
        configured_model="qwen2.5:0.5b",
        available_models=[item["model"] for item in _FakeOllamaClient.models],
    )

    assert model == "llama3.2:3b"
    assert "Automatically switched" in notice


def test_nicegui_get_engine_returns_cached_instance(monkeypatch) -> None:
    """Lazy-loading should cache the created engine instead of recreating it."""
    fake_ui = _FakeUI()
    module = _load_module(
        "frontend_app_nicegui_cache",
        "frontend/src/app_nicegui.py",
        {"nicegui": types.SimpleNamespace(ui=fake_ui)},
    )
    created: list[object] = []

    class FakeRAGEngine:
        def __init__(self, config) -> None:
            self.config = config
            created.append(self)

    monkeypatch.setattr(module, "Config", _FakeConfig)
    monkeypatch.setattr(module, "RAGEngine", FakeRAGEngine)
    module._engine = None

    first = module.get_engine()
    second = module.get_engine()

    assert first is second
    assert len(created) == 1
    assert created[0].config["path"].name == "config.yaml"


def test_nicegui_get_engine_returns_none_on_initialization_error(monkeypatch, capsys) -> None:
    """Initialization failures should be surfaced as a missing engine, not a crash."""
    fake_ui = _FakeUI()
    module = _load_module(
        "frontend_app_nicegui_error",
        "frontend/src/app_nicegui.py",
        {"nicegui": types.SimpleNamespace(ui=fake_ui)},
    )

    class BrokenConfig:
        @staticmethod
        def load(path: Path):
            raise RuntimeError("config missing")

    monkeypatch.setattr(module, "Config", BrokenConfig)
    module._engine = None

    assert module.get_engine() is None
    assert "Failed to initialize RAG engine: config missing" in capsys.readouterr().out
