"""
Real-Time Notification Service
Handles creation, delivery, and management of notifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationSettings,
    NotificationTemplate,
    NotificationType,
    UserPresence,
    UserPresenceStatus,
)
from app.models.user import User
from app.services.tasks.notifications import (
    send_email_notification,
    send_whatsapp_notification,
)
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing real-time notifications."""

    def __init__(self, db: Session):
        self.db = db

    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        category: NotificationCategory,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        related_type: str = None,
        related_id: str = None,
        action_url: str = None,
        action_text: str = None,
        action_data: dict = None,
        expires_hours: int = None,
        metadata: dict = None,
        created_by: str = None,
        auto_send: bool = True,
    ) -> Notification:
        """
        Create a new notification.

        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            category: Notification category
            type: Notification type
            priority: Notification priority
            related_type: Type of related entity
            related_id: ID of related entity
            action_url: URL for notification action
            action_text: Text for action button
            action_data: Additional action data
            expires_hours: Hours until notification expires
            metadata: Additional metadata
            created_by: ID of user who created notification
            auto_send: Whether to automatically send via WebSocket

        Returns:
            Created notification
        """
        try:
            # Create notification
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                type=type,
                priority=priority,
                related_type=related_type,
                related_id=related_id,
                action_url=action_url,
                action_text=action_text,
                action_data=action_data,
                expires_at=(
                    datetime.utcnow() + timedelta(hours=expires_hours)
                    if expires_hours
                    else None
                ),
                metadata=metadata,
                created_by=created_by,
            )

            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)

            logger.info(f"Created notification {notification.id} for user {user_id}")

            # Auto-send if requested
            if auto_send:
                await self.send_notification(notification)

            return notification

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating notification: {str(e)}")
            raise

    async def create_from_template(
        self,
        template_name: str,
        user_id: str,
        context: dict,
        created_by: str = None,
        auto_send: bool = True,
    ) -> Notification:
        """
        Create notification from template.

        Args:
            template_name: Name of notification template
            user_id: Target user ID
            context: Template context variables
            created_by: ID of user who created notification
            auto_send: Whether to automatically send

        Returns:
            Created notification
        """
        # Get template
        template = (
            self.db.query(NotificationTemplate)
            .filter(
                and_(
                    NotificationTemplate.name == template_name,
                    NotificationTemplate.is_active == True,
                )
            )
            .first()
        )

        if not template:
            raise ValueError(f"Template '{template_name}' not found or inactive")

        # Render template
        rendered = template.render(context)

        # Update template usage
        template.usage_count += 1
        template.last_used_at = datetime.utcnow()

        # Create notification
        notification = await self.create_notification(
            user_id=user_id,
            title=rendered["title"],
            message=rendered["message"],
            category=rendered["category"],
            type=rendered["type"],
            priority=rendered["priority"],
            action_url=rendered["action_url"],
            action_text=rendered["action_text"],
            expires_hours=(
                (rendered["expires_at"] - datetime.utcnow()).total_seconds() / 3600
                if rendered["expires_at"]
                else None
            ),
            metadata={"template_name": template_name, "context": context},
            created_by=created_by,
            auto_send=auto_send,
        )

        self.db.commit()
        return notification

    async def send_notification(self, notification: Notification):
        """
        Send notification via appropriate channels.

        Args:
            notification: Notification to send
        """
        try:
            # Get user settings
            settings = self.get_user_settings(notification.user_id)

            # Check if category is enabled
            if not settings.is_category_enabled(notification.category):
                logger.debug(
                    f"Category {notification.category} disabled for user {notification.user_id}"
                )
                return

            # Check do-not-disturb
            if (
                settings.is_in_dnd_period()
                and notification.priority != NotificationPriority.URGENT
            ):
                logger.debug(
                    f"User {notification.user_id} in DND period, skipping non-urgent notification"
                )
                return

            # Send via WebSocket (real-time)
            if settings.websocket_enabled and settings.should_send_via_channel(
                notification.priority, "websocket"
            ):
                await self._send_websocket(notification)

            # Send via email (if configured)
            if settings.email_enabled and settings.should_send_via_channel(
                notification.priority, "email"
            ):
                await self._send_email(notification)

            # Send via SMS (for high priority)
            if settings.sms_enabled and settings.should_send_via_channel(
                notification.priority, "sms"
            ):
                await self._send_sms(notification)

            logger.info(f"Sent notification {notification.id} via configured channels")

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {str(e)}")

    async def _send_websocket(self, notification: Notification):
        """Send notification via WebSocket."""
        try:
            await connection_manager.send_personal_message(
                user_id=str(notification.user_id),
                message={"type": "notification:new", "data": notification.to_dict()},
            )

            # Update delivery status
            notification.sent_via_websocket = True
            notification.websocket_sent_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {str(e)}")

    async def _send_email(self, notification: Notification):
        """Send notification via email."""
        try:
            user = self.db.query(User).filter(User.id == notification.user_id).first()
            if not user or not user.email:
                return

            # Queue email task
            send_email_notification.delay(
                to_email=user.email,
                subject=notification.title,
                template="notification",
                context={
                    "notification": notification.to_dict(),
                    "user": {
                        "first_name": user.first_name,
                        "full_name": user.full_name,
                    },
                },
            )

            # Update delivery status
            notification.sent_via_email = True
            notification.email_sent_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            logger.error(f"Error queuing email notification: {str(e)}")

    async def _send_sms(self, notification: Notification):
        """Send notification via SMS."""
        try:
            user = self.db.query(User).filter(User.id == notification.user_id).first()
            if not user or not user.phone:
                return

            # Create SMS message
            sms_message = f"COTAI: {notification.title}"
            if len(sms_message) > 160:
                sms_message = sms_message[:157] + "..."

            # Queue SMS task
            send_whatsapp_notification.delay(
                phone_number=user.phone,
                message=sms_message,
                notification_type="notification",
            )

            # Update delivery status
            notification.sent_via_sms = True
            notification.sms_sent_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            logger.error(f"Error queuing SMS notification: {str(e)}")

    def get_user_notifications(
        self,
        user_id: str,
        category: NotificationCategory = None,
        is_read: bool = None,
        is_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        """
        Get user notifications with filters.

        Args:
            user_id: User ID
            category: Filter by category
            is_read: Filter by read status
            is_archived: Filter by archived status
            limit: Maximum number of notifications
            offset: Offset for pagination

        Returns:
            List of notifications
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        if category:
            query = query.filter(Notification.category == category)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        query = query.filter(Notification.is_archived == is_archived)

        # Exclude expired notifications
        query = query.filter(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow(),
            )
        )

        return (
            query.order_by(desc(Notification.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for user."""
        return (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False,
                    or_(
                        Notification.expires_at.is_(None),
                        Notification.expires_at > datetime.utcnow(),
                    ),
                )
            )
            .count()
        )

    def get_unread_count_by_category(self, user_id: str) -> Dict[str, int]:
        """Get count of unread notifications by category."""
        from sqlalchemy import func

        results = (
            self.db.query(
                Notification.category, func.count(Notification.id).label("count")
            )
            .filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False,
                    or_(
                        Notification.expires_at.is_(None),
                        Notification.expires_at > datetime.utcnow(),
                    ),
                )
            )
            .group_by(Notification.category)
            .all()
        )

        counts = {category.value: 0 for category in NotificationCategory}
        for category, count in results:
            counts[category.value] = count

        return counts

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security)

        Returns:
            True if successful, False otherwise
        """
        try:
            notification = (
                self.db.query(Notification)
                .filter(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
                .first()
            )

            if not notification:
                return False

            if not notification.is_read:
                notification.mark_as_read()
                self.db.commit()

                # Send WebSocket update
                await connection_manager.send_personal_message(
                    user_id=user_id,
                    message={
                        "type": "notification:read",
                        "data": {
                            "notification_id": notification_id,
                            "read_at": notification.read_at.isoformat(),
                        },
                    },
                )

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

    async def mark_all_as_read(
        self, user_id: str, category: NotificationCategory = None
    ) -> int:
        """
        Mark all notifications as read for user.

        Args:
            user_id: User ID
            category: Optional category filter

        Returns:
            Number of notifications marked as read
        """
        try:
            query = self.db.query(Notification).filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False,
                )
            )

            if category:
                query = query.filter(Notification.category == category)

            notifications = query.all()
            count = 0

            for notification in notifications:
                notification.mark_as_read()
                count += 1

            self.db.commit()

            # Send WebSocket update
            await connection_manager.send_personal_message(
                user_id=user_id,
                message={
                    "type": "notification:mark_all_read",
                    "data": {
                        "category": category.value if category else None,
                        "count": count,
                        "marked_at": datetime.utcnow().isoformat(),
                    },
                },
            )

            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0

    async def archive_notification(self, notification_id: str, user_id: str) -> bool:
        """Archive a notification."""
        try:
            notification = (
                self.db.query(Notification)
                .filter(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
                .first()
            )

            if not notification:
                return False

            notification.archive()
            self.db.commit()

            # Send WebSocket update
            await connection_manager.send_personal_message(
                user_id=user_id,
                message={
                    "type": "notification:archived",
                    "data": {
                        "notification_id": notification_id,
                        "archived_at": notification.archived_at.isoformat(),
                    },
                },
            )

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error archiving notification: {str(e)}")
            return False

    def get_user_settings(self, user_id: str) -> NotificationSettings:
        """Get or create user notification settings."""
        settings = (
            self.db.query(NotificationSettings)
            .filter(NotificationSettings.user_id == user_id)
            .first()
        )

        if not settings:
            # Create default settings
            settings = NotificationSettings(user_id=user_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)

        return settings

    def update_user_settings(
        self, user_id: str, settings_data: dict
    ) -> NotificationSettings:
        """Update user notification settings."""
        settings = self.get_user_settings(user_id)

        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    async def update_user_presence(
        self,
        user_id: str,
        status: UserPresenceStatus,
        page: str = None,
        user_agent: str = None,
        ip_address: str = None,
    ) -> UserPresence:
        """Update user presence status."""
        presence = (
            self.db.query(UserPresence).filter(UserPresence.user_id == user_id).first()
        )

        if not presence:
            presence = UserPresence(user_id=user_id)
            self.db.add(presence)

        # Update presence
        if status == UserPresenceStatus.ONLINE:
            presence.set_online()
        elif status == UserPresenceStatus.AWAY:
            presence.set_away()
        elif status == UserPresenceStatus.OFFLINE:
            presence.set_offline()

        presence.update_activity(page, user_agent, ip_address)

        self.db.commit()
        self.db.refresh(presence)

        # Broadcast presence update
        await connection_manager.send_room_message(
            "global",
            {"type": "user:presence", "data": presence.to_dict()},
            exclude_user=user_id,
        )

        return presence

    async def cleanup_expired_notifications(self) -> int:
        """Clean up expired notifications."""
        try:
            expired = (
                self.db.query(Notification)
                .filter(
                    and_(
                        Notification.expires_at.isnot(None),
                        Notification.expires_at <= datetime.utcnow(),
                    )
                )
                .all()
            )

            count = len(expired)
            for notification in expired:
                self.db.delete(notification)

            self.db.commit()

            if count > 0:
                logger.info(f"Cleaned up {count} expired notifications")

            return count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up expired notifications: {str(e)}")
            return 0


# Convenience functions for common notification types


async def notify_new_tender(
    db: Session, user_id: str, tender_data: dict, created_by: str = None
) -> Notification:
    """Send notification for new tender."""
    service = NotificationService(db)

    return await service.create_notification(
        user_id=user_id,
        title=f"Nova licitação disponível",
        message=f"Nova oportunidade: {tender_data.get('title', 'Sem título')}",
        category=NotificationCategory.LICITACOES,
        priority=NotificationPriority.HIGH
        if tender_data.get("ai_score", 0) >= 80
        else NotificationPriority.MEDIUM,
        related_type="tender",
        related_id=tender_data.get("id"),
        action_url=f"/tenders/{tender_data.get('id')}",
        action_text="Ver Detalhes",
        metadata={
            "ai_score": tender_data.get("ai_score"),
            "estimated_value": tender_data.get("estimated_value"),
        },
        created_by=created_by,
    )


async def notify_task_assigned(
    db: Session, user_id: str, task_data: dict, assigned_by: str = None
) -> Notification:
    """Send notification for task assignment."""
    service = NotificationService(db)

    return await service.create_notification(
        user_id=user_id,
        title="Nova tarefa atribuída",
        message=f"Você recebeu uma nova tarefa: {task_data.get('title', 'Sem título')}",
        category=NotificationCategory.TAREFAS,
        priority=NotificationPriority.HIGH
        if task_data.get("priority") == "urgent"
        else NotificationPriority.MEDIUM,
        related_type="task",
        related_id=task_data.get("id"),
        action_url=f"/tasks/{task_data.get('id')}",
        action_text="Ver Tarefa",
        metadata={
            "due_date": task_data.get("due_date"),
            "priority": task_data.get("priority"),
        },
        created_by=assigned_by,
    )


async def notify_deadline_approaching(
    db: Session, user_id: str, item_data: dict, item_type: str = "tender"
) -> Notification:
    """Send notification for approaching deadline."""
    service = NotificationService(db)

    return await service.create_notification(
        user_id=user_id,
        title="Prazo se aproximando",
        message=f"Atenção: prazo para {item_data.get('title', 'item')} se aproxima em breve",
        category=NotificationCategory.SISTEMA,
        type=NotificationType.WARNING,
        priority=NotificationPriority.HIGH,
        related_type=item_type,
        related_id=item_data.get("id"),
        action_url=f"/{item_type}s/{item_data.get('id')}",
        action_text="Ver Detalhes",
        metadata={
            "deadline": item_data.get("deadline"),
            "days_remaining": item_data.get("days_remaining"),
        },
    )
