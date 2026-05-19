from __future__ import annotations

from app.answering.citations import check_citation_existence, extract_citations
from app.schemas import EvidenceChunk


def test_extract_citations() -> None:
    assert extract_citations("Answer. [file.pdf p.12]") == [("file.pdf", 12)]


def test_citation_existence_rejects_sources_outside_selected_evidence() -> None:
    evidence = [
        EvidenceChunk(
            id=1,
            stable_id="file.pdf:p1:c0",
            filename="file.pdf",
            page_number=1,
            text="supporting text",
        )
    ]

    result = check_citation_existence("Answer. [other.pdf p.2]", evidence)

    assert not result.ok
    assert result.issues == ["citation not in selected evidence: other.pdf p.2"]
