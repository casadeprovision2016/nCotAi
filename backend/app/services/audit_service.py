"""
Comprehensive Audit Service for COTAI
Handles security monitoring, compliance logging, and suspicious activity detection
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import AuditLog, LoginAttempt, User

logger = logging.getLogger(__name__)


class AuditService:
    """Service for comprehensive audit logging and security monitoring"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis_client = redis_client

        # Security thresholds
        self.max_failed_logins = 5
        self.suspicious_activity_window = timedelta(minutes=15)
        self.geographic_anomaly_threshold = 500  # km

        # Event severity levels
        self.severity_levels = {
            "LOGIN_SUCCESS": "INFO",
            "LOGIN_FAILED": "WARNING",
            "MFA_ENABLED": "INFO",
            "MFA_DISABLED": "WARNING",
            "PASSWORD_CHANGED": "INFO",
            "ACCOUNT_LOCKED": "WARNING",
            "SUSPICIOUS_LOGIN": "HIGH",
            "TOKEN_REUSE_ATTACK": "CRITICAL",
            "PRIVILEGE_ESCALATION": "CRITICAL",
            "DATA_EXPORT": "MEDIUM",
            "ADMIN_ACTION": "MEDIUM",
        }

    async def log_user_action(
        self,
        user_id: Optional[UUID],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """Log user action with comprehensive details."""

        try:
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
                request_method=request_method,
                details=details or {},
                status=status,
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
            )

            self.db.add(audit_log)
            self.db.commit()

            # Check for suspicious patterns
            await self._analyze_security_patterns(
                user_id, action, ip_address, user_agent, details
            )

            # Log to external systems if configured
            await self._export_to_siem(audit_log)

            return audit_log

        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            self.db.rollback()
            raise

    async def log_login_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> LoginAttempt:
        """Log login attempt for security monitoring."""

        try:
            login_attempt = LoginAttempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
                details=details or {},
                attempted_at=datetime.utcnow(),
            )

            self.db.add(login_attempt)
            self.db.commit()

            # Check for brute force attacks
            if not success:
                await self._check_brute_force_attack(email, ip_address)

            return login_attempt

        except Exception as e:
            logger.error(f"Failed to log login attempt: {str(e)}")
            self.db.rollback()
            raise

    async def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        """Get audit logs with filtering and pagination."""

        try:
            query = self.db.query(AuditLog)

            # Apply filters
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)

            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)

            if action:
                query = query.filter(AuditLog.action.ilike(f"%{action}%"))

            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)

            if status:
                query = query.filter(AuditLog.status == status)

            # Filter by severity if provided
            if severity:
                actions_with_severity = [
                    action
                    for action, sev in self.severity_levels.items()
                    if sev == severity
                ]
                if actions_with_severity:
                    query = query.filter(AuditLog.action.in_(actions_with_severity))

            # Get total count
            total = query.count()

            # Apply pagination and ordering
            logs = (
                query.order_by(desc(AuditLog.timestamp))
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )

            # Convert to response format
            log_data = []
            for log in logs:
                log_data.append(
                    {
                        "id": str(log.id),
                        "user_id": str(log.user_id) if log.user_id else None,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "request_path": log.request_path,
                        "request_method": log.request_method,
                        "details": log.details,
                        "status": log.status,
                        "timestamp": log.timestamp.isoformat(),
                        "duration_ms": log.duration_ms,
                        "severity": self.severity_levels.get(log.action, "INFO"),
                    }
                )

            return {
                "logs": log_data,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size,
            }

        except Exception as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            return {
                "logs": [],
                "total": 0,
                "page": page,
                "size": size,
                "pages": 0,
                "error": str(e),
            }

    async def get_security_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """Get security dashboard data."""

        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Get login statistics
            login_stats = await self._get_login_statistics(start_date)

            # Get security events
            security_events = await self._get_security_events(start_date)

            # Get top users by activity
            top_users = await self._get_top_users_by_activity(start_date)

            # Get geographic distribution
            geographic_data = await self._get_geographic_distribution(start_date)

            # Get failed login attempts by IP
            failed_logins_by_ip = await self._get_failed_logins_by_ip(start_date)

            return {
                "period_days": days,
                "login_statistics": login_stats,
                "security_events": security_events,
                "top_users": top_users,
                "geographic_distribution": geographic_data,
                "failed_logins_by_ip": failed_logins_by_ip,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating security dashboard: {str(e)}")
            return {
                "error": "Erro ao gerar dashboard de segurança",
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def _analyze_security_patterns(
        self,
        user_id: Optional[UUID],
        action: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        details: Optional[Dict[str, Any]],
    ):
        """Analyze patterns for suspicious activity."""

        if not user_id or not ip_address:
            return

        try:
            # Check for multiple rapid actions
            await self._check_rapid_actions(user_id, action)

            # Check for geographic anomalies
            await self._check_geographic_anomalies(user_id, ip_address)

            # Check for privilege escalation attempts
            await self._check_privilege_escalation(user_id, action, details)

            # Check for suspicious user agent changes
            await self._check_user_agent_changes(user_id, user_agent)

        except Exception as e:
            logger.error(f"Error analyzing security patterns: {str(e)}")

    async def _check_brute_force_attack(self, email: str, ip_address: str):
        """Check for brute force login attacks."""

        try:
            # Check failed attempts in last 15 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)

            # Count failed attempts by email
            email_failures = (
                self.db.query(LoginAttempt)
                .filter(
                    and_(
                        LoginAttempt.email == email,
                        LoginAttempt.success == False,
                        LoginAttempt.attempted_at >= cutoff_time,
                    )
                )
                .count()
            )

            # Count failed attempts by IP
            ip_failures = (
                self.db.query(LoginAttempt)
                .filter(
                    and_(
                        LoginAttempt.ip_address == ip_address,
                        LoginAttempt.success == False,
                        LoginAttempt.attempted_at >= cutoff_time,
                    )
                )
                .count()
            )

            # Log if suspicious
            if email_failures >= self.max_failed_logins:
                await self.log_user_action(
                    user_id=None,
                    action="BRUTE_FORCE_DETECTED_EMAIL",
                    resource_type="SECURITY",
                    ip_address=ip_address,
                    details={
                        "email": email,
                        "failed_attempts": email_failures,
                        "time_window_minutes": 15,
                    },
                    status="SECURITY_INCIDENT",
                )

            if ip_failures >= self.max_failed_logins:
                await self.log_user_action(
                    user_id=None,
                    action="BRUTE_FORCE_DETECTED_IP",
                    resource_type="SECURITY",
                    ip_address=ip_address,
                    details={"failed_attempts": ip_failures, "time_window_minutes": 15},
                    status="SECURITY_INCIDENT",
                )

        except Exception as e:
            logger.error(f"Error checking brute force attack: {str(e)}")

    async def _check_rapid_actions(self, user_id: UUID, action: str):
        """Check for rapid successive actions."""

        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)

            action_count = (
                self.db.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.action == action,
                        AuditLog.timestamp >= cutoff_time,
                    )
                )
                .count()
            )

            # Threshold depends on action type
            thresholds = {
                "LOGIN_SUCCESS": 3,
                "FILE_DOWNLOAD": 20,
                "API_REQUEST": 100,
                "PASSWORD_CHANGE": 2,
                "MFA_VERIFY": 10,
            }

            threshold = thresholds.get(action, 50)

            if action_count > threshold:
                await self.log_user_action(
                    user_id=user_id,
                    action="RAPID_ACTIONS_DETECTED",
                    resource_type="SECURITY",
                    details={
                        "action_type": action,
                        "count": action_count,
                        "threshold": threshold,
                        "time_window_minutes": 5,
                    },
                    status="SECURITY_WARNING",
                )

        except Exception as e:
            logger.error(f"Error checking rapid actions: {str(e)}")

    async def _check_geographic_anomalies(self, user_id: UUID, ip_address: str):
        """Check for geographic location anomalies."""

        try:
            # Get last known location for user
            last_log = (
                self.db.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.ip_address.isnot(None),
                        AuditLog.ip_address != ip_address,
                    )
                )
                .order_by(desc(AuditLog.timestamp))
                .first()
            )

            if last_log and last_log.ip_address:
                # In production, use GeoIP service to calculate distance
                # For now, just check if IP is completely different
                if not self._are_ips_similar(last_log.ip_address, ip_address):
                    time_diff = datetime.utcnow() - last_log.timestamp

                    # If location changed very quickly, it's suspicious
                    if time_diff < timedelta(hours=1):
                        await self.log_user_action(
                            user_id=user_id,
                            action="GEOGRAPHIC_ANOMALY_DETECTED",
                            resource_type="SECURITY",
                            ip_address=ip_address,
                            details={
                                "previous_ip": last_log.ip_address,
                                "current_ip": ip_address,
                                "time_difference_minutes": int(
                                    time_diff.total_seconds() / 60
                                ),
                                "previous_timestamp": last_log.timestamp.isoformat(),
                            },
                            status="SECURITY_WARNING",
                        )

        except Exception as e:
            logger.error(f"Error checking geographic anomalies: {str(e)}")

    async def _check_privilege_escalation(
        self, user_id: UUID, action: str, details: Optional[Dict[str, Any]]
    ):
        """Check for privilege escalation attempts."""

        try:
            # Define privilege escalation indicators
            escalation_actions = [
                "USER_ROLE_CHANGED",
                "PERMISSION_GRANTED",
                "ADMIN_ACCESS_ATTEMPTED",
                "SYSTEM_CONFIG_CHANGED",
            ]

            if action in escalation_actions:
                # Get user's current role
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    await self.log_user_action(
                        user_id=user_id,
                        action="PRIVILEGE_ESCALATION_ATTEMPT",
                        resource_type="SECURITY",
                        details={
                            "attempted_action": action,
                            "user_role": user.role.value,
                            "action_details": details,
                        },
                        status="SECURITY_WARNING",
                    )

        except Exception as e:
            logger.error(f"Error checking privilege escalation: {str(e)}")

    async def _check_user_agent_changes(self, user_id: UUID, user_agent: Optional[str]):
        """Check for suspicious user agent changes."""

        if not user_agent:
            return

        try:
            # Get recent user agent for this user
            recent_log = (
                self.db.query(AuditLog)
                .filter(
                    and_(AuditLog.user_id == user_id, AuditLog.user_agent.isnot(None))
                )
                .order_by(desc(AuditLog.timestamp))
                .first()
            )

            if recent_log and recent_log.user_agent:
                if recent_log.user_agent != user_agent:
                    # Check if change is suspicious (automated tools, etc.)
                    suspicious_agents = [
                        "bot",
                        "crawler",
                        "spider",
                        "scraper",
                        "automated",
                        "curl",
                        "wget",
                        "python",
                        "java",
                        "go-http",
                    ]

                    is_suspicious = any(
                        agent in user_agent.lower() for agent in suspicious_agents
                    )

                    if is_suspicious:
                        await self.log_user_action(
                            user_id=user_id,
                            action="SUSPICIOUS_USER_AGENT",
                            resource_type="SECURITY",
                            user_agent=user_agent,
                            details={
                                "previous_user_agent": recent_log.user_agent,
                                "current_user_agent": user_agent,
                                "suspicious_indicators": [
                                    agent
                                    for agent in suspicious_agents
                                    if agent in user_agent.lower()
                                ],
                            },
                            status="SECURITY_WARNING",
                        )

        except Exception as e:
            logger.error(f"Error checking user agent changes: {str(e)}")

    def _are_ips_similar(self, ip1: str, ip2: str) -> bool:
        """Check if two IPs are similar (same subnet)."""
        try:
            # Simple check for same first 3 octets (Class C subnet)
            parts1 = ip1.split(".")
            parts2 = ip2.split(".")

            if len(parts1) == 4 and len(parts2) == 4:
                return parts1[:3] == parts2[:3]

            return False
        except:
            return False

    async def _get_login_statistics(self, start_date: datetime) -> Dict[str, Any]:
        """Get login statistics for dashboard."""

        total_attempts = (
            self.db.query(LoginAttempt)
            .filter(LoginAttempt.attempted_at >= start_date)
            .count()
        )

        successful_logins = (
            self.db.query(LoginAttempt)
            .filter(
                and_(
                    LoginAttempt.attempted_at >= start_date,
                    LoginAttempt.success == True,
                )
            )
            .count()
        )

        failed_logins = total_attempts - successful_logins

        return {
            "total_attempts": total_attempts,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round(
                (successful_logins / total_attempts * 100) if total_attempts > 0 else 0,
                2,
            ),
        }

    async def _get_security_events(self, start_date: datetime) -> List[Dict[str, Any]]:
        """Get recent security events."""

        security_actions = [
            "BRUTE_FORCE_DETECTED_%",
            "SUSPICIOUS_%",
            "TOKEN_REUSE_ATTACK",
            "GEOGRAPHIC_ANOMALY_%",
            "PRIVILEGE_ESCALATION_%",
        ]

        events = []
        for action_pattern in security_actions:
            event_logs = (
                self.db.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.action.like(action_pattern),
                    )
                )
                .order_by(desc(AuditLog.timestamp))
                .limit(10)
                .all()
            )

            for log in event_logs:
                events.append(
                    {
                        "action": log.action,
                        "timestamp": log.timestamp.isoformat(),
                        "severity": self.severity_levels.get(log.action, "INFO"),
                        "ip_address": log.ip_address,
                        "details": log.details,
                    }
                )

        # Sort by timestamp and return latest
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:20]

    async def _get_top_users_by_activity(
        self, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get most active users."""

        result = (
            self.db.query(
                AuditLog.user_id, func.count(AuditLog.id).label("activity_count")
            )
            .filter(
                and_(AuditLog.timestamp >= start_date, AuditLog.user_id.isnot(None))
            )
            .group_by(AuditLog.user_id)
            .order_by(desc("activity_count"))
            .limit(10)
            .all()
        )

        top_users = []
        for user_id, count in result:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                top_users.append(
                    {
                        "user_id": str(user_id),
                        "user_name": user.full_name,
                        "activity_count": count,
                    }
                )

        return top_users

    async def _get_geographic_distribution(
        self, start_date: datetime
    ) -> Dict[str, int]:
        """Get geographic distribution of access."""

        # Simple IP-based distribution (in production, use GeoIP)
        result = (
            self.db.query(AuditLog.ip_address, func.count(AuditLog.id).label("count"))
            .filter(
                and_(AuditLog.timestamp >= start_date, AuditLog.ip_address.isnot(None))
            )
            .group_by(AuditLog.ip_address)
            .all()
        )

        distribution = {}
        for ip, count in result:
            # Simple classification
            if (
                ip.startswith("127.")
                or ip.startswith("192.168.")
                or ip.startswith("10.")
            ):
                location = "Local/Internal"
            else:
                location = "External"

            distribution[location] = distribution.get(location, 0) + count

        return distribution

    async def _get_failed_logins_by_ip(
        self, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get failed login attempts by IP address."""

        result = (
            self.db.query(
                LoginAttempt.ip_address,
                func.count(LoginAttempt.id).label("failed_count"),
            )
            .filter(
                and_(
                    LoginAttempt.attempted_at >= start_date,
                    LoginAttempt.success == False,
                )
            )
            .group_by(LoginAttempt.ip_address)
            .order_by(desc("failed_count"))
            .limit(10)
            .all()
        )

        failed_logins = []
        for ip, count in result:
            failed_logins.append({"ip_address": ip, "failed_count": count})

        return failed_logins

    async def _export_to_siem(self, audit_log: AuditLog):
        """Export audit log to external SIEM system."""

        # In production, integrate with SIEM tools like Splunk, ELK, etc.
        # For now, just log critical events
        severity = self.severity_levels.get(audit_log.action, "INFO")

        if severity in ["HIGH", "CRITICAL"]:
            logger.warning(
                f"SECURITY_EVENT: {audit_log.action} - User: {audit_log.user_id} - IP: {audit_log.ip_address}"
            )

    async def export_compliance_report(
        self, start_date: datetime, end_date: datetime, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Export compliance report for auditing purposes."""

        try:
            # Get all audit logs in period
            logs = (
                self.db.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date
                    )
                )
                .order_by(AuditLog.timestamp)
                .all()
            )

            # Generate report data
            report_data = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "total_events": len(logs),
                    "unique_users": len(
                        set(log.user_id for log in logs if log.user_id)
                    ),
                    "security_incidents": len(
                        [log for log in logs if "SECURITY" in log.status]
                    ),
                },
                "events": [],
            }

            for log in logs:
                report_data["events"].append(
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "user_id": str(log.user_id) if log.user_id else None,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "ip_address": log.ip_address,
                        "status": log.status,
                        "details": log.details,
                    }
                )

            return report_data

        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return {
                "error": "Erro ao gerar relatório de compliance",
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }
