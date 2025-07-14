"""
Advanced Token Management Service
Handles refresh token rotation, blacklisting, and security monitoring
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_device_fingerprint,
    create_refresh_token,
    extract_device_info,
    extract_token_jti,
    verify_token,
)
from app.models.user import AuditLog, RefreshToken, User

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """In-memory token blacklist (in production, use Redis)"""

    _blacklisted_tokens = set()

    @classmethod
    def add_token(cls, jti: str):
        cls._blacklisted_tokens.add(jti)

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        return jti in cls._blacklisted_tokens

    @classmethod
    def clear_expired(cls):
        # In production, implement proper TTL cleanup
        pass


class TokenService:
    """Service for advanced token management"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis_client = redis_client
        self.max_refresh_tokens_per_user = 5  # Limit concurrent sessions
        self.refresh_token_rotation_threshold = timedelta(
            hours=6
        )  # Rotate after 6 hours

    async def create_token_pair(
        self,
        user: User,
        ip_address: str,
        user_agent: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create access and refresh token pair with device tracking."""

        try:
            # Extract device information
            device_info = extract_device_info(user_agent)
            device_fingerprint = create_device_fingerprint(
                user_agent, ip_address, device_info
            )

            # Clean up old refresh tokens for this user
            await self._cleanup_old_refresh_tokens(user.id)

            # Create access token
            access_token_claims = {
                "role": user.role.value,
                "permissions": self._get_user_permissions(user),
                "device_id": device_fingerprint[:16],  # Short device identifier
            }

            if additional_claims:
                access_token_claims.update(additional_claims)

            access_token = create_access_token(
                subject=str(user.id), additional_claims=access_token_claims
            )

            # Create refresh token
            refresh_token = create_refresh_token(
                subject=str(user.id), device_info=device_info
            )

            # Store refresh token in database
            refresh_token_record = RefreshToken(
                token=refresh_token,
                user_id=user.id,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow()
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                last_used_at=datetime.utcnow(),
            )

            self.db.add(refresh_token_record)
            self.db.commit()

            # Log token creation
            await self._log_token_event(
                user_id=user.id,
                action="TOKEN_CREATED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "device_fingerprint": device_fingerprint,
                    "access_token_jti": extract_token_jti(access_token),
                    "refresh_token_jti": extract_token_jti(refresh_token),
                },
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "device_id": device_fingerprint[:16],
            }

        except Exception as e:
            logger.error(f"Error creating token pair: {str(e)}")
            self.db.rollback()
            raise

    async def refresh_token_pair(
        self, refresh_token: str, ip_address: str, user_agent: str
    ) -> Dict[str, Any]:
        """Refresh token pair with rotation and security checks."""

        try:
            # Verify refresh token
            payload = verify_token(refresh_token, "refresh")
            if not payload:
                raise ValueError("Token inválido")

            # Check if token is blacklisted
            token_jti = payload.get("jti")
            if TokenBlacklist.is_blacklisted(token_jti):
                raise ValueError("Token foi revogado")

            # Get user
            user_id = UUID(payload["sub"])
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                raise ValueError("Usuário não encontrado ou inativo")

            # Find refresh token record
            token_record = (
                self.db.query(RefreshToken)
                .filter(
                    and_(
                        RefreshToken.token == refresh_token,
                        RefreshToken.user_id == user_id,
                        RefreshToken.is_active == True,
                        RefreshToken.expires_at > datetime.utcnow(),
                    )
                )
                .first()
            )

            if not token_record:
                # Token not found - possible reuse attack
                await self._handle_token_reuse_attack(
                    user_id, refresh_token, ip_address, user_agent
                )
                raise ValueError("Token não encontrado ou expirado")

            # Check device consistency
            current_device_info = extract_device_info(user_agent)
            if not self._is_device_consistent(
                token_record.device_info,
                current_device_info,
                ip_address,
                token_record.ip_address,
            ):
                await self._handle_suspicious_activity(
                    user_id,
                    "DEVICE_MISMATCH",
                    ip_address,
                    user_agent,
                    {
                        "original_device": token_record.device_info,
                        "current_device": current_device_info,
                        "original_ip": token_record.ip_address,
                        "current_ip": ip_address,
                    },
                )
                raise ValueError("Atividade suspeita detectada")

            # Check if rotation is needed
            needs_rotation = self._needs_token_rotation(token_record)

            if needs_rotation:
                # Rotate: blacklist old token and create new pair
                TokenBlacklist.add_token(token_jti)
                token_record.is_active = False

                new_token_pair = await self.create_token_pair(
                    user=user, ip_address=ip_address, user_agent=user_agent
                )

                await self._log_token_event(
                    user_id=user_id,
                    action="TOKEN_ROTATED",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "old_token_jti": token_jti,
                        "new_access_token_jti": extract_token_jti(
                            new_token_pair["access_token"]
                        ),
                        "new_refresh_token_jti": extract_token_jti(
                            new_token_pair["refresh_token"]
                        ),
                    },
                )

                return new_token_pair

            else:
                # Just create new access token
                access_token_claims = {
                    "role": user.role.value,
                    "permissions": self._get_user_permissions(user),
                    "device_id": create_device_fingerprint(user_agent, ip_address)[:16],
                }

                access_token = create_access_token(
                    subject=str(user.id), additional_claims=access_token_claims
                )

                # Update last used time
                token_record.last_used_at = datetime.utcnow()
                self.db.commit()

                await self._log_token_event(
                    user_id=user_id,
                    action="TOKEN_REFRESHED",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "access_token_jti": extract_token_jti(access_token),
                        "refresh_token_jti": token_jti,
                    },
                )

                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,  # Keep same refresh token
                    "token_type": "bearer",
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                }

        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise

    async def revoke_token(
        self,
        refresh_token: str,
        user_id: Optional[UUID] = None,
        revoke_all_user_tokens: bool = False,
    ) -> bool:
        """Revoke refresh token(s)."""

        try:
            if revoke_all_user_tokens and user_id:
                # Revoke all tokens for user
                tokens = (
                    self.db.query(RefreshToken)
                    .filter(
                        and_(
                            RefreshToken.user_id == user_id,
                            RefreshToken.is_active == True,
                        )
                    )
                    .all()
                )

                for token in tokens:
                    token.is_active = False
                    token_jti = extract_token_jti(token.token)
                    if token_jti:
                        TokenBlacklist.add_token(token_jti)

                await self._log_token_event(
                    user_id=user_id,
                    action="ALL_TOKENS_REVOKED",
                    details={"revoked_count": len(tokens)},
                )

            else:
                # Revoke specific token
                payload = verify_token(refresh_token, "refresh")
                if payload:
                    token_jti = payload.get("jti")
                    user_id = UUID(payload["sub"])

                    # Blacklist token
                    if token_jti:
                        TokenBlacklist.add_token(token_jti)

                    # Deactivate in database
                    token_record = (
                        self.db.query(RefreshToken)
                        .filter(RefreshToken.token == refresh_token)
                        .first()
                    )

                    if token_record:
                        token_record.is_active = False

                    await self._log_token_event(
                        user_id=user_id,
                        action="TOKEN_REVOKED",
                        details={"token_jti": token_jti},
                    )

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error revoking token: {str(e)}")
            self.db.rollback()
            return False

    async def get_user_sessions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get active sessions for user."""

        try:
            sessions = (
                self.db.query(RefreshToken)
                .filter(
                    and_(
                        RefreshToken.user_id == user_id,
                        RefreshToken.is_active == True,
                        RefreshToken.expires_at > datetime.utcnow(),
                    )
                )
                .order_by(RefreshToken.last_used_at.desc())
                .all()
            )

            result = []
            for session in sessions:
                device_info = session.device_info or {}
                result.append(
                    {
                        "id": str(session.id),
                        "device": device_info.get("device", "unknown"),
                        "browser": device_info.get("browser", "unknown"),
                        "os": device_info.get("os", "unknown"),
                        "ip_address": session.ip_address,
                        "location": await self._get_location_from_ip(
                            session.ip_address
                        ),
                        "created_at": session.created_at,
                        "last_used_at": session.last_used_at,
                        "is_current": False,  # Will be determined by caller
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []

    def _get_user_permissions(self, user: User) -> List[str]:
        """Get user permissions for token claims."""
        # This would integrate with your RBAC system
        permissions = []

        # Add role-based permissions
        role_permissions = {
            "super_admin": ["*"],
            "admin": ["users:read", "users:write", "tenders:*", "reports:*"],
            "manager": ["tenders:read", "tenders:write", "reports:read"],
            "operator": ["tenders:read", "quotations:*"],
            "viewer": ["tenders:read", "quotations:read"],
        }

        permissions.extend(role_permissions.get(user.role.value, []))

        # Add explicit user permissions
        for permission in user.permissions:
            if permission.is_active:
                perm_string = (
                    f"{permission.resource_type.value}:{permission.action.value}"
                )
                permissions.append(perm_string)

        return list(set(permissions))  # Remove duplicates

    async def _cleanup_old_refresh_tokens(self, user_id: UUID):
        """Clean up old refresh tokens to maintain session limit."""

        # Get all active tokens for user
        active_tokens = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_active == True,
                    RefreshToken.expires_at > datetime.utcnow(),
                )
            )
            .order_by(RefreshToken.last_used_at.desc())
            .all()
        )

        # If we have too many active tokens, deactivate the oldest ones
        if len(active_tokens) >= self.max_refresh_tokens_per_user:
            tokens_to_remove = active_tokens[self.max_refresh_tokens_per_user - 1 :]

            for token in tokens_to_remove:
                token.is_active = False
                token_jti = extract_token_jti(token.token)
                if token_jti:
                    TokenBlacklist.add_token(token_jti)

        # Also clean up expired tokens
        expired_tokens = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.expires_at <= datetime.utcnow(),
                )
            )
            .all()
        )

        for token in expired_tokens:
            token.is_active = False

        self.db.commit()

    def _needs_token_rotation(self, token_record: RefreshToken) -> bool:
        """Check if token needs rotation based on age and usage."""

        # Rotate if token is older than threshold
        if (
            datetime.utcnow() - token_record.created_at
            > self.refresh_token_rotation_threshold
        ):
            return True

        # Rotate if last used time is significantly old
        if (
            token_record.last_used_at
            and datetime.utcnow() - token_record.last_used_at > timedelta(hours=24)
        ):
            return True

        return False

    def _is_device_consistent(
        self,
        original_device: Dict[str, Any],
        current_device: Dict[str, Any],
        original_ip: str,
        current_ip: str,
    ) -> bool:
        """Check if current device is consistent with original."""

        # Allow some flexibility in device detection
        if not original_device or not current_device:
            return True

        # Check critical fields
        critical_fields = ["browser", "os"]
        for field in critical_fields:
            if (
                original_device.get(field, "unknown") != "unknown"
                and current_device.get(field, "unknown") != "unknown"
                and original_device.get(field) != current_device.get(field)
            ):
                return False

        # IP address changes are allowed but logged
        if original_ip != current_ip:
            logger.info(f"IP address changed: {original_ip} -> {current_ip}")

        return True

    async def _handle_token_reuse_attack(
        self, user_id: UUID, token: str, ip_address: str, user_agent: str
    ):
        """Handle potential token reuse attack."""

        logger.warning(
            f"Potential token reuse attack for user {user_id} from {ip_address}"
        )

        # Revoke all tokens for this user
        await self.revoke_token(token, user_id, revoke_all_user_tokens=True)

        # Log security incident
        await self._log_token_event(
            user_id=user_id,
            action="TOKEN_REUSE_ATTACK",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"all_tokens_revoked": True},
            status="SECURITY_INCIDENT",
        )

    async def _handle_suspicious_activity(
        self,
        user_id: UUID,
        activity_type: str,
        ip_address: str,
        user_agent: str,
        details: Dict[str, Any],
    ):
        """Handle suspicious activity detection."""

        logger.warning(
            f"Suspicious activity detected: {activity_type} for user {user_id}"
        )

        await self._log_token_event(
            user_id=user_id,
            action=f"SUSPICIOUS_ACTIVITY_{activity_type}",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            status="SECURITY_WARNING",
        )

    async def _log_token_event(
        self,
        user_id: UUID,
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
    ):
        """Log token-related events."""

        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="TOKEN",
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                status=status,
                timestamp=datetime.utcnow(),
            )

            self.db.add(audit_log)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log token event: {str(e)}")
            self.db.rollback()

    async def _get_location_from_ip(self, ip_address: str) -> str:
        """Get approximate location from IP address."""
        # In production, use a GeoIP service
        if ip_address in ["127.0.0.1", "localhost", "::1"]:
            return "Local"
        return "Unknown"
