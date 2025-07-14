"""
User management endpoints
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import (
    get_current_superuser,
    get_current_user,
    get_current_verified_user,
    require_admin,
    require_user_read,
    require_user_update,
)
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.user import (
    AuditLogListResponse,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    UserAdminUpdate,
    UserListResponse,
    UserProfile,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        phone=current_user.phone,
        company=current_user.company,
        position=current_user.position,
        department=current_user.department,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        mfa_enabled=current_user.mfa_enabled,
        timezone=current_user.timezone,
        language=current_user.language,
        theme=current_user.theme,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user(
            user_id=current_user.id, user_update=user_update, updated_by=current_user.id
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    current_user: User = Depends(require_user_read),
    db: Session = Depends(get_db),
):
    """Get users list with filtering and pagination."""
    try:
        user_service = UserService(db)
        users, total = user_service.get_users(
            skip=skip,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active,
            is_verified=is_verified,
        )

        pages = (total + limit - 1) // limit

        return UserListResponse(
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages,
            items=[UserResponse.from_orm(user) for user in users],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_user_read),
    db: Session = Depends(get_db),
):
    """Get user by ID."""
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        return UserProfile.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserAdminUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (admin only)."""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user_admin(
            user_id=user_id, user_update=user_update, updated_by=current_user.id
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Deactivate user account."""
    try:
        user_service = UserService(db)
        result = user_service.deactivate_user(
            user_id=user_id, deactivated_by=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/{user_id}/reactivate")
async def reactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reactivate user account."""
    try:
        user_service = UserService(db)
        result = user_service.reactivate_user(
            user_id=user_id, reactivated_by=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Delete user account (superuser only)."""
    try:
        user_service = UserService(db)
        result = user_service.delete_user(user_id=user_id, deleted_by=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/stats/overview")
async def get_user_stats(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Get user statistics (admin only)."""
    try:
        user_service = UserService(db)
        stats = user_service.get_user_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


# Permission management endpoints
@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Create permission (superuser only)."""
    try:
        user_service = UserService(db)
        permission = user_service.create_permission(
            permission_data=permission_data, created_by=current_user.id
        )
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/permissions")
async def get_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get permissions list."""
    try:
        user_service = UserService(db)
        permissions, total = user_service.get_permissions(
            skip=skip,
            limit=limit,
            resource_type=resource_type,
            action=action,
            is_active=is_active,
        )

        pages = (total + limit - 1) // limit

        return {
            "total": total,
            "page": (skip // limit) + 1,
            "size": limit,
            "pages": pages,
            "items": [PermissionResponse.from_orm(perm) for perm in permissions],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: UUID,
    permission_update: PermissionUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Update permission (superuser only)."""
    try:
        user_service = UserService(db)
        permission = user_service.update_permission(
            permission_id=permission_id, permission_update=permission_update
        )
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: UUID,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Delete permission (superuser only)."""
    try:
        user_service = UserService(db)
        result = user_service.delete_permission(permission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.post("/{user_id}/permissions/{permission_id}")
async def assign_permission_to_user(
    user_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assign permission to user."""
    try:
        user_service = UserService(db)
        result = user_service.assign_permission_to_user(
            user_id=user_id, permission_id=permission_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.delete("/{user_id}/permissions/{permission_id}")
async def remove_permission_from_user(
    user_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove permission from user."""
    try:
        user_service = UserService(db)
        result = user_service.remove_permission_from_user(
            user_id=user_id, permission_id=permission_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@router.get("/{user_id}/audit-logs", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get user audit logs."""
    try:
        user_service = UserService(db)
        logs, total = user_service.get_user_audit_logs(
            user_id=user_id, skip=skip, limit=limit, action=action
        )

        pages = (total + limit - 1) // limit

        return AuditLogListResponse(
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            pages=pages,
            items=[log for log in logs],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )
