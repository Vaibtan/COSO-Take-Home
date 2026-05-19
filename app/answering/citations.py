from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import EvidenceChunk

CITATION_RE = re.compile(r"\[([^\[\]]+?)\s+p\.(\d+)\]")


@dataclass(frozen=True)
class CitationCheck:
    ok: bool
    issues: list[str]


def extract_citations(text: str) -> list[tuple[str, int]]:
    return [(match.group(1).strip(), int(match.group(2))) for match in CITATION_RE.finditer(text)]


def check_citation_existence(answer: str, evidence: list[EvidenceChunk]) -> CitationCheck:
    available = {(item.filename, item.page_number) for item in evidence}
    citations = extract_citations(answer)
    issues: list[str] = []
    if not citations:
        issues.append("answer has no citations")
    for filename, page_number in citations:
        if (filename, page_number) not in available:
            issues.append(f"citation not in selected evidence: {filename} p.{page_number}")
    return CitationCheck(ok=not issues, issues=issues)
