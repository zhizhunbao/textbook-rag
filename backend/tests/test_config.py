# Unit tests for configuration loading.
# Refs:
# - Okken, Python Testing with pytest, Ch2-Ch4: keep tests behavior-focused and
#   use simple inputs instead of heavy fixture scaffolding when isolation is easy.
# - Software Engineering at Google, Testing chapters: verify externally visible
#   behavior and keep unit tests clear about the contract being checked.

from __future__ import annotations

from pathlib import Path

from backend.app.config import Config


class TestConfig:
    """Tests for Config.load()."""

    def test_load_uses_defaults_when_config_missing(self, tmp_path: Path) -> None:
        """Missing config file falls back to defaults and resolved paths."""
        config = Config.load(tmp_path / "config.yaml")

        assert config.ollama.host == "http://localhost:11434"
        assert config.embedding.model == "Qwen/Qwen3-Embedding-0.6B"
        assert config.retrieval.top_k == 5
        assert config.chunking.max_tokens == 512
        assert config.project_root == tmp_path.resolve()
        assert config.paths.sqlite_db == tmp_path / "data/textbook_qa.db"
        assert config.paths.chroma_db == tmp_path / "data/chroma_db"

    def test_load_applies_yaml_overrides(self, tmp_path: Path) -> None:
        """YAML values override defaults and relative paths resolve from backend root."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "ollama:",
                    "  host: http://example:11434",
                    "  model: qwen-test",
                    "  timeout: 45",
                    "embedding:",
                    "  model: demo-embed",
                    "  dimension: 768",
                    "retrieval:",
                    "  top_k: 7",
                    "  rrf_k: 77",
                    "  parallel_timeout: 12",
                    "  methods:",
                    "    bm25: true",
                    "    semantic: false",
                    "chunking:",
                    "  max_tokens: 256",
                    "  overlap_tokens: 16",
                    "paths:",
                    "  mineru_output: ../mineru",
                    "  textbooks_dir: ../books",
                    "  sqlite_db: custom/data.db",
                    "  chroma_db: custom/chroma",
                    "  pageindex_trees: custom/trees",
                ]
            ),
            encoding="utf-8",
        )

        config = Config.load(config_path)

        assert config.ollama.host == "http://example:11434"
        assert config.ollama.model == "qwen-test"
        assert config.ollama.timeout == 45
        assert config.embedding.model == "demo-embed"
        assert config.embedding.dimension == 768
        assert config.retrieval.top_k == 7
        assert config.retrieval.rrf_k == 77
        assert config.retrieval.parallel_timeout == 12
        assert config.retrieval.methods == {"bm25": True, "semantic": False}
        assert config.chunking.max_tokens == 256
        assert config.chunking.overlap_tokens == 16
        assert config.paths.mineru_output == (tmp_path / "../mineru").resolve()
        assert config.paths.textbooks_dir == (tmp_path / "../books").resolve()
        assert config.paths.sqlite_db == tmp_path / "custom/data.db"
        assert config.paths.chroma_db == tmp_path / "custom/chroma"
        assert config.paths.pageindex_trees == tmp_path / "custom/trees"
