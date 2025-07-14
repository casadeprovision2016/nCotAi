"""
COTAI Backend API
Sistema de Automação para Cotações e Editais
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.middleware import MonitoringMiddleware

# Setup logging
setup_logging()
logger = get_logger("app.main")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    logger.info("Creating FastAPI application")

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Sistema avançado de automação para gerenciamento de cotações e editais",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add monitoring middleware first
    app.add_middleware(MonitoringMiddleware)

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        return {
            "message": "COTAI API",
            "version": settings.VERSION,
            "docs": "/docs",
            "status": "running",
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_application()
