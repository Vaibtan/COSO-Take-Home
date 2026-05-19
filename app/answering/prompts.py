from __future__ import annotations

from app.schemas import EvidenceChunk


def render_evidence(evidence: list[EvidenceChunk], *, max_chars: int = 1800) -> str:
    parts: list[str] = []
    for index, chunk in enumerate(evidence, start=1):
        text = chunk.text[:max_chars].replace("\n", " ").strip()
        parts.append(
            f"[{index}] chunk_id={chunk.id} source={chunk.filename} p.{chunk.page_number}\n{text}"
        )
    return "\n\n".join(parts)


def answer_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    return f"""
You are answering questions over construction documents.

Rules:
- Answer only from the evidence below.
- Every factual sentence must end with citations like [filename p.N].
- If evidence does not support an answer, say:
  "I don't have enough cited evidence to answer that."
- Do not cite sources that are not listed.

Question:
{question}

Evidence:
{render_evidence(evidence)}

Answer:
""".strip()


def evidence_selector_prompt(question: str, evidence: list[EvidenceChunk], *, limit: int) -> str:
    return f"""
Select up to {limit} chunks that directly support answering the question.
Return JSON only with this shape:
{{"selected_chunk_ids": [123, 456], "reason": "short reason"}}

Question:
{question}

Candidate chunks:
{render_evidence(evidence, max_chars=1200)}
""".strip()


def verification_prompt(answer: str, evidence: list[EvidenceChunk]) -> str:
    return f"""
Check whether every factual sentence in the answer is supported by its cited source.
Return JSON only:
{{
  "supported": true,
  "issues": [],
  "repaired_answer": null
}}

If a sentence is unsupported but can be repaired using the evidence, set
"supported" to false and provide "repaired_answer".

Answer:
{answer}

Evidence:
{render_evidence(evidence, max_chars=1500)}
""".strip()
