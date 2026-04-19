"""Groq LLM service for the complaint chatbot."""

import json
import os
from typing import Iterable, List, Optional

from groq import Groq


class GroqService:
    """Service for interacting with Groq chat completions."""

    def __init__(self):
        """Initialize the Groq client."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    def _normalize_messages(self, conversation_history: Optional[Iterable[dict]]) -> List[dict]:
        """Keep only valid Groq-compatible chat messages."""
        normalized = []
        for message in conversation_history or []:
            role = (message or {}).get("role")
            content = ((message or {}).get("content") or "").strip()
            if role in {"user", "assistant", "system"} and content:
                normalized.append({
                    "role": role,
                    "content": content,
                })
        return normalized

    def chat(
        self,
        conversation_history: list[dict],
        system_prompt: str = None,
        policy_context: str = "",
        validation_context: str = "",
    ) -> str:
        """
        Send the full conversation to Groq and get the next assistant message.
        """
        if not system_prompt:
            system_prompt = """You are Dhaka Nagorik AI, the civic complaint assistant for Dhaka.
Never introduce yourself using any other name.
You help users file complaints about infrastructure, utilities, and public services.
Be conversational, empathetic, and ask clarifying questions when needed.
Support both Bangla and English. Extract key information from user messages:
- Type of complaint (e.g., pothole, water leak, garbage, noise, etc.)
- Location (thana/area in Dhaka)
- Duration (how long has the issue existed)
Be concise and friendly, and avoid long generic welcome speeches."""

        messages = [{"role": "system", "content": system_prompt}]
        if policy_context:
            messages.append({
                "role": "system",
                "content": (
                    "Relevant municipal policy context is below. Use it to guide the user, "
                    "but do not invent rules beyond this context.\n\n"
                    f"{policy_context}"
                ),
            })
        if validation_context:
            messages.append({
                "role": "system",
                "content": (
                    "Recent validation context is below. Use it carefully as supporting "
                    "context, not as a final legal judgment.\n\n"
                    f"{validation_context}"
                ),
            })

        messages.extend(self._normalize_messages(conversation_history))

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def extract_complaint_info(
        self,
        conversation_text: list[dict],
        policy_context: str = "",
    ) -> dict:
        """
        Extract structured complaint information from a conversation.
        """
        conversation_str = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_text
        )

        extraction_prompt = f"""Analyze this civic complaint conversation and extract:
1. Category (pothole, water, garbage, electricity, noise, etc.)
2. Area/Thana in Dhaka (e.g., Mirpur, Dhanmondi, Gulshan, etc.)
3. Duration (e.g., "2 weeks", "3 months", "ongoing")
4. Full description of the complaint
5. Inconsistency score (1=consistent, 5=highly inconsistent)
6. Keywords (3-5 main keywords)

If the user has not provided enough information, leave unknown fields as empty strings.

Respond in JSON format:
{{
    "category": "",
    "area": "",
    "duration": "",
    "description": "",
    "inconsistency_score": 3,
    "keywords": ["key1", "key2", "key3"]
}}

Conversation:
{conversation_str}
"""

        messages = [{
            "role": "system",
            "content": (
                "You are an expert complaint analyst. Extract and structure complaint "
                "information into valid JSON only."
            ),
        }]
        if policy_context:
            messages.append({
                "role": "system",
                "content": (
                    "Relevant policy context is below. Use it when estimating whether the "
                    "complaint seems consistent, but still output JSON only.\n\n"
                    f"{policy_context}"
                ),
            })
        messages.append({"role": "user", "content": extraction_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            max_tokens=500,
        )

        result_text = response.choices[0].message.content
        return self._coerce_extraction_payload(result_text, conversation_str)

    def _default_extraction_payload(self, conversation_str: str) -> dict:
        """Return a safe default extraction payload."""
        return {
            "category": "",
            "area": "",
            "duration": "",
            "description": conversation_str,
            "inconsistency_score": 3,
            "keywords": ["complaint", "issue"],
        }

    def _coerce_extraction_payload(self, result_text, conversation_str: str) -> dict:
        """Parse Groq output defensively and always return a dict payload."""
        if isinstance(result_text, list):
            result_text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in result_text
            )

        if not isinstance(result_text, str):
            return self._default_extraction_payload(conversation_str)

        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        candidates = [cleaned]
        if "{" in cleaned and "}" in cleaned:
            candidates.append(cleaned[cleaned.find("{"):cleaned.rfind("}") + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, dict):
                return parsed

            if isinstance(parsed, str):
                try:
                    reparsed = json.loads(parsed)
                except json.JSONDecodeError:
                    continue
                if isinstance(reparsed, dict):
                    return reparsed

        return self._default_extraction_payload(conversation_str)
