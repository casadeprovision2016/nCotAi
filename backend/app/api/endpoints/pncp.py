"""
PNCP Integration endpoints
All PNCP API calls are proxied through backend to handle CORS restrictions
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.core.auth import RoleChecker
from app.models.user import User
from app.services.pncp_service import PNCPService

router = APIRouter()


@router.get("/health")
async def pncp_health_check(
    current_user: User = Depends(get_current_user),
):
    """Check PNCP API connectivity and health."""
    pncp_service = PNCPService()
    return await pncp_service.health_check()


@router.get("/modalities")
async def get_pncp_modalities(
    current_user: User = Depends(get_current_user),
):
    """Get available PNCP modalities."""
    pncp_service = PNCPService()
    return await pncp_service.get_available_modalities()


@router.get("/contractions/published")
async def get_published_contractions(
    start_date: str = Query(..., description="Data inicial no formato AAAAMMDD"),
    end_date: str = Query(..., description="Data final no formato AAAAMMDD"),
    modality_code: Optional[int] = Query(None, description="Código da modalidade"),
    uf: Optional[str] = Query(None, max_length=2, description="Sigla da UF"),
    cnpj: Optional[str] = Query(None, description="CNPJ do órgão"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(50, ge=1, le=500, description="Tamanho da página"),
    current_user: User = Depends(get_current_user),
):
    """
    Proxy para API PNCP - Consultar Contratações por Data de Publicação.
    Este endpoint contorna as restrições CORS fazendo a chamada pelo backend.
    """
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")

        # Validate date range
        if start_dt > end_dt:
            raise HTTPException(
                status_code=400, detail="Data inicial deve ser anterior à data final"
            )

        # Limit to 90 days to prevent overload
        if (end_dt - start_dt).days > 90:
            raise HTTPException(
                status_code=400, detail="Período máximo permitido é de 90 dias"
            )

        pncp_service = PNCPService()
        return await pncp_service.get_contractions_by_publication_date(
            start_date=start_dt,
            end_date=end_dt,
            modality_code=modality_code,
            uf=uf,
            cnpj=cnpj,
            page=page,
            page_size=page_size,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Formato de data inválido. Use AAAAMMDD: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar PNCP: {str(e)}")


@router.get("/contractions/open")
async def get_open_contractions(
    end_date: str = Query(..., description="Data final no formato AAAAMMDD"),
    modality_code: int = Query(..., description="Código da modalidade (obrigatório)"),
    uf: Optional[str] = Query(None, max_length=2, description="Sigla da UF"),
    cnpj: Optional[str] = Query(None, description="CNPJ do órgão"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(100, ge=1, le=500, description="Tamanho da página"),
    current_user: User = Depends(get_current_user),
):
    """
    Proxy para API PNCP - Consultar Contratações com Propostas em Aberto.
    Este endpoint contorna as restrições CORS fazendo a chamada pelo backend.
    """
    try:
        # Parse date
        end_dt = datetime.strptime(end_date, "%Y%m%d")

        # Validate date is not too far in future
        max_future_date = datetime.now() + timedelta(days=365)
        if end_dt > max_future_date:
            raise HTTPException(
                status_code=400, detail="Data não pode ser superior a 1 ano no futuro"
            )

        pncp_service = PNCPService()
        return await pncp_service.get_open_contractions(
            end_date=end_dt,
            modality_code=modality_code,
            uf=uf,
            cnpj=cnpj,
            page=page,
            page_size=page_size,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Formato de data inválido. Use AAAAMMDD: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar PNCP: {str(e)}")


@router.post("/sync/recent")
async def sync_recent_tenders(
    background_tasks: BackgroundTasks,
    days_back: int = Query(
        7, ge=1, le=30, description="Dias para sincronizar (máximo 30)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """
    Sincronizar editais recentes do PNCP para o banco de dados local.
    Operação executada em background para não bloquear a interface.
    """

    def sync_task():
        """Background task para sincronização."""
        import asyncio

        pncp_service = PNCPService()

        # Create new event loop for background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                pncp_service.sync_recent_tenders(db, days_back)
            )

            # Log result
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"PNCP sync completed: {result}")

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"PNCP sync failed: {str(e)}")
        finally:
            loop.close()

    # Add background task
    background_tasks.add_task(sync_task)

    return {
        "message": "Sincronização iniciada em background",
        "days_back": days_back,
        "started_at": datetime.now().isoformat(),
        "started_by": current_user.email,
    }


@router.get("/sync/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obter status da última sincronização com PNCP.
    """
    # Check for recent tenders with PNCP source
    from app.models.tender import Tender as TenderModel

    recent_pncp_tenders = (
        db.query(TenderModel)
        .filter(
            TenderModel.additional_info.op("->>")('"source"') == "PNCP_API",
            TenderModel.created_at >= datetime.now() - timedelta(days=7),
        )
        .count()
    )

    last_pncp_tender = (
        db.query(TenderModel)
        .filter(TenderModel.additional_info.op("->>")('"source"') == "PNCP_API")
        .order_by(TenderModel.created_at.desc())
        .first()
    )

    last_sync_date = None
    if last_pncp_tender and last_pncp_tender.additional_info:
        last_sync_date = last_pncp_tender.additional_info.get("sync_date")

    return {
        "recent_synced_tenders": recent_pncp_tenders,
        "last_sync_date": last_sync_date,
        "last_tender_synced": last_pncp_tender.created_at.isoformat()
        if last_pncp_tender
        else None,
        "pncp_integration_active": True,
    }


