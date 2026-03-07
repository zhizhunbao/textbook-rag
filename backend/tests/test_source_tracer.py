# Unit tests for source tracing.
# Refs:
# - Okken, Python Testing with pytest, Ch3 and mocking sections: isolate PDF and
#   imaging dependencies so rendering edge cases can be tested deterministically.
# - Jurafsky and Martin, Speech and Language Processing, QA/citation sections:
#   source presentation matters because answers must be traceable back to the
#   underlying document evidence.

from __future__ import annotations

from pathlib import Path

from backend.app.tracing import source_tracer as tracer_module
from backend.app.tracing.source_tracer import SourceTracer


class _FakeImageObject:
    def __init__(self) -> None:
        self.rectangles = []


class _FakeImageModule:
    @staticmethod
    def frombytes(mode: str, size: tuple[int, int], samples: bytes) -> _FakeImageObject:
        assert mode == "RGB"
        assert size == (10, 20)
        assert samples == b"pixels"
        return _FakeImageObject()


class _FakeImageDrawModule:
    @staticmethod
    def Draw(img: _FakeImageObject, mode: str):
        class Drawer:
            def rectangle(self, bbox, fill=None, outline=None, width=None) -> None:
                img.rectangles.append((bbox, fill, outline, width))

        assert mode == "RGBA"
        return Drawer()


class _FakePixmap:
    width = 10
    height = 20
    samples = b"pixels"


class _FakePage:
    def get_pixmap(self, matrix, alpha: bool) -> _FakePixmap:
        assert alpha is False
        return _FakePixmap()


class _FakeDoc:
    def __init__(self, pages: int) -> None:
        self.pages = pages
        self.closed = False

    def __len__(self) -> int:
        return self.pages

    def __getitem__(self, page_number: int) -> _FakePage:
        assert page_number == 0
        return _FakePage()

    def close(self) -> None:
        self.closed = True


class _FakeFitzModule:
    @staticmethod
    def Matrix(x: float, y: float) -> tuple[float, float]:
        return (x, y)

    @staticmethod
    def open(path: str) -> _FakeDoc:
        assert path.endswith(".pdf")
        return _FakeDoc(1)


class TestSourceTracer:
    """Tests for SourceTracer."""

    def test_render_returns_none_without_pdf_dependencies(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """Missing optional rendering libraries disables source rendering."""
        monkeypatch.setattr(tracer_module, "fitz", None)
        monkeypatch.setattr(tracer_module, "Image", None)

        tracer = SourceTracer(tmp_path, tmp_path)
        assert tracer.render_page_with_highlight("book", 0, [0, 0, 1, 1]) is None

    def test_render_returns_none_when_pdf_missing(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """No matching PDF returns None before rendering."""
        monkeypatch.setattr(tracer_module, "fitz", _FakeFitzModule)
        monkeypatch.setattr(tracer_module, "Image", _FakeImageModule)
        monkeypatch.setattr(tracer_module, "ImageDraw", _FakeImageDrawModule)
        monkeypatch.setattr(SourceTracer, "_find_pdf", lambda self, book_key: None)

        tracer = SourceTracer(tmp_path, tmp_path)
        assert tracer.render_page_with_highlight("book", 0, [0, 0, 1, 1]) is None

    def test_render_returns_none_for_page_out_of_range(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """Requesting a missing page is handled gracefully."""

        class RangeFitz(_FakeFitzModule):
            @staticmethod
            def open(path: str) -> _FakeDoc:
                return _FakeDoc(1)

        monkeypatch.setattr(tracer_module, "fitz", RangeFitz)
        monkeypatch.setattr(tracer_module, "Image", _FakeImageModule)
        monkeypatch.setattr(tracer_module, "ImageDraw", _FakeImageDrawModule)
        monkeypatch.setattr(
            SourceTracer, "_find_pdf", lambda self, book_key: tmp_path / "book.pdf"
        )

        tracer = SourceTracer(tmp_path, tmp_path)
        assert tracer.render_page_with_highlight("book", 5, [0, 0, 1, 1]) is None

    def test_render_draws_highlight_for_valid_bbox(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """Valid bbox values result in both fill and outline draw calls."""
        monkeypatch.setattr(tracer_module, "fitz", _FakeFitzModule)
        monkeypatch.setattr(tracer_module, "Image", _FakeImageModule)
        monkeypatch.setattr(tracer_module, "ImageDraw", _FakeImageDrawModule)
        monkeypatch.setattr(
            SourceTracer, "_find_pdf", lambda self, book_key: tmp_path / "book.pdf"
        )

        tracer = SourceTracer(tmp_path, tmp_path)
        image = tracer.render_page_with_highlight("book", 0, [1, 2, 3, 4], zoom=2.0)

        assert image is not None
        assert len(image.rectangles) == 2
        assert image.rectangles[0][0] == [2.0, 4.0, 6.0, 8.0]

    def test_find_pdf_prefers_layout_then_textbook_fallback(
        self, tmp_path: Path
    ) -> None:
        """PDF lookup prefers MinerU layout PDFs and then scans textbook files."""
        mineru_layout = tmp_path / "mineru" / "book" / "book" / "auto"
        mineru_layout.mkdir(parents=True)
        layout_pdf = mineru_layout / "book_layout.pdf"
        layout_pdf.write_bytes(b"pdf")

        textbooks = tmp_path / "books"
        textbooks.mkdir()
        fallback_pdf = textbooks / "book-copy.pdf"
        fallback_pdf.write_bytes(b"pdf")

        tracer = SourceTracer(
            textbooks_dir=textbooks, mineru_output_dir=tmp_path / "mineru"
        )
        assert tracer._find_pdf("book") == layout_pdf

        layout_pdf.unlink()
        assert tracer._find_pdf("book") == fallback_pdf
