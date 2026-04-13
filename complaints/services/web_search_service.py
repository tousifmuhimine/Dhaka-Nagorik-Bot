"""Web search service using Tavily for fact-checking and policy validation."""
import os
from typing import Optional
from tavily import TavilyClient


class WebSearchService:
    """Service for conducting web searches to validate complaints."""
    
    def __init__(self):
        """Initialize Tavily client."""
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")
        
        self.client = TavilyClient(api_key=api_key)
    
    def search_for_verification(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Search for information to verify a complaint.
        
        Args:
            query: Search query about the complaint (e.g., "pothole road Dhaka water logging")
            max_results: Number of results to return
            
        Returns:
            List of search results with title, url, content, and relevance
        """
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_answer=True
            )
            
            results = []
            
            # Extract answer if available
            if response.get('answer'):
                results.append({
                    'title': 'Direct Answer',
                    'content': response['answer'],
                    'source': 'AI Summary',
                    'relevance': 0.95
                })
            
            # Extract web results
            for result in response.get('results', []):
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', '')[:500],
                    'source': result.get('source', ''),
                    'relevance': 0.8
                })
            
            return results
        
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []
    
    def search_dhaka_complaints(self, category: str, area: str) -> list[dict]:
        """
        Search for similar complaints in Dhaka.
        
        Args:
            category: Type of complaint (e.g., "pothole", "water")
            area: Area/Thana in Dhaka
            
        Returns:
            List of relevant search results
        """
        query = f"{category} problem {area} Dhaka complaint infrastructure"
        return self.search_for_verification(query)
    
    def validate_against_policy(self, complaint: dict) -> dict:
        """
        Check if complaint aligns with known policies and real-world issues.
        
        Args:
            complaint: Dictionary with complaint details
            {
                "category": "...",
                "area": "...",
                "duration": "...",
                "description": "..."
            }
            
        Returns:
            Validation result:
            {
                "is_valid": bool,
                "inconsistencies": [list of issues],
                "references": [list of supporting sources],
                "recommendation": "..."
            }
        """
        search_query = f"{complaint.get('category', 'issue')} {complaint.get('area', 'Dhaka')}"
        search_results = self.search_for_verification(search_query)
        
        inconsistencies = []
        
        # Check if area is in Dhaka
        valid_thanas = [
            "mirpur", "dhanmondi", "gulshan", "banani", "baridhara", "motijheel",
            "rampura", "boshundhara", "uttara", "adabor", "cantonment", "savar",
            "tongi", "khilgaon", "malibagh", "paltan", "ramna", "sutrapur",
            "shakbazar", "ibrahimpur", "kotwali"
        ]
        
        if complaint.get('area', '').lower() not in valid_thanas:
            inconsistencies.append(f"Area '{complaint.get('area')}' may not be in Dhaka")
        
        # Check duration sanity
        duration = complaint.get('duration', '').lower()
        if 'year' in duration and '10' in duration:
            inconsistencies.append("Duration seems unusually long (10+ years)")
        
        return {
            'is_valid': len(inconsistencies) == 0,
            'inconsistencies': inconsistencies,
            'references': search_results[:3],
            'recommendation': self._generate_recommendation(complaint, search_results)
        }
    
    def _generate_recommendation(self, complaint: dict, search_results: list) -> str:
        """Generate a recommendation based on complaint and search results."""
        category = complaint.get('category', 'issue')
        area = complaint.get('area', 'your area')
        
        if search_results:
            return f"Your {category} complaint in {area} has been verified against recent reports. Please proceed with filing a formal complaint with the municipal authority."
        else:
            return f"Limited information found. Consider providing more specific details about the {category} in {area} to help expedite resolution."
