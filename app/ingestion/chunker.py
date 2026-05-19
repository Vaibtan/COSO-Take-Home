from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingestion.extractor import ExtractedPage
from app.utils import estimate_tokens


@dataclass(frozen=True)
class ChunkCandidate:
    stable_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    token_estimate: int
    metadata: dict[str, object] = field(default_factory=dict)


class PageAwareChunker:
    def __init__(self, target_tokens: int = 800, overlap_tokens: int = 100) -> None:
        self._target_tokens = target_tokens
        self._overlap_tokens = overlap_tokens

    def chunk_pages(self, pages: list[ExtractedPage]) -> list[ChunkCandidate]:
        chunks: list[ChunkCandidate] = []
        for page in pages:
            chunks.extend(self._chunk_page(page))
        return chunks

    def _chunk_page(self, page: ExtractedPage) -> list[ChunkCandidate]:
        text = re.sub(r"\n{3,}", "\n\n", page.text).strip()
        if not text:
            return []
        if estimate_tokens(text) <= self._target_tokens:
            return [self._candidate(page, 0, text)]

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        chunks: list[ChunkCandidate] = []
        current: list[str] = []
        current_tokens = 0
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph_tokens = estimate_tokens(paragraph)
            if current and current_tokens + paragraph_tokens > self._target_tokens:
                chunk_text = "\n\n".join(current)
                chunks.append(self._candidate(page, chunk_index, chunk_text))
                chunk_index += 1
                current = self._tail_overlap(current)
                current_tokens = estimate_tokens("\n\n".join(current)) if current else 0
            if paragraph_tokens > self._target_tokens:
                for segment in self._split_long_text(paragraph):
                    if current:
                        chunks.append(self._candidate(page, chunk_index, "\n\n".join(current)))
                        chunk_index += 1
                        current = []
                        current_tokens = 0
                    chunks.append(self._candidate(page, chunk_index, segment))
                    chunk_index += 1
                continue
            current.append(paragraph)
            current_tokens += paragraph_tokens

        if current:
            chunks.append(self._candidate(page, chunk_index, "\n\n".join(current)))
        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        words = text.split()
        words_per_chunk = max(100, self._target_tokens * 3 // 4)
        overlap_words = max(10, self._overlap_tokens * 3 // 4)
        result: list[str] = []
        start = 0
        while start < len(words):
            end = min(len(words), start + words_per_chunk)
            result.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start = max(0, end - overlap_words)
        return result

    def _tail_overlap(self, paragraphs: list[str]) -> list[str]:
        kept: list[str] = []
        for paragraph in reversed(paragraphs):
            if estimate_tokens("\n\n".join([paragraph, *kept])) > self._overlap_tokens:
                break
            kept.insert(0, paragraph)
        return kept

    @staticmethod
    def _candidate(page: ExtractedPage, chunk_index: int, text: str) -> ChunkCandidate:
        stable_id = f"{page.filename}:p{page.page_number}:c{chunk_index}"
        return ChunkCandidate(
            stable_id=stable_id,
            filename=page.filename,
            page_number=page.page_number,
            chunk_index=chunk_index,
            text=text,
            token_estimate=estimate_tokens(text),
            metadata=dict(page.metadata),
        )
