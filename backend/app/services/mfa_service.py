"""
Multi-Factor Authentication Service
Handles MFA setup, verification, and security events
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import AuditLog, User

logger = logging.getLogger(__name__)


class MFAService:
    """Service for handling Multi-Factor Authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, user: User, password: str) -> bool:
        """Verify user's current password."""
        return verify_password(password, user.hashed_password)

    def verify_password_hash(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return verify_password(password, hashed)

    async def log_security_event(
        self,
        user_id: UUID,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "SUCCESS",
    ):
        """Log security-related events for audit purposes."""

        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="SECURITY",
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                status=status,
                timestamp=datetime.utcnow(),
            )

            self.db.add(audit_log)
            self.db.commit()

            logger.info(f"Security event logged: {action} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
            self.db.rollback()

    async def check_mfa_requirements(self, user: User) -> Dict[str, Any]:
        """Check if user needs to complete MFA setup or verification."""

        result = {
            "requires_setup": False,
            "requires_verification": False,
            "has_backup_codes": False,
            "backup_codes_count": 0,
        }

        if not user.mfa_enabled:
            # MFA is not enabled
            result["requires_setup"] = True
        else:
            # MFA is enabled, check verification requirements
            result["requires_verification"] = True

            # Check backup codes
            if user.backup_codes:
                try:
                    codes = json.loads(user.backup_codes)
                    result["has_backup_codes"] = len(codes) > 0
                    result["backup_codes_count"] = len(codes)
                except:
                    result["has_backup_codes"] = False

        return result

    async def validate_mfa_setup(self, user: User) -> List[str]:
        """Validate MFA setup and return any issues."""

        issues = []

        if user.mfa_enabled:
            # Check if secret exists
            if not user.mfa_secret:
                issues.append("MFA habilitado mas segredo não encontrado")

            # Check if backup codes exist
            if not user.backup_codes:
                issues.append("Códigos de backup não configurados")
            else:
                try:
                    codes = json.loads(user.backup_codes)
                    if len(codes) == 0:
                        issues.append("Nenhum código de backup restante")
                    elif len(codes) < 3:
                        issues.append(
                            f"Poucos códigos de backup restantes: {len(codes)}"
                        )
                except:
                    issues.append("Códigos de backup corrompidos")

        return issues

    async def get_mfa_statistics(
        self, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get MFA usage statistics."""

        try:
            # Base query
            query = self.db.query(AuditLog).filter(AuditLog.action.like("MFA_%"))

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            # Get recent events (last 30 days)
            recent_date = datetime.utcnow() - timedelta(days=30)
            recent_events = query.filter(AuditLog.timestamp >= recent_date).all()

            # Count different event types
            event_counts = {}
            for event in recent_events:
                action = event.action
                event_counts[action] = event_counts.get(action, 0) + 1

            # Get total MFA enabled users
            if not user_id:
                total_mfa_users = (
                    self.db.query(User).filter(User.mfa_enabled == True).count()
                )

                total_users = self.db.query(User).filter(User.is_active == True).count()

                mfa_adoption_rate = (
                    (total_mfa_users / total_users * 100) if total_users > 0 else 0
                )
            else:
                total_mfa_users = None
                total_users = None
                mfa_adoption_rate = None

            return {
                "event_counts": event_counts,
                "total_events": len(recent_events),
                "period_days": 30,
                "total_mfa_users": total_mfa_users,
                "total_users": total_users,
                "mfa_adoption_rate": round(mfa_adoption_rate, 2)
                if mfa_adoption_rate
                else None,
            }

        except Exception as e:
            logger.error(f"Error getting MFA statistics: {str(e)}")
            return {
                "error": "Erro ao obter estatísticas",
                "event_counts": {},
                "total_events": 0,
            }

    async def handle_mfa_login_attempt(
        self,
        user: User,
        code: str,
        backup_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle MFA verification during login."""

        if not user.mfa_enabled:
            return {
                "success": False,
                "error": "MFA não está habilitado para este usuário",
            }

        success = False
        used_backup = False

        try:
            # Try TOTP code first
            if code:
                from app.core.security import verify_totp_code

                if verify_totp_code(user.mfa_secret, code):
                    success = True
                    await self.log_security_event(
                        user_id=user.id,
                        action="MFA_LOGIN_SUCCESS",
                        details={"method": "TOTP"},
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )

            # Try backup code if TOTP failed
            if not success and backup_code and user.backup_codes:
                from app.core.security import verify_backup_code

                hashed_codes = json.loads(user.backup_codes)

                if verify_backup_code(backup_code, hashed_codes):
                    success = True
                    used_backup = True

                    # Remove used backup code
                    for i, hashed_code in enumerate(hashed_codes):
                        normalized_code = backup_code.replace("-", "").upper()
                        if verify_password(normalized_code, hashed_code):
                            hashed_codes.pop(i)
                            break

                    # Update backup codes
                    user.backup_codes = json.dumps(hashed_codes)
                    self.db.commit()

                    await self.log_security_event(
                        user_id=user.id,
                        action="MFA_LOGIN_BACKUP_CODE",
                        details={
                            "method": "backup_code",
                            "remaining_codes": len(hashed_codes),
                        },
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )

            # Log failed attempt
            if not success:
                await self.log_security_event(
                    user_id=user.id,
                    action="MFA_LOGIN_FAILED",
                    details={"attempted_method": "TOTP" if code else "backup_code"},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status="FAILED",
                )

            result = {"success": success, "used_backup": used_backup}

            if success and used_backup:
                remaining_codes = (
                    len(json.loads(user.backup_codes)) if user.backup_codes else 0
                )
                result["remaining_backup_codes"] = remaining_codes
                if remaining_codes < 3:
                    result["warning"] = "Poucos códigos de backup restantes"

            return result

        except Exception as e:
            logger.error(f"Error in MFA login attempt: {str(e)}")
            await self.log_security_event(
                user_id=user.id,
                action="MFA_LOGIN_ERROR",
                details={"error": str(e)},
                ip_address=ip_address,
                user_agent=user_agent,
                status="ERROR",
            )

            return {"success": False, "error": "Erro interno na verificação MFA"}

    async def emergency_disable_mfa(
        self,
        user_id: UUID,
        admin_user_id: UUID,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Emergency MFA disable by admin (for account recovery)."""

        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Disable MFA
            user.mfa_enabled = False
            user.mfa_secret = None
            user.backup_codes = None

            self.db.commit()

            # Log emergency action
            await self.log_security_event(
                user_id=user_id,
                action="MFA_EMERGENCY_DISABLED",
                details={"admin_user_id": str(admin_user_id), "reason": reason},
                ip_address=ip_address,
                status="SUCCESS",
            )

            logger.warning(
                f"Emergency MFA disable for user {user_id} by admin {admin_user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error in emergency MFA disable: {str(e)}")
            self.db.rollback()
            return False
