"""
WhatsApp Webhook Handler
Handles incoming WhatsApp webhook events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler:
    """Handler for WhatsApp webhook events."""

    def __init__(self, whatsapp_service):
        self.whatsapp_service = whatsapp_service
        self.message_handlers: Dict[str, Callable] = {}
        self.status_handlers: Dict[str, Callable] = {}
        self.button_handlers: Dict[str, Callable] = {}

        # Register default handlers
        self._register_default_handlers()

    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types."""
        self.message_handlers[message_type] = handler

    def register_status_handler(self, status: str, handler: Callable):
        """Register a handler for specific message statuses."""
        self.status_handlers[status] = handler

    def register_button_handler(self, button_id: str, handler: Callable):
        """Register a handler for interactive button responses."""
        self.button_handlers[button_id] = handler

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook payload."""
        try:
            # Verify webhook structure
            if "entry" not in payload:
                return {"status": "error", "message": "Invalid payload structure"}

            responses = []

            for entry in payload["entry"]:
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        response = await self._handle_message_change(
                            change.get("value", {})
                        )
                        responses.append(response)

            return {"status": "success", "responses": responses}

        except Exception as e:
            logger.error(f"Error handling WhatsApp webhook: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_message_change(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a message change event."""
        responses = []

        # Handle incoming messages
        if "messages" in value:
            for message in value["messages"]:
                response = await self._handle_incoming_message(
                    message, value.get("contacts", [])
                )
                responses.append(response)

        # Handle message status updates
        if "statuses" in value:
            for status in value["statuses"]:
                response = await self._handle_status_update(status)
                responses.append(response)

        return {"message_responses": responses}

    async def _handle_incoming_message(
        self, message: Dict[str, Any], contacts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle an incoming message."""
        try:
            message_id = message.get("id")
            from_number = message.get("from")
            message_type = message.get("type")
            timestamp = message.get("timestamp")

            # Get contact info
            contact_name = None
            for contact in contacts:
                if contact.get("wa_id") == from_number:
                    contact_name = contact.get("profile", {}).get("name")
                    break

            # Mark message as read
            await self.whatsapp_service.mark_message_as_read(message_id)

            # Handle different message types
            if message_type == "text":
                return await self._handle_text_message(
                    message, from_number, contact_name
                )
            elif message_type == "interactive":
                return await self._handle_interactive_message(
                    message, from_number, contact_name
                )
            elif message_type == "document":
                return await self._handle_document_message(
                    message, from_number, contact_name
                )
            elif message_type == "image":
                return await self._handle_image_message(
                    message, from_number, contact_name
                )
            else:
                return await self._handle_unsupported_message(
                    message, from_number, contact_name
                )

        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_text_message(
        self, message: Dict[str, Any], from_number: str, contact_name: str
    ) -> Dict[str, Any]:
        """Handle incoming text message."""
        text_body = message.get("text", {}).get("body", "").lower().strip()

        # Check for registered handlers
        for keyword, handler in self.message_handlers.items():
            if keyword.lower() in text_body:
                try:
                    return await handler(message, from_number, contact_name)
                except Exception as e:
                    logger.error(f"Error in message handler for '{keyword}': {e}")
                    break

        # Default response for unrecognized messages
        return await self._handle_default_message(message, from_number, contact_name)

    async def _handle_interactive_message(
        self, message: Dict[str, Any], from_number: str, contact_name: str
    ) -> Dict[str, Any]:
        """Handle interactive message (button responses)."""
        interactive = message.get("interactive", {})

        if interactive.get("type") == "button_reply":
            button_id = interactive.get("button_reply", {}).get("id")

            # Check for registered button handlers
            for handler_id, handler in self.button_handlers.items():
                if handler_id in button_id:
                    try:
                        return await handler(message, from_number, contact_name)
                    except Exception as e:
                        logger.error(f"Error in button handler for '{handler_id}': {e}")
                        break

        return {"status": "handled", "type": "interactive"}

    async def _handle_document_message(
        self, message: Dict[str, Any], from_number: str, contact_name: str
    ) -> Dict[str, Any]:
        """Handle incoming document."""
        document = message.get("document", {})
        filename = document.get("filename", "document")

        # Log document receipt
        logger.info(f"Received document '{filename}' from {from_number}")

        # Send acknowledgment
        response_text = f"📄 Documento '{filename}' recebido com sucesso! Nossa equipe irá analisá-lo em breve."
        await self.whatsapp_service.send_text_message(from_number, response_text)

        return {"status": "handled", "type": "document", "filename": filename}

    async def _handle_image_message(
        self, message: Dict[str, Any], from_number: str, contact_name: str
    ) -> Dict[str, Any]:
        """Handle incoming image."""
        # Log image receipt
        logger.info(f"Received image from {from_number}")

        # Send acknowledgment
        response_text = "📷 Imagem recebida! Obrigado por compartilhar."
        await self.whatsapp_service.send_text_message(from_number, response_text)

        return {"status": "handled", "type": "image"}

    async def _handle_unsupported_message(
        self, message: Dict[str, Any], from_number: str, contact_name: str
    ) -> Dict[str, Any]:
        """Handle unsupported message types."""
        message_type = message.get("type", "unknown")

        response_text = f"Desculpe, o tipo de mensagem '{message_type}' não é suportado no momento. Por favor, use texto ou documentos."
        await self.whatsapp_service.send_text_message(from_number, response_text)

        return {
            "status": "handled",
            "type": "unsupported",
            "original_type": message_type,
        }

    async def _handle_status_update(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message status update."""
        message_id = status.get("id")
        status_type = status.get("status")
        timestamp = status.get("timestamp")
        recipient_id = status.get("recipient_id")

        # Check for registered status handlers
        for status_name, handler in self.status_handlers.items():
            if status_name == status_type:
                try:
                    return await handler(status)
                except Exception as e:
                    logger.error(f"Error in status handler for '{status_name}': {e}")
                    break

        # Log status update
        logger.info(f"Message {message_id} status: {status_type}")

        return {"status": "logged", "type": "status", "message_status": status_type}

    def _register_default_handlers(self):
        """Register default message handlers."""

        # Help command
        async def help_handler(message, from_number, contact_name):
            help_text = """
🤖 *COTAI - Assistente WhatsApp*

Comandos disponíveis:
• *status* - Ver status das cotações
• *editais* - Listar editais ativos
• *prazo* - Ver prazos próximos
• *ajuda* - Esta mensagem

📞 Para suporte personalizado, entre em contato com nossa equipe.
            """.strip()

            await self.whatsapp_service.send_text_message(from_number, help_text)
            return {"status": "handled", "type": "help"}

        # Status command
        async def status_handler(message, from_number, contact_name):
            # This would typically query the database for user's quotations
            status_text = """
📊 *STATUS DAS COTAÇÕES*

📝 Em análise: 3 editais
💰 Coletando preços: 2 editais
✅ Finalizadas: 5 editais

🔗 Acesse o sistema para detalhes completos.
            """.strip()

            await self.whatsapp_service.send_text_message(from_number, status_text)
            return {"status": "handled", "type": "status"}

        # Deadline command
        async def deadline_handler(message, from_number, contact_name):
            deadline_text = """
⏰ *PRAZOS PRÓXIMOS*

🔴 Urgente (1 dia): 1 edital
🟡 Em breve (3 dias): 2 editais
🟢 Próximos (7 dias): 4 editais

⚡ Acesse o COTAI para priorizar suas ações!
            """.strip()

            await self.whatsapp_service.send_text_message(from_number, deadline_text)
            return {"status": "handled", "type": "deadline"}

        # Default message handler
        async def default_handler(message, from_number, contact_name):
            default_text = """
👋 Olá! Sou o assistente COTAI.

Digite *ajuda* para ver os comandos disponíveis ou entre em contato com nossa equipe para suporte personalizado.
            """.strip()

            await self.whatsapp_service.send_text_message(from_number, default_text)
            return {"status": "handled", "type": "default"}

        # Register handlers
        self.message_handlers.update(
            {
                "ajuda": help_handler,
                "help": help_handler,
                "status": status_handler,
                "prazo": deadline_handler,
                "deadline": deadline_handler,
                "editais": status_handler,  # Reuse status handler for now
            }
        )

        # Default handler for unrecognized messages
        self._handle_default_message = default_handler

        # Status handlers
        async def delivered_handler(status):
            logger.info(f"Message {status.get('id')} delivered")
            return {"status": "logged", "type": "delivered"}

        async def read_handler(status):
            logger.info(f"Message {status.get('id')} read")
            return {"status": "logged", "type": "read"}

        async def failed_handler(status):
            logger.warning(
                f"Message {status.get('id')} failed: {status.get('errors', [])}"
            )
            return {"status": "logged", "type": "failed"}

        self.status_handlers.update(
            {
                "delivered": delivered_handler,
                "read": read_handler,
                "failed": failed_handler,
            }
        )
