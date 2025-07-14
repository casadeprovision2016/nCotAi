"""
User API endpoint tests for COTAI backend.
Tests for user management, profile operations, admin functions, and bulk operations.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    SuperUserFactory,
    UserWithMFAFactory,
    create_test_user,
    create_admin_user,
    create_bulk_users,
)


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersCRUD:
    """Test basic CRUD operations for users."""

    async def test_create_user_admin_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful user creation by admin."""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
            "company_name": "Test Company",
            "role": "USER",
            "permissions": {
                "tenders": {"read": True, "write": False},
                "quotations": {"read": True, "write": True}
            }
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert data["company_name"] == user_data["company_name"]
        assert data["role"] == user_data["role"]
        assert data["permissions"] == user_data["permissions"]
        assert data["is_active"] == True
        assert data["is_verified"] == True
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_create_user_validation_error(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user creation with validation errors."""
        invalid_user_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "weak",  # Weak password
            "first_name": "",  # Empty first name
            "last_name": "User",
            "role": "INVALID_ROLE",  # Invalid role
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=invalid_user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data
        assert len(error_data["detail"]) > 0

    async def test_create_user_duplicate_email(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user creation with duplicate email."""
        existing_user = UserFactory()
        async_db_session.add(existing_user)
        await async_db_session.commit()
        
        user_data = {
            "email": existing_user.email,
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
            "company_name": "Test Company",
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_user_non_admin_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user creation by non-admin is forbidden."""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User",
            "company_name": "Test Company",
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_get_user_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful user retrieval by admin."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/users/{user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["first_name"] == user.first_name
        assert data["last_name"] == user.last_name
        assert data["role"] == user.role.value
        assert "hashed_password" not in data
        assert "mfa_secret" not in data

    async def test_get_user_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test retrieval of non-existent user."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.get(
            f"/api/v1/users/{non_existent_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_user_non_admin_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user retrieval by non-admin is forbidden."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/users/{user.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_user_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful user update by admin."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "company_name": "Updated Company",
            "role": "MANAGER",
            "permissions": {
                "tenders": {"read": True, "write": True},
                "quotations": {"read": True, "write": True}
            }
        }
        
        response = await async_client.put(
            f"/api/v1/users/{user.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        assert data["last_name"] == update_data["last_name"]
        assert data["company_name"] == update_data["company_name"]
        assert data["role"] == update_data["role"]
        assert data["permissions"] == update_data["permissions"]

    async def test_update_user_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test updating non-existent user."""
        non_existent_id = str(uuid.uuid4())
        update_data = {"first_name": "Updated"}
        
        response = await async_client.put(
            f"/api/v1/users/{non_existent_id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_user_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful user deletion by admin."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.delete(
            f"/api/v1/users/{user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_user_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test deleting non-existent user."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.delete(
            f"/api/v1/users/{non_existent_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_users_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful user listing by admin."""
        users = [UserFactory() for _ in range(5)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/users",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) == 5
        assert data["total"] == 5

    async def test_list_users_pagination(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user listing with pagination."""
        users = [UserFactory() for _ in range(10)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/users?page=1&size=5",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["size"] == 5
        assert data["total"] == 10

    async def test_list_users_non_admin_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user listing by non-admin is forbidden."""
        response = await async_client.get(
            "/api/v1/users",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersProfile:
    """Test user profile management operations."""

    async def test_get_own_profile_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user getting their own profile."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        assert "permissions" in data
        assert "hashed_password" not in data
        assert "mfa_secret" not in data

    async def test_get_own_profile_unauthorized(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test getting profile without authentication."""
        response = await async_client.get("/api/v1/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_own_profile_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user updating their own profile."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "company_name": "Updated Company"
        }
        
        response = await async_client.put(
            "/api/v1/users/me",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        assert data["last_name"] == update_data["last_name"]
        assert data["company_name"] == update_data["company_name"]

    async def test_update_own_profile_restricted_fields(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user cannot update restricted fields in their profile."""
        update_data = {
            "first_name": "Updated",
            "role": "ADMIN",  # Should not be allowed
            "permissions": {"admin": True},  # Should not be allowed
            "is_superuser": True  # Should not be allowed
        }
        
        response = await async_client.put(
            "/api/v1/users/me",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        # Role should remain unchanged
        assert data["role"] != "ADMIN"
        assert data["is_superuser"] != True

    async def test_change_password_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful password change."""
        password_data = {
            "current_password": "secret",  # Default password from factory
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
        
        response = await async_client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password changed" in data["message"].lower()

    async def test_change_password_invalid_current(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test password change with invalid current password."""
        password_data = {
            "current_password": "wrong_password",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
        
        response = await async_client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "current password" in response.json()["detail"].lower()

    async def test_change_password_mismatch(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test password change with password mismatch."""
        password_data = {
            "current_password": "secret",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = await async_client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "passwords do not match" in response.json()["detail"].lower()

    async def test_change_password_weak_password(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test password change with weak password."""
        password_data = {
            "current_password": "secret",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = await async_client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()

    async def test_deactivate_own_account(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user deactivating their own account."""
        response = await async_client.put(
            "/api/v1/users/me/deactivate",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deactivated" in data["message"].lower()

    async def test_delete_own_account_request(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user requesting account deletion."""
        response = await async_client.delete(
            "/api/v1/users/me",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deletion request" in data["message"].lower()


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersValidation:
    """Test user validation rules."""

    async def test_user_email_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user email validation."""
        test_cases = [
            ("", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty email
            ("invalid-email", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Invalid format
            ("valid@example.com", status.HTTP_201_CREATED),  # Valid email
            ("user.name+tag@example.com", status.HTTP_201_CREATED),  # Valid complex email
        ]
        
        for email, expected_status in test_cases:
            user_data = {
                "email": email,
                "password": "SecurePassword123!",
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Company",
            }
            
            response = await async_client.post(
                "/api/v1/users",
                json=user_data,
                headers=admin_headers
            )
            
            assert response.status_code == expected_status

    async def test_user_password_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user password validation."""
        test_cases = [
            ("", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty password
            ("weak", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too weak
            ("password123", status.HTTP_422_UNPROCESSABLE_ENTITY),  # No uppercase
            ("PASSWORD123", status.HTTP_422_UNPROCESSABLE_ENTITY),  # No lowercase
            ("PasswordABC", status.HTTP_422_UNPROCESSABLE_ENTITY),  # No numbers
            ("Password123", status.HTTP_422_UNPROCESSABLE_ENTITY),  # No special chars
            ("Password123!", status.HTTP_201_CREATED),  # Valid password
        ]
        
        for password, expected_status in test_cases:
            user_data = {
                "email": f"test_{len(password)}@example.com",
                "password": password,
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Company",
            }
            
            response = await async_client.post(
                "/api/v1/users",
                json=user_data,
                headers=admin_headers
            )
            
            assert response.status_code == expected_status

    async def test_user_name_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user name validation."""
        test_cases = [
            ("", "Last", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty first name
            ("First", "", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty last name
            ("A" * 101, "Last", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too long first name
            ("First", "A" * 101, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too long last name
            ("Valid", "Name", status.HTTP_201_CREATED),  # Valid names
        ]
        
        for first_name, last_name, expected_status in test_cases:
            user_data = {
                "email": f"test_{len(first_name)}_{len(last_name)}@example.com",
                "password": "SecurePassword123!",
                "first_name": first_name,
                "last_name": last_name,
                "company_name": "Test Company",
            }
            
            response = await async_client.post(
                "/api/v1/users",
                json=user_data,
                headers=admin_headers
            )
            
            assert response.status_code == expected_status

    async def test_user_role_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user role validation."""
        valid_roles = ["GUEST", "USER", "MANAGER", "ADMIN", "SUPER_ADMIN"]
        
        for role in valid_roles:
            user_data = {
                "email": f"test_{role.lower()}@example.com",
                "password": "SecurePassword123!",
                "first_name": "Test",
                "last_name": "User",
                "company_name": "Test Company",
                "role": role
            }
            
            response = await async_client.post(
                "/api/v1/users",
                json=user_data,
                headers=admin_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["role"] == role

        # Test invalid role
        invalid_user_data = {
            "email": "test_invalid@example.com",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company",
            "role": "INVALID_ROLE"
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=invalid_user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_user_permissions_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user permissions validation."""
        valid_permissions = {
            "tenders": {"read": True, "write": False},
            "quotations": {"read": True, "write": True},
            "users": {"read": False, "write": False}
        }
        
        user_data = {
            "email": "test_permissions@example.com",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User",
            "company_name": "Test Company",
            "permissions": valid_permissions
        }
        
        response = await async_client.post(
            "/api/v1/users",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["permissions"] == valid_permissions


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersFiltering:
    """Test user filtering and search functionality."""

    async def test_filter_users_by_role(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test filtering users by role."""
        # Create users with different roles
        user1 = UserFactory(role=UserRole.USER)
        user2 = UserFactory(role=UserRole.MANAGER)
        user3 = AdminUserFactory()
        
        async_db_session.add(user1)
        async_db_session.add(user2)
        async_db_session.add(user3)
        await async_db_session.commit()
        
        # Filter by USER role
        response = await async_client.get(
            "/api/v1/users?role=USER",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["role"] == "USER"

    async def test_filter_users_by_active_status(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test filtering users by active status."""
        # Create users with different active statuses
        active_user = UserFactory(is_active=True)
        inactive_user = UserFactory(is_active=False)
        
        async_db_session.add(active_user)
        async_db_session.add(inactive_user)
        await async_db_session.commit()
        
        # Filter by active status
        response = await async_client.get(
            "/api/v1/users?is_active=true",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["is_active"] == True

    async def test_search_users_by_email(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test searching users by email."""
        # Create users with different emails
        user1 = UserFactory(email="john.doe@example.com")
        user2 = UserFactory(email="jane.smith@example.com")
        user3 = UserFactory(email="bob.wilson@company.com")
        
        async_db_session.add(user1)
        async_db_session.add(user2)
        async_db_session.add(user3)
        await async_db_session.commit()
        
        # Search for "john"
        response = await async_client.get(
            "/api/v1/users?search=john",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert "john" in data["items"][0]["email"].lower()

    async def test_search_users_by_name(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test searching users by name."""
        # Create users with different names
        user1 = UserFactory(first_name="Alice", last_name="Johnson")
        user2 = UserFactory(first_name="Bob", last_name="Smith")
        user3 = UserFactory(first_name="Charlie", last_name="Brown")
        
        async_db_session.add(user1)
        async_db_session.add(user2)
        async_db_session.add(user3)
        await async_db_session.commit()
        
        # Search for "Alice"
        response = await async_client.get(
            "/api/v1/users?search=Alice",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["first_name"] == "Alice"

    async def test_search_users_by_company(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test searching users by company name."""
        # Create users with different companies
        user1 = UserFactory(company_name="Tech Corp")
        user2 = UserFactory(company_name="Design Studio")
        user3 = UserFactory(company_name="Tech Solutions")
        
        async_db_session.add(user1)
        async_db_session.add(user2)
        async_db_session.add(user3)
        await async_db_session.commit()
        
        # Search for "Tech"
        response = await async_client.get(
            "/api/v1/users?search=Tech",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2

    async def test_combined_filters(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test combining multiple filters."""
        # Create users with specific combinations
        target_user = UserFactory(
            role=UserRole.USER,
            is_active=True,
            first_name="Target",
            company_name="Target Company"
        )
        other_user = UserFactory(
            role=UserRole.MANAGER,
            is_active=True,
            first_name="Other",
            company_name="Target Company"
        )
        
        async_db_session.add(target_user)
        async_db_session.add(other_user)
        await async_db_session.commit()
        
        # Apply multiple filters
        response = await async_client.get(
            "/api/v1/users?role=USER&is_active=true&search=Target",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["first_name"] == "Target"

    async def test_sort_users(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test sorting users."""
        # Create users with different creation dates
        user1 = UserFactory(
            first_name="Alice",
            created_at=datetime(2025, 1, 1)
        )
        user2 = UserFactory(
            first_name="Bob",
            created_at=datetime(2025, 1, 2)
        )
        user3 = UserFactory(
            first_name="Charlie",
            created_at=datetime(2025, 1, 3)
        )
        
        async_db_session.add(user1)
        async_db_session.add(user2)
        async_db_session.add(user3)
        await async_db_session.commit()
        
        # Sort by first name ascending
        response = await async_client.get(
            "/api/v1/users?sort_by=first_name&sort_order=asc",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        
        # Check sorting order
        names = [item["first_name"] for item in data["items"]]
        assert names == sorted(names)


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersBulkOperations:
    """Test bulk operations on users."""

    async def test_bulk_create_users(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk user creation."""
        users_data = [
            {
                "email": f"user{i}@example.com",
                "password": "SecurePassword123!",
                "first_name": f"User{i}",
                "last_name": "Test",
                "company_name": "Test Company",
                "role": "USER"
            }
            for i in range(1, 4)
        ]
        
        response = await async_client.post(
            "/api/v1/users/bulk",
            json={"users": users_data},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created_count"] == 3
        assert len(data["users"]) == 3

    async def test_bulk_update_users(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk user update."""
        users = [UserFactory() for _ in range(3)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        bulk_update_data = {
            "user_ids": user_ids,
            "updates": {
                "is_active": False,
                "company_name": "Updated Company"
            }
        }
        
        response = await async_client.put(
            "/api/v1/users/bulk",
            json=bulk_update_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3

    async def test_bulk_delete_users(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk user deletion."""
        users = [UserFactory() for _ in range(3)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        response = await async_client.delete(
            "/api/v1/users/bulk",
            json={"user_ids": user_ids},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 3

    async def test_bulk_role_assignment(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk role assignment."""
        users = [UserFactory(role=UserRole.USER) for _ in range(3)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        bulk_role_data = {
            "user_ids": user_ids,
            "role": "MANAGER"
        }
        
        response = await async_client.put(
            "/api/v1/users/bulk/role",
            json=bulk_role_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3

    async def test_bulk_permissions_update(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk permissions update."""
        users = [UserFactory() for _ in range(3)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        bulk_permissions_data = {
            "user_ids": user_ids,
            "permissions": {
                "tenders": {"read": True, "write": True},
                "quotations": {"read": True, "write": False}
            }
        }
        
        response = await async_client.put(
            "/api/v1/users/bulk/permissions",
            json=bulk_permissions_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3

    async def test_bulk_activate_deactivate(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk user activation/deactivation."""
        users = [UserFactory(is_active=True) for _ in range(3)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        # Bulk deactivate
        response = await async_client.put(
            "/api/v1/users/bulk/deactivate",
            json={"user_ids": user_ids},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3
        
        # Bulk activate
        response = await async_client.put(
            "/api/v1/users/bulk/activate",
            json={"user_ids": user_ids},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3


@pytest.mark.api
@pytest.mark.asyncio
class TestUsersReporting:
    """Test user reporting and analytics."""

    async def test_user_analytics(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user analytics endpoint."""
        # Create users with different roles and statuses
        users = [
            UserFactory(role=UserRole.USER, is_active=True),
            UserFactory(role=UserRole.USER, is_active=False),
            UserFactory(role=UserRole.MANAGER, is_active=True),
            AdminUserFactory(is_active=True),
        ]
        
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/users/analytics",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_users"] == 4
        assert data["active_users"] == 3
        assert data["inactive_users"] == 1
        assert data["role_distribution"]["USER"] == 2
        assert data["role_distribution"]["MANAGER"] == 1
        assert data["role_distribution"]["ADMIN"] == 1

    async def test_user_activity_report(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user activity report."""
        # Create users with different last login times
        users = [
            UserFactory(last_login=datetime.utcnow() - timedelta(days=1)),
            UserFactory(last_login=datetime.utcnow() - timedelta(days=7)),
            UserFactory(last_login=datetime.utcnow() - timedelta(days=30)),
            UserFactory(last_login=None),
        ]
        
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/users/activity-report",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_users"] == 4
        assert data["never_logged_in"] == 1
        assert data["active_last_day"] == 1
        assert data["active_last_week"] == 2
        assert data["active_last_month"] == 3

    async def test_user_export(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user data export."""
        users = [UserFactory() for _ in range(5)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        # Test CSV export
        response = await async_client.get(
            "/api/v1/users/export?format=csv",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"
        
        # Test Excel export
        response = await async_client.get(
            "/api/v1/users/export?format=xlsx",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "spreadsheet" in response.headers["content-type"]

    async def test_user_permissions_report(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user permissions report."""
        users = [
            UserFactory(permissions={"tenders": {"read": True, "write": True}}),
            UserFactory(permissions={"tenders": {"read": True, "write": False}}),
            UserFactory(permissions={"quotations": {"read": True, "write": True}}),
        ]
        
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/users/permissions-report",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permissions_summary" in data
        assert "resource_access" in data


@pytest.mark.api
@pytest.mark.performance
@pytest.mark.asyncio
class TestUsersPerformance:
    """Test user API performance."""

    async def test_user_list_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test performance of user listing."""
        # Create many users
        users = [UserFactory() for _ in range(100)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/users?page=1&size=20",
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 2.0  # Should complete within 2 seconds

    async def test_user_search_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test performance of user search."""
        # Create many users with searchable content
        users = [
            UserFactory(first_name=f"User{i}", email=f"user{i}@example.com") 
            for i in range(50)
        ]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/users?search=User&page=1&size=20",
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 1.5  # Should complete within 1.5 seconds

    async def test_bulk_operations_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test performance of bulk operations."""
        # Create many users
        users = [UserFactory() for _ in range(50)]
        for user in users:
            async_db_session.add(user)
        await async_db_session.commit()
        
        user_ids = [str(user.id) for user in users]
        
        bulk_update_data = {
            "user_ids": user_ids,
            "updates": {"is_active": False}
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.put(
            "/api/v1/users/bulk",
            json=bulk_update_data,
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 3.0  # Should complete within 3 seconds
        
        data = response.json()
        assert data["updated_count"] == 50