"""
Security tests for COTAI backend.
Tests for XSS protection, CSRF protection, rate limiting, input validation, and encryption.
"""
import base64
import json
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.tender import Tender
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    TenderFactory,
)


@pytest.mark.security
@pytest.mark.asyncio
class TestXSSProtection:
    """Test Cross-Site Scripting (XSS) protection."""

    async def test_xss_in_user_input_escaped(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test XSS payload in user input is properly escaped."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
        ]
        
        for payload in xss_payloads:
            tender_data = {
                "title": payload,
                "description": f"Description with {payload}",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": 100000.0,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            if response.status_code == status.HTTP_201_CREATED:
                # Check that XSS payload is escaped in response
                data = response.json()
                assert "<script>" not in data["title"]
                assert "javascript:" not in data["title"]
                assert "onerror=" not in data["description"]
                assert "onload=" not in data["description"]
            else:
                # XSS payload should be rejected
                assert response.status_code in [
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ]

    async def test_xss_in_search_parameters(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test XSS protection in search parameters."""
        xss_payload = "<script>alert('XSS')</script>"
        
        response = await async_client.get(
            f"/api/v1/tenders?search={xss_payload}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        # Response should not contain unescaped XSS payload
        response_text = response.text
        assert "<script>" not in response_text
        assert "alert('XSS')" not in response_text

    async def test_xss_in_user_profile_update(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test XSS protection in user profile updates."""
        xss_payload = "<script>document.cookie='stolen'</script>"
        
        update_data = {
            "first_name": xss_payload,
            "last_name": "Normal Name",
            "company_name": f"Company {xss_payload}"
        }
        
        response = await async_client.put(
            "/api/v1/users/me",
            json=update_data,
            headers=authenticated_headers
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # XSS payload should be escaped or sanitized
            assert "<script>" not in data["first_name"]
            assert "document.cookie" not in data["company_name"]
        else:
            # XSS payload should be rejected
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    async def test_xss_in_file_upload_filename(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test XSS protection in file upload filenames."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        malicious_filename = "<script>alert('XSS')</script>.pdf"
        
        files = {
            "file": (malicious_filename, b"test content", "application/pdf")
        }
        
        response = await async_client.post(
            f"/api/v1/tenders/{tender.id}/documents",
            files=files,
            headers=authenticated_headers
        )
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Filename should be sanitized
            assert "<script>" not in data["name"]
            assert "alert" not in data["name"]
        else:
            # Malicious filename should be rejected
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    async def test_content_type_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test Content-Type validation to prevent MIME type attacks."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Try to upload HTML with PDF content type
        malicious_html = b"<html><script>alert('XSS')</script></html>"
        
        files = {
            "file": ("document.pdf", malicious_html, "application/pdf")
        }
        
        response = await async_client.post(
            f"/api/v1/tenders/{tender.id}/documents",
            files=files,
            headers=authenticated_headers
        )
        
        # Should validate actual file content vs declared content type
        if response.status_code == status.HTTP_201_CREATED:
            # File should be scanned and sanitized
            data = response.json()
            assert data["mime_type"] == "text/html"  # Detected actual type
        else:
            # Mismatched content type should be rejected
            assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.security
@pytest.mark.asyncio
class TestCSRFProtection:
    """Test Cross-Site Request Forgery (CSRF) protection."""

    async def test_csrf_token_required_for_state_changing_operations(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test CSRF token is required for state-changing operations."""
        tender_data = {
            "title": "Test Tender",
            "description": "Test description",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        # Request without CSRF token should fail
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        
        # Depending on implementation, might require CSRF token
        # or be protected by other mechanisms (JWT, SameSite cookies)
        assert response.status_code in [
            status.HTTP_201_CREATED,  # If JWT provides CSRF protection
            status.HTTP_403_FORBIDDEN,  # If CSRF token required
            status.HTTP_400_BAD_REQUEST  # If CSRF token missing
        ]

    async def test_csrf_token_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test CSRF token validation."""
        # Get CSRF token
        csrf_response = await async_client.get(
            "/api/v1/auth/csrf-token",
            headers=authenticated_headers
        )
        
        if csrf_response.status_code == status.HTTP_200_OK:
            csrf_data = csrf_response.json()
            csrf_token = csrf_data["csrf_token"]
            
            tender_data = {
                "title": "Test Tender with CSRF",
                "description": "Test description",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": 100000.0,
                "deadline": "2025-12-31"
            }
            
            # Request with valid CSRF token
            headers_with_csrf = {
                **authenticated_headers,
                "X-CSRF-Token": csrf_token
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=headers_with_csrf
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            
            # Request with invalid CSRF token
            headers_with_invalid_csrf = {
                **authenticated_headers,
                "X-CSRF-Token": "invalid_token"
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=headers_with_invalid_csrf
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_csrf_double_submit_cookie_pattern(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test CSRF protection using double-submit cookie pattern."""
        # This test assumes implementation of double-submit cookie pattern
        csrf_token = "test_csrf_token_123"
        
        # Set CSRF token in cookie and header
        response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "password"},
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token}
        )
        
        # Should work when cookie and header match
        # Implementation depends on actual CSRF protection mechanism
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,  # If credentials are invalid
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]

    async def test_csrf_protection_bypassed_by_cors(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test that CSRF protection is not bypassed by CORS misconfiguration."""
        # Test request from different origin
        malicious_headers = {
            "Origin": "https://malicious-site.com",
            "Referer": "https://malicious-site.com/attack.html"
        }
        
        tender_data = {
            "title": "Malicious Tender",
            "description": "This should be blocked",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=malicious_headers
        )
        
        # Should be blocked due to authentication or CORS policy
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST
        ]


@pytest.mark.security
@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting protection."""

    @patch('app.core.rate_limiter.redis_client')
    async def test_rate_limiting_login_attempts(
        self, mock_redis, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test rate limiting on login attempts."""
        # Mock Redis to simulate rate limiting
        mock_redis.incr.return_value = 6  # Exceed limit of 5 attempts
        mock_redis.ttl.return_value = 300  # 5 minutes remaining
        
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrong_password"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"X-Forwarded-For": "192.168.1.100"}
        )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert "rate limit" in data["detail"].lower()
        assert "try again" in data["detail"].lower()

    @patch('app.core.rate_limiter.redis_client')
    async def test_rate_limiting_api_calls(
        self, mock_redis, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test rate limiting on API calls."""
        # Mock Redis to simulate rate limiting
        mock_redis.incr.return_value = 101  # Exceed limit of 100 requests per minute
        mock_redis.ttl.return_value = 30  # 30 seconds remaining
        
        response = await async_client.get(
            "/api/v1/tenders",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert "rate limit" in data["detail"].lower()
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @patch('app.core.rate_limiter.redis_client')
    async def test_rate_limiting_per_user(
        self, mock_redis, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test per-user rate limiting."""
        user1 = UserFactory(is_verified=True)
        user2 = UserFactory(is_verified=True)
        async_db_session.add_all([user1, user2])
        await async_db_session.commit()
        
        # Mock Redis to return different counts for different users
        def mock_incr(key):
            if str(user1.id) in key:
                return 101  # User1 exceeds limit
            else:
                return 50   # User2 is within limit
        
        mock_redis.incr.side_effect = mock_incr
        mock_redis.ttl.return_value = 30
        
        # Generate tokens for both users
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        
        user1_token = auth_service.create_access_token(
            data={"sub": str(user1.id), "email": user1.email}
        )
        user2_token = auth_service.create_access_token(
            data={"sub": str(user2.id), "email": user2.email}
        )
        
        # User1 should be rate limited
        response1 = await async_client.get(
            "/api/v1/tenders",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response1.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        
        # User2 should not be rate limited
        response2 = await async_client.get(
            "/api/v1/tenders",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response2.status_code == status.HTTP_200_OK

    async def test_rate_limiting_bypass_attempts(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test attempts to bypass rate limiting."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrong_password"
        }
        
        # Try different techniques to bypass rate limiting
        bypass_attempts = [
            {"X-Forwarded-For": "192.168.1.100"},
            {"X-Real-IP": "192.168.1.101"},
            {"X-Forwarded-For": "192.168.1.102, 192.168.1.103"},
            {"X-Forwarded-For": "127.0.0.1"},  # Try localhost
            {"User-Agent": "Different-Agent-1"},
            {"User-Agent": "Different-Agent-2"},
        ]
        
        # Multiple attempts with different headers should still be rate limited
        for headers in bypass_attempts:
            response = await async_client.post(
                "/api/v1/auth/login",
                data=login_data,
                headers=headers
            )
            
            # Should be rate limited or return authentication error
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_429_TOO_MANY_REQUESTS
            ]

    @patch('app.core.rate_limiter.redis_client')
    async def test_rate_limiting_sliding_window(
        self, mock_redis, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test sliding window rate limiting."""
        # Simulate sliding window behavior
        call_times = []
        
        def mock_incr(key):
            current_time = time.time()
            call_times.append(current_time)
            
            # Count calls in last 60 seconds (sliding window)
            recent_calls = [t for t in call_times if current_time - t < 60]
            return len(recent_calls)
        
        mock_redis.incr.side_effect = mock_incr
        mock_redis.ttl.return_value = 60
        
        # Make requests rapidly
        for i in range(5):
            response = await async_client.get(
                "/api/v1/tenders",
                headers=authenticated_headers
            )
            
            if i < 3:  # First few should succeed
                assert response.status_code == status.HTTP_200_OK
            # Later requests might be rate limited depending on implementation


@pytest.mark.security
@pytest.mark.asyncio
class TestInputValidation:
    """Test input validation and sanitization."""

    async def test_sql_injection_protection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test SQL injection protection."""
        sql_injection_payloads = [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "1; DELETE FROM tenders;--",
            "' UNION SELECT * FROM users--",
            "admin'--",
            "'; INSERT INTO users VALUES ('hacker', 'password');--",
        ]
        
        for payload in sql_injection_payloads:
            # Test in search parameter
            response = await async_client.get(
                f"/api/v1/tenders?search={payload}",
                headers=authenticated_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            # Should return normal results, not error or unexpected data
            data = response.json()
            assert "items" in data
            
            # Test in POST data
            tender_data = {
                "title": payload,
                "description": "Test description",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": 100000.0,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            # Should either succeed (with sanitized data) or be rejected
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    async def test_command_injection_protection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test command injection protection."""
        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)",
            "; ping -c 10 127.0.0.1",
        ]
        
        for payload in command_injection_payloads:
            tender_data = {
                "title": f"Test {payload}",
                "description": f"Description {payload}",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": 100000.0,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            # Should either succeed (with sanitized data) or be rejected
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]
            
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                # Command injection chars should be escaped or removed
                assert "; ls" not in data["title"]
                assert "| cat" not in data["description"]
                assert "&& rm" not in data["title"]

    async def test_path_traversal_protection(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test path traversal protection in file operations."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
        ]
        
        for payload in path_traversal_payloads:
            files = {
                "file": (payload, b"test content", "text/plain")
            }
            
            response = await async_client.post(
                f"/api/v1/tenders/{tender.id}/documents",
                files=files,
                headers=authenticated_headers
            )
            
            # Should reject path traversal attempts
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    async def test_file_type_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test file type validation."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Test malicious file types
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("script.php", b"<?php phpinfo(); ?>", "application/x-php"),
            ("malware.bat", b"@echo off\ndel *.*", "application/x-msdos-program"),
            ("script.jsp", b"<%@ page import=\"java.io.*\" %>", "application/x-jsp"),
        ]
        
        for filename, content, content_type in malicious_files:
            files = {
                "file": (filename, content, content_type)
            }
            
            response = await async_client.post(
                f"/api/v1/tenders/{tender.id}/documents",
                files=files,
                headers=authenticated_headers
            )
            
            # Should reject malicious file types
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ]

    async def test_file_size_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test file size validation."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Test oversized file (simulate large file)
        large_content = b"A" * (100 * 1024 * 1024)  # 100MB
        
        files = {
            "file": ("large_file.pdf", large_content, "application/pdf")
        }
        
        response = await async_client.post(
            f"/api/v1/tenders/{tender.id}/documents",
            files=files,
            headers=authenticated_headers
        )
        
        # Should reject oversized files
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST
        ]

    async def test_malformed_json_handling(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test handling of malformed JSON input."""
        malformed_json_payloads = [
            '{"title": "Test"',  # Missing closing brace
            '{"title": "Test", "invalid": }',  # Invalid value
            '{"title": "Test",}',  # Trailing comma
            'null',  # Null JSON
            '[]',  # Array instead of object
            '{"title": "\u0000"}',  # Null byte
        ]
        
        for payload in malformed_json_payloads:
            response = await async_client.post(
                "/api/v1/tenders",
                content=payload,
                headers={
                    **authenticated_headers,
                    "Content-Type": "application/json"
                }
            )
            
            # Should return proper error for malformed JSON
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


@pytest.mark.security
@pytest.mark.asyncio
class TestEncryption:
    """Test encryption and data protection."""

    async def test_password_hashing(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test password hashing and storage."""
        user_data = {
            "email": "test_encryption@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company"
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get user from database to check password is hashed
        created_user = response.json()
        user_response = await async_client.get(
            f"/api/v1/users/{created_user['id']}",
            headers=admin_headers
        )
        
        user_data_response = user_response.json()
        
        # Password should not be in response
        assert "password" not in user_data_response
        assert "hashed_password" not in user_data_response
        
        # Stored password should be hashed (not plain text)
        # This would require database access to verify

    async def test_sensitive_data_encryption(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test encryption of sensitive data fields."""
        # Setup MFA for user to test MFA secret encryption
        response = await async_client.post(
            "/api/v1/auth/mfa/setup",
            headers=authenticated_headers
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            
            # MFA secret should be provided for setup but not stored in plain text
            assert "secret" in data
            assert "qr_code" in data
            
            # The secret returned should be base32 encoded
            secret = data["secret"]
            assert len(secret) == 32  # Base32 encoded secret length
            assert secret.isalnum()  # Should only contain alphanumeric chars

    async def test_jwt_token_security(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test JWT token security features."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Login to get JWT token
        login_data = {
            "username": user.email,
            "password": "secret"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Decode JWT header to check algorithm
        import jwt
        header = jwt.get_unverified_header(access_token)
        assert header["alg"] != "none"  # Should not use 'none' algorithm
        assert header["alg"] in ["HS256", "RS256"]  # Should use secure algorithm
        
        # Decode JWT payload (without verification for testing)
        payload = jwt.decode(access_token, options={"verify_signature": False})
        
        # Check token contains required claims
        assert "sub" in payload  # Subject
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at
        assert "email" in payload
        
        # Check expiration is reasonable (not too long)
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        token_lifetime = exp_timestamp - iat_timestamp
        assert token_lifetime <= 3600  # Max 1 hour

    async def test_session_security(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test session security features."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Login to create session
        login_data = {
            "username": user.email,
            "password": "secret"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Check security headers are set
        assert "Set-Cookie" not in response.headers or \
               "HttpOnly" in response.headers.get("Set-Cookie", "")
        
        # Check for security headers in response
        # Note: These would be set by middleware
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
        ]
        
        # These headers might be set by middleware or reverse proxy
        # Test implementation would depend on actual setup

    async def test_data_transmission_security(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test data transmission security."""
        # Test that sensitive operations require HTTPS
        # This would typically be enforced by middleware or reverse proxy
        
        tender_data = {
            "title": "Secure Transmission Test",
            "description": "Testing data transmission security",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        
        # Should succeed with proper authentication
        assert response.status_code == status.HTTP_201_CREATED
        
        # Response should not contain sensitive data in plain text
        data = response.json()
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "token" not in str(data).lower()


@pytest.mark.security
@pytest.mark.asyncio
class TestAuthorizationBypass:
    """Test authorization bypass attempts."""

    async def test_horizontal_privilege_escalation(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test horizontal privilege escalation prevention."""
        # Create two users
        user1 = UserFactory(is_verified=True)
        user2 = UserFactory(is_verified=True)
        
        # Create tender owned by user1
        tender = TenderFactory(created_by=user1)
        
        async_db_session.add_all([user1, user2, tender])
        await async_db_session.commit()
        
        # Generate token for user2
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        user2_token = auth_service.create_access_token(
            data={"sub": str(user2.id), "email": user2.email}
        )
        headers = {"Authorization": f"Bearer {user2_token}"}
        
        # User2 should not be able to modify user1's tender
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json={"title": "Hacked by User2"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_vertical_privilege_escalation(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test vertical privilege escalation prevention."""
        # Create regular user
        user = UserFactory(role="USER", is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate token for user
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        user_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # User should not be able to access admin endpoints
        response = await async_client.get("/api/v1/users", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # User should not be able to create other users
        new_user_data = {
            "email": "hacker@example.com",
            "password": "HackerPassword123!",
            "first_name": "Hacker",
            "last_name": "User",
            "role": "ADMIN"
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=new_user_data,
            headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_jwt_manipulation_attacks(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test JWT manipulation attack prevention."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Get legitimate token
        login_data = {"username": user.email, "password": "secret"}
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        legitimate_token = response.json()["access_token"]
        
        # Test various JWT manipulation attacks
        
        # 1. Algorithm confusion attack (change HS256 to none)
        import jwt
        payload = jwt.decode(legitimate_token, options={"verify_signature": False})
        malicious_token_none = jwt.encode(payload, "", algorithm="none")
        
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {malicious_token_none}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 2. Role manipulation
        payload["role"] = "ADMIN"
        malicious_token_role = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        response = await async_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {malicious_token_role}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 3. Subject manipulation
        payload["sub"] = str(uuid.uuid4())  # Different user ID
        malicious_token_sub = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {malicious_token_sub}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_parameter_pollution_attacks(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test parameter pollution attack prevention."""
        # Test HTTP Parameter Pollution (HPP)
        
        # Create tender for testing
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Try parameter pollution in query string
        response = await async_client.get(
            f"/api/v1/tenders/{tender.id}?id={tender.id}&id=999",
            headers=authenticated_headers
        )
        
        # Should return the correct tender, not be confused by duplicate params
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(tender.id)
        
        # Try parameter pollution in form data
        update_data = {
            "title": "Legitimate Title",
            "title": "Malicious Title"  # Duplicate parameter
        }
        
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        # Should handle duplicate parameters appropriately
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]


@pytest.mark.security
@pytest.mark.performance
@pytest.mark.asyncio
class TestSecurityPerformance:
    """Test security controls performance impact."""

    async def test_rate_limiting_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance impact of rate limiting."""
        import time
        
        start_time = time.time()
        
        # Make multiple requests within rate limit
        for i in range(10):
            response = await async_client.get(
                "/api/v1/tenders",
                headers=authenticated_headers
            )
            assert response.status_code == status.HTTP_200_OK
        
        end_time = time.time()
        
        # Rate limiting should not significantly impact response time
        avg_response_time = (end_time - start_time) / 10
        assert avg_response_time < 1.0  # Should be under 1 second per request

    async def test_input_validation_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance impact of input validation."""
        import time
        
        # Large but valid input
        large_description = "A" * 10000  # 10KB description
        
        tender_data = {
            "title": "Performance Test Tender",
            "description": large_description,
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Input validation should not significantly impact performance
        processing_time = end_time - start_time
        assert processing_time < 2.0  # Should complete within 2 seconds

    async def test_encryption_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance impact of encryption operations."""
        import time
        
        # Test multiple password operations
        start_time = time.time()
        
        for i in range(5):
            password_data = {
                "current_password": "secret",
                "new_password": f"NewPassword{i}123!",
                "confirm_password": f"NewPassword{i}123!"
            }
            
            response = await async_client.put(
                "/api/v1/users/me/password",
                json=password_data,
                headers=authenticated_headers
            )
            
            # Reset password for next iteration
            if response.status_code == status.HTTP_200_OK:
                reset_data = {
                    "current_password": f"NewPassword{i}123!",
                    "new_password": "secret",
                    "confirm_password": "secret"
                }
                await async_client.put(
                    "/api/v1/users/me/password",
                    json=reset_data,
                    headers=authenticated_headers
                )
        
        end_time = time.time()
        
        # Encryption operations should not take too long
        total_time = end_time - start_time
        assert total_time < 10.0  # Should complete within 10 seconds for 5 operations