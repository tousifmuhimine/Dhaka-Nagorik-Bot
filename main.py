from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import get_settings


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI civic complaint automation system for Dhaka authorities and citizens.",
)
app.include_router(api_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running."}
