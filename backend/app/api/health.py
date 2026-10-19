from fastapi import APIRouter, Depends
from sqlmodel import Session, select, text
from app.database import get_session
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(session: Session = Depends(get_session)):
    db_ok = False
    try:
        session.exec(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_connected": db_ok,
        "llm_provider": settings.LLM_PROVIDER
    }
