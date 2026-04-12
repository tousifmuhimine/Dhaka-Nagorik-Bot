"""API routes for chat conversations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import UserContext, get_user_context
from app.schemas.conversation import (
    ChatResponse,
    ChatSendRequest,
    ComplaintFromChatResponse,
    ConversationHistoryResponse,
    ConversationStartRequest,
    ConversationSummaryResponse,
    MessageSchema,
    SubmitFromChatRequest,
)
from app.services.conversation_service import ConversationService, get_conversation_service

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


@chat_router.post("/start", response_model=dict)
async def start_chat(
    payload: ConversationStartRequest,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """Start a new chat conversation."""
    conversation_id = await service.start_conversation(user.user_id, payload.initial_message)
    return {
        "conversation_id": conversation_id,
        "message": "Chat started successfully",
    }


@chat_router.post("/{conversation_id}/message", response_model=ChatResponse)
async def send_chat_message(
    conversation_id: str,
    payload: ChatSendRequest,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ChatResponse:
    """Send a message in chat conversation."""
    # Verify conversation ownership
    conversation = await service.get_conversation_history(conversation_id)
    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only access your own conversations")

    # Send message and get response
    assistant_response, extracted_data = await service.send_message(conversation_id, payload.message)

    # Determine suggested action
    suggested_action = None
    if extracted_data and all(k in extracted_data for k in ["category", "thana", "urgency"]):
        suggested_action = "submit_complaint"
    elif not extracted_data:
        suggested_action = "ask_clarification"

    return ChatResponse(
        conversation_id=conversation_id,
        user_message=payload.message,
        assistant_message=assistant_response,
        extracted_data=extracted_data,
        suggested_action=suggested_action,
    )


@chat_router.get("/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_chat_history(
    conversation_id: str,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationHistoryResponse:
    """Get chat conversation history."""
    conversation = await service.get_conversation_history(conversation_id)
    
    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only access your own conversations")

    messages = [
        MessageSchema(
            role=msg.role.value,
            content=msg.content,
            timestamp=msg.timestamp,
            metadata=msg.metadata,
        )
        for msg in conversation.messages
    ]

    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=messages,
        status=conversation.status.value,
        complaint_id=conversation.complaint_id,
        created_at=conversation.created_at,
        message_count=len(conversation.messages),
    )


@chat_router.get("/{conversation_id}/summary", response_model=ConversationSummaryResponse)
async def get_chat_summary(
    conversation_id: str,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationSummaryResponse:
    """Get chat conversation summary."""
    conversation = await service.get_conversation_history(conversation_id)
    
    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only access your own conversations")

    last_message = conversation.messages[-1].content if conversation.messages else None

    return ConversationSummaryResponse(
        conversation_id=conversation_id,
        user_id=conversation.user_id,
        status=conversation.status.value,
        message_count=len(conversation.messages),
        created_at=conversation.created_at,
        ended_at=conversation.ended_at,
        complaint_id=conversation.complaint_id,
        last_message=last_message,
    )


@chat_router.post("/{conversation_id}/submit", response_model=ComplaintFromChatResponse)
async def submit_complaint_from_chat(
    conversation_id: str,
    payload: SubmitFromChatRequest,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> ComplaintFromChatResponse:
    """Extract and submit complaint from chat conversation."""
    # Verify conversation ownership
    conversation = await service.get_conversation_history(conversation_id)
    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only submit from your own conversations")

    if conversation.complaint_id:
        raise HTTPException(status_code=400, detail="Complaint already submitted from this conversation")

    # Submit complaint
    complaint = await service.submit_complaint_from_chat(
        conversation_id,
        preferred_language=payload.preferred_language,
        attachment_urls=payload.attachment_urls,
    )

    if not complaint:
        raise HTTPException(status_code=400, detail="Failed to submit complaint")

    return ComplaintFromChatResponse(
        complaint_id=complaint.id,
        conversation_id=conversation_id,
        reference_id=complaint.id[:8].upper(),
    )


@chat_router.post("/{conversation_id}/end")
async def end_chat(
    conversation_id: str,
    user: UserContext = Depends(get_user_context),
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    """End a chat conversation."""
    conversation = await service.get_conversation_history(conversation_id)
    
    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only end your own conversations")

    await service.end_conversation(conversation_id)

    return {
        "conversation_id": conversation_id,
        "message": "Chat ended successfully",
    }
