from typing import List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_pages(pages: List[Tuple[int, str]], chunk_size: int = 800, chunk_overlap: int = 100) -> List[dict]:
    """
    Split per-page texts into chunks while preserving page numbers.
    Returns list of {chunk_index, content, page_number}.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    chunk_index = 0
    for page_number, text in pages:
        for piece in splitter.split_text(text):
            chunks.append({
                "chunk_index": chunk_index,
                "content": piece,
                "page_number": page_number,
            })
            chunk_index += 1
    return chunks
