"""
ComprasNet Service
Integration with Brazil's federal government procurement system.
"""

import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class ComprasnetService:
    """Service for integrating with ComprasNet system."""

    BASE_URL = "http://comprasnet.gov.br/acesso.asp"
    SEARCH_URL = "http://comprasnet.gov.br/ConsultaLicitacoes/ConsLicitacao_Relacao.asp"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = {
            "requests": 0,
            "window_start": datetime.utcnow(),
            "max_requests": 60,  # Per hour (more conservative)
            "window_size": timedelta(hours=1),
        }

    async def initialize(self):
        """Initialize the service."""
        timeout = aiohttp.ClientTimeout(total=45)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; COTAI/1.0; +http://cotai.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
        logger.info("ComprasNet service initialized")

    async def close(self):
        """Close the service."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if ComprasNet service is available."""
        try:
            async with self.session.get(self.BASE_URL) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"ComprasNet health check failed: {e}")
            return False

    async def search_tenders(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for tenders in ComprasNet."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for ComprasNet")

        params = self._build_search_params(query, filters)

        try:
            async with self.session.post(self.SEARCH_URL, data=params) as response:
                if response.status == 429:
                    raise Exception("Rate limited by ComprasNet")

                response.raise_for_status()
                html_content = await response.text()

                return self._parse_search_results(html_content)

        except Exception as e:
            logger.error(f"ComprasNet search failed: {e}")
            raise

    async def get_tender_details(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tender."""
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded for ComprasNet")

        try:
            # ComprasNet uses different URLs for details
            detail_url = f"http://comprasnet.gov.br/ConsultaLicitacoes/download/download_editais_detalhe.asp?coduasg={tender_id}"

            async with self.session.get(detail_url) as response:
                if response.status == 404:
                    return None

                if response.status == 429:
                    raise Exception("Rate limited by ComprasNet")

                response.raise_for_status()
                html_content = await response.text()

                return self._parse_tender_details(html_content, tender_id)

        except Exception as e:
            logger.error(f"ComprasNet get tender details failed: {e}")
            raise

    async def get_federal_agencies(self) -> List[Dict[str, Any]]:
        """Get list of federal agencies in ComprasNet."""
        try:
            # Predefined list of major federal agencies
            return [
                {"id": "153100", "name": "Ministério da Educação", "acronym": "MEC"},
                {"id": "153101", "name": "Ministério da Saúde", "acronym": "MS"},
                {"id": "153102", "name": "Ministério da Justiça", "acronym": "MJ"},
                {"id": "153103", "name": "Ministério da Defesa", "acronym": "MD"},
                {"id": "153104", "name": "Ministério do Trabalho", "acronym": "MT"},
                {"id": "153105", "name": "Ministério da Fazenda", "acronym": "MF"},
                {
                    "id": "153106",
                    "name": "Ministério do Desenvolvimento",
                    "acronym": "MDIC",
                },
                {
                    "id": "153107",
                    "name": "Ministério da Agricultura",
                    "acronym": "MAPA",
                },
                {
                    "id": "153108",
                    "name": "Ministério do Meio Ambiente",
                    "acronym": "MMA",
                },
                {
                    "id": "153109",
                    "name": "Ministério da Ciência e Tecnologia",
                    "acronym": "MCTI",
                },
            ]
        except Exception as e:
            logger.error(f"Error getting federal agencies: {e}")
            return []

    def _build_search_params(
        self, query: str, filters: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Build search parameters for ComprasNet."""
        params = {
            "txtlicitacao": query,
            "numprp": "",  # Process number
            "dt_publ_ini": "",  # Start publication date
            "dt_publ_fim": "",  # End publication date
            "chkModalidade": "1",  # Include all modalities
            "optTipoLicitacao": "5",  # All types
            "chkConcorrencia": "1",
            "chkTomada": "1",
            "chkConvite": "1",
            "chkPregao": "1",
            "chkOutros": "1",
            "txtEdital": "",
            "txtUasg": "",
            "txtObjeto": query,
            "btnPesquisar": "Pesquisar",
        }

        if filters:
            # Date filters
            if "start_date" in filters:
                params["dt_publ_ini"] = self._format_date(filters["start_date"])
            if "end_date" in filters:
                params["dt_publ_fim"] = self._format_date(filters["end_date"])

            # Agency UASG filter
            if "agency_uasg" in filters:
                params["txtUasg"] = filters["agency_uasg"]

            # Edital number filter
            if "edital_number" in filters:
                params["txtEdital"] = filters["edital_number"]

            # Process number filter
            if "process_number" in filters:
                params["numprp"] = filters["process_number"]

        return params

    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse HTML search results from ComprasNet."""
        results = []

        try:
            # ComprasNet returns HTML tables - would need proper HTML parsing
            # This is a simplified version that would need BeautifulSoup in production
            lines = html_content.split("\n")

            # Look for table rows with tender information
            for i, line in enumerate(lines):
                if (
                    "Pregão" in line
                    or "Concorrência" in line
                    or "Tomada de Preços" in line
                ):
                    try:
                        # Extract basic information from table row
                        # This is simplified - real implementation would parse HTML properly
                        tender_data = self._extract_tender_from_line(
                            line, lines[i : i + 5]
                        )
                        if tender_data:
                            results.append(tender_data)
                    except Exception as e:
                        logger.warning(f"Error parsing tender line: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing ComprasNet results: {e}")

        return results

    def _extract_tender_from_line(
        self, line: str, context_lines: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract tender information from HTML line (simplified)."""
        try:
            # This is a placeholder implementation
            # Real implementation would use BeautifulSoup or similar
            return {
                "id": f"comprasnet_{datetime.utcnow().timestamp()}",
                "source": "comprasnet",
                "title": "Tender title extracted from HTML",
                "description": "Description extracted from HTML",
                "agency": "Agency extracted from HTML",
                "modality": "Pregão",
                "estimated_value": 0,
                "publication_date": datetime.utcnow().isoformat(),
                "submission_deadline": datetime.utcnow().isoformat(),
                "status": "open",
                "category": "Não categorizado",
                "url": "http://comprasnet.gov.br",
                "raw_data": {"html_line": line},
            }
        except Exception:
            return None

    def _parse_tender_details(
        self, html_content: str, tender_id: str
    ) -> Dict[str, Any]:
        """Parse detailed tender information from HTML."""
        # Simplified implementation - would need proper HTML parsing
        return {
            "id": tender_id,
            "source": "comprasnet",
            "title": "Detailed title from ComprasNet",
            "description": "Detailed description from HTML",
            "agency": "Agency from details page",
            "modality": "Pregão",
            "estimated_value": 0,
            "publication_date": datetime.utcnow().isoformat(),
            "submission_deadline": datetime.utcnow().isoformat(),
            "status": "open",
            "location": {"state": "DF", "city": "Brasília"},
            "requirements": [],
            "documents": [],
            "items": [],
            "category": "Não categorizado",
            "url": f"http://comprasnet.gov.br/ConsultaLicitacoes/download/download_editais_detalhe.asp?coduasg={tender_id}",
            "raw_data": {"html_content": html_content[:1000]},  # Truncated
        }

    def _format_date(self, date_str: str) -> str:
        """Format date for ComprasNet (dd/mm/yyyy)."""
        try:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date_obj.strftime("%d/%m/%Y")
        except Exception:
            return date_str

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
