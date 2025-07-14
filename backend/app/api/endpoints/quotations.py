"""
Quotation (Cotação) endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.core.auth import RoleChecker
from app.models.user import User
from app.schemas.quotation import (
    Quotation,
    QuotationCreate,
    QuotationItem,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationResponse,
    QuotationResponseCreate,
    QuotationResponseUpdate,
    QuotationSearchFilters,
    QuotationSearchParams,
    QuotationSearchResponse,
    QuotationSummary,
    QuotationUpdate,
    Supplier,
    SupplierCreate,
    SupplierUpdate,
)
from app.services.quotation_service import QuotationService

router = APIRouter()


# Quotation CRUD Endpoints
@router.get("/", response_model=QuotationSearchResponse)
async def list_quotations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    search: Optional[str] = Query(None, description="Busca textual"),
    status: Optional[str] = Query(None, description="Status"),
    priority: Optional[str] = Query(None, description="Prioridade"),
    tender_id: Optional[UUID] = Query(None, description="ID do edital"),
    sort_by: str = Query("created_at", description="Campo para ordenação"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Ordem"),
):
    """Listar cotações com filtros e paginação."""

    # Construir filtros
    filters = QuotationSearchFilters(
        search=search,
        status=[status] if status else None,
        priority=[priority] if priority else None,
        tender_id=[tender_id] if tender_id else None,
    )

    search_params = QuotationSearchParams(
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    quotation_service = QuotationService(db)
    return quotation_service.search_quotations(search_params)


@router.post("/", response_model=Quotation, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    quotation_data: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Criar nova cotação."""
    quotation_service = QuotationService(db)
    return quotation_service.create_quotation(quotation_data, current_user.id)


@router.get("/{quotation_id}", response_model=Quotation)
async def get_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter cotação por ID."""
    quotation_service = QuotationService(db)
    quotation = quotation_service.get_quotation(quotation_id)

    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada"
        )

    return quotation


@router.put("/{quotation_id}", response_model=Quotation)
async def update_quotation(
    quotation_id: UUID,
    quotation_data: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualizar cotação."""
    quotation_service = QuotationService(db)
    quotation = quotation_service.update_quotation(quotation_id, quotation_data)

    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada"
        )

    return quotation


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["MANAGER", "ADMIN", "SUPER_ADMIN"])),
):
    """Deletar cotação."""
    quotation_service = QuotationService(db)
    success = quotation_service.delete_quotation(quotation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada"
        )


# Quotation Items Endpoints
@router.get("/{quotation_id}/items", response_model=List[QuotationItem])
async def list_quotation_items(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar itens de uma cotação."""
    quotation_service = QuotationService(db)
    return quotation_service.list_quotation_items(quotation_id)


@router.post(
    "/{quotation_id}/items",
    response_model=QuotationItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_quotation_item(
    quotation_id: UUID,
    item_data: QuotationItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Criar novo item de cotação."""
    # Override quotation_id from URL
    item_data.quotation_id = quotation_id

    quotation_service = QuotationService(db)
    return quotation_service.create_quotation_item(item_data)


@router.get("/{quotation_id}/items/{item_id}", response_model=QuotationItem)
async def get_quotation_item(
    quotation_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter item de cotação por ID."""
    quotation_service = QuotationService(db)
    item = quotation_service.get_quotation_item(item_id)

    if not item or item.quotation_id != quotation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )

    return item


@router.put("/{quotation_id}/items/{item_id}", response_model=QuotationItem)
async def update_quotation_item(
    quotation_id: UUID,
    item_id: UUID,
    item_data: QuotationItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualizar item de cotação."""
    quotation_service = QuotationService(db)
    item = quotation_service.update_quotation_item(item_id, item_data)

    if not item or item.quotation_id != quotation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )

    return item


@router.delete(
    "/{quotation_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_quotation_item(
    quotation_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletar item de cotação."""
    quotation_service = QuotationService(db)
    success = quotation_service.delete_quotation_item(item_id, quotation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado"
        )


# Supplier Endpoints
@router.get("/suppliers/", response_model=List[Supplier])
async def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Buscar por nome ou email"),
    active_only: bool = Query(True, description="Apenas fornecedores ativos"),
):
    """Listar fornecedores."""
    quotation_service = QuotationService(db)
    return quotation_service.list_suppliers(
        skip=skip, limit=limit, search=search, active_only=active_only
    )


@router.post(
    "/suppliers/", response_model=Supplier, status_code=status.HTTP_201_CREATED
)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Criar novo fornecedor."""
    quotation_service = QuotationService(db)
    return quotation_service.create_supplier(supplier_data, current_user.id)


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter fornecedor por ID."""
    quotation_service = QuotationService(db)
    supplier = quotation_service.get_supplier(supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado"
        )

    return supplier


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(
    supplier_id: UUID,
    supplier_data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualizar fornecedor."""
    quotation_service = QuotationService(db)
    supplier = quotation_service.update_supplier(supplier_id, supplier_data)

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado"
        )

    return supplier


# Quotation Responses Endpoints
@router.get(
    "/{quotation_id}/items/{item_id}/responses", response_model=List[QuotationResponse]
)
async def list_item_responses(
    quotation_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar respostas de um item."""
    quotation_service = QuotationService(db)
    return quotation_service.list_item_responses(item_id)


@router.post(
    "/{quotation_id}/items/{item_id}/responses",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quotation_response(
    quotation_id: UUID,
    item_id: UUID,
    response_data: QuotationResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Criar resposta para um item de cotação."""
    # Override item_id from URL
    response_data.item_id = item_id

    quotation_service = QuotationService(db)
    return quotation_service.create_quotation_response(response_data)


@router.put(
    "/{quotation_id}/items/{item_id}/responses/{response_id}",
    response_model=QuotationResponse,
)
async def update_quotation_response(
    quotation_id: UUID,
    item_id: UUID,
    response_id: UUID,
    response_data: QuotationResponseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualizar resposta de cotação."""
    quotation_service = QuotationService(db)
    response = quotation_service.update_quotation_response(response_id, response_data)

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada"
        )

    return response


@router.post(
    "/{quotation_id}/items/{item_id}/responses/{response_id}/select",
    response_model=QuotationResponse,
)
async def select_quotation_response(
    quotation_id: UUID,
    item_id: UUID,
    response_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["MANAGER", "ADMIN", "SUPER_ADMIN"])),
):
    """Selecionar resposta de cotação."""
    quotation_service = QuotationService(db)
    response = quotation_service.select_quotation_response(response_id, item_id)

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada"
        )

    return response


# Statistics and Dashboard
@router.get("/stats/summary")
async def get_quotation_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter estatísticas resumidas das cotações."""
    quotation_service = QuotationService(db)
    return quotation_service.get_quotation_statistics()


@router.get("/stats/by-status")
async def get_quotations_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter estatísticas por status."""
    quotation_service = QuotationService(db)
    return quotation_service.get_quotations_by_status()


@router.get("/stats/by-month")
async def get_quotations_by_month(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    months: int = Query(12, ge=1, le=24, description="Número de meses"),
):
    """Obter estatísticas por mês."""
    quotation_service = QuotationService(db)
    return quotation_service.get_quotations_by_month(months=months)
