# NiceGUI UI — AI Textbook Q&A System
# Run: python frontend/src/app_nicegui.py
# Ref: NiceGUI provides a Pythonic API for building modern web UIs with Vue.js + Quasar
# Ref: Ramalho, Fluent Python, asyncio/concurrency chapters - blocking work must
# not run on the event loop when a thread executor can isolate it.

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from nicegui import ui  # noqa: E402

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


# ─── Helper ───────────────────────────────────────────────────────
BADGE_COLORS: dict[str, str] = {
    "text": "indigo",
    "table": "purple",
    "formula": "pink",
    "figure": "teal",
}

BADGE_ICONS: dict[str, str] = {
    "text": "article",
    "table": "table_chart",
    "formula": "functions",
    "figure": "image",
}


# ─── Custom CSS ───────────────────────────────────────────────────
CUSTOM_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body {
    font-family: 'Inter', sans-serif !important;
}

.source-card {
    transition: all 0.25s ease;
    cursor: pointer;
}

.source-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.15) !important;
    border-color: #6366f1 !important;
}

.chat-bubble-user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 12px 18px !important;
    max-width: 80% !important;
    margin-left: auto !important;
}

.chat-bubble-bot {
    background: #f3f4f6 !important;
    color: #1f2937 !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 12px 18px !important;
    max-width: 80% !important;
}

.stats-chip {
    transition: all 0.2s ease;
}
.stats-chip:hover {
    transform: scale(1.05);
}

