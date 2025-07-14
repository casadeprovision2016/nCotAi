"""
Pydantic schemas for user authentication and management
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str):
    """User role constants."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    timezone: str = Field("America/Sao_Paulo", max_length=50)
    language: str = Field("pt-BR", max_length=10)
    theme: str = Field("auto", pattern=r"^(light|dark|auto)$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]{10,20}$", v):
            raise ValueError("Formato de telefone inválido")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v):
        # Add custom email validation if needed
        return v.lower()


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    role: Optional[str] = Field(UserRole.VIEWER)
    terms_accepted: bool = Field(
        ..., description="User must accept terms and conditions"
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Senha deve ter pelo menos 8 caracteres")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")

        if not re.search(r"[a-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")

        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Senha deve conter pelo menos um caractere especial")

        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("password") and v != info.data["password"]:
            raise ValueError("Senhas não coincidem")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def terms(cls, v):
        if not v:
            raise ValueError("Você deve aceitar os termos e condições")
        return v


class UserUpdate(BaseModel):
    """Schema for user updates."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    theme: Optional[str] = Field(None, pattern=r"^(light|dark|auto)$")
    avatar_url: Optional[str] = Field(None, max_length=500)

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]{10,20}$", v):
            raise ValueError("Formato de telefone inválido")
        return v


class UserInDB(UserBase):
    """Schema for user as stored in database."""

    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    mfa_enabled: bool
    avatar_url: Optional[str]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """Schema for user response (public fields only)."""

    id: UUID
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    avatar_url: Optional[str]
    last_login_at: Optional[datetime]
    created_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Detailed user profile schema."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    avatar_url: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    position: Optional[str]
    department: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    timezone: str
    language: str
    theme: str
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication schemas
class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(False)
    device_info: Optional[Dict[str, Any]] = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        return v.lower()


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str = Field(..., min_length=1)


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Senha deve ter pelo menos 8 caracteres")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")

        if not re.search(r"[a-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")

        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Senha deve conter pelo menos um caractere especial")

        return v

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Senhas não coincidem")
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        return v.lower()


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Senha deve ter pelo menos 8 caracteres")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")

        if not re.search(r"[a-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")

        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Senha deve conter pelo menos um caractere especial")

        return v

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Senhas não coincidem")
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str = Field(..., min_length=1)


# MFA schemas
class MFASetupRequest(BaseModel):
    """Schema for MFA setup request."""

    password: str = Field(..., min_length=1)


class MFASetupResponse(BaseModel):
    """Schema for MFA setup response."""

    secret: str
    qr_code_url: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """Schema for MFA verification request."""

    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v):
        if not v.isdigit():
            raise ValueError("Código deve conter apenas números")
        return v


class MFALoginRequest(BaseModel):
    """Schema for MFA login request."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    mfa_code: str = Field(..., min_length=6, max_length=6)
    remember_me: bool = Field(False)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        return v.lower()

    @field_validator("mfa_code")
    @classmethod
    def validate_mfa_code(cls, v):
        if not v.isdigit():
            raise ValueError("Código MFA deve conter apenas números")
        return v


# Admin schemas
class UserAdminUpdate(BaseModel):
    """Schema for admin user updates."""

    role: Optional[str] = Field(
        None, pattern=r"^(super_admin|admin|manager|operator|viewer)$"
    )
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserListResponse(BaseModel):
    """Schema for user list response."""

    total: int
    page: int
    size: int
    pages: int
    items: List[UserResponse]


# Permission schemas
class PermissionBase(BaseModel):
    """Base permission schema."""

    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    resource_type: str
    action: str
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool = True


class PermissionCreate(PermissionBase):
    """Schema for permission creation."""

    pass


class PermissionUpdate(BaseModel):
    """Schema for permission updates."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PermissionResponse(PermissionBase):
    """Schema for permission response."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Audit schemas
class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_path: Optional[str]
    request_method: Optional[str]
    details: Optional[Dict[str, Any]]
    status: str
    timestamp: datetime
    duration_ms: Optional[int]

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema for audit log list response."""

    total: int
    page: int
    size: int
    pages: int
    items: List[AuditLogResponse]
