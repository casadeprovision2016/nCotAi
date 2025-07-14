"""
Gov.br SSO Authentication endpoints
"""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.govbr_sso_service import GovBrSSOService

router = APIRouter()


# Pydantic models
class GovBrAuthInitRequest(BaseModel):
    redirect_url: str
    scopes: List[str] = ["openid", "profile", "email", "phone", "govbr_company"]


class GovBrCallbackRequest(BaseModel):
    code: str
    state: str


class GovBrSimulationRequest(BaseModel):
    cpf: str


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent string."""
    return request.headers.get("User-Agent", "unknown")


@router.get("/authorize")
async def initiate_govbr_auth(
    redirect_url: str = Query(
        ..., description="URL para redirecionamento após autenticação"
    ),
    scopes: str = Query(
        "openid profile email phone", description="Escopos OAuth2 separados por espaço"
    ),
):
    """Initiate Gov.br SSO authentication flow."""

    try:
        govbr_service = GovBrSSOService()

        # Parse scopes
        scope_list = scopes.split()

        # Generate authorization URL
        auth_url = govbr_service.get_authorization_url(
            state=redirect_url,  # Use redirect_url as state for simplicity
            scopes=scope_list,
        )

        return {"authorization_url": auth_url, "state": redirect_url}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar autenticação Gov.br: {str(e)}",
        )


@router.get("/simulate")
async def simulate_govbr_auth(
    simulation: str = Query(...),
    original_params: str = Query(...),
    cpf: str = Query(..., description="CPF para simulação"),
):
    """Simulate Gov.br authentication (development only)."""

    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint de simulação disponível apenas em desenvolvimento",
        )

    try:
        govbr_service = GovBrSSOService()

        # Parse original parameters
        params = json.loads(original_params)

        # Simulate authorization flow
        callback_url = govbr_service.simulate_authorization_flow(cpf, params)

        # Redirect to callback URL
        return RedirectResponse(url=callback_url, status_code=302)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na simulação Gov.br: {str(e)}",
        )


@router.post("/callback")
async def handle_govbr_callback(
    callback_data: GovBrCallbackRequest, request: Request, db: Session = Depends(get_db)
):
    """Handle Gov.br SSO callback."""

    try:
        govbr_service = GovBrSSOService()
        auth_service = AuthService(db)
        audit_service = AuditService(db)

        # Exchange authorization code for tokens
        token_response = await govbr_service.exchange_code_for_token(
            code=callback_data.code, redirect_uri=govbr_service.redirect_uri
        )

        # Get user info from Gov.br
        govbr_user = await govbr_service.get_user_info(token_response["access_token"])

        # Map Gov.br user to local user format
        local_user_data = govbr_service.map_govbr_user_to_local(govbr_user)

        # Check if user already exists
        existing_user = (
            db.query(User).filter(User.email == local_user_data["email"]).first()
        )

        if existing_user:
            # Update existing user with Gov.br data
            existing_user.first_name = local_user_data["first_name"]
            existing_user.last_name = local_user_data["last_name"]
            existing_user.phone = local_user_data["phone"]
            existing_user.avatar_url = local_user_data["avatar_url"]
            existing_user.is_verified = True
            existing_user.email_verified_at = (
                datetime.utcnow() if local_user_data["email_verified"] else None
            )

            db.commit()
            user = existing_user

            # Log Gov.br login
            await audit_service.log_user_action(
                user_id=user.id,
                action="GOVBR_LOGIN_EXISTING_USER",
                resource_type="AUTH",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                details={
                    "govbr_sub": govbr_user["sub"],
                    "cpf": govbr_user.get("cpf"),
                    "verification_level": local_user_data["verification_level"],
                },
            )

        else:
            # Create new user from Gov.br data
            from app.core.security import get_password_hash

            user = User(
                email=local_user_data["email"],
                hashed_password=get_password_hash(
                    "govbr_sso_user"
                ),  # Placeholder password
                first_name=local_user_data["first_name"],
                last_name=local_user_data["last_name"],
                phone=local_user_data["phone"],
                avatar_url=local_user_data["avatar_url"],
                role=UserRole.VIEWER,  # Default role for Gov.br users
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.utcnow()
                if local_user_data["email_verified"]
                else None,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            # Log new user creation
            await audit_service.log_user_action(
                user_id=user.id,
                action="GOVBR_USER_CREATED",
                resource_type="AUTH",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                details={
                    "govbr_sub": govbr_user["sub"],
                    "cpf": govbr_user.get("cpf"),
                    "verification_level": local_user_data["verification_level"],
                    "new_user": True,
                },
            )

        # Create access and refresh tokens for the user
        from app.services.token_service import TokenService

        token_service = TokenService(db)

        tokens = await token_service.create_token_pair(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            additional_claims={"govbr_verified": True, "govbr_sub": govbr_user["sub"]},
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "govbr_verified": True,
            },
            "redirect_url": callback_data.state,  # Original redirect URL
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no callback Gov.br: {str(e)}",
        )


@router.get("/simulated-users")
async def get_simulated_users():
    """Get list of simulated Gov.br users (development only)."""

    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint disponível apenas em desenvolvimento",
        )

    try:
        govbr_service = GovBrSSOService()
        users = govbr_service.get_simulated_users()

        return {
            "message": "Usuários simulados para teste Gov.br",
            "users": users,
            "instructions": "Use qualquer CPF da lista para simular login Gov.br",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter usuários simulados: {str(e)}",
        )


@router.post("/revoke")
async def revoke_govbr_session(access_token: str, db: Session = Depends(get_db)):
    """Revoke Gov.br SSO session."""

    try:
        govbr_service = GovBrSSOService()

        # Revoke Gov.br token
        success = await govbr_service.revoke_token(access_token)

        if success:
            # Log revocation
            audit_service = AuditService(db)
            await audit_service.log_user_action(
                user_id=None,  # Can't determine user without token validation
                action="GOVBR_TOKEN_REVOKED",
                resource_type="AUTH",
                details={"access_token_revoked": True},
            )

        return {
            "success": success,
            "message": "Token revogado com sucesso"
            if success
            else "Falha ao revogar token",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao revogar sessão Gov.br: {str(e)}",
        )


@router.get("/status")
async def get_govbr_status():
    """Get Gov.br integration status."""

    return {
        "integration_enabled": True,
        "environment": settings.ENVIRONMENT,
        "simulation_mode": settings.ENVIRONMENT == "development",
        "supported_scopes": ["openid", "profile", "email", "phone", "govbr_company"],
        "features": {
            "sso_login": True,
            "user_creation": True,
            "email_verification": True,
            "phone_verification": True,
            "government_verification": True,
        },
    }


@router.get("/user-info")
async def get_govbr_user_info(
    access_token: str = Query(..., description="Gov.br access token")
):
    """Get user information from Gov.br token."""

    try:
        govbr_service = GovBrSSOService()
        user_info = await govbr_service.get_user_info(access_token)

        # Remove sensitive information
        safe_user_info = {
            "sub": user_info["sub"],
            "name": user_info["name"],
            "email": user_info["email"],
            "email_verified": user_info.get("email_verified", False),
            "phone_verified": user_info.get("phone_number_verified", False),
            "government_verified": True,
            "updated_at": user_info.get("updated_at"),
        }

        return safe_user_info

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter informações do usuário: {str(e)}",
        )
