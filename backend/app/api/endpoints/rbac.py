"""
Role-Based Access Control (RBAC) Management endpoints
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.auth import get_current_user
from app.models.user import Permission, PermissionAction, ResourceType, User, UserRole
from app.services.audit_service import AuditService

router = APIRouter()


# Pydantic models
class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    resource_type: ResourceType
    action: PermissionAction
    conditions: Optional[Dict[str, Any]] = None


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PermissionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    resource_type: ResourceType
    action: PermissionAction
    conditions: Optional[Dict[str, Any]]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserPermissionAssign(BaseModel):
    permission_ids: List[str]


class RolePermissionsResponse(BaseModel):
    role: UserRole
    permissions: List[str]
    description: str


def check_admin_access(current_user: User = Depends(get_current_user)):
    """Check if user has admin access for RBAC management."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar permissões.",
        )
    return current_user


def check_super_admin_access(current_user: User = Depends(get_current_user)):
    """Check if user has super admin access for system-level operations."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas super administradores podem realizar esta operação.",
        )
    return current_user


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource_type: Optional[ResourceType] = Query(None),
    action: Optional[PermissionAction] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """List all available permissions with filtering."""

    try:
        query = db.query(Permission)

        if resource_type:
            query = query.filter(Permission.resource_type == resource_type)

        if action:
            query = query.filter(Permission.action == action)

        if is_active is not None:
            query = query.filter(Permission.is_active == is_active)

        permissions = query.order_by(Permission.resource_type, Permission.action).all()

        return [
            PermissionResponse(
                id=str(perm.id),
                name=perm.name,
                description=perm.description,
                resource_type=perm.resource_type,
                action=perm.action,
                conditions=perm.conditions,
                is_active=perm.is_active,
                created_at=perm.created_at.isoformat(),
            )
            for perm in permissions
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar permissões",
        )


@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    """Create a new permission."""

    try:
        # Check if permission already exists
        existing = (
            db.query(Permission)
            .filter(
                Permission.resource_type == permission_data.resource_type,
                Permission.action == permission_data.action,
                Permission.name == permission_data.name,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Permissão já existe"
            )

        # Create new permission
        permission = Permission(
            name=permission_data.name,
            description=permission_data.description,
            resource_type=permission_data.resource_type,
            action=permission_data.action,
            conditions=permission_data.conditions,
            created_by=current_user.id,
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)

        # Log creation
        audit_service = AuditService(db)
        await audit_service.log_user_action(
            user_id=current_user.id,
            action="PERMISSION_CREATED",
            resource_type="PERMISSION",
            resource_id=str(permission.id),
            details={
                "permission_name": permission.name,
                "resource_type": permission.resource_type.value,
                "action": permission.action.value,
            },
        )

        return PermissionResponse(
            id=str(permission.id),
            name=permission.name,
            description=permission.description,
            resource_type=permission.resource_type,
            action=permission.action,
            conditions=permission.conditions,
            is_active=permission.is_active,
            created_at=permission.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar permissão",
        )


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: str,
    permission_data: PermissionUpdate,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    """Update an existing permission."""

    try:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Permissão não encontrada"
            )

        # Update fields
        if permission_data.name is not None:
            permission.name = permission_data.name

        if permission_data.description is not None:
            permission.description = permission_data.description

        if permission_data.conditions is not None:
            permission.conditions = permission_data.conditions

        if permission_data.is_active is not None:
            permission.is_active = permission_data.is_active

        db.commit()
        db.refresh(permission)

        # Log update
        audit_service = AuditService(db)
        await audit_service.log_user_action(
            user_id=current_user.id,
            action="PERMISSION_UPDATED",
            resource_type="PERMISSION",
            resource_id=str(permission.id),
            details={
                "permission_name": permission.name,
                "updated_fields": permission_data.dict(exclude_unset=True),
            },
        )

        return PermissionResponse(
            id=str(permission.id),
            name=permission.name,
            description=permission.description,
            resource_type=permission.resource_type,
            action=permission.action,
            conditions=permission.conditions,
            is_active=permission.is_active,
            created_at=permission.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar permissão",
        )


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: str,
    current_user: User = Depends(check_super_admin_access),
    db: Session = Depends(get_db),
):
    """Delete a permission."""

    try:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Permissão não encontrada"
            )

        # Check if permission is in use
        users_with_permission = (
            db.query(User).filter(User.permissions.contains(permission)).count()
        )

        if users_with_permission > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permissão está sendo usada por {users_with_permission} usuário(s)",
            )

        permission_name = permission.name
        db.delete(permission)
        db.commit()

        # Log deletion
        audit_service = AuditService(db)
        await audit_service.log_user_action(
            user_id=current_user.id,
            action="PERMISSION_DELETED",
            resource_type="PERMISSION",
            resource_id=permission_id,
            details={"permission_name": permission_name},
        )

        return {"message": "Permissão excluída com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao excluir permissão",
        )


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get all permissions for a specific user."""

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        # Get explicit permissions
        explicit_permissions = [
            {
                "id": str(perm.id),
                "name": perm.name,
                "resource_type": perm.resource_type.value,
                "action": perm.action.value,
                "source": "explicit",
            }
            for perm in user.permissions
            if perm.is_active
        ]

        # Get role-based permissions (simplified)
        role_permissions = []
        if user.role:
            # This would be more sophisticated in practice
            role_permission_map = {
                UserRole.SUPER_ADMIN: ["*:*"],
                UserRole.ADMIN: ["user:read", "user:write", "tender:*", "report:*"],
                UserRole.MANAGER: ["tender:read", "tender:write", "report:read"],
                UserRole.OPERATOR: ["tender:read", "quotation:*"],
                UserRole.VIEWER: ["tender:read", "quotation:read"],
            }

            for perm_string in role_permission_map.get(user.role, []):
                resource, action = perm_string.split(":")
                role_permissions.append(
                    {"resource_type": resource, "action": action, "source": "role"}
                )

        return {
            "user_id": user_id,
            "user_name": user.full_name,
            "role": user.role.value,
            "explicit_permissions": explicit_permissions,
            "role_permissions": role_permissions,
            "total_permissions": len(explicit_permissions) + len(role_permissions),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter permissões do usuário",
        )


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Update user role."""

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        # Check permissions for role assignment
        if current_user.role == UserRole.ADMIN and role_data.role in [
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administradores não podem atribuir papéis administrativos",
            )

        old_role = user.role
        user.role = role_data.role
        db.commit()

        # Log role change
        audit_service = AuditService(db)
        await audit_service.log_user_action(
            user_id=current_user.id,
            action="USER_ROLE_CHANGED",
            resource_type="USER",
            resource_id=user_id,
            details={
                "target_user": user.full_name,
                "old_role": old_role.value,
                "new_role": role_data.role.value,
            },
        )

        return {
            "message": "Papel do usuário atualizado com sucesso",
            "user_id": user_id,
            "old_role": old_role.value,
            "new_role": role_data.role.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar papel do usuário",
        )


@router.put("/users/{user_id}/permissions")
async def assign_user_permissions(
    user_id: str,
    permission_data: UserPermissionAssign,
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Assign explicit permissions to user."""

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
            )

        # Get permissions
        permissions = (
            db.query(Permission)
            .filter(
                Permission.id.in_(permission_data.permission_ids),
                Permission.is_active == True,
            )
            .all()
        )

        if len(permissions) != len(permission_data.permission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uma ou mais permissões não foram encontradas",
            )

        # Assign permissions
        user.permissions = permissions
        db.commit()

        # Log permission assignment
        audit_service = AuditService(db)
        await audit_service.log_user_action(
            user_id=current_user.id,
            action="USER_PERMISSIONS_ASSIGNED",
            resource_type="USER",
            resource_id=user_id,
            details={
                "target_user": user.full_name,
                "permissions_assigned": [perm.name for perm in permissions],
                "permission_count": len(permissions),
            },
        )

        return {
            "message": "Permissões atribuídas com sucesso",
            "user_id": user_id,
            "assigned_permissions": [
                {
                    "id": str(perm.id),
                    "name": perm.name,
                    "resource_type": perm.resource_type.value,
                    "action": perm.action.value,
                }
                for perm in permissions
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atribuir permissões",
        )


@router.get("/roles", response_model=List[RolePermissionsResponse])
async def list_roles(current_user: User = Depends(check_admin_access)):
    """List all available roles with their default permissions."""

    roles_info = [
        RolePermissionsResponse(
            role=UserRole.SUPER_ADMIN,
            permissions=["*:*"],
            description="Acesso total ao sistema, incluindo gerenciamento de usuários e configurações",
        ),
        RolePermissionsResponse(
            role=UserRole.ADMIN,
            permissions=[
                "user:read",
                "user:write",
                "tender:create",
                "tender:read",
                "tender:update",
                "tender:delete",
                "document:create",
                "document:read",
                "document:update",
                "document:delete",
                "report:read",
                "report:create",
            ],
            description="Administrador com acesso a gestão de usuários e licitações",
        ),
        RolePermissionsResponse(
            role=UserRole.MANAGER,
            permissions=[
                "tender:create",
                "tender:read",
                "tender:update",
                "document:create",
                "document:read",
                "document:update",
                "task:create",
                "task:read",
                "task:update",
                "report:read",
                "report:create",
            ],
            description="Gerente com acesso a criação e edição de licitações",
        ),
        RolePermissionsResponse(
            role=UserRole.OPERATOR,
            permissions=[
                "tender:read",
                "tender:update",
                "document:create",
                "document:read",
                "task:read",
                "task:update",
                "quotation:create",
                "quotation:read",
                "quotation:update",
            ],
            description="Operador com acesso a cotações e atualização de licitações",
        ),
        RolePermissionsResponse(
            role=UserRole.VIEWER,
            permissions=[
                "tender:read",
                "document:read",
                "task:read",
                "quotation:read",
                "report:read",
            ],
            description="Visualizador com acesso apenas de leitura",
        ),
    ]

    return roles_info


@router.get("/check-permission")
async def check_user_permission(
    resource_type: ResourceType = Query(...),
    action: PermissionAction = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Check if current user has specific permission."""

    try:
        has_permission = current_user.has_permission(resource_type, action)

        return {
            "user_id": str(current_user.id),
            "resource_type": resource_type.value,
            "action": action.value,
            "has_permission": has_permission,
            "user_role": current_user.role.value,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao verificar permissão",
        )


@router.get("/matrix")
async def get_permission_matrix(
    current_user: User = Depends(check_admin_access), db: Session = Depends(get_db)
):
    """Get complete permission matrix for all roles and resources."""

    try:
        # Get all users with their roles and permissions
        users = db.query(User).filter(User.is_active == True).all()

        # Build permission matrix
        matrix = {}

        for user in users:
            user_permissions = []

            # Add explicit permissions
            for perm in user.permissions:
                if perm.is_active:
                    user_permissions.append(
                        f"{perm.resource_type.value}:{perm.action.value}"
                    )

            # Add role-based permissions (simplified)
            role_perms = {
                UserRole.SUPER_ADMIN: ["*:*"],
                UserRole.ADMIN: ["user:read", "user:write", "tender:*", "report:*"],
                UserRole.MANAGER: ["tender:read", "tender:write", "report:read"],
                UserRole.OPERATOR: ["tender:read", "quotation:*"],
                UserRole.VIEWER: ["tender:read", "quotation:read"],
            }

            user_permissions.extend(role_perms.get(user.role, []))

            matrix[str(user.id)] = {
                "name": user.full_name,
                "email": user.email,
                "role": user.role.value,
                "permissions": list(set(user_permissions)),  # Remove duplicates
            }

        # Get resource/action combinations
        all_resources = [r.value for r in ResourceType]
        all_actions = [a.value for a in PermissionAction]

        return {
            "users": matrix,
            "available_resources": all_resources,
            "available_actions": all_actions,
            "total_users": len(matrix),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar matriz de permissões",
        )
