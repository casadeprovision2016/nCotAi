"""
PNCP Integration Service - Portal Nacional de Contratações Públicas
Handles API integration with proper CORS handling via backend proxy
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tender import Tender as TenderModel
from app.models.tender import TenderModalityType, TenderStatus, TenderType
from app.models.user import User
from app.services.tender_service import TenderService

logger = logging.getLogger(__name__)


class PNCPService:
    """
    Service for integrating with PNCP API
    Note: PNCP APIs have strict CORS policies, so all requests must go through backend
    """

    def __init__(self):
        self.base_url = "https://pncp.gov.br/api/consulta"
        self.timeout = 30.0
        self.max_retries = 3
        self.rate_limit_delay = 1.0  # Seconds between requests

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any] = None, retries: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request to PNCP API with proper error handling and rate limiting.
        Note: This bypasses CORS by executing on backend.
        """
        url = f"{self.base_url}{endpoint}"

        # Add rate limiting to respect PNCP API limits
        await asyncio.sleep(self.rate_limit_delay)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "accept": "*/*",
                    "User-Agent": "COTAI-System/1.0 (Compliance Tool)",
                }

                logger.info(f"Making PNCP API request to: {url}")
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 204:
                    return {"data": [], "totalRegistros": 0}
                elif response.status_code == 429:  # Rate limit
                    if retries < self.max_retries:
                        wait_time = (retries + 1) * 5  # Exponential backoff
                        logger.warning(
                            f"Rate limited. Waiting {wait_time}s before retry..."
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(endpoint, params, retries + 1)
                    else:
                        raise HTTPException(
                            status_code=429, detail="PNCP API rate limit exceeded"
                        )
                else:
                    logger.error(
                        f"PNCP API error: {response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"PNCP API error: {response.text}",
                    )

        except httpx.TimeoutException:
            if retries < self.max_retries:
                logger.warning(
                    f"Request timeout. Retrying... ({retries + 1}/{self.max_retries})"
                )
                await asyncio.sleep(2**retries)  # Exponential backoff
                return await self._make_request(endpoint, params, retries + 1)
            else:
                raise HTTPException(status_code=504, detail="PNCP API timeout")
        except Exception as e:
            logger.error(f"Error making PNCP API request: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"PNCP integration error: {str(e)}"
            )

    def _map_pncp_modality_to_local(self, pncp_modality_id: int) -> TenderModalityType:
        """Map PNCP modality codes to local enum values."""
        modality_mapping = {
            1: TenderModalityType.LEILAO,  # Leilão - Eletrônico
            2: TenderModalityType.DIALOGO_COMPETITIVO,  # Diálogo Competitivo
            3: TenderModalityType.CONCURSO,  # Concurso
            4: TenderModalityType.CONCORRENCIA,  # Concorrência - Eletrônica
            5: TenderModalityType.CONCORRENCIA,  # Concorrência - Presencial
            6: TenderModalityType.PREGAO_ELETRONICO,  # Pregão - Eletrônico
            7: TenderModalityType.PREGAO_PRESENCIAL,  # Pregão - Presencial
            8: TenderModalityType.PREGAO_ELETRONICO,  # Dispensa de Licitação (mapped to pregao)
            9: TenderModalityType.PREGAO_ELETRONICO,  # Inexigibilidade (mapped to pregao)
            10: TenderModalityType.CONCURSO,  # Manifestação de Interesse
            11: TenderModalityType.CONCURSO,  # Pré-qualificação
            12: TenderModalityType.CONCURSO,  # Credenciamento
            13: TenderModalityType.LEILAO,  # Leilão - Presencial
        }
        return modality_mapping.get(
            pncp_modality_id, TenderModalityType.PREGAO_ELETRONICO
        )

    def _map_pncp_status_to_local(self, pncp_status_id: int) -> TenderStatus:
        """Map PNCP status codes to local enum values."""
        status_mapping = {
            1: TenderStatus.PUBLISHED,  # Divulgada no PNCP
            2: TenderStatus.CANCELLED,  # Revogada
            3: TenderStatus.CANCELLED,  # Anulada
            4: TenderStatus.SUSPENDED,  # Suspensa
        }
        return status_mapping.get(pncp_status_id, TenderStatus.PUBLISHED)

    async def get_contractions_by_publication_date(
        self,
        start_date: datetime,
        end_date: datetime,
        modality_code: int = None,
        uf: str = None,
        cnpj: str = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        6.3. Serviço Consultar Contratações por Data de Publicação

        Args:
            start_date: Data inicial (AAAAMMDD)
            end_date: Data final (AAAAMMDD)
            modality_code: Código da modalidade (optional)
            uf: Sigla da UF (optional)
            cnpj: CNPJ do órgão (optional)
            page: Número da página
            page_size: Tamanho da página (max 500)
        """
        params = {
            "dataInicial": start_date.strftime("%Y%m%d"),
            "dataFinal": end_date.strftime("%Y%m%d"),
            "pagina": page,
            "tamanhoPagina": min(page_size, 500),
        }

        if modality_code:
            params["codigoModalidadeContratacao"] = modality_code
        if uf:
            params["uf"] = uf
        if cnpj:
            params["cnpj"] = cnpj

        return await self._make_request("/v1/contratacoes/publicacao", params)

    async def get_open_contractions(
        self,
        end_date: datetime,
        modality_code: int,
        uf: str = None,
        cnpj: str = None,
        page: int = 1,
        page_size: int = 500,
    ) -> Dict[str, Any]:
        """
        6.4. Serviço Consultar Contratações com Período de Recebimento de Propostas em Aberto

        Args:
            end_date: Data final para consulta
            modality_code: Código da modalidade (obrigatório)
            uf: Sigla da UF (optional)
            cnpj: CNPJ do órgão (optional)
            page: Número da página
            page_size: Tamanho da página (max 500)
        """
        params = {
            "dataFinal": end_date.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modality_code,
            "pagina": page,
            "tamanhoPagina": min(page_size, 500),
        }

        if uf:
            params["uf"] = uf
        if cnpj:
            params["cnpj"] = cnpj

        return await self._make_request("/v1/contratacoes/proposta", params)

    async def sync_recent_tenders(
        self, db: Session, days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Synchronize recent tenders from PNCP to local database.
        This method handles the CORS limitation by executing on backend.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        tender_service = TenderService(db)
        created_count = 0
        updated_count = 0
        errors = []

        try:
            # Get data for main modalities
            modalities_to_sync = [6, 7]  # Pregão Eletrônico e Presencial

            for modality_code in modalities_to_sync:
                logger.info(f"Syncing tenders for modality {modality_code}")

                page = 1
                while True:
                    try:
                        # Get published tenders
                        response = await self.get_contractions_by_publication_date(
                            start_date=start_date,
                            end_date=end_date,
                            modality_code=modality_code,
                            page=page,
                            page_size=100,
                        )

                        if not response.get("data"):
                            break

                        for tender_data in response["data"]:
                            try:
                                # Check if tender already exists
                                pncp_id = tender_data.get("numeroControlePNCP")
                                existing_tender = (
                                    db.query(TenderModel)
                                    .filter(TenderModel.notice_number == pncp_id)
                                    .first()
                                )

                                if existing_tender:
                                    # Update existing tender
                                    self._update_tender_from_pncp(
                                        existing_tender, tender_data
                                    )
                                    db.commit()
                                    updated_count += 1
                                else:
                                    # Create new tender
                                    new_tender = self._create_tender_from_pncp(
                                        tender_data
                                    )
                                    db.add(new_tender)
                                    db.commit()
                                    created_count += 1

                            except Exception as e:
                                error_msg = f"Error processing tender {tender_data.get('numeroControlePNCP', 'unknown')}: {str(e)}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                continue

                        # Check if there are more pages
                        if page >= response.get("totalPaginas", 1):
                            break
                        page += 1

                        # Rate limiting between pages
                        await asyncio.sleep(1)

                    except Exception as e:
                        error_msg = f"Error fetching page {page} for modality {modality_code}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        break

        except Exception as e:
            error_msg = f"Error in sync_recent_tenders: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        return {
            "created_count": created_count,
            "updated_count": updated_count,
            "errors": errors,
            "sync_date": datetime.now().isoformat(),
        }

    def _create_tender_from_pncp(self, pncp_data: Dict[str, Any]) -> TenderModel:
        """Create a new tender from PNCP data."""
        # Extract basic information
        title = pncp_data.get("objetoCompra", "")[:255]  # Limit to 255 chars
        description = pncp_data.get("informacaoComplementar", "")
        notice_number = pncp_data.get("numeroControlePNCP", "")
        process_number = pncp_data.get("processo", "")

        # Map modality
        modality_id = pncp_data.get("modalidadeId", 6)
        modality = self._map_pncp_modality_to_local(modality_id)

        # Map status
        status_id = pncp_data.get("situacaoCompraId", 1)
        status = self._map_pncp_status_to_local(status_id)

        # Extract dates
        published_date = None
        submission_deadline = None
        opening_date = None

        if pncp_data.get("dataPublicacaoPncp"):
            published_date = datetime.fromisoformat(
                pncp_data["dataPublicacaoPncp"].replace("Z", "+00:00")
            )

        if pncp_data.get("dataEncerramentoProposta"):
            submission_deadline = datetime.fromisoformat(
                pncp_data["dataEncerramentoProposta"].replace("Z", "+00:00")
            )

        if pncp_data.get("dataAberturaProposta"):
            opening_date = datetime.fromisoformat(
                pncp_data["dataAberturaProposta"].replace("Z", "+00:00")
            )

        # Extract value
        estimated_value = pncp_data.get("valorTotalEstimado", 0)
        if estimated_value:
            estimated_value = float(estimated_value)

        # Extract government entity info
        gov_entity_name = ""
        if pncp_data.get("orgaoEntidade"):
            gov_entity_name = pncp_data["orgaoEntidade"].get("razaosocial", "")

        # Create tender object
        tender = TenderModel(
            title=title,
            description=description,
            notice_number=notice_number,
            process_number=process_number,
            modality=modality,
            status=status,
            type=TenderType.MIXED,  # Default to mixed
            estimated_value=estimated_value,
            published_date=published_date,
            submission_deadline=submission_deadline,
            opening_date=opening_date,
            location=pncp_data.get("unidadeOrgao", {}).get("municipioNome", ""),
            object_description=title,
            additional_info={
                "pncp_data": pncp_data,
                "government_entity_name": gov_entity_name,
                "source": "PNCP_API",
                "sync_date": datetime.now().isoformat(),
            },
            is_monitored=False,
            is_favorite=False,
        )

        return tender

    def _update_tender_from_pncp(
        self, tender: TenderModel, pncp_data: Dict[str, Any]
    ) -> None:
        """Update existing tender with PNCP data."""
        # Update status
        status_id = pncp_data.get("situacaoCompraId", 1)
        tender.status = self._map_pncp_status_to_local(status_id)

        # Update value if it has changed
        estimated_value = pncp_data.get("valorTotalEstimado", 0)
        if estimated_value:
            tender.estimated_value = float(estimated_value)

        # Update additional info with latest data
        if not tender.additional_info:
            tender.additional_info = {}

        tender.additional_info.update(
            {"pncp_data": pncp_data, "last_sync_date": datetime.now().isoformat()}
        )

        tender.updated_at = datetime.now()

    async def get_available_modalities(self) -> List[Dict[str, Any]]:
        """Get list of available modalities from PNCP API documentation."""
        return [
            {"codigo": 1, "nome": "Leilão - Eletrônico"},
            {"codigo": 2, "nome": "Diálogo Competitivo"},
            {"codigo": 3, "nome": "Concurso"},
            {"codigo": 4, "nome": "Concorrência - Eletrônica"},
            {"codigo": 5, "nome": "Concorrência - Presencial"},
            {"codigo": 6, "nome": "Pregão - Eletrônico"},
            {"codigo": 7, "nome": "Pregão - Presencial"},
            {"codigo": 8, "nome": "Dispensa de Licitação"},
            {"codigo": 9, "nome": "Inexigibilidade"},
            {"codigo": 10, "nome": "Manifestação de Interesse"},
            {"codigo": 11, "nome": "Pré-qualificação"},
            {"codigo": 12, "nome": "Credenciamento"},
            {"codigo": 13, "nome": "Leilão - Presencial"},
        ]

    async def health_check(self) -> Dict[str, Any]:
        """Check PNCP API health and connectivity."""
        try:
            # Try a simple request to check connectivity
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            response = await self.get_contractions_by_publication_date(
                start_date=start_date,
                end_date=end_date,
                modality_code=6,  # Pregão Eletrônico
                page=1,
                page_size=1,
            )

            return {
                "status": "healthy",
                "api_responsive": True,
                "last_check": datetime.now().isoformat(),
                "sample_response": bool(response),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "api_responsive": False,
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }
