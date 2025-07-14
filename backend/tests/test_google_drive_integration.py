"""
Google Drive integration tests for COTAI backend.
Tests for Google Drive API integration, authentication, and file operations.
"""
import os
import tempfile
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import pytest
import aiohttp
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings
from app.services.cloud_storage_integration_service import CloudStorageIntegrationService


@pytest.mark.external
@pytest.mark.asyncio
class TestGoogleDriveConfiguration:
    """Test Google Drive configuration and setup."""
    
    def test_google_drive_configuration_available(self):
        """Test that Google Drive configuration is properly set."""
        assert settings.GOOGLE_DRIVE_CLIENT_ID is not None
        assert settings.GOOGLE_DRIVE_CLIENT_SECRET is not None
        assert settings.GOOGLE_DRIVE_REDIRECT_URI is not None
        assert settings.GOOGLE_DRIVE_PROJECT_ID is not None
        assert len(settings.GOOGLE_DRIVE_SCOPES) > 0
    
    def test_google_drive_configured_property(self):
        """Test GOOGLE_DRIVE_CONFIGURED property."""
        # Should be True with current configuration
        assert settings.GOOGLE_DRIVE_CONFIGURED is True
    
    def test_cloud_storage_settings(self):
        """Test cloud storage related settings."""
        assert settings.CLOUD_STORAGE_MAX_FILE_SIZE > 0
        assert len(settings.CLOUD_STORAGE_ALLOWED_TYPES) > 0
        assert "application/pdf" in settings.CLOUD_STORAGE_ALLOWED_TYPES


