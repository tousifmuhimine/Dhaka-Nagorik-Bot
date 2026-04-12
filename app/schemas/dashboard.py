from pydantic import BaseModel, Field

from app.schemas.complaint import ComplaintRecord


class DashboardMetrics(BaseModel):
    average_resolution_hours: float
    pending_count: int
    completed_count: int
    delayed_count: int


class AuthorityDashboardResponse(BaseModel):
    assigned_thana: str
    metrics: DashboardMetrics
    complaints: list[ComplaintRecord] = Field(default_factory=list)


class AdminDashboardResponse(BaseModel):
    metrics: DashboardMetrics
    complaints: list[ComplaintRecord] = Field(default_factory=list)
    available_thanas: list[str] = Field(default_factory=list)
    available_categories: list[str] = Field(default_factory=list)
