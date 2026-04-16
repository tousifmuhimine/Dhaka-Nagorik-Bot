"""Image analysis service using Groq Vision API."""

import base64
import os
from typing import Optional

from groq import Groq


class ImageAnalysisService:
    """Service for analyzing complaint images using Groq Vision."""

    def __init__(self):
        """Initialize the Groq client with vision capabilities."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=api_key)
        self.model = os.getenv(
            "GROQ_VISION_MODEL",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        )

    def _encode_image_bytes_to_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 string."""
        return base64.standard_b64encode(image_bytes).decode("utf-8")

    def analyze_complaint_image(self, image_path: str) -> dict:
        """
        Analyze a complaint image and extract infrastructure issue details.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with analysis results including issue type, severity, location clues, etc.
        """
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        return self.analyze_complaint_image_bytes(
            image_bytes,
            filename=image_path,
        )

    def analyze_complaint_image_bytes(
        self,
        image_bytes: bytes,
        *,
        filename: str = "",
        mime_type: Optional[str] = None,
    ) -> dict:
        """Analyze a complaint image from raw bytes."""
        try:
            image_data = self._encode_image_bytes_to_base64(image_bytes)
            mime_type = mime_type or self._mime_type_for_name(filename)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self._get_analysis_prompt(),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )

            analysis_text = response.choices[0].message.content
            return self._parse_analysis(analysis_text)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "issue_type": "unknown",
                "severity": "unknown",
                "description": "Error analyzing image",
            }

    def _mime_type_for_name(self, filename: str) -> str:
        """Infer MIME type from the file extension."""
        file_ext = os.path.splitext(filename or "")[1].lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(file_ext, "image/jpeg")

    def _get_analysis_prompt(self) -> str:
        """Get the analysis prompt for image inspection."""
        return """Analyze this image of a potential civic complaint in Dhaka. Provide:

1. **Issue Type**: Identify the infrastructure/civic problem (e.g., pothole, flooding, garbage accumulation, broken streetlight, damaged road, drainage issue, electrical hazard, pollution, etc.)

2. **Severity**: Rate as critical, high, moderate, or low based on:
   - Safety risk to public
   - Scale/extent of problem
   - Impact on utilities/services

3. **Location Indicators**: What geographic clues are visible? (e.g., street signs, landmarks, shop names in Bangla, thana area indicators)

4. **Visual Evidence**: List specific problems you observe (e.g., "large pothole ~1 meter across", "stagnant water", "overflowing garbage", etc.)

5. **Recommended Action**: What should be done? (e.g., "fill pothole", "clear drainage", "remove garbage", "repair streetlight")

6. **Safety Concerns**: Any immediate dangers? (e.g., traffic hazard, electrical risk, contaminated water)

Be specific, concise, and focus on actionable details. Respond in a structured format."""

    def _parse_analysis(self, analysis_text: str) -> dict:
        """Parse the vision analysis into structured data."""
        return {
            "success": True,
            "raw_analysis": analysis_text,
            "issue_type": self._extract_issue_type(analysis_text),
            "severity": self._extract_severity(analysis_text),
            "location_indicators": self._extract_location_clues(analysis_text),
            "safety_concerns": self._extract_safety_concerns(analysis_text),
        }

    def _extract_issue_type(self, text: str) -> str:
        """Extract the primary issue type from analysis."""
        text_lower = text.lower()
        
        issue_keywords = {
            "pothole": ("pothole", "hole in road", "pit"),
            "flooding": ("flood", "water logging", "water", "drain", "stagnant water"),
            "garbage": ("garbage", "waste", "trash", "litter", "accumulation"),
            "streetlight": ("light", "streetlight", "lamp", "electrical", "dark"),
            "drainage": ("drain", "drainage", "sewer", "pipe"),
            "road_damage": ("road", "asphalt", "broken", "cracked", "damaged", "deteriorat"),
            "pollution": ("pollution", "smoke", "smog", "air quality"),
            "vegetation": ("tree", "branch", "overgrown", "vegetation"),
        }
        
        for issue_type, keywords in issue_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return issue_type
        
        return "other"

    def _extract_severity(self, text: str) -> str:
        """Extract severity level from analysis."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["critical", "severe", "dangerous", "risk", "hazard", "immediate"]):
            return "critical"
        elif any(word in text_lower for word in ["high", "significant", "major", "urgent"]):
            return "high"
        elif any(word in text_lower for word in ["moderate", "medium", "noticeable"]):
            return "moderate"
        else:
            return "low"

    def _extract_location_clues(self, text: str) -> list:
        """Extract location-related clues from the analysis."""
        clues = []
        text_lines = text.split('\n')
        
        for line in text_lines:
            if any(word in line.lower() for word in ["location", "sign", "landmark", "near", "street", "area"]):
                clue = line.strip().strip('-').strip('•').strip('*').strip()
                if clue and len(clue) > 5:
                    clues.append(clue)
        
        return clues[:5]  # Return top 5 clues

    def _extract_safety_concerns(self, text: str) -> list:
        """Extract safety concerns from the analysis."""
        concerns = []
        text_lines = text.split('\n')
        
        for line in text_lines:
            if any(word in line.lower() for word in ["danger", "risk", "hazard", "safety", "concern", "threat"]):
                concern = line.strip().strip('-').strip('•').strip('*').strip()
                if concern and len(concern) > 5:
                    concerns.append(concern)
        
        return concerns[:5]  # Return top 5 concerns

    def batch_analyze_images(self, image_paths: list) -> dict:
        """Analyze multiple images and combine results."""
        results = []
        for path in image_paths:
            try:
                result = self.analyze_complaint_image(path)
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "file": path,
                })
        
        # Combine analyses
        combined_severity = self._combine_severities([r.get("severity") for r in results if r.get("success")])
        combined_types = list(set([r.get("issue_type") for r in results if r.get("success")]))
        
        return {
            "total_images": len(image_paths),
            "successful": sum(1 for r in results if r.get("success")),
            "combined_severity": combined_severity,
            "issue_types": combined_types,
            "individual_results": results,
        }

    def _combine_severities(self, severities: list) -> str:
        """Combine multiple severity levels into one."""
        severity_order = ["critical", "high", "moderate", "low"]
        
        for sev in severity_order:
            if sev in severities:
                return sev
        
        return "low"
