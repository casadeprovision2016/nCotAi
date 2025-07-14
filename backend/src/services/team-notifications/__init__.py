"""
Team Notifications Integration Service
Provides integration with Slack, Microsoft Teams and other team collaboration platforms.
"""
from .notification_manager import TeamNotificationManager
from .slack_service import SlackService
from .teams_service import MicrosoftTeamsService
from .workflow_automation import WorkflowAutomationService

__all__ = [
    "SlackService",
    "MicrosoftTeamsService",
    "TeamNotificationManager",
    "WorkflowAutomationService",
]
