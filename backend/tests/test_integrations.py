"""
External integrations tests for COTAI backend.
Tests for WhatsApp, Cloud Storage, Team Notifications, and Government APIs with mocks.
"""
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.tender import Tender
from app.models.quotation import Quotation
from tests.factories import (
    UserFactory,
    TenderFactory,
    QuotationFactory,
    NotificationFactory,
)


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestWhatsAppIntegration:
    """Test WhatsApp Business API integration."""

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_send_message_success(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful WhatsApp message sending."""
        # Mock WhatsApp service
        mock_service = Mock()
        mock_service.send_message.return_value = {
            "success": True,
            "message_id": "wamid.test123",
            "status": "sent"
        }
        mock_whatsapp_service.return_value = mock_service
        
        message_data = {
            "to": "+5511999999999",
            "message": "Test message from COTAI",
            "message_type": "text"
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/send/text",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["message_id"] == "wamid.test123"
        assert data["status"] == "sent"
        
        # Verify service was called with correct parameters
        mock_service.send_message.assert_called_once_with(
            to="+5511999999999",
            message="Test message from COTAI",
            message_type="text"
        )

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_send_template_success(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful WhatsApp template message sending."""
        # Mock WhatsApp service
        mock_service = Mock()
        mock_service.send_template.return_value = {
            "success": True,
            "message_id": "wamid.template123",
            "status": "sent"
        }
        mock_whatsapp_service.return_value = mock_service
        
        template_data = {
            "to": "+5511999999999",
            "template_name": "tender_alert",
            "template_params": {
                "tender_title": "Construction Project Alpha",
                "deadline": "2025-02-15",
                "estimated_value": "R$ 500.000",
                "agency": "Municipal Government"
            }
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/send/template",
            json=template_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["message_id"] == "wamid.template123"
        
        # Verify service was called with correct parameters
        mock_service.send_template.assert_called_once_with(
            to="+5511999999999",
            template_name="tender_alert",
            template_params=template_data["template_params"]
        )

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_send_message_failure(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test WhatsApp message sending failure."""
        # Mock WhatsApp service failure
        mock_service = Mock()
        mock_service.send_message.return_value = {
            "success": False,
            "error": "Invalid phone number",
            "error_code": "INVALID_PHONE"
        }
        mock_whatsapp_service.return_value = mock_service
        
        message_data = {
            "to": "invalid-phone",
            "message": "Test message",
            "message_type": "text"
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/send/text",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["success"] == False
        assert data["error"] == "Invalid phone number"
        assert data["error_code"] == "INVALID_PHONE"

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_webhook_verification(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test WhatsApp webhook verification."""
        # Mock webhook verification
        mock_service = Mock()
        mock_service.verify_webhook.return_value = "challenge_token"
        mock_whatsapp_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "challenge_token"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.text == "challenge_token"

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_webhook_message_received(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test WhatsApp webhook message processing."""
        # Mock webhook message processing
        mock_service = Mock()
        mock_service.process_webhook_message.return_value = {
            "processed": True,
            "message_id": "wamid.received123",
            "from": "+5511999999999",
            "text": "Hello COTAI"
        }
        mock_whatsapp_service.return_value = mock_service
        
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry_id",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "wamid.received123",
                                        "from": "+5511999999999",
                                        "text": {"body": "Hello COTAI"},
                                        "timestamp": "1640995200"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/webhook",
            json=webhook_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["processed"] == True
        assert data["message_id"] == "wamid.received123"

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_health_check(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test WhatsApp service health check."""
        # Mock health check
        mock_service = Mock()
        mock_service.health_check.return_value = {
            "status": "healthy",
            "api_version": "v17.0",
            "last_check": "2025-01-14T10:00:00Z",
            "rate_limit": {
                "remaining": 950,
                "reset_time": "2025-01-14T11:00:00Z"
            }
        }
        mock_whatsapp_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/whatsapp/health",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api_version"] == "v17.0"
        assert "rate_limit" in data

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_tender_notification(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test WhatsApp tender notification."""
        # Create tender
        tender = TenderFactory()
        async_db_session.add(tender)
        await async_db_session.commit()
        
        # Mock WhatsApp service
        mock_service = Mock()
        mock_service.send_tender_notification.return_value = {
            "success": True,
            "message_id": "wamid.tender123",
            "recipients": ["+5511999999999"]
        }
        mock_whatsapp_service.return_value = mock_service
        
        notification_data = {
            "tender_id": str(tender.id),
            "recipients": ["+5511999999999"],
            "notification_type": "new_tender"
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/send/tender-notification",
            json=notification_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["message_id"] == "wamid.tender123"


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestCloudStorageIntegration:
    """Test Cloud Storage (Google Drive, Dropbox) integration."""

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_upload_file_success(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful file upload to cloud storage."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.upload_file.return_value = {
            "success": True,
            "file_id": "drive_file_123",
            "file_name": "test_document.pdf",
            "file_size": 1024000,
            "upload_url": "https://drive.google.com/file/d/drive_file_123",
            "provider": "google_drive"
        }
        mock_cloud_service.return_value = mock_service
        
        # Mock file upload
        files = {
            "file": ("test_document.pdf", b"test content", "application/pdf")
        }
        
        response = await async_client.post(
            "/api/v1/cloud-storage/upload",
            files=files,
            params={"provider": "google_drive", "folder_path": "/cotai/documents"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["file_id"] == "drive_file_123"
        assert data["file_name"] == "test_document.pdf"
        assert data["provider"] == "google_drive"

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_download_file_success(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful file download from cloud storage."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.download_file.return_value = {
            "success": True,
            "file_content": b"test file content",
            "file_name": "test_document.pdf",
            "mime_type": "application/pdf"
        }
        mock_cloud_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/cloud-storage/download/drive_file_123",
            params={"provider": "google_drive"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"test file content"

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_list_files_success(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful file listing from cloud storage."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.list_files.return_value = {
            "success": True,
            "files": [
                {
                    "file_id": "drive_file_1",
                    "file_name": "document1.pdf",
                    "file_size": 1024000,
                    "created_at": "2025-01-14T10:00:00Z",
                    "modified_at": "2025-01-14T10:00:00Z"
                },
                {
                    "file_id": "drive_file_2",
                    "file_name": "document2.pdf",
                    "file_size": 2048000,
                    "created_at": "2025-01-14T11:00:00Z",
                    "modified_at": "2025-01-14T11:00:00Z"
                }
            ],
            "total_files": 2,
            "folder_path": "/cotai/documents"
        }
        mock_cloud_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/cloud-storage/files",
            params={"provider": "google_drive", "folder_path": "/cotai/documents", "limit": 50},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert len(data["files"]) == 2
        assert data["total_files"] == 2
        assert data["folder_path"] == "/cotai/documents"

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_sync_folder_success(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful folder synchronization."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.sync_folder.return_value = {
            "success": True,
            "sync_id": "sync_123",
            "files_uploaded": 5,
            "files_downloaded": 2,
            "files_skipped": 1,
            "sync_direction": "upload",
            "local_path": "/app/documents",
            "remote_path": "/cotai/backup"
        }
        mock_cloud_service.return_value = mock_service
        
        sync_data = {
            "provider": "google_drive",
            "local_path": "/app/documents",
            "remote_path": "/cotai/backup",
            "sync_direction": "upload",
            "delete_remote": False
        }
        
        response = await async_client.post(
            "/api/v1/cloud-storage/sync",
            json=sync_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["sync_id"] == "sync_123"
        assert data["files_uploaded"] == 5
        assert data["files_downloaded"] == 2

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_delete_file_success(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful file deletion from cloud storage."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.delete_file.return_value = {
            "success": True,
            "file_id": "drive_file_123",
            "deleted_at": "2025-01-14T10:00:00Z"
        }
        mock_cloud_service.return_value = mock_service
        
        response = await async_client.delete(
            "/api/v1/cloud-storage/files/drive_file_123",
            params={"provider": "google_drive"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["file_id"] == "drive_file_123"

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_providers_list(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test cloud storage providers listing."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.get_providers.return_value = {
            "providers": [
                {
                    "name": "google_drive",
                    "display_name": "Google Drive",
                    "status": "active",
                    "quota_used": "2.5 GB",
                    "quota_total": "15 GB",
                    "last_sync": "2025-01-14T09:30:00Z"
                },
                {
                    "name": "dropbox",
                    "display_name": "Dropbox",
                    "status": "active",
                    "quota_used": "1.2 GB",
                    "quota_total": "2 GB",
                    "last_sync": "2025-01-14T09:45:00Z"
                }
            ]
        }
        mock_cloud_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/cloud-storage/providers",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["providers"]) == 2
        assert data["providers"][0]["name"] == "google_drive"
        assert data["providers"][1]["name"] == "dropbox"

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_health_check(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test cloud storage health check."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.health_check.return_value = {
            "status": "healthy",
            "providers": {
                "google_drive": {"status": "connected", "last_check": "2025-01-14T10:00:00Z"},
                "dropbox": {"status": "connected", "last_check": "2025-01-14T10:00:00Z"}
            }
        }
        mock_cloud_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/cloud-storage/health",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data
        assert data["providers"]["google_drive"]["status"] == "connected"


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestTeamNotificationsIntegration:
    """Test Team Notifications (Slack, Microsoft Teams) integration."""

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_slack_send_message_success(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful Slack message sending."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.send_message.return_value = {
            "success": True,
            "message_id": "slack_msg_123",
            "channel_id": "C1234567890",
            "provider": "slack",
            "timestamp": "2025-01-14T10:00:00Z"
        }
        mock_team_service.return_value = mock_service
        
        message_data = {
            "provider": "slack",
            "channel_id": "C1234567890",
            "message": "New tender opportunity available!",
            "message_type": "text"
        }
        
        response = await async_client.post(
            "/api/v1/team-notifications/send/text",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["message_id"] == "slack_msg_123"
        assert data["provider"] == "slack"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_slack_send_rich_message_success(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful Slack rich message sending."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.send_rich_message.return_value = {
            "success": True,
            "message_id": "slack_rich_123",
            "channel_id": "C1234567890",
            "provider": "slack"
        }
        mock_team_service.return_value = mock_service
        
        rich_message_data = {
            "provider": "slack",
            "channel_id": "C1234567890",
            "title": "🚨 Tender Alert",
            "message": "High-value opportunity identified",
            "color": "#ff6b35",
            "fields": [
                {"title": "Value", "value": "R$ 2.5M", "short": True},
                {"title": "Deadline", "value": "15 days", "short": True},
                {"title": "Agency", "value": "Federal Government", "short": False}
            ],
            "actions": [
                {"text": "View Details", "url": "https://cotai.com/tender/123"}
            ]
        }
        
        response = await async_client.post(
            "/api/v1/team-notifications/send/rich",
            json=rich_message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["message_id"] == "slack_rich_123"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_teams_send_workflow_notification(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test Microsoft Teams workflow notification."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.send_workflow_notification.return_value = {
            "success": True,
            "message_id": "teams_workflow_123",
            "channel_id": "19:...",
            "provider": "teams",
            "workflow_type": "tender_alert"
        }
        mock_team_service.return_value = mock_service
        
        workflow_data = {
            "provider": "teams",
            "channel_id": "19:...",
            "workflow_type": "tender_alert",
            "data": {
                "tender_title": "Construction Project",
                "deadline": "2025-02-15",
                "value": "R$ 1.5M",
                "agency": "Municipal Government",
                "urgency": "high"
            }
        }
        
        response = await async_client.post(
            "/api/v1/team-notifications/send/workflow",
            json=workflow_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["workflow_type"] == "tender_alert"
        assert data["provider"] == "teams"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_get_channels_success(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test successful channel listing."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.get_channels.return_value = {
            "success": True,
            "channels": [
                {
                    "id": "C1234567890",
                    "name": "tender-alerts",
                    "provider": "slack",
                    "members": 25,
                    "is_active": True
                },
                {
                    "id": "19:...",
                    "name": "COTAI Notifications",
                    "provider": "teams",
                    "members": 15,
                    "is_active": True
                }
            ]
        }
        mock_team_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/team-notifications/channels",
            params={"provider": "slack", "limit": 20},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert len(data["channels"]) == 2
        assert data["channels"][0]["name"] == "tender-alerts"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_team_notifications_providers_list(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test team notifications providers listing."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.get_providers.return_value = {
            "providers": [
                {
                    "name": "slack",
                    "display_name": "Slack",
                    "status": "connected",
                    "workspace": "COTAI Team",
                    "bot_user": "@cotai-bot",
                    "last_activity": "2025-01-14T09:30:00Z"
                },
                {
                    "name": "teams",
                    "display_name": "Microsoft Teams",
                    "status": "connected",
                    "tenant": "cotai.onmicrosoft.com",
                    "app_id": "app_123",
                    "last_activity": "2025-01-14T09:45:00Z"
                }
            ]
        }
        mock_team_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/team-notifications/providers",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["providers"]) == 2
        assert data["providers"][0]["name"] == "slack"
        assert data["providers"][1]["name"] == "teams"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_team_notifications_health_check(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test team notifications health check."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.health_check.return_value = {
            "status": "healthy",
            "providers": {
                "slack": {"status": "connected", "last_check": "2025-01-14T10:00:00Z"},
                "teams": {"status": "connected", "last_check": "2025-01-14T10:00:00Z"}
            }
        }
        mock_team_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/team-notifications/health",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data
        assert data["providers"]["slack"]["status"] == "connected"

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_bulk_notification_sending(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test bulk notification sending to multiple channels."""
        # Mock team notifications service
        mock_service = Mock()
        mock_service.send_bulk_notifications.return_value = {
            "success": True,
            "total_sent": 3,
            "results": [
                {"channel_id": "C1234567890", "provider": "slack", "status": "sent", "message_id": "msg_1"},
                {"channel_id": "C0987654321", "provider": "slack", "status": "sent", "message_id": "msg_2"},
                {"channel_id": "19:...", "provider": "teams", "status": "sent", "message_id": "msg_3"}
            ]
        }
        mock_team_service.return_value = mock_service
        
        bulk_data = {
            "message": "Important system update available",
            "channels": [
                {"provider": "slack", "channel_id": "C1234567890"},
                {"provider": "slack", "channel_id": "C0987654321"},
                {"provider": "teams", "channel_id": "19:..."}
            ]
        }
        
        response = await async_client.post(
            "/api/v1/team-notifications/send/bulk",
            json=bulk_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["total_sent"] == 3
        assert len(data["results"]) == 3


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestGovernmentAPIsIntegration:
    """Test Government APIs (PNCP, COMPRASNET, Receita Federal) integration."""

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_pncp_get_tender_data(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test PNCP tender data retrieval."""
        # Mock government APIs service
        mock_service = Mock()
        mock_service.get_pncp_tender.return_value = {
            "success": True,
            "tender": {
                "id": "pncp_12345",
                "title": "Construção de Ponte Municipal",
                "description": "Projeto de construção de ponte sobre o Rio Grande",
                "estimated_value": 2500000.00,
                "deadline": "2025-03-15",
                "agency": {
                    "name": "Prefeitura Municipal de Exemplo",
                    "cnpj": "12.345.678/0001-90",
                    "contact": "licitacao@exemplo.gov.br"
                },
                "category": "OBRAS",
                "status": "ABERTA",
                "documents": [
                    {
                        "name": "Edital Completo",
                        "url": "https://pncp.gov.br/docs/edital_12345.pdf",
                        "size": 1024000
                    }
                ]
            }
        }
        mock_gov_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/government-apis/pncp/tender/pncp_12345",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["tender"]["id"] == "pncp_12345"
        assert data["tender"]["title"] == "Construção de Ponte Municipal"
        assert data["tender"]["estimated_value"] == 2500000.00

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_comprasnet_search_tenders(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test COMPRASNET tender search."""
        # Mock government APIs service
        mock_service = Mock()
        mock_service.search_comprasnet_tenders.return_value = {
            "success": True,
            "tenders": [
                {
                    "id": "compras_67890",
                    "title": "Aquisição de Equipamentos de TI",
                    "estimated_value": 150000.00,
                    "deadline": "2025-02-20",
                    "agency": "Ministério da Educação",
                    "category": "BENS"
                },
                {
                    "id": "compras_54321",
                    "title": "Serviços de Limpeza Terceirizada",
                    "estimated_value": 85000.00,
                    "deadline": "2025-02-25",
                    "agency": "Ministério da Saúde",
                    "category": "SERVIÇOS"
                }
            ],
            "total": 2,
            "page": 1,
            "per_page": 20
        }
        mock_gov_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/government-apis/comprasnet/search",
            params={
                "keyword": "equipamentos",
                "category": "BENS",
                "min_value": 100000,
                "max_value": 200000,
                "page": 1,
                "per_page": 20
            },
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert len(data["tenders"]) == 2
        assert data["total"] == 2
        assert data["tenders"][0]["id"] == "compras_67890"

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_receita_federal_validate_cnpj(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test Receita Federal CNPJ validation."""
        # Mock government APIs service
        mock_service = Mock()
        mock_service.validate_cnpj.return_value = {
            "success": True,
            "cnpj": "12.345.678/0001-90",
            "valid": True,
            "company_data": {
                "name": "Empresa Exemplo Ltda",
                "trade_name": "Exemplo Corp",
                "legal_nature": "Sociedade Empresária Limitada",
                "activity": "Desenvolvimento de Software",
                "address": {
                    "street": "Rua das Flores, 123",
                    "city": "São Paulo",
                    "state": "SP",
                    "zipcode": "01234-567"
                },
                "status": "ATIVA",
                "registration_date": "2020-01-15",
                "capital": 100000.00
            }
        }
        mock_gov_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/government-apis/receita-federal/validate-cnpj/12.345.678/0001-90",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["cnpj"] == "12.345.678/0001-90"
        assert data["valid"] == True
        assert data["company_data"]["name"] == "Empresa Exemplo Ltda"

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_government_apis_health_check(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test government APIs health check."""
        # Mock government APIs service
        mock_service = Mock()
        mock_service.health_check.return_value = {
            "status": "healthy",
            "apis": {
                "pncp": {
                    "status": "online",
                    "response_time": "250ms",
                    "last_check": "2025-01-14T10:00:00Z",
                    "rate_limit": {"remaining": 480, "reset": "2025-01-14T11:00:00Z"}
                },
                "comprasnet": {
                    "status": "online",
                    "response_time": "180ms",
                    "last_check": "2025-01-14T10:00:00Z",
                    "rate_limit": {"remaining": 950, "reset": "2025-01-14T11:00:00Z"}
                },
                "receita_federal": {
                    "status": "online",
                    "response_time": "320ms",
                    "last_check": "2025-01-14T10:00:00Z",
                    "rate_limit": {"remaining": 1000, "reset": "2025-01-14T11:00:00Z"}
                }
            }
        }
        mock_gov_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/government-apis/health",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "apis" in data
        assert data["apis"]["pncp"]["status"] == "online"
        assert data["apis"]["comprasnet"]["status"] == "online"
        assert data["apis"]["receita_federal"]["status"] == "online"

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_sync_government_tenders(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test government tenders synchronization."""
        # Mock government APIs service
        mock_service = Mock()
        mock_service.sync_tenders.return_value = {
            "success": True,
            "sync_id": "sync_gov_123",
            "sources": ["pncp", "comprasnet"],
            "tenders_found": 25,
            "tenders_imported": 20,
            "tenders_updated": 3,
            "tenders_skipped": 2,
            "sync_duration": "45 seconds",
            "next_sync": "2025-01-14T14:00:00Z"
        }
        mock_gov_service.return_value = mock_service
        
        sync_data = {
            "sources": ["pncp", "comprasnet"],
            "filters": {
                "categories": ["BENS", "SERVIÇOS"],
                "min_value": 50000,
                "max_value": 5000000,
                "states": ["SP", "RJ", "MG"]
            }
        }
        
        response = await async_client.post(
            "/api/v1/government-apis/sync-tenders",
            json=sync_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["sync_id"] == "sync_gov_123"
        assert data["tenders_found"] == 25
        assert data["tenders_imported"] == 20


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestCeleryTasksIntegration:
    """Test Celery tasks for external integrations."""

    @patch('app.services.tasks.external_integrations.send_whatsapp_notification')
    async def test_celery_whatsapp_notification_task(
        self, mock_task, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test Celery WhatsApp notification task."""
        # Mock Celery task
        mock_task.delay.return_value = Mock(id="task_whatsapp_123")
        
        task_data = {
            "task_type": "whatsapp_notification",
            "data": {
                "to": "+5511999999999",
                "message": "Async notification test",
                "template": "tender_alert",
                "params": {"tender_title": "Test Tender"}
            }
        }
        
        response = await async_client.post(
            "/api/v1/tasks/external-integrations",
            json=task_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["task_id"] == "task_whatsapp_123"
        assert data["status"] == "queued"

    @patch('app.services.tasks.external_integrations.sync_cloud_storage')
    async def test_celery_cloud_storage_sync_task(
        self, mock_task, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test Celery cloud storage sync task."""
        # Mock Celery task
        mock_task.delay.return_value = Mock(id="task_cloud_sync_123")
        
        task_data = {
            "task_type": "cloud_storage_sync",
            "data": {
                "provider": "google_drive",
                "local_path": "/app/documents",
                "remote_path": "/cotai/backup",
                "sync_direction": "upload"
            }
        }
        
        response = await async_client.post(
            "/api/v1/tasks/external-integrations",
            json=task_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["task_id"] == "task_cloud_sync_123"
        assert data["status"] == "queued"

    @patch('app.services.tasks.external_integrations.sync_government_tenders')
    async def test_celery_government_sync_task(
        self, mock_task, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test Celery government APIs sync task."""
        # Mock Celery task
        mock_task.delay.return_value = Mock(id="task_gov_sync_123")
        
        task_data = {
            "task_type": "government_sync",
            "data": {
                "sources": ["pncp", "comprasnet"],
                "filters": {
                    "categories": ["BENS", "SERVIÇOS"],
                    "min_value": 50000
                }
            }
        }
        
        response = await async_client.post(
            "/api/v1/tasks/external-integrations",
            json=task_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["task_id"] == "task_gov_sync_123"
        assert data["status"] == "queued"

    async def test_get_task_status(
        self, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test getting task status."""
        with patch('app.services.celery.celery_app.AsyncResult') as mock_result:
            mock_result.return_value.status = "SUCCESS"
            mock_result.return_value.result = {
                "success": True,
                "message": "Task completed successfully"
            }
            
            response = await async_client.get(
                "/api/v1/tasks/task_123/status",
                headers=admin_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == "task_123"
            assert data["status"] == "SUCCESS"
            assert data["result"]["success"] == True


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.asyncio
class TestIntegrationErrorHandling:
    """Test error handling for external integrations."""

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_rate_limit_error(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test WhatsApp rate limit error handling."""
        # Mock rate limit error
        mock_service = Mock()
        mock_service.send_message.side_effect = Exception("Rate limit exceeded")
        mock_whatsapp_service.return_value = mock_service
        
        message_data = {
            "to": "+5511999999999",
            "message": "Test message",
            "message_type": "text"
        }
        
        response = await async_client.post(
            "/api/v1/whatsapp/send/text",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert "rate limit" in data["detail"].lower()

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_quota_exceeded(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test cloud storage quota exceeded error."""
        # Mock quota exceeded error
        mock_service = Mock()
        mock_service.upload_file.return_value = {
            "success": False,
            "error": "Storage quota exceeded",
            "error_code": "QUOTA_EXCEEDED"
        }
        mock_cloud_service.return_value = mock_service
        
        files = {
            "file": ("large_file.pdf", b"large content", "application/pdf")
        }
        
        response = await async_client.post(
            "/api/v1/cloud-storage/upload",
            files=files,
            params={"provider": "google_drive"},
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        data = response.json()
        assert "quota exceeded" in data["detail"].lower()

    @patch('app.services.government_apis_service.GovernmentAPIsService')
    async def test_government_api_timeout(
        self, mock_gov_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test government API timeout error."""
        # Mock timeout error
        mock_service = Mock()
        mock_service.get_pncp_tender.side_effect = Exception("Request timeout")
        mock_gov_service.return_value = mock_service
        
        response = await async_client.get(
            "/api/v1/government-apis/pncp/tender/timeout_test",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        data = response.json()
        assert "timeout" in data["detail"].lower()

    @patch('app.services.team_notifications_service.TeamNotificationsService')
    async def test_team_notifications_connection_error(
        self, mock_team_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test team notifications connection error."""
        # Mock connection error
        mock_service = Mock()
        mock_service.send_message.side_effect = Exception("Connection failed")
        mock_team_service.return_value = mock_service
        
        message_data = {
            "provider": "slack",
            "channel_id": "C1234567890",
            "message": "Test message",
            "message_type": "text"
        }
        
        response = await async_client.post(
            "/api/v1/team-notifications/send/text",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert "connection" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.performance
@pytest.mark.asyncio
class TestIntegrationPerformance:
    """Test performance of external integrations."""

    @patch('app.services.whatsapp_integration_service.WhatsAppService')
    async def test_whatsapp_bulk_messaging_performance(
        self, mock_whatsapp_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test WhatsApp bulk messaging performance."""
        # Mock WhatsApp service
        mock_service = Mock()
        mock_service.send_bulk_messages.return_value = {
            "success": True,
            "total_sent": 50,
            "duration": "2.5 seconds"
        }
        mock_whatsapp_service.return_value = mock_service
        
        # Create bulk message data
        recipients = [f"+551199999{i:04d}" for i in range(50)]
        
        bulk_data = {
            "recipients": recipients,
            "message": "Bulk notification test",
            "message_type": "text"
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/whatsapp/send/bulk",
            json=bulk_data,
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 5.0  # Should complete within 5 seconds
        
        data = response.json()
        assert data["success"] == True
        assert data["total_sent"] == 50

    @patch('app.services.cloud_storage_integration_service.CloudStorageService')
    async def test_cloud_storage_batch_upload_performance(
        self, mock_cloud_service, async_client: AsyncClient, async_db_session: AsyncSession, admin_headers: dict
    ):
        """Test cloud storage batch upload performance."""
        # Mock cloud storage service
        mock_service = Mock()
        mock_service.upload_batch.return_value = {
            "success": True,
            "uploaded_files": 20,
            "total_size": "10.5 MB",
            "duration": "3.2 seconds"
        }
        mock_cloud_service.return_value = mock_service
        
        # Create batch upload data
        files_data = [
            {"name": f"file_{i}.pdf", "size": 512000, "content": f"content_{i}"}
            for i in range(20)
        ]
        
        batch_data = {
            "provider": "google_drive",
            "folder_path": "/cotai/batch_test",
            "files": files_data
        }
        
        import time
        
        start_time = time.time()
        response = await async_client.post(
            "/api/v1/cloud-storage/upload/batch",
            json=batch_data,
            headers=admin_headers
        )
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        assert end_time - start_time < 10.0  # Should complete within 10 seconds
        
        data = response.json()
        assert data["success"] == True
        assert data["uploaded_files"] == 20