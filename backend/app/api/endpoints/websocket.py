"""
WebSocket endpoints for real-time notifications
"""

import json
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.services.notification_service import NotificationService
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time notifications.

    Args:
        websocket: WebSocket connection
        user_id: User ID for the connection
        token: JWT access token for authentication
        db: Database session
    """
    connection_id = str(uuid.uuid4())

    # Attempt to connect
    connected = await connection_manager.connect(
        websocket, user_id, connection_id, token
    )

    if not connected:
        return

    notification_service = NotificationService(db)

    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")
                message_data = message.get("data", {})

                # Handle different message types
                if message_type == "heartbeat:ping":
                    await connection_manager.handle_heartbeat(user_id, connection_id)

                elif message_type == "notification:mark_read":
                    notification_id = message_data.get("notification_id")
                    if notification_id:
                        await notification_service.mark_as_read(
                            notification_id, user_id
                        )

                elif message_type == "notification:mark_all_read":
                    category = message_data.get("category")
                    await notification_service.mark_all_as_read(user_id, category)

                elif message_type == "notification:archive":
                    notification_id = message_data.get("notification_id")
                    if notification_id:
                        await notification_service.archive_notification(
                            notification_id, user_id
                        )

                elif message_type == "user:set_presence":
                    status = message_data.get("status")
                    page = message_data.get("page")
                    if status:
                        await notification_service.update_user_presence(
                            user_id=user_id, status=status, page=page
                        )

                elif message_type == "notification:get_unread_count":
                    # Send current unread count
                    unread_count = notification_service.get_unread_count(user_id)
                    unread_by_category = (
                        notification_service.get_unread_count_by_category(user_id)
                    )

                    await connection_manager.send_personal_message(
                        user_id,
                        {
                            "type": "notification:unread_count",
                            "data": {
                                "total": unread_count,
                                "by_category": unread_by_category,
                            },
                        },
                    )

                elif message_type == "notification:get_recent":
                    # Send recent notifications
                    limit = min(message_data.get("limit", 10), 50)
                    notifications = notification_service.get_user_notifications(
                        user_id=user_id, limit=limit, is_archived=False
                    )

                    await connection_manager.send_personal_message(
                        user_id,
                        {
                            "type": "notification:recent",
                            "data": {
                                "notifications": [n.to_dict() for n in notifications]
                            },
                        },
                    )

                elif message_type == "room:join":
                    room_name = message_data.get("room")
                    if room_name and room_name.startswith(
                        ("tender:", "task:", "project:")
                    ):
                        await connection_manager.join_room(
                            room_name, user_id, connection_id
                        )

                        await connection_manager.send_personal_message(
                            user_id,
                            {"type": "room:joined", "data": {"room": room_name}},
                        )

                elif message_type == "room:leave":
                    room_name = message_data.get("room")
                    if room_name:
                        await connection_manager.leave_room(
                            room_name, user_id, connection_id
                        )

                        await connection_manager.send_personal_message(
                            user_id, {"type": "room:left", "data": {"room": room_name}}
                        )

                else:
                    logger.warning(
                        f"Unknown message type from user {user_id}: {message_type}"
                    )

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from user {user_id}: {data}")
            except Exception as e:
                logger.error(f"Error processing message from user {user_id}: {str(e)}")
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "data": {
                            "message": "Error processing message",
                            "error": str(e),
                        },
                    },
                )

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"Unexpected error in websocket for user {user_id}: {str(e)}")
    finally:
        await connection_manager.disconnect(user_id, connection_id)


@router.websocket("/ws/global")
async def websocket_global(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db),
):
    """
    Global WebSocket endpoint for system-wide notifications.
    Admins can use this to broadcast messages.
    """
    connection_id = str(uuid.uuid4())

    # For global endpoint, we need to verify admin privileges
    # This is a simplified implementation - you might want more sophisticated auth
    try:
        from app.core.auth import decode_access_token

        payload = decode_access_token(token)

        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = payload.get("sub")
        # TODO: Check if user has admin privileges

        await websocket.accept()
        await connection_manager.join_room("global_admin", user_id, connection_id)

        try:
            while True:
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    message_data = message.get("data", {})

                    if message_type == "system:broadcast":
                        # Broadcast system message to all users
                        await connection_manager.broadcast_system_message(message_data)

                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "broadcast:sent",
                                    "data": {"status": "success"},
                                }
                            )
                        )

                    elif message_type == "room:broadcast":
                        room_name = message_data.get("room")
                        broadcast_message = message_data.get("message")

                        if room_name and broadcast_message:
                            await connection_manager.send_room_message(
                                room_name, broadcast_message
                            )

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from global connection: {data}")

        except WebSocketDisconnect:
            pass
        finally:
            await connection_manager.leave_room("global_admin", user_id, connection_id)

    except Exception as e:
        logger.error(f"Error in global websocket: {str(e)}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass


# HTTP endpoints for notification management


@router.get("/notifications")
async def get_notifications(
    category: str = None,
    is_read: bool = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get user notifications with filters."""
    from app.models.notification import NotificationCategory

    notification_service = NotificationService(db)

    category_enum = None
    if category:
        try:
            category_enum = NotificationCategory(category)
        except ValueError:
            pass

    notifications = notification_service.get_user_notifications(
        user_id=str(current_user.id),
        category=category_enum,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )

    return {
        "notifications": [n.to_dict() for n in notifications],
        "total": len(notifications),
    }


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get unread notification count."""
    notification_service = NotificationService(db)

    total_count = notification_service.get_unread_count(str(current_user.id))
    by_category = notification_service.get_unread_count_by_category(
        str(current_user.id)
    )

    return {"total": total_count, "by_category": by_category}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark notification as read."""
    notification_service = NotificationService(db)

    success = await notification_service.mark_as_read(
        notification_id, str(current_user.id)
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "success"}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    category: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark all notifications as read."""
    from app.models.notification import NotificationCategory

    notification_service = NotificationService(db)

    category_enum = None
    if category:
        try:
            category_enum = NotificationCategory(category)
        except ValueError:
            pass

    count = await notification_service.mark_all_as_read(
        str(current_user.id), category_enum
    )

    return {"status": "success", "marked_count": count}


@router.post("/notifications/{notification_id}/archive")
async def archive_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Archive notification."""
    notification_service = NotificationService(db)

    success = await notification_service.archive_notification(
        notification_id, str(current_user.id)
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "success"}


