from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from PyPDF2 import PdfReader

from app.core.config import get_settings
from app.schemas.complaint import ComplaintExtraction, PolicyAssessment


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "about",
    "your",
    "একটি",
    "এবং",
    "এই",
    "থেকে",
    "করে",
    "যদি",
}


@dataclass(slots=True)
class PolicyChunk:
    source: str
    text: str
    tokens: set[str]


class PolicyRAGService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._chunks: list[PolicyChunk] | None = None

    async def evaluate(self, complaint: ComplaintExtraction, original_text: str) -> PolicyAssessment:
        if self._chunks is None:
            self._chunks = self._load_chunks()
        query = f"{complaint.category} {complaint.thana} {complaint.summary} {original_text}"
        ranked = self._rank_chunks(query)
        top_chunks = ranked[:3]
        overlap_score = sum(score for score, _ in top_chunks) / max(len(top_chunks), 1)
        inconsistency = round(max(0.0, 1.0 - overlap_score), 3)
        if not top_chunks:
            status = "Insufficient policy context"
        elif inconsistency < 0.35:
            status = "Compliant"
        elif inconsistency < 0.65:
            status = "Needs review"
        else:
            status = "Potential inconsistency"
        delayed = self._is_delayed(complaint.urgency, complaint.duration)
        return PolicyAssessment(
            compliance_status=status,
            inconsistency_score=inconsistency,
            matched_policy_sections=[chunk.text[:180] for _, chunk in top_chunks],
            delayed=delayed,
        )

    def _load_chunks(self) -> list[PolicyChunk]:
        chunks: list[PolicyChunk] = []
        pdf_paths = sorted(Path(self.settings.policy_directory).glob("*.pdf"))
        for pdf_path in pdf_paths:
            try:
                reader = PdfReader(str(pdf_path))
            except Exception:
                continue
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            for piece in self._chunk_text(full_text):
                tokens = self._tokenize(piece)
                if tokens:
                    chunks.append(PolicyChunk(source=pdf_path.name, text=f"{pdf_path.name}: {piece}", tokens=tokens))
        return chunks

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 700) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        return [normalized[index:index + chunk_size] for index in range(0, len(normalized), chunk_size)]

    def _rank_chunks(self, query: str) -> list[tuple[float, PolicyChunk]]:
        query_tokens = self._tokenize(query)
        ranked: list[tuple[float, PolicyChunk]] = []
        for chunk in self._chunks or []:
            intersection = len(query_tokens & chunk.tokens)
            denominator = math.sqrt(len(query_tokens) * len(chunk.tokens)) or 1
            score = intersection / denominator
            if score > 0:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        tokens = {token for token in re.findall(r"[A-Za-z0-9\u0980-\u09FF]+", text.lower()) if token not in STOPWORDS}
        return {token for token in tokens if len(token) > 1}

    @staticmethod
    def _is_delayed(urgency: str, duration: str) -> bool:
        duration_lower = duration.lower()
        if urgency == "Critical":
            return any(word in duration_lower for word in ["day", "days", "দিন", "week", "weeks", "সপ্তাহ"])
        if urgency == "High":
            return any(word in duration_lower for word in ["week", "weeks", "সপ্তাহ", "month", "months", "মাস"])
        return "month" in duration_lower or "মাস" in duration_lower
