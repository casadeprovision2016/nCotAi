"""
Government API Manager
Central manager for all government API integrations.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .comprasnet_service import ComprasnetService
from .pncp_service import PNCPService
from .receita_federal_service import ReceitaFederalService
from .siconv_service import SiconvService

logger = logging.getLogger(__name__)


class APIStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class APIHealth:
    service_name: str
    status: APIStatus
    last_check: datetime
    response_time: Optional[float]
    error_message: Optional[str]
    rate_limit_reset: Optional[datetime]


class GovernmentAPIManager:
    """Manages all government API integrations with health monitoring and rate limiting."""

    def __init__(self):
        self.services = {
            "pncp": PNCPService(),
            "comprasnet": ComprasnetService(),
            "receita_federal": ReceitaFederalService(),
            "siconv": SiconvService(),
        }
        self.health_status: Dict[str, APIHealth] = {}
        self._monitoring_task = None

    async def initialize(self):
        """Initialize all services and start health monitoring."""
        for name, service in self.services.items():
            try:
                await service.initialize()
                self.health_status[name] = APIHealth(
                    service_name=name,
                    status=APIStatus.ACTIVE,
                    last_check=datetime.utcnow(),
                    response_time=None,
                    error_message=None,
                    rate_limit_reset=None,
                )
            except Exception as e:
                logger.error(f"Failed to initialize {name} service: {e}")
                self.health_status[name] = APIHealth(
                    service_name=name,
                    status=APIStatus.ERROR,
                    last_check=datetime.utcnow(),
                    response_time=None,
                    error_message=str(e),
                    rate_limit_reset=None,
                )

        # Start health monitoring
        self._monitoring_task = asyncio.create_task(self._health_monitor())

    async def shutdown(self):
        """Shutdown all services and stop monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()

        for service in self.services.values():
            try:
                await service.close()
            except Exception as e:
                logger.error(f"Error closing service: {e}")

    async def search_tenders(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for tenders across all available government sources."""
        if sources is None:
            sources = ["pncp", "comprasnet"]

        results = []
        tasks = []

        for source in sources:
            if source in self.services and self._is_service_available(source):
                service = self.services[source]
                if hasattr(service, "search_tenders"):
                    tasks.append(self._safe_search(service, query, filters, source))

        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(search_results):
                source = sources[i] if i < len(sources) else "unknown"
                if isinstance(result, Exception):
                    logger.error(f"Search failed for {source}: {result}")
                    await self._update_service_health(
                        source, APIStatus.ERROR, str(result)
                    )
                elif isinstance(result, list):
                    results.extend(result)

        return results

    async def get_tender_details(
        self, tender_id: str, source: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tender."""
        if source not in self.services or not self._is_service_available(source):
            return None

        service = self.services[source]
        if not hasattr(service, "get_tender_details"):
            return None

        try:
            start_time = datetime.utcnow()
            result = await service.get_tender_details(tender_id)
            response_time = (datetime.utcnow() - start_time).total_seconds()

            await self._update_service_health(
                source, APIStatus.ACTIVE, response_time=response_time
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get tender details from {source}: {e}")
            await self._update_service_health(source, APIStatus.ERROR, str(e))
            return None

    async def validate_company(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Validate company information using Receita Federal."""
        if not self._is_service_available("receita_federal"):
            return None

        try:
            service = self.services["receita_federal"]
            result = await service.get_company_info(cnpj)
            await self._update_service_health("receita_federal", APIStatus.ACTIVE)
            return result

        except Exception as e:
            logger.error(f"Failed to validate company: {e}")
            await self._update_service_health(
                "receita_federal", APIStatus.ERROR, str(e)
            )
            return None

    async def get_siconv_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get SICONV transfer data."""
        if not self._is_service_available("siconv"):
            return []

        try:
            service = self.services["siconv"]
            result = await service.search_transfers(filters)
            await self._update_service_health("siconv", APIStatus.ACTIVE)
            return result

        except Exception as e:
            logger.error(f"Failed to get SICONV data: {e}")
            await self._update_service_health("siconv", APIStatus.ERROR, str(e))
            return []

    def get_service_health(self) -> Dict[str, APIHealth]:
        """Get health status of all services."""
        return self.health_status.copy()

    def get_available_services(self) -> List[str]:
        """Get list of currently available services."""
        return [
            name
            for name, health in self.health_status.items()
            if health.status == APIStatus.ACTIVE
        ]

    async def _safe_search(
        self, service, query: str, filters: Optional[Dict[str, Any]], source: str
    ) -> List[Dict[str, Any]]:
        """Safely execute search with error handling."""
        try:
            start_time = datetime.utcnow()
            result = await service.search_tenders(query, filters)
            response_time = (datetime.utcnow() - start_time).total_seconds()

            await self._update_service_health(
                source, APIStatus.ACTIVE, response_time=response_time
            )
            return result

        except Exception as e:
            logger.error(f"Search failed for {source}: {e}")
            await self._update_service_health(source, APIStatus.ERROR, str(e))
            return []

    def _is_service_available(self, service_name: str) -> bool:
        """Check if a service is currently available."""
        health = self.health_status.get(service_name)
        if not health:
            return False

        if health.status == APIStatus.RATE_LIMITED:
            if health.rate_limit_reset and datetime.utcnow() > health.rate_limit_reset:
                # Rate limit has expired, mark as active
                health.status = APIStatus.ACTIVE
                health.rate_limit_reset = None
                return True
            return False

        return health.status == APIStatus.ACTIVE

    async def _update_service_health(
        self,
        service_name: str,
        status: APIStatus,
        error_message: Optional[str] = None,
        response_time: Optional[float] = None,
    ):
        """Update health status for a service."""
        if service_name in self.health_status:
            health = self.health_status[service_name]
            health.status = status
            health.last_check = datetime.utcnow()
            health.error_message = error_message

            if response_time is not None:
                health.response_time = response_time

    async def _health_monitor(self):
        """Background task to monitor service health."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                for name, service in self.services.items():
                    if hasattr(service, "health_check"):
                        try:
                            start_time = datetime.utcnow()
                            await service.health_check()
                            response_time = (
                                datetime.utcnow() - start_time
                            ).total_seconds()

                            await self._update_service_health(
                                name, APIStatus.ACTIVE, response_time=response_time
                            )

                        except Exception as e:
                            await self._update_service_health(
                                name, APIStatus.ERROR, str(e)
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
