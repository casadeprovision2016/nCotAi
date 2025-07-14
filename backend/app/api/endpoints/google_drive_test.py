"""
Google Drive API test endpoints for COTAI backend.
Endpoints for testing Google Drive integration and connectivity.
"""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.models.user import User
from app.services.cloud_storage_integration_service import CloudStorageIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def google_drive_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Check Google Drive service health and connectivity.
    """
    try:
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        # Check if Google Drive is configured
        if not settings.GOOGLE_DRIVE_CONFIGURED:
            return {
                "status": "error",
                "message": "Google Drive not configured",
                "details": {
                    "client_id_configured": bool(settings.GOOGLE_DRIVE_CLIENT_ID),
                    "client_secret_configured": bool(settings.GOOGLE_DRIVE_CLIENT_SECRET),
                    "redirect_uri_configured": bool(settings.GOOGLE_DRIVE_REDIRECT_URI),
                }
            }
        
        # Initialize services
        init_result = await cloud_service.initialize_services()
        
        # Get Google Drive status
        if cloud_service.google_drive_service:
            gdrive_health = await cloud_service.google_drive_service.health_check()
        else:
            gdrive_health = {
                "status": "error",
                "message": "Google Drive service not available"
            }
        
        return {
            "status": "success",
            "message": "Google Drive health check completed",
            "google_drive_configured": settings.GOOGLE_DRIVE_CONFIGURED,
            "service_health": gdrive_health,
            "initialization": init_result,
            "configuration": {
                "client_id": settings.GOOGLE_DRIVE_CLIENT_ID[:20] + "..." if settings.GOOGLE_DRIVE_CLIENT_ID else None,
                "project_id": settings.GOOGLE_DRIVE_PROJECT_ID,
                "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
                "scopes": settings.GOOGLE_DRIVE_SCOPES,
            }
        }
        
    except Exception as e:
        logger.error(f"Google Drive health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/authorization-url", response_model=Dict[str, str])
async def get_google_drive_authorization_url(
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Get Google Drive OAuth2 authorization URL.
    """
    try:
        if not settings.GOOGLE_DRIVE_CONFIGURED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Drive not configured"
            )
        
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        if not cloud_service.google_drive_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Drive service not available"
            )
        
        # Get authorization URL
        auth_url = cloud_service.google_drive_service.get_authorization_url(state)
        
        return {
            "authorization_url": auth_url,
            "state": state or "",
            "message": "Visit this URL to authorize access to Google Drive"
        }
        
    except Exception as e:
        logger.error(f"Error getting authorization URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get authorization URL: {str(e)}"
        )


@router.post("/callback", response_model=Dict[str, Any])
async def google_drive_oauth_callback(
    request_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Handle Google Drive OAuth2 callback.
    
    Expected request_data:
    {
        "code": "authorization_code_from_google",
        "state": "optional_state_parameter"
    }
    """
    try:
        authorization_code = request_data.get("code")
        if not authorization_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
        
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        if not cloud_service.google_drive_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Drive service not available"
            )
        
        # Exchange code for tokens
        token_result = await cloud_service.google_drive_service.exchange_code_for_tokens(
            authorization_code
        )
        
        if not token_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token exchange failed: {token_result.get('error')}"
            )
        
        return {
            "status": "success",
            "message": "Google Drive authorization completed successfully",
            "token_info": {
                "expires_at": token_result.get("expires_at"),
                "has_refresh_token": bool(token_result.get("refresh_token")),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/test-upload", response_model=Dict[str, Any])
async def test_google_drive_upload(
    file: UploadFile = File(...),
    folder_id: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Test file upload to Google Drive.
    """
    try:
        # Validate file size
        if file.size and file.size > settings.CLOUD_STORAGE_MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {settings.CLOUD_STORAGE_MAX_FILE_SIZE} bytes"
            )
        
        # Validate file type
        if file.content_type not in settings.CLOUD_STORAGE_ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed"
            )
        
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        if not cloud_service.google_drive_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Drive service not available"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Upload file
        upload_result = await cloud_service.upload_file(
            provider="google_drive",
            file_content=file_content,
            filename=file.filename,
            folder_path=folder_id,
            description=description,
            user_id=str(current_user.id),
        )
        
        if not upload_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {upload_result.get('error')}"
            )
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully to Google Drive",
            "upload_result": upload_result,
            "file_info": {
                "original_name": file.filename,
                "size": file.size,
                "content_type": file.content_type,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload test failed: {str(e)}"
        )


@router.get("/test-list-files", response_model=Dict[str, Any])
async def test_google_drive_list_files(
    folder_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Test listing files from Google Drive.
    """
    try:
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        if not cloud_service.google_drive_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Drive service not available"
            )
        
        # List files
        list_result = await cloud_service.list_files(
            provider="google_drive",
            folder_id=folder_id,
            limit=limit,
            user_id=str(current_user.id),
        )
        
        if not list_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File listing failed: {list_result.get('error')}"
            )
        
        return {
            "status": "success",
            "message": "Files listed successfully from Google Drive",
            "list_result": list_result,
            "parameters": {
                "folder_id": folder_id,
                "limit": limit,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test list files error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File listing test failed: {str(e)}"
        )


@router.get("/user-info", response_model=Dict[str, Any])
async def get_google_drive_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get Google Drive user information and storage quota.
    """
    try:
        # Initialize cloud storage service
        cloud_service = CloudStorageIntegrationService(db)
        
        if not cloud_service.google_drive_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google Drive service not available"
            )
        
        # Get user info
        user_info = await cloud_service.google_drive_service.get_user_info()
        
        if not user_info.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get user info: {user_info.get('error')}"
            )
        
        return {
            "status": "success",
            "message": "Google Drive user information retrieved successfully",
            "user_info": user_info,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.get("/configuration", response_model=Dict[str, Any])
async def get_google_drive_configuration(
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get Google Drive configuration status.
    """
    try:
        return {
            "status": "success",
            "google_drive_configured": settings.GOOGLE_DRIVE_CONFIGURED,
            "cloud_storage_enabled": settings.CLOUD_STORAGE_ENABLED,
            "configuration": {
                "has_client_id": bool(settings.GOOGLE_DRIVE_CLIENT_ID),
                "has_client_secret": bool(settings.GOOGLE_DRIVE_CLIENT_SECRET),
                "has_redirect_uri": bool(settings.GOOGLE_DRIVE_REDIRECT_URI),
                "project_id": settings.GOOGLE_DRIVE_PROJECT_ID,
                "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
                "scopes": settings.GOOGLE_DRIVE_SCOPES,
                "default_provider": settings.CLOUD_STORAGE_DEFAULT_PROVIDER,
                "max_file_size": settings.CLOUD_STORAGE_MAX_FILE_SIZE,
                "allowed_file_types": settings.CLOUD_STORAGE_ALLOWED_TYPES,
            }
        }
        
    except Exception as e:
        logger.error(f"Get configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )