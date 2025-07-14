"""
Tender (Edital/Licitação) endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.dependencies import get_db
from app.core.auth import PermissionChecker, RoleChecker
from app.models.user import User
from app.schemas.tender import (
    GovernmentEntity,
    GovernmentEntityCreate,
    GovernmentEntityUpdate,
    Tender,
    TenderCategory,
    TenderCategoryCreate,
    TenderCategoryUpdate,
    TenderCreate,
    TenderSearchFilters,
    TenderSearchParams,
    TenderSearchResponse,
    TenderSummary,
    TenderUpdate,
)
from app.services.tender_service import TenderService

router = APIRouter()


# Tender CRUD Endpoints
@router.get("/", response_model=TenderSearchResponse)
async def list_tenders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    search: Optional[str] = Query(None, description="Busca textual"),
    modality: Optional[str] = Query(None, description="Modalidade"),
    status: Optional[str] = Query(None, description="Status"),
    government_entity_id: Optional[UUID] = Query(None, description="ID do órgão"),
    category_id: Optional[UUID] = Query(None, description="ID da categoria"),
    min_value: Optional[float] = Query(None, ge=0, description="Valor mínimo"),
    max_value: Optional[float] = Query(None, ge=0, description="Valor máximo"),
    sort_by: str = Query("created_at", description="Campo para ordenação"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Ordem"),
):
    """Listar editais com filtros e paginação."""

    # Construir filtros
    filters = TenderSearchFilters(
        search=search,
        modality=[modality] if modality else None,
        status=[status] if status else None,
        government_entity_id=[government_entity_id] if government_entity_id else None,
        category_id=[category_id] if category_id else None,
        min_value=min_value,
        max_value=max_value,
    )

    search_params = TenderSearchParams(
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    tender_service = TenderService(db)
    return tender_service.search_tenders(search_params)


@router.post("/", response_model=Tender, status_code=status.HTTP_201_CREATED)
async def create_tender(
    tender_data: TenderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["MANAGER", "ADMIN", "SUPER_ADMIN"])),
):
    """Criar novo edital."""
    tender_service = TenderService(db)
    return tender_service.create_tender(tender_data)


@router.get("/{tender_id}", response_model=Tender)
async def get_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter edital por ID."""
    tender_service = TenderService(db)
    tender = tender_service.get_tender(tender_id)

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado"
        )

    return tender


@router.put("/{tender_id}", response_model=Tender)
async def update_tender(
    tender_id: UUID,
    tender_data: TenderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["MANAGER", "ADMIN", "SUPER_ADMIN"])),
):
    """Atualizar edital."""
    tender_service = TenderService(db)
    tender = tender_service.update_tender(tender_id, tender_data)

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado"
        )

    return tender


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """Deletar edital."""
    tender_service = TenderService(db)
    success = tender_service.delete_tender(tender_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado"
        )


# Tender Actions
@router.post("/{tender_id}/monitor", response_model=Tender)
async def toggle_monitor_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alternar monitoramento do edital."""
    tender_service = TenderService(db)
    tender = tender_service.toggle_monitor(tender_id)

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado"
        )

    return tender


@router.post("/{tender_id}/favorite", response_model=Tender)
async def toggle_favorite_tender(
    tender_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alternar favorito do edital."""
    tender_service = TenderService(db)
    tender = tender_service.toggle_favorite(tender_id)

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado"
        )

    return tender


# Government Entity Endpoints
@router.get("/government-entities/", response_model=List[GovernmentEntity])
async def list_government_entities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Buscar por nome ou sigla"),
):
    """Listar órgãos públicos."""
    tender_service = TenderService(db)
    return tender_service.list_government_entities(
        skip=skip, limit=limit, search=search
    )


@router.post(
    "/government-entities/",
    response_model=GovernmentEntity,
    status_code=status.HTTP_201_CREATED,
)
async def create_government_entity(
    entity_data: GovernmentEntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """Criar novo órgão público."""
    tender_service = TenderService(db)
    return tender_service.create_government_entity(entity_data)


@router.get("/government-entities/{entity_id}", response_model=GovernmentEntity)
async def get_government_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter órgão público por ID."""
    tender_service = TenderService(db)
    entity = tender_service.get_government_entity(entity_id)

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Órgão não encontrado"
        )

    return entity


@router.put("/government-entities/{entity_id}", response_model=GovernmentEntity)
async def update_government_entity(
    entity_id: UUID,
    entity_data: GovernmentEntityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """Atualizar órgão público."""
    tender_service = TenderService(db)
    entity = tender_service.update_government_entity(entity_id, entity_data)

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Órgão não encontrado"
        )

    return entity


# Tender Category Endpoints
@router.get("/categories/", response_model=List[TenderCategory])
async def list_tender_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    parent_id: Optional[UUID] = Query(None, description="ID da categoria pai"),
):
    """Listar categorias de editais."""
    tender_service = TenderService(db)
    return tender_service.list_tender_categories(parent_id=parent_id)


@router.post(
    "/categories/", response_model=TenderCategory, status_code=status.HTTP_201_CREATED
)
async def create_tender_category(
    category_data: TenderCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """Criar nova categoria de edital."""
    tender_service = TenderService(db)
    return tender_service.create_tender_category(category_data)


@router.get("/categories/{category_id}", response_model=TenderCategory)
async def get_tender_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter categoria por ID."""
    tender_service = TenderService(db)
    category = tender_service.get_tender_category(category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )

    return category


@router.put("/categories/{category_id}", response_model=TenderCategory)
async def update_tender_category(
    category_id: UUID,
    category_data: TenderCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"])),
):
    """Atualizar categoria de edital."""
    tender_service = TenderService(db)
    category = tender_service.update_tender_category(category_id, category_data)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )

    return category


# Statistics and Dashboard
@router.get("/stats/summary")
async def get_tender_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter estatísticas resumidas dos editais."""
    tender_service = TenderService(db)
    return tender_service.get_tender_statistics()


@router.get("/stats/by-modality")
async def get_tenders_by_modality(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter estatísticas por modalidade."""
    tender_service = TenderService(db)
    return tender_service.get_tenders_by_modality()


@router.get("/stats/by-month")
async def get_tenders_by_month(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    months: int = Query(12, ge=1, le=24, description="Número de meses"),
):
    """Obter estatísticas por mês."""
    tender_service = TenderService(db)
    return tender_service.get_tenders_by_month(months=months)
