from typing import List, Tuple
from PyPDF2 import PdfReader
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> List[Tuple[int, str]]:
    """
    Returns a list of (page_number, text) tuples (1-indexed pages).
    """
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        cleaned = " ".join(text.split())
        if cleaned:
            pages.append((i, cleaned))
    return pages
