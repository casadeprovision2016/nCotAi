"""
WhatsApp Integration Service
Main service for coordinating WhatsApp Business API integrations.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from src.services.whatsapp_api.bot_manager import WhatsAppBotManager
from src.services.whatsapp_api.message_templates import WhatsAppTemplateManager
from src.services.whatsapp_api.webhook_handler import WhatsAppWebhookHandler
from src.services.whatsapp_api.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class WhatsAppIntegrationService:
    """Main service for WhatsApp Business API integration coordination."""

    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
        self.webhook_handler = WhatsAppWebhookHandler()
        self.template_manager = WhatsAppTemplateManager()
        self.bot_manager = WhatsAppBotManager()

        # Service registry
        self.services = {
            "whatsapp": self.whatsapp_service,
            "webhook": self.webhook_handler,
            "templates": self.template_manager,
            "bot": self.bot_manager,
        }

        # Integration status
        self.status = {
            "initialized": True,
            "services_health": {},
            "last_check": datetime.utcnow(),
        }

    async def initialize_services(self) -> Dict[str, Any]:
        """Initialize all WhatsApp integration services."""
        try:
            logger.info("Initializing WhatsApp integration services")

            # Initialize services
            results = {}

            # Initialize WhatsApp service
            whatsapp_result = await self.whatsapp_service.initialize()
            results["whatsapp"] = whatsapp_result

            # Initialize webhook handler
            webhook_result = await self.webhook_handler.initialize()
            results["webhook"] = webhook_result

            # Initialize template manager
            template_result = await self.template_manager.initialize()
            results["templates"] = template_result

            # Initialize bot manager
            bot_result = await self.bot_manager.initialize()
            results["bot"] = bot_result

            # Update service health status
            for service_name, result in results.items():
                self.status["services_health"][service_name] = {
                    "status": "healthy" if result.get("success") else "error",
                    "last_check": datetime.utcnow(),
                    "details": result,
                }

            logger.info("WhatsApp integration services initialized successfully")
            return {
                "success": True,
                "message": "WhatsApp integration services initialized",
                "services": results,
                "status": self.status,
            }

        except Exception as e:
            logger.error(f"Error initializing WhatsApp services: {str(e)}")
            return {"success": False, "error": str(e), "status": self.status}

    async def send_notification(
        self,
        phone_number: str,
        message: str,
        template_name: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Send WhatsApp notification."""
        try:
            if template_name:
                # Send template message
                result = await self.whatsapp_service.send_template_message(
                    phone_number=phone_number,
                    template_name=template_name,
                    variables=variables or {},
                )
            else:
                # Send text message
                result = await self.whatsapp_service.send_text_message(
                    phone_number=phone_number, message=message
                )

            return result

        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_tender_alert(
        self, phone_number: str, tender_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send tender-related alert."""
        try:
            template_name = "tender_alert"
            variables = {
                "tender_title": tender_data.get("title", "Edital"),
                "deadline": tender_data.get("deadline", "Em breve"),
                "value": tender_data.get("estimated_value", "Não informado"),
                "agency": tender_data.get("agency", "Órgão público"),
            }

            result = await self.send_notification(
                phone_number=phone_number,
                message=None,
                template_name=template_name,
                variables=variables,
                priority="high",
            )

            return result

        except Exception as e:
            logger.error(f"Error sending tender alert: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_deadline_reminder(
        self, phone_number: str, tender_data: Dict[str, Any], days_left: int
    ) -> Dict[str, Any]:
        """Send deadline reminder."""
        try:
            template_name = "deadline_reminder"
            variables = {
                "tender_title": tender_data.get("title", "Edital"),
                "days_left": str(days_left),
                "deadline_date": tender_data.get("deadline", "Em breve"),
            }

            result = await self.send_notification(
                phone_number=phone_number,
                message=None,
                template_name=template_name,
                variables=variables,
                priority="high",
            )

            return result

        except Exception as e:
            logger.error(f"Error sending deadline reminder: {str(e)}")
            return {"success": False, "error": str(e)}

    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook from WhatsApp."""
        try:
            result = await self.webhook_handler.process_webhook(webhook_data)

            # If it's a message, let bot manager handle it
            if result.get("type") == "message":
                bot_response = await self.bot_manager.handle_message(
                    result.get("message_data", {})
                )
                result["bot_response"] = bot_response

            return result

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all WhatsApp integration services."""
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
                "health_checks": health_checks,
            }

        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_templates(self) -> Dict[str, Any]:
        """Get available WhatsApp message templates."""
        try:
            templates = await self.template_manager.get_available_templates()

            return {"success": True, "templates": templates}

        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new WhatsApp message template."""
        try:
            result = await self.template_manager.create_template(template_data)

            return result

        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return {"success": False, "error": str(e)}

    async def setup_automation_rules(
        self, rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Setup automation rules for WhatsApp notifications."""
        try:
            results = []

            for rule in rules:
                # Setup rule in bot manager
                rule_result = await self.bot_manager.setup_rule(rule)
                results.append(rule_result)

            return {
                "success": True,
                "message": f"Setup {len(results)} automation rules",
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error setting up automation rules: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_message_history(
        self, phone_number: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Get message history for a phone number."""
        try:
            history = await self.whatsapp_service.get_message_history(
                phone_number=phone_number, limit=limit
            )

            return {"success": True, "history": history}

        except Exception as e:
            logger.error(f"Error getting message history: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cleanup_services(self) -> Dict[str, Any]:
        """Cleanup and shutdown WhatsApp integration services."""
        try:
            logger.info("Cleaning up WhatsApp integration services")

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

            logger.info("WhatsApp integration services cleanup completed")
            return {
                "success": True,
                "message": "Services cleaned up successfully",
                "cleanup_results": cleanup_results,
            }

        except Exception as e:
            logger.error(f"Error cleaning up services: {str(e)}")
            return {"success": False, "error": str(e)}
