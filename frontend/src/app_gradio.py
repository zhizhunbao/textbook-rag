# Gradio UI — AI Textbook Q&A System
# Run: python frontend/src/app_gradio.py
# Ref: Gradio's Blocks API enables flexible, component-based UI composition
# Ref: Krug, Don't Make Me Think - error recovery should be obvious and should
# preserve the user's sense of where they are in the flow.

from __future__ import annotations

import sys
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import gradio as gr  # noqa: E402

from backend.app.config import Config  # noqa: E402
from backend.app.rag_engine import RAGEngine  # noqa: E402

# ─── RAG Engine Singleton ─────────────────────────────────────────
_engine: RAGEngine | None = None


def get_engine() -> RAGEngine | None:
    """Lazy-load the RAG engine (singleton)."""
    global _engine
    if _engine is None:
        try:
            config = Config.load(_PROJECT_ROOT / "backend" / "config.yaml")
            _engine = RAGEngine(config)
        except Exception as exc:
            print(f"Failed to initialize RAG engine: {exc}")
            return None
    return _engine


# ─── Helper Functions ─────────────────────────────────────────────
def format_badge(content_type: str) -> str:
    """Return an emoji badge for content type."""
    return {
        "text": "📝 Text",
        "table": "📊 Table",
        "formula": "🔢 Formula",
        "figure": "🖼️ Figure",
    }.get(content_type, "📝 Text")


def get_books() -> list[str]:
    """Fetch available book keys from engine."""
    engine = get_engine()
    if engine is None:
        return []
    books = engine.get_available_books()
    return [b.book_key for b in books]


def get_book_labels() -> dict[str, str]:
    """Fetch book_key → display label mapping."""
    engine = get_engine()
    if engine is None:
        return {}
    books = engine.get_available_books()
    return {b.book_key: f"{b.book_title} ({b.total_chunks} chunks)" for b in books}


def get_health() -> str:
    """Return health status as formatted text."""
    engine = get_engine()
    if engine is None:
        return "❌ RAG Engine not loaded"
    health = engine.check_health()
    lines = []
    for comp, ok in health.items():
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} {comp}")
    return "\n".join(lines)


# ─── Query Handler ────────────────────────────────────────────────
def handle_query(
    question: str,
    selected_books: list[str],
    show_text: bool,
    show_table: bool,
    show_formula: bool,
    show_figure: bool,
    history: list[dict],
) -> tuple:
    """Process a question through the RAG pipeline.

    Returns:
        Tuple of (chatbot_history, sources_md, stats_md, updated_history_state).
    """
    engine = get_engine()
    if engine is None:
        error_msg = "⚠️ RAG Engine not available. Check system status."
        new_history = history + [{"role": "user", "content": question},
                                 {"role": "assistant", "content": error_msg}]
        return new_history, "", "", new_history

    # Build content-type filter
    content_types = []
    if show_text:
        content_types.append("text")
    if show_table:
        content_types.append("table")
    if show_formula:
        content_types.append("formula")
    if show_figure:
        content_types.append("figure")

    # Execute query
    result = engine.query(
        question=question,
        book_filter=selected_books or None,
        content_type_filter=content_types or None,
    )

    # Format sources as markdown
    sources_lines = []
    for src in result.sources:
        badge = format_badge(src.chunk.content_type)
        sources_lines.append(
            f"**[{src.citation_id}]** {badge}\n"
            f"📖 **{src.chunk.book_title}**\n"
            f"*{src.chunk.chapter}* · p.{src.chunk.page_number}\n"
            f"Relevance: {src.relevance_score:.3f}\n"
            f"---"
        )
    sources_md = "\n\n".join(sources_lines) if sources_lines else "*No sources found*"

    # Format retrieval stats
    stats_lines = [f"- **{m}**: {s}" for m, s in result.retrieval_stats.items()]
    stats_md = "\n".join(stats_lines) if stats_lines else "*No stats*"

    # Update chat history
    new_history = history + [{"role": "user", "content": question},
                             {"role": "assistant", "content": result.answer}]

    return new_history, sources_md, stats_md, new_history


