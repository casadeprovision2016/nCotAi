"""
Tender (Edital/Licitação) schemas
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.tender import (
    TenderCriteria,
    TenderModalityType,
    TenderStatus,
    TenderType,
)


# Government Entity Schemas
class GovernmentEntityBase(BaseModel):
    name: str = Field(..., max_length=300, description="Nome do órgão")
    code: Optional[str] = Field(
        None, max_length=50, description="CNPJ ou código oficial"
    )
    acronym: Optional[str] = Field(None, max_length=20, description="Sigla")
    type: Optional[str] = Field(
        None, max_length=100, description="Tipo (Municipal, Estadual, Federal)"
    )
    sphere: Optional[str] = Field(
        None, max_length=50, description="Esfera (Executivo, Legislativo, Judiciário)"
    )
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2, pattern="^[A-Z]{2}$")
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)


class GovernmentEntityCreate(GovernmentEntityBase):
    pass


class GovernmentEntityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=300)
    code: Optional[str] = Field(None, max_length=50)
    acronym: Optional[str] = Field(None, max_length=20)
    type: Optional[str] = Field(None, max_length=100)
    sphere: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2, pattern="^[A-Z]{2}$")
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class GovernmentEntity(GovernmentEntityBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Tender Category Schemas
class TenderCategoryBase(BaseModel):
    name: str = Field(..., max_length=200, description="Nome da categoria")
    code: Optional[str] = Field(None, max_length=50, description="Código CATMAT/CATSER")
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    level: int = Field(1, ge=1, le=5, description="Nível da categoria")


class TenderCategoryCreate(TenderCategoryBase):
    pass


class TenderCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    level: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None


class TenderCategory(TenderCategoryBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    children: List["TenderCategory"] = []

    class Config:
        from_attributes = True


# Tender Item Schemas
class TenderItemBase(BaseModel):
    item_number: str = Field(..., max_length=20, description="Número do item")
    lot_number: Optional[str] = Field(None, max_length=20, description="Número do lote")
    description: str = Field(..., description="Descrição do item")
    technical_specifications: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=50, description="Unidade de medida")
    quantity: Optional[float] = Field(None, ge=0)
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    estimated_total_price: Optional[float] = Field(None, ge=0)
    catmat_code: Optional[str] = Field(None, max_length=20)
    catser_code: Optional[str] = Field(None, max_length=20)
    is_reserved_me_epp: bool = False
    is_sustainable: bool = False


class TenderItemCreate(TenderItemBase):
    pass


class TenderItemUpdate(BaseModel):
    item_number: Optional[str] = Field(None, max_length=20)
    lot_number: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    technical_specifications: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=50)
    quantity: Optional[float] = Field(None, ge=0)
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    estimated_total_price: Optional[float] = Field(None, ge=0)
    catmat_code: Optional[str] = Field(None, max_length=20)
    catser_code: Optional[str] = Field(None, max_length=20)
    is_reserved_me_epp: Optional[bool] = None
    is_sustainable: Optional[bool] = None


class TenderItem(TenderItemBase):
    id: UUID
    tender_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Tender Document Schemas
class TenderDocumentBase(BaseModel):
    name: str = Field(..., max_length=300, description="Nome do documento")
    description: Optional[str] = None
    file_type: Optional[str] = Field(None, max_length=50)
    file_size: Optional[int] = Field(None, ge=0)
    original_url: Optional[str] = Field(None, max_length=500)
    local_path: Optional[str] = Field(None, max_length=500)


class TenderDocumentCreate(TenderDocumentBase):
    pass


class TenderDocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    file_type: Optional[str] = Field(None, max_length=50)
    file_size: Optional[int] = Field(None, ge=0)
    original_url: Optional[str] = Field(None, max_length=500)
    local_path: Optional[str] = Field(None, max_length=500)
    is_downloaded: Optional[bool] = None
    is_processed: Optional[bool] = None


class TenderDocument(TenderDocumentBase):
    id: UUID
    tender_id: UUID
    is_downloaded: bool
    is_processed: bool
    processing_status: Optional[str]
    extracted_text: Optional[str]
    extracted_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Main Tender Schemas
class TenderBase(BaseModel):
    number: str = Field(..., max_length=100, description="Número do edital")
    process_number: Optional[str] = Field(
        None, max_length=100, description="Número do processo"
    )
    title: str = Field(..., max_length=500, description="Título do edital")
    description: Optional[str] = None
    modality: TenderModalityType
    type: TenderType
    criteria: TenderCriteria
    government_entity_id: UUID
    category_id: Optional[UUID] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    minimum_value: Optional[float] = Field(None, ge=0)
    maximum_value: Optional[float] = Field(None, ge=0)
    publication_date: Optional[date] = None
    opening_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    delivery_deadline: Optional[date] = None
    delivery_location: Optional[str] = Field(None, max_length=500)
    delivery_city: Optional[str] = Field(None, max_length=100)
    delivery_state: Optional[str] = Field(None, max_length=2, pattern="^[A-Z]{2}$")
    notice_url: Optional[str] = Field(None, max_length=500)
    edict_url: Optional[str] = Field(None, max_length=500)
    attachments_urls: Optional[List[str]] = None
    requires_visit: bool = False
    visit_deadline: Optional[date] = None
    min_participants: Optional[int] = Field(None, ge=1)
    max_participants: Optional[int] = Field(None, ge=1)
    source: Optional[str] = Field(None, max_length=100)
    source_id: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=500)
    observations: Optional[str] = None

    @field_validator("closing_date")
    @classmethod
    def validate_closing_date(cls, v, info):
        if v and info.data.get("opening_date") and v <= info.data["opening_date"]:
            raise ValueError("Closing date must be after opening date")
        return v

    @field_validator("maximum_value")
    @classmethod
    def validate_maximum_value(cls, v, info):
        if v and info.data.get("minimum_value") and v <= info.data["minimum_value"]:
            raise ValueError("Maximum value must be greater than minimum value")
        return v


class TenderCreate(TenderBase):
    status: TenderStatus = TenderStatus.DRAFT


class TenderUpdate(BaseModel):
    number: Optional[str] = Field(None, max_length=100)
    process_number: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    modality: Optional[TenderModalityType] = None
    type: Optional[TenderType] = None
    criteria: Optional[TenderCriteria] = None
    status: Optional[TenderStatus] = None
    government_entity_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    minimum_value: Optional[float] = Field(None, ge=0)
    maximum_value: Optional[float] = Field(None, ge=0)
    publication_date: Optional[date] = None
    opening_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    delivery_deadline: Optional[date] = None
    delivery_location: Optional[str] = Field(None, max_length=500)
    delivery_city: Optional[str] = Field(None, max_length=100)
    delivery_state: Optional[str] = Field(None, max_length=2, pattern="^[A-Z]{2}$")
    notice_url: Optional[str] = Field(None, max_length=500)
    edict_url: Optional[str] = Field(None, max_length=500)
    attachments_urls: Optional[List[str]] = None
    requires_visit: Optional[bool] = None
    visit_deadline: Optional[date] = None
    min_participants: Optional[int] = Field(None, ge=1)
    max_participants: Optional[int] = Field(None, ge=1)
    source: Optional[str] = Field(None, max_length=100)
    source_id: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=500)
    observations: Optional[str] = None
    internal_notes: Optional[str] = None
    is_monitored: Optional[bool] = None
    is_favorite: Optional[bool] = None
    is_relevant: Optional[bool] = None


class Tender(TenderBase):
    id: UUID
    status: TenderStatus
    internal_notes: Optional[str]
    is_monitored: bool
    is_favorite: bool
    is_relevant: bool
    last_update_check: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Related objects
    government_entity: Optional[GovernmentEntity] = None
    category: Optional[TenderCategory] = None
    items: List[TenderItem] = []
    documents: List[TenderDocument] = []

    class Config:
        from_attributes = True


class TenderSummary(BaseModel):
    """Resumo do edital para listagens."""

    id: UUID
    number: str
    title: str
    modality: TenderModalityType
    type: TenderType
    status: TenderStatus
    estimated_value: Optional[float]
    opening_date: Optional[datetime]
    closing_date: Optional[datetime]
    government_entity_name: Optional[str]
    is_monitored: bool
    is_favorite: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Search and Filter Schemas
class TenderSearchFilters(BaseModel):
    """Filtros para busca de editais."""

    search: Optional[str] = Field(None, description="Busca textual")
    modality: Optional[List[TenderModalityType]] = None
    type: Optional[List[TenderType]] = None
    status: Optional[List[TenderStatus]] = None
    government_entity_id: Optional[List[UUID]] = None
    category_id: Optional[List[UUID]] = None
    min_value: Optional[float] = Field(None, ge=0)
    max_value: Optional[float] = Field(None, ge=0)
    opening_date_from: Optional[date] = None
    opening_date_to: Optional[date] = None
    closing_date_from: Optional[date] = None
    closing_date_to: Optional[date] = None
    state: Optional[List[str]] = None
    is_monitored: Optional[bool] = None
    is_favorite: Optional[bool] = None
    is_relevant: Optional[bool] = None


class TenderSearchParams(BaseModel):
    """Parâmetros de busca e paginação."""

    filters: Optional[TenderSearchFilters] = None
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(20, ge=1, le=100, description="Itens por página")
    sort_by: str = Field("created_at", description="Campo para ordenação")
    sort_order: str = Field(
        "desc", pattern="^(asc|desc)$", description="Ordem de classificação"
    )


class TenderSearchResponse(BaseModel):
    """Resposta da busca de editais."""

    items: List[TenderSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# Update TenderCategory to handle recursive structure
TenderCategory.model_rebuild()
