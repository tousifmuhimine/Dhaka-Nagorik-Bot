from fastapi import APIRouter, Depends, HTTPException, Query

from .chat_routes import chat_router
from app.core.security import UserContext, get_user_context
from app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintRecord,
    ComplaintStatusUpdateResponse,
    ResolutionDecisionRequest,
)
from app.schemas.dashboard import AdminDashboardResponse, AuthorityDashboardResponse
from app.services.auth_service import SupabaseAuthService
from app.services.complaint_service import ComplaintService, get_complaint_service
from app.services.dashboard_service import DashboardService, get_dashboard_service


api_router = APIRouter(prefix="/api")
api_router.include_router(chat_router)


@api_router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.post("/auth/signup", tags=["auth"])
async def sign_up(payload: dict) -> dict:
    return await SupabaseAuthService().sign_up(payload)


@api_router.post("/auth/login", tags=["auth"])
async def sign_in(payload: dict) -> dict:
    return await SupabaseAuthService().sign_in(payload)


@api_router.post("/complaints", response_model=ComplaintRecord, tags=["complaints"])
async def create_complaint(
    payload: ComplaintCreateRequest,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintRecord:
    return await service.create_complaint(payload, user)


@api_router.get("/complaints", response_model=list[ComplaintRecord], tags=["complaints"])
async def list_complaints(
    thana: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> list[ComplaintRecord]:
    return await service.list_visible_complaints(user, thana=thana, status=status, category=category)


@api_router.get("/complaints/{complaint_id}", response_model=ComplaintRecord, tags=["complaints"])
async def get_complaint(
    complaint_id: str,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintRecord:
    complaint = await service.get_visible_complaint(complaint_id, user)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint


@api_router.post("/complaints/{complaint_id}/acknowledge", response_model=ComplaintStatusUpdateResponse, tags=["complaints"])
async def acknowledge_complaint(
    complaint_id: str,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintStatusUpdateResponse:
    return await service.acknowledge_complaint(complaint_id, user)


@api_router.post("/complaints/{complaint_id}/progress", response_model=ComplaintStatusUpdateResponse, tags=["complaints"])
async def mark_in_progress(
    complaint_id: str,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintStatusUpdateResponse:
    return await service.mark_in_progress(complaint_id, user)


@api_router.post("/complaints/{complaint_id}/done", response_model=ComplaintStatusUpdateResponse, tags=["complaints"])
async def mark_done(
    complaint_id: str,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintStatusUpdateResponse:
    return await service.mark_done(complaint_id, user)


@api_router.post("/complaints/{complaint_id}/confirm", response_model=ComplaintStatusUpdateResponse, tags=["complaints"])
async def confirm_resolution(
    complaint_id: str,
    payload: ResolutionDecisionRequest,
    user: UserContext = Depends(get_user_context),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintStatusUpdateResponse:
    if payload.decision == "rejected":
        return await service.reject_resolution(complaint_id, user, payload.comment)
    return await service.confirm_resolution(complaint_id, user, payload.comment)


@api_router.get("/dashboard/authority", response_model=AuthorityDashboardResponse, tags=["dashboard"])
async def authority_dashboard(
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> AuthorityDashboardResponse:
    return await service.get_authority_dashboard(user)


@api_router.get("/dashboard/admin", response_model=AdminDashboardResponse, tags=["dashboard"])
async def admin_dashboard(
    thana: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    min_inconsistency: float | None = Query(default=None),
    max_inconsistency: float | None = Query(default=None),
    created_from: str | None = Query(default=None),
    created_to: str | None = Query(default=None),
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> AdminDashboardResponse:
    return await service.get_admin_dashboard(
        user,
        thana=thana,
        status=status,
        category=category,
        min_inconsistency=min_inconsistency,
        max_inconsistency=max_inconsistency,
        created_from=created_from,
        created_to=created_to,
    )
