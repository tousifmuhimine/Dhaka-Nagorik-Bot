"""Groq LLM service for complaint chatbot."""
import os
from groq import Groq


class GroqService:
    """Service for interacting with Groq LLM."""
    
    def __init__(self):
        """Initialize Groq client."""
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=api_key)
        self.model = "mixtral-8x7b-32768"  # Fast and good for our use case
        self.conversation_history = []
    
    def chat(self, user_message: str, system_prompt: str = None) -> str:
        """
        Send a message to Groq and get a response.
        
        Args:
            user_message: The user's message
            system_prompt: Optional system prompt to guide the LLM
            
        Returns:
            The LLM's response
        """
        if not system_prompt:
            system_prompt = """You are a helpful civic complaint assistant for Dhaka city. 
You help users file complaints about infrastructure, utilities, and public services.
Be conversational, empathetic, and ask clarifying questions when needed.
Support both Bangla and English. Extract key information from user messages:
- Type of complaint (e.g., pothole, water leak, garbage, noise, etc.)
- Location (thana/area in Dhaka)
- Duration (how long has the issue existed)
Be concise and friendly."""
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Groq API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                *self.conversation_history
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def extract_complaint_info(self, conversation_text: list[dict]) -> dict:
        """
        Extract structured complaint information from conversation.
        
        Args:
            conversation_text: List of messages in the conversation
            
        Returns:
            Dictionary with extracted info:
            {
                "category": "type of complaint",
                "area": "thana/area",
                "duration": "how long",
                "description": "full description",
                "inconsistency_score": 1-5,
                "keywords": ["key", "words"]
            }
        """
        conversation_str = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_text
        ])
        
        extraction_prompt = f"""Analyze this civic complaint conversation and extract:
1. Category (pothole, water, garbage, electricity, noise, etc.)
2. Area/Thana in Dhaka (e.g., Mirpur, Dhanmondi, Gulshan, etc.)
3. Duration (e.g., "2 weeks", "3 months", "ongoing")
4. Full description
5. Inconsistencies (1=very consistent, 5=highly inconsistent with policy/reality)
6. Keywords (3-5 main keywords)

Respond in JSON format:
{{
    "category": "...",
    "area": "...",
    "duration": "...",
    "description": "...",
    "inconsistency_score": 1-5,
    "keywords": ["key1", "key2", "key3"]
}}

Conversation:
{conversation_str}"""
        
        extraction_prompt_with_system = """You are an expert complaint analyst. Extract and structure complaint information into JSON.
Only respond with valid JSON, no additional text."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": extraction_prompt_with_system},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0,
            max_tokens=500,
        )
        
        import json
        
        result_text = response.choices[0].message.content
        
        # Try to parse JSON
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return default structure
            return {
                "category": "unknown",
                "area": "unknown",
                "duration": "unknown",
                "description": conversation_str,
                "inconsistency_score": 3,
                "keywords": ["complaint", "issue"]
            }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
