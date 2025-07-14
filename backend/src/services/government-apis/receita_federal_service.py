"""
Receita Federal Service
Integration with Brazil's federal revenue service for company validation.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class ReceitaFederalService:
    """Service for integrating with Receita Federal APIs."""

    # Using public API services for CNPJ consultation
    CNPJ_API_URLS = [
        "https://www.receitaws.com.br/v1/cnpj/{cnpj}",
        "https://publica.cnpj.ws/cnpj/{cnpj}",
        "https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
    ]

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = {
            "requests": 0,
            "window_start": datetime.utcnow(),
            "max_requests": 30,  # Conservative limit
            "window_size": timedelta(minutes=1),
        }

    async def initialize(self):
        """Initialize the service."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "COTAI/1.0 (Sistema de Automação para Cotações)",
                "Accept": "application/json",
            },
        )
        logger.info("Receita Federal service initialized")

    async def close(self):
        """Close the service."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if Receita Federal service is available."""
        try:
            # Test with a known valid CNPJ (Receita Federal itself)
            test_cnpj = "00394460000187"
            result = await self.get_company_info(test_cnpj)
            return result is not None
        except Exception as e:
            logger.error(f"Receita Federal health check failed: {e}")
            return False

    async def get_company_info(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Get company information by CNPJ."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for Receita Federal API")

        # Clean and validate CNPJ
        cnpj_clean = self._clean_cnpj(cnpj)
        if not self._validate_cnpj(cnpj_clean):
            return None

        # Try multiple API services in order
        for api_url in self.CNPJ_API_URLS:
            try:
                result = await self._query_cnpj_api(api_url, cnpj_clean)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"CNPJ API {api_url} failed: {e}")
                continue

        return None

    async def validate_cnpj(self, cnpj: str) -> bool:
        """Validate if CNPJ exists and is active."""
        company_info = await self.get_company_info(cnpj)
        if not company_info:
            return False

        # Check if company is active
        status = company_info.get("status", "").lower()
        situation = company_info.get("situacao", "").lower()

        active_statuses = ["ok", "ativa", "ativo", "active"]
        return any(
            active_status in status or active_status in situation
            for active_status in active_statuses
        )

    async def get_company_address(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Get company address information."""
        company_info = await self.get_company_info(cnpj)
        if not company_info:
            return None

        return {
            "street": company_info.get("logradouro"),
            "number": company_info.get("numero"),
            "complement": company_info.get("complemento"),
            "neighborhood": company_info.get("bairro"),
            "city": company_info.get("municipio"),
            "state": company_info.get("uf"),
            "zip_code": company_info.get("cep"),
            "full_address": self._format_full_address(company_info),
        }

    async def get_company_activities(self, cnpj: str) -> List[Dict[str, Any]]:
        """Get company's economic activities (CNAE)."""
        company_info = await self.get_company_info(cnpj)
        if not company_info:
            return []

        activities = []

        # Primary activity
        primary = company_info.get("atividade_principal", [])
        if primary:
            for activity in primary:
                activities.append(
                    {
                        "code": activity.get("code"),
                        "description": activity.get("text"),
                        "type": "primary",
                    }
                )

        # Secondary activities
        secondary = company_info.get("atividades_secundarias", [])
        for activity in secondary:
            activities.append(
                {
                    "code": activity.get("code"),
                    "description": activity.get("text"),
                    "type": "secondary",
                }
            )

        return activities

    async def _query_cnpj_api(
        self, api_url: str, cnpj: str
    ) -> Optional[Dict[str, Any]]:
        """Query a specific CNPJ API."""
        url = api_url.format(cnpj=cnpj)

        try:
            async with self.session.get(url) as response:
                if response.status == 429:
                    raise Exception("Rate limited")

                if response.status != 200:
                    return None

                data = await response.json()

                # Normalize response format
                return self._normalize_cnpj_response(data, api_url)

        except Exception as e:
            logger.error(f"Error querying CNPJ API {url}: {e}")
            raise

    def _normalize_cnpj_response(
        self, data: Dict[str, Any], api_url: str
    ) -> Dict[str, Any]:
        """Normalize response format from different CNPJ APIs."""
        normalized = {
            "cnpj": data.get("cnpj"),
            "company_name": None,
            "trade_name": None,
            "status": None,
            "situacao": None,
            "opening_date": None,
            "legal_nature": None,
            "share_capital": None,
            "logradouro": None,
            "numero": None,
            "complemento": None,
            "bairro": None,
            "municipio": None,
            "uf": None,
            "cep": None,
            "phone": None,
            "email": None,
            "atividade_principal": [],
            "atividades_secundarias": [],
            "partners": [],
            "source_api": api_url,
            "raw_data": data,
        }

        # ReceitaWS format
        if "nome" in data:
            normalized.update(
                {
                    "company_name": data.get("nome"),
                    "trade_name": data.get("fantasia"),
                    "status": data.get("status"),
                    "situacao": data.get("situacao"),
                    "opening_date": data.get("abertura"),
                    "legal_nature": data.get("natureza_juridica"),
                    "share_capital": data.get("capital_social"),
                    "logradouro": data.get("logradouro"),
                    "numero": data.get("numero"),
                    "complemento": data.get("complemento"),
                    "bairro": data.get("bairro"),
                    "municipio": data.get("municipio"),
                    "uf": data.get("uf"),
                    "cep": data.get("cep"),
                    "phone": data.get("telefone"),
                    "email": data.get("email"),
                    "atividade_principal": data.get("atividade_principal", []),
                    "atividades_secundarias": data.get("atividades_secundarias", []),
                    "partners": data.get("qsa", []),
                }
            )

        # BrasilAPI format
        elif "razao_social" in data:
            normalized.update(
                {
                    "company_name": data.get("razao_social"),
                    "trade_name": data.get("nome_fantasia"),
                    "status": "ativa"
                    if data.get("situacao_cadastral") == "02"
                    else "inativa",
                    "situacao": data.get("descricao_situacao_cadastral"),
                    "opening_date": data.get("data_inicio_atividade"),
                    "legal_nature": data.get("natureza_juridica", {}).get("descricao"),
                    "share_capital": data.get("capital_social"),
                    "logradouro": data.get("logradouro"),
                    "numero": data.get("numero"),
                    "complemento": data.get("complemento"),
                    "bairro": data.get("bairro"),
                    "municipio": data.get("municipio", {}).get("descricao"),
                    "uf": data.get("uf"),
                    "cep": data.get("cep"),
                    "phone": f"{data.get('ddd_telefone_1', '')}{data.get('telefone_1', '')}",
                    "email": data.get("correio_eletronico"),
                }
            )

            # Convert CNAE activities
            if data.get("cnae_fiscal_principal"):
                normalized["atividade_principal"] = [
                    {
                        "code": data["cnae_fiscal_principal"]["codigo"],
                        "text": data["cnae_fiscal_principal"]["descricao"],
                    }
                ]

            if data.get("cnae_fiscal_secundaria"):
                normalized["atividades_secundarias"] = [
                    {"code": cnae["codigo"], "text": cnae["descricao"]}
                    for cnae in data["cnae_fiscal_secundaria"]
                ]

            if data.get("qsa"):
                normalized["partners"] = [
                    {
                        "nome": partner.get("nome_socio"),
                        "qualificacao": partner.get("qualificacao_socio", {}).get(
                            "descricao"
                        ),
                    }
                    for partner in data["qsa"]
                ]

        return normalized

    def _clean_cnpj(self, cnpj: str) -> str:
        """Clean CNPJ string removing non-numeric characters."""
        return re.sub(r"[^0-9]", "", cnpj)

    def _validate_cnpj(self, cnpj: str) -> bool:
        """Validate CNPJ format and check digit."""
        if len(cnpj) != 14:
            return False

        # Check if all digits are the same
        if cnpj == cnpj[0] * 14:
            return False

        # Validate check digits
        def calculate_digit(cnpj_partial, weights):
            total = sum(
                int(digit) * weight for digit, weight in zip(cnpj_partial, weights)
            )
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        # First check digit
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        digit1 = calculate_digit(cnpj[:12], weights1)

        # Second check digit
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        digit2 = calculate_digit(cnpj[:13], weights2)

        return cnpj[12:14] == f"{digit1}{digit2}"

    def _format_full_address(self, company_info: Dict[str, Any]) -> str:
        """Format complete address string."""
        parts = []

        if company_info.get("logradouro"):
            street_part = company_info["logradouro"]
            if company_info.get("numero"):
                street_part += f", {company_info['numero']}"
            if company_info.get("complemento"):
                street_part += f", {company_info['complemento']}"
            parts.append(street_part)

        if company_info.get("bairro"):
            parts.append(company_info["bairro"])

        if company_info.get("municipio"):
            city_part = company_info["municipio"]
            if company_info.get("uf"):
                city_part += f"/{company_info['uf']}"
            parts.append(city_part)

        if company_info.get("cep"):
            parts.append(f"CEP: {company_info['cep']}")

        return " - ".join(parts)

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
