"""Web search service using Tavily for fact-checking and policy validation."""

import os

from tavily import TavilyClient


class WebSearchService:
    """Service for conducting web searches to validate complaints."""

    def __init__(self):
        """Initialize Tavily client."""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")

        self.client = TavilyClient(api_key=api_key)

    def search_for_verification(self, query: str, max_results: int = 5) -> list[dict]:
        """Search for information to verify a complaint."""
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=True,
            )

            results = []
            if response.get("answer"):
                results.append({
                    "title": "Direct Answer",
                    "content": response["answer"],
                    "source": "AI Summary",
                    "relevance": 0.95,
                })

            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")[:500],
                    "source": result.get("source", ""),
                    "relevance": 0.8,
                })

            return results
        except Exception as exc:
            print(f"Tavily search error: {exc}")
            return []

    def validate_against_policy(self, complaint: dict, policies: list[dict] = None) -> dict:
        """Combine web search results with retrieved policy context."""
        policies = policies or []
        category = complaint.get("category", "") or "issue"
        area = complaint.get("area", "") or "Dhaka"
        description = complaint.get("description", "") or ""
        duration = (complaint.get("duration", "") or "").lower()

        search_query = " ".join(part for part in [category, area, description[:120], "Dhaka complaint"] if part).strip()
        search_results = self.search_for_verification(search_query)

        inconsistencies = []
        valid_thanas = {
            "mirpur", "dhanmondi", "gulshan", "banani", "baridhara", "motijheel",
            "rampura", "boshundhara", "uttara", "adabor", "cantonment", "savar",
            "tongi", "khilgaon", "malibagh", "paltan", "ramna", "sutrapur",
            "shakbazar", "ibrahimpur", "kotwali",
        }

        if complaint.get("area") and complaint["area"].lower() not in valid_thanas:
            inconsistencies.append(f"Area '{complaint.get('area')}' may not be a Dhaka thana.")

        if "year" in duration and any(number in duration for number in ("10", "11", "12", "15", "20")):
            inconsistencies.append("Duration seems unusually long and should be confirmed.")

        if not policies:
            inconsistencies.append("No closely matching municipal policy context was retrieved.")

        policy_references = []
        for policy in policies[:3]:
            policy_references.append({
                "title": policy.get("title_en") or policy.get("title") or "Policy Reference",
                "category": policy.get("category", ""),
                "content": (policy.get("content", "") or "")[:320],
                "source_file": policy.get("source_file", ""),
            })

        recommendation = self._generate_recommendation(
            category=category,
            area=area,
            search_results=search_results,
            policy_references=policy_references,
            inconsistencies=inconsistencies,
        )

        return {
            "is_valid": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies,
            "references": search_results[:3],
            "policy_references": policy_references,
            "recommendation": recommendation,
        }

    def _generate_recommendation(
        self,
        category: str,
        area: str,
        search_results: list[dict],
        policy_references: list[dict],
        inconsistencies: list[str],
    ) -> str:
        """Generate a short actionable recommendation."""
        if inconsistencies:
            return (
                f"Please confirm the complaint details for {category} in {area} before filing. "
                "The assistant found gaps or inconsistencies that may need clarification."
            )

        if search_results and policy_references:
            return (
                f"This {category} complaint in {area} aligns with retrieved policy context and "
                "recent search results. It is ready to be filed as a formal complaint."
            )

        if policy_references:
            return (
                f"Policy context was found for this {category} issue, but web verification was limited. "
                "You can still file the complaint with the details collected so far."
            )

        return (
            f"Limited supporting context was found for this {category} issue in {area}. "
            "Try providing a more specific location, timeline, or incident description."
        )
