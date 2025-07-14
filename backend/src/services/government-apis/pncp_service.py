"""
PNCP (Portal Nacional de Contratações Públicas) Service
Integration with Brazil's national public contracting portal.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class PNCPService:
    """Service for integrating with PNCP API."""

    BASE_URL = "https://pncp.gov.br/api"
    SEARCH_ENDPOINT = "/consulta/v1/contratacoes"
    DETAILS_ENDPOINT = "/consulta/v1/contratacoes/{id}"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = {
            "requests": 0,
            "window_start": datetime.utcnow(),
            "max_requests": 100,  # Per hour
            "window_size": timedelta(hours=1),
        }

    async def initialize(self):
        """Initialize the service."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "COTAI/1.0 (Sistema de Automação para Cotações)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        logger.info("PNCP service initialized")

    async def close(self):
        """Close the service."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if PNCP service is available."""
        try:
            async with self.session.get(f"{self.BASE_URL}/status") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"PNCP health check failed: {e}")
            return False

    async def search_tenders(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for tenders in PNCP."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for PNCP API")

        params = self._build_search_params(query, filters)

        try:
            url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"

            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    raise Exception("Rate limited by PNCP API")

                response.raise_for_status()
                data = await response.json()

                return self._process_search_results(data)

        except Exception as e:
            logger.error(f"PNCP search failed: {e}")
            raise

    async def get_tender_details(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tender."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for PNCP API")

        try:
            url = f"{self.BASE_URL}{self.DETAILS_ENDPOINT.format(id=tender_id)}"

            async with self.session.get(url) as response:
                if response.status == 404:
                    return None

                if response.status == 429:
                    raise Exception("Rate limited by PNCP API")

                response.raise_for_status()
                data = await response.json()

                return self._process_tender_details(data)

        except Exception as e:
            logger.error(f"PNCP get tender details failed: {e}")
            raise

    async def get_agencies(self) -> List[Dict[str, Any]]:
        """Get list of government agencies."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for PNCP API")

        try:
            url = f"{self.BASE_URL}/consulta/v1/orgaos"

            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                return data.get("data", [])

        except Exception as e:
            logger.error(f"PNCP get agencies failed: {e}")
            raise

    async def get_modalities(self) -> List[Dict[str, Any]]:
        """Get list of contracting modalities."""
        try:
            # Static list since PNCP modalities are standardized
            return [
                {
                    "id": 1,
                    "name": "Convite",
                    "description": "Modalidade para valores menores",
                },
                {
                    "id": 2,
                    "name": "Tomada de Preços",
                    "description": "Modalidade para valores médios",
                },
                {
                    "id": 3,
                    "name": "Concorrência",
                    "description": "Modalidade para valores maiores",
                },
                {
                    "id": 4,
                    "name": "Pregão",
                    "description": "Modalidade eletrônica preferencial",
                },
                {"id": 5, "name": "Dispensa", "description": "Dispensa de licitação"},
                {
                    "id": 6,
                    "name": "Inexigibilidade",
                    "description": "Inexigibilidade de licitação",
                },
                {
                    "id": 7,
                    "name": "Registro de Preços",
                    "description": "Sistema de registro de preços",
                },
            ]
        except Exception as e:
            logger.error(f"Error getting modalities: {e}")
            return []

    def _build_search_params(
        self, query: str, filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build search parameters for PNCP API."""
        params = {"q": query, "size": 50, "from": 0}  # Results per page  # Offset

        if filters:
            # Date filters
            if "start_date" in filters:
                params["dataInicio"] = filters["start_date"]
            if "end_date" in filters:
                params["dataFim"] = filters["end_date"]

            # Value filters
            if "min_value" in filters:
                params["valorMinimo"] = filters["min_value"]
            if "max_value" in filters:
                params["valorMaximo"] = filters["max_value"]

            # Agency filter
            if "agency_id" in filters:
                params["orgaoId"] = filters["agency_id"]

            # Modality filter
            if "modality" in filters:
                params["modalidade"] = filters["modality"]

            # Status filter
            if "status" in filters:
                params["situacao"] = filters["status"]

            # Location filter
            if "state" in filters:
                params["uf"] = filters["state"]
            if "city" in filters:
                params["municipio"] = filters["city"]

        return params

    def _process_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process and normalize search results from PNCP."""
        results = []

        items = data.get("data", [])
        for item in items:
            processed = {
                "id": item.get("id"),
                "source": "pncp",
                "title": item.get("objeto"),
                "description": item.get("informacaoComplementar"),
                "agency": item.get("orgaoEntidade", {}).get("razaoSocial"),
                "agency_cnpj": item.get("orgaoEntidade", {}).get("cnpj"),
                "modality": item.get("modalidade"),
                "estimated_value": item.get("valorEstimado"),
                "publication_date": item.get("dataPublicacao"),
                "submission_deadline": item.get("dataLimiteSubmissao"),
                "opening_date": item.get("dataAberturaPropostas"),
                "status": item.get("situacao"),
                "location": {"state": item.get("uf"), "city": item.get("municipio")},
                "process_number": item.get("numeroProcesso"),
                "edital_number": item.get("numeroEdital"),
                "category": self._determine_category(item.get("objeto", "")),
                "url": f"https://pncp.gov.br/app/editais/{item.get('id')}",
                "raw_data": item,
            }
            results.append(processed)

        return results

    def _process_tender_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process detailed tender information from PNCP."""
        return {
            "id": data.get("id"),
            "source": "pncp",
            "title": data.get("objeto"),
            "description": data.get("informacaoComplementar"),
            "agency": data.get("orgaoEntidade", {}).get("razaoSocial"),
            "agency_cnpj": data.get("orgaoEntidade", {}).get("cnpj"),
            "agency_contact": {
                "phone": data.get("telefone"),
                "email": data.get("email"),
                "address": data.get("endereco"),
            },
            "modality": data.get("modalidade"),
            "estimated_value": data.get("valorEstimado"),
            "publication_date": data.get("dataPublicacao"),
            "submission_deadline": data.get("dataLimiteSubmissao"),
            "opening_date": data.get("dataAberturaPropostas"),
            "status": data.get("situacao"),
            "location": {"state": data.get("uf"), "city": data.get("municipio")},
            "process_number": data.get("numeroProcesso"),
            "edital_number": data.get("numeroEdital"),
            "requirements": data.get("exigencias", []),
            "documents": data.get("documentos", []),
            "items": data.get("itens", []),
            "legal_basis": data.get("fundamentoLegal"),
            "category": self._determine_category(data.get("objeto", "")),
            "url": f"https://pncp.gov.br/app/editais/{data.get('id')}",
            "raw_data": data,
        }

    def _determine_category(self, title: str) -> str:
        """Determine tender category based on title keywords."""
        title_lower = title.lower()

        tech_keywords = [
            "software",
            "sistema",
            "tecnologia",
            "informatica",
            "computador",
            "rede",
        ]
        construction_keywords = [
            "obra",
            "construção",
            "reforma",
            "engenharia",
            "edificação",
        ]
        services_keywords = [
            "serviço",
            "consultoria",
            "manutenção",
            "limpeza",
            "vigilância",
        ]
        equipment_keywords = ["equipamento", "máquina", "veículo", "mobiliário"]
        supplies_keywords = ["material", "suprimento", "insumo", "combustível"]

        if any(keyword in title_lower for keyword in tech_keywords):
            return "Tecnologia da Informação"
        elif any(keyword in title_lower for keyword in construction_keywords):
            return "Construção Civil"
        elif any(keyword in title_lower for keyword in services_keywords):
            return "Serviços"
        elif any(keyword in title_lower for keyword in equipment_keywords):
            return "Equipamentos"
        elif any(keyword in title_lower for keyword in supplies_keywords):
            return "Materiais"
        else:
            return "Outros"

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