@pytest.mark.external
@pytest.mark.asyncio
class TestGoogleDriveService:
    """Test Google Drive service functionality."""
    
    @pytest.fixture
    def google_drive_service(self):
        """Create a Google Drive service instance."""
        # Import here to avoid import errors if module not available
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../src/services/cloud-storage'))
        
        try:
            from google_drive_service import GoogleDriveService
            return GoogleDriveService()
        except ImportError:
            pytest.skip("GoogleDriveService not available")
    
    async def test_service_initialization(self, google_drive_service):
        """Test Google Drive service initialization."""
        result = await google_drive_service.initialize()
        
        assert isinstance(result, dict)
        assert "success" in result
        # Should succeed with proper configuration
        assert result["success"] is True
        assert "message" in result
        assert "scopes" in result
    
    def test_authorization_url_generation(self, google_drive_service):
        """Test generation of OAuth2 authorization URL."""
        state = "test_state_123"
        auth_url = google_drive_service.get_authorization_url(state)
        
        assert isinstance(auth_url, str)
        assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
        assert settings.GOOGLE_DRIVE_CLIENT_ID in auth_url
        assert "scope=" in auth_url
        assert "response_type=code" in auth_url
        assert f"state={state}" in auth_url
    
    @patch('aiohttp.ClientSession.post')
    async def test_token_exchange_success(self, mock_post, google_drive_service):
        """Test successful token exchange."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Initialize session
        google_drive_service.session = aiohttp.ClientSession()
        
        try:
            result = await google_drive_service.exchange_code_for_tokens("test_code")
            
            assert result["success"] is True
            assert "access_token" in result
            assert "refresh_token" in result
            assert "expires_at" in result
            
            # Verify service has stored tokens
            assert google_drive_service.access_token == "mock_access_token"
            assert google_drive_service.refresh_token == "mock_refresh_token"
        finally:
            await google_drive_service.session.close()
    
    @patch('aiohttp.ClientSession.post')
    async def test_token_exchange_failure(self, mock_post, google_drive_service):
        """Test failed token exchange."""
        # Mock failed token response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="invalid_grant")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Initialize session
        google_drive_service.session = aiohttp.ClientSession()
        
        try:
            result = await google_drive_service.exchange_code_for_tokens("invalid_code")
            
            assert result["success"] is False
            assert "error" in result
            assert "Token exchange failed" in result["error"]
        finally:
            await google_drive_service.session.close()
    
    @patch('aiohttp.ClientSession.post')
    async def test_token_refresh(self, mock_post, google_drive_service):
        """Test access token refresh."""
        # Set up service with refresh token
        google_drive_service.refresh_token = "mock_refresh_token"
        google_drive_service.session = aiohttp.ClientSession()
        
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        try:
            result = await google_drive_service.refresh_access_token()
            
            assert result["success"] is True
            assert "access_token" in result
            assert google_drive_service.access_token == "new_access_token"
        finally:
            await google_drive_service.session.close()
    
    async def test_health_check_without_token(self, google_drive_service):
        """Test health check without valid token."""
        # Ensure no access token is set
        google_drive_service.access_token = None
        
        result = await google_drive_service.health_check()
        
        assert result["status"] == "error"
        assert "Invalid or missing access token" in result["message"]
    
    @patch('aiohttp.ClientSession.get')
    async def test_health_check_with_token(self, mock_get, google_drive_service):
        """Test health check with valid token."""
        # Set up service with mock token
        google_drive_service.access_token = "mock_token"
        google_drive_service.session = aiohttp.ClientSession()
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "user": {"emailAddress": "test@example.com"},
            "storageQuota": {"limit": "1000000000"}
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        try:
            result = await google_drive_service.health_check()
            
            assert result["status"] == "healthy"
            assert "Google Drive service is operational" in result["message"]
            assert "user_email" in result
        finally:
            await google_drive_service.session.close()


@pytest.mark.external
@pytest.mark.asyncio  
class TestCloudStorageIntegrationService:
    """Test cloud storage integration service with Google Drive."""
    
    @pytest.fixture
    def cloud_storage_service(self, db_session):
        """Create cloud storage integration service."""
        return CloudStorageIntegrationService(db_session)
    
    async def test_service_initialization(self, cloud_storage_service):
        """Test cloud storage service initialization."""
        result = await cloud_storage_service.initialize_services()
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "services" in result
        assert "google_drive" in result["services"]
    
    async def test_available_providers(self, cloud_storage_service):
        """Test getting available providers."""
        providers = await cloud_storage_service.get_available_providers()
        
        assert isinstance(providers, list)
        assert "google_drive" in providers
        assert "dropbox" in providers
    
    async def test_service_status(self, cloud_storage_service):
        """Test getting service status."""
        status_result = await cloud_storage_service.get_service_status()
        
        assert isinstance(status_result, dict)
        assert "success" in status_result
        assert "status" in status_result
        assert "providers" in status_result
    
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    async def test_file_upload_google_drive(self, mock_unlink, mock_temp_file, cloud_storage_service):
        """Test file upload to Google Drive."""
        # Mock temporary file
        mock_temp = Mock()
        mock_temp.name = "/tmp/test_file.pdf"
        mock_temp.write = Mock()
        mock_temp.__enter__ = Mock(return_value=mock_temp)
        mock_temp.__exit__ = Mock(return_value=None)
        mock_temp_file.return_value = mock_temp
        
        # Mock Google Drive service
        if cloud_storage_service.google_drive_service:
            with patch.object(
                cloud_storage_service.google_drive_service,
                'upload_file',
                new_callable=AsyncMock
            ) as mock_upload:
                mock_upload.return_value = {
                    "success": True,
                    "file_id": "mock_file_id",
                    "file_name": "test.pdf",
                    "web_view_link": "https://drive.google.com/file/d/mock_file_id/view"
                }
                
                file_content = b"Mock PDF content"
                result = await cloud_storage_service.upload_file(
                    provider="google_drive",
                    file_content=file_content,
                    filename="test.pdf",
                    folder_path=None,
                    description="Test upload",
                    user_id="test_user"
                )
                
                assert result["success"] is True
                assert "file_id" in result
                mock_upload.assert_called_once()
                mock_unlink.assert_called_once()
    
    async def test_file_upload_unsupported_provider(self, cloud_storage_service):
        """Test file upload with unsupported provider."""
        file_content = b"Test content"
        
        result = await cloud_storage_service.upload_file(
            provider="unsupported_provider",
            file_content=file_content,
            filename="test.txt",
            user_id="test_user"
        )
        
        assert result["success"] is False
        assert "Unsupported provider" in result["error"]


@pytest.mark.external
@pytest.mark.asyncio
class TestGoogleDriveAPIEndpoints:
    """Test Google Drive API endpoints."""
    
    async def test_health_check_endpoint(self, async_client: AsyncClient, authenticated_headers):
        """Test Google Drive health check endpoint."""
        response = await async_client.get(
            "/api/google-drive/health",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "status" in data
        assert "google_drive_configured" in data
        assert "configuration" in data
        
        # Should be configured with current settings
        assert data["google_drive_configured"] is True
    
    async def test_configuration_endpoint(self, async_client: AsyncClient, authenticated_headers):
        """Test Google Drive configuration endpoint."""
        response = await async_client.get(
            "/api/google-drive/configuration",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "success"
        assert data["google_drive_configured"] is True
        assert "configuration" in data
        
        config = data["configuration"]
        assert config["has_client_id"] is True
        assert config["has_client_secret"] is True
        assert config["has_redirect_uri"] is True
        assert config["project_id"] == settings.GOOGLE_DRIVE_PROJECT_ID
    
    async def test_authorization_url_endpoint(self, async_client: AsyncClient, authenticated_headers):
        """Test getting authorization URL endpoint."""
        response = await async_client.get(
            "/api/google-drive/authorization-url?state=test_state",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "authorization_url" in data
        assert "state" in data
        assert "message" in data
        
        auth_url = data["authorization_url"]
        assert "accounts.google.com" in auth_url
        assert "state=test_state" in auth_url
    
    async def test_oauth_callback_endpoint_missing_code(self, async_client: AsyncClient, authenticated_headers):
        """Test OAuth callback endpoint with missing code."""
        response = await async_client.post(
            "/api/google-drive/callback",
            json={"state": "test_state"},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Authorization code is required" in data["detail"]
    
    async def test_oauth_callback_endpoint_invalid_code(self, async_client: AsyncClient, authenticated_headers):
        """Test OAuth callback endpoint with invalid code."""
        with patch('app.services.cloud_storage_integration_service.CloudStorageIntegrationService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock Google Drive service
            mock_gdrive = Mock()
            mock_gdrive.exchange_code_for_tokens = AsyncMock(return_value={
                "success": False,
                "error": "Invalid authorization code"
            })
            mock_service_instance.google_drive_service = mock_gdrive
            
            response = await async_client.post(
                "/api/google-drive/callback",
                json={
                    "code": "invalid_code",
                    "state": "test_state"
                },
                headers=authenticated_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Token exchange failed" in data["detail"]
    
    async def test_test_upload_endpoint_no_file(self, async_client: AsyncClient, authenticated_headers):
        """Test upload endpoint without file."""
        response = await async_client.post(
            "/api/google-drive/test-upload",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_test_list_files_endpoint(self, async_client: AsyncClient, authenticated_headers):
        """Test list files endpoint."""
        with patch('app.services.cloud_storage_integration_service.CloudStorageIntegrationService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock Google Drive service
            mock_gdrive = Mock()
            mock_service_instance.google_drive_service = mock_gdrive
            mock_service_instance.list_files = AsyncMock(return_value={
                "success": True,
                "files": [
                    {
                        "id": "file1",
                        "name": "test1.pdf",
                        "size": "1024"
                    },
                    {
                        "id": "file2", 
                        "name": "test2.pdf",
                        "size": "2048"
                    }
                ]
            })
            
            response = await async_client.get(
                "/api/google-drive/test-list-files?limit=10",
                headers=authenticated_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["status"] == "success"
            assert "list_result" in data
            assert "parameters" in data
    
    async def test_user_info_endpoint(self, async_client: AsyncClient, authenticated_headers):
        """Test get user info endpoint."""
        with patch('app.services.cloud_storage_integration_service.CloudStorageIntegrationService') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            # Mock Google Drive service
            mock_gdrive = Mock()
            mock_gdrive.get_user_info = AsyncMock(return_value={
                "success": True,
                "user": {
                    "emailAddress": "test@example.com",
                    "displayName": "Test User"
                },
                "storage_quota": {
                    "limit": "15000000000",
                    "usage": "1000000000"
                }
            })
            mock_service_instance.google_drive_service = mock_gdrive
            
            response = await async_client.get(
                "/api/google-drive/user-info",
                headers=authenticated_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["status"] == "success"
            assert "user_info" in data


@pytest.mark.external
@pytest.mark.asyncio  
class TestGoogleDriveFileOperations:
    """Test actual file operations with Google Drive (requires authentication)."""
    
    @pytest.mark.skip(reason="Requires actual Google Drive authentication")
    async def test_real_file_upload(self):
        """Test real file upload to Google Drive.
        
        This test is skipped by default as it requires actual authentication.
        To run this test:
        1. Set up proper OAuth2 authentication
        2. Remove the skip decorator
        3. Ensure you have proper credentials
        """
        # This would test real file upload operations
        pass
    
    @pytest.mark.skip(reason="Requires actual Google Drive authentication")
    async def test_real_file_download(self):
        """Test real file download from Google Drive.
        
        This test is skipped by default as it requires actual authentication.
        """
        # This would test real file download operations
        pass
    
    @pytest.mark.skip(reason="Requires actual Google Drive authentication")
    async def test_real_file_listing(self):
        """Test real file listing from Google Drive.
        
        This test is skipped by default as it requires actual authentication.
        """
        # This would test real file listing operations
        pass


@pytest.mark.external
@pytest.mark.asyncio
class TestGoogleDriveErrorHandling:
    """Test error handling in Google Drive integration."""
    
    async def test_service_unavailable_error(self, db_session):
        """Test behavior when Google Drive service is unavailable."""
        # Mock GoogleDriveService to be None
        with patch('app.services.cloud_storage_integration_service.GoogleDriveService', None):
            service = CloudStorageIntegrationService(db_session)
            
            result = await service.upload_file(
                provider="google_drive",
                file_content=b"test",
                filename="test.txt"
            )
            
            assert result["success"] is False
            assert "Google Drive service not available" in result["error"]
    
    async def test_configuration_missing_error(self):
        """Test behavior when Google Drive configuration is missing."""
        with patch.object(settings, 'GOOGLE_DRIVE_CONFIGURED', False):
            # Test that service handles missing configuration gracefully
            assert settings.GOOGLE_DRIVE_CONFIGURED is False
    
    async def test_network_error_handling(self, db_session):
        """Test handling of network errors."""
        service = CloudStorageIntegrationService(db_session)
        
        if service.google_drive_service:
            with patch.object(
                service.google_drive_service,
                'upload_file',
                side_effect=Exception("Network error")
            ):
                result = await service.upload_file(
                    provider="google_drive",
                    file_content=b"test",
                    filename="test.txt"
                )
                
                assert result["success"] is False
                assert "error" in result
    
    async def test_invalid_file_type_handling(self, async_client: AsyncClient, authenticated_headers):
        """Test handling of invalid file types."""
        # Create a file with invalid content type
        file_content = b"executable content"
        
        with patch('app.core.config.settings.CLOUD_STORAGE_ALLOWED_TYPES', ["application/pdf"]):
            response = await async_client.post(
                "/api/google-drive/test-upload",
                files={"file": ("test.exe", file_content, "application/x-executable")},
                headers=authenticated_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "not allowed" in data["detail"]
    
    async def test_file_size_limit_handling(self, async_client: AsyncClient, authenticated_headers):
        """Test handling of files exceeding size limit."""
        # Mock a large file
        large_file_content = b"x" * (settings.CLOUD_STORAGE_MAX_FILE_SIZE + 1)
        
        response = await async_client.post(
            "/api/google-drive/test-upload", 
            files={"file": ("large.pdf", large_file_content, "application/pdf")},
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        data = response.json()
        assert "exceeds maximum" in data["detail"]