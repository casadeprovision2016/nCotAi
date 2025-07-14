"""
Authentication service with comprehensive user management
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_device_fingerprint,
    create_rate_limit_key,
    create_refresh_token,
    decrypt_data,
    encrypt_data,
    extract_device_info,
    generate_backup_codes,
    generate_mfa_secret,
    generate_qr_code_image,
    generate_reset_token,
    generate_verification_token,
    get_password_hash,
    hash_backup_codes,
    is_rate_limited,
    verify_password,
    verify_token,
    verify_totp_code,
)
from app.models.user import AuditLog, LoginAttempt, RefreshToken, User, UserRole
from app.schemas.user import LoginRequest, UserCreate, UserUpdate


class AuthService:
    """Authentication service class."""

    def __init__(self, db: Session, redis_client: redis.Redis = None):
        self.db = db
        self.redis_client = redis_client

    async def register_user(
        self, user_data: UserCreate, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """Register a new user."""

        # Check if user already exists
        existing_user = (
            self.db.query(User).filter(User.email == user_data.email.lower()).first()
        )
        if existing_user:
            raise ValueError("Email já está em uso")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        verification_token = generate_verification_token()

        db_user = User(
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            company=user_data.company,
            position=user_data.position,
            department=user_data.department,
            role=UserRole(user_data.role) if user_data.role else UserRole.VIEWER,
            timezone=user_data.timezone,
            language=user_data.language,
            theme=user_data.theme,
            email_verification_token=verification_token,
            is_active=True,
            is_verified=False,
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Log registration
        await self._log_audit(
            user_id=db_user.id,
            action="REGISTER",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user_data.email.lower()},
        )

        return {
            "user_id": db_user.id,
            "email": db_user.email,
            "verification_token": verification_token,
            "message": "Usuário criado com sucesso. Verifique seu email para ativar a conta.",
        }

    async def authenticate_user(
        self, login_data: LoginRequest, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """Authenticate user and return tokens."""

        # Rate limiting
        if self.redis_client:
            rate_limit_key = create_rate_limit_key(login_data.email, "login")
            if is_rate_limited(
                self.redis_client, rate_limit_key, 5, 300
            ):  # 5 attempts per 5 minutes
                raise ValueError(
                    "Muitas tentativas de login. Tente novamente em 5 minutos."
                )

        # Get user
        user = (
            self.db.query(User).filter(User.email == login_data.email.lower()).first()
        )

        # Log login attempt
        await self._log_login_attempt(
            email=login_data.email.lower(),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="USER_NOT_FOUND" if not user else None,
        )

        if not user:
            raise ValueError("Email ou senha incorretos")

        # Check if account is active
        if not user.is_active:
            await self._log_login_attempt(
                email=login_data.email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="ACCOUNT_INACTIVE",
            )
            raise ValueError("Conta desativada. Entre em contato com o suporte.")

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.is_active = False
                await self._log_audit(
                    user_id=user.id,
                    action="ACCOUNT_LOCKED",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "too_many_failed_attempts"},
                )

            self.db.commit()

            await self._log_login_attempt(
                email=login_data.email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="INVALID_PASSWORD",
            )
            raise ValueError("Email ou senha incorretos")

        # Check if MFA is required
        if user.mfa_enabled:
            # Return MFA challenge
            return {
                "requires_mfa": True,
                "user_id": str(user.id),
                "message": "Código de autenticação de dois fatores necessário",
            }

        # Successful login
        return await self._complete_login(user, login_data, ip_address, user_agent)

    async def authenticate_with_mfa(
        self,
        user_id: str,
        mfa_code: str,
        login_data: LoginRequest,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Complete authentication with MFA code."""

        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise ValueError("Usuário não encontrado")

        # Verify MFA code
        if user.mfa_secret:
            decrypted_secret = decrypt_data(user.mfa_secret)
            if not verify_totp_code(decrypted_secret, mfa_code):
                # Check backup codes
                if user.backup_codes:
                    # TODO: Implement backup code verification
                    pass

                await self._log_login_attempt(
                    email=user.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason="INVALID_MFA_CODE",
                )
                raise ValueError("Código de autenticação inválido")

        # Complete login
        return await self._complete_login(user, login_data, ip_address, user_agent)

    async def _complete_login(
        self,
        user: User,
        login_data: LoginRequest,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Complete the login process and return tokens."""

        # Reset failed attempts
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address

        # Extract device information
        device_info = extract_device_info(user_agent or "")
        device_info["ip_address"] = ip_address
        device_info["fingerprint"] = create_device_fingerprint(
            user_agent or "", ip_address or ""
        )

        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        # If "remember me" is checked, extend refresh token lifetime
        if login_data.remember_me:
            refresh_token_expires = timedelta(days=30)

        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
            additional_claims={
                "role": user.role.value,
                "verified": user.is_verified,
                "mfa": user.mfa_enabled,
            },
        )

        refresh_token = create_refresh_token(
            subject=str(user.id),
            expires_delta=refresh_token_expires,
            device_info=device_info,
        )

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + refresh_token_expires,
        )

        self.db.add(db_refresh_token)
        self.db.commit()

        # Log successful login
        await self._log_login_attempt(
            email=user.email, ip_address=ip_address, user_agent=user_agent, success=True
        )

        await self._log_audit(
            user_id=user.id,
            action="LOGIN",
            ip_address=ip_address,
            user_agent=user_agent,
            details=device_info,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
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

    async def refresh_access_token(
        self, refresh_token: str, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token."""

        # Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise ValueError("Token de atualização inválido")

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Check if refresh token exists in database
        db_refresh_token = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.token == refresh_token,
                    RefreshToken.user_id == UUID(user_id),
                    RefreshToken.is_active == True,
                    RefreshToken.expires_at > datetime.utcnow(),
                )
            )
            .first()
        )

        if not db_refresh_token:
            raise ValueError("Token de atualização não encontrado ou expirado")

        # Get user
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user or not user.is_active:
            raise ValueError("Usuário não encontrado ou inativo")

        # Update refresh token last used
        db_refresh_token.last_used_at = datetime.utcnow()

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
            additional_claims={
                "role": user.role.value,
                "verified": user.is_verified,
                "mfa": user.mfa_enabled,
            },
        )

        self.db.commit()

        # Log token refresh
        await self._log_audit(
            user_id=user.id,
            action="TOKEN_REFRESH",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
        }

    async def logout_user(
        self,
        refresh_token: str,
        user_id: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Logout user and invalidate refresh token."""

        # Deactivate refresh token
        db_refresh_token = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.token == refresh_token,
                    RefreshToken.user_id == UUID(user_id),
                    RefreshToken.is_active == True,
                )
            )
            .first()
        )

        if db_refresh_token:
            db_refresh_token.is_active = False
            self.db.commit()

        # Log logout
        await self._log_audit(
            user_id=UUID(user_id),
            action="LOGOUT",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"message": "Logout realizado com sucesso"}

    async def logout_all_devices(
        self, user_id: str, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """Logout user from all devices."""

        # Deactivate all refresh tokens for user
        self.db.query(RefreshToken).filter(
            and_(RefreshToken.user_id == UUID(user_id), RefreshToken.is_active == True)
        ).update({"is_active": False})

        self.db.commit()

        # Log logout all
        await self._log_audit(
            user_id=UUID(user_id),
            action="LOGOUT_ALL_DEVICES",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"message": "Logout realizado em todos os dispositivos"}

    async def setup_mfa(
        self,
        user_id: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Setup MFA for user."""

        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise ValueError("Usuário não encontrado")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise ValueError("Senha incorreta")

        # Generate MFA secret
        secret = generate_mfa_secret()
        encrypted_secret = encrypt_data(secret)

        # Generate backup codes
        backup_codes = generate_backup_codes()
        hashed_backup_codes = hash_backup_codes(backup_codes)

        # Store in database (but don't enable MFA yet)
        user.mfa_secret = encrypted_secret
        user.backup_codes = hashed_backup_codes

        self.db.commit()

        # Generate QR code
        qr_code_image = generate_qr_code_image(secret, user.email)

        # Log MFA setup
        await self._log_audit(
            user_id=user.id,
            action="MFA_SETUP_STARTED",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "secret": secret,
            "qr_code_image": qr_code_image,
            "backup_codes": backup_codes,
            "message": "Configure o aplicativo autenticador e confirme com um código",
        }

    async def verify_and_enable_mfa(
        self,
        user_id: str,
        verification_code: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Verify MFA setup and enable it."""

        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user or not user.mfa_secret:
            raise ValueError("Setup MFA não iniciado")

        # Verify code
        decrypted_secret = decrypt_data(user.mfa_secret)
        if not verify_totp_code(decrypted_secret, verification_code):
            raise ValueError("Código de verificação inválido")

        # Enable MFA
        user.mfa_enabled = True
        self.db.commit()

        # Log MFA enabled
        await self._log_audit(
            user_id=user.id,
            action="MFA_ENABLED",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"message": "Autenticação de dois fatores habilitada com sucesso"}

    async def disable_mfa(
        self,
        user_id: str,
        password: str,
        mfa_code: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Disable MFA for user."""

        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise ValueError("Usuário não encontrado")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise ValueError("Senha incorreta")

        # Verify MFA code
        if user.mfa_secret:
            decrypted_secret = decrypt_data(user.mfa_secret)
            if not verify_totp_code(decrypted_secret, mfa_code):
                raise ValueError("Código MFA inválido")

        # Disable MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        user.backup_codes = None

        self.db.commit()

        # Log MFA disabled
        await self._log_audit(
            user_id=user.id,
            action="MFA_DISABLED",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"message": "Autenticação de dois fatores desabilitada"}

    async def _log_audit(
        self,
        user_id: UUID,
        action: str,
        ip_address: str = None,
        user_agent: str = None,
        details: Dict[str, Any] = None,
        status: str = "SUCCESS",
    ):
        """Log audit event."""

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            status=status,
        )

        self.db.add(audit_log)
        # Note: Commit is handled by the calling method

    async def _log_login_attempt(
        self,
        email: str,
        ip_address: str = None,
        user_agent: str = None,
        success: bool = False,
        failure_reason: str = None,
    ):
        """Log login attempt."""

        login_attempt = LoginAttempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )

        self.db.add(login_attempt)
        # Note: Commit is handled by the calling method
