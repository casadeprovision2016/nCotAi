"""
Test configuration and fixtures for COTAI backend tests.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService

# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

fake = Faker()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
async def async_db_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    AsyncTestingSessionLocal = sessionmaker(
        async_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncTestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with dependency overrides."""
    
    async def override_get_db():
        try:
            yield async_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.ttl.return_value = 3600
    return mock_redis


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client for testing."""
    mock_mongodb = Mock()
    mock_collection = Mock()
    mock_mongodb.__getitem__.return_value = mock_collection
    mock_collection.insert_one.return_value = Mock(inserted_id="test_id")
    mock_collection.find_one.return_value = None
    mock_collection.update_one.return_value = Mock(modified_count=1)
    mock_collection.delete_one.return_value = Mock(deleted_count=1)
    return mock_mongodb


@pytest.fixture
def mock_celery():
    """Mock Celery tasks for testing."""
    mock_celery = Mock()
    mock_celery.delay.return_value = Mock(id="test_task_id")
    mock_celery.apply_async.return_value = Mock(id="test_task_id")
    return mock_celery


@pytest.fixture
def test_user_data():
    """Generate test user data."""
    return {
        "email": fake.email(),
        "password": "TestPassword123!",
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "company_name": fake.company(),
        "role": "USER",
        "is_active": True,
        "is_verified": True,
        "mfa_enabled": False,
    }


@pytest.fixture
def admin_user_data():
    """Generate admin user data."""
    return {
        "email": "admin@cotai.com",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "company_name": "COTAI",
        "role": "ADMIN",
        "is_active": True,
        "is_verified": True,
        "mfa_enabled": False,
    }


@pytest.fixture
async def test_user(async_db_session: AsyncSession, test_user_data: dict) -> User:
    """Create a test user in the database."""
    user_service = UserService(async_db_session)
    user = await user_service.create_user(test_user_data)
    await async_db_session.commit()
    return user


@pytest.fixture
async def admin_user(async_db_session: AsyncSession, admin_user_data: dict) -> User:
    """Create an admin user in the database."""
    user_service = UserService(async_db_session)
    user = await user_service.create_user(admin_user_data)
    await async_db_session.commit()
    return user


@pytest.fixture
async def authenticated_headers(test_user: User) -> dict:
    """Generate authentication headers for test user."""
    auth_service = AuthService()
    access_token = auth_service.create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def admin_headers(admin_user: User) -> dict:
    """Generate authentication headers for admin user."""
    auth_service = AuthService()
    access_token = auth_service.create_access_token(
        data={"sub": str(admin_user.id), "email": admin_user.email}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_whatsapp_service():
    """Mock WhatsApp service for testing."""
    mock_service = Mock()
    mock_service.send_message.return_value = {"success": True, "message_id": "test_id"}
    mock_service.send_template.return_value = {"success": True, "message_id": "test_id"}
    mock_service.get_health.return_value = {"status": "healthy"}
    return mock_service


@pytest.fixture
def mock_cloud_storage_service():
    """Mock cloud storage service for testing."""
    mock_service = Mock()
    mock_service.upload_file.return_value = {"success": True, "file_id": "test_file_id"}
    mock_service.download_file.return_value = b"test_file_content"
    mock_service.delete_file.return_value = {"success": True}
    mock_service.list_files.return_value = {"files": []}
    return mock_service


@pytest.fixture
def mock_team_notifications_service():
    """Mock team notifications service for testing."""
    mock_service = Mock()
    mock_service.send_notification.return_value = {"success": True, "message_id": "test_id"}
    mock_service.get_channels.return_value = {"channels": []}
    mock_service.get_health.return_value = {"status": "healthy"}
    return mock_service


@pytest.fixture
def mock_government_api():
    """Mock government API responses for testing."""
    mock_api = Mock()
    mock_api.get_tender_data.return_value = {
        "id": "test_tender_id",
        "title": "Test Tender",
        "description": "Test tender description",
        "estimated_value": 100000.0,
        "deadline": "2025-12-31",
        "agency": "Test Agency",
    }
    mock_api.validate_cnpj.return_value = {"valid": True, "company_name": "Test Company"}
    return mock_api


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    mock_limiter = Mock()
    mock_limiter.is_allowed.return_value = True
    mock_limiter.get_remaining.return_value = 10
    mock_limiter.reset.return_value = None
    return mock_limiter


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    mock_logger = Mock()
    mock_logger.log_action.return_value = None
    mock_logger.log_security_event.return_value = None
    mock_logger.log_api_access.return_value = None
    return mock_logger


@pytest.fixture
def test_environment():
    """Set test environment variables."""
    original_env = os.environ.copy()
    
    # Override environment variables for testing
    os.environ.update({
        "TESTING": "True",
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_URL": "redis://localhost:6379/15",  # Use different Redis DB for tests
        "JWT_SECRET_KEY": "test_secret_key",
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def setup_test_environment(test_environment):
    """Automatically setup test environment for all tests."""
    pass


# Performance testing fixtures
@pytest.fixture
def performance_test_data():
    """Generate data for performance tests."""
    return {
        "users": [
            {
                "email": f"user{i}@test.com",
                "password": "TestPassword123!",
                "first_name": f"User{i}",
                "last_name": "Test",
                "company_name": f"Company{i}",
                "role": "USER",
                "is_active": True,
                "is_verified": True,
            }
            for i in range(100)
        ],
        "tenders": [
            {
                "title": f"Test Tender {i}",
                "description": f"Test tender description {i}",
                "estimated_value": 100000.0 + i * 1000,
                "deadline": "2025-12-31",
                "agency": f"Test Agency {i}",
            }
            for i in range(50)
        ],
        "quotations": [
            {
                "title": f"Test Quotation {i}",
                "description": f"Test quotation description {i}",
                "estimated_value": 50000.0 + i * 500,
                "status": "DRAFT",
                "priority": "MEDIUM",
            }
            for i in range(30)
        ],
    }


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Generate security test payloads."""
    return {
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
        ],
        "sql_injection_payloads": [
            "' OR '1'='1",
            "1; DROP TABLE users;--",
            "' UNION SELECT * FROM users--",
            "admin'--",
        ],
        "csrf_payloads": [
            {"csrf_token": "invalid_token"},
            {"csrf_token": ""},
            {},  # Missing CSRF token
        ],
        "malicious_files": [
            {"filename": "test.exe", "content": b"malicious content"},
            {"filename": "../../../etc/passwd", "content": b"sensitive content"},
            {"filename": "test.php", "content": b"<?php phpinfo(); ?>"},
        ],
    }


@pytest.fixture
def integration_test_mocks():
    """Comprehensive mocks for integration tests."""
    return {
        "whatsapp": mock_whatsapp_service,
        "cloud_storage": mock_cloud_storage_service,
        "team_notifications": mock_team_notifications_service,
        "government_api": mock_government_api,
        "redis": mock_redis,
        "mongodb": mock_mongodb,
        "celery": mock_celery,
    }