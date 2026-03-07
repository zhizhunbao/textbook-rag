# Streamlit UI — AI Textbook Q&A System
# Run: streamlit run frontend/src/app.py
# Ref: Krug, Don't Make Me Think, Ch1 — self-evident pages need no explanation;
#      our chat_input and source cards are immediately understandable
# Ref: Krug, Ch3 — visual hierarchy for scanning: badges, section headers, cards
# Ref: Norman, Design of Everyday Things, Ch1 — affordances: buttons/cards look clickable

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from functools import lru_cache
import sys
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from ollama import Client  # noqa: E402

from backend.app.config import Config  # noqa: E402
from backend.app.rag_engine import RAGEngine  # noqa: E402

st.set_page_config(
    page_title="AI Textbook Q&A",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
}

.source-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
    transition: all 0.2s ease;
    cursor: pointer;
}
.source-card:hover {
    border-color: #6366f1;
    box-shadow: 0 4px 6px rgba(99, 102, 241, 0.1);
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
}
.badge-text { background: #eef2ff; color: #6366f1; }
.badge-table { background: #f5f3ff; color: #8b5cf6; }
.badge-formula { background: #fdf2f8; color: #ec4899; }
.badge-figure { background: #f0fdfa; color: #14b8a6; }

.citation {
    background: #eef2ff;
    color: #6366f1;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
}

.main-title {
    font-size: 28px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 4px;
}
.subtitle {
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 24px;
}
</style>
""",
    unsafe_allow_html=True,
)


def init_session() -> None:
    """Initialize session state variables."""
    if "engine" not in st.session_state:
        st.session_state.engine = None
    if "engine_model" not in st.session_state:
        st.session_state.engine_model = None
    if "configured_model" not in st.session_state:
        st.session_state.configured_model = None
    if "available_models" not in st.session_state:
        st.session_state.available_models = []
    if "model_notice" not in st.session_state:
        st.session_state.model_notice = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "selected_source" not in st.session_state:
        st.session_state.selected_source = None


def list_ollama_models(host: str) -> tuple[list[str], str | None]:
    """List locally installed Ollama models."""
    try:
        response = Client(host=host).list()
    except Exception as exc:
        return [], f"Could not inspect local Ollama models: {exc}"

    models = [item["model"] for item in response.get("models", [])]
    return models, None


def resolve_ollama_model(
    configured_model: str,
    available_models: list[str],
    fallback_order: list[str] | None = None,
) -> tuple[str, str | None]:
    """Resolve the model to a locally available Ollama model.

    Ref: Krug, Don't Make Me Think - error recovery should be obvious.
    Ref: Norman, Design of Everyday Things - systems should give clear feedback
    and reduce user error when a fix can be automated safely.
    """
    available = set(available_models)
    if configured_model in available:
        return configured_model, None

    preferred = fallback_order or [
        "qwen2.5:0.5b",
        "llama3.2:3b",
        "llama3.2:latest",
        "qwen3.5:27b",
    ]
    for candidate in preferred:
        if candidate in available:
            return (
                candidate,
                f"Configured model '{configured_model}' is unavailable. "
                f"Automatically switched to '{candidate}'.",
            )

    if available:
        candidate = sorted(available)[0]
        return (
            candidate,
            f"Configured model '{configured_model}' is unavailable. "
            f"Automatically switched to '{candidate}'.",
        )

    return configured_model, "No local Ollama models were found."


def build_engine(selected_model: str) -> RAGEngine:
    """Create a RAG engine for the selected Ollama model."""
    config = Config.load(_PROJECT_ROOT / "backend" / "config.yaml")
    runtime_config = replace(
        config,
        ollama=replace(config.ollama, model=selected_model),
    )
    st.session_state.configured_model = config.ollama.model
    return RAGEngine(runtime_config)


def set_engine_model(selected_model: str, notice: str | None = None) -> None:
    """Replace the cached engine with a new one using the selected model."""
    old_engine = st.session_state.engine
    if old_engine is not None:
        old_engine.close()
    st.session_state.engine = build_engine(selected_model)
    st.session_state.engine_model = selected_model
    st.session_state.model_notice = notice


def get_engine() -> RAGEngine | None:
    """Lazy-load the RAG engine."""
    if st.session_state.engine is None:
        try:
            config = Config.load(_PROJECT_ROOT / "backend" / "config.yaml")
            available_models, list_notice = list_ollama_models(config.ollama.host)
            st.session_state.available_models = available_models
            resolved_model, notice = resolve_ollama_model(
                configured_model=config.ollama.model,
                available_models=available_models,
            )
            set_engine_model(
                resolved_model,
                notice=notice or list_notice,
            )
        except Exception as exc:
            st.error(f"Failed to initialize RAG engine: {exc}")
            return None
    return st.session_state.engine


def get_badge_class(content_type: str) -> str:
    """Get CSS class for content type badge."""
    return {
        "text": "badge-text",
        "table": "badge-table",
        "formula": "badge-formula",
        "figure": "badge-figure",
    }.get(content_type, "badge-text")


@lru_cache(maxsize=1)
def load_book_domains(mapping_path: Path | None = None) -> dict[str, str]:
    """Load textbook domains from the textbook registry."""
    source_path = mapping_path or (
        _PROJECT_ROOT / ".agent" / "config" / "textbook-skill-mapping.yaml"
    )
    with source_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    textbooks = raw.get("textbooks", {})
    return {
        book_key: metadata.get("domain", "other")
        for book_key, metadata in textbooks.items()
    }


def summarize_book_library(
    books: list,
    domain_map: dict[str, str],
) -> tuple[int, int, list[tuple[str, int]]]:
    """Build total counts and category counts for the sidebar.

    Ref: Krug, Don't Make Me Think, Ch1 - make important system scope obvious.
    Ref: Norman, Design of Everyday Things, Ch1 - visible state reduces guessing.
    """
    total_books = len(books)
    total_chunks = sum(getattr(book, "total_chunks", 0) for book in books)
    counts = Counter(domain_map.get(book.book_key, "other") for book in books)
    category_labels = {
        "algorithms": "Algorithms",
        "cv": "Computer Vision",
        "ir": "Information Retrieval",
        "javascript": "JavaScript",
        "math": "Mathematics",
        "ml": "Machine Learning",
        "nlp": "Natural Language Processing",
        "python": "Python",
        "rl": "Reinforcement Learning",
        "se": "Software Engineering",
        "other": "Other",
    }
    ordered = sorted(
        (
            category_labels.get(category, category.replace("_", " ").title()),
            count,
        )
        for category, count in counts.items()
    )
    return total_books, total_chunks, ordered


def describe_query_scope(
    selected_books: list[str],
    content_types: list[str],
    available_books: list,
) -> list[str]:
    """Describe what the current query will search."""
    book_scope = (
        f"{len(selected_books)} selected book(s)"
        if selected_books
        else f"all {len(available_books)} indexed books"
    )
    content_scope = ", ".join(content_types) if content_types else "no content types"
    return [
        f"Scope: {book_scope}",
        f"Content types: {content_scope}",
        "Stages: retrieve -> fuse -> generate answer",
    ]


def main() -> None:
    """Render the Streamlit UI."""
    init_session()

    with st.sidebar:
        st.markdown("### 📚 AI Textbook Q&A")
        st.markdown("---")

        engine = get_engine()

        if engine:
            available_models = st.session_state.available_models
            if st.session_state.model_notice:
                st.warning(st.session_state.model_notice)

            if available_models:
                selected_model = st.selectbox(
                    "Model",
                    options=available_models,
                    index=available_models.index(st.session_state.engine_model),
                    help="Choose any locally installed Ollama model.",
                )
                if selected_model != st.session_state.engine_model:
                    set_engine_model(selected_model)
                    st.rerun()

            books = engine.get_available_books()
            domain_map = load_book_domains()
            total_books, total_chunks, category_counts = summarize_book_library(
                books,
                domain_map,
            )

            st.markdown("**Library Overview**")
            st.caption(f"{total_books} books indexed")
            st.caption(f"{total_chunks} chunks searchable")
            if category_counts:
                with st.expander("Categories", expanded=True):
                    for category, count in category_counts:
                        st.markdown(f"- {category}: {count}")

            book_options = {
                book.book_key: f"{book.book_title} ({book.total_chunks})"
                for book in books
            }
            selected_books = st.multiselect(
                "📖 Filter by Books",
                options=list(book_options.keys()),
                format_func=lambda key: book_options.get(key, key),
                help="Leave empty to search all books",
            )

            st.markdown("**Content Types**")
            show_text = st.checkbox("Text", value=True)
            show_table = st.checkbox("Tables", value=True)
            show_formula = st.checkbox("Formulas", value=True)
            show_figure = st.checkbox("Figures", value=True)

            content_types = []
            if show_text:
                content_types.append("text")
            if show_table:
                content_types.append("table")
            if show_formula:
                content_types.append("formula")
            if show_figure:
                content_types.append("figure")

            st.markdown("---")
            health = engine.check_health()
            st.markdown("**System Status**")
            if st.session_state.engine_model:
                st.caption(f"Model: {st.session_state.engine_model}")
            for component, ok in health.items():
                icon = "✅" if ok else "❌"
                st.markdown(f"{icon} {component}")
        else:
            books = []
            selected_books = []
            content_types = ["text", "table", "formula", "figure"]

        if st.session_state.history:
            st.markdown("---")
            st.markdown("**Query History**")
            for entry in reversed(st.session_state.history[-10:]):
                question = entry["question"]
                preview = question[:50] + "..." if len(question) > 50 else question
                st.caption(f"▸ {preview}")

    st.markdown('<div class="main-title">📚 AI Textbook Q&A</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Ask questions about AI, ML, NLP, and more — '
        "grounded in 30+ canonical textbooks with source tracing</div>",
        unsafe_allow_html=True,
    )

    question = st.chat_input("Ask a question about AI/ML textbooks...")

    if question:
        engine = get_engine()
        if engine is None:
            st.error("⚠️ RAG Engine not available. Check system status in sidebar.")
            return

        query_scope_lines = describe_query_scope(
            selected_books=selected_books,
            content_types=content_types,
            available_books=books,
        )
        with st.status("Searching your textbook library...", expanded=True) as status:
            for line in query_scope_lines:
                status.write(line)
            result = engine.query(
                question=question,
                book_filter=selected_books or None,
                content_type_filter=content_types or None,
                progress_callback=status.write,
            )
            status.update(label="Search complete", state="complete", expanded=False)

        st.session_state.history.append(
            {
                "question": question,
                "result": result,
            }
        )

    if st.session_state.history:
        latest = st.session_state.history[-1]
        result = latest["result"]

        st.markdown(f"**🔍 Question:** {latest['question']}")

        with st.expander("📊 Retrieval Statistics", expanded=False):
            for method, stat in result.retrieval_stats.items():
                st.text(f"  {method}: {stat}")

        st.markdown("---")
        st.markdown("### 💡 Answer")
        st.markdown(result.answer)

        if result.sources:
            st.markdown("---")
            st.markdown("### 📖 Sources")

            cols = st.columns(min(len(result.sources), 3))
            for i, source in enumerate(result.sources):
                with cols[i % 3]:
                    badge_class = get_badge_class(source.chunk.content_type)
                    st.markdown(
                        f'<div class="source-card">'
                        f"<strong>[{source.citation_id}]</strong> "
                        f'<span class="badge {badge_class}">{source.chunk.content_type}</span><br>'
                        f"📖 {source.chunk.book_title}<br>"
                        f"<small>{source.chunk.chapter} · p.{source.chunk.page_number}</small>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if st.button(f"🔍 View Source [{source.citation_id}]", key=f"src_{i}"):
                        st.session_state.selected_source = source

            if st.session_state.selected_source:
                source = st.session_state.selected_source
                st.markdown("---")
                st.markdown(
                    f"### 📄 Source Viewer — {source.chunk.book_title}, "
                    f"p.{source.chunk.page_number}"
                )

                img = engine.render_source(
                    book_key=source.chunk.book_key,
                    page_number=source.chunk.page_number,
                    bbox=source.chunk.bbox,
                )

                if img is not None:
                    st.image(img, use_container_width=True)
                else:
                    st.warning(
                        "PDF not available for viewing. Showing text content instead:"
                    )
                    st.code(source.chunk.text[:2000])

    else:
        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; padding: 60px 0; color: #6b7280;">
                <div style="font-size: 48px; margin-bottom: 16px;">💭</div>
                <div style="font-size: 18px; font-weight: 600;">Ask your first question</div>
                <div style="font-size: 14px; margin-top: 8px;">
                    Try: "What is the Adam optimizer?" or "Explain backpropagation"
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