@router.get("/notifications/settings")
async def get_notification_settings(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get user notification settings."""
    notification_service = NotificationService(db)
    settings = notification_service.get_user_settings(str(current_user.id))

    return {
        "licitacoes_enabled": settings.licitacoes_enabled,
        "tarefas_enabled": settings.tarefas_enabled,
        "sistema_enabled": settings.sistema_enabled,
        "mensagens_enabled": settings.mensagens_enabled,
        "websocket_enabled": settings.websocket_enabled,
        "email_enabled": settings.email_enabled,
        "sms_enabled": settings.sms_enabled,
        "browser_notifications": settings.browser_notifications,
        "dnd_enabled": settings.dnd_enabled,
        "dnd_start_time": settings.dnd_start_time,
        "dnd_end_time": settings.dnd_end_time,
        "dnd_weekends": settings.dnd_weekends,
        "sound_enabled": settings.sound_enabled,
        "sound_theme": settings.sound_theme,
        "sound_volume": settings.sound_volume,
    }


@router.put("/notifications/settings")
async def update_notification_settings(
    settings_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update user notification settings."""
    notification_service = NotificationService(db)

    updated_settings = notification_service.update_user_settings(
        str(current_user.id), settings_data
    )

    return {"status": "success", "message": "Settings updated successfully"}


from fastapi import HTTPException

# Import dependencies
from app.core.auth import get_current_user
