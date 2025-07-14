"""
WhatsApp Message Templates Manager
Manages WhatsApp Business API message templates.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WhatsAppTemplateManager:
    """Manager for WhatsApp message templates."""

    def __init__(self, whatsapp_service):
        self.whatsapp_service = whatsapp_service
        self.templates = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default message templates."""
        self.templates = {
            "tender_alert": {
                "name": "tender_alert",
                "language": "pt_BR",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "HEADER",
                        "format": "TEXT",
                        "text": "🚨 Novo Edital Disponível",
                    },
                    {
                        "type": "BODY",
                        "text": "Um novo edital foi encontrado que pode ser do seu interesse:\n\n📋 *{{1}}*\n🏛️ Órgão: {{2}}\n💰 Valor: {{3}}\n⏰ Prazo: {{4}}\n\nAcesse o COTAI para mais detalhes.",
                    },
                    {"type": "FOOTER", "text": "COTAI - Sistema de Automação"},
                ],
            },
            "deadline_reminder": {
                "name": "deadline_reminder",
                "language": "pt_BR",
                "category": "UTILITY",
                "components": [
                    {"type": "HEADER", "format": "TEXT", "text": "⏰ Lembrete de Prazo"},
                    {
                        "type": "BODY",
                        "text": "Atenção! O prazo para submissão está se aproximando:\n\n📋 *{{1}}*\n⏰ Restam apenas *{{2}} dias*\n\nFinalize sua proposta no COTAI agora!",
                    },
                    {"type": "FOOTER", "text": "COTAI - Sistema de Automação"},
                ],
            },
            "status_update": {
                "name": "status_update",
                "language": "pt_BR",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "HEADER",
                        "format": "TEXT",
                        "text": "📊 Atualização de Status",
                    },
                    {
                        "type": "BODY",
                        "text": "Status da cotação atualizado:\n\n📋 *{{1}}*\n🔄 Novo status: *{{2}}*\n\nVerifique os detalhes no COTAI.",
                    },
                    {"type": "FOOTER", "text": "COTAI - Sistema de Automação"},
                ],
            },
            "welcome_message": {
                "name": "welcome_message",
                "language": "pt_BR",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "HEADER",
                        "format": "TEXT",
                        "text": "👋 Bem-vindo ao COTAI",
                    },
                    {
                        "type": "BODY",
                        "text": "Olá {{1}}!\n\nObrigado por se cadastrar no COTAI. Agora você receberá notificações importantes sobre editais e cotações diretamente no WhatsApp.\n\nDigite *ajuda* para ver os comandos disponíveis.",
                    },
                    {"type": "FOOTER", "text": "COTAI - Sistema de Automação"},
                ],
            },
            "document_ready": {
                "name": "document_ready",
                "language": "pt_BR",
                "category": "UTILITY",
                "components": [
                    {"type": "HEADER", "format": "TEXT", "text": "📄 Documento Pronto"},
                    {
                        "type": "BODY",
                        "text": "Seu documento foi processado e está pronto para download:\n\n📋 *{{1}}*\n📄 Tipo: {{2}}\n\nAcesse o COTAI para fazer o download.",
                    },
                    {"type": "FOOTER", "text": "COTAI - Sistema de Automação"},
                ],
            },
        }

    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new message template."""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.whatsapp_service.phone_number_id}/message_templates"

            async with self.whatsapp_service.session.post(
                url, json=template_data
            ) as response:
                response.raise_for_status()
                result = await response.json()

                # Store template locally
                template_name = template_data.get("name")
                if template_name:
                    self.templates[template_name] = template_data

                logger.info(f"Template '{template_name}' created successfully")
                return result

        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all message templates."""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.whatsapp_service.phone_number_id}/message_templates"

            async with self.whatsapp_service.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("data", [])

        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []

    async def delete_template(self, template_name: str) -> bool:
        """Delete a message template."""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.whatsapp_service.phone_number_id}/message_templates"
            params = {"name": template_name}

            async with self.whatsapp_service.session.delete(
                url, params=params
            ) as response:
                success = response.status == 200

                if success and template_name in self.templates:
                    del self.templates[template_name]
                    logger.info(f"Template '{template_name}' deleted successfully")

                return success

        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False

    async def send_tender_alert_template(
        self, to: str, tender_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send tender alert using template."""
        parameters = [
            tender_data.get("title", "Edital"),
            tender_data.get("agency", "Órgão não informado"),
            self._format_currency(tender_data.get("estimated_value", 0)),
            self._format_deadline(tender_data.get("submission_deadline", "")),
        ]

        return await self.whatsapp_service.send_template_message(
            to=to, template_name="tender_alert", parameters=parameters
        )

    async def send_deadline_reminder_template(
        self, to: str, tender_data: Dict[str, Any], days_left: int
    ) -> Dict[str, Any]:
        """Send deadline reminder using template."""
        parameters = [tender_data.get("title", "Edital"), str(days_left)]

        return await self.whatsapp_service.send_template_message(
            to=to, template_name="deadline_reminder", parameters=parameters
        )

    async def send_status_update_template(
        self, to: str, quotation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send status update using template."""
        status_map = {
            "draft": "📝 Rascunho",
            "in_analysis": "🔍 Em Análise",
            "collecting_quotes": "💰 Coletando Cotações",
            "completed": "✅ Concluída",
            "submitted": "📤 Enviada",
        }

        status = quotation_data.get("status", "unknown")
        status_formatted = status_map.get(status, status)

        parameters = [quotation_data.get("title", "Cotação"), status_formatted]

        return await self.whatsapp_service.send_template_message(
            to=to, template_name="status_update", parameters=parameters
        )

    async def send_welcome_template(self, to: str, user_name: str) -> Dict[str, Any]:
        """Send welcome message using template."""
        parameters = [user_name]

        return await self.whatsapp_service.send_template_message(
            to=to, template_name="welcome_message", parameters=parameters
        )

    async def send_document_ready_template(
        self, to: str, document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send document ready notification using template."""
        parameters = [
            document_data.get("title", "Documento"),
            document_data.get("type", "PDF"),
        ]

        return await self.whatsapp_service.send_template_message(
            to=to, template_name="document_ready", parameters=parameters
        )

    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific template."""
        return self.templates.get(template_name)

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())

    def validate_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate template structure."""
        errors = []

        # Required fields
        if "name" not in template_data:
            errors.append("Template name is required")

        if "language" not in template_data:
            errors.append("Template language is required")

        if "category" not in template_data:
            errors.append("Template category is required")

        if "components" not in template_data:
            errors.append("Template components are required")

        # Validate components
        components = template_data.get("components", [])
        has_body = False

        for component in components:
            if component.get("type") == "BODY":
                has_body = True
                if "text" not in component:
                    errors.append("BODY component must have text")

        if not has_body:
            errors.append("Template must have a BODY component")

        return {"valid": len(errors) == 0, "errors": errors}

    def _format_currency(self, value: float) -> str:
        """Format currency value."""
        if value == 0:
            return "Valor não informado"
        return f"R$ {value:,.2f}"

    def _format_deadline(self, deadline: str) -> str:
        """Format deadline string."""
        try:
            deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            return deadline_date.strftime("%d/%m/%Y às %H:%M")
        except:
            return "Prazo não informado"

    async def setup_default_templates(self) -> Dict[str, Any]:
        """Setup default templates in WhatsApp Business API."""
        results = {}

        for template_name, template_data in self.templates.items():
            try:
                # Check if template already exists
                existing_templates = await self.get_templates()
                template_exists = any(
                    t.get("name") == template_name for t in existing_templates
                )

                if not template_exists:
                    result = await self.create_template(template_data)
                    results[template_name] = {"status": "created", "result": result}
                else:
                    results[template_name] = {"status": "exists"}

            except Exception as e:
                results[template_name] = {"status": "error", "error": str(e)}
                logger.error(f"Error setting up template '{template_name}': {e}")

        return results