@router.get("/stats")
async def get_pncp_integration_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Estatísticas da integração PNCP.
    """
    from sqlalchemy import func

    from app.models.tender import Tender as TenderModel

    # Count PNCP tenders by modality
    pncp_tenders_by_modality = (
        db.query(TenderModel.modality, func.count(TenderModel.id).label("count"))
        .filter(TenderModel.additional_info.op("->>")('"source"') == "PNCP_API")
        .group_by(TenderModel.modality)
        .all()
    )

    # Count PNCP tenders by status
    pncp_tenders_by_status = (
        db.query(TenderModel.status, func.count(TenderModel.id).label("count"))
        .filter(TenderModel.additional_info.op("->>")('"source"') == "PNCP_API")
        .group_by(TenderModel.status)
        .all()
    )

    # Total PNCP tenders
    total_pncp_tenders = (
        db.query(TenderModel)
        .filter(TenderModel.additional_info.op("->>")('"source"') == "PNCP_API")
        .count()
    )

    # Recent PNCP tenders (last 30 days)
    recent_pncp_tenders = (
        db.query(TenderModel)
        .filter(
            TenderModel.additional_info.op("->>")('"source"') == "PNCP_API",
            TenderModel.created_at >= datetime.now() - timedelta(days=30),
        )
        .count()
    )

    return {
        "total_pncp_tenders": total_pncp_tenders,
        "recent_pncp_tenders": recent_pncp_tenders,
        "tenders_by_modality": {
            modality.value: count for modality, count in pncp_tenders_by_modality
        },
        "tenders_by_status": {
            status.value: count for status, count in pncp_tenders_by_status
        },
        "integration_health": "active",
    }


@router.post("/test-connection")
async def test_pncp_connection(
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """
    Testar conectividade com API PNCP.
    Endpoint de diagnóstico para administradores.
    """
    pncp_service = PNCPService()

    try:
        # Test basic connectivity
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        test_response = await pncp_service.get_contractions_by_publication_date(
            start_date=start_date,
            end_date=end_date,
            modality_code=6,  # Pregão Eletrônico
            page=1,
            page_size=1,
        )

        return {
            "connection_status": "success",
            "api_responsive": True,
            "sample_data_received": bool(test_response.get("data")),
            "total_available": test_response.get("totalRegistros", 0),
            "test_completed_at": datetime.now().isoformat(),
            "cors_bypass": "working",  # Indicates CORS bypass is functioning
        }

    except Exception as e:
        return {
            "connection_status": "failed",
            "api_responsive": False,
            "error": str(e),
            "test_completed_at": datetime.now().isoformat(),
            "cors_bypass": "unknown",
        }
