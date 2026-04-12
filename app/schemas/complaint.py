from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ComplaintStatus


class ComplaintCreateRequest(BaseModel):
    complaint_text: str = Field(..., min_length=10)
    preferred_language: Literal["bn", "en"] | None = "bn"
    attachment_urls: list[str] = Field(default_factory=list)


class ComplaintExtraction(BaseModel):
    category: str
    thana: str
    area: str
    duration: str
    urgency: str
    summary: str


class PolicyAssessment(BaseModel):
    compliance_status: str
    inconsistency_score: float
    matched_policy_sections: list[str] = Field(default_factory=list)
    delayed: bool = False


class ComplaintRecord(BaseModel):
    id: str
    user_id: str
    category: str
    thana: str
    area: str
    duration: str
    urgency: str
    summary: str
    original_text: str
    preferred_language: str
    attachment_urls: list[str] = Field(default_factory=list)
    status: ComplaintStatus
    compliance_status: str
    inconsistency_score: float
    delayed: bool = False
    matched_policy_sections: list[str] = Field(default_factory=list)
    document_pdf_path: str | None = None
    document_docx_path: str | None = None
    created_at: datetime
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None
    user_confirmed_at: datetime | None = None
    updated_at: datetime | None = None
    resolution_comment: str | None = None


class ComplaintStatusUpdateResponse(BaseModel):
    complaint_id: str
    status: ComplaintStatus
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None
    user_confirmed_at: datetime | None = None
    resolution_comment: str | None = None


class ResolutionDecisionRequest(BaseModel):
    decision: Literal["confirmed", "rejected"]
    comment: str | None = None
