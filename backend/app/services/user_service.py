"""
User management service
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.core.security import (
    generate_reset_token,
    generate_verification_token,
    get_password_hash,
    verify_password,
)
from app.models.user import (
    AuditLog,
    Permission,
    PermissionAction,
    ResourceType,
    User,
    UserRole,
)
from app.schemas.user import (
    PermissionCreate,
    PermissionUpdate,
    UserAdminUpdate,
    UserUpdate,
)


class UserService:
    """User management service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email.lower()).first()

    def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str = None,
        role: str = None,
        is_active: bool = None,
        is_verified: bool = None,
    ) -> Tuple[List[User], int]:
        """Get users with filtering and pagination."""

        query = self.db.query(User)

        # Apply filters
        if search:
            search_filter = or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.company.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        if role:
            query = query.filter(User.role == role)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if is_verified is not None:
            query = query.filter(User.is_verified == is_verified)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()

        return users, total

    def update_user(
        self, user_id: UUID, user_update: UserUpdate, updated_by: UUID = None
    ) -> User:
        """Update user information."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_by = updated_by
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        return user

    def update_user_admin(
        self, user_id: UUID, user_update: UserAdminUpdate, updated_by: UUID
    ) -> User:
        """Update user information (admin only)."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "role" and value:
                setattr(user, field, UserRole(value))
            else:
                setattr(user, field, value)

        user.updated_by = updated_by
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> Dict[str, str]:
        """Change user password."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Senha atual incorreta")

        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = datetime.utcnow()

        self.db.commit()

        return {"message": "Senha alterada com sucesso"}

    def reset_password_request(self, email: str) -> Dict[str, str]:
        """Request password reset."""

        user = self.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists
            return {
                "message": "Se o email existir, você receberá instruções para redefinir a senha"
            }

        # Generate reset token
        reset_token = generate_reset_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)

        self.db.commit()

        # TODO: Send email with reset link

        return {
            "message": "Se o email existir, você receberá instruções para redefinir a senha",
            "reset_token": reset_token,  # Remove this in production
        }

    def reset_password_confirm(self, token: str, new_password: str) -> Dict[str, str]:
        """Confirm password reset."""

        user = (
            self.db.query(User)
            .filter(
                and_(
                    User.password_reset_token == token,
                    User.password_reset_expires > datetime.utcnow(),
                )
            )
            .first()
        )

        if not user:
            raise ValueError("Token de redefinição inválido ou expirado")

        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.password_changed_at = datetime.utcnow()

        self.db.commit()

        return {"message": "Senha redefinida com sucesso"}

    def verify_email(self, token: str) -> Dict[str, str]:
        """Verify user email."""

        user = (
            self.db.query(User).filter(User.email_verification_token == token).first()
        )
        if not user:
            raise ValueError("Token de verificação inválido")

        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None

        self.db.commit()

        return {"message": "Email verificado com sucesso"}

    def resend_verification_email(self, email: str) -> Dict[str, str]:
        """Resend verification email."""

        user = self.get_user_by_email(email)
        if not user:
            return {
                "message": "Se o email existir, será enviado um novo link de verificação"
            }

        if user.is_verified:
            return {"message": "Email já verificado"}

        # Generate new verification token
        verification_token = generate_verification_token()
        user.email_verification_token = verification_token

        self.db.commit()

        # TODO: Send verification email

        return {
            "message": "Se o email existir, será enviado um novo link de verificação",
            "verification_token": verification_token,  # Remove this in production
        }

    def deactivate_user(self, user_id: UUID, deactivated_by: UUID) -> Dict[str, str]:
        """Deactivate user account."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        user.is_active = False
        user.updated_by = deactivated_by
        user.updated_at = datetime.utcnow()

        self.db.commit()

        return {"message": "Usuário desativado com sucesso"}

    def reactivate_user(self, user_id: UUID, reactivated_by: UUID) -> Dict[str, str]:
        """Reactivate user account."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        user.is_active = True
        user.failed_login_attempts = 0  # Reset failed attempts
        user.updated_by = reactivated_by
        user.updated_at = datetime.utcnow()

        self.db.commit()

        return {"message": "Usuário reativado com sucesso"}

    def delete_user(self, user_id: UUID, deleted_by: UUID) -> Dict[str, str]:
        """Soft delete user account."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        # Soft delete by deactivating and marking email as deleted
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.com"
        user.updated_by = deleted_by
        user.updated_at = datetime.utcnow()

        self.db.commit()

        return {"message": "Usuário removido com sucesso"}

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""

        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        verified_users = self.db.query(User).filter(User.is_verified == True).count()

        # Users by role
        role_stats = (
            self.db.query(User.role, func.count(User.id).label("count"))
            .group_by(User.role)
            .all()
        )

        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = (
            self.db.query(User).filter(User.created_at >= thirty_days_ago).count()
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "inactive_users": total_users - active_users,
            "unverified_users": total_users - verified_users,
            "recent_registrations": recent_registrations,
            "role_distribution": {role: count for role, count in role_stats},
        }

    # Permission management
    def create_permission(
        self, permission_data: PermissionCreate, created_by: UUID
    ) -> Permission:
        """Create a new permission."""

        permission = Permission(
            name=permission_data.name,
            description=permission_data.description,
            resource_type=ResourceType(permission_data.resource_type),
            action=PermissionAction(permission_data.action),
            conditions=permission_data.conditions,
            is_active=permission_data.is_active,
            created_by=created_by,
        )

        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)

        return permission

    def get_permissions(
        self,
        skip: int = 0,
        limit: int = 100,
        resource_type: str = None,
        action: str = None,
        is_active: bool = None,
    ) -> Tuple[List[Permission], int]:
        """Get permissions with filtering and pagination."""

        query = self.db.query(Permission)

        if resource_type:
            query = query.filter(Permission.resource_type == resource_type)

        if action:
            query = query.filter(Permission.action == action)

        if is_active is not None:
            query = query.filter(Permission.is_active == is_active)

        total = query.count()
        permissions = (
            query.order_by(desc(Permission.created_at)).offset(skip).limit(limit).all()
        )

        return permissions, total

    def update_permission(
        self, permission_id: UUID, permission_update: PermissionUpdate
    ) -> Permission:
        """Update permission."""

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError("Permissão não encontrada")

        update_data = permission_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(permission, field, value)

        permission.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(permission)

        return permission

    def delete_permission(self, permission_id: UUID) -> Dict[str, str]:
        """Delete permission."""

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError("Permissão não encontrada")

        self.db.delete(permission)
        self.db.commit()

        return {"message": "Permissão removida com sucesso"}

    def assign_permission_to_user(
        self, user_id: UUID, permission_id: UUID
    ) -> Dict[str, str]:
        """Assign permission to user."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError("Permissão não encontrada")

        if permission not in user.permissions:
            user.permissions.append(permission)
            self.db.commit()

        return {"message": "Permissão atribuída com sucesso"}

    def remove_permission_from_user(
        self, user_id: UUID, permission_id: UUID
    ) -> Dict[str, str]:
        """Remove permission from user."""

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")

        permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if not permission:
            raise ValueError("Permissão não encontrada")

        if permission in user.permissions:
            user.permissions.remove(permission)
            self.db.commit()

        return {"message": "Permissão removida com sucesso"}

    def get_user_audit_logs(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        action: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> Tuple[List[AuditLog], int]:
        """Get user audit logs."""

        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        total = query.count()
        logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()

        return logs, total
