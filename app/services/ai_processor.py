from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.complaint import ComplaintExtraction


KNOWN_THANAS = [
    "Dhanmondi",
    "Gulshan",
    "Mirpur",
    "Mohammadpur",
    "Ramna",
    "Badda",
    "Tejgaon",
    "Uttara",
    "Kotwali",
    "Wari",
    "Jatrabari",
    "Pallabi",
    "Banani",
    "Khilgaon",
]

CATEGORY_KEYWORDS = {
    "Drainage": ["drain", "waterlogging", "ড্রেন", "পানি জমে", "জলাবদ্ধতা"],
    "Road Damage": ["road", "pothole", "রাস্তা", "গর্ত"],
    "Waste Management": ["garbage", "waste", "ময়লা", "আবর্জনা"],
    "Street Light": ["light", "lamp", "বাতি", "স্ট্রিট লাইট"],
    "Water Supply": ["water", "pipeline", "পানি", "লাইন"],
    "Public Safety": ["crime", "unsafe", "নিরাপত্তা", "ঝুঁকি"],
}

URGENCY_KEYWORDS = {
    "Critical": ["urgent", "emergency", "immediately", "খুব জরুরি", "জরুরি"],
    "High": ["soon", "quickly", "দ্রুত"],
    "Medium": ["issue", "problem", "সমস্যা"],
}


class AIComplaintProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, complaint_text: str) -> ComplaintExtraction:
        if self.settings.groq_api_key:
            extracted = await self._extract_with_groq(complaint_text)
            if extracted:
                return extracted
        return self._heuristic_extract(complaint_text)

    async def _extract_with_groq(self, complaint_text: str) -> ComplaintExtraction | None:
        system_prompt = """
You extract civic complaint data for Dhaka city operations.
Return strict JSON with keys:
category, thana, area, duration, urgency, summary
Use short strings. If something is missing, infer conservatively.
"""
        body: dict[str, Any] = {
            "model": self.settings.groq_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": complaint_text},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        return ComplaintExtraction.model_validate(json.loads(content))

    def _heuristic_extract(self, complaint_text: str) -> ComplaintExtraction:
        lowered = complaint_text.lower()
        category = self._match_first(CATEGORY_KEYWORDS, lowered) or "General Civic Issue"
        urgency = self._match_first(URGENCY_KEYWORDS, lowered) or "Medium"
        thana = next((name for name in KNOWN_THANAS if name.lower() in lowered), "Unspecified")
        area = self._extract_area(complaint_text)
        duration = self._extract_duration(complaint_text)
        summary = complaint_text.strip().replace("\n", " ")[:200]
        return ComplaintExtraction(
            category=category,
            thana=thana,
            area=area,
            duration=duration,
            urgency=urgency,
            summary=summary,
        )

    @staticmethod
    def _match_first(mapping: dict[str, list[str]], lowered_text: str) -> str | None:
        for label, keywords in mapping.items():
            if any(keyword.lower() in lowered_text for keyword in keywords):
                return label
        return None

    @staticmethod
    def _extract_area(text: str) -> str:
        match = re.search(r"(area|near|around|এলাকা|পাশে)\s*[:\-]?\s*([A-Za-z0-9\u0980-\u09FF ,.-]+)", text, re.IGNORECASE)
        if match:
            return match.group(2).strip()[:80]
        return "Unspecified"

    @staticmethod
    def _extract_duration(text: str) -> str:
        match = re.search(r"(\d+\s+(day|days|week|weeks|month|months|দিন|সপ্তাহ|মাস))", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return "Not specified"
