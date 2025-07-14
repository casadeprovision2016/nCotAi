"""
WhatsApp Business API Service
Main service for WhatsApp Business API integration.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for integrating with WhatsApp Business API."""

    def __init__(
        self, access_token: str, phone_number_id: str, webhook_verify_token: str
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.webhook_verify_token = webhook_verify_token
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate limiting
        self.rate_limiter = {
            "requests": 0,
            "window_start": datetime.utcnow(),
            "max_requests": 1000,  # Per hour
            "window_size": timedelta(hours=1),
        }

    async def initialize(self):
        """Initialize the service."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "COTAI/1.0 WhatsApp Integration",
        }

        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        logger.info("WhatsApp service initialized")

    async def close(self):
        """Close the service."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if WhatsApp API is available."""
        try:
            url = f"{self.base_url}"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"WhatsApp health check failed: {e}")
            return False

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a text message."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for WhatsApp API")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        return await self._send_message(payload)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        parameters: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send a template message."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for WhatsApp API")

        template_data = {"name": template_name, "language": {"code": language_code}}

        if parameters:
            template_data["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": param} for param in parameters
                    ],
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template_data,
        }

        return await self._send_message(payload)

    async def send_tender_alert(
        self, to: str, tender_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a tender alert notification."""
        message = self._format_tender_alert(tender_data)
        return await self.send_text_message(to, message)

    async def send_deadline_reminder(
        self, to: str, tender_data: Dict[str, Any], days_left: int
    ) -> Dict[str, Any]:
        """Send a deadline reminder."""
        message = self._format_deadline_reminder(tender_data, days_left)
        return await self.send_text_message(to, message)

    async def send_status_update(
        self, to: str, quotation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a quotation status update."""
        message = self._format_status_update(quotation_data)
        return await self.send_text_message(to, message)

    async def send_document(
        self, to: str, document_url: str, filename: str, caption: str = ""
    ) -> Dict[str, Any]:
        """Send a document."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for WhatsApp API")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename,
                "caption": caption,
            },
        }

        return await self._send_message(payload)

    async def send_interactive_message(
        self,
        to: str,
        header: str,
        body: str,
        footer: str,
        buttons: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Send an interactive message with buttons."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for WhatsApp API")

        interactive_buttons = []
        for i, button in enumerate(buttons[:3]):  # WhatsApp allows max 3 buttons
            interactive_buttons.append(
                {
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i}_{button.get('id', i)}",
                        "title": button.get("title", f"Option {i+1}"),
                    },
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "footer": {"text": footer},
                "action": {"buttons": interactive_buttons},
            },
        }

        return await self._send_message(payload)

    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get the status of a sent message."""
        try:
            url = f"https://graph.facebook.com/v18.0/{message_id}"
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error getting message status: {e}")
            return {}

    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark an incoming message as read."""
        try:
            url = f"{self.base_url}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }

            async with self.session.post(url, json=payload) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False

    async def get_business_profile(self) -> Dict[str, Any]:
        """Get WhatsApp Business profile information."""
        try:
            url = f"{self.base_url}/whatsapp_business_profile"
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("data", [{}])[0]
        except Exception as e:
            logger.error(f"Error getting business profile: {e}")
            return {}

    async def update_business_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Update WhatsApp Business profile."""
        try:
            url = f"{self.base_url}/whatsapp_business_profile"
            async with self.session.post(url, json=profile_data) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error updating business profile: {e}")
            return False

    def verify_webhook(self, signature: str, payload: str) -> bool:
        """Verify webhook signature."""
        try:
            # Create expected signature
            app_secret = self.webhook_verify_token.encode("utf-8")
            expected_signature = hmac.new(
                app_secret, payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def _send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message using the WhatsApp API."""
        try:
            url = f"{self.base_url}/messages"

            async with self.session.post(url, json=payload) as response:
                if response.status == 429:
                    raise Exception("Rate limited by WhatsApp API")

                response.raise_for_status()
                data = await response.json()

                logger.info(
                    f"WhatsApp message sent successfully: {data.get('messages', [{}])[0].get('id')}"
                )
                return data

        except Exception as e:
            logger.error(f"WhatsApp message send failed: {e}")
            raise

    def _format_tender_alert(self, tender_data: Dict[str, Any]) -> str:
        """Format tender alert message."""
        title = tender_data.get("title", "Novo Edital")
        agency = tender_data.get("agency", "Órgão não informado")
        value = tender_data.get("estimated_value", 0)
        deadline = tender_data.get("submission_deadline", "")

        value_formatted = f"R$ {value:,.2f}" if value else "Valor não informado"

        try:
            deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            deadline_formatted = deadline_date.strftime("%d/%m/%Y às %H:%M")
        except:
            deadline_formatted = "Prazo não informado"

        message = f"""
🚨 *NOVO EDITAL DISPONÍVEL*

📋 *Título:* {title}

🏛️ *Órgão:* {agency}

💰 *Valor Estimado:* {value_formatted}

⏰ *Prazo:* {deadline_formatted}

🔗 Acesse o sistema COTAI para mais detalhes e iniciar a análise.
        """.strip()

        return message

    def _format_deadline_reminder(
        self, tender_data: Dict[str, Any], days_left: int
    ) -> str:
        """Format deadline reminder message."""
        title = tender_data.get("title", "Edital")

        urgency_emoji = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"

        message = f"""
{urgency_emoji} *LEMBRETE DE PRAZO*

📋 *Edital:* {title}

⏰ *Restam apenas {days_left} dia(s)* para o prazo de submissão!

🚀 Acesse o COTAI para finalizar sua proposta.
        """.strip()

        return message

    def _format_status_update(self, quotation_data: Dict[str, Any]) -> str:
        """Format status update message."""
        title = quotation_data.get("title", "Cotação")
        status = quotation_data.get("status", "unknown")

        status_map = {
            "draft": "📝 Rascunho",
            "in_analysis": "🔍 Em Análise",
            "collecting_quotes": "💰 Coletando Cotações",
            "completed": "✅ Concluída",
            "submitted": "📤 Enviada",
        }

        status_formatted = status_map.get(status, status)

        message = f"""
📊 *ATUALIZAÇÃO DE STATUS*

📋 *Cotação:* {title}

🔄 *Novo Status:* {status_formatted}

🔗 Acesse o COTAI para ver os detalhes.
        """.strip()

        return message

    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.utcnow()

        # Reset window if needed
        if now - self.rate_limiter["window_start"] >= self.rate_limiter["window_size"]:
            self.rate_limiter["requests"] = 0
            self.rate_limiter["window_start"] = now

        # Check if we're under the limit
        if self.rate_limiter["requests"] >= self.rate_limiter["max_requests"]:
            return False

        self.rate_limiter["requests"] += 1
        return True
