"""
WhatsApp API Endpoints
API endpoints for WhatsApp Business integration.
"""

import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from ...core.auth import get_current_user
from ...models.user import User
from ...services.whatsapp_integration_service import WhatsAppIntegrationService

router = APIRouter()


class SendMessageRequest(BaseModel):
    to: str
    message: str
    message_type: str = "text"


class SendTemplateRequest(BaseModel):
    to: str
    template_name: str
    parameters: Optional[List[str]] = None
    language_code: str = "pt_BR"


class SendTenderAlertRequest(BaseModel):
    to: str
    tender_data: Dict[str, Any]


class SendInteractiveRequest(BaseModel):
    to: str
    header: str
    body: str
    footer: str
    buttons: List[Dict[str, str]]


class SendDocumentRequest(BaseModel):
    to: str
    document_url: str
    filename: str
    caption: str = ""


class UpdateProfileRequest(BaseModel):
    about: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    name: str
    language: str
    category: str
    components: List[Dict[str, Any]]


@router.post("/send/text")
async def send_text_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a text message via WhatsApp."""
    try:
        result = await whatsapp_service.send_text_message(request.to, request.message)
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post("/send/template")
async def send_template_message(
    request: SendTemplateRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a template message via WhatsApp."""
    try:
        result = await whatsapp_service.send_template_message(
            to=request.to,
            template_name=request.template_name,
            language_code=request.language_code,
            parameters=request.parameters,
        )
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send template: {str(e)}"
        )


@router.post("/send/tender-alert")
async def send_tender_alert(
    request: SendTenderAlertRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a tender alert notification."""
    try:
        result = await whatsapp_service.send_tender_alert(
            request.to, request.tender_data
        )
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send tender alert: {str(e)}"
        )


@router.post("/send/deadline-reminder")
async def send_deadline_reminder(
    to: str,
    tender_data: Dict[str, Any],
    days_left: int,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a deadline reminder."""
    try:
        result = await whatsapp_service.send_deadline_reminder(
            to, tender_data, days_left
        )
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send deadline reminder: {str(e)}"
        )


@router.post("/send/status-update")
async def send_status_update(
    to: str,
    quotation_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a quotation status update."""
    try:
        result = await whatsapp_service.send_status_update(to, quotation_data)
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send status update: {str(e)}"
        )


@router.post("/send/interactive")
async def send_interactive_message(
    request: SendInteractiveRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send an interactive message with buttons."""
    try:
        result = await whatsapp_service.send_interactive_message(
            to=request.to,
            header=request.header,
            body=request.body,
            footer=request.footer,
            buttons=request.buttons,
        )
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send interactive message: {str(e)}"
        )


@router.post("/send/document")
async def send_document(
    request: SendDocumentRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Send a document via WhatsApp."""
    try:
        result = await whatsapp_service.send_document(
            to=request.to,
            document_url=request.document_url,
            filename=request.filename,
            caption=request.caption,
        )
        return {
            "status": "sent",
            "message_id": result.get("messages", [{}])[0].get("id"),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send document: {str(e)}"
        )


@router.get("/message/{message_id}/status")
async def get_message_status(
    message_id: str,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Get the status of a sent message."""
    try:
        status = await whatsapp_service.get_message_status(message_id)
        return {"message_id": message_id, "status": status}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get message status: {str(e)}"
        )


@router.post("/message/{message_id}/mark-read")
async def mark_message_as_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Mark a message as read."""
    try:
        success = await whatsapp_service.mark_message_as_read(message_id)
        return {"message_id": message_id, "marked_as_read": success}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to mark message as read: {str(e)}"
        )


@router.get("/profile")
async def get_business_profile(
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Get WhatsApp Business profile."""
    try:
        profile = await whatsapp_service.get_business_profile()
        return {"profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.put("/profile")
async def update_business_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Update WhatsApp Business profile."""
    try:
        profile_data = request.dict(exclude_none=True)
        success = await whatsapp_service.update_business_profile(profile_data)
        return {"updated": success, "profile_data": profile_data}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/templates")
async def get_message_templates(
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Get all message templates."""
    try:
        templates = await whatsapp_service.get_templates()
        local_templates = whatsapp_service.template_manager.list_templates()
        return {"api_templates": templates, "local_templates": local_templates}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get templates: {str(e)}"
        )


@router.post("/templates")
async def create_message_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Create a new message template."""
    try:
        template_data = request.dict()

        # Validate template
        validation = whatsapp_service.template_manager.validate_template(template_data)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, detail=f"Invalid template: {validation['errors']}"
            )

        result = await whatsapp_service.template_manager.create_template(template_data)
        return {"status": "created", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create template: {str(e)}"
        )


@router.delete("/templates/{template_name}")
async def delete_message_template(
    template_name: str,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Delete a message template."""
    try:
        success = await whatsapp_service.template_manager.delete_template(template_name)
        return {"template_name": template_name, "deleted": success}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete template: {str(e)}"
        )


@router.get("/health")
async def get_whatsapp_health(
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Get WhatsApp service health status."""
    try:
        health = await whatsapp_service.health_check()
        bot_stats = whatsapp_service.bot_manager.get_session_stats()

        return {
            "service_healthy": health,
            "bot_statistics": bot_stats,
            "last_check": "2024-01-01T12:00:00Z",  # Would be actual timestamp
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get health status: {str(e)}"
        )


@router.get("/bot/sessions")
async def get_bot_sessions(
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Get bot session statistics."""
    try:
        stats = whatsapp_service.bot_manager.get_session_stats()
        return {"session_statistics": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get bot sessions: {str(e)}"
        )


# Webhook endpoints (no authentication required)
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Verify webhook for WhatsApp."""
    if (
        hub_mode == "subscribe"
        and hub_verify_token == whatsapp_service.webhook_verify_token
    ):
        return int(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Handle incoming WhatsApp webhook."""
    try:
        # Get raw body
        body = await request.body()
        body_str = body.decode("utf-8")

        # Verify signature
        if x_hub_signature_256:
            if not whatsapp_service.verify_webhook(x_hub_signature_256, body_str):
                raise HTTPException(status_code=403, detail="Invalid signature")

        # Parse payload
        payload = json.loads(body_str)

        # Handle webhook
        result = await whatsapp_service.webhook_handler.handle_webhook(payload)

        return {"status": "received", "result": result}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Webhook handling failed: {str(e)}"
        )


@router.post("/test/send-welcome")
async def test_send_welcome(
    phone_number: str,
    user_name: str,
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Test endpoint to send welcome message."""
    try:
        result = await whatsapp_service.template_manager.send_welcome_template(
            phone_number, user_name
        )
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send welcome: {str(e)}")


@router.post("/setup-templates")
async def setup_default_templates(
    current_user: User = Depends(get_current_user),
    whatsapp_service: WhatsAppIntegrationService = Depends(),
):
    """Setup default message templates."""
    try:
        results = await whatsapp_service.template_manager.setup_default_templates()
        return {"setup_results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to setup templates: {str(e)}"
        )
