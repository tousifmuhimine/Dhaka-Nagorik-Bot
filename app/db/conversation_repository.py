"""Repository for managing conversations in Supabase."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.db.supabase_client import SupabaseRestClient
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Handle persistence of conversations to Supabase."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.supabase = SupabaseRestClient()

    @property
    def enabled(self) -> bool:
        """Check if Supabase is available."""
        return self.supabase.enabled

    async def create_conversation(self, conversation: Conversation) -> str:
        """
        Create a new conversation in database.

        Args:
            conversation: Conversation object

        Returns:
            conversation_id
        """
        if not self.enabled:
            logger.warning("Supabase not available. Conversation not persisted.")
            return conversation.conversation_id

        try:
            payload = {
                "id": conversation.conversation_id,
                "user_id": conversation.user_id,
                "status": conversation.status.value,
                "messages": json.dumps([msg.to_dict() for msg in conversation.messages]),
                "message_count": len(conversation.messages),
                "complaint_id": conversation.complaint_id,
            }

            await self.supabase.insert("conversations", payload)
            logger.info(f"Created conversation {conversation.conversation_id} in Supabase")
            return conversation.conversation_id

        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation from database."""
        if not self.enabled:
            logger.warning("Supabase not available. Cannot retrieve conversation.")
            return None

        try:
            params = {
                "id": f"eq.{conversation_id}",
                "select": "*",
            }
            results = await self.supabase.select("conversations", params)

            if not results:
                logger.warning(f"Conversation {conversation_id} not found")
                return None

            data = results[0]
            messages = [Message.from_dict(msg) for msg in json.loads(data.get("messages", "[]"))]

            conversation = Conversation(
                conversation_id=data["id"],
                user_id=data["user_id"],
                status=ConversationStatus(data.get("status", "active")),
                complaint_id=data.get("complaint_id"),
                messages=messages,
                created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
                ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            )

            return conversation

        except Exception as e:
            logger.error(f"Failed to retrieve conversation: {e}")
            return None

    async def update_conversation(self, conversation: Conversation) -> bool:
        """Update an existing conversation."""
        if not self.enabled:
            logger.warning("Supabase not available. Conversation not updated.")
            return False

        try:
            payload = {
                "status": conversation.status.value,
                "messages": json.dumps([msg.to_dict() for msg in conversation.messages]),
                "message_count": len(conversation.messages),
                "complaint_id": conversation.complaint_id,
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            }

            await self.supabase.update(
                "conversations",
                {"id": f"eq.{conversation.conversation_id}"},
                payload,
            )

            logger.info(f"Updated conversation {conversation.conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update conversation: {e}")
            return False

    async def list_user_conversations(
        self, user_id: str, status: str | None = None, limit: int = 50
    ) -> list[Conversation]:
        """List all conversations for a user."""
        if not self.enabled:
            logger.warning("Supabase not available. Cannot list conversations.")
            return []

        try:
            params: dict[str, Any] = {
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc",
                "limit": str(limit),
            }

            if status:
                params["status"] = f"eq.{status}"

            results = await self.supabase.select("conversations", params)

            conversations = []
            for data in results:
                messages = [Message.from_dict(msg) for msg in json.loads(data.get("messages", "[]"))]
                conversation = Conversation(
                    conversation_id=data["id"],
                    user_id=data["user_id"],
                    status=ConversationStatus(data.get("status", "active")),
                    complaint_id=data.get("complaint_id"),
                    messages=messages,
                    created_at=datetime.fromisoformat(
                        data.get("created_at", datetime.utcnow().isoformat())
                    ),
                    ended_at=datetime.fromisoformat(data["ended_at"])
                    if data.get("ended_at")
                    else None,
                )
                conversations.append(conversation)

            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []

    async def add_message(self, conversation_id: str, message: Message) -> bool:
        """Add a message to a conversation."""
        if not self.enabled:
            logger.warning("Supabase not available. Message not persisted.")
            return False

        try:
            # Retrieve current conversation
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return False

            # Add message
            conversation.add_message(message.role, message.content, message.metadata)

            # Update in database
            return await self.update_conversation(conversation)

        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation (soft delete via status update recommended)."""
        if not self.enabled:
            logger.warning("Supabase not available. Conversation not deleted.")
            return False

        try:
            # Soft delete: update status to abandoned
            conversation = await self.get_conversation(conversation_id)
            if conversation:
                conversation.status = ConversationStatus.abandoned
                return await self.update_conversation(conversation)

            logger.warning(f"Conversation {conversation_id} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False

    async def get_conversation_by_complaint(self, complaint_id: str) -> Conversation | None:
        """Get a conversation by its associated complaint."""
        if not self.enabled:
            logger.warning("Supabase not available. Cannot retrieve conversation.")
            return None

        try:
            params = {
                "complaint_id": f"eq.{complaint_id}",
                "select": "*",
                "limit": "1",
            }
            results = await self.supabase.select("conversations", params)

            if not results:
                return None

            data = results[0]
            messages = [Message.from_dict(msg) for msg in json.loads(data.get("messages", "[]"))]

            conversation = Conversation(
                conversation_id=data["id"],
                user_id=data["user_id"],
                status=ConversationStatus(data.get("status", "active")),
                complaint_id=data.get("complaint_id"),
                messages=messages,
                created_at=datetime.fromisoformat(
                    data.get("created_at", datetime.utcnow().isoformat())
                ),
                ended_at=datetime.fromisoformat(data["ended_at"])
                if data.get("ended_at")
                else None,
            )

            return conversation

        except Exception as e:
            logger.error(f"Failed to get conversation by complaint: {e}")
            return None


# Singleton instance
_conversation_repository: ConversationRepository | None = None


def get_conversation_repository() -> ConversationRepository:
    """Get or create conversation repository singleton."""
    global _conversation_repository
    if _conversation_repository is None:
        _conversation_repository = ConversationRepository()
    return _conversation_repository
