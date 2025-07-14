"""
Government API Service
Main service for coordinating government API integrations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

# Temporarily commenting out while government API modules are being implemented
# from src.services.government_apis.government_api_manager import GovernmentAPIManager
from ..db.dependencies import get_db
from ..models.tender import Tender
from ..services.tender_service import TenderService

logger = logging.getLogger(__name__)


class GovernmentAPIService:
    """Main service for government API integrations."""

    def __init__(self):
        # TODO: Initialize GovernmentAPIManager when modules are implemented
        # self.api_manager = GovernmentAPIManager()
        self.api_manager = None
        self.tender_service = TenderService()
        self._initialized = False

    async def initialize(self):
        """Initialize the service."""
        if not self._initialized:
            await self.api_manager.initialize()
            self._initialized = True
            logger.info("Government API service initialized")

    async def shutdown(self):
        """Shutdown the service."""
        if self._initialized:
            await self.api_manager.shutdown()
            self._initialized = False
            logger.info("Government API service shutdown")

    async def search_tenders(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for tenders across government sources."""
        await self._ensure_initialized()

        results = await self.api_manager.search_tenders(query, sources, filters)

        # Enrich results with relevance scoring
        for result in results:
            result["relevance_score"] = self._calculate_relevance_score(result, query)
            result["retrieved_at"] = datetime.utcnow().isoformat()

        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return results

    async def get_tender_details(
        self, tender_id: str, source: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tender."""
        await self._ensure_initialized()

        result = await self.api_manager.get_tender_details(tender_id, source)

        if result:
            result["retrieved_at"] = datetime.utcnow().isoformat()
            result["relevance_score"] = self._calculate_relevance_score(result, "")

        return result

    async def validate_company(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Validate company information."""
        await self._ensure_initialized()

        return await self.api_manager.validate_company(cnpj)

    async def get_company_details(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Get detailed company information."""
        await self._ensure_initialized()

        company_info = await self.api_manager.validate_company(cnpj)

        if company_info:
            # Add additional processing
            company_info["activities"] = await self._get_company_activities(cnpj)
            company_info["address"] = await self._get_company_address(cnpj)
            company_info["retrieved_at"] = datetime.utcnow().isoformat()

        return company_info

    async def get_siconv_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get SICONV transfer data."""
        await self._ensure_initialized()

        return await self.api_manager.get_siconv_data(filters)

    async def get_agencies(self, source: str = "pncp") -> List[Dict[str, Any]]:
        """Get list of government agencies."""
        await self._ensure_initialized()

        if source == "pncp" and "pncp" in self.api_manager.services:
            return await self.api_manager.services["pncp"].get_agencies()
        elif source == "comprasnet" and "comprasnet" in self.api_manager.services:
            return await self.api_manager.services["comprasnet"].get_federal_agencies()
        else:
            return []

    async def get_modalities(self) -> List[Dict[str, Any]]:
        """Get list of tender modalities."""
        await self._ensure_initialized()

        if "pncp" in self.api_manager.services:
            return await self.api_manager.services["pncp"].get_modalities()
        else:
            return []

    async def get_municipalities(
        self, state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of municipalities."""
        await self._ensure_initialized()

        if "siconv" in self.api_manager.services:
            return await self.api_manager.services["siconv"].get_municipalities(state)
        else:
            return []

    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        if not self._initialized:
            return {}

        health_status = self.api_manager.get_service_health()

        # Convert APIHealth objects to dictionaries
        formatted_health = {}
        for service_name, health in health_status.items():
            formatted_health[service_name] = {
                "service_name": health.service_name,
                "status": health.status.value,
                "last_check": health.last_check.isoformat(),
                "response_time": health.response_time,
                "error_message": health.error_message,
                "rate_limit_reset": health.rate_limit_reset.isoformat()
                if health.rate_limit_reset
                else None,
            }

        return formatted_health

    def get_available_services(self) -> List[str]:
        """Get list of currently available services."""
        if not self._initialized:
            return []

        return self.api_manager.get_available_services()

    async def sync_tenders(
        self,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sync tenders from government sources to local database."""
        await self._ensure_initialized()

        start_time = datetime.utcnow()
        synced_count = 0
        updated_count = 0

        # Default search query for sync
        search_query = filters.get("query", "licitação pregão concorrência")

        try:
            # Search for tenders
            results = await self.api_manager.search_tenders(
                search_query, sources, filters
            )

            # Sync each tender to database
            for tender_data in results:
                try:
                    # Convert government API format to our tender format
                    local_tender = await self._convert_to_local_tender(tender_data)

                    # Check if tender already exists
                    db = next(get_db())
                    existing = await self.tender_service.get_by_external_id(
                        tender_data["id"], tender_data["source"], db
                    )

                    if existing:
                        # Update existing tender
                        await self.tender_service.update(existing.id, local_tender, db)
                        updated_count += 1
                    else:
                        # Create new tender
                        await self.tender_service.create(local_tender, db)
                        synced_count += 1

                except Exception as e:
                    logger.error(f"Error syncing tender {tender_data.get('id')}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error during tender sync: {e}")
            raise

        sync_time = (datetime.utcnow() - start_time).total_seconds()
        sources_used = self.get_available_services()

        return {
            "synced_count": synced_count,
            "updated_count": updated_count,
            "sources_used": sources_used,
            "sync_time": sync_time,
        }

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about government data integration."""
        # This would typically query database for statistics
        # For now, return mock statistics

        return {
            "total_tenders": 1250,
            "last_sync": datetime.utcnow().isoformat(),
            "sources_active": len(self.get_available_services()),
            "avg_response_time": 1.2,
            "daily_requests": 450,
            "rate_limits": {
                "pncp": {"remaining": 85, "reset_time": "2024-01-01T15:00:00Z"},
                "comprasnet": {"remaining": 42, "reset_time": "2024-01-01T14:30:00Z"},
                "receita_federal": {
                    "remaining": 28,
                    "reset_time": "2024-01-01T14:45:00Z",
                },
            },
        }

    async def _ensure_initialized(self):
        """Ensure the service is initialized."""
        if not self._initialized:
            await self.initialize()

    async def _get_company_activities(self, cnpj: str) -> List[Dict[str, Any]]:
        """Get company activities from Receita Federal."""
        try:
            if "receita_federal" in self.api_manager.services:
                service = self.api_manager.services["receita_federal"]
                return await service.get_company_activities(cnpj)
        except Exception as e:
            logger.error(f"Error getting company activities: {e}")

        return []

    async def _get_company_address(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Get company address from Receita Federal."""
        try:
            if "receita_federal" in self.api_manager.services:
                service = self.api_manager.services["receita_federal"]
                return await service.get_company_address(cnpj)
        except Exception as e:
            logger.error(f"Error getting company address: {e}")

        return None

    def _calculate_relevance_score(
        self, tender_data: Dict[str, Any], query: str
    ) -> float:
        """Calculate relevance score for a tender."""
        score = 0.0

        # Base score
        score += 50.0

        # Title relevance
        title = tender_data.get("title", "").lower()
        if query and query.lower() in title:
            score += 20.0

        # Description relevance
        description = tender_data.get("description", "").lower()
        if query and query.lower() in description:
            score += 15.0

        # Value score (higher values get more points)
        value = tender_data.get("estimated_value", 0)
        if value > 1000000:  # Above 1M
            score += 10.0
        elif value > 100000:  # Above 100K
            score += 5.0

        # Deadline urgency (closer deadlines get more points)
        deadline = tender_data.get("submission_deadline")
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                days_until = (deadline_date - datetime.utcnow()).days
                if days_until <= 7:
                    score += 15.0
                elif days_until <= 30:
                    score += 10.0
                elif days_until <= 60:
                    score += 5.0
            except Exception:
                pass

        # Status bonus
        status = tender_data.get("status", "").lower()
        if status in ["open", "aberto", "publicado"]:
            score += 10.0

        # Source reliability
        source = tender_data.get("source", "")
        if source == "pncp":
            score += 5.0  # PNCP is more reliable
        elif source == "comprasnet":
            score += 3.0

        return min(score, 100.0)  # Cap at 100

    async def _convert_to_local_tender(
        self, gov_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert government API data to local tender format."""
        return {
            "external_id": gov_data["id"],
            "source": gov_data["source"],
            "title": gov_data.get("title", ""),
            "description": gov_data.get("description", ""),
            "agency": gov_data.get("agency", ""),
            "category": gov_data.get("category", ""),
            "estimated_value": gov_data.get("estimated_value", 0),
            "submission_deadline": gov_data.get("submission_deadline"),
            "publication_date": gov_data.get("publication_date"),
            "opening_date": gov_data.get("opening_date"),
            "status": self._map_status(gov_data.get("status", "")),
            "location": gov_data.get("location", {}),
            "modality": gov_data.get("modality", ""),
            "process_number": gov_data.get("process_number", ""),
            "edital_number": gov_data.get("edital_number", ""),
            "url": gov_data.get("url", ""),
            "relevance_score": gov_data.get("relevance_score", 0),
            "raw_data": gov_data.get("raw_data", {}),
            "last_updated": datetime.utcnow(),
        }

    def _map_status(self, gov_status: str) -> str:
        """Map government API status to local status."""
        status_map = {
            "open": "open",
            "aberto": "open",
            "publicado": "open",
            "closed": "closed",
            "encerrado": "closed",
            "cancelado": "cancelled",
            "cancelled": "cancelled",
            "suspended": "suspended",
            "suspenso": "suspended",
        }

        return status_map.get(gov_status.lower(), "unknown")
