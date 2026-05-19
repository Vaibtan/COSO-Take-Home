from __future__ import annotations

from app.answering.citations import check_citation_existence
from app.answering.prompts import answer_prompt, evidence_selector_prompt, verification_prompt
from app.config import Settings
from app.llm import GeminiClient
from app.schemas import EvidenceChunk, QueryMode, QueryResult


class AnsweringService:
    def __init__(self, settings: Settings, llm: GeminiClient) -> None:
        self._settings = settings
        self._llm = llm

    async def select_evidence(
        self, question: str, candidates: list[EvidenceChunk], mode: QueryMode
    ) -> list[EvidenceChunk]:
        if mode is QueryMode.baseline:
            return candidates[: self._settings.baseline_top_k]
        if not candidates:
            return []
        payload = await self._llm.generate_json(
            evidence_selector_prompt(
                question,
                candidates,
                limit=self._settings.fixed_evidence_top_k,
            )
        )
        selected_ids = payload.get("selected_chunk_ids", [])
        if not isinstance(selected_ids, list):
            return candidates[: self._settings.fixed_evidence_top_k]
        by_id = {chunk.id: chunk for chunk in candidates}
        selected = [by_id[int(chunk_id)] for chunk_id in selected_ids if int(chunk_id) in by_id]
        return selected or candidates[: self._settings.fixed_evidence_top_k]

    async def answer(
        self, question: str, evidence: list[EvidenceChunk], mode: QueryMode
    ) -> QueryResult:
        if len(evidence) < self._settings.refusal_min_evidence:
            return QueryResult(
                answer=None,
                refusal_reason="I don't have enough cited evidence to answer that.",
                evidence=evidence,
            )
        answer = (await self._llm.generate_text(answer_prompt(question, evidence))).strip()
        if mode is QueryMode.baseline:
            return QueryResult(answer=answer, refusal_reason=None, evidence=evidence)

        citation_check = check_citation_existence(answer, evidence)
        if not citation_check.ok:
            return QueryResult(
                answer=None,
                refusal_reason="Citation verification failed: " + "; ".join(citation_check.issues),
                evidence=evidence,
            )

        verification = await self._llm.generate_json(verification_prompt(answer, evidence))
        if verification.get("supported") is True:
            return QueryResult(answer=answer, refusal_reason=None, evidence=evidence)

        repaired = verification.get("repaired_answer")
        if isinstance(repaired, str) and repaired.strip():
            repaired_check = check_citation_existence(repaired, evidence)
            if repaired_check.ok:
                return QueryResult(answer=repaired.strip(), refusal_reason=None, evidence=evidence)

        issues = verification.get("issues")
        reason = "Citation support verification failed."
        if isinstance(issues, list) and issues:
            reason += " " + "; ".join(str(issue) for issue in issues[:3])
        return QueryResult(answer=None, refusal_reason=reason, evidence=evidence)
