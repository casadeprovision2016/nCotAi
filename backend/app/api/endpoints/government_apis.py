"""
Government APIs Endpoints
API endpoints for government data integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...core.auth import get_current_user
from ...models.user import User
from ...services.government_api_service import GovernmentAPIService

router = APIRouter()


class TenderSearchRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class TenderSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int
    sources_used: List[str]
    search_time: float


class CompanyValidationRequest(BaseModel):
    cnpj: str


class CompanyValidationResponse(BaseModel):
    cnpj: str
    is_valid: bool
    company_info: Optional[Dict[str, Any]]


class SiconvSearchRequest(BaseModel):
    filters: Dict[str, Any]


class ServiceHealthResponse(BaseModel):
    services: Dict[str, Dict[str, Any]]
    available_services: List[str]
    last_updated: datetime


@router.post("/tenders/search", response_model=TenderSearchResponse)
async def search_government_tenders(
    request: TenderSearchRequest,
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Search for tenders across government sources."""
    try:
        start_time = datetime.utcnow()

        results = await gov_api_service.search_tenders(
            query=request.query, sources=request.sources, filters=request.filters
        )

        search_time = (datetime.utcnow() - start_time).total_seconds()
        sources_used = gov_api_service.get_available_services()

        return TenderSearchResponse(
            results=results,
            total_count=len(results),
            sources_used=sources_used,
            search_time=search_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/tenders/{tender_id}")
async def get_tender_details(
    tender_id: str,
    source: str = Query(..., description="Data source (pncp, comprasnet)"),
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get detailed information about a specific tender."""
    try:
        result = await gov_api_service.get_tender_details(tender_id, source)

        if not result:
            raise HTTPException(status_code=404, detail="Tender not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get tender details: {str(e)}"
        )


@router.post("/company/validate", response_model=CompanyValidationResponse)
async def validate_company(
    request: CompanyValidationRequest,
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Validate company information using Receita Federal."""
    try:
        company_info = await gov_api_service.validate_company(request.cnpj)

        return CompanyValidationResponse(
            cnpj=request.cnpj,
            is_valid=company_info is not None,
            company_info=company_info,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Company validation failed: {str(e)}"
        )


@router.get("/company/{cnpj}")
async def get_company_info(
    cnpj: str,
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get detailed company information by CNPJ."""
    try:
        result = await gov_api_service.get_company_details(cnpj)

        if not result:
            raise HTTPException(status_code=404, detail="Company not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get company info: {str(e)}"
        )


@router.post("/siconv/search")
async def search_siconv_data(
    request: SiconvSearchRequest,
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Search SICONV transfer data."""
    try:
        results = await gov_api_service.get_siconv_data(request.filters)

        return {
            "results": results,
            "total_count": len(results),
            "filters_applied": request.filters,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SICONV search failed: {str(e)}")


@router.get("/agencies")
async def get_government_agencies(
    source: str = Query("pncp", description="Data source for agencies"),
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get list of government agencies."""
    try:
        results = await gov_api_service.get_agencies(source)
        return {"agencies": results, "source": source}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agencies: {str(e)}")


@router.get("/modalities")
async def get_tender_modalities(
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get list of tender modalities."""
    try:
        results = await gov_api_service.get_modalities()
        return {"modalities": results}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get modalities: {str(e)}"
        )


@router.get("/municipalities")
async def get_municipalities(
    state: Optional[str] = Query(None, description="Filter by state (UF)"),
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get list of municipalities."""
    try:
        results = await gov_api_service.get_municipalities(state)
        return {"municipalities": results, "state_filter": state}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get municipalities: {str(e)}"
        )


@router.get("/health", response_model=ServiceHealthResponse)
async def get_service_health(
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get health status of all government API services."""
    try:
        health_status = gov_api_service.get_service_health()
        available_services = gov_api_service.get_available_services()

        return ServiceHealthResponse(
            services=health_status,
            available_services=available_services,
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get service health: {str(e)}"
        )


@router.post("/sync/tenders")
async def sync_government_tenders(
    sources: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Sync tenders from government sources to local database."""
    try:
        result = await gov_api_service.sync_tenders(sources, filters)

        return {
            "synced_count": result.get("synced_count", 0),
            "updated_count": result.get("updated_count", 0),
            "sources_used": result.get("sources_used", []),
            "sync_time": result.get("sync_time", 0),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tender sync failed: {str(e)}")


@router.get("/statistics")
async def get_government_data_statistics(
    current_user: User = Depends(get_current_user),
    gov_api_service: GovernmentAPIService = Depends(),
):
    """Get statistics about government data integration."""
    try:
        stats = await gov_api_service.get_statistics()

        return {
            "total_tenders_synced": stats.get("total_tenders", 0),
            "last_sync": stats.get("last_sync"),
            "sources_active": stats.get("sources_active", 0),
            "avg_response_time": stats.get("avg_response_time", 0),
            "daily_requests": stats.get("daily_requests", 0),
            "rate_limit_status": stats.get("rate_limits", {}),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )
