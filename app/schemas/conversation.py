"""Pydantic schemas for chat conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.conversation import ConversationStatus, MessageRole


class MessageSchema(BaseModel):
    """Schema for a single message."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=5000)
    timestamp: datetime | None = None
    metadata: dict | None = Field(default_factory=dict)


class ChatSendRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=5000, description="User's message")
    conversation_id: str | None = None  # If None, create new conversation


class ChatResponse(BaseModel):
    """Response schema for chat message."""

    conversation_id: str
    user_message: str
    assistant_message: str
    extracted_data: dict | None = None  # Extracted complaint fields if any
    suggested_action: str | None = None  # e.g., "submit_complaint", "ask_clarification"


class ConversationStartRequest(BaseModel):
    """Request to start a new conversation."""

    initial_message: str | None = Field(default=None, description="Optional first message")


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""

    conversation_id: str
    messages: list[MessageSchema]
    status: str
    complaint_id: str | None = None
    created_at: datetime
    message_count: int


class ConversationSummaryResponse(BaseModel):
    """Response schema for conversation summary."""

    conversation_id: str
    user_id: str
    status: str
    message_count: int
    created_at: datetime
    ended_at: datetime | None = None
    complaint_id: str | None = None
    last_message: str | None = None


class SubmitFromChatRequest(BaseModel):
    """Request to submit complaint from chat conversation."""

    conversation_id: str
    preferred_language: Literal["bn", "en"] = "bn"
    attachment_urls: list[str] = Field(default_factory=list)


class ComplaintFromChatResponse(BaseModel):
    """Response when complaint is submitted from chat."""

    complaint_id: str
    conversation_id: str
    message: str = "Complaint submitted successfully"
    reference_id: str  # Short readable ID for user
