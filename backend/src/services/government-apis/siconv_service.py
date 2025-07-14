"""
SICONV Service
Integration with Brazil's federal transfer system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class SiconvService:
    """Service for integrating with SICONV API."""

    BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
    TRANSFERS_ENDPOINT = "/transferencias"
    AGREEMENTS_ENDPOINT = "/convenios"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key: Optional[str] = None
        self.rate_limiter = {
            "requests": 0,
            "window_start": datetime.utcnow(),
            "max_requests": 100,  # Per hour
            "window_size": timedelta(hours=1),
        }

    async def initialize(self, api_key: Optional[str] = None):
        """Initialize the service."""
        self.api_key = api_key

        headers = {
            "User-Agent": "COTAI/1.0 (Sistema de Automação para Cotações)",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["chave-api-dados"] = self.api_key

        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        logger.info("SICONV service initialized")

    async def close(self):
        """Close the service."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if SICONV service is available."""
        try:
            # Test with a simple query
            params = {"pagina": 1, "tamanhoPagina": 1}
            url = f"{self.BASE_URL}{self.TRANSFERS_ENDPOINT}"

            async with self.session.get(url, params=params) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"SICONV health check failed: {e}")
            return False

    async def search_transfers(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for federal transfers."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for SICONV API")

        params = self._build_transfer_params(filters)

        try:
            url = f"{self.BASE_URL}{self.TRANSFERS_ENDPOINT}"

            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    raise Exception("Rate limited by SICONV API")

                response.raise_for_status()
                data = await response.json()

                return self._process_transfer_results(data)

        except Exception as e:
            logger.error(f"SICONV transfer search failed: {e}")
            raise

    async def search_agreements(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for federal agreements (convênios)."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for SICONV API")

        params = self._build_agreement_params(filters)

        try:
            url = f"{self.BASE_URL}{self.AGREEMENTS_ENDPOINT}"

            async with self.session.get(url, params=params) as response:
                if response.status == 429:
                    raise Exception("Rate limited by SICONV API")

                response.raise_for_status()
                data = await response.json()

                return self._process_agreement_results(data)

        except Exception as e:
            logger.error(f"SICONV agreement search failed: {e}")
            raise

    async def get_transfer_by_id(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get specific transfer details."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for SICONV API")

        try:
            url = f"{self.BASE_URL}{self.TRANSFERS_ENDPOINT}/{transfer_id}"

            async with self.session.get(url) as response:
                if response.status == 404:
                    return None

                if response.status == 429:
                    raise Exception("Rate limited by SICONV API")

                response.raise_for_status()
                data = await response.json()

                return self._process_transfer_details(data)

        except Exception as e:
            logger.error(f"SICONV get transfer details failed: {e}")
            raise

    async def get_municipalities(
        self, state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of municipalities, optionally filtered by state."""
        try:
            # This would typically come from a separate municipalities endpoint
            # For now, return a subset of major Brazilian municipalities
            municipalities = [
                {"code": "3550308", "name": "São Paulo", "state": "SP"},
                {"code": "3304557", "name": "Rio de Janeiro", "state": "RJ"},
                {"code": "3106200", "name": "Belo Horizonte", "state": "MG"},
                {"code": "4314902", "name": "Porto Alegre", "state": "RS"},
                {"code": "4106902", "name": "Curitiba", "state": "PR"},
                {"code": "2304400", "name": "Fortaleza", "state": "CE"},
                {"code": "2927408", "name": "Salvador", "state": "BA"},
                {"code": "5300108", "name": "Brasília", "state": "DF"},
                {"code": "1302603", "name": "Manaus", "state": "AM"},
                {"code": "2611606", "name": "Recife", "state": "PE"},
            ]

            if state:
                municipalities = [
                    m for m in municipalities if m["state"] == state.upper()
                ]

            return municipalities

        except Exception as e:
            logger.error(f"Error getting municipalities: {e}")
            return []

    def _build_transfer_params(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for transfer search."""
        params = {
            "pagina": filters.get("page", 1),
            "tamanhoPagina": filters.get("page_size", 50),
        }

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

        # Location filters
        if "state" in filters:
            params["uf"] = filters["state"]
        if "municipality_code" in filters:
            params["codigoMunicipio"] = filters["municipality_code"]

        # Ministry/organ filter
        if "ministry_code" in filters:
            params["codigoOrgao"] = filters["ministry_code"]

        # Program filter
        if "program_code" in filters:
            params["codigoPrograma"] = filters["program_code"]

        return params

    def _build_agreement_params(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for agreement search."""
        params = {
            "pagina": filters.get("page", 1),
            "tamanhoPagina": filters.get("page_size", 50),
        }

        # Date filters
        if "start_date" in filters:
            params["dataInicioVigencia"] = filters["start_date"]
        if "end_date" in filters:
            params["dataFimVigencia"] = filters["end_date"]

        # Value filters
        if "min_value" in filters:
            params["valorMinimo"] = filters["min_value"]
        if "max_value" in filters:
            params["valorMaximo"] = filters["max_value"]

        # Location filters
        if "state" in filters:
            params["uf"] = filters["state"]
        if "municipality_code" in filters:
            params["codigoMunicipio"] = filters["municipality_code"]

        # Status filter
        if "status" in filters:
            params["situacao"] = filters["status"]

        return params

    def _process_transfer_results(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process and normalize transfer search results."""
        results = []

        for item in data:
            processed = {
                "id": item.get("id"),
                "source": "siconv_transfer",
                "title": f"Transferência - {item.get('programa', {}).get('nome', 'Programa não informado')}",
                "description": item.get("objeto"),
                "ministry": item.get("orgao", {}).get("nome"),
                "ministry_code": item.get("orgao", {}).get("codigo"),
                "program": item.get("programa", {}).get("nome"),
                "program_code": item.get("programa", {}).get("codigo"),
                "value": item.get("valor"),
                "start_date": item.get("dataInicio"),
                "end_date": item.get("dataFim"),
                "beneficiary": item.get("beneficiario", {}).get("nome"),
                "beneficiary_cnpj": item.get("beneficiario", {}).get("cnpj"),
                "location": {
                    "state": item.get("municipio", {}).get("uf"),
                    "municipality": item.get("municipio", {}).get("nome"),
                    "municipality_code": item.get("municipio", {}).get("codigo"),
                },
                "status": item.get("situacao"),
                "type": "transfer",
                "raw_data": item,
            }
            results.append(processed)

        return results

    def _process_agreement_results(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process and normalize agreement search results."""
        results = []

        for item in data:
            processed = {
                "id": item.get("id"),
                "source": "siconv_agreement",
                "title": f"Convênio - {item.get('objeto', 'Objeto não informado')}",
                "description": item.get("objeto"),
                "ministry": item.get("orgaoSuperior", {}).get("nome"),
                "ministry_code": item.get("orgaoSuperior", {}).get("codigo"),
                "value_agreement": item.get("valorConvenio"),
                "value_counterpart": item.get("valorContrapartida"),
                "start_date": item.get("dataInicioVigencia"),
                "end_date": item.get("dataFimVigencia"),
                "signing_date": item.get("dataAssinatura"),
                "beneficiary": item.get("convenente", {}).get("nome"),
                "beneficiary_cnpj": item.get("convenente", {}).get("cnpj"),
                "location": {
                    "state": item.get("municipio", {}).get("uf"),
                    "municipality": item.get("municipio", {}).get("nome"),
                    "municipality_code": item.get("municipio", {}).get("codigo"),
                },
                "status": item.get("situacaoConvenio"),
                "type": "agreement",
                "raw_data": item,
            }
            results.append(processed)

        return results

    def _process_transfer_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process detailed transfer information."""
        return {
            "id": data.get("id"),
            "source": "siconv_transfer",
            "title": f"Transferência - {data.get('programa', {}).get('nome', 'Programa não informado')}",
            "description": data.get("objeto"),
            "ministry": data.get("orgao", {}).get("nome"),
            "ministry_code": data.get("orgao", {}).get("codigo"),
            "program": data.get("programa", {}).get("nome"),
            "program_code": data.get("programa", {}).get("codigo"),
            "action": data.get("acao", {}).get("nome"),
            "action_code": data.get("acao", {}).get("codigo"),
            "value": data.get("valor"),
            "start_date": data.get("dataInicio"),
            "end_date": data.get("dataFim"),
            "beneficiary": data.get("beneficiario", {}).get("nome"),
            "beneficiary_cnpj": data.get("beneficiario", {}).get("cnpj"),
            "beneficiary_type": data.get("beneficiario", {}).get("tipo"),
            "location": {
                "state": data.get("municipio", {}).get("uf"),
                "municipality": data.get("municipio", {}).get("nome"),
                "municipality_code": data.get("municipio", {}).get("codigo"),
            },
            "status": data.get("situacao"),
            "execution_status": data.get("situacaoExecucao"),
            "disbursements": data.get("repasses", []),
            "type": "transfer",
            "raw_data": data,
        }

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
