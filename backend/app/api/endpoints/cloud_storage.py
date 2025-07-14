"""
Cloud Storage API Endpoints
API endpoints for cloud storage integrations (Google Drive, Dropbox).
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.auth import get_current_user
from ...models.user import User
from ...services.cloud_storage_integration_service import CloudStorageIntegrationService
from ...db.dependencies import get_db

router = APIRouter()


def get_cloud_storage_service(db: Session = Depends(get_db)) -> CloudStorageIntegrationService:
    """Dependency to get cloud storage integration service."""
    return CloudStorageIntegrationService(db)


class UploadRequest(BaseModel):
    provider: str  # "google_drive" or "dropbox"
    folder_path: Optional[str] = None
    filename: Optional[str] = None
    description: Optional[str] = None


class CreateFolderRequest(BaseModel):
    provider: str
    folder_name: str
    parent_folder_id: Optional[str] = None


class ShareFileRequest(BaseModel):
    provider: str
    file_id: str
    permissions: str = "read"  # "read", "write", "comment"
    expires_hours: Optional[int] = None


class SyncRequest(BaseModel):
    provider: str
    local_path: str
    remote_path: str
    sync_direction: str = "bidirectional"  # "upload", "download", "bidirectional"


class ProviderConfigRequest(BaseModel):
    provider: str
    config: Dict[str, Any]


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    provider: str = Query(...),
    folder_path: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Upload file to cloud storage provider."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to specified provider
        result = await cloud_service.upload_file(
            provider=provider,
            file_content=file_content,
            filename=file.filename,
            folder_path=folder_path,
            description=description,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "uploaded",
            "provider": provider,
            "file_id": result.get("file_id"),
            "file_url": result.get("file_url"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file to {provider}: {str(e)}"
        )


@router.get("/files")
async def list_files(
    provider: str = Query(...),
    folder_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    page_token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """List files from cloud storage provider."""
    try:
        result = await cloud_service.list_files(
            provider=provider,
            folder_id=folder_id,
            limit=limit,
            page_token=page_token,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider,
            "files": result.get("files", []),
            "next_page_token": result.get("next_page_token"),
            "total_count": result.get("total_count", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files from {provider}: {str(e)}"
        )


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    provider: str = Query(...),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Download file from cloud storage provider."""
    try:
        result = await cloud_service.download_file(
            provider=provider,
            file_id=file_id,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "ready",
            "provider": provider,
            "file_id": file_id,
            "download_url": result.get("download_url"),
            "filename": result.get("filename"),
            "size": result.get("size")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file from {provider}: {str(e)}"
        )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    provider: str = Query(...),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Delete file from cloud storage provider."""
    try:
        result = await cloud_service.delete_file(
            provider=provider,
            file_id=file_id,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "deleted",
            "provider": provider,
            "file_id": file_id,
            "deleted": result.get("success", False)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file from {provider}: {str(e)}"
        )


@router.post("/folders")
async def create_folder(
    request: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Create folder in cloud storage provider."""
    try:
        result = await cloud_service.create_folder(
            provider=request.provider,
            folder_name=request.folder_name,
            parent_folder_id=request.parent_folder_id,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "created",
            "provider": request.provider,
            "folder_id": result.get("folder_id"),
            "folder_name": request.folder_name,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create folder in {request.provider}: {str(e)}"
        )


@router.post("/files/{file_id}/share")
async def share_file(
    file_id: str,
    request: ShareFileRequest,
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Create shareable link for file."""
    try:
        result = await cloud_service.share_file(
            provider=request.provider,
            file_id=file_id,
            permissions=request.permissions,
            expires_hours=request.expires_hours,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "shared",
            "provider": request.provider,
            "file_id": file_id,
            "share_url": result.get("share_url"),
            "permissions": request.permissions,
            "expires_at": result.get("expires_at")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to share file from {request.provider}: {str(e)}"
        )


@router.post("/sync")
async def sync_files(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Sync files between local and cloud storage."""
    try:
        result = await cloud_service.sync_files(
            provider=request.provider,
            local_path=request.local_path,
            remote_path=request.remote_path,
            sync_direction=request.sync_direction,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "synced",
            "provider": request.provider,
            "sync_direction": request.sync_direction,
            "files_synced": result.get("files_synced", 0),
            "errors": result.get("errors", []),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync files with {request.provider}: {str(e)}"
        )


@router.get("/providers")
async def get_available_providers(
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Get list of available cloud storage providers."""
    try:
        providers = await cloud_service.get_available_providers()
        
        return {
            "providers": providers,
            "count": len(providers)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get providers: {str(e)}"
        )


@router.get("/providers/{provider}/status")
async def get_provider_status(
    provider: str,
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Get status of specific cloud storage provider."""
    try:
        status = await cloud_service.get_provider_status(
            provider=provider,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider,
            "status": status.get("status"),
            "connected": status.get("connected", False),
            "quota_used": status.get("quota_used"),
            "quota_total": status.get("quota_total"),
            "last_sync": status.get("last_sync"),
            "details": status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status for {provider}: {str(e)}"
        )


@router.post("/providers/{provider}/configure")
async def configure_provider(
    provider: str,
    request: ProviderConfigRequest,
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Configure cloud storage provider settings."""
    try:
        result = await cloud_service.configure_provider(
            provider=provider,
            config=request.config,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "configured",
            "provider": provider,
            "configured": result.get("success", False),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to configure {provider}: {str(e)}"
        )


@router.post("/providers/{provider}/authorize")
async def authorize_provider(
    provider: str,
    authorization_code: str = Query(...),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Authorize access to cloud storage provider."""
    try:
        result = await cloud_service.authorize_provider(
            provider=provider,
            authorization_code=authorization_code,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "authorized",
            "provider": provider,
            "authorized": result.get("success", False),
            "access_token": result.get("access_token_preview"),  # Just preview
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authorize {provider}: {str(e)}"
        )


@router.get("/health")
async def get_cloud_storage_health(
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Get health status of all cloud storage integrations."""
    try:
        health = await cloud_service.get_service_status()
        
        return {
            "service_healthy": health.get("success", False),
            "providers_status": health.get("providers", {}),
            "last_check": health.get("last_check"),
            "details": health
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health status: {str(e)}"
        )


@router.get("/usage")
async def get_usage_statistics(
    provider: Optional[str] = Query(None),
    days: int = Query(30, le=365),
    current_user: User = Depends(get_current_user),
    cloud_service: CloudStorageIntegrationService = Depends(get_cloud_storage_service),
):
    """Get usage statistics for cloud storage."""
    try:
        stats = await cloud_service.get_usage_statistics(
            provider=provider,
            days=days,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider or "all",
            "period_days": days,
            "uploads": stats.get("uploads", 0),
            "downloads": stats.get("downloads", 0),
            "storage_used": stats.get("storage_used", 0),
            "api_calls": stats.get("api_calls", 0),
            "details": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage statistics: {str(e)}"
        )