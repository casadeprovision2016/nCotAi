"""
Authentication and authorization middleware and dependencies
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db.dependencies import get_db
from app.models.user import PermissionAction, ResourceType, User, UserRole
from app.services.user_service import UserService

security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error."""

    def __init__(self, detail: str = "Não autenticado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""

    def __init__(self, detail: str = "Permissão negada"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user."""

    # Verify token
    payload = verify_token(credentials.credentials, "access")
    if not payload:
        raise AuthenticationError("Token inválido ou expirado")

    # Extract user ID
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token inválido")

    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(UUID(user_id))

    if not user:
        raise AuthenticationError("Usuário não encontrado")

    if not user.is_active:
        raise AuthenticationError("Conta desativada")

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated and verified user."""

    if not current_user.is_verified:
        raise AuthenticationError("Email não verificado")

    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_verified_user),
) -> User:
    """Get current superuser."""

    if not current_user.is_superuser:
        raise AuthorizationError(
            "Acesso negado - privilégios de superusuário necessários"
        )

    return current_user


class RoleChecker:
    """Role-based access control checker."""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_verified_user)) -> User:
        if current_user.is_superuser:
            return current_user

        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                f"Acesso negado - Função necessária: {', '.join([role.value for role in self.allowed_roles])}"
            )

        return current_user


class PermissionChecker:
    """Permission-based access control checker."""

    def __init__(self, resource_type: ResourceType, action: PermissionAction):
        self.resource_type = resource_type
        self.action = action

    def __call__(self, current_user: User = Depends(get_current_verified_user)) -> User:
        if not current_user.has_permission(self.resource_type, self.action):
            raise AuthorizationError(
                f"Acesso negado - Permissão necessária: {self.action.value} em {self.resource_type.value}"
            )

        return current_user


class ResourceOwnerChecker:
    """Resource ownership checker."""

    def __init__(self, get_resource_owner_id):
        self.get_resource_owner_id = get_resource_owner_id

    def __call__(
        self,
        current_user: User = Depends(get_current_verified_user),
        db: Session = Depends(get_db),
    ) -> User:
        resource_owner_id = self.get_resource_owner_id(db)

        # Superuser and admin can access any resource
        if current_user.is_superuser or current_user.role == UserRole.ADMIN:
            return current_user

        # Resource owner can access their own resource
        if str(current_user.id) == str(resource_owner_id):
            return current_user

        raise AuthorizationError(
            "Acesso negado - Você só pode acessar seus próprios recursos"
        )


# Convenience role checkers
require_admin = RoleChecker([UserRole.ADMIN, UserRole.SUPER_ADMIN])
require_manager = RoleChecker([UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
require_operator = RoleChecker(
    [UserRole.OPERATOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
)

# Convenience permission checkers
require_user_create = PermissionChecker(ResourceType.USER, PermissionAction.CREATE)
require_user_read = PermissionChecker(ResourceType.USER, PermissionAction.READ)
require_user_update = PermissionChecker(ResourceType.USER, PermissionAction.UPDATE)
require_user_delete = PermissionChecker(ResourceType.USER, PermissionAction.DELETE)

require_tender_create = PermissionChecker(ResourceType.TENDER, PermissionAction.CREATE)
require_tender_read = PermissionChecker(ResourceType.TENDER, PermissionAction.READ)
require_tender_update = PermissionChecker(ResourceType.TENDER, PermissionAction.UPDATE)
require_tender_delete = PermissionChecker(ResourceType.TENDER, PermissionAction.DELETE)

require_document_create = PermissionChecker(
    ResourceType.DOCUMENT, PermissionAction.CREATE
)
require_document_read = PermissionChecker(ResourceType.DOCUMENT, PermissionAction.READ)
require_document_update = PermissionChecker(
    ResourceType.DOCUMENT, PermissionAction.UPDATE
)
require_document_delete = PermissionChecker(
    ResourceType.DOCUMENT, PermissionAction.DELETE
)

require_task_create = PermissionChecker(ResourceType.TASK, PermissionAction.CREATE)
require_task_read = PermissionChecker(ResourceType.TASK, PermissionAction.READ)
require_task_update = PermissionChecker(ResourceType.TASK, PermissionAction.UPDATE)
require_task_delete = PermissionChecker(ResourceType.TASK, PermissionAction.DELETE)

require_message_create = PermissionChecker(
    ResourceType.MESSAGE, PermissionAction.CREATE
)
require_message_read = PermissionChecker(ResourceType.MESSAGE, PermissionAction.READ)
require_message_update = PermissionChecker(
    ResourceType.MESSAGE, PermissionAction.UPDATE
)

require_report_read = PermissionChecker(ResourceType.REPORT, PermissionAction.READ)
require_report_create = PermissionChecker(ResourceType.REPORT, PermissionAction.CREATE)

require_system_admin = PermissionChecker(ResourceType.SYSTEM, PermissionAction.ADMIN)


def get_optional_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""

    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ")[1]

        # Verify token
        payload = verify_token(token, "access")
        if not payload:
            return None

        # Get user
        user_id = payload.get("sub")
        if not user_id:
            return None

        user_service = UserService(db)
        user = user_service.get_user_by_id(UUID(user_id))

        if not user or not user.is_active:
            return None

        return user
    except Exception:
        return None


async def audit_request(
    request: Request, current_user: Optional[User] = None, db: Session = Depends(get_db)
):
    """Audit API request."""

    # This would typically log the request for security monitoring
    # For now, we'll implement a basic version
    try:
        from app.models.user import AuditLog

        audit_log = AuditLog(
            user_id=current_user.id if current_user else None,
            action=f"{request.method}:{request.url.path}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            request_path=str(request.url.path),
            request_method=request.method,
            status="SUCCESS",  # This would be updated based on response
        )

        db.add(audit_log)
        db.commit()
    except Exception:
        # Don't fail the request if audit logging fails
        pass


class IPWhitelistChecker:
    """IP whitelist checker for sensitive operations."""

    def __init__(self, allowed_ips: list[str] = None):
        self.allowed_ips = allowed_ips or []

    def __call__(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"

        # If no whitelist is configured, allow all IPs
        if not self.allowed_ips:
            return client_ip

        # Check if IP is in whitelist
        if client_ip not in self.allowed_ips:
            raise AuthorizationError(f"Acesso negado para IP: {client_ip}")

        return client_ip


class RateLimitChecker:
    """Rate limiting checker."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def __call__(
        self,
        request: Request,
        current_user: Optional[User] = Depends(get_optional_current_user),
    ):
        # Rate limiting logic would go here
        # For now, this is a placeholder
        # In production, you would use Redis or another store to track request counts
        pass


def create_access_token_for_user(user: User) -> Dict[str, Any]:
    """Create access token for user with proper claims."""
    from datetime import timedelta

    from app.core.config import settings
    from app.core.security import create_access_token

    additional_claims = {
        "role": user.role.value,
        "verified": user.is_verified,
        "mfa": user.mfa_enabled,
        "email": user.email,
    }

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        additional_claims=additional_claims,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "is_verified": user.is_verified,
            "mfa_enabled": user.mfa_enabled,
        },
    }
