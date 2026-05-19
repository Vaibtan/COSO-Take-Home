from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.schemas import EvidenceChunk

IN09_FILES = {
    "coso-corpus-05-mpmrcl-in09-corr9.pdf",
    "coso-corpus-06-mpmrcl-in09-corr2.pdf",
    "coso-corpus-07-mpmrcl-in09-corr4.pdf",
}

CORR_RE = re.compile(r"corr(?:igendum)?\s*[- ]?\s*(\d+)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})")
ADDENDUM_LABEL_RE = re.compile(
    r"last\s+date\s+(?:of|for)\s+issuing\s+addend(?:um|a)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConflictAnswer:
    answer: str
    evidence: list[EvidenceChunk]


def is_in09_addendum_question(question: str) -> bool:
    normalized = question.lower()
    return "in-09" in normalized and "addend" in normalized and "date" in normalized


class In09ConflictResolver:
    async def extract_facts(self, connection: AsyncConnection) -> int:
        await connection.execute(text("DELETE FROM conflict_facts WHERE tender_id = 'IN-09'"))
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT c.id, c.document_id, c.filename, c.page_number, c.text
                    FROM chunks c
                    WHERE c.filename = ANY(CAST(:filenames AS text[]))
                    """
                ),
                {"filenames": list(IN09_FILES)},
            )
        ).mappings().all()
        inserted = 0
        for row in rows:
            value = self._addendum_date(str(row["text"]))
            if value is None:
                continue
            corr_number = self._corrigendum_number(str(row["filename"]), str(row["text"]))
            corr_date = self._first_date(str(row["text"]))
            await connection.execute(
                text(
                    """
                    INSERT INTO conflict_facts(
                        tender_id, field_name, field_value, normalized_value,
                        corrigendum_number, corrigendum_date, document_id, chunk_id,
                        confidence, metadata
                    )
                    VALUES (
                        'IN-09', 'last_date_for_issuing_addendum', :field_value,
                        :normalized_value, :corrigendum_number, :corrigendum_date,
                        :document_id, :chunk_id, 0.8, '{}'::jsonb
                    )
                    """
                ),
                {
                    "field_value": value,
                    "normalized_value": value,
                    "corrigendum_number": corr_number,
                    "corrigendum_date": corr_date,
                    "document_id": row["document_id"],
                    "chunk_id": row["id"],
                },
            )
            inserted += 1
        return inserted

    async def resolve(self, connection: AsyncConnection) -> ConflictAnswer | None:
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT f.field_value, f.corrigendum_number, f.corrigendum_date,
                           c.id, c.stable_id, c.filename, c.page_number, c.text, c.metadata
                    FROM conflict_facts f
                    JOIN chunks c ON c.id = f.chunk_id
                    WHERE f.tender_id = 'IN-09'
                      AND f.field_name = 'last_date_for_issuing_addendum'
                    ORDER BY f.corrigendum_number DESC NULLS LAST,
                             f.corrigendum_date DESC NULLS LAST,
                             f.id DESC
                    """
                )
            )
        ).mappings().all()
        if not rows:
            return None
        evidence = [
            EvidenceChunk(
                id=int(row["id"]),
                stable_id=str(row["stable_id"]),
                filename=str(row["filename"]),
                page_number=int(row["page_number"]),
                text=str(row["text"]),
                source="conflict",
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]
        winner = rows[0]
        answer = (
            "The latest cited IN-09 corrigendum evidence I found gives the last date "
            f"for issuing addenda as {winner['field_value']}. "
            f"[{winner['filename']} p.{winner['page_number']}]"
        )
        if len(rows) > 1:
            superseded = "; ".join(
                f"{row['field_value']} [{row['filename']} p.{row['page_number']}]"
                for row in rows[1:4]
            )
            answer += f" Earlier conflicting values found were: {superseded}."
        return ConflictAnswer(answer=answer, evidence=evidence)

    @staticmethod
    def _corrigendum_number(filename: str, text_value: str) -> int | None:
        filename_match = CORR_RE.search(filename)
        if filename_match:
            return int(filename_match.group(1))
        text_match = CORR_RE.search(text_value[:1000])
        return int(text_match.group(1)) if text_match else None

    @staticmethod
    def _first_date(text_value: str) -> date | None:
        match = DATE_RE.search(text_value[:2000])
        if not match:
            return None
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _addendum_date(text_value: str) -> str | None:
        label_match = ADDENDUM_LABEL_RE.search(text_value)
        if not label_match:
            return None
        window = text_value[label_match.start() : label_match.start() + 700]
        dates = [match.group(0) for match in DATE_RE.finditer(window)]
        return dates[-1] if dates else None
