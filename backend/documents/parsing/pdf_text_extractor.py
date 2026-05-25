from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract text from a PDF in page order."""

    reader = PdfReader(str(file_path))
    page_texts = []
    for page in reader.pages:
        page_texts.append(page.extract_text() or "")

    return "\n".join(page_texts).strip()

