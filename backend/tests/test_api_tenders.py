"""
Tender API endpoint tests for COTAI backend.
Tests for CRUD operations, validation, filtering, permissions, and AI integration.
"""
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender, TenderStatus, TenderCategory, TenderType
from app.models.user import User, UserRole
from tests.factories import (
    TenderFactory,
    TenderWithItemsFactory,
    TenderWithDocumentsFactory,
    CompleteTenderFactory,
    TenderItemFactory,
    TenderDocumentFactory,
    GovernmentEntityFactory,
    UserFactory,
    AdminUserFactory,
)


@pytest.mark.api
@pytest.mark.asyncio
class TestTendersCRUD:
    """Test basic CRUD operations for tenders."""

    async def test_create_tender_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful tender creation."""
        government_entity = GovernmentEntityFactory()
        async_db_session.add(government_entity)
        await async_db_session.commit()
        
        tender_data = {
            "title": "Test Tender Creation",
            "description": "Test tender description for creation",
            "government_entity_id": str(government_entity.id),
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 150000.50,
            "publication_date": "2025-01-15",
            "deadline": "2025-02-15",
            "opening_date": "2025-02-20",
            "external_id": "EXT-12345",
            "external_url": "https://example.gov.br/tender/12345",
            "requirements": {
                "qualification": "Advanced",
                "experience": "5 years",
                "certifications": ["ISO 9001"]
            },
            "evaluation_criteria": {
                "price": 60,
                "technical": 30,
                "delivery": 10
            }
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == tender_data["title"]
        assert data["description"] == tender_data["description"]
        assert data["category"] == tender_data["category"]
        assert data["type"] == tender_data["type"]
        assert float(data["estimated_value"]) == tender_data["estimated_value"]
        assert data["status"] == "DRAFT"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_tender_validation_error(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender creation with validation errors."""
        invalid_tender_data = {
            "title": "",  # Empty title
            "description": "Test description",
            "category": "INVALID_CATEGORY",
            "type": "INVALID_TYPE",
            "estimated_value": -1000,  # Negative value
            "deadline": "2023-01-01",  # Past date
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=invalid_tender_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data
        assert len(error_data["detail"]) > 0

    async def test_create_tender_unauthorized(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender creation without authentication."""
        tender_data = {
            "title": "Test Tender",
            "description": "Test description",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        response = await async_client.post("/api/v1/tenders", json=tender_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_tender_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful tender retrieval."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        response = await async_client.get(
            f"/api/v1/tenders/{tender.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(tender.id)
        assert data["title"] == tender.title
        assert data["description"] == tender.description
        assert data["category"] == tender.category.value
        assert data["type"] == tender.type.value
        assert data["status"] == tender.status.value

    async def test_get_tender_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test retrieval of non-existent tender."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.get(
            f"/api/v1/tenders/{non_existent_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_tender_unauthorized(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test tender retrieval without authentication."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        response = await async_client.get(f"/api/v1/tenders/{tender.id}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_tender_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful tender update."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        update_data = {
            "title": "Updated Tender Title",
            "description": "Updated description",
            "estimated_value": 200000.0,
            "status": "ACTIVE"
        }
        
        response = await async_client.put(
            f"/api/v1/tenders/{tender.id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert float(data["estimated_value"]) == update_data["estimated_value"]
        assert data["status"] == update_data["status"]

    async def test_update_tender_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test updating non-existent tender."""
        non_existent_id = str(uuid.uuid4())
        update_data = {"title": "Updated Title"}
        
        response = await async_client.put(
            f"/api/v1/tenders/{non_existent_id}",
            json=update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_tender_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful tender deletion."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        response = await async_client.delete(
            f"/api/v1/tenders/{tender.id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_tender_not_found(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test deleting non-existent tender."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.delete(
            f"/api/v1/tenders/{non_existent_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_tenders_success(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test successful tender listing."""
        # Create multiple tenders
        tenders = [TenderFactory() for _ in range(5)]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/tenders",
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

    async def test_list_tenders_pagination(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender listing with pagination."""
        # Create multiple tenders
        tenders = [TenderFactory() for _ in range(10)]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        response = await async_client.get(
            "/api/v1/tenders?page=1&size=5",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["size"] == 5
        assert data["total"] == 10

    async def test_list_tenders_empty(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender listing with no tenders."""
        response = await async_client.get(
            "/api/v1/tenders",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


@pytest.mark.api
@pytest.mark.asyncio
class TestTendersValidation:
    """Test tender validation rules and error handling."""

    async def test_tender_title_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender title validation."""
        test_cases = [
            ("", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Empty title
            ("a", status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too short
            ("A" * 500, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Too long
            ("Valid Title", status.HTTP_201_CREATED),  # Valid title
        ]
        
        for title, expected_status in test_cases:
            tender_data = {
                "title": title,
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
            
            assert response.status_code == expected_status

    async def test_tender_estimated_value_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender estimated value validation."""
        test_cases = [
            (-1000, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Negative value
            (0, status.HTTP_422_UNPROCESSABLE_ENTITY),  # Zero value
            (100000.50, status.HTTP_201_CREATED),  # Valid value
            (999999999.99, status.HTTP_201_CREATED),  # Large valid value
        ]
        
        for value, expected_status in test_cases:
            tender_data = {
                "title": "Test Tender",
                "description": "Test description",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": value,
                "deadline": "2025-12-31"
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_tender_date_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender date validation."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        test_cases = [
            (str(yesterday), status.HTTP_422_UNPROCESSABLE_ENTITY),  # Past deadline
            (str(tomorrow), status.HTTP_201_CREATED),  # Future deadline
            (str(today), status.HTTP_201_CREATED),  # Today deadline
        ]
        
        for deadline, expected_status in test_cases:
            tender_data = {
                "title": "Test Tender",
                "description": "Test description",
                "category": "GOODS",
                "type": "OPEN",
                "estimated_value": 100000.0,
                "deadline": deadline
            }
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_tender_enum_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender enum fields validation."""
        valid_tender_data = {
            "title": "Test Tender",
            "description": "Test description",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        # Test category validation
        category_cases = [
            ("GOODS", status.HTTP_201_CREATED),
            ("SERVICES", status.HTTP_201_CREATED),
            ("WORKS", status.HTTP_201_CREATED),
            ("INVALID_CATEGORY", status.HTTP_422_UNPROCESSABLE_ENTITY),
        ]
        
        for category, expected_status in category_cases:
            tender_data = {**valid_tender_data, "category": category, "type": "OPEN"}
            
            response = await async_client.post(
                "/api/v1/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_status

    async def test_tender_json_field_validation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender JSON field validation."""
        base_tender_data = {
            "title": "Test Tender",
            "description": "Test description",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        # Test valid JSON fields
        valid_data = {
            **base_tender_data,
            "requirements": {"qualification": "Basic", "experience": "2 years"},
            "evaluation_criteria": {"price": 70, "technical": 30}
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=valid_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["requirements"] == valid_data["requirements"]
        assert data["evaluation_criteria"] == valid_data["evaluation_criteria"]


@pytest.mark.api
@pytest.mark.asyncio
class TestTendersFiltering:
    """Test tender filtering, search, and pagination."""

    async def test_filter_tenders_by_status(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test filtering tenders by status."""
        # Create tenders with different statuses
        draft_tender = TenderFactory(status=TenderStatus.DRAFT)
        active_tender = TenderFactory(status=TenderStatus.ACTIVE)
        closed_tender = TenderFactory(status=TenderStatus.CLOSED)
        
        async_db_session.add(draft_tender)
        async_db_session.add(active_tender)
        async_db_session.add(closed_tender)
        await async_db_session.commit()
        
        # Filter by ACTIVE status
        response = await async_client.get(
            "/api/v1/tenders?status=ACTIVE",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "ACTIVE"

    async def test_filter_tenders_by_category(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test filtering tenders by category."""
        # Create tenders with different categories
        goods_tender = TenderFactory(category=TenderCategory.GOODS)
        services_tender = TenderFactory(category=TenderCategory.SERVICES)
        works_tender = TenderFactory(category=TenderCategory.WORKS)
        
        async_db_session.add(goods_tender)
        async_db_session.add(services_tender)
        async_db_session.add(works_tender)
        await async_db_session.commit()
        
        # Filter by GOODS category
        response = await async_client.get(
            "/api/v1/tenders?category=GOODS",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category"] == "GOODS"

    async def test_filter_tenders_by_value_range(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test filtering tenders by value range."""
        # Create tenders with different values
        low_value_tender = TenderFactory(estimated_value=50000.0)
        medium_value_tender = TenderFactory(estimated_value=150000.0)
        high_value_tender = TenderFactory(estimated_value=500000.0)
        
        async_db_session.add(low_value_tender)
        async_db_session.add(medium_value_tender)
        async_db_session.add(high_value_tender)
        await async_db_session.commit()
        
        # Filter by value range
        response = await async_client.get(
            "/api/v1/tenders?min_value=100000&max_value=200000",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert float(data["items"][0]["estimated_value"]) == 150000.0

    async def test_filter_tenders_by_date_range(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test filtering tenders by date range."""
        # Create tenders with different deadlines
        early_tender = TenderFactory(deadline=date(2025, 1, 15))
        middle_tender = TenderFactory(deadline=date(2025, 6, 15))
        late_tender = TenderFactory(deadline=date(2025, 12, 15))
        
        async_db_session.add(early_tender)
        async_db_session.add(middle_tender)
        async_db_session.add(late_tender)
        await async_db_session.commit()
        
        # Filter by date range
        response = await async_client.get(
            "/api/v1/tenders?deadline_from=2025-05-01&deadline_to=2025-07-01",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["deadline"] == "2025-06-15"

    async def test_search_tenders_by_title(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test searching tenders by title."""
        # Create tenders with different titles
        construction_tender = TenderFactory(title="Construction Project Alpha")
        software_tender = TenderFactory(title="Software Development Beta")
        maintenance_tender = TenderFactory(title="Maintenance Services Gamma")
        
        async_db_session.add(construction_tender)
        async_db_session.add(software_tender)
        async_db_session.add(maintenance_tender)
        await async_db_session.commit()
        
        # Search for "Software"
        response = await async_client.get(
            "/api/v1/tenders?search=Software",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert "Software" in data["items"][0]["title"]

    async def test_search_tenders_by_description(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test searching tenders by description."""
        # Create tenders with different descriptions
        tender1 = TenderFactory(
            title="Project A",
            description="Building construction with steel framework"
        )
        tender2 = TenderFactory(
            title="Project B",
            description="Software development with Python framework"
        )
        tender3 = TenderFactory(
            title="Project C",
            description="Maintenance services for equipment"
        )
        
        async_db_session.add(tender1)
        async_db_session.add(tender2)
        async_db_session.add(tender3)
        await async_db_session.commit()
        
        # Search for "framework"
        response = await async_client.get(
            "/api/v1/tenders?search=framework",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2

    async def test_combined_filters(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test combining multiple filters."""
        # Create tenders with specific combinations
        target_tender = TenderFactory(
            title="Target Tender",
            category=TenderCategory.GOODS,
            status=TenderStatus.ACTIVE,
            estimated_value=150000.0
        )
        other_tender = TenderFactory(
            title="Other Tender",
            category=TenderCategory.SERVICES,
            status=TenderStatus.ACTIVE,
            estimated_value=150000.0
        )
        
        async_db_session.add(target_tender)
        async_db_session.add(other_tender)
        await async_db_session.commit()
        
        # Apply multiple filters
        response = await async_client.get(
            "/api/v1/tenders?category=GOODS&status=ACTIVE&search=Target",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Target Tender"

    async def test_pagination_with_filters(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test pagination combined with filters."""
        # Create multiple tenders with same category
        tenders = [
            TenderFactory(category=TenderCategory.GOODS) for _ in range(10)
        ]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        # Get first page with filter
        response = await async_client.get(
            "/api/v1/tenders?category=GOODS&page=1&size=5",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["size"] == 5
        assert data["total"] == 10

    async def test_sorting_tenders(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test sorting tenders."""
        # Create tenders with different creation dates
        tender1 = TenderFactory(
            title="A Tender",
            estimated_value=100000.0,
            created_at=datetime(2025, 1, 1)
        )
        tender2 = TenderFactory(
            title="B Tender",
            estimated_value=200000.0,
            created_at=datetime(2025, 1, 2)
        )
        tender3 = TenderFactory(
            title="C Tender",
            estimated_value=50000.0,
            created_at=datetime(2025, 1, 3)
        )
        
        async_db_session.add(tender1)
        async_db_session.add(tender2)
        async_db_session.add(tender3)
        await async_db_session.commit()
        
        # Sort by estimated value descending
        response = await async_client.get(
            "/api/v1/tenders?sort_by=estimated_value&sort_order=desc",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        
        # Check sorting order
        values = [float(item["estimated_value"]) for item in data["items"]]
        assert values == sorted(values, reverse=True)


@pytest.mark.api
@pytest.mark.asyncio
class TestTendersPermissions:
    """Test role-based access control for tenders."""

    async def test_tender_read_permission_user(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test user read permission for tenders."""
        user = UserFactory(
            role=UserRole.USER,
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

    async def test_tender_write_permission_denied(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test user write permission denied for tenders."""
        user = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"tenders": {"read": True, "write": False}}
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
            "description": "Test description",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_tender_admin_full_access(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test admin full access to tenders."""
        admin = AdminUserFactory(is_verified=True)
        user = UserFactory(is_verified=True)
        tender = TenderFactory(created_by=user)
        
        async_db_session.add(admin)
        async_db_session.add(user)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Generate admin auth headers
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

    async def test_tender_ownership_access_control(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test ownership-based access control."""
        owner = UserFactory(
            role=UserRole.USER,
            is_verified=True,
            permissions={"tenders": {"read": True, "write": True}}
        )
        other_user = UserFactory(
            role=UserRole.USER,
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
            json={"title": "Unauthorized Update"},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
@pytest.mark.asyncio
class TestTendersIntegration:
    """Test tender integration with AI, documents, and items."""

    async def test_tender_with_items_creation(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test creating tender with items."""
        tender_data = {
            "title": "Tender with Items",
            "description": "Test tender with items",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31",
            "items": [
                {
                    "item_number": 1,
                    "description": "Item 1 description",
                    "quantity": 10,
                    "unit": "pieces",
                    "estimated_unit_price": 100.0,
                    "specifications": {"material": "Steel", "size": "Large"}
                },
                {
                    "item_number": 2,
                    "description": "Item 2 description",
                    "quantity": 5,
                    "unit": "units",
                    "estimated_unit_price": 200.0,
                    "specifications": {"material": "Aluminum", "size": "Medium"}
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["item_number"] == 1
        assert data["items"][0]["quantity"] == 10
        assert float(data["items"][0]["estimated_unit_price"]) == 100.0

    @patch('app.services.ai_service.AIService')
    async def test_tender_ai_scoring(
        self, mock_ai_service, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test AI scoring for tenders."""
        # Mock AI service
        mock_ai_instance = Mock()
        mock_ai_instance.score_tender.return_value = {
            "score": 8.5,
            "analysis": {
                "keyword_match": 0.9,
                "historical_success": 0.8,
                "profile_alignment": 0.85,
                "timeframe_fit": 0.9,
                "value_capacity": 0.8
            },
            "recommendations": [
                "High relevance for your company profile",
                "Historical success rate: 75%",
                "Recommended participation"
            ]
        }
        mock_ai_service.return_value = mock_ai_instance
        
        tender_data = {
            "title": "AI Scored Tender",
            "description": "Test tender for AI scoring",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31",
            "enable_ai_scoring": True
        }
        
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "ai_score" in data
        assert "ai_analysis" in data
        assert data["ai_score"] == 8.5
        assert data["ai_analysis"]["keyword_match"] == 0.9

    async def test_tender_document_upload(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test document upload for tenders."""
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Mock file upload
        files = {
            "file": ("test_document.pdf", b"test content", "application/pdf")
        }
        
        response = await async_client.post(
            f"/api/v1/tenders/{tender.id}/documents",
            files=files,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "test_document.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["document_type"] == "EDICT"

    async def test_tender_status_workflow(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender status workflow transitions."""
        tender = TenderFactory(status=TenderStatus.DRAFT)
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Test valid status transitions
        valid_transitions = [
            ("ACTIVE", status.HTTP_200_OK),
            ("SUSPENDED", status.HTTP_200_OK),
            ("ACTIVE", status.HTTP_200_OK),
            ("CLOSED", status.HTTP_200_OK),
        ]
        
        for new_status, expected_code in valid_transitions:
            response = await async_client.put(
                f"/api/v1/tenders/{tender.id}",
                json={"status": new_status},
                headers=authenticated_headers
            )
            
            assert response.status_code == expected_code
            if expected_code == status.HTTP_200_OK:
                data = response.json()
                assert data["status"] == new_status

    async def test_tender_bulk_operations(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test bulk operations on tenders."""
        # Create multiple tenders
        tenders = [TenderFactory() for _ in range(5)]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        tender_ids = [str(tender.id) for tender in tenders]
        
        # Test bulk status update
        bulk_update_data = {
            "tender_ids": tender_ids,
            "status": "ACTIVE"
        }
        
        response = await async_client.put(
            "/api/v1/tenders/bulk",
            json=bulk_update_data,
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 5

    async def test_tender_export(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test tender data export."""
        # Create multiple tenders
        tenders = [TenderFactory() for _ in range(3)]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        # Test CSV export
        response = await async_client.get(
            "/api/v1/tenders/export?format=csv",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"
        
        # Test Excel export
        response = await async_client.get(
            "/api/v1/tenders/export?format=xlsx",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]


@pytest.mark.api
@pytest.mark.performance
@pytest.mark.asyncio
class TestTendersPerformance:
    """Test tender API performance and scalability."""

    async def test_tender_list_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of tender listing with large dataset."""
        # Create many tenders
        tenders = [TenderFactory() for _ in range(100)]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/tenders?page=1&size=20",
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 2.0  # Should complete within 2 seconds

    async def test_tender_search_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of tender search functionality."""
        # Create many tenders with searchable content
        tenders = [
            TenderFactory(title=f"Construction Project {i}") for i in range(50)
        ]
        for tender in tenders:
            async_db_session.add(tender)
        await async_db_session.commit()
        
        import time
        
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/tenders?search=Construction&page=1&size=20",
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 1.5  # Should complete within 1.5 seconds
        
        data = response.json()
        assert len(data["items"]) == 20  # Should return paginated results

    async def test_tender_creation_performance(
        self, async_client: AsyncClient, async_db_session: AsyncSession, authenticated_headers: dict
    ):
        """Test performance of tender creation."""
        tender_data = {
            "title": "Performance Test Tender",
            "description": "Test tender for performance testing",
            "category": "GOODS",
            "type": "OPEN",
            "estimated_value": 100000.0,
            "deadline": "2025-12-31"
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/tenders",
            json=tender_data,
            headers=authenticated_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_201_CREATED
        assert end_time - start_time < 1.0  # Should complete within 1 second