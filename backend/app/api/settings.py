from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    default_timezone: Optional[str] = None
    environment: Optional[str] = None

@router.get("")
def get_application_settings():
    # Mask API key for security
    masked_key = None
    if settings.LLM_API_KEY:
        masked_key = f"{settings.LLM_API_KEY[:4]}••••••••{settings.LLM_API_KEY[-4:]}" if len(settings.LLM_API_KEY) > 8 else "••••••••"

    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "default_timezone": settings.DEFAULT_TIMEZONE,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "llm_api_key_configured": bool(settings.LLM_API_KEY),
        "llm_api_key_masked": masked_key,
        "mock_destination_default": "mock://employer.recruitment/v1/intake",
        "rules_engine_version": "2026.1-deterministic"
    }

@router.post("")
def update_application_settings(update_data: SettingsUpdateRequest):
    if update_data.llm_provider:
        settings.LLM_PROVIDER = update_data.llm_provider
    if update_data.llm_model:
        settings.LLM_MODEL = update_data.llm_model
    if update_data.llm_api_key:
        settings.LLM_API_KEY = update_data.llm_api_key
    if update_data.default_timezone:
        settings.DEFAULT_TIMEZONE = update_data.default_timezone
    if update_data.environment:
        settings.ENVIRONMENT = update_data.environment

    return {
        "status": "success",
        "message": "Settings updated successfully",
        "settings": get_application_settings()
    }
