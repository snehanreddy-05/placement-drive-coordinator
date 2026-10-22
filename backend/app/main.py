from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import health, dashboard, students, drives, eligibility, clashes, approvals, uploads, attendance, agent, audit, settings as settings_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="PlacementOS - Placement Drive Coordinator API",
    lifespan=lifespan
)

# CORS configuration
# Parse the comma-separated ALLOWED_ORIGINS setting and always guarantee
# the production Vercel frontend origin is present.
PRODUCTION_ORIGIN = "https://placement-drive-coordinator-olive.vercel.app"
origins: list[str] = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if PRODUCTION_ORIGIN not in origins:
    origins.append(PRODUCTION_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

# Mount API routers
app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(drives.router, prefix="/api")
app.include_router(eligibility.router, prefix="/api")
app.include_router(clashes.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs"
    }
