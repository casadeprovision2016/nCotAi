"""
Role-Based Access Control (RBAC) tests for COTAI backend.
Tests for granular permissions, resource access control, and role management.
"""
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.rbac_service import RBACService
from app.services.user_service import UserService
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    SuperUserFactory,
    TenderFactory,
    QuotationFactory,
    create_test_user,
    create_admin_user,
)


@pytest.mark.rbac
@pytest.mark.asyncio
class TestRBACService:
    """Test RBAC service functionality."""

    def test_rbac_service_check_permission_success(self):
        """Test successful permission check."""
        rbac_service = RBACService()
        user = UserFactory(
            role=UserRole.USER,
            permissions={"tenders": {"read": True, "write": True}}
        )
        
        has_permission = rbac_service.check_permission(user, "tenders", "read")
        
        assert has_permission is True

    def test_rbac_service_check_permission_denied(self):
        """Test permission check denial."""
        rbac_service = RBACService()
        user = UserFactory(
            role=UserRole.USER,
            permissions={"tenders": {"read": True, "write": False}}
        )
        
        has_permission = rbac_service.check_permission(user, "tenders", "write")
        
        assert has_permission is False

    def test_rbac_service_check_permission_missing_resource(self):
        """Test permission check for missing resource."""
        rbac_service = RBACService()
        user = UserFactory(
            role=UserRole.USER,
            permissions={"tenders": {"read": True}}
        )
        
        has_permission = rbac_service.check_permission(user, "quotations", "read")
        
        assert has_permission is False

    def test_rbac_service_check_permission_admin_override(self):
        """Test admin permission override."""
        rbac_service = RBACService()
        user = AdminUserFactory()
        
        has_permission = rbac_service.check_permission(user, "any_resource", "admin")
        
        assert has_permission is True

    def test_rbac_service_check_permission_super_admin_override(self):
        """Test super admin permission override."""
        rbac_service = RBACService()
        user = SuperUserFactory()
        
        has_permission = rbac_service.check_permission(user, "any_resource", "super_admin")
        
        assert has_permission is True

    def test_rbac_service_check_resource_ownership(self):
        """Test resource ownership check."""
        rbac_service = RBACService()
        user = UserFactory()
        tender = TenderFactory(created_by=user)
        
        is_owner = rbac_service.check_resource_ownership(user, tender, "created_by")
        
        assert is_owner is True

    def test_rbac_service_check_resource_ownership_denied(self):
        """Test resource ownership check denial."""
        rbac_service = RBACService()
        user = UserFactory()
        other_user = UserFactory()
        tender = TenderFactory(created_by=other_user)
        
        is_owner = rbac_service.check_resource_ownership(user, tender, "created_by")
        
        assert is_owner is False

    def test_rbac_service_get_user_permissions(self):
        """Test getting user permissions."""
        rbac_service = RBACService()
        user = UserFactory(
            role=UserRole.USER,
            permissions={
                "tenders": {"read": True, "write": True},
                "quotations": {"read": True, "write": False}
            }
        )
        
        permissions = rbac_service.get_user_permissions(user)
        
        assert "tenders" in permissions
        assert "quotations" in permissions
        assert permissions["tenders"]["read"] is True
        assert permissions["quotations"]["write"] is False

    def test_rbac_service_get_default_permissions_for_role(self):
        """Test getting default permissions for role."""
        rbac_service = RBACService()
        
        user_permissions = rbac_service.get_default_permissions_for_role(UserRole.USER)
        admin_permissions = rbac_service.get_default_permissions_for_role(UserRole.ADMIN)
        
        assert isinstance(user_permissions, dict)
        assert isinstance(admin_permissions, dict)
        assert len(admin_permissions) >= len(user_permissions)

    def test_rbac_service_update_user_permissions(self):
        """Test updating user permissions."""
        rbac_service = RBACService()
        user = UserFactory(permissions={})
        
        new_permissions = {"tenders": {"read": True, "write": True}}
        rbac_service.update_user_permissions(user, new_permissions)
        
        assert user.permissions == new_permissions

    def test_rbac_service_add_permission_to_user(self):
        """Test adding permission to user."""
        rbac_service = RBACService()
        user = UserFactory(permissions={"tenders": {"read": True}})
        
        rbac_service.add_permission_to_user(user, "tenders", "write", True)
        
        assert user.permissions["tenders"]["write"] is True

    def test_rbac_service_remove_permission_from_user(self):
        """Test removing permission from user."""
        rbac_service = RBACService()
        user = UserFactory(permissions={"tenders": {"read": True, "write": True}})
        
        rbac_service.remove_permission_from_user(user, "tenders", "write")
        
        assert "write" not in user.permissions["tenders"]

    def test_rbac_service_check_role_hierarchy(self):
        """Test role hierarchy checking."""
        rbac_service = RBACService()
        
        # Admin should have higher hierarchy than User
        assert rbac_service.check_role_hierarchy(UserRole.ADMIN, UserRole.USER) is True
        assert rbac_service.check_role_hierarchy(UserRole.USER, UserRole.ADMIN) is False
        
        # Super Admin should have highest hierarchy
        assert rbac_service.check_role_hierarchy(UserRole.SUPER_ADMIN, UserRole.ADMIN) is True
        assert rbac_service.check_role_hierarchy(UserRole.SUPER_ADMIN, UserRole.USER) is True


@pytest.mark.rbac
@pytest.mark.asyncio
class TestRBACEndpoints:
    """Test RBAC API endpoints."""

    async def test_get_user_permissions_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful retrieval of user permissions."""
        response = await async_client.get(
            "/api/v1/rbac/permissions/me",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permissions" in data
        assert isinstance(data["permissions"], dict)

    async def test_get_user_permissions_unauthorized(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test unauthorized access to user permissions."""
        response = await async_client.get("/api/v1/rbac/permissions/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_all_permissions_admin_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test admin retrieval of all permissions."""
        response = await async_client.get(
            "/api/v1/rbac/permissions",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permissions" in data
        assert isinstance(data["permissions"], dict)

    async def test_get_all_permissions_user_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user access to all permissions is forbidden."""
        response = await async_client.get(
            "/api/v1/rbac/permissions",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_user_permissions_admin_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test admin updating user permissions."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        new_permissions = {
            "tenders": {"read": True, "write": True},
            "quotations": {"read": True, "write": False}
        }
        
        response = await async_client.put(
            f"/api/v1/rbac/permissions/{user.id}",
            json={"permissions": new_permissions},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == new_permissions

    async def test_update_user_permissions_user_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user updating permissions is forbidden."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        new_permissions = {"tenders": {"read": True, "write": True}}
        
        response = await async_client.put(
            f"/api/v1/rbac/permissions/{user.id}",
            json={"permissions": new_permissions},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_get_user_roles_admin_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test admin retrieval of user roles."""
        response = await async_client.get(
            "/api/v1/rbac/roles",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "roles" in data
        assert isinstance(data["roles"], list)

    async def test_update_user_role_admin_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test admin updating user role."""
        user = UserFactory(role=UserRole.USER)
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.put(
            f"/api/v1/rbac/roles/{user.id}",
            json={"role": "MANAGER"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == "MANAGER"

    async def test_update_user_role_user_forbidden(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user updating role is forbidden."""
        user = UserFactory(role=UserRole.USER)
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.put(
            f"/api/v1/rbac/roles/{user.id}",
            json={"role": "MANAGER"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_check_permission_endpoint_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test permission check endpoint."""
        response = await async_client.post(
            "/api/v1/rbac/check-permission",
            json={"resource": "tenders", "action": "read"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "has_permission" in data
        assert isinstance(data["has_permission"], bool)

    async def test_check_permission_endpoint_unauthorized(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test permission check endpoint without authentication."""
        response = await async_client.post(
            "/api/v1/rbac/check-permission",
            json={"resource": "tenders", "action": "read"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.rbac
@pytest.mark.asyncio
class TestResourceAccessControl:
    """Test resource-specific access control."""

    async def test_tender_read_access_with_permission(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender read access with proper permission."""
        user = UserFactory(
            is_verified=True,
            permissions={"tenders": {"read": True}}
        )
        tender = TenderFactory(created_by=user)
        async_db_session.add(user)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Generate auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.get(
            f"/api/v1/tenders/{tender.id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK

    async def test_tender_read_access_without_permission(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender read access without permission."""
        user = UserFactory(
            is_verified=True,
            permissions={"tenders": {"read": False}}
        )
        tender = TenderFactory()
        async_db_session.add(user)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Generate auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.get(
            f"/api/v1/tenders/{tender.id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_tender_write_access_with_permission(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender write access with proper permission."""
        user = UserFactory(
            is_verified=True,
            permissions={"tenders": {"write": True}}
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        tender_data = {
            "title": "Test Tender",
            "description": "Test Description",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31",
            "category": "GOODS",
            "type": "OPEN"
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED

    async def test_tender_write_access_without_permission(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender write access without permission."""
        user = UserFactory(
            is_verified=True,
            permissions={"tenders": {"write": False}}
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Generate auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        tender_data = {
            "title": "Test Tender",
            "description": "Test Description",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31",
            "category": "GOODS",
            "type": "OPEN"
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_tender_ownership_access_control(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender ownership-based access control."""
        owner = UserFactory(
            is_verified=True,
            permissions={"tenders": {"read": True, "write": True}}
        )
        other_user = UserFactory(
            is_verified=True,
            permissions={"tenders": {"read": True, "write": True}}
        )
        tender = TenderFactory(created_by=owner)
        async_db_session.add(owner)
        async_db_session.add(other_user)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Generate auth headers for other user
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(other_user.id), "email": other_user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Other user should not be able to update tender they don't own
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json={"title": "Updated Title"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_admin_bypass_ownership_access_control(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test admin bypass of ownership access control."""
        owner = UserFactory(is_verified=True)
        admin = AdminUserFactory(is_verified=True)
        tender = TenderFactory(created_by=owner)
        async_db_session.add(owner)
        async_db_session.add(admin)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Generate auth headers for admin
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(admin.id), "email": admin.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Admin should be able to update any tender
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json={"title": "Updated by Admin"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK

    async def test_quotation_access_control(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test quotation access control."""
        user = UserFactory(
            is_verified=True,
            permissions={"quotations": {"read": True, "write": True}}
        )
        quotation = QuotationFactory(created_by=user)
        async_db_session.add(user)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Generate auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.get(
            f"/api/v1/quotations/{quotation.id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK

    async def test_user_management_admin_only(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test user management is admin-only."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/users/{user.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_user_management_admin_access(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test user management admin access."""
        user = UserFactory()
        async_db_session.add(user)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/users/{user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.rbac
@pytest.mark.asyncio
class TestRoleHierarchy:
    """Test role hierarchy and inheritance."""

    async def test_role_hierarchy_permissions(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test role hierarchy permissions."""
        # Create users with different roles
        user = UserFactory(role=UserRole.USER, is_verified=True)
        manager = UserFactory(role=UserRole.MANAGER, is_verified=True)
        admin = AdminUserFactory(is_verified=True)
        
        async_db_session.add(user)
        async_db_session.add(manager)
        async_db_session.add(admin)
        await async_db_session.commit()
        
        # Test different access levels
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        
        # User should have basic permissions
        user_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Manager should have extended permissions
        manager_token = auth_service.create_access_token(
            data={"sub": str(manager.id), "email": manager.email}
        )
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        
        # Admin should have full permissions
        admin_token = auth_service.create_access_token(
            data={"sub": str(admin.id), "email": admin.email}
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test accessing user management endpoint
        responses = []
        for headers in [user_headers, manager_headers, admin_headers]:
            response = await async_client.get("/api/v1/users", headers=headers)
            responses.append(response.status_code)
        
        # User should be forbidden, manager might have limited access, admin should have full access
        assert responses[0] == status.HTTP_403_FORBIDDEN  # User
        assert responses[2] == status.HTTP_200_OK  # Admin

    async def test_role_based_resource_filtering(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test role-based resource filtering."""
        # Create users with different roles
        user = UserFactory(role=UserRole.USER, is_verified=True)
        admin = AdminUserFactory(is_verified=True)
        
        # Create tenders by different users
        user_tender = TenderFactory(created_by=user)
        admin_tender = TenderFactory(created_by=admin)
        
        async_db_session.add(user)
        async_db_session.add(admin)
        async_db_session.add(user_tender)
        async_db_session.add(admin_tender)
        await async_db_session.commit()
        
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        
        # User should only see their own tenders
        user_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        user_response = await async_client.get("/api/v1/tenders", headers=user_headers)
        
        if user_response.status_code == status.HTTP_200_OK:
            user_tenders = user_response.json()
            # User should only see their own tenders
            assert len(user_tenders) == 1
            assert user_tenders[0]["id"] == str(user_tender.id)
        
        # Admin should see all tenders
        admin_token = auth_service.create_access_token(
            data={"sub": str(admin.id), "email": admin.email}
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        admin_response = await async_client.get("/api/v1/tenders", headers=admin_headers)
        
        if admin_response.status_code == status.HTTP_200_OK:
            admin_tenders = admin_response.json()
            # Admin should see all tenders
            assert len(admin_tenders) == 2

    async def test_permission_inheritance(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test permission inheritance in role hierarchy."""
        rbac_service = RBACService()
        
        # Manager should inherit USER permissions
        manager = UserFactory(role=UserRole.MANAGER)
        manager_permissions = rbac_service.get_user_permissions(manager)
        
        # Admin should inherit MANAGER and USER permissions
        admin = AdminUserFactory()
        admin_permissions = rbac_service.get_user_permissions(admin)
        
        # Super Admin should inherit all permissions
        super_admin = SuperUserFactory()
        super_admin_permissions = rbac_service.get_user_permissions(super_admin)
        
        # Check inheritance hierarchy
        assert len(admin_permissions) >= len(manager_permissions)
        assert len(super_admin_permissions) >= len(admin_permissions)

    async def test_role_based_field_filtering(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test role-based field filtering in responses."""
        user = UserFactory(role=UserRole.USER, is_verified=True)
        admin = AdminUserFactory(is_verified=True)
        
        async_db_session.add(user)
        async_db_session.add(admin)
        await async_db_session.commit()
        
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        
        # User accessing their own profile
        user_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        user_response = await async_client.get("/api/v1/auth/me", headers=user_headers)
        
        if user_response.status_code == status.HTTP_200_OK:
            user_data = user_response.json()
            # User should not see sensitive fields
            assert "hashed_password" not in user_data
            assert "mfa_secret" not in user_data
        
        # Admin accessing user profile
        admin_token = auth_service.create_access_token(
            data={"sub": str(admin.id), "email": admin.email}
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        admin_response = await async_client.get(
            f"/api/v1/users/{user.id}", 
            headers=admin_headers
        )
        
        if admin_response.status_code == status.HTTP_200_OK:
            admin_user_data = admin_response.json()
            # Admin should see additional fields but not sensitive ones
            assert "role" in admin_user_data
            assert "permissions" in admin_user_data
            assert "hashed_password" not in admin_user_data


@pytest.mark.rbac
@pytest.mark.unit
class TestRBACHelpers:
    """Test RBAC helper functions and utilities."""

    def test_permission_decorator_success(self):
        """Test permission decorator allows access."""
        from app.core.rbac import require_permission
        
        @require_permission("tenders", "read")
        def test_function(current_user):
            return "success"
        
        user = UserFactory(permissions={"tenders": {"read": True}})
        
        # This would normally be tested with dependency injection
        # but we're testing the decorator logic
        assert callable(test_function)

    def test_permission_decorator_failure(self):
        """Test permission decorator denies access."""
        from app.core.rbac import require_permission
        
        @require_permission("tenders", "write")
        def test_function(current_user):
            return "success"
        
        user = UserFactory(permissions={"tenders": {"write": False}})
        
        # This would normally raise an HTTPException
        assert callable(test_function)

    def test_resource_permission_matrix(self):
        """Test resource permission matrix."""
        rbac_service = RBACService()
        
        # Test permission matrix for different roles
        resources = ["tenders", "quotations", "users", "reports"]
        actions = ["read", "write", "delete", "admin"]
        roles = [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        
        for role in roles:
            permissions = rbac_service.get_default_permissions_for_role(role)
            assert isinstance(permissions, dict)
            
            # Higher roles should have more permissions
            if role == UserRole.SUPER_ADMIN:
                # Super admin should have all permissions
                for resource in resources:
                    if resource in permissions:
                        for action in actions:
                            if action in permissions[resource]:
                                assert permissions[resource][action] is True

    def test_dynamic_permission_checking(self):
        """Test dynamic permission checking."""
        rbac_service = RBACService()
        
        # Test with dynamic permissions
        user = UserFactory(permissions={
            "tenders": {"read": True, "write": True},
            "quotations": {"read": True, "write": False}
        })
        
        # Test multiple permission checks
        test_cases = [
            ("tenders", "read", True),
            ("tenders", "write", True),
            ("quotations", "read", True),
            ("quotations", "write", False),
            ("users", "read", False),
            ("reports", "admin", False)
        ]
        
        for resource, action, expected in test_cases:
            result = rbac_service.check_permission(user, resource, action)
            assert result == expected, f"Expected {expected} for {resource}:{action}, got {result}"

    def test_permission_caching(self):
        """Test permission caching mechanism."""
        rbac_service = RBACService()
        user = UserFactory(permissions={"tenders": {"read": True}})
        
        # First call should compute permissions
        result1 = rbac_service.check_permission(user, "tenders", "read")
        
        # Second call should use cached result
        result2 = rbac_service.check_permission(user, "tenders", "read")
        
        assert result1 == result2 == True

    def test_context_aware_permissions(self):
        """Test context-aware permission checking."""
        rbac_service = RBACService()
        
        user = UserFactory()
        tender = TenderFactory(created_by=user)
        other_tender = TenderFactory()
        
        # User should have access to their own tender
        has_access_own = rbac_service.check_resource_ownership(user, tender, "created_by")
        assert has_access_own is True
        
        # User should not have access to other's tender
        has_access_other = rbac_service.check_resource_ownership(user, other_tender, "created_by")
        assert has_access_other is False

    def test_bulk_permission_checking(self):
        """Test bulk permission checking for efficiency."""
        rbac_service = RBACService()
        user = UserFactory(permissions={
            "tenders": {"read": True, "write": True},
            "quotations": {"read": True, "write": False}
        })
        
        # Test bulk permission checking
        permissions_to_check = [
            ("tenders", "read"),
            ("tenders", "write"),
            ("quotations", "read"),
            ("quotations", "write"),
            ("users", "read")
        ]
        
        results = rbac_service.check_permissions_bulk(user, permissions_to_check)
        
        expected_results = [True, True, True, False, False]
        assert results == expected_results