"""Service for managing chat conversations and extracting complaints from chat."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import get_settings
from app.db.conversation_repository import ConversationRepository, get_conversation_repository
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.schemas.complaint import ComplaintCreateRequest, ComplaintExtraction, ComplaintRecord
from app.services.advanced_rag_service import get_advanced_rag_service
from app.services.ai_processor import AIComplaintProcessor
from app.services.corporation_service import get_corporation_service
from app.services.policy_rag import PolicyRAGService

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing chat conversations and complaint extraction."""

    def __init__(self, repository: ConversationRepository | None = None) -> None:
        self.settings = get_settings()
        self.ai_processor = AIComplaintProcessor()
        self.policy_rag = PolicyRAGService()
        self.advanced_rag = None  # Will be initialized lazily
        self.corporation_service = get_corporation_service()
        self.repository = repository or get_conversation_repository()
        # Fallback in-memory storage if database not available
        self._conversations: dict[str, Conversation] = {}

    async def start_conversation(self, user_id: str, initial_message: str | None = None) -> str:
        """
        Start a new chat conversation.

        Args:
            user_id: ID of user starting conversation
            initial_message: Optional first message

        Returns:
            conversation_id
        """
        conversation_id = str(uuid4())
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            status=ConversationStatus.active,
        )

        # Add system greeting
        system_greeting = (
            "হ্যালো! আমি Dhaka Nagorik Bot এর চ্যাট সহায়ক। "
            "আপনার ঢাকার যেকোনো সমস্যা সম্পর্কে বলুন, "
            "এবং আমরা সেটি সঠিক কর্তৃপক্ষের কাছে পৌঁছে দেব। "
            "(You can also write in English)"
        )
        conversation.add_message(MessageRole.assistant, system_greeting)

        if initial_message:
            conversation.add_message(MessageRole.user, initial_message)

        # Save to database (or fallback to memory)
        if self.repository.enabled:
            await self.repository.create_conversation(conversation)
            logger.info(f"Started conversation {conversation_id} for user {user_id} (persisted)")
        else:
            self._conversations[conversation_id] = conversation
            logger.info(f"Started conversation {conversation_id} for user {user_id} (in-memory)")

        return conversation_id

    async def send_message(self, conversation_id: str, user_message: str) -> tuple[str, dict[str, Any] | None]:
        """
        Send a message in conversation and get response.

        Args:
            conversation_id: ID of conversation
            user_message: User's message

        Returns:
            Tuple of (assistant_response, extracted_fields)
        """
        conversation = await self._get_conversation(conversation_id)

        # Add user message
        conversation.add_message(MessageRole.user, user_message)

        # Try to extract complaint data from user message
        extracted = await self.ai_processor.extract(user_message)

        # Generate assistant response based on extraction
        assistant_response = await self._generate_response(user_message, extracted)

        # Add assistant response
        conversation.add_message(MessageRole.assistant, assistant_response)

        # Persist changes
        if self.repository.enabled:
            await self.repository.update_conversation(conversation)
        else:
            self._conversations[conversation_id] = conversation

        # Return response and extracted data
        return assistant_response, extracted.model_dump() if extracted else None

    async def get_conversation_history(self, conversation_id: str) -> Conversation:
        """Get full conversation history."""
        return await self._get_conversation(conversation_id)

    async def extract_complaint_from_conversation(self, conversation_id: str) -> ComplaintExtraction | None:
        """
        Extract structured complaint data from entire conversation.

        Args:
            conversation_id: ID of conversation

        Returns:
            Extracted complaint data or None if insufficient data
        """
        conversation = await self._get_conversation(conversation_id)

        # Combine all user messages
        user_messages = [msg.content for msg in conversation.messages if msg.role == MessageRole.user]
        combined_text = " ".join(user_messages)

        if not combined_text.strip():
            logger.warning(f"No user messages in conversation {conversation_id}")
            return None

        # Extract from combined text
        extracted = await self.ai_processor.extract(combined_text)
        return extracted

    async def submit_complaint_from_chat(
        self, conversation_id: str, preferred_language: str = "bn", attachment_urls: list[str] | None = None
    ) -> ComplaintRecord | None:
        """
        Submit a complaint extracted from conversation.

        Args:
            conversation_id: ID of conversation
            preferred_language: Bangla or English
            attachment_urls: Optional attachment URLs

        Returns:
            Submitted complaint record
        """
        conversation = await self._get_conversation(conversation_id)

        if conversation.complaint_id:
            logger.warning(f"Complaint already submitted for conversation {conversation_id}")
            return None

        # Extract complaint from conversation
        extracted = await self.extract_complaint_from_conversation(conversation_id)
        if not extracted:
            raise HTTPException(status_code=400, detail="Unable to extract complaint data from conversation")

        # Create complaint request
        user_messages = [msg.content for msg in conversation.messages if msg.role == MessageRole.user]
        original_text = " ".join(user_messages)

        complaint_request = ComplaintCreateRequest(
            complaint_text=original_text,
            preferred_language=preferred_language,
            attachment_urls=attachment_urls or [],
        )

        # Get corporation from thana
        corporation = self.corporation_service.get_corporation_by_thana(extracted.thana)

        # Evaluate policy
        policy = await self.policy_rag.evaluate(extracted, original_text)

        # Create complaint record
        complaint_id = str(uuid4())
        complaint = ComplaintRecord(
            id=complaint_id,
            user_id=conversation.user_id,
            category=extracted.category,
            thana=extracted.thana,
            area=extracted.area,
            duration=extracted.duration,
            urgency=extracted.urgency,
            summary=extracted.summary,
            original_text=original_text,
            preferred_language=preferred_language,
            attachment_urls=attachment_urls or [],
            status="Pending",
            compliance_status=policy.compliance_status,
            inconsistency_score=policy.inconsistency_score,
            delayed=policy.delayed,
            matched_policy_sections=policy.matched_policy_sections,
            created_at=datetime.utcnow(),
        )

        # Update conversation
        conversation.complaint_id = complaint_id
        conversation.status = ConversationStatus.complaint_submitted
        conversation.add_message(
            MessageRole.system,
            f"Complaint submitted with ID: {complaint_id[:8].upper()}",
        )

        # Persist
        if self.repository.enabled:
            await self.repository.update_conversation(conversation)
        else:
            self._conversations[conversation_id] = conversation

        logger.info(f"Complaint {complaint_id} submitted from conversation {conversation_id}")
        return complaint

    async def end_conversation(self, conversation_id: str) -> None:
        """End a conversation session."""
        conversation = await self._get_conversation(conversation_id)
        conversation.status = ConversationStatus.completed
        conversation.ended_at = datetime.utcnow()

        # Persist
        if self.repository.enabled:
            await self.repository.update_conversation(conversation)
        else:
            self._conversations[conversation_id] = conversation

        logger.info(f"Ended conversation {conversation_id}")

    async def _get_conversation(self, conversation_id: str) -> Conversation:
        """Get conversation from database or memory."""
        # Try database first if available
        if self.repository.enabled:
            conversation = await self.repository.get_conversation(conversation_id)
            if conversation:
                return conversation

        # Fallback to in-memory
        if conversation_id in self._conversations:
            return self._conversations[conversation_id]

        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

    async def _generate_response(self, user_message: str, extracted: ComplaintExtraction | None) -> str:
        """Generate conversational response based on extraction."""
        if not extracted:
            # No extraction, ask for more info
            return (
                "আমাদের কাছে আরও বিবরণ প্রয়োজন। "
                "অনুগ্রহ করে বলুন:\n"
                "- সমস্যার ধরন কী? (রাস্তা ক্ষতি, পানি সরবরাহ, ড্রেনেজ, ইত্যাদি)\n"
                "- কোন এলাকায় সমস্যা? (থানা ও এলাকার নাম)\n"
                "- সমস্যার গুরুত্ব কী? (জরুরি বা সাধারণ)\n\n"
                "(Or describe the issue in English)"
            )

        # Successfully extracted, provide summary
        response = (
            f"আপনার সমস্যা বুঝেছি:\n\n"
            f"**বিভাগ:** {extracted.category}\n"
            f"**থানা:** {extracted.thana}\n"
            f"**এলাকা:** {extracted.area}\n"
            f"**জরুরিতা:** {extracted.urgency}\n"
            f"**সারসংক্ষেপ:** {extracted.summary}\n\n"
            "এই তথ্য সঠিক মনে হলে, আপনার অভিযোগ জমা দিতে 'Submit' বোতাম ক্লিক করুন। "
            "নয়তো, আরও বিবরণ প্রদান করুন।"
        )
        return response

    async def _enhance_context_with_semantic_search(self, complaint_text: str) -> str:
        """
        Enhance complaint context with semantic search from advanced RAG.

        Args:
            complaint_text: Original complaint text

        Returns:
            Enhanced context string for AI extraction
        """
        try:
            # Lazy initialize advanced RAG
            if self.advanced_rag is None:
                self.advanced_rag = await get_advanced_rag_service()

            if self.advanced_rag and self.advanced_rag._initialized:
                context = await self.advanced_rag.get_context_for_extraction(complaint_text, top_k=3)
                if context:
                    logger.debug(f"Enhanced context with semantic search ({len(context)} chars)")
                    return context
        except Exception as e:
            logger.warning(f"Failed to enhance context with semantic search: {e}")

        return ""


# Singleton instance
_conversation_service: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """Get or create conversation service singleton."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
