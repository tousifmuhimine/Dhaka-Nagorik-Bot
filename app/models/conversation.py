"""Data models for chat conversations."""

from __future__ import annotations

from enum import StrEnum
from datetime import datetime
from typing import Any


class MessageRole(StrEnum):
    """Message sender role in conversation."""
    user = "user"
    assistant = "assistant"
    system = "system"


class ConversationStatus(StrEnum):
    """Status of a conversation."""
    active = "active"
    complaint_submitted = "complaint_submitted"
    completed = "completed"
    abandoned = "abandoned"


class Message:
    """A single message in a conversation."""

    def __init__(
        self,
        role: MessageRole,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create message from dictionary."""
        return cls(
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            metadata=data.get("metadata", {}),
        )


class Conversation:
    """Represents a chat conversation session."""

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        status: ConversationStatus = ConversationStatus.active,
        complaint_id: str | None = None,
        messages: list[Message] | None = None,
        created_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> None:
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.status = status
        self.complaint_id = complaint_id
        self.messages = messages or []
        self.created_at = created_at or datetime.utcnow()
        self.ended_at = ended_at

    def add_message(self, role: MessageRole, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a message to the conversation."""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)

    def get_last_user_message(self) -> Message | None:
        """Get the last message from user."""
        for message in reversed(self.messages):
            if message.role == MessageRole.user:
                return message
        return None

    def get_conversation_context(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent messages for context (for LLM)."""
        recent = self.messages[-limit:]
        return [msg.to_dict() for msg in recent]

    def to_dict(self) -> dict[str, Any]:
        """Convert conversation to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "complaint_id": self.complaint_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Conversation:
        """Create conversation from dictionary."""
        messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        return cls(
            conversation_id=data.get("conversation_id", ""),
            user_id=data.get("user_id", ""),
            status=ConversationStatus(data.get("status", "active")),
            complaint_id=data.get("complaint_id"),
            messages=messages,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
        )
