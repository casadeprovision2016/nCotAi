"""
WhatsApp Business API Configuration
Configuration settings for WhatsApp Business API integration.
"""
import os
from typing import Any, Dict, Optional

from pydantic import BaseSettings


class WhatsAppConfig(BaseSettings):
    """WhatsApp Business API configuration settings."""

    # WhatsApp Business API credentials
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    WHATSAPP_APP_ID: str = os.getenv("WHATSAPP_APP_ID", "")
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")

    # Webhook configuration
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = os.getenv(
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "cotai_webhook_token_123"
    )
    WHATSAPP_WEBHOOK_URL: str = os.getenv(
        "WHATSAPP_WEBHOOK_URL", "https://api.cotai.com.br/whatsapp/webhook"
    )

    # API URLs
    WHATSAPP_API_BASE_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_API_VERSION: str = "v18.0"

    # Rate limiting
    WHATSAPP_RATE_LIMIT_PER_MINUTE: int = int(
        os.getenv("WHATSAPP_RATE_LIMIT_PER_MINUTE", "60")
    )
    WHATSAPP_RATE_LIMIT_PER_HOUR: int = int(
        os.getenv("WHATSAPP_RATE_LIMIT_PER_HOUR", "1000")
    )
    WHATSAPP_RATE_LIMIT_PER_DAY: int = int(
        os.getenv("WHATSAPP_RATE_LIMIT_PER_DAY", "10000")
    )

    # Message settings
    WHATSAPP_MESSAGE_TIMEOUT: int = int(os.getenv("WHATSAPP_MESSAGE_TIMEOUT", "30"))
    WHATSAPP_MAX_MESSAGE_LENGTH: int = int(
        os.getenv("WHATSAPP_MAX_MESSAGE_LENGTH", "4096")
    )
    WHATSAPP_RETRY_ATTEMPTS: int = int(os.getenv("WHATSAPP_RETRY_ATTEMPTS", "3"))
    WHATSAPP_RETRY_DELAY: int = int(os.getenv("WHATSAPP_RETRY_DELAY", "5"))

    # Template settings
    WHATSAPP_TEMPLATE_LANGUAGE: str = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR")
    WHATSAPP_TEMPLATE_CATEGORY: str = os.getenv(
        "WHATSAPP_TEMPLATE_CATEGORY", "MARKETING"
    )

    # Bot settings
    WHATSAPP_BOT_ENABLED: bool = (
        os.getenv("WHATSAPP_BOT_ENABLED", "true").lower() == "true"
    )
    WHATSAPP_BOT_GREETING_MESSAGE: str = os.getenv(
        "WHATSAPP_BOT_GREETING_MESSAGE",
        "Olá! Sou o assistente virtual do COTAI. Como posso ajudá-lo hoje?",
    )
    WHATSAPP_BOT_HELP_MESSAGE: str = os.getenv(
        "WHATSAPP_BOT_HELP_MESSAGE",
        "Comandos disponíveis:\n- 'status' - Ver status das licitações\n- 'prazos' - Ver prazos próximos\n- 'help' - Ver esta mensagem",
    )

    # Notification settings
    WHATSAPP_NOTIFICATION_ENABLED: bool = (
        os.getenv("WHATSAPP_NOTIFICATION_ENABLED", "true").lower() == "true"
    )
    WHATSAPP_NOTIFICATION_BUSINESS_HOURS_ONLY: bool = (
        os.getenv("WHATSAPP_NOTIFICATION_BUSINESS_HOURS_ONLY", "false").lower()
        == "true"
    )
    WHATSAPP_BUSINESS_HOURS_START: str = os.getenv(
        "WHATSAPP_BUSINESS_HOURS_START", "08:00"
    )
    WHATSAPP_BUSINESS_HOURS_END: str = os.getenv("WHATSAPP_BUSINESS_HOURS_END", "18:00")

    # Security settings
    WHATSAPP_WEBHOOK_SIGNATURE_VALIDATION: bool = (
        os.getenv("WHATSAPP_WEBHOOK_SIGNATURE_VALIDATION", "true").lower() == "true"
    )
    WHATSAPP_ALLOWED_PHONE_NUMBERS: str = os.getenv(
        "WHATSAPP_ALLOWED_PHONE_NUMBERS", ""
    )
    WHATSAPP_BLOCKED_PHONE_NUMBERS: str = os.getenv(
        "WHATSAPP_BLOCKED_PHONE_NUMBERS", ""
    )

    # Logging settings
    WHATSAPP_LOG_LEVEL: str = os.getenv("WHATSAPP_LOG_LEVEL", "INFO")
    WHATSAPP_LOG_MESSAGES: bool = (
        os.getenv("WHATSAPP_LOG_MESSAGES", "true").lower() == "true"
    )
    WHATSAPP_LOG_WEBHOOKS: bool = (
        os.getenv("WHATSAPP_LOG_WEBHOOKS", "true").lower() == "true"
    )

    # Storage settings
    WHATSAPP_MEDIA_STORAGE_PATH: str = os.getenv(
        "WHATSAPP_MEDIA_STORAGE_PATH", "/app/media/whatsapp"
    )
    WHATSAPP_MEDIA_MAX_SIZE_MB: int = int(os.getenv("WHATSAPP_MEDIA_MAX_SIZE_MB", "16"))
    WHATSAPP_MEDIA_ALLOWED_TYPES: str = os.getenv(
        "WHATSAPP_MEDIA_ALLOWED_TYPES",
        "image/jpeg,image/png,application/pdf,text/plain",
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_api_url(self, endpoint: str = "") -> str:
        """Get full API URL for specific endpoint."""
        base_url = f"{self.WHATSAPP_API_BASE_URL}/{self.WHATSAPP_PHONE_NUMBER_ID}"
        if endpoint:
            return f"{base_url}/{endpoint.lstrip('/')}"
        return base_url

    def get_business_api_url(self, endpoint: str = "") -> str:
        """Get business API URL for management operations."""
        base_url = f"{self.WHATSAPP_API_BASE_URL}/{self.WHATSAPP_BUSINESS_ACCOUNT_ID}"
        if endpoint:
            return f"{base_url}/{endpoint.lstrip('/')}"
        return base_url

    def get_headers(self) -> Dict[str, str]:
        """Get standard headers for API requests."""
        return {
            "Authorization": f"Bearer {self.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "COTAI-WhatsApp-Integration/1.0",
        }

    def get_allowed_phone_numbers(self) -> list:
        """Get list of allowed phone numbers."""
        if not self.WHATSAPP_ALLOWED_PHONE_NUMBERS:
            return []
        return [
            phone.strip()
            for phone in self.WHATSAPP_ALLOWED_PHONE_NUMBERS.split(",")
            if phone.strip()
        ]

    def get_blocked_phone_numbers(self) -> list:
        """Get list of blocked phone numbers."""
        if not self.WHATSAPP_BLOCKED_PHONE_NUMBERS:
            return []
        return [
            phone.strip()
            for phone in self.WHATSAPP_BLOCKED_PHONE_NUMBERS.split(",")
            if phone.strip()
        ]

    def get_allowed_media_types(self) -> list:
        """Get list of allowed media types."""
        return [
            media_type.strip()
            for media_type in self.WHATSAPP_MEDIA_ALLOWED_TYPES.split(",")
            if media_type.strip()
        ]

    def is_phone_number_allowed(self, phone_number: str) -> bool:
        """Check if phone number is allowed."""
        allowed = self.get_allowed_phone_numbers()
        blocked = self.get_blocked_phone_numbers()

        # If there's a blocklist and number is in it, deny
        if blocked and phone_number in blocked:
            return False

        # If there's an allowlist, only allow numbers in it
        if allowed:
            return phone_number in allowed

        # If no allowlist and not in blocklist, allow
        return True

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate WhatsApp configuration."""
        errors = []
        warnings = []

        # Required fields
        required_fields = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_BUSINESS_ACCOUNT_ID",
        ]

        for field in required_fields:
            if not getattr(self, field):
                errors.append(f"Missing required field: {field}")

        # Validate phone number ID format
        if (
            self.WHATSAPP_PHONE_NUMBER_ID
            and not self.WHATSAPP_PHONE_NUMBER_ID.isdigit()
        ):
            errors.append("WHATSAPP_PHONE_NUMBER_ID should be numeric")

        # Validate business account ID format
        if (
            self.WHATSAPP_BUSINESS_ACCOUNT_ID
            and not self.WHATSAPP_BUSINESS_ACCOUNT_ID.isdigit()
        ):
            errors.append("WHATSAPP_BUSINESS_ACCOUNT_ID should be numeric")

        # Validate rate limits
        if self.WHATSAPP_RATE_LIMIT_PER_MINUTE <= 0:
            warnings.append("Rate limit per minute should be positive")

        # Validate business hours
        try:
            start_hour = int(self.WHATSAPP_BUSINESS_HOURS_START.split(":")[0])
            end_hour = int(self.WHATSAPP_BUSINESS_HOURS_END.split(":")[0])
            if start_hour >= end_hour:
                warnings.append("Business hours start should be before end time")
        except (ValueError, IndexError):
            warnings.append("Invalid business hours format (should be HH:MM)")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# Global configuration instance
whatsapp_config = WhatsAppConfig()

# Template configurations
WHATSAPP_TEMPLATES = {
    "tender_alert": {
        "name": "tender_alert",
        "language": "pt_BR",
        "category": "MARKETING",
        "components": [
            {"type": "HEADER", "format": "TEXT", "text": "🚨 Nova Licitação Disponível"},
            {
                "type": "BODY",
                "text": "Olá! Encontramos uma nova licitação que pode interessar:\n\n*{{1}}*\n\nPrazo: {{2}}\nValor estimado: {{3}}\nÓrgão: {{4}}\n\nAcesse sua conta para mais detalhes.",
            },
            {"type": "FOOTER", "text": "COTAI - Seu assistente em licitações"},
        ],
    },
    "deadline_reminder": {
        "name": "deadline_reminder",
        "language": "pt_BR",
        "category": "MARKETING",
        "components": [
            {"type": "HEADER", "format": "TEXT", "text": "⏰ Lembrete de Prazo"},
            {
                "type": "BODY",
                "text": "Atenção! O prazo para a licitação está próximo:\n\n*{{1}}*\n\nRestam apenas {{2}} dias até {{3}}\n\nNão perca esta oportunidade!",
            },
            {"type": "FOOTER", "text": "COTAI - Nunca perca um prazo"},
        ],
    },
    "quotation_status": {
        "name": "quotation_status",
        "language": "pt_BR",
        "category": "MARKETING",
        "components": [
            {"type": "HEADER", "format": "TEXT", "text": "📋 Status da Cotação"},
            {
                "type": "BODY",
                "text": "Sua cotação foi atualizada:\n\n*{{1}}*\n\nStatus: {{2}}\nÚltima atualização: {{3}}\n\nVerifique os detalhes em sua conta.",
            },
            {"type": "FOOTER", "text": "COTAI - Controle total das suas cotações"},
        ],
    },
    "welcome_message": {
        "name": "welcome_message",
        "language": "pt_BR",
        "category": "MARKETING",
        "components": [
            {"type": "HEADER", "format": "TEXT", "text": "🎉 Bem-vindo ao COTAI!"},
            {
                "type": "BODY",
                "text": "Olá {{1}}!\n\nSua conta foi ativada com sucesso. Agora você terá:\n\n✅ Alertas de novas licitações\n✅ Lembretes de prazos\n✅ Atualizações de cotações\n✅ Suporte via WhatsApp\n\nVamos começar?",
            },
            {"type": "FOOTER", "text": "COTAI - Simplifique suas licitações"},
        ],
    },
}

# Bot commands configuration
WHATSAPP_BOT_COMMANDS = {
    "help": {
        "description": "Mostra comandos disponíveis",
        "response": "Comandos disponíveis:\n\n🔍 *status* - Ver status das licitações\n⏰ *prazos* - Ver prazos próximos\n📊 *dashboard* - Link para dashboard\n💬 *contato* - Falar com suporte\n❓ *help* - Esta mensagem\n\nDigite qualquer comando para começar!",
    },
    "status": {
        "description": "Mostra status das licitações",
        "response": "📊 *Status das suas licitações:*\n\n🟢 Em andamento: {active_count}\n🟡 Aguardando análise: {pending_count}\n🔴 Próximas ao prazo: {urgent_count}\n\nPara ver detalhes, acesse: {dashboard_url}",
    },
    "prazos": {
        "description": "Mostra prazos próximos",
        "response": "⏰ *Prazos próximos:*\n\n{deadlines_list}\n\nMantenha-se sempre atualizado!",
    },
    "dashboard": {
        "description": "Link para o dashboard",
        "response": "🔗 *Acesse seu dashboard:*\n{dashboard_url}\n\nGerencie todas as suas licitações em um só lugar!",
    },
    "contato": {
        "description": "Informações de contato",
        "response": "📞 *Precisa de ajuda?*\n\nEquipe de suporte:\n• WhatsApp: Este chat\n• Email: suporte@cotai.com.br\n• Telefone: (11) 9999-9999\n\nHorário: Segunda a Sexta, 8h às 18h",
    },
}
