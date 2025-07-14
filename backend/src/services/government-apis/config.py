"""
Government APIs Configuration
Configuration settings for government API integrations.
"""

import os
from typing import Any, Dict, Optional

from pydantic import BaseSettings


class GovernmentAPIConfig(BaseSettings):
    """Configuration for government API services."""

    # PNCP Configuration
    PNCP_BASE_URL: str = "https://pncp.gov.br/api"
    PNCP_RATE_LIMIT: int = 100  # requests per hour
    PNCP_TIMEOUT: int = 30  # seconds

    # ComprasNet Configuration
    COMPRASNET_BASE_URL: str = "http://comprasnet.gov.br"
    COMPRASNET_RATE_LIMIT: int = 60  # requests per hour
    COMPRASNET_TIMEOUT: int = 45  # seconds

    # Receita Federal Configuration
    RECEITA_FEDERAL_API_URLS: list = [
        "https://www.receitaws.com.br/v1/cnpj/{cnpj}",
        "https://publica.cnpj.ws/cnpj/{cnpj}",
        "https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
    ]
    RECEITA_FEDERAL_RATE_LIMIT: int = 30  # requests per minute
    RECEITA_FEDERAL_TIMEOUT: int = 30  # seconds

    # SICONV Configuration
    SICONV_BASE_URL: str = "https://api.portaldatransparencia.gov.br/api-de-dados"
    SICONV_API_KEY: Optional[str] = None
    SICONV_RATE_LIMIT: int = 100  # requests per hour
    SICONV_TIMEOUT: int = 30  # seconds

    # General Configuration
    HEALTH_CHECK_INTERVAL: int = 300  # seconds (5 minutes)
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 1  # seconds
    CACHE_TTL: int = 3600  # seconds (1 hour)

    # Request Configuration
    USER_AGENT: str = "COTAI/1.0 (Sistema de Automação para Cotações)"
    REQUEST_TIMEOUT: int = 30  # seconds
    MAX_CONCURRENT_REQUESTS: int = 10

    # Sync Configuration
    AUTO_SYNC_ENABLED: bool = False
    SYNC_INTERVAL: int = 3600  # seconds (1 hour)
    SYNC_BATCH_SIZE: int = 100

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_REQUESTS: bool = True
    LOG_RESPONSES: bool = False  # Set to True for debugging (may log sensitive data)

    class Config:
        env_prefix = "GOV_API_"
        case_sensitive = True


# Global configuration instance
config = GovernmentAPIConfig()


def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get configuration for a specific service."""
    configs = {
        "pncp": {
            "base_url": config.PNCP_BASE_URL,
            "rate_limit": config.PNCP_RATE_LIMIT,
            "timeout": config.PNCP_TIMEOUT,
            "endpoints": {
                "search": "/consulta/v1/contratacoes",
                "details": "/consulta/v1/contratacoes/{id}",
                "agencies": "/consulta/v1/orgaos",
            },
        },
        "comprasnet": {
            "base_url": config.COMPRASNET_BASE_URL,
            "rate_limit": config.COMPRASNET_RATE_LIMIT,
            "timeout": config.COMPRASNET_TIMEOUT,
            "endpoints": {
                "search": "/ConsultaLicitacoes/ConsLicitacao_Relacao.asp",
                "details": "/ConsultaLicitacoes/download/download_editais_detalhe.asp",
            },
        },
        "receita_federal": {
            "api_urls": config.RECEITA_FEDERAL_API_URLS,
            "rate_limit": config.RECEITA_FEDERAL_RATE_LIMIT,
            "timeout": config.RECEITA_FEDERAL_TIMEOUT,
        },
        "siconv": {
            "base_url": config.SICONV_BASE_URL,
            "api_key": config.SICONV_API_KEY,
            "rate_limit": config.SICONV_RATE_LIMIT,
            "timeout": config.SICONV_TIMEOUT,
            "endpoints": {"transfers": "/transferencias", "agreements": "/convenios"},
        },
    }

    return configs.get(service_name, {})


def get_headers(service_name: str) -> Dict[str, str]:
    """Get default headers for a service."""
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }

    if service_name == "siconv" and config.SICONV_API_KEY:
        headers["chave-api-dados"] = config.SICONV_API_KEY
    elif service_name == "comprasnet":
        headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            }
        )

    return headers


def validate_config() -> bool:
    """Validate configuration settings."""
    errors = []

    # Check required URLs
    if not config.PNCP_BASE_URL:
        errors.append("PNCP_BASE_URL is required")

    if not config.COMPRASNET_BASE_URL:
        errors.append("COMPRASNET_BASE_URL is required")

    if not config.SICONV_BASE_URL:
        errors.append("SICONV_BASE_URL is required")

    # Check rate limits
    if config.PNCP_RATE_LIMIT <= 0:
        errors.append("PNCP_RATE_LIMIT must be positive")

    if config.COMPRASNET_RATE_LIMIT <= 0:
        errors.append("COMPRASNET_RATE_LIMIT must be positive")

    # Check timeouts
    if config.REQUEST_TIMEOUT <= 0:
        errors.append("REQUEST_TIMEOUT must be positive")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    return True