.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #9ca3af;
}
"""


# ─── Main Page ────────────────────────────────────────────────────
@ui.page("/")
def index():
    """Build the main application page."""
    # Inject custom CSS
    ui.add_head_html(f"<style>{CUSTOM_STYLE}</style>")

    # App-level state
    selected_books: list[str] = []
    content_filters: dict[str, bool] = {
        "text": True,
        "table": True,
        "formula": True,
        "figure": True,
    }

    # Engine + books
    engine = get_engine()
    books = engine.get_available_books() if engine else []
    book_options = {b.book_key: f"{b.book_title} ({b.total_chunks})" for b in books}

    # ── Header ──
    with ui.header().classes("bg-gradient-to-r from-indigo-600 to-purple-600 shadow-lg"):
        with ui.row().classes("w-full items-center justify-between px-6"):
            ui.label("📚 AI Textbook Q&A").classes(
                "text-white text-2xl font-bold tracking-tight"
            )
            ui.label("Powered by RAG · 30+ Textbooks").classes(
                "text-white/70 text-sm"
            )

    # ── Layout ──
    with ui.row().classes("w-full gap-0").style("min-height: calc(100vh - 64px)"):
        # ── Left Sidebar ──
        with ui.column().classes(
            "w-72 bg-gray-50 p-4 border-r border-gray-200 shrink-0"
        ):
            ui.label("Filters").classes("text-lg font-semibold text-gray-700 mb-2")

            # Book filter
            if book_options:
                book_select = ui.select(
                    options=book_options,
                    multiple=True,
                    label="📖 Filter by Books",
                    with_input=True,
                ).classes("w-full").props("clearable")

                def on_book_change(e):
                    nonlocal selected_books
                    selected_books = e.value if e.value else []

                book_select.on("update:model-value", on_book_change)

            # Content type filters
            ui.label("Content Types").classes("font-semibold text-gray-600 mt-4 mb-1")
            for ctype in BADGE_ICONS:
                cb = ui.checkbox(
                    ctype.capitalize(), value=True
                ).classes("w-full")

                def make_handler(ct):
                    def handler(e):
                        content_filters[ct] = e.value
                    return handler

                cb.on("update:model-value", make_handler(ctype))

            # System health
            ui.separator().classes("my-4")
            ui.label("System Status").classes("font-semibold text-gray-600 mb-2")

            if engine:
                health = engine.check_health()
                for comp, ok in health.items():
                    color = "positive" if ok else "negative"
                    icon = "check_circle" if ok else "cancel"
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(icon, color=color).classes("text-sm")
                        ui.label(comp).classes("text-sm text-gray-600")
            else:
                ui.label("❌ Engine not loaded").classes("text-red-500 text-sm")

        # ── Main Content Area ──
        with ui.column().classes("flex-grow p-6 max-w-4xl mx-auto"):
            # Chat area
            chat_container = ui.column().classes(
                "w-full flex-grow gap-3 overflow-y-auto"
            ).style("max-height: 55vh; min-height: 300px;")

            # Empty state (shown initially)
            with chat_container:
                empty_placeholder = ui.column().classes("empty-state w-full")
                with empty_placeholder:
                    ui.label("📭").classes("text-6xl mb-4")
                    ui.label("Ask your first question").classes(
                        "text-xl font-semibold text-gray-400"
                    )
                    ui.label(
                        'Try: "What is the Adam optimizer?" or "Explain backpropagation"'
                    ).classes("text-sm text-gray-400 mt-2")

            # Sources / Stats section
            results_section = ui.column().classes("w-full").style("display: none;")
            with results_section:
                ui.separator().classes("my-3")

                # Sources accordion
                with ui.expansion("📖 Sources", icon="menu_book").classes(
                    "w-full bg-white rounded-lg shadow-sm"
                ).props("default-opened"):
                    sources_container = ui.column().classes("w-full gap-2")

                # Stats accordion
                with ui.expansion("📊 Retrieval Statistics", icon="analytics").classes(
                    "w-full bg-white rounded-lg shadow-sm mt-2"
                ):
                    stats_container = ui.column().classes("w-full")

            # ── Input bar ──
            with ui.row().classes(
                "w-full items-center gap-3 mt-4 p-3 bg-white rounded-xl shadow-md border border-gray-100"
            ):
                question_input = ui.input(
                    placeholder="Ask a question about AI/ML textbooks..."
                ).classes("flex-grow").props(
                    'outlined dense rounded'
                )

                send_btn = ui.button(
                    "Ask", icon="send", color="indigo"
                ).props("rounded unelevated").classes(
                    "px-6"
                )

            # ── Query handler ──
            async def do_query():
                question = question_input.value
                if not question or not question.strip():
                    return

                question_input.value = ""

                if engine is None:
                    ui.notify("RAG Engine not available!", type="negative")
                    return

                # Hide empty state
                empty_placeholder.set_visibility(False)
                results_section.style("display: block;")

                # Add user message
                with chat_container:
                    with ui.row().classes("w-full justify-end"):
                        ui.label(question).classes("chat-bubble-user")

                # Spinner while processing
                with chat_container:
                    spinner_row = ui.row().classes("w-full justify-start")
                    with spinner_row:
                        ui.spinner("dots", size="lg", color="indigo")

                # Build filters
                ct_filter = [k for k, v in content_filters.items() if v]

                # Execute RAG pipeline
                result = await asyncio.to_thread(
                    engine.query,
                    question=question,
                    book_filter=selected_books or None,
                    content_type_filter=ct_filter or None,
                )

                # Remove spinner
                chat_container.remove(spinner_row)

                # Add bot response
                with chat_container:
                    with ui.row().classes("w-full justify-start"):
                        ui.markdown(result.answer).classes("chat-bubble-bot")

                # Populate sources
                sources_container.clear()
                with sources_container:
                    if result.sources:
                        for src in result.sources:
                            color = BADGE_COLORS.get(src.chunk.content_type, "grey")
                            with ui.card().classes("source-card w-full").props("flat bordered"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(
                                        f"[{src.citation_id}]",
                                        color="indigo",
                                    ).props("rounded")
                                    ui.badge(
                                        src.chunk.content_type,
                                        color=color,
                                    ).props("rounded outline")
                                    ui.label(src.chunk.book_title).classes(
                                        "font-semibold text-gray-800"
                                    )
                                ui.label(
                                    f"{src.chunk.chapter} · p.{src.chunk.page_number}"
                                ).classes("text-sm text-gray-500 ml-1")
                    else:
                        ui.label("No sources found").classes("text-gray-400 italic")

                # Populate stats
                stats_container.clear()
                with stats_container:
                    if result.retrieval_stats:
                        with ui.row().classes("gap-2 flex-wrap"):
                            for method, stat in result.retrieval_stats.items():
                                ui.chip(
                                    f"{method}: {stat}",
                                    icon="bar_chart",
                                    color="indigo-2",
                                ).classes("stats-chip").props("outline")

                # Scroll to bottom
                ui.run_javascript(
                    "document.querySelector('.overflow-y-auto')?.scrollTo("
                    "{top: 999999, behavior: 'smooth'})"
                )

            send_btn.on("click", do_query)
            question_input.on("keydown.enter", do_query)

    # ── Footer ──
    with ui.footer().classes("bg-gray-50 border-t border-gray-200"):
        ui.label(
            "Built with NiceGUI · RAG-based Educational Q&A System"
        ).classes("text-xs text-gray-400 mx-auto")


# ─── Entry Point ──────────────────────────────────────────────────
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="AI Textbook Q&A — NiceGUI",
        port=8080,
        reload=False,
        show=True,
    )
