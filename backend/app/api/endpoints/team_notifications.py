"""
Team Notifications API Endpoints
API endpoints for team notification integrations (Slack, Microsoft Teams).
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.auth import get_current_user
from ...models.user import User
from ...services.team_notifications_integration_service import TeamNotificationsIntegrationService
from ...db.dependencies import get_db

router = APIRouter()


def get_team_notifications_service(db: Session = Depends(get_db)) -> TeamNotificationsIntegrationService:
    """Dependency to get team notifications integration service."""
    return TeamNotificationsIntegrationService(db)


class SendMessageRequest(BaseModel):
    provider: str  # "slack" or "teams"
    channel_id: str
    message: str
    message_type: str = "text"  # "text", "rich", "card"
    thread_id: Optional[str] = None


class SendRichMessageRequest(BaseModel):
    provider: str
    channel_id: str
    title: str
    message: str
    color: Optional[str] = None
    fields: Optional[List[Dict[str, str]]] = None
    buttons: Optional[List[Dict[str, str]]] = None
    image_url: Optional[str] = None


class CreateChannelRequest(BaseModel):
    provider: str
    channel_name: str
    description: Optional[str] = None
    is_private: bool = False
    members: Optional[List[str]] = None


class SendFileRequest(BaseModel):
    provider: str
    channel_id: str
    file_url: str
    filename: str
    comment: Optional[str] = None


class WorkflowNotificationRequest(BaseModel):
    provider: str
    workflow_type: str  # "tender_alert", "deadline_reminder", "status_update"
    channel_id: str
    data: Dict[str, Any]


class ProviderConfigRequest(BaseModel):
    provider: str
    config: Dict[str, Any]


@router.post("/send/text")
async def send_text_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Send text message to team channel."""
    try:
        result = await team_service.send_message(
            provider=request.provider,
            channel_id=request.channel_id,
            message=request.message,
            thread_id=request.thread_id,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "sent",
            "provider": request.provider,
            "channel_id": request.channel_id,
            "message_id": result.get("message_id"),
            "timestamp": result.get("timestamp"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to send message via {request.provider}: {str(e)}"
        )


@router.post("/send/rich")
async def send_rich_message(
    request: SendRichMessageRequest,
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Send rich formatted message with attachments."""
    try:
        result = await team_service.send_rich_message(
            provider=request.provider,
            channel_id=request.channel_id,
            title=request.title,
            message=request.message,
            color=request.color,
            fields=request.fields,
            buttons=request.buttons,
            image_url=request.image_url,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "sent",
            "provider": request.provider,
            "channel_id": request.channel_id,
            "message_id": result.get("message_id"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send rich message via {request.provider}: {str(e)}"
        )


@router.post("/send/file")
async def send_file(
    request: SendFileRequest,
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Send file to team channel."""
    try:
        result = await team_service.send_file(
            provider=request.provider,
            channel_id=request.channel_id,
            file_url=request.file_url,
            filename=request.filename,
            comment=request.comment,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "sent",
            "provider": request.provider,
            "channel_id": request.channel_id,
            "file_id": result.get("file_id"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send file via {request.provider}: {str(e)}"
        )


@router.post("/send/workflow")
async def send_workflow_notification(
    request: WorkflowNotificationRequest,
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Send workflow-specific notification."""
    try:
        result = await team_service.send_workflow_notification(
            provider=request.provider,
            workflow_type=request.workflow_type,
            channel_id=request.channel_id,
            data=request.data,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "sent",
            "provider": request.provider,
            "workflow_type": request.workflow_type,
            "channel_id": request.channel_id,
            "message_id": result.get("message_id"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send workflow notification via {request.provider}: {str(e)}"
        )


@router.get("/channels")
async def list_channels(
    provider: str = Query(...),
    limit: int = Query(50, le=100),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """List available channels for provider."""
    try:
        result = await team_service.list_channels(
            provider=provider,
            limit=limit,
            cursor=cursor,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider,
            "channels": result.get("channels", []),
            "next_cursor": result.get("next_cursor"),
            "total_count": result.get("total_count", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list channels from {provider}: {str(e)}"
        )


@router.post("/channels")
async def create_channel(
    request: CreateChannelRequest,
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Create new channel in team platform."""
    try:
        result = await team_service.create_channel(
            provider=request.provider,
            channel_name=request.channel_name,
            description=request.description,
            is_private=request.is_private,
            members=request.members,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "created",
            "provider": request.provider,
            "channel_id": result.get("channel_id"),
            "channel_name": request.channel_name,
            "channel_url": result.get("channel_url"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create channel in {request.provider}: {str(e)}"
        )


@router.get("/channels/{channel_id}/messages")
async def get_channel_messages(
    channel_id: str,
    provider: str = Query(...),
    limit: int = Query(20, le=100),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Get messages from channel."""
    try:
        result = await team_service.get_channel_messages(
            provider=provider,
            channel_id=channel_id,
            limit=limit,
            cursor=cursor,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider,
            "channel_id": channel_id,
            "messages": result.get("messages", []),
            "next_cursor": result.get("next_cursor"),
            "total_count": result.get("total_count", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get messages from {provider}: {str(e)}"
        )


@router.get("/providers")
async def get_available_providers(
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Get list of available team notification providers."""
    try:
        providers = await team_service.get_available_providers()
        
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
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Get status of specific team notification provider."""
    try:
        status = await team_service.get_provider_status(
            provider=provider,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider,
            "status": status.get("status"),
            "connected": status.get("connected", False),
            "workspace_name": status.get("workspace_name"),
            "user_name": status.get("user_name"),
            "permissions": status.get("permissions", []),
            "last_activity": status.get("last_activity"),
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
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Configure team notification provider settings."""
    try:
        result = await team_service.configure_provider(
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
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Authorize access to team notification provider."""
    try:
        result = await team_service.authorize_provider(
            provider=provider,
            authorization_code=authorization_code,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "authorized",
            "provider": provider,
            "authorized": result.get("success", False),
            "workspace_info": result.get("workspace_info"),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authorize {provider}: {str(e)}"
        )


@router.post("/webhooks/{provider}")
async def handle_webhook(
    provider: str,
    webhook_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Handle incoming webhook from team notification provider."""
    try:
        result = await team_service.handle_webhook(
            provider=provider,
            webhook_data=webhook_data,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "processed",
            "provider": provider,
            "event_type": result.get("event_type"),
            "processed": result.get("success", False),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook from {provider}: {str(e)}"
        )


@router.get("/health")
async def get_team_notifications_health(
    current_user: User = Depends(get_current_user),
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Get health status of all team notification integrations."""
    try:
        health = await team_service.get_service_status()
        
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
    team_service: TeamNotificationsIntegrationService = Depends(get_team_notifications_service),
):
    """Get usage statistics for team notifications."""
    try:
        stats = await team_service.get_usage_statistics(
            provider=provider,
            days=days,
            user_id=str(current_user.id)
        )
        
        return {
            "provider": provider or "all",
            "period_days": days,
            "messages_sent": stats.get("messages_sent", 0),
            "channels_created": stats.get("channels_created", 0),
            "files_shared": stats.get("files_shared", 0),
            "api_calls": stats.get("api_calls", 0),
            "details": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage statistics: {str(e)}"
        )