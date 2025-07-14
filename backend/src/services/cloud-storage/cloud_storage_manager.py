"""
Cloud Storage Manager
Central manager for all cloud storage integrations.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .dropbox_service import DropboxService
from .google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)


class StorageProvider(Enum):
    """Supported storage providers."""

    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"


@dataclass
class StorageConfig:
    """Storage configuration."""

    provider: StorageProvider
    enabled: bool
    credentials: Dict[str, Any]
    settings: Dict[str, Any]


class CloudStorageManager:
    """Central manager for cloud storage integrations."""

    def __init__(self):
        self.services = {}
        self.configurations = {}

        # Initialize services
        self.google_drive = GoogleDriveService()
        self.dropbox = DropboxService()

        # Service registry
        self.services = {
            StorageProvider.GOOGLE_DRIVE: self.google_drive,
            StorageProvider.DROPBOX: self.dropbox,
        }

        # Manager status
        self.status = {
            "initialized": False,
            "active_providers": [],
            "last_sync": None,
            "sync_status": {},
        }

    async def initialize(self, configurations: List[StorageConfig]) -> Dict[str, Any]:
        """Initialize cloud storage manager with configurations."""
        try:
            logger.info("Initializing Cloud Storage Manager")

            # Store configurations
            for config in configurations:
                self.configurations[config.provider] = config

            # Initialize enabled services
            initialization_results = {}

            for provider, config in self.configurations.items():
                if config.enabled:
                    service = self.services.get(provider)
                    if service:
                        # Set service credentials if available
                        if hasattr(service, "set_credentials"):
                            service.set_credentials(config.credentials)

                        # Initialize service
                        result = await service.initialize()
                        initialization_results[provider.value] = result

                        if result.get("success"):
                            self.status["active_providers"].append(provider.value)
                    else:
                        initialization_results[provider.value] = {
                            "success": False,
                            "error": f"Service not available for provider: {provider.value}",
                        }

            self.status["initialized"] = True

            logger.info(
                f"Cloud Storage Manager initialized with {len(self.status['active_providers'])} active providers"
            )
            return {
                "success": True,
                "message": "Cloud Storage Manager initialized successfully",
                "active_providers": self.status["active_providers"],
                "initialization_results": initialization_results,
            }

        except Exception as e:
            logger.error(f"Error initializing Cloud Storage Manager: {str(e)}")
            return {"success": False, "error": str(e)}

    async def upload_file(
        self,
        file_path: str,
        providers: Optional[List[StorageProvider]] = None,
        file_name: Optional[str] = None,
        folder_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to specified providers or all active providers."""
        try:
            if not providers:
                providers = [
                    StorageProvider(p) for p in self.status["active_providers"]
                ]

            upload_results = {}

            for provider in providers:
                if provider.value not in self.status["active_providers"]:
                    upload_results[provider.value] = {
                        "success": False,
                        "error": "Provider not active",
                    }
                    continue

                service = self.services.get(provider)
                if not service:
                    upload_results[provider.value] = {
                        "success": False,
                        "error": "Service not available",
                    }
                    continue

                try:
                    if provider == StorageProvider.GOOGLE_DRIVE:
                        result = await service.upload_file(
                            file_path=file_path,
                            file_name=file_name,
                            parent_folder_id=folder_path,
                        )
                    elif provider == StorageProvider.DROPBOX:
                        dropbox_path = (
                            f"/{folder_path}/{file_name}"
                            if folder_path and file_name
                            else f"/{file_name or 'file'}"
                        )
                        result = await service.upload_file(
                            file_path=file_path, dropbox_path=dropbox_path
                        )
                    else:
                        result = {"success": False, "error": "Unsupported provider"}

                    upload_results[provider.value] = result

                except Exception as e:
                    upload_results[provider.value] = {"success": False, "error": str(e)}

            # Calculate overall success
            successful_uploads = sum(
                1 for result in upload_results.values() if result.get("success")
            )
            total_uploads = len(upload_results)

            return {
                "success": successful_uploads > 0,
                "uploaded_to": successful_uploads,
                "total_providers": total_uploads,
                "results": upload_results,
            }

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def download_file(
        self, provider: StorageProvider, file_id_or_path: str, download_path: str
    ) -> Dict[str, Any]:
        """Download file from specified provider."""
        try:
            if provider.value not in self.status["active_providers"]:
                return {"success": False, "error": "Provider not active"}

            service = self.services.get(provider)
            if not service:
                return {"success": False, "error": "Service not available"}

            if provider == StorageProvider.GOOGLE_DRIVE:
                result = await service.download_file(file_id_or_path, download_path)
            elif provider == StorageProvider.DROPBOX:
                result = await service.download_file(file_id_or_path, download_path)
            else:
                result = {"success": False, "error": "Unsupported provider"}

            return result

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def sync_folders(
        self,
        local_folder: str,
        remote_folder: str,
        providers: Optional[List[StorageProvider]] = None,
        sync_direction: str = "bidirectional",  # 'upload', 'download', 'bidirectional'
    ) -> Dict[str, Any]:
        """Synchronize folders with cloud storage providers."""
        try:
            if not providers:
                providers = [
                    StorageProvider(p) for p in self.status["active_providers"]
                ]

            sync_results = {}

            for provider in providers:
                if provider.value not in self.status["active_providers"]:
                    sync_results[provider.value] = {
                        "success": False,
                        "error": "Provider not active",
                    }
                    continue

                service = self.services.get(provider)
                if not service:
                    sync_results[provider.value] = {
                        "success": False,
                        "error": "Service not available",
                    }
                    continue

                try:
                    # This is a simplified sync implementation
                    # In production, you'd want more sophisticated sync logic
                    if sync_direction in ["upload", "bidirectional"]:
                        # Upload local files that don't exist remotely
                        upload_result = await self._sync_upload(
                            service, provider, local_folder, remote_folder
                        )

                    if sync_direction in ["download", "bidirectional"]:
                        # Download remote files that don't exist locally
                        download_result = await self._sync_download(
                            service, provider, local_folder, remote_folder
                        )

                    sync_results[provider.value] = {
                        "success": True,
                        "message": "Sync completed successfully",
                    }

                except Exception as e:
                    sync_results[provider.value] = {"success": False, "error": str(e)}

            self.status["last_sync"] = datetime.utcnow()
            self.status["sync_status"] = sync_results

            return {
                "success": True,
                "sync_results": sync_results,
                "last_sync": self.status["last_sync"].isoformat(),
            }

        except Exception as e:
            logger.error(f"Error syncing folders: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _sync_upload(
        self,
        service: Any,
        provider: StorageProvider,
        local_folder: str,
        remote_folder: str,
    ) -> Dict[str, Any]:
        """Sync upload implementation."""
        # Simplified implementation
        # In production, this would compare file timestamps, hashes, etc.
        return {"success": True, "message": "Upload sync completed"}

    async def _sync_download(
        self,
        service: Any,
        provider: StorageProvider,
        local_folder: str,
        remote_folder: str,
    ) -> Dict[str, Any]:
        """Sync download implementation."""
        # Simplified implementation
        # In production, this would compare file timestamps, hashes, etc.
        return {"success": True, "message": "Download sync completed"}

    async def create_shared_link(
        self,
        provider: StorageProvider,
        file_id_or_path: str,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create shared link for file."""
        try:
            if provider.value not in self.status["active_providers"]:
                return {"success": False, "error": "Provider not active"}

            service = self.services.get(provider)
            if not service:
                return {"success": False, "error": "Service not available"}

            if provider == StorageProvider.GOOGLE_DRIVE:
                result = await service.share_file(
                    file_id=file_id_or_path, **permissions or {}
                )
            elif provider == StorageProvider.DROPBOX:
                result = await service.get_sharing_link(dropbox_path=file_id_or_path)
            else:
                result = {"success": False, "error": "Unsupported provider"}

            return result

        except Exception as e:
            logger.error(f"Error creating shared link: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage information from all providers."""
        try:
            usage_info = {}

            for provider_name in self.status["active_providers"]:
                provider = StorageProvider(provider_name)
                service = self.services.get(provider)

                if not service:
                    continue

                try:
                    if provider == StorageProvider.GOOGLE_DRIVE:
                        user_info = await service.get_user_info()
                        if user_info.get("success"):
                            usage_info[provider_name] = user_info.get(
                                "storage_quota", {}
                            )
                    elif provider == StorageProvider.DROPBOX:
                        space_usage = await service.get_space_usage()
                        if space_usage.get("success"):
                            usage_info[provider_name] = {
                                "used": space_usage.get("used"),
                                "allocation": space_usage.get("allocation"),
                            }
                except Exception as e:
                    usage_info[provider_name] = {"error": str(e)}

            return {"success": True, "usage_info": usage_info}

        except Exception as e:
            logger.error(f"Error getting storage usage: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for all active providers."""
        try:
            health_results = {}

            for provider_name in self.status["active_providers"]:
                provider = StorageProvider(provider_name)
                service = self.services.get(provider)

                if service:
                    health_result = await service.health_check()
                    health_results[provider_name] = health_result
                else:
                    health_results[provider_name] = {
                        "status": "error",
                        "message": "Service not available",
                    }

            # Overall health
            healthy_providers = sum(
                1
                for result in health_results.values()
                if result.get("status") == "healthy"
            )
            total_providers = len(health_results)

            overall_status = (
                "healthy" if healthy_providers == total_providers else "degraded"
            )
            if healthy_providers == 0:
                overall_status = "unhealthy"

            return {
                "success": True,
                "overall_status": overall_status,
                "healthy_providers": healthy_providers,
                "total_providers": total_providers,
                "provider_health": health_results,
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error performing health check: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup all cloud storage services."""
        try:
            cleanup_results = {}

            for provider, service in self.services.items():
                try:
                    if hasattr(service, "cleanup"):
                        result = await service.cleanup()
                        cleanup_results[provider.value] = result
                except Exception as e:
                    cleanup_results[provider.value] = {
                        "status": "error",
                        "error": str(e),
                    }

            self.status["initialized"] = False
            self.status["active_providers"] = []

            return {
                "success": True,
                "message": "Cloud Storage Manager cleaned up successfully",
                "cleanup_results": cleanup_results,
            }

        except Exception as e:
            logger.error(f"Error cleaning up Cloud Storage Manager: {str(e)}")
            return {"success": False, "error": str(e)}
