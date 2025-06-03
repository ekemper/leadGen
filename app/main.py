from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import jobs, health, campaigns, organizations, auth, queue_management
from app.api.endpoints import leads
from app.core.config import settings
from app.core.middleware import AuthenticationMiddleware

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)

    # Include routers
    app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
    app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])
    app.include_router(campaigns.router, prefix=f"{settings.API_V1_STR}/campaigns", tags=["campaigns"])
    app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
    app.include_router(leads.router, prefix=f"{settings.API_V1_STR}/leads", tags=["leads"])
    app.include_router(queue_management.router, prefix=f"{settings.API_V1_STR}/queue-management", tags=["queue-management"])

    return app

app = create_application()