# ─── Custom CSS ───────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    font-family: 'Inter', sans-serif !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* Refined dark theme overrides */
.dark .source-panel {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
}

/* Chatbot bubble styling */
.chatbot .message {
    border-radius: 12px !important;
}

/* Smooth transitions */
.gradio-button {
    transition: all 0.2s ease !important;
    border-radius: 8px !important;
}

.gradio-button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
}

/* Header gradient */
.app-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2em;
    font-weight: 700;
    text-align: center;
    padding: 16px 0;
}

/* Stats and source panels */
.panel-card {
    background: linear-gradient(145deg, #f8f9ff, #ffffff);
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
}
"""


# ─── Build Gradio UI ──────────────────────────────────────────────
def build_app() -> gr.Blocks:
    """Construct the Gradio Blocks application."""

    book_labels = get_book_labels()
    book_keys = list(book_labels.keys())

    with gr.Blocks(
        title="AI Textbook Q&A — Gradio",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
    ) as app:
        # Header
        gr.HTML(
            '<div class="app-header">📚 AI Textbook Q&A</div>'
            '<p style="text-align:center; color:#6b7280; margin-bottom:24px;">'
            "Ask questions about AI, ML, NLP — grounded in 30+ canonical textbooks"
            "</p>"
        )

        # State for conversation history
        chat_state = gr.State([])

        with gr.Row():
            # ── Left sidebar: filters ──
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### ⚙️ Filters")

                book_filter = gr.CheckboxGroup(
                    choices=book_keys,
                    label="📖 Filter by Books",
                    info="Leave empty to search all books",
                )

                gr.Markdown("**Content Types**")
                with gr.Row():
                    show_text = gr.Checkbox(label="Text", value=True)
                    show_table = gr.Checkbox(label="Tables", value=True)
                with gr.Row():
                    show_formula = gr.Checkbox(label="Formulas", value=True)
                    show_figure = gr.Checkbox(label="Figures", value=True)

                gr.Markdown("---")
                gr.Markdown("### 🏥 System Status")
                health_display = gr.Textbox(
                    value=get_health(),
                    label="Component Health",
                    interactive=False,
                    lines=4,
                )
                refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                refresh_btn.click(fn=get_health, outputs=health_display)

            # ── Main content ──
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=450,
                    type="messages",
                    show_copy_button=True,
                    avatar_images=(None, "📚"),
                    placeholder=(
                        "📭 Ask your first question!\n\n"
                        'Try: "What is the Adam optimizer?" or '
                        '"Explain backpropagation"'
                    ),
                )

                with gr.Row():
                    question_input = gr.Textbox(
                        placeholder="Ask a question about AI/ML textbooks...",
                        show_label=False,
                        scale=5,
                        container=False,
                    )
                    submit_btn = gr.Button(
                        "🔍 Ask", variant="primary", scale=1
                    )

                with gr.Row():
                    with gr.Accordion("📖 Sources", open=True):
                        sources_display = gr.Markdown("*Ask a question to see sources*")
                    with gr.Accordion("📊 Retrieval Stats", open=False):
                        stats_display = gr.Markdown("*No stats yet*")

        # ── Event wiring ──
        submit_inputs = [
            question_input,
            book_filter,
            show_text,
            show_table,
            show_formula,
            show_figure,
            chat_state,
        ]
        submit_outputs = [chatbot, sources_display, stats_display, chat_state]

        submit_btn.click(
            fn=handle_query,
            inputs=submit_inputs,
            outputs=submit_outputs,
        ).then(fn=lambda: "", outputs=question_input)

        question_input.submit(
            fn=handle_query,
            inputs=submit_inputs,
            outputs=submit_outputs,
        ).then(fn=lambda: "", outputs=question_input)

    return app


# ─── Entry Point ──────────────────────────────────────────────────
if __name__ == "__main__":
    demo = build_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
