from __future__ import annotations

from app.ingestion.chunker import PageAwareChunker
from app.ingestion.extractor import ExtractedPage


def test_chunker_preserves_page_boundaries() -> None:
    pages = [
        ExtractedPage("doc.pdf", 1, "alpha " * 1200, "test"),
        ExtractedPage("doc.pdf", 2, "beta " * 1200, "test"),
    ]

    chunks = PageAwareChunker(target_tokens=200, overlap_tokens=20).chunk_pages(pages)

    assert chunks
    assert {chunk.page_number for chunk in chunks} == {1, 2}
    assert all(chunk.stable_id.startswith(f"doc.pdf:p{chunk.page_number}:") for chunk in chunks)
    assert not any("alpha" in chunk.text and "beta" in chunk.text for chunk in chunks)
