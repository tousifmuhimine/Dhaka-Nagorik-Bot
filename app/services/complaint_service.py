from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core.security import UserContext
from app.db.repository import ComplaintRepository, get_complaint_repository
from app.models.enums import ComplaintStatus, UserRole
from app.schemas.complaint import ComplaintCreateRequest, ComplaintRecord, ComplaintStatusUpdateResponse
from app.services.ai_processor import AIComplaintProcessor
from app.services.document_generator import DocumentGenerator
from app.services.policy_rag import PolicyRAGService


class ComplaintService:
    def __init__(self, repository: ComplaintRepository | None = None) -> None:
        self.repository = repository or ComplaintRepository()
        self.ai_processor = AIComplaintProcessor()
        self.policy_rag = PolicyRAGService()
        self.document_generator = DocumentGenerator()

    async def create_complaint(self, payload: ComplaintCreateRequest, user: UserContext) -> ComplaintRecord:
        if user.role != UserRole.citizen:
            raise HTTPException(status_code=403, detail="Only citizens can submit complaints.")
        created_at = datetime.utcnow()
        extracted = await self.ai_processor.extract(payload.complaint_text)
        policy = await self.policy_rag.evaluate(extracted, payload.complaint_text)
        complaint = ComplaintRecord(
            id=str(uuid4()),
            user_id=user.user_id,
            category=extracted.category,
            thana=extracted.thana,
            area=extracted.area,
            duration=extracted.duration,
            urgency=extracted.urgency,
            summary=extracted.summary,
            original_text=payload.complaint_text,
            preferred_language=payload.preferred_language or "bn",
            attachment_urls=payload.attachment_urls,
            status=ComplaintStatus.pending,
            compliance_status=policy.compliance_status,
            inconsistency_score=policy.inconsistency_score,
            delayed=policy.delayed,
            matched_policy_sections=policy.matched_policy_sections,
            created_at=created_at,
            updated_at=created_at,
        )
        pdf_path, docx_path = await self.document_generator.generate_submission_documents(complaint)
        complaint.document_pdf_path = pdf_path
        complaint.document_docx_path = docx_path
        stored = await self.repository.create_complaint(complaint.model_dump(mode="json"))
        return ComplaintRecord.model_validate(stored)

    async def list_visible_complaints(
        self,
        user: UserContext,
        *,
        thana: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[ComplaintRecord]:
        records = [ComplaintRecord.model_validate(item) for item in await self.repository.list_complaints()]
        filtered = []
        for record in records:
            if user.role == UserRole.citizen and record.user_id != user.user_id:
                continue
            if user.role == UserRole.authority and user.assigned_thana and record.thana.lower() != user.assigned_thana.lower():
                continue
            if thana and record.thana.lower() != thana.lower():
                continue
            if status and record.status.lower() != status.lower():
                continue
            if category and record.category.lower() != category.lower():
                continue
            filtered.append(record)
        return sorted(filtered, key=lambda item: item.created_at, reverse=True)

    async def get_visible_complaint(self, complaint_id: str, user: UserContext) -> ComplaintRecord | None:
        complaint = await self.repository.get_complaint(complaint_id)
        if not complaint:
            return None
        record = ComplaintRecord.model_validate(complaint)
        if user.role == UserRole.citizen and record.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="You can only view your own complaints.")
        if user.role == UserRole.authority and user.assigned_thana and record.thana.lower() != user.assigned_thana.lower():
            raise HTTPException(status_code=403, detail="Complaint belongs to a different thana.")
        return record

    async def acknowledge_complaint(self, complaint_id: str, user: UserContext) -> ComplaintStatusUpdateResponse:
        complaint = await self._require_authority_scope(complaint_id, user)
        acknowledged_at = complaint.acknowledged_at or datetime.utcnow()
        updated = await self.repository.update_complaint(
            complaint_id,
            {
                "status": ComplaintStatus.acknowledged,
                "acknowledged_at": acknowledged_at.isoformat(),
            },
        )
        return ComplaintStatusUpdateResponse.model_validate({"complaint_id": complaint_id, **updated})

    async def mark_in_progress(self, complaint_id: str, user: UserContext) -> ComplaintStatusUpdateResponse:
        await self._require_authority_scope(complaint_id, user)
        updated = await self.repository.update_complaint(complaint_id, {"status": ComplaintStatus.in_progress})
        return ComplaintStatusUpdateResponse.model_validate({"complaint_id": complaint_id, **updated})

    async def mark_done(self, complaint_id: str, user: UserContext) -> ComplaintStatusUpdateResponse:
        await self._require_authority_scope(complaint_id, user)
        completed_at = datetime.utcnow()
        updated = await self.repository.update_complaint(
            complaint_id,
            {
                "status": ComplaintStatus.done,
                "completed_at": completed_at.isoformat(),
            },
        )
        return ComplaintStatusUpdateResponse.model_validate({"complaint_id": complaint_id, **updated})

    async def confirm_resolution(self, complaint_id: str, user: UserContext, comment: str | None = None) -> ComplaintStatusUpdateResponse:
        complaint = await self._require_citizen_owner(complaint_id, user)
        if complaint.status != ComplaintStatus.done:
            raise HTTPException(status_code=400, detail="Only completed complaints can be confirmed.")
        confirmed_at = datetime.utcnow()
        updated = await self.repository.update_complaint(
            complaint_id,
            {
                "status": ComplaintStatus.resolved,
                "user_confirmed_at": confirmed_at.isoformat(),
                "resolution_comment": comment,
            },
        )
        return ComplaintStatusUpdateResponse.model_validate({"complaint_id": complaint_id, **updated})

    async def reject_resolution(self, complaint_id: str, user: UserContext, comment: str | None = None) -> ComplaintStatusUpdateResponse:
        complaint = await self._require_citizen_owner(complaint_id, user)
        if complaint.status != ComplaintStatus.done:
            raise HTTPException(status_code=400, detail="Only completed complaints can be rejected.")
        updated = await self.repository.update_complaint(
            complaint_id,
            {
                "status": ComplaintStatus.rejected,
                "resolution_comment": comment,
            },
        )
        return ComplaintStatusUpdateResponse.model_validate({"complaint_id": complaint_id, **updated})

    async def _require_authority_scope(self, complaint_id: str, user: UserContext) -> ComplaintRecord:
        if user.role not in {UserRole.authority, UserRole.admin}:
            raise HTTPException(status_code=403, detail="Authority access required.")
        complaint = await self.get_visible_complaint(complaint_id, user)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        return complaint

    async def _require_citizen_owner(self, complaint_id: str, user: UserContext) -> ComplaintRecord:
        if user.role != UserRole.citizen:
            raise HTTPException(status_code=403, detail="Citizen access required.")
        complaint = await self.get_visible_complaint(complaint_id, user)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        return complaint


def get_complaint_service() -> ComplaintService:
    return ComplaintService(get_complaint_repository())
