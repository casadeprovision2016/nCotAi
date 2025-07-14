"""
Cloud Storage Integration Service
Main service for coordinating cloud storage integrations.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from app.core.config import settings

# Import cloud storage services
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src/services/cloud-storage'))

try:
    from google_drive_service import GoogleDriveService
except ImportError:
    logger.warning("GoogleDriveService not available")
    GoogleDriveService = None

logger = logging.getLogger(__name__)


class CloudStorageIntegrationService:
    """Main service for cloud storage integration coordination."""

    def __init__(self, db: Session):
        self.db = db
        
        # Initialize Google Drive service if available and configured
        self.google_drive_service = None
        if GoogleDriveService and settings.GOOGLE_DRIVE_CONFIGURED:
            self.google_drive_service = GoogleDriveService()
        
        # Service registry
        self.services = {
            "google_drive": self.google_drive_service,
            "dropbox": None,  # TODO: Implement Dropbox service
            "manager": None,  # TODO: Implement storage manager
            "sync": None,     # TODO: Implement sync service
        }

        # Integration status
        self.status = {
            "initialized": True,
            "services_health": {},
            "last_check": datetime.utcnow(),
        }

    async def initialize_services(self) -> Dict[str, Any]:
        """Initialize all cloud storage integration services."""
        try:
            logger.info("Initializing cloud storage integration services")

            # Initialize services
            results = {}

            # Initialize Google Drive service
            if self.google_drive_service:
                gdrive_result = await self.google_drive_service.initialize()
                results["google_drive"] = gdrive_result
            else:
                results["google_drive"] = {
                    "success": False,
                    "error": "Google Drive service not configured or not available"
                }

            # TODO: Initialize other services when implemented
            results["dropbox"] = {"success": False, "error": "Service not implemented"}
            results["manager"] = {"success": False, "error": "Service not implemented"}
            results["sync"] = {"success": False, "error": "Service not implemented"}

            # Update service health status
            for service_name, result in results.items():
                self.status["services_health"][service_name] = {
                    "status": "healthy" if result.get("success") else "error",
                    "last_check": datetime.utcnow(),
                    "details": result,
                }

            logger.info("Cloud storage integration services initialized")
            return {
                "success": True,
                "message": "Cloud storage integration services initialized",
                "services": results,
                "status": self.status,
            }

        except Exception as e:
            logger.error(f"Error initializing cloud storage services: {str(e)}")
            return {"success": False, "error": str(e), "status": self.status}

    async def upload_file(
        self,
        provider: str,
        file_content: bytes,
        filename: str,
        folder_path: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to cloud storage provider."""
        try:
            if provider == "google_drive":
                if not self.google_drive_service:
                    return {"success": False, "error": "Google Drive service not available"}
                
                # Save file temporarily for upload
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                try:
                    result = await self.google_drive_service.upload_file(
                        file_path=temp_file_path,
                        file_name=filename,
                        parent_folder_id=folder_path,
                        description=description,
                    )
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)
                    
            elif provider == "dropbox":
                return {"success": False, "error": "Dropbox service not implemented"}
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            # Log upload activity
            if result.get("success"):
                logger.info(f"File uploaded to {provider}: {filename}")
            else:
                logger.error(f"Failed to upload file to {provider}: {result.get('error')}")
            
            return result

        except Exception as e:
            logger.error(f"Error uploading file to {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def download_file(
        self,
        provider: str,
        file_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Download file from cloud storage provider."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.download_file(file_id)
            elif provider == "dropbox":
                result = await self.dropbox_service.download_file(file_id)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error downloading file from {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def list_files(
        self,
        provider: str,
        folder_id: Optional[str] = None,
        limit: int = 50,
        page_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files from cloud storage provider."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.list_files(
                    folder_id=folder_id,
                    limit=limit,
                    page_token=page_token,
                )
            elif provider == "dropbox":
                result = await self.dropbox_service.list_files(
                    folder_path=folder_id,
                    limit=limit,
                    cursor=page_token,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error listing files from {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_file(
        self,
        provider: str,
        file_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete file from cloud storage provider."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.delete_file(file_id)
            elif provider == "dropbox":
                result = await self.dropbox_service.delete_file(file_id)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error deleting file from {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_folder(
        self,
        provider: str,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create folder in cloud storage provider."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.create_folder(
                    folder_name=folder_name,
                    parent_folder_id=parent_folder_id,
                )
            elif provider == "dropbox":
                result = await self.dropbox_service.create_folder(
                    folder_path=f"{parent_folder_id or ''}/{folder_name}".lstrip("/")
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error creating folder in {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def share_file(
        self,
        provider: str,
        file_id: str,
        permissions: str = "read",
        expires_hours: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create shareable link for file."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.share_file(
                    file_id=file_id,
                    permissions=permissions,
                    expires_hours=expires_hours,
                )
            elif provider == "dropbox":
                result = await self.dropbox_service.create_shared_link(
                    file_path=file_id,
                    expires_hours=expires_hours,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error sharing file from {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def sync_files(
        self,
        provider: str,
        local_path: str,
        remote_path: str,
        sync_direction: str = "bidirectional",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sync files between local and cloud storage."""
        try:
            result = await self.sync_service.sync_files(
                provider=provider,
                local_path=local_path,
                remote_path=remote_path,
                sync_direction=sync_direction,
            )

            return result

        except Exception as e:
            logger.error(f"Error syncing files with {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_available_providers(self) -> List[str]:
        """Get list of available cloud storage providers."""
        return ["google_drive", "dropbox"]

    async def get_provider_status(
        self,
        provider: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get status of specific cloud storage provider."""
        try:
            if provider == "google_drive":
                status = await self.google_drive_service.get_status()
            elif provider == "dropbox":
                status = await self.dropbox_service.get_status()
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return status

        except Exception as e:
            logger.error(f"Error getting status for {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def configure_provider(
        self,
        provider: str,
        config: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Configure cloud storage provider settings."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.configure(config)
            elif provider == "dropbox":
                result = await self.dropbox_service.configure(config)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error configuring {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def authorize_provider(
        self,
        provider: str,
        authorization_code: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authorize access to cloud storage provider."""
        try:
            if provider == "google_drive":
                result = await self.google_drive_service.authorize(authorization_code)
            elif provider == "dropbox":
                result = await self.dropbox_service.authorize(authorization_code)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            return result

        except Exception as e:
            logger.error(f"Error authorizing {provider}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all cloud storage integration services."""
        try:
            # Perform health checks
            health_checks = {}

            for service_name, service in self.services.items():
                try:
                    if hasattr(service, "health_check"):
                        health_result = await service.health_check()
                        health_checks[service_name] = health_result
                    else:
                        health_checks[service_name] = {
                            "status": "unknown",
                            "message": "No health check available",
                        }
                except Exception as e:
                    health_checks[service_name] = {"status": "error", "error": str(e)}

            # Update status
            self.status["services_health"] = health_checks
            self.status["last_check"] = datetime.utcnow()

            return {
                "success": True,
                "status": self.status,
                "providers": health_checks,
            }

        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_usage_statistics(
        self,
        provider: Optional[str] = None,
        days: int = 30,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics for cloud storage."""
        try:
            # This would typically query a database for usage statistics
            # For now, return placeholder data
            stats = {
                "uploads": 0,
                "downloads": 0,
                "storage_used": 0,
                "api_calls": 0,
                "period_start": datetime.utcnow(),
                "period_end": datetime.utcnow(),
            }

            if provider:
                # Get provider-specific stats
                if provider == "google_drive":
                    provider_stats = await self.google_drive_service.get_usage_stats(days)
                elif provider == "dropbox":
                    provider_stats = await self.dropbox_service.get_usage_stats(days)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                
                stats.update(provider_stats)

            return stats

        except Exception as e:
            logger.error(f"Error getting usage statistics: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cleanup_services(self) -> Dict[str, Any]:
        """Cleanup and shutdown cloud storage integration services."""
        try:
            logger.info("Cleaning up cloud storage integration services")

            cleanup_results = {}

            for service_name, service in self.services.items():
                try:
                    if hasattr(service, "cleanup"):
                        result = await service.cleanup()
                        cleanup_results[service_name] = result
                    else:
                        cleanup_results[service_name] = {"status": "no_cleanup_needed"}
                except Exception as e:
                    cleanup_results[service_name] = {"status": "error", "error": str(e)}

            logger.info("Cloud storage integration services cleanup completed")
            return {
                "success": True,
                "message": "Services cleaned up successfully",
                "cleanup_results": cleanup_results,
            }

        except Exception as e:
            logger.error(f"Error cleaning up services: {str(e)}")
            return {"success": False, "error": str(e)}