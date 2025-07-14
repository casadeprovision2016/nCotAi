"""
Audit and compliance tests for COTAI backend.
Tests for audit logs, data integrity, compliance reporting, and immutable trails.
"""
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, AuditLog, LoginAttempt
from app.models.tender import Tender
from app.models.quotation import Quotation
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    TenderFactory,
    QuotationFactory,
    AuditLogFactory,
    LoginAttemptFactory,
    FailedLoginAttemptFactory,
)


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.asyncio
class TestAuditLogging:
    """Test audit logging functionality."""

    async def test_audit_log_creation_on_user_action(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test audit log creation on user actions."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Update tender to trigger audit log
        update_data = {"title": "Updated Tender Title"}
        
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check if audit log was created
        audit_response = await async_client.get(
            "/api/v1/audit/logs",
            params={"resource": "tender", "resource_id": str(tender.id)},
            headers=authenticated_headers
        )
        
        assert audit_response.status_code == status.HTTP_200_OK
        audit_data = audit_response.json()
        assert len(audit_data["items"]) > 0
        assert audit_data["items"][0]["action"] == "update"
        assert audit_data["items"][0]["resource"] == "tender"

    async def test_audit_log_immutability(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log immutability."""
        audit_log = AuditLogFactory()
        async_db_session.add(audit_log)
        await async_db_session.commit()
        
        # Try to update audit log (should fail)
        update_data = {"action": "modified_action"}
        
        response = await async_client.put(
            f"/api/v1/audit/logs/{audit_log.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        error_data = response.json()
        assert "audit logs are immutable" in error_data["detail"].lower()

    async def test_audit_log_data_integrity(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test audit log data integrity and completeness."""
        # Create multiple audit logs
        audit_logs = [AuditLogFactory() for _ in range(5)]
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/logs",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify all required fields are present
        for log_data in data["items"]:
            assert "id" in log_data
            assert "user_id" in log_data
            assert "action" in log_data
            assert "resource" in log_data
            assert "timestamp" in log_data
            assert "ip_address" in log_data
            assert "user_agent" in log_data
            assert "old_values" in log_data
            assert "new_values" in log_data

    async def test_audit_log_digital_signature(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test audit log digital signature verification."""
        audit_log = AuditLogFactory()
        async_db_session.add(audit_log)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/audit/logs/{audit_log.id}/verify-signature",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["signature_valid"] == True
        assert "signature_algorithm" in data
        assert "signed_at" in data
        assert "hash" in data

    async def test_audit_log_chain_integrity(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log chain integrity verification."""
        # Create a chain of audit logs
        audit_logs = [AuditLogFactory() for _ in range(10)]
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/verify-chain",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["chain_valid"] == True
        assert data["total_logs"] == 10
        assert data["broken_links"] == 0
        assert "last_verified" in data

    async def test_audit_log_filtering_by_user(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log filtering by user."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        audit_log1 = AuditLogFactory(user=user1, action="create")
        audit_log2 = AuditLogFactory(user=user2, action="update")
        audit_log3 = AuditLogFactory(user=user1, action="delete")
        
        async_db_session.add_all([user1, user2, audit_log1, audit_log2, audit_log3])
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/logs",
            params={"user_id": str(user1.id)},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        for log in data["items"]:
            assert log["user_id"] == str(user1.id)

    async def test_audit_log_filtering_by_timeframe(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log filtering by timeframe."""
        # Create audit logs with different timestamps
        now = datetime.utcnow()
        old_log = AuditLogFactory(timestamp=now - timedelta(days=10))
        recent_log = AuditLogFactory(timestamp=now - timedelta(hours=1))
        
        async_db_session.add_all([old_log, recent_log])
        await async_db_session.commit()
        
        # Filter for last 24 hours
        start_time = (now - timedelta(days=1)).isoformat()
        end_time = now.isoformat()
        
        response = await async_client.get(
            "/api/v1/audit/logs",
            params={"start_time": start_time, "end_time": end_time},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(recent_log.id)

    async def test_audit_log_sensitive_data_protection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test sensitive data protection in audit logs."""
        # Create audit log with sensitive data
        audit_log = AuditLogFactory(
            action="update",
            resource="user",
            old_values={"password": "old_password", "name": "John"},
            new_values={"password": "new_password", "name": "Jane"}
        )
        async_db_session.add(audit_log)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/audit/logs/{audit_log.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Sensitive fields should be masked or excluded
        assert "password" not in data["old_values"]
        assert "password" not in data["new_values"]
        assert data["old_values"]["name"] == "John"
        assert data["new_values"]["name"] == "Jane"

    async def test_audit_log_bulk_export(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk audit log export for compliance."""
        # Create multiple audit logs
        audit_logs = [AuditLogFactory() for _ in range(20)]
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/logs/export",
            params={"format": "csv", "start_date": "2025-01-01", "end_date": "2025-12-31"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"
        
        # Check CSV content
        csv_content = response.text
        lines = csv_content.split('\n')
        assert len(lines) > 20  # Header + data rows
        assert "id,user_id,action,resource" in lines[0]  # CSV header


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.asyncio
class TestLoginAuditTrail:
    """Test login attempt audit trail."""

    async def test_successful_login_audit(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test audit trail for successful login."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"X-Forwarded-For": "192.168.1.100"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check login attempt record
        audit_response = await async_client.get(
            "/api/v1/audit/login-attempts",
            params={"email": user.email},
            headers={"Authorization": f"Bearer {response.json()['access_token']}"}
        )
        
        assert audit_response.status_code == status.HTTP_200_OK
        audit_data = audit_response.json()
        assert len(audit_data["items"]) > 0
        assert audit_data["items"][0]["success"] == True
        assert audit_data["items"][0]["ip_address"] == "192.168.1.100"

    async def test_failed_login_audit(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test audit trail for failed login attempts."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Multiple failed login attempts
        for i in range(3):
            login_data = {
                "username": user.email,
                "password": "wrong_password"
            }
            
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers={"X-Forwarded-For": f"192.168.1.{100 + i}"}
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Generate admin token to check audit logs
        admin = AdminUserFactory(is_verified=True)
        async_db_session.add(admin)
        await async_db_session.commit()
        
        admin_login = await async_client.post(
            "/api/v1/auth/login",
            data={"username": admin.email, "password": "secret"}
        )
        admin_token = admin_login.json()["access_token"]
        
        # Check failed login attempts
        audit_response = await async_client.get(
            "/api/v1/audit/login-attempts",
            params={"email": user.email, "success": "false"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert audit_response.status_code == status.HTTP_200_OK
        audit_data = audit_response.json()
        assert len(audit_data["items"]) == 3
        
        for attempt in audit_data["items"]:
            assert attempt["success"] == False
            assert attempt["failure_reason"] == "Invalid credentials"

    async def test_suspicious_login_detection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test detection of suspicious login patterns."""
        # Create failed login attempts from multiple IPs
        failed_attempts = [
            FailedLoginAttemptFactory(
                email="target@example.com",
                ip_address=f"192.168.1.{i}",
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            for i in range(1, 11)  # 10 attempts from different IPs
        ]
        
        for attempt in failed_attempts:
            async_db_session.add(attempt)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/suspicious-activities",
            params={"timeframe": "1h"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["suspicious_activities"]) > 0
        
        # Check for brute force detection
        brute_force_activity = next(
            (activity for activity in data["suspicious_activities"] 
             if activity["type"] == "brute_force_attempt"), None
        )
        assert brute_force_activity is not None
        assert brute_force_activity["target_email"] == "target@example.com"
        assert brute_force_activity["attempt_count"] == 10

    async def test_geographic_anomaly_detection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test geographic anomaly detection in login patterns."""
        user = UserFactory()
        
        # Normal login from Brazil
        normal_attempt = LoginAttemptFactory(
            email=user.email,
            ip_address="200.123.45.67",  # Brazilian IP
            success=True,
            timestamp=datetime.utcnow() - timedelta(hours=2)
        )
        
        # Suspicious login from different country shortly after
        suspicious_attempt = LoginAttemptFactory(
            email=user.email,
            ip_address="1.2.3.4",  # Different country IP
            success=True,
            timestamp=datetime.utcnow() - timedelta(minutes=30)
        )
        
        async_db_session.add_all([user, normal_attempt, suspicious_attempt])
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/geographic-anomalies",
            params={"timeframe": "24h"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["anomalies"]) > 0
        
        anomaly = data["anomalies"][0]
        assert anomaly["user_email"] == user.email
        assert anomaly["type"] == "impossible_travel"
        assert "distance" in anomaly
        assert "time_difference" in anomaly


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.asyncio
class TestComplianceReporting:
    """Test compliance reporting functionality."""

    async def test_gdpr_data_export(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test GDPR data export for user."""
        user = UserFactory()
        tender = TenderFactory(created_by=user)
        quotation = QuotationFactory(created_by=user)
        audit_logs = [AuditLogFactory(user=user) for _ in range(5)]
        
        async_db_session.add(user)
        async_db_session.add(tender)
        async_db_session.add(quotation)
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/compliance/gdpr-export/{user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check all user data is included
        assert "user_profile" in data
        assert "tenders" in data
        assert "quotations" in data
        assert "audit_logs" in data
        assert "login_attempts" in data
        
        assert data["user_profile"]["id"] == str(user.id)
        assert len(data["tenders"]) == 1
        assert len(data["quotations"]) == 1
        assert len(data["audit_logs"]) == 5

    async def test_gdpr_data_deletion(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test GDPR data deletion (right to be forgotten)."""
        user = UserFactory()
        tender = TenderFactory(created_by=user)
        quotation = QuotationFactory(created_by=user)
        
        async_db_session.add_all([user, tender, quotation])
        await async_db_session.commit()
        
        deletion_request = {
            "user_id": str(user.id),
            "reason": "User requested data deletion",
            "delete_related_data": True,
            "anonymize_audit_logs": True
        }
        
        response = await async_client.post(
            "/api/v1/compliance/gdpr-delete",
            json=deletion_request,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deletion_successful"] == True
        assert data["anonymized_records"] > 0
        assert "deletion_certificate" in data

    async def test_compliance_audit_report(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test compliance audit report generation."""
        # Create various audit data
        users = [UserFactory() for _ in range(10)]
        audit_logs = [AuditLogFactory() for _ in range(50)]
        login_attempts = [LoginAttemptFactory() for _ in range(30)]
        
        for user in users:
            async_db_session.add(user)
        for log in audit_logs:
            async_db_session.add(log)
        for attempt in login_attempts:
            async_db_session.add(attempt)
        await async_db_session.commit()
        
        report_params = {
            "report_type": "comprehensive",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "include_user_activity": True,
            "include_security_events": True,
            "include_data_access": True
        }
        
        response = await async_client.get(
            "/api/v1/compliance/audit-report",
            params=report_params,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "report_summary" in data
        assert "user_activity_summary" in data
        assert "security_events_summary" in data
        assert "data_access_summary" in data
        assert "compliance_score" in data
        assert "recommendations" in data

    async def test_regulatory_compliance_check(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test regulatory compliance check."""
        response = await async_client.get(
            "/api/v1/compliance/regulatory-check",
            params={"regulations": "lgpd,gdpr,sox"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "compliance_status" in data
        assert "lgpd" in data["compliance_status"]
        assert "gdpr" in data["compliance_status"]
        assert "sox" in data["compliance_status"]
        
        for regulation, status in data["compliance_status"].items():
            assert "compliant" in status
            assert "score" in status
            assert "violations" in status
            assert "recommendations" in status

    async def test_data_retention_policy_check(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test data retention policy compliance check."""
        # Create old data that should be flagged for retention policy
        old_user = UserFactory(created_at=datetime.utcnow() - timedelta(days=2200))  # ~6 years old
        old_audit_log = AuditLogFactory(timestamp=datetime.utcnow() - timedelta(days=2200))
        
        async_db_session.add_all([old_user, old_audit_log])
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/compliance/data-retention-check",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "retention_violations" in data
        assert "expired_data_count" in data
        assert "recommendations" in data
        assert data["expired_data_count"] > 0

    async def test_data_classification_report(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test data classification and sensitivity report."""
        response = await async_client.get(
            "/api/v1/compliance/data-classification",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "data_categories" in data
        assert "sensitivity_levels" in data
        assert "encryption_status" in data
        assert "access_controls" in data
        
        # Check data categories
        categories = data["data_categories"]
        assert "personal_data" in categories
        assert "financial_data" in categories
        assert "business_data" in categories
        
        # Check sensitivity levels
        sensitivity = data["sensitivity_levels"]
        assert "public" in sensitivity
        assert "internal" in sensitivity
        assert "confidential" in sensitivity
        assert "restricted" in sensitivity


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.asyncio
class TestDataIntegrity:
    """Test data integrity and verification."""

    async def test_database_integrity_check(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test database integrity verification."""
        response = await async_client.get(
            "/api/v1/audit/database-integrity",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "integrity_status" in data
        assert "tables_checked" in data
        assert "orphaned_records" in data
        assert "constraint_violations" in data
        assert "checksum_verification" in data
        
        assert data["integrity_status"] in ["healthy", "warning", "critical"]
        assert isinstance(data["tables_checked"], int)
        assert isinstance(data["orphaned_records"], int)

    async def test_audit_log_hash_verification(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log hash chain verification."""
        # Create a sequence of audit logs
        audit_logs = []
        for i in range(5):
            log = AuditLogFactory(
                action=f"action_{i}",
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            audit_logs.append(log)
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/verify-hashes",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "hash_verification_status" in data
        assert "total_logs_verified" in data
        assert "hash_mismatches" in data
        assert "chain_breaks" in data
        
        assert data["hash_verification_status"] == "valid"
        assert data["total_logs_verified"] == 5
        assert data["hash_mismatches"] == 0
        assert data["chain_breaks"] == 0

    async def test_backup_integrity_verification(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test backup integrity verification."""
        response = await async_client.get(
            "/api/v1/audit/backup-integrity",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "backup_status" in data
        assert "last_backup" in data
        assert "backup_size" in data
        assert "integrity_check" in data
        assert "restoration_test" in data
        
        assert data["backup_status"] in ["healthy", "outdated", "corrupted", "missing"]
        assert "checksum" in data["integrity_check"]

    async def test_encryption_compliance_check(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test encryption compliance verification."""
        response = await async_client.get(
            "/api/v1/audit/encryption-compliance",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "encryption_status" in data
        assert "encrypted_fields" in data
        assert "unencrypted_sensitive_data" in data
        assert "encryption_algorithms" in data
        assert "key_rotation_status" in data
        
        # Check that sensitive fields are encrypted
        encrypted_fields = data["encrypted_fields"]
        assert "user.hashed_password" in encrypted_fields
        assert "user.mfa_secret" in encrypted_fields


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.asyncio
class TestSecurityEventTracking:
    """Test security event tracking and monitoring."""

    async def test_privilege_escalation_detection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test privilege escalation detection."""
        user = UserFactory(role="USER")
        
        # Simulate privilege escalation
        escalation_log = AuditLogFactory(
            user=user,
            action="role_change",
            resource="user",
            old_values={"role": "USER"},
            new_values={"role": "ADMIN"}
        )
        
        async_db_session.add_all([user, escalation_log])
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/security-events",
            params={"event_type": "privilege_escalation"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["security_events"]) > 0
        event = data["security_events"][0]
        assert event["event_type"] == "privilege_escalation"
        assert event["severity"] == "high"
        assert event["user_id"] == str(user.id)

    async def test_unauthorized_access_detection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test unauthorized access attempt detection."""
        # Create audit logs for unauthorized access attempts
        unauthorized_attempts = [
            AuditLogFactory(
                action="access_denied",
                resource="sensitive_data",
                old_values={"reason": "insufficient_permissions"},
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            for i in range(5)
        ]
        
        for attempt in unauthorized_attempts:
            async_db_session.add(attempt)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/security-events",
            params={"event_type": "unauthorized_access", "timeframe": "1h"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["security_events"]) == 5
        for event in data["security_events"]:
            assert event["event_type"] == "unauthorized_access"
            assert event["resource"] == "sensitive_data"

    async def test_data_exfiltration_monitoring(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test data exfiltration monitoring."""
        user = UserFactory()
        
        # Simulate suspicious data access pattern
        bulk_access_logs = [
            AuditLogFactory(
                user=user,
                action="bulk_export",
                resource="tender",
                new_values={"exported_count": 100, "file_size": "50MB"},
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            for i in range(3)  # Multiple bulk exports in short time
        ]
        
        for log in bulk_access_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/data-exfiltration-alerts",
            params={"timeframe": "1h"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["alerts"]) > 0
        alert = data["alerts"][0]
        assert alert["alert_type"] == "suspicious_bulk_export"
        assert alert["user_id"] == str(user.id)
        assert alert["severity"] == "medium"

    async def test_system_configuration_changes(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test system configuration change tracking."""
        admin_user = AdminUserFactory()
        
        # Log system configuration changes
        config_changes = [
            AuditLogFactory(
                user=admin_user,
                action="config_change",
                resource="system_settings",
                old_values={"security_level": "medium"},
                new_values={"security_level": "high"}
            ),
            AuditLogFactory(
                user=admin_user,
                action="config_change",
                resource="backup_settings",
                old_values={"retention_days": 30},
                new_values={"retention_days": 90}
            )
        ]
        
        for change in config_changes:
            async_db_session.add(change)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/audit/configuration-changes",
            params={"timeframe": "24h"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["configuration_changes"]) == 2
        for change in data["configuration_changes"]:
            assert change["action"] == "config_change"
            assert change["user_id"] == str(admin_user.id)
            assert "old_values" in change
            assert "new_values" in change


@pytest.mark.audit
@pytest.mark.compliance
@pytest.mark.performance
@pytest.mark.asyncio
class TestAuditPerformance:
    """Test audit system performance."""

    async def test_audit_log_query_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit log query performance with large dataset."""
        # Create many audit logs
        audit_logs = [AuditLogFactory() for _ in range(1000)]
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/audit/logs",
            params={"page": 1, "size": 50},
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 2.0  # Should complete within 2 seconds
        
        data = response.json()
        assert len(data["items"]) == 50
        assert data["total"] == 1000

    async def test_audit_search_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test audit search performance."""
        # Create audit logs with searchable content
        audit_logs = [
            AuditLogFactory(
                action=f"action_{i % 10}",
                resource=f"resource_{i % 5}"
            )
            for i in range(500)
        ]
        for log in audit_logs:
            async_db_session.add(log)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/audit/logs",
            params={"search": "action_1", "page": 1, "size": 20},
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 1.5  # Should complete within 1.5 seconds

    async def test_bulk_audit_log_processing(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk audit log processing performance."""
        import time
        
        start_time = time.time()
        
        # Simulate bulk operations that generate many audit logs
        for i in range(100):
            tender = TenderFactory()
            async_db_session.add(tender)
        
        await async_db_session.commit()
        end_time = time.time()
        
        # Bulk operations should complete efficiently
        assert end_time - start_time < 5.0  # Should complete within 5 seconds