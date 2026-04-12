from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from app.core.security import UserContext
from app.db.repository import get_complaint_repository
from app.models.enums import ComplaintStatus, UserRole
from app.schemas.complaint import ComplaintRecord
from app.schemas.dashboard import AdminDashboardResponse, AuthorityDashboardResponse, DashboardMetrics


class DashboardService:
    def __init__(self) -> None:
        self.repository = get_complaint_repository()

    async def get_authority_dashboard(self, user: UserContext) -> AuthorityDashboardResponse:
        if user.role != UserRole.authority:
            raise HTTPException(status_code=403, detail="Authority role required.")
        complaints = [ComplaintRecord.model_validate(item) for item in await self.repository.list_complaints()]
        scoped = [
            complaint for complaint in complaints
            if (user.assigned_thana and complaint.thana.lower() == user.assigned_thana.lower())
        ]
        return AuthorityDashboardResponse(
            assigned_thana=user.assigned_thana or "Unassigned",
            metrics=self._build_metrics(scoped),
            complaints=sorted(scoped, key=lambda item: item.created_at, reverse=True),
        )

    async def get_admin_dashboard(
        self,
        user: UserContext,
        *,
        thana: str | None,
        status: str | None,
        category: str | None,
        min_inconsistency: float | None,
        max_inconsistency: float | None,
        created_from: str | None,
        created_to: str | None,
    ) -> AdminDashboardResponse:
        if user.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="Admin role required.")
        complaints = [ComplaintRecord.model_validate(item) for item in await self.repository.list_complaints()]
        filtered = self._apply_filters(
            complaints,
            thana=thana,
            status=status,
            category=category,
            min_inconsistency=min_inconsistency,
            max_inconsistency=max_inconsistency,
            created_from=created_from,
            created_to=created_to,
        )
        return AdminDashboardResponse(
            metrics=self._build_metrics(filtered),
            complaints=sorted(filtered, key=lambda item: item.created_at, reverse=True),
            available_thanas=sorted({item.thana for item in complaints}),
            available_categories=sorted({item.category for item in complaints}),
        )

    @staticmethod
    def _apply_filters(
        complaints: list[ComplaintRecord],
        *,
        thana: str | None,
        status: str | None,
        category: str | None,
        min_inconsistency: float | None,
        max_inconsistency: float | None,
        created_from: str | None,
        created_to: str | None,
    ) -> list[ComplaintRecord]:
        start = datetime.fromisoformat(created_from) if created_from else None
        end = datetime.fromisoformat(created_to) if created_to else None
        output: list[ComplaintRecord] = []
        for complaint in complaints:
            if thana and complaint.thana.lower() != thana.lower():
                continue
            if status and complaint.status.lower() != status.lower():
                continue
            if category and complaint.category.lower() != category.lower():
                continue
            if min_inconsistency is not None and complaint.inconsistency_score < min_inconsistency:
                continue
            if max_inconsistency is not None and complaint.inconsistency_score > max_inconsistency:
                continue
            if start and complaint.created_at < start:
                continue
            if end and complaint.created_at > end:
                continue
            output.append(complaint)
        return output

    @staticmethod
    def _build_metrics(complaints: list[ComplaintRecord]) -> DashboardMetrics:
        resolved_durations: list[float] = []
        for complaint in complaints:
            if complaint.user_confirmed_at:
                hours = (complaint.user_confirmed_at - complaint.created_at).total_seconds() / 3600
                resolved_durations.append(hours)
        average_hours = round(sum(resolved_durations) / len(resolved_durations), 2) if resolved_durations else 0.0
        return DashboardMetrics(
            average_resolution_hours=average_hours,
            pending_count=sum(1 for item in complaints if item.status == ComplaintStatus.pending),
            completed_count=sum(1 for item in complaints if item.status in {ComplaintStatus.done, ComplaintStatus.resolved}),
            delayed_count=sum(1 for item in complaints if item.delayed),
        )


def get_dashboard_service() -> DashboardService:
    return DashboardService()
