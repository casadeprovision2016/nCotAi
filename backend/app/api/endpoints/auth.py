"""
Authentication endpoints
"""

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.schemas.user import (
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    MFALoginRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserCreate,
)
from app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()

# Redis client for rate limiting (in production, inject this properly)
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
except:
    redis_client = None


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent string."""
    return request.headers.get("User-Agent", "unknown")


@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate, request: Request, db: Session = Depends(get_db)
):
    """User registration endpoint."""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.register_user(
            user_data=user_data,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """User login endpoint."""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.authenticate_user(
            login_data=login_data,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        # Check if MFA is required
        if result.get("requires_mfa"):
            raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=result)

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/login/mfa", response_model=LoginResponse)
async def login_with_mfa(
    mfa_login_data: MFALoginRequest, request: Request, db: Session = Depends(get_db)
):
    """Login with MFA code."""
    try:
        auth_service = AuthService(db, redis_client)

        # First authenticate without MFA to get user ID
        login_data = LoginRequest(
            email=mfa_login_data.email,
            password=mfa_login_data.password,
            remember_me=mfa_login_data.remember_me,
        )

        result = await auth_service.authenticate_user(
            login_data=login_data,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        if not result.get("requires_mfa"):
            return result

        # Complete MFA authentication
        final_result = await auth_service.authenticate_with_mfa(
            user_id=result["user_id"],
            mfa_code=mfa_login_data.mfa_code,
            login_data=login_data,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        return final_result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)
):
    """Token refresh endpoint."""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/logout")
async def logout(
    refresh_data: RefreshTokenRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """User logout endpoint."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        auth_service = AuthService(db, redis_client)
        result = await auth_service.logout_user(
            refresh_token=refresh_data.refresh_token,
            user_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/logout/all")
async def logout_all_devices(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Logout from all devices."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        auth_service = AuthService(db, redis_client)
        result = await auth_service.logout_all_devices(
            user_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/password/change")
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Change user password."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        from app.services.user_service import UserService

        user_service = UserService(db)
        result = user_service.change_password(
            user_id=user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/password/reset/request")
async def request_password_reset(
    reset_data: PasswordResetRequest, db: Session = Depends(get_db)
):
    """Request password reset."""
    try:
        from app.services.user_service import UserService

        user_service = UserService(db)
        result = user_service.reset_password_request(reset_data.email)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm, db: Session = Depends(get_db)
):
    """Confirm password reset."""
    try:
        from app.services.user_service import UserService

        user_service = UserService(db)
        result = user_service.reset_password_confirm(
            token=reset_data.token, new_password=reset_data.new_password
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/email/verify")
async def verify_email(
    verification_data: EmailVerificationRequest, db: Session = Depends(get_db)
):
    """Verify user email."""
    try:
        from app.services.user_service import UserService

        user_service = UserService(db)
        result = user_service.verify_email(verification_data.token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/email/resend-verification")
async def resend_verification_email(
    email_data: PasswordResetRequest,  # Reuse schema as it only has email
    db: Session = Depends(get_db),
):
    """Resend email verification."""
    try:
        from app.services.user_service import UserService

        user_service = UserService(db)
        result = user_service.resend_verification_email(email_data.email)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


# MFA endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    mfa_data: MFASetupRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Setup MFA for user."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        auth_service = AuthService(db, redis_client)
        result = await auth_service.setup_mfa(
            user_id=user_id,
            password=mfa_data.password,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/mfa/verify")
async def verify_mfa_setup(
    mfa_data: MFAVerifyRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Verify and enable MFA."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        auth_service = AuthService(db, redis_client)
        result = await auth_service.verify_and_enable_mfa(
            user_id=user_id,
            verification_code=mfa_data.code,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/mfa/disable")
async def disable_mfa(
    mfa_data: MFALoginRequest,  # Reuse schema with email, password, mfa_code
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Disable MFA for user."""
    try:
        # Extract user ID from access token
        from app.core.security import verify_token

        payload = verify_token(credentials.credentials, "access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )

        user_id = payload.get("sub")

        auth_service = AuthService(db, redis_client)
        result = await auth_service.disable_mfa(
            user_id=user_id,
            password=mfa_data.password,
            mfa_code=mfa_data.mfa_code,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )
