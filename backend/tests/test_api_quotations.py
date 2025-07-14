"""
Quotation API endpoint tests for COTAI backend.
Tests for CRUD operations, workflow management, validation, and integrations.
"""
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quotation import Quotation, QuotationStatus, QuotationPriority
from app.models.user import User, UserRole
from tests.factories import (
    QuotationFactory,
    QuotationWithItemsFactory,
    CompleteQuotationFactory,
    QuotationItemFactory,
    QuotationDocumentFactory,
    SupplierFactory,
    TenderFactory,
    UserFactory,
    AdminUserFactory,
)


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsCRUD:
    """Test basic CRUD operations for quotations."""

    async def test_create_quotation_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful quotation creation."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        quotation_data = {
            "title": "Test Quotation Creation",
            "description": "Test quotation description for creation",
            "tender_id": str(tender.id),
            "status": "DRAFT",
            "priority": "MEDIUM",
            "estimated_value": 75000.50,
            "deadline": "2025-02-10",
            "requirements": {
                "delivery_time": "30 days",
                "warranty": "12 months",
                "payment_terms": "30 days"
            }
        }
        
        response = await async_client.post(
            "/api/v1/quotations",
            json=quotation_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == quotation_data["title"]
        assert data["description"] == quotation_data["description"]
        assert data["status"] == quotation_data["status"]
        assert data["priority"] == quotation_data["priority"]
        assert float(data["estimated_value"]) == quotation_data["estimated_value"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_quotation_validation_error(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation creation with validation errors."""
        invalid_quotation_data = {
            "title": "",  # Empty title
            "description": "Test description",
            "status": "INVALID_STATUS",
            "priority": "INVALID_PRIORITY",
            "estimated_value": -1000,  # Negative value
            "deadline": "2023-01-01",  # Past date
        }
        
        response = await async_client.post(
            "/api/v1/quotations",
            json=invalid_quotation_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data
        assert len(error_data["detail"]) > 0

    async def test_get_quotation_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful quotation retrieval."""
        quotation = QuotationFactory()
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/quotations/{quotation.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(quotation.id)
        assert data["title"] == quotation.title
        assert data["description"] == quotation.description
        assert data["status"] == quotation.status.value
        assert data["priority"] == quotation.priority.value

    async def test_get_quotation_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test retrieval of non-existent quotation."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.get(
            f"/api/v1/quotations/{non_existent_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_quotation_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful quotation update."""
        quotation = QuotationFactory()
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        update_data = {
            "title": "Updated Quotation Title",
            "description": "Updated description",
            "estimated_value": 85000.0,
            "priority": "HIGH"
        }
        
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert float(data["estimated_value"]) == update_data["estimated_value"]
        assert data["priority"] == update_data["priority"]

    async def test_update_quotation_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test updating non-existent quotation."""
        non_existent_id = str(uuid.uuid4())
        update_data = {"title": "Updated Title"}
        
        response = await async_client.put(
            f"/api/v1/quotations/{non_existent_id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_quotation_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful quotation deletion."""
        quotation = QuotationFactory()
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        response = await async_client.delete(
            f"/api/v1/quotations/{quotation.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_quotation_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test deleting non-existent quotation."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.delete(
            f"/api/v1/quotations/{non_existent_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_quotations_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful quotation listing."""
        # Create multiple quotations
        quotations = [QuotationFactory() for _ in range(5)]
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/quotations",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) == 5
        assert data["total"] == 5

    async def test_list_quotations_pagination(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation listing with pagination."""
        # Create multiple quotations
        quotations = [QuotationFactory() for _ in range(10)]
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/quotations?page=1&size=5",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["size"] == 5
        assert data["total"] == 10


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsWorkflow:
    """Test quotation workflow and status management."""

    async def test_quotation_status_transitions(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test valid quotation status transitions."""
        quotation = QuotationFactory(status=QuotationStatus.DRAFT)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Test valid status transitions
        valid_transitions = [
            ("ACTIVE", status.HTTP_200_OK),
            ("IN_PROGRESS", status.HTTP_200_OK),
            ("COMPLETED", status.HTTP_200_OK),
        ]
        
        for new_status, expected_code in valid_transitions:
            response = await async_client.put(
                f"/api/v1/quotations/{quotation.id}",
                json={"status": new_status},
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_code
            if expected_code == status.HTTP_200_OK:
                data = response.json()
                assert data["status"] == new_status

    async def test_quotation_status_invalid_transition(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test invalid quotation status transitions."""
        quotation = QuotationFactory(status=QuotationStatus.COMPLETED)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Completed quotation should not be able to go back to DRAFT
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json={"status": "DRAFT"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert "transition" in error_data["detail"].lower()

    async def test_quotation_assignment(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation assignment to users."""
        quotation = QuotationFactory()
        assignee = UserFactory()
        
        async_db_session.add(quotation)
        async_db_session.add(assignee)
        await async_db_session.commit()
        
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}/assign",
            json={"assigned_to": str(assignee.id)},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["assigned_to"]["id"] == str(assignee.id)

    async def test_quotation_priority_update(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation priority updates."""
        quotation = QuotationFactory(priority=QuotationPriority.LOW)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Test priority escalation
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json={"priority": "URGENT"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["priority"] == "URGENT"

    async def test_quotation_deadline_extension(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation deadline extension."""
        original_deadline = date.today() + timedelta(days=7)
        quotation = QuotationFactory(deadline=original_deadline)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        new_deadline = original_deadline + timedelta(days=7)
        
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json={"deadline": str(new_deadline)},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deadline"] == str(new_deadline)

    async def test_quotation_bulk_status_update(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test bulk status update for quotations."""
        quotations = [QuotationFactory(status=QuotationStatus.DRAFT) for _ in range(3)]
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        quotation_ids = [str(q.id) for q in quotations]
        
        bulk_update_data = {
            "quotation_ids": quotation_ids,
            "status": "ACTIVE"
        }
        
        response = await async_client.put(
            "/api/v1/quotations/bulk",
            json=bulk_update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsItems:
    """Test quotation items management."""

    async def test_create_quotation_with_items(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test creating quotation with items."""
        tender = TenderFactory()
        supplier = SupplierFactory()
        
        async_db_session.add(tender)
        async_db_session.add(supplier)
        await async_db_session.commit()
        
        quotation_data = {
            "title": "Quotation with Items",
            "description": "Test quotation with items",
            "tender_id": str(tender.id),
            "status": "DRAFT",
            "priority": "MEDIUM",
            "estimated_value": 50000.0,
            "deadline": "2025-02-15",
            "items": [
                {
                    "item_number": 1,
                    "description": "Item 1 description",
                    "quantity": 10,
                    "unit": "pieces",
                    "unit_price": 500.0,
                    "supplier_id": str(supplier.id),
                    "notes": "Special requirements for item 1"
                },
                {
                    "item_number": 2,
                    "description": "Item 2 description",
                    "quantity": 5,
                    "unit": "units",
                    "unit_price": 1000.0,
                    "supplier_id": str(supplier.id),
                    "notes": "Standard delivery"
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/quotations",
            json=quotation_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["quantity"] == 10
        assert float(data["items"][0]["unit_price"]) == 500.0
        assert float(data["items"][0]["total_price"]) == 5000.0

    async def test_add_item_to_quotation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test adding item to existing quotation."""
        quotation = QuotationFactory()
        supplier = SupplierFactory()
        
        async_db_session.add(quotation)
        async_db_session.add(supplier)
        await async_db_session.commit()
        
        item_data = {
            "item_number": 1,
            "description": "New item description",
            "quantity": 15,
            "unit": "pieces",
            "unit_price": 75.0,
            "supplier_id": str(supplier.id),
            "notes": "Urgent delivery required"
        }
        
        response = await async_client.post(
            f"/api/v1/quotations/{quotation.id}/items",
            json=item_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["description"] == item_data["description"]
        assert data["quantity"] == item_data["quantity"]
        assert float(data["unit_price"]) == item_data["unit_price"]
        assert float(data["total_price"]) == 15 * 75.0

    async def test_update_quotation_item(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test updating quotation item."""
        quotation = QuotationFactory()
        item = QuotationItemFactory(quotation=quotation)
        
        async_db_session.add(quotation)
        async_db_session.add(item)
        await async_db_session.commit()
        
        update_data = {
            "quantity": 20,
            "unit_price": 85.0,
            "notes": "Updated delivery requirements"
        }
        
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}/items/{item.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == update_data["quantity"]
        assert float(data["unit_price"]) == update_data["unit_price"]
        assert float(data["total_price"]) == 20 * 85.0

    async def test_delete_quotation_item(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test deleting quotation item."""
        quotation = QuotationFactory()
        item = QuotationItemFactory(quotation=quotation)
        
        async_db_session.add(quotation)
        async_db_session.add(item)
        await async_db_session.commit()
        
        response = await async_client.delete(
            f"/api/v1/quotations/{quotation.id}/items/{item.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_quotation_items_calculation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation total calculation with items."""
        quotation = QuotationFactory()
        
        # Create items with different prices
        item1 = QuotationItemFactory(
            quotation=quotation,
            quantity=10,
            unit_price=100.0
        )
        item2 = QuotationItemFactory(
            quotation=quotation,
            quantity=5,
            unit_price=200.0
        )
        
        async_db_session.add(quotation)
        async_db_session.add(item1)
        async_db_session.add(item2)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/quotations/{quotation.id}/summary",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_items"] == 2
        assert float(data["total_value"]) == 2000.0  # (10*100) + (5*200)
        assert data["items_summary"][0]["total_price"] == 1000.0
        assert data["items_summary"][1]["total_price"] == 1000.0


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsValidation:
    """Test quotation validation rules."""

    async def test_quotation_title_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation title validation."""
        test_cases = [
            ("", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty title
            ("a", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too short
            ("A" * 500, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too long
            ("Valid Quotation Title", status.HTTP_201_CREATED),  # Valid title
        ]
        
        for title, expected_status in test_cases:
            quotation_data = {
                "title": title,
                "description": "Test description",
                "status": "DRAFT",
                "priority": "MEDIUM",
                "estimated_value": 10000.0,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/quotations",
                json=quotation_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_quotation_estimated_value_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation estimated value validation."""
        test_cases = [
            (-1000, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Negative value
            (0, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Zero value
            (10000.50, status.HTTP_201_CREATED),  # Valid value
        ]
        
        for value, expected_status in test_cases:
            quotation_data = {
                "title": "Test Quotation",
                "description": "Test description",
                "status": "DRAFT",
                "priority": "MEDIUM",
                "estimated_value": value,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/quotations",
                json=quotation_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_quotation_deadline_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation deadline validation."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        test_cases = [
            (str(yesterday), status.HTTP_422_UNPROCESSABLE_ENTITY),  # Past deadline
            (str(tomorrow), status.HTTP_201_CREATED),  # Future deadline
            (str(today), status.HTTP_201_CREATED),  # Today deadline
        ]
        
        for deadline, expected_status in test_cases:
            quotation_data = {
                "title": "Test Quotation",
                "description": "Test description",
                "status": "DRAFT",
                "priority": "MEDIUM",
                "estimated_value": 10000.0,
                "deadline": deadline
            }
            
            response = await async_client.post(
                "/api/v1/quotations",
                json=quotation_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_quotation_enum_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation enum fields validation."""
        valid_quotation_data = {
            "title": "Test Quotation",
            "description": "Test description",
            "estimated_value": 10000.0,
            "deadline": "2025-12-31"
        }
        
        # Test status validation
        status_cases = [
            ("DRAFT", status.HTTP_201_CREATED),
            ("ACTIVE", status.HTTP_201_CREATED),
            ("IN_PROGRESS", status.HTTP_201_CREATED),
            ("COMPLETED", status.HTTP_201_CREATED),
            ("CANCELLED", status.HTTP_201_CREATED),
            ("INVALID_STATUS", status.HTTP_422_UNPROCESSABLE_ENTITY),
        ]
        
        for status_value, expected_status in status_cases:
            quotation_data = {
                **valid_quotation_data,
                "status": status_value,
                "priority": "MEDIUM"
            }
            
            response = await async_client.post(
                "/api/v1/quotations",
                json=quotation_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_quotation_item_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation item validation."""
        quotation = QuotationFactory()
        supplier = SupplierFactory()
        
        async_db_session.add(quotation)
        async_db_session.add(supplier)
        await async_db_session.commit()
        
        # Test invalid item data
        invalid_item_data = {
            "item_number": 0,  # Invalid item number
            "description": "",  # Empty description
            "quantity": -5,  # Negative quantity
            "unit": "",  # Empty unit
            "unit_price": -100.0,  # Negative price
            "supplier_id": str(supplier.id)
        }
        
        response = await async_client.post(
            f"/api/v1/quotations/{quotation.id}/items",
            json=invalid_item_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsPermissions:
    """Test role-based access control for quotations."""

    async def test_quotation_read_permission_user(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test user read permission for quotations."""
        user = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"quotations": {"read": True}}
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

    async def test_quotation_write_permission_denied(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test user write permission denied for quotations."""
        user = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"quotations": {"read": True, "write": False}}
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
        
        quotation_data = {
            "title": "Test Quotation",
            "description": "Test description",
            "status": "DRAFT",
            "priority": "MEDIUM",
            "estimated_value": 10000.0,
            "deadline": "2025-12-31"
        }
        
        response = await async_client.post(
            "/api/v1/quotations",
            json=quotation_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_quotation_ownership_access_control(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test ownership-based access control for quotations."""
        owner = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"quotations": {"read": True, "write": True}}
        )
        other_user = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"quotations": {"read": True, "write": True}}
        )
        quotation = QuotationFactory(created_by=owner)
        
        async_db_session.add(owner)
        async_db_session.add(other_user)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Generate auth headers for other user
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(other_user.id), "email": other_user.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Other user should not be able to update quotation they don't own
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json={"title": "Unauthorized Update"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_quotation_admin_full_access(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test admin full access to quotations."""
        admin = AdminUserFactory(is_verified=True)
        user = UserFactory(is_verified=True)
        quotation = QuotationFactory(created_by=user)
        
        async_db_session.add(admin)
        async_db_session.add(user)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Generate admin auth headers
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.create_access_token(
            data={"sub": str(admin.id), "email": admin.email}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Admin should be able to update any quotation
        response = await async_client.put(
            f"/api/v1/quotations/{quotation.id}",
            json={"title": "Updated by Admin"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.api
@pytest.mark.asyncio
class TestQuotationsIntegration:
    """Test quotation integration with other systems."""

    async def test_quotation_from_tender(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test creating quotation from tender."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        quotation_data = {
            "title": "Quotation from Tender",
            "description": "Auto-generated from tender",
            "tender_id": str(tender.id),
            "status": "DRAFT",
            "priority": "MEDIUM",
            "estimated_value": 75000.0,
            "deadline": "2025-02-15"
        }
        
        response = await async_client.post(
            "/api/v1/quotations",
            json=quotation_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tender"]["id"] == str(tender.id)
        assert data["tender"]["title"] == tender.title

    async def test_quotation_supplier_integration(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation integration with suppliers."""
        quotation = QuotationFactory()
        supplier = SupplierFactory()
        
        async_db_session.add(quotation)
        async_db_session.add(supplier)
        await async_db_session.commit()
        
        # Add supplier to quotation
        response = await async_client.post(
            f"/api/v1/quotations/{quotation.id}/suppliers",
            json={"supplier_id": str(supplier.id)},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["supplier"]["id"] == str(supplier.id)

    async def test_quotation_document_upload(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test document upload for quotations."""
        quotation = QuotationFactory()
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Mock file upload
        files = {
            "file": ("quotation_document.pdf", b"quotation content", "application/pdf")
        }
        
        response = await async_client.post(
            f"/api/v1/quotations/{quotation.id}/documents",
            files=files,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "quotation_document.pdf"
        assert data["mime_type"] == "application/pdf"

    @patch('app.services.notification_service.NotificationService')
    async def test_quotation_deadline_notifications(
        self, mock_notification_service, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test deadline notifications for quotations."""
        # Mock notification service
        mock_notification = Mock()
        mock_notification.send_deadline_reminder.return_value = True
        mock_notification_service.return_value = mock_notification
        
        # Create quotation with deadline in 3 days
        deadline = date.today() + timedelta(days=3)
        quotation = QuotationFactory(deadline=deadline)
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Trigger deadline check
        response = await async_client.post(
            "/api/v1/quotations/check-deadlines",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notifications_sent"] > 0

    async def test_quotation_export_formats(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation export in different formats."""
        quotation = CompleteQuotationFactory()
        async_db_session.add(quotation)
        await async_db_session.commit()
        
        # Test PDF export
        response = await async_client.get(
            f"/api/v1/quotations/{quotation.id}/export?format=pdf",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        
        # Test Excel export
        response = await async_client.get(
            f"/api/v1/quotations/{quotation.id}/export?format=xlsx",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "spreadsheet" in response.headers["content-type"]

    async def test_quotation_analytics(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test quotation analytics and reporting."""
        # Create quotations with different statuses
        quotations = [
            QuotationFactory(status=QuotationStatus.DRAFT),
            QuotationFactory(status=QuotationStatus.ACTIVE),
            QuotationFactory(status=QuotationStatus.COMPLETED),
            QuotationFactory(status=QuotationStatus.COMPLETED),
        ]
        
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/quotations/analytics",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_quotations"] == 4
        assert data["status_distribution"]["DRAFT"] == 1
        assert data["status_distribution"]["ACTIVE"] == 1
        assert data["status_distribution"]["COMPLETED"] == 2


@pytest.mark.api
@pytest.mark.performance
@pytest.mark.asyncio
class TestQuotationsPerformance:
    """Test quotation API performance."""

    async def test_quotation_list_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of quotation listing."""
        # Create many quotations
        quotations = [QuotationFactory() for _ in range(100)]
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/quotations?page=1&size=20",
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 2.0  # Should complete within 2 seconds

    async def test_quotation_creation_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of quotation creation."""
        quotation_data = {
            "title": "Performance Test Quotation",
            "description": "Test quotation for performance testing",
            "status": "DRAFT",
            "priority": "MEDIUM",
            "estimated_value": 10000.0,
            "deadline": "2025-12-31"
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/quotations",
            json=quotation_data,
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_201_CREATED
        assert end_time - start_time < 1.0  # Should complete within 1 second

    async def test_quotation_bulk_operations_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of bulk quotation operations."""
        # Create many quotations
        quotations = [QuotationFactory() for _ in range(50)]
        for quotation in quotations:
            async_db_session.add(quotation)
        await async_db_session.commit()
        
        quotation_ids = [str(q.id) for q in quotations]
        
        bulk_update_data = {
            "quotation_ids": quotation_ids,
            "status": "ACTIVE"
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.put(
            "/api/v1/quotations/bulk",
            json=bulk_update_data,
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 3.0  # Should complete within 3 seconds
        
        data = response.json()
        assert data["updated_count"] == 50