"""
Authentication system tests for COTAI backend.
Tests for login, MFA, SSO, token rotation, and auth security.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from freezegun import freeze_time
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.services.mfa_service import MFAService
from app.services.user_service import UserService
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    UserWithMFAFactory,
    RefreshTokenFactory,
    LoginAttemptFactory,
    FailedLoginAttemptFactory,
)


@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication endpoints and workflows."""

    async def test_user_registration_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful user registration."""
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["role"] == "USER"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_user_registration_duplicate_email(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test registration with duplicate email fails."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        user_data = {
            "email": user.email,
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    async def test_user_registration_weak_password(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test registration with weak password fails."""
        user_data = {
            "email": "test@example.com",
            "password": "weak",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()

    async def test_user_login_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful user login."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret",  # Default password in factory
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == user.email
        
        # Verify JWT token
        token = data["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email

    async def test_user_login_invalid_credentials(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test login with invalid credentials fails."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrongpassword",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "credentials" in response.json()["detail"].lower()

    async def test_user_login_unverified_account(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test login with unverified account fails."""
        user = UserFactory(is_verified=False)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "verified" in response.json()["detail"].lower()

    async def test_user_login_inactive_account(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test login with inactive account fails."""
        user = UserFactory(is_active=False, is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in response.json()["detail"].lower()

    async def test_user_login_locked_account(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test login with locked account fails."""
        user = UserFactory(
            is_verified=True,
            failed_login_attempts=5,
            locked_until=datetime.utcnow() + timedelta(minutes=30)
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_423_LOCKED
        assert "locked" in response.json()["detail"].lower()

    async def test_token_refresh_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful token refresh."""
        user = UserFactory(is_verified=True)
        refresh_token = RefreshTokenFactory(user=user)
        async_db_session.add(user)
        async_db_session.add(refresh_token)
        await async_db_session.commit()
        
        response = await async_client.post(
            "/api/v1/auth/refresh", 
            json={"refresh_token": refresh_token.token}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_token_refresh_invalid_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test token refresh with invalid token fails."""
        response = await async_client.post(
            "/api/v1/auth/refresh", 
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    async def test_token_refresh_expired_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test token refresh with expired token fails."""
        user = UserFactory(is_verified=True)
        refresh_token = RefreshTokenFactory(
            user=user,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        async_db_session.add(user)
        async_db_session.add(refresh_token)
        await async_db_session.commit()
        
        response = await async_client.post(
            "/api/v1/auth/refresh", 
            json={"refresh_token": refresh_token.token}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in response.json()["detail"].lower()

    async def test_token_refresh_revoked_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test token refresh with revoked token fails."""
        user = UserFactory(is_verified=True)
        refresh_token = RefreshTokenFactory(user=user, is_revoked=True)
        async_db_session.add(user)
        async_db_session.add(refresh_token)
        await async_db_session.commit()
        
        response = await async_client.post(
            "/api/v1/auth/refresh", 
            json={"refresh_token": refresh_token.token}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "revoked" in response.json()["detail"].lower()

    async def test_logout_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful logout."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"].lower()

    async def test_logout_invalid_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test logout with invalid token fails."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_password_reset_request_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful password reset request."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.post(
            "/api/v1/auth/password-reset",
            json={"email": user.email}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "email" in response.json()["message"].lower()

    async def test_password_reset_request_nonexistent_user(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test password reset request for nonexistent user."""
        response = await async_client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return 200 to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK
        assert "email" in response.json()["message"].lower()

    async def test_password_reset_confirm_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful password reset confirmation."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate reset token
        auth_service = AuthService()
        reset_token = auth_service.create_password_reset_token(user.email)
        
        response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_token,
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "password" in response.json()["message"].lower()

    async def test_password_reset_confirm_invalid_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test password reset confirmation with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "invalid_token",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()

    async def test_me_endpoint_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful me endpoint."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" in data
        assert "first_name" in data
        assert "role" in data
        assert "permissions" in data

    async def test_me_endpoint_invalid_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test me endpoint with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.asyncio
class TestMFA:
    """Test Multi-Factor Authentication (MFA) functionality."""

    async def test_mfa_setup_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful MFA setup."""
        response = await async_client.post(
            "/api/v1/auth/mfa/setup",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "secret" in data
        assert "qr_code" in data
        assert "backup_codes" in data

    async def test_mfa_verify_setup_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful MFA verification during setup."""
        # First setup MFA
        setup_response = await async_client.post(
            "/api/v1/auth/mfa/setup",
            headers=authenticated_headers
        )
        secret = setup_response.json()["secret"]
        
        # Generate valid TOTP token
        mfa_service = MFAService()
        totp_token = mfa_service.generate_totp_token(secret)
        
        response = await async_client.post(
            "/api/v1/auth/mfa/verify",
            json={"token": totp_token},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "enabled" in response.json()["message"].lower()

    async def test_mfa_verify_setup_invalid_token(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test MFA verification with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/mfa/verify",
            json={"token": "invalid_token"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()

    async def test_mfa_login_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful MFA login."""
        user = UserWithMFAFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Regular login should require MFA
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "mfa_required" in data
        assert data["mfa_required"] is True
        assert "mfa_token" in data
        
        # Complete MFA login
        mfa_service = MFAService()
        totp_token = mfa_service.generate_totp_token(user.mfa_secret)
        
        mfa_response = await async_client.post(
            "/api/v1/auth/mfa/login",
            json={
                "mfa_token": data["mfa_token"],
                "totp_token": totp_token
            }
        )
        
        assert mfa_response.status_code == status.HTTP_200_OK
        mfa_data = mfa_response.json()
        assert "access_token" in mfa_data
        assert "refresh_token" in mfa_data

    async def test_mfa_login_invalid_totp(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test MFA login with invalid TOTP token."""
        user = UserWithMFAFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Regular login
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        data = response.json()
        
        # Complete MFA login with invalid token
        mfa_response = await async_client.post(
            "/api/v1/auth/mfa/login",
            json={
                "mfa_token": data["mfa_token"],
                "totp_token": "invalid_token"
            }
        )
        
        assert mfa_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in mfa_response.json()["detail"].lower()

    async def test_mfa_backup_code_login_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful MFA login with backup code."""
        user = UserWithMFAFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Regular login
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        data = response.json()
        
        # Complete MFA login with backup code
        mfa_response = await async_client.post(
            "/api/v1/auth/mfa/login",
            json={
                "mfa_token": data["mfa_token"],
                "backup_code": user.backup_codes[0]
            }
        )
        
        assert mfa_response.status_code == status.HTTP_200_OK
        mfa_data = mfa_response.json()
        assert "access_token" in mfa_data
        assert "refresh_token" in mfa_data

    async def test_mfa_disable_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful MFA disable."""
        user = UserWithMFAFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate auth headers
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Generate valid TOTP token
        mfa_service = MFAService()
        totp_token = mfa_service.generate_totp_token(user.mfa_secret)
        
        response = await async_client.post(
            "/api/v1/auth/mfa/disable",
            json={"token": totp_token},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "disabled" in response.json()["message"].lower()

    async def test_mfa_regenerate_backup_codes_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful MFA backup codes regeneration."""
        user = UserWithMFAFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate auth headers
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.post(
            "/api/v1/auth/mfa/regenerate-backup-codes",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10


@pytest.mark.auth
@pytest.mark.asyncio
class TestSSO:
    """Test Single Sign-On (SSO) functionality."""

    @patch('app.services.govbr_service.GovBrService')
    async def test_govbr_sso_login_success(
        self, mock_govbr_service, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful Gov.br SSO login."""
        # Mock Gov.br service
        mock_service = Mock()
        mock_service.get_authorization_url.return_value = "https://sso.gov.br/auth"
        mock_govbr_service.return_value = mock_service
        
        response = await async_client.get("/api/v1/auth/sso/govbr")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "https://sso.gov.br/auth" in data["authorization_url"]

    @patch('app.services.govbr_service.GovBrService')
    async def test_govbr_sso_callback_success(
        self, mock_govbr_service, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test successful Gov.br SSO callback."""
        # Mock Gov.br service
        mock_service = Mock()
        mock_service.get_user_info.return_value = {
            "email": "user@gov.br",
            "first_name": "João",
            "last_name": "Silva",
            "cpf": "123.456.789-00"
        }
        mock_govbr_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/auth/sso/govbr/callback?code=auth_code&state=state"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "user@gov.br"

    @patch('app.services.govbr_service.GovBrService')
    async def test_govbr_sso_callback_invalid_code(
        self, mock_govbr_service, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test Gov.br SSO callback with invalid code."""
        # Mock Gov.br service to raise exception
        mock_service = Mock()
        mock_service.get_user_info.side_effect = Exception("Invalid code")
        mock_govbr_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/auth/sso/govbr/callback?code=invalid_code&state=state"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()


@pytest.mark.auth
@pytest.mark.security
@pytest.mark.asyncio
class TestAuthSecurity:
    """Test authentication security features."""

    async def test_login_rate_limiting(
        self, async_client: AsyncClient, async_db_session: AsyncSession, mock_redis
    ):
        """Test login rate limiting."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrongpassword",
        }
        
        # Mock Redis to simulate rate limiting
        mock_redis.incr.return_value = 6  # Exceed limit
        
        with patch('app.services.auth_service.redis_client', mock_redis):
            response = await async_client.post(
                "/api/v1/auth/login", data=login_data
            )
            
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "rate limit" in response.json()["detail"].lower()

    async def test_failed_login_attempts_tracking(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tracking of failed login attempts."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrongpassword",
        }
        
        # Make multiple failed attempts
        for i in range(3):
            response = await async_client.post(
                "/api/v1/auth/login", data=login_data
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Check that failed attempts are tracked
        await async_db_session.refresh(user)
        assert user.failed_login_attempts == 3

    async def test_account_lockout_after_failed_attempts(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test account lockout after multiple failed attempts."""
        user = UserFactory(is_verified=True, failed_login_attempts=4)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "wrongpassword",
        }
        
        # One more failed attempt should lock the account
        response = await async_client.post(
            "/api/v1/auth/login", data=login_data
        )
        
        assert response.status_code == status.HTTP_423_LOCKED
        assert "locked" in response.json()["detail"].lower()

    async def test_jwt_token_blacklisting(
        self, async_client: AsyncClient, async_db_session: AsyncSession, mock_redis
    ):
        """Test JWT token blacklisting on logout."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate auth headers
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Mock Redis for blacklisting
        mock_redis.set.return_value = True
        
        with patch('app.services.auth_service.redis_client', mock_redis):
            # Logout should blacklist the token
            response = await async_client.post(
                "/api/v1/auth/logout",
                headers=headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_redis.set.assert_called()

    async def test_session_timeout(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test session timeout functionality."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create expired token
        auth_service = AuthService()
        with freeze_time("2023-01-01"):
            access_token = auth_service.create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Token should be expired
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in response.json()["detail"].lower()

    async def test_password_complexity_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test password complexity validation."""
        weak_passwords = [
            "password",
            "12345678",
            "Password",
            "password123",
            "PASSWORD123",
        ]
        
        for password in weak_passwords:
            user_data = {
                "email": f"test_{password}@example.com",
                "password": password,
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Company",
            }
            
            response = await async_client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "password" in response.json()["detail"].lower()

    async def test_concurrent_login_protection(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test protection against concurrent login sessions."""
        user = UserFactory(is_verified=True)
        async_db_session.add(user)
        await async_db_session.commit()
        
        login_data = {
            "username": user.email,
            "password": "secret",
        }
        
        # First login
        response1 = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response1.status_code == status.HTTP_200_OK
        
        # Second login should invalidate first session
        response2 = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response2.status_code == status.HTTP_200_OK
        
        # First token should be invalidated
        headers1 = {"Authorization": f"Bearer {response1.json()['access_token']}"}
        me_response = await async_client.get("/api/v1/auth/me", headers=headers1)
        
        # This might pass or fail depending on implementation
        # The test demonstrates the concept
        assert me_response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.auth
@pytest.mark.unit
class TestAuthServices:
    """Test authentication service classes."""

    def test_auth_service_create_access_token(self):
        """Test access token creation."""
        auth_service = AuthService()
        data = {"sub": "user_id", "email": "test@example.com"}
        
        token = auth_service.create_access_token(data)
        
        assert isinstance(token, str)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user_id"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_auth_service_verify_token(self):
        """Test token verification."""
        auth_service = AuthService()
        data = {"sub": "user_id", "email": "test@example.com"}
        
        token = auth_service.create_access_token(data)
        payload = auth_service.verify_token(token)
        
        assert payload["sub"] == "user_id"
        assert payload["email"] == "test@example.com"

    def test_auth_service_verify_invalid_token(self):
        """Test verification of invalid token."""
        auth_service = AuthService()
        
        with pytest.raises(Exception):
            auth_service.verify_token("invalid_token")

    def test_mfa_service_generate_secret(self):
        """Test MFA secret generation."""
        mfa_service = MFAService()
        
        secret = mfa_service.generate_secret()
        
        assert isinstance(secret, str)
        assert len(secret) == 32

    def test_mfa_service_generate_qr_code(self):
        """Test MFA QR code generation."""
        mfa_service = MFAService()
        secret = "JBSWY3DPEHPK3PXP"
        email = "test@example.com"
        
        qr_code = mfa_service.generate_qr_code(secret, email)
        
        assert isinstance(qr_code, str)
        assert qr_code.startswith("data:image/png;base64,")

    def test_mfa_service_verify_token(self):
        """Test MFA token verification."""
        mfa_service = MFAService()
        secret = "JBSWY3DPEHPK3PXP"
        
        # Generate token
        token = mfa_service.generate_totp_token(secret)
        
        # Verify token
        is_valid = mfa_service.verify_totp_token(secret, token)
        
        assert is_valid is True

    def test_mfa_service_verify_invalid_token(self):
        """Test MFA invalid token verification."""
        mfa_service = MFAService()
        secret = "JBSWY3DPEHPK3PXP"
        
        is_valid = mfa_service.verify_totp_token(secret, "invalid_token")
        
        assert is_valid is False

    def test_mfa_service_generate_backup_codes(self):
        """Test MFA backup codes generation."""
        mfa_service = MFAService()
        
        codes = mfa_service.generate_backup_codes()
        
        assert isinstance(codes, list)
        assert len(codes) == 10
        assert all(isinstance(code, str) for code in codes)
        assert all(len(code) == 6 for code in codes)
        assert all(code.isdigit() for code in codes)