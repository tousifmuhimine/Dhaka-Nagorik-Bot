"""Web search service using Tavily API for policy validation and information enrichment."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SearchService:
    """Service for web search and external policy validation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        # Note: tavily-python client will be imported when needed if available
        self._client = None

    @property
    def enabled(self) -> bool:
        """Check if Tavily search is configured."""
        return self.settings.has_tavily_config

    def _get_client(self) -> Any:
        """Lazily import and initialize Tavily client."""
        if self._client is None and self.enabled:
            try:
                from tavily import TavilyClient

                self._client = TavilyClient(api_key=self.settings.tavily_api_key)
            except ImportError:
                logger.warning("tavily-python not installed. Install with: pip install tavily-python")
                return None
        return self._client

    async def search_policy_context(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Search for policy-related information using Tavily.

        Args:
            query: Search query about policy or complaint
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and snippet
        """
        if not self.enabled:
            logger.warning("Tavily search disabled. Returning empty results.")
            return []

        try:
            client = self._get_client()
            if client is None:
                return []

            results = client.search(query, max_results=max_results)

            # Extract relevant information
            parsed_results = []
            if "results" in results:
                for result in results["results"]:
                    parsed_results.append(
                        {
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", ""),
                            "content": result.get("content", ""),
                        }
                    )

            logger.info(f"Tavily search completed. Found {len(parsed_results)} results for: {query}")
            return parsed_results

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    async def validate_policy_compliance(
        self, category: str, thana: str, area: str, complaint_summary: str
    ) -> dict[str, Any]:
        """
        Search for policy information to validate complaint compliance.

        Args:
            category: Complaint category
            thana: Thana name
            area: Area in thana
            complaint_summary: Summary of complaint

        Returns:
            Dictionary with compliance_info and search_results
        """
        if not self.enabled:
            logger.warning("Tavily search disabled. Skipping policy validation.")
            return {"compliance_info": "", "search_results": [], "confidence": 0.0}

        try:
            # Build search query
            query = f"Dhaka {thana} {category} policy compliance {area}"

            results = await self.search_policy_context(query, max_results=3)

            # Combine snippets into compliance info
            compliance_info = " ".join([r["snippet"] for r in results])

            logger.info(f"Policy compliance search completed for {category} in {thana}")
            return {
                "compliance_info": compliance_info[:500],  # Limit length
                "search_results": results,
                "confidence": min(len(results) / 3, 1.0),  # Normalize to 0-1
            }

        except Exception as e:
            logger.error(f"Policy compliance validation failed: {e}")
            return {"compliance_info": "", "search_results": [], "confidence": 0.0}

    async def search_similar_complaints(self, category: str, thana: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Search for similar complaints or issues in the area.

        Args:
            category: Complaint category
            thana: Thana name
            max_results: Maximum results

        Returns:
            List of similar complaint information
        """
        if not self.enabled:
            logger.warning("Tavily search disabled. Cannot search similar complaints.")
            return []

        try:
            query = f"Dhaka {category} complaints {thana} issues"
            results = await self.search_policy_context(query, max_results=max_results)
            logger.info(f"Found {len(results)} similar complaints for {category} in {thana}")
            return results

        except Exception as e:
            logger.error(f"Similar complaints search failed: {e}")
            return []

    async def get_authority_contact_info(self, thana: str) -> dict[str, Any]:
        """
        Search for authority contact information.

        Args:
            thana: Thana name

        Returns:
            Dictionary with contact information
        """
        if not self.enabled:
            logger.warning("Tavily search disabled. Cannot fetch authority info.")
            return {}

        try:
            query = f"Dhaka {thana} thana police station contact address phone"
            results = await self.search_policy_context(query, max_results=2)

            if results:
                return {
                    "thana": thana,
                    "info": results[0]["snippet"],
                    "sources": results,
                }

            return {"thana": thana, "info": "", "sources": []}

        except Exception as e:
            logger.error(f"Authority contact search failed: {e}")
            return {}


# Singleton instance
_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    """Get or create search service singleton."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
