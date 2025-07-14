"""
User Session Management endpoints
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.token_service import TokenService

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SessionResponse(BaseModel):
    id: str
    device: str
    browser: str
    os: str
    ip_address: str
    location: str
    created_at: str
    last_used_at: str
    is_current: bool


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent string."""
    return request.headers.get("User-Agent", "unknown")


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: RefreshTokenRequest, http_request: Request, db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""

    try:
        token_service = TokenService(db)

        result = await token_service.refresh_token_pair(
            refresh_token=request.refresh_token,
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

        return TokenRefreshResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/active", response_model=List[SessionResponse])
async def get_active_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all active sessions for current user."""

    try:
        token_service = TokenService(db)
        sessions = await token_service.get_user_sessions(current_user.id)

        # Convert to response format
        result = []
        for session in sessions:
            result.append(
                SessionResponse(
                    id=session["id"],
                    device=session["device"],
                    browser=session["browser"],
                    os=session["os"],
                    ip_address=session["ip_address"],
                    location=session["location"],
                    created_at=session["created_at"].isoformat()
                    if session["created_at"]
                    else "",
                    last_used_at=session["last_used_at"].isoformat()
                    if session["last_used_at"]
                    else "",
                    is_current=session["is_current"],
                )
            )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter sessões ativas",
        )


@router.delete("/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific session."""

    try:
        # Find the refresh token for this session
        from app.models.user import RefreshToken

        token_record = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.id == session_id,
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_active == True,
            )
            .first()
        )

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada"
            )

        token_service = TokenService(db)
        success = await token_service.revoke_token(token_record.token)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao revogar sessão",
            )

        return {"message": "Sessão revogada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.delete("/all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Revoke all sessions for current user."""

    try:
        token_service = TokenService(db)
        success = await token_service.revoke_token(
            refresh_token="",  # Not used when revoking all
            user_id=current_user.id,
            revoke_all_user_tokens=True,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao revogar todas as sessões",
            )

        return {"message": "Todas as sessões foram revogadas com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/security-summary")
async def get_security_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get security summary for current user."""

    try:
        token_service = TokenService(db)
        sessions = await token_service.get_user_sessions(current_user.id)

        # Count sessions by device type
        device_counts = {}
        for session in sessions:
            device = session["device"]
            device_counts[device] = device_counts.get(device, 0) + 1

        # Get recent security events
        from datetime import datetime, timedelta

        from app.models.user import AuditLog

        recent_events = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == current_user.id,
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=7),
                AuditLog.resource_type.in_(["TOKEN", "SECURITY", "AUTH"]),
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
            .all()
        )

        security_events = []
        for event in recent_events:
            security_events.append(
                {
                    "action": event.action,
                    "timestamp": event.timestamp.isoformat(),
                    "ip_address": event.ip_address,
                    "status": event.status,
                    "details": event.details,
                }
            )

        return {
            "total_active_sessions": len(sessions),
            "device_breakdown": device_counts,
            "mfa_enabled": current_user.mfa_enabled,
            "last_login": current_user.last_login_at.isoformat()
            if current_user.last_login_at
            else None,
            "password_changed_at": current_user.password_changed_at.isoformat()
            if current_user.password_changed_at
            else None,
            "recent_security_events": security_events,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter resumo de segurança",
        )
