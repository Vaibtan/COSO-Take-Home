from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz


@dataclass(frozen=True)
class ExtractedPage:
    filename: str
    page_number: int
    text: str
    extraction_method: str
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def is_weak(self) -> bool:
        return len(self.text.strip()) < 200


class PdfExtractor:
    def extract(self, path: Path) -> list[ExtractedPage]:
        pages: list[ExtractedPage] = []
        with fitz.open(path) as document:
            for index, page in enumerate(document, start=1):
                text = page.get_text("text", sort=True).strip()
                pages.append(
                    ExtractedPage(
                        filename=path.name,
                        page_number=index,
                        text=text,
                        extraction_method="pymupdf",
                        metadata={
                            "width": float(page.rect.width),
                            "height": float(page.rect.height),
                            "weak_text": len(text) < 200,
                        },
                    )
                )
        return pages
