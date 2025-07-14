"""
User models for authentication and RBAC system
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class UserRole(str, enum.Enum):
    """User role enumeration for RBAC system."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class PermissionAction(str, enum.Enum):
    """Permission actions for RBAC system."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(str, enum.Enum):
    """Resource types for permission system."""

    TENDER = "tender"
    DOCUMENT = "document"
    TASK = "task"
    MESSAGE = "message"
    USER = "user"
    REPORT = "report"
    SYSTEM = "system"


# Association table for many-to-many relationship between User and Permission
user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("permissions.id"),
        primary_key=True,
    ),
)


class User(Base):
    """User model with comprehensive authentication and profile information."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)

    # Organization information
    company = Column(String(200), nullable=True)
    position = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    # Role and status
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # MFA settings
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(32), nullable=True)  # TOTP secret
    backup_codes = Column(JSON, nullable=True)  # Encrypted backup codes

    # Security tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 support
    password_changed_at = Column(DateTime(timezone=True), default=func.now())

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Preferences
    timezone = Column(String(50), default="America/Sao_Paulo", nullable=False)
    language = Column(String(10), default="pt-BR", nullable=False)
    theme = Column(String(10), default="auto", nullable=False)  # light, dark, auto

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    permissions = relationship(
        "Permission", secondary=user_permissions, back_populates="users"
    )
    created_users = relationship("User", foreign_keys=[created_by], remote_side=[id])
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_settings = relationship(
        "NotificationSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    presence = relationship(
        "UserPresence",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Get user's display name with company if available."""
        name = self.full_name
        if self.company:
            name += f" ({self.company})"
        return name

    def has_permission(
        self, resource_type: ResourceType, action: PermissionAction
    ) -> bool:
        """Check if user has specific permission."""
        # Super admin has all permissions
        if self.is_superuser:
            return True

        # Check explicit permissions
        for permission in self.permissions:
            if (
                permission.resource_type == resource_type
                and permission.action == action
                and permission.is_active
            ):
                return True

        # Check role-based permissions
        return self._has_role_permission(resource_type, action)

    def _has_role_permission(
        self, resource_type: ResourceType, action: PermissionAction
    ) -> bool:
        """Check role-based permissions."""
        role_permissions = {
            UserRole.SUPER_ADMIN: True,  # All permissions
            UserRole.ADMIN: {
                ResourceType.USER: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.TENDER: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                    PermissionAction.DELETE,
                ],
                ResourceType.DOCUMENT: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                    PermissionAction.DELETE,
                ],
                ResourceType.TASK: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                    PermissionAction.DELETE,
                ],
                ResourceType.MESSAGE: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.REPORT: [PermissionAction.READ, PermissionAction.CREATE],
            },
            UserRole.MANAGER: {
                ResourceType.TENDER: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.DOCUMENT: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.TASK: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.MESSAGE: [
                    PermissionAction.CREATE,
                    PermissionAction.READ,
                    PermissionAction.UPDATE,
                ],
                ResourceType.REPORT: [PermissionAction.READ, PermissionAction.CREATE],
            },
            UserRole.OPERATOR: {
                ResourceType.TENDER: [PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.DOCUMENT: [PermissionAction.CREATE, PermissionAction.READ],
                ResourceType.TASK: [PermissionAction.READ, PermissionAction.UPDATE],
                ResourceType.MESSAGE: [PermissionAction.CREATE, PermissionAction.READ],
                ResourceType.REPORT: [PermissionAction.READ],
            },
            UserRole.VIEWER: {
                ResourceType.TENDER: [PermissionAction.READ],
                ResourceType.DOCUMENT: [PermissionAction.READ],
                ResourceType.TASK: [PermissionAction.READ],
                ResourceType.MESSAGE: [PermissionAction.READ],
                ResourceType.REPORT: [PermissionAction.READ],
            },
        }

        if self.role == UserRole.SUPER_ADMIN:
            return True

        role_perms = role_permissions.get(self.role, {})
        resource_perms = role_perms.get(resource_type, [])
        return action in resource_perms


class Permission(Base):
    """Permission model for granular access control."""

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Permission details
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    action = Column(SQLEnum(PermissionAction), nullable=False)

    # Conditions (JSON field for complex permission logic)
    conditions = Column(JSON, nullable=True)  # e.g., {"tender_value": {"max": 100000}}

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    users = relationship(
        "User", secondary=user_permissions, back_populates="permissions"
    )


class RefreshToken(Base):
    """Refresh token model for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Token metadata
    device_info = Column(JSON, nullable=True)  # Browser, OS, etc.
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Status and expiry
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(Base):
    """Audit log model for security and compliance tracking."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Action details
    action = Column(String(100), nullable=False)  # LOGIN, LOGOUT, CREATE_TENDER, etc.
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_path = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)

    # Additional context
    details = Column(JSON, nullable=True)  # Additional action details
    status = Column(
        String(20), nullable=False, default="SUCCESS"
    )  # SUCCESS, FAILED, ERROR

    # Timing
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class LoginAttempt(Base):
    """Login attempt tracking for security monitoring."""

    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)

    # Attempt details
    success = Column(Boolean, nullable=False)
    failure_reason = Column(
        String(100), nullable=True
    )  # INVALID_PASSWORD, ACCOUNT_LOCKED, etc.

    # Timestamps
    attempted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Additional context
    details = Column(JSON, nullable=True)
