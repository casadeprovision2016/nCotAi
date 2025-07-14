"""
Notification models for real-time notification system
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class NotificationCategory(str, enum.Enum):
    """Notification categories for grouping and filtering."""

    LICITACOES = "licitacoes"  # Tenders/bids
    TAREFAS = "tarefas"  # Tasks
    SISTEMA = "sistema"  # System notifications
    MENSAGENS = "mensagens"  # Messages/chat


class NotificationType(str, enum.Enum):
    """Notification types for styling and behavior."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationPriority(str, enum.Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class UserPresenceStatus(str, enum.Enum):
    """User presence status for real-time features."""

    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"
    DO_NOT_DISTURB = "do_not_disturb"


class Notification(Base):
    """Notification model for real-time notifications."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic notification data
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(SQLEnum(NotificationCategory), nullable=False)
    type = Column(
        SQLEnum(NotificationType), default=NotificationType.INFO, nullable=False
    )
    priority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )

    # User targeting
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Related entity (optional)
    related_type = Column(
        String(50), nullable=True
    )  # 'tender', 'task', 'message', etc.
    related_id = Column(String(100), nullable=True)  # ID of related entity

    # Status tracking
    is_read = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Action data (for interactive notifications)
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)
    action_data = Column(JSON, nullable=True)  # Additional action parameters

    # Delivery tracking
    sent_via_websocket = Column(Boolean, default=False, nullable=False)
    sent_via_email = Column(Boolean, default=False, nullable=False)
    sent_via_sms = Column(Boolean, default=False, nullable=False)
    websocket_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    sms_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Expiry (for temporary notifications)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    creator = relationship("User", foreign_keys=[created_by])

    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def archive(self):
        """Archive notification."""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert notification to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "title": self.title,
            "message": self.message,
            "category": self.category.value,
            "type": self.type.value,
            "priority": self.priority.value,
            "user_id": str(self.user_id),
            "related_type": self.related_type,
            "related_id": self.related_id,
            "is_read": self.is_read,
            "is_archived": self.is_archived,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "action_url": self.action_url,
            "action_text": self.action_text,
            "action_data": self.action_data,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_expired": self.is_expired,
        }


class NotificationSettings(Base):
    """User notification preferences and settings."""

    __tablename__ = "notification_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Category preferences
    licitacoes_enabled = Column(Boolean, default=True, nullable=False)
    tarefas_enabled = Column(Boolean, default=True, nullable=False)
    sistema_enabled = Column(Boolean, default=True, nullable=False)
    mensagens_enabled = Column(Boolean, default=True, nullable=False)

    # Channel preferences
    websocket_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    browser_notifications = Column(Boolean, default=True, nullable=False)

    # Do not disturb settings
    dnd_enabled = Column(Boolean, default=False, nullable=False)
    dnd_start_time = Column(String(5), nullable=True)  # Format: "22:00"
    dnd_end_time = Column(String(5), nullable=True)  # Format: "08:00"
    dnd_weekends = Column(Boolean, default=False, nullable=False)

    # Sound preferences
    sound_enabled = Column(Boolean, default=True, nullable=False)
    sound_theme = Column(String(50), default="default", nullable=False)
    sound_volume = Column(Integer, default=50, nullable=False)  # 0-100

    # Priority filtering
    min_priority_websocket = Column(
        SQLEnum(NotificationPriority), default=NotificationPriority.LOW, nullable=False
    )
    min_priority_email = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )
    min_priority_sms = Column(
        SQLEnum(NotificationPriority), default=NotificationPriority.HIGH, nullable=False
    )

    # Digest settings
    daily_digest_enabled = Column(Boolean, default=True, nullable=False)
    daily_digest_time = Column(String(5), default="08:00", nullable=False)
    weekly_digest_enabled = Column(Boolean, default=False, nullable=False)
    weekly_digest_day = Column(Integer, default=1, nullable=False)  # 1=Monday, 7=Sunday

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="notification_settings")

    def is_category_enabled(self, category: NotificationCategory) -> bool:
        """Check if a notification category is enabled."""
        category_mapping = {
            NotificationCategory.LICITACOES: self.licitacoes_enabled,
            NotificationCategory.TAREFAS: self.tarefas_enabled,
            NotificationCategory.SISTEMA: self.sistema_enabled,
            NotificationCategory.MENSAGENS: self.mensagens_enabled,
        }
        return category_mapping.get(category, True)

    def is_in_dnd_period(self) -> bool:
        """Check if current time is in do-not-disturb period."""
        if not self.dnd_enabled or not self.dnd_start_time or not self.dnd_end_time:
            return False

        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")

        # Check weekend DND
        if self.dnd_weekends and now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True

        # Check time range
        if self.dnd_start_time <= self.dnd_end_time:
            # Same day range (e.g., 09:00 to 17:00)
            return self.dnd_start_time <= current_time <= self.dnd_end_time
        else:
            # Cross-midnight range (e.g., 22:00 to 08:00)
            return (
                current_time >= self.dnd_start_time or current_time <= self.dnd_end_time
            )

    def should_send_via_channel(
        self, priority: NotificationPriority, channel: str
    ) -> bool:
        """Check if notification should be sent via specific channel based on priority."""
        priority_levels = {
            NotificationPriority.LOW: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.HIGH: 3,
            NotificationPriority.URGENT: 4,
        }

        current_level = priority_levels[priority]

        if channel == "websocket":
            min_level = priority_levels[self.min_priority_websocket]
        elif channel == "email":
            min_level = priority_levels[self.min_priority_email]
        elif channel == "sms":
            min_level = priority_levels[self.min_priority_sms]
        else:
            return False

        return current_level >= min_level


class UserPresence(Base):
    """User presence tracking for real-time features."""

    __tablename__ = "user_presence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Presence data
    status = Column(
        SQLEnum(UserPresenceStatus), default=UserPresenceStatus.OFFLINE, nullable=False
    )
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    # Connection info
    active_connections = Column(Integer, default=0, nullable=False)
    current_page = Column(String(200), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Status message (optional)
    status_message = Column(String(100), nullable=True)

    # Auto-away settings
    auto_away_minutes = Column(Integer, default=15, nullable=False)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="presence")

    @property
    def is_online(self) -> bool:
        """Check if user is currently online."""
        return self.status == UserPresenceStatus.ONLINE and self.active_connections > 0

    @property
    def is_away(self) -> bool:
        """Check if user is away."""
        return self.status == UserPresenceStatus.AWAY

    @property
    def time_since_last_activity(self) -> int:
        """Get minutes since last activity."""
        if not self.last_activity_at:
            return 9999
        delta = datetime.utcnow() - self.last_activity_at.replace(tzinfo=None)
        return int(delta.total_seconds() / 60)

    def should_auto_away(self) -> bool:
        """Check if user should be automatically set to away."""
        return (
            self.status == UserPresenceStatus.ONLINE
            and self.time_since_last_activity >= self.auto_away_minutes
        )

    def update_activity(
        self, page: str = None, user_agent: str = None, ip_address: str = None
    ):
        """Update user activity timestamp and metadata."""
        self.last_activity_at = datetime.utcnow()
        if page:
            self.current_page = page
        if user_agent:
            self.user_agent = user_agent
        if ip_address:
            self.ip_address = ip_address

    def set_online(self):
        """Set user status to online."""
        self.status = UserPresenceStatus.ONLINE
        self.last_seen_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()

    def set_away(self):
        """Set user status to away."""
        self.status = UserPresenceStatus.AWAY
        self.last_seen_at = datetime.utcnow()

    def set_offline(self):
        """Set user status to offline."""
        self.status = UserPresenceStatus.OFFLINE
        self.last_seen_at = datetime.utcnow()
        self.active_connections = 0
        self.current_page = None

    def to_dict(self) -> dict:
        """Convert presence to dictionary for JSON serialization."""
        return {
            "user_id": str(self.user_id),
            "status": self.status.value,
            "last_seen_at": self.last_seen_at.isoformat()
            if self.last_seen_at
            else None,
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "active_connections": self.active_connections,
            "current_page": self.current_page,
            "status_message": self.status_message,
            "is_online": self.is_online,
            "is_away": self.is_away,
            "time_since_last_activity": self.time_since_last_activity,
        }


class NotificationTemplate(Base):
    """Templates for common notification types."""

    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template identification
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(NotificationCategory), nullable=False)
    type = Column(
        SQLEnum(NotificationType), default=NotificationType.INFO, nullable=False
    )
    priority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )

    # Template content (with placeholders)
    title_template = Column(String(255), nullable=False)
    message_template = Column(Text, nullable=False)

    # Default action
    action_url_template = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)

    # Template settings
    is_active = Column(Boolean, default=True, nullable=False)
    auto_expire_hours = Column(Integer, nullable=True)  # Auto-expire after N hours

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = relationship("User")

    def render(self, context: dict) -> dict:
        """Render template with provided context."""
        title = self.title_template
        message = self.message_template
        action_url = self.action_url_template

        # Simple template rendering (replace {key} with values)
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
            if action_url:
                action_url = action_url.replace(placeholder, str(value))

        return {
            "title": title,
            "message": message,
            "action_url": action_url,
            "action_text": self.action_text,
            "category": self.category,
            "type": self.type,
            "priority": self.priority,
            "expires_at": (
                datetime.utcnow() + timedelta(hours=self.auto_expire_hours)
                if self.auto_expire_hours
                else None
            ),
        }
