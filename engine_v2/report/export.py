"""export — Markdown to PDF export for reports.

Responsibilities:
    - Convert Markdown content to styled HTML
    - Render HTML to PDF using xhtml2pdf
    - Return PDF bytes for download

Ref: xhtml2pdf — HTML/CSS to PDF renderer (pure Python)
"""

from __future__ import annotations

from io import BytesIO

from loguru import logger


# ============================================================
# CSS template for professional PDF styling
# ============================================================
_PDF_CSS = """
@page {
    size: letter;
    margin: 2.5cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        bottom: 1cm;
        margin-left: 2.5cm;
        margin-right: 2.5cm;
        height: 1cm;
    }
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}

h1 {
    font-size: 22pt;
    color: #004890;
    border-bottom: 3px solid #004890;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
}

h2 {
    font-size: 16pt;
    color: #004890;
    margin-top: 24px;
    margin-bottom: 12px;
    border-bottom: 1px solid #E8E4DE;
    padding-bottom: 4px;
}

h3 {
    font-size: 13pt;
    color: #333;
    margin-top: 16px;
    margin-bottom: 8px;
}

p {
    margin-bottom: 8px;
    text-align: justify;
}

ul, ol {
    margin-bottom: 12px;
    padding-left: 24px;
}

li {
    margin-bottom: 4px;
}

strong {
    color: #004890;
}

code {
    font-family: "Courier New", monospace;
    font-size: 9pt;
    background-color: #f5f5f5;
    padding: 2px 4px;
}

blockquote {
    border-left: 3px solid #004890;
    padding-left: 12px;
    margin-left: 0;
    color: #555;
    font-style: italic;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
}

th {
    background-color: #004890;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-size: 10pt;
}

td {
    padding: 6px 12px;
    border-bottom: 1px solid #E8E4DE;
    font-size: 10pt;
}

tr:nth-child(even) td {
    background-color: #FAF9F6;
}

.cover-header {
    text-align: center;
    margin-top: 60px;
    margin-bottom: 40px;
}

.cover-header h1 {
    font-size: 28pt;
    border: none;
    margin-bottom: 8px;
}

.cover-meta {
    text-align: center;
    color: #666;
    font-size: 10pt;
    margin-bottom: 40px;
}

.footer-text {
    font-size: 8pt;
    color: #999;
    text-align: center;
}
"""


# ============================================================
# Export function
# ============================================================
def markdown_to_pdf(markdown_content: str, title: str = "Report") -> bytes:
    """Convert Markdown content to PDF bytes.

    Uses `markdown` library for MD→HTML, then `xhtml2pdf` for HTML→PDF.
    Returns raw PDF bytes suitable for streaming response.
    """
    import markdown
    from xhtml2pdf import pisa

    # Convert Markdown to HTML
    html_body = markdown.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    # Build full HTML document with CSS styling
    from datetime import datetime
    generated_date = datetime.now().strftime("%B %d, %Y at %H:%M")

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{_PDF_CSS}</style>
</head>
<body>
    <div class="cover-meta">
        Generated on {generated_date} &bull; EcDev Research v2.0
    </div>

    {html_body}

    <div id="footerContent">
        <p class="footer-text">
            EcDev Research &mdash; AI-Powered Research Assistant &bull; City of Ottawa Economic Development
        </p>
    </div>
</body>
</html>"""

    # Render HTML to PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_doc, dest=pdf_buffer, encoding="utf-8")

    if pisa_status.err:
        logger.error("PDF generation failed with {} error(s)", pisa_status.err)
        raise RuntimeError(f"PDF generation failed: {pisa_status.err} error(s)")

    pdf_bytes = pdf_buffer.getvalue()
    logger.info("Generated PDF: {} bytes for '{}'", len(pdf_bytes), title)
    return pdf_bytes
