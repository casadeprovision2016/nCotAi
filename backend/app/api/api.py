"""
Main API router
"""

from fastapi import APIRouter

from app.api.endpoints import (
    audit,
    auth,
    cloud_storage,
    files,
    govbr_auth,
    government_apis,
    health,
    mfa,
    pncp,
    quotations,
    rbac,
    # reports,  # Temporarily disabled due to missing dependencies
    sessions,
    team_notifications,
    tenders,
    users,
    websocket,
    # whatsapp,  # Temporarily disabled due to module path issues
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
api_router.include_router(quotations.router, prefix="/quotations", tags=["quotations"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(pncp.router, prefix="/pncp", tags=["pncp"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
# api_router.include_router(reports.router, prefix="/reports", tags=["reports"])  # Temporarily disabled
api_router.include_router(mfa.router, prefix="/mfa", tags=["mfa"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(govbr_auth.router, prefix="/auth/govbr", tags=["govbr-sso"])
api_router.include_router(rbac.router, prefix="/rbac", tags=["rbac"])
api_router.include_router(
    government_apis.router, prefix="/government", tags=["government-apis"]
)
# api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])  # Temporarily disabled
api_router.include_router(
    cloud_storage.router, prefix="/cloud-storage", tags=["cloud-storage"]
)
api_router.include_router(
    team_notifications.router, prefix="/team-notifications", tags=["team-notifications"]
)
