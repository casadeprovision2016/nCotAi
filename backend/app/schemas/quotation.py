"""
Quotation (Cotação) schemas
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.quotation import QuotationPriority, QuotationStatus
from enum import Enum

class ItemStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Base schemas
class QuotationBase(BaseModel):
    """Base quotation schema."""

    title: str = Field(
        ..., min_length=1, max_length=255, description="Título da cotação"
    )
    description: Optional[str] = Field(
        None, max_length=2000, description="Descrição detalhada"
    )
    tender_id: Optional[UUID] = Field(None, description="ID do edital relacionado")
    status: QuotationStatus = Field(
        default=QuotationStatus.DRAFT, description="Status da cotação"
    )
    priority: QuotationPriority = Field(
        default=QuotationPriority.MEDIUM, description="Prioridade"
    )
    deadline: Optional[date] = Field(None, description="Prazo final para cotação")
    expected_delivery: Optional[date] = Field(
        None, description="Data esperada de entrega"
    )
    notes: Optional[str] = Field(
        None, max_length=2000, description="Observações gerais"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadados adicionais"
    )

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v):
        if v and v <= date.today():
            raise ValueError("Data limite deve ser no futuro")
        return v

    @field_validator("expected_delivery")
    @classmethod
    def delivery_must_be_after_deadline(cls, v, info):
        if v and info.data.get("deadline") and v < info.data["deadline"]:
            raise ValueError("Data de entrega deve ser após o prazo da cotação")
        return v


class QuotationCreate(QuotationBase):
    """Schema for creating quotations."""

    pass


class QuotationUpdate(BaseModel):
    """Schema for updating quotations."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[QuotationStatus] = None
    priority: Optional[QuotationPriority] = None
    deadline: Optional[date] = None
    expected_delivery: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None


class QuotationSummary(BaseModel):
    """Summary schema for quotation listings."""

    id: UUID
    title: str
    status: QuotationStatus
    priority: QuotationPriority
    deadline: Optional[date]
    total_value: Optional[Decimal]
    items_count: int
    suppliers_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Quotation(QuotationBase):
    """Full quotation schema with all relationships."""

    id: UUID
    created_by: UUID
    total_value: Optional[Decimal] = Field(None, description="Valor total estimado")
    items_count: int = Field(0, description="Número de itens")
    suppliers_count: int = Field(0, description="Número de fornecedores")
    created_at: datetime
    updated_at: datetime

    # Related objects (will be populated when needed)
    items: List["QuotationItem"] = Field(default_factory=list)
    suppliers: List["Supplier"] = Field(default_factory=list)

    class Config:
        from_attributes = True


# QuotationItem schemas
class QuotationItemBase(BaseModel):
    """Base quotation item schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Nome do item")
    description: Optional[str] = Field(
        None, max_length=1000, description="Descrição do item"
    )
    quantity: Decimal = Field(..., gt=0, description="Quantidade")
    unit: str = Field(..., min_length=1, max_length=50, description="Unidade de medida")
    estimated_price: Optional[Decimal] = Field(
        None, ge=0, description="Preço estimado unitário"
    )
    category: Optional[str] = Field(
        None, max_length=100, description="Categoria do item"
    )
    specifications: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Especificações técnicas"
    )
    status: ItemStatus = Field(default=ItemStatus.PENDING, description="Status do item")
    priority: QuotationPriority = Field(
        default=QuotationPriority.MEDIUM, description="Prioridade do item"
    )

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v

    @field_validator("estimated_price")
    @classmethod
    def price_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Preço não pode ser negativo")
        return v


class QuotationItemCreate(QuotationItemBase):
    """Schema for creating quotation items."""

    quotation_id: UUID = Field(..., description="ID da cotação")


class QuotationItemUpdate(BaseModel):
    """Schema for updating quotation items."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    estimated_price: Optional[Decimal] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    specifications: Optional[Dict[str, Any]] = None
    status: Optional[ItemStatus] = None
    priority: Optional[QuotationPriority] = None


class QuotationItem(QuotationItemBase):
    """Full quotation item schema."""

    id: UUID
    quotation_id: UUID
    total_estimated_value: Optional[Decimal] = Field(
        None, description="Valor total estimado (quantity * estimated_price)"
    )
    responses_count: int = Field(0, description="Número de respostas recebidas")
    best_price: Optional[Decimal] = Field(None, description="Melhor preço recebido")
    selected_supplier_id: Optional[UUID] = Field(
        None, description="Fornecedor selecionado"
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Supplier schemas
class SupplierBase(BaseModel):
    """Base supplier schema."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Nome do fornecedor"
    )
    email: str = Field(..., description="Email do fornecedor")
    phone: Optional[str] = Field(None, max_length=20, description="Telefone")
    document: Optional[str] = Field(None, max_length=20, description="CPF/CNPJ")
    address: Optional[str] = Field(None, max_length=500, description="Endereço")
    city: Optional[str] = Field(None, max_length=100, description="Cidade")
    state: Optional[str] = Field(None, max_length=2, description="Estado (UF)")
    zip_code: Optional[str] = Field(None, max_length=10, description="CEP")
    website: Optional[str] = Field(None, max_length=255, description="Website")
    notes: Optional[str] = Field(None, max_length=1000, description="Observações")
    is_active: bool = Field(default=True, description="Fornecedor ativo")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadados adicionais"
    )

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v):
        import re

        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Email inválido")
        return v.lower()

    @field_validator("state")
    @classmethod
    def state_must_be_valid(cls, v):
        if v and len(v) != 2:
            raise ValueError("Estado deve ter 2 caracteres")
        return v.upper() if v else v


class SupplierCreate(SupplierBase):
    """Schema for creating suppliers."""

    pass


class SupplierUpdate(BaseModel):
    """Schema for updating suppliers."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    document: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    website: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class Supplier(SupplierBase):
    """Full supplier schema."""

    id: UUID
    created_by: UUID
    quotations_count: int = Field(0, description="Número de cotações participadas")
    average_rating: Optional[Decimal] = Field(None, description="Avaliação média")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# QuotationResponse schemas
class QuotationResponseBase(BaseModel):
    """Base quotation response schema."""

    item_id: UUID = Field(..., description="ID do item da cotação")
    supplier_id: UUID = Field(..., description="ID do fornecedor")
    unit_price: Decimal = Field(..., gt=0, description="Preço unitário")
    quantity_available: Optional[Decimal] = Field(
        None, gt=0, description="Quantidade disponível"
    )
    delivery_time_days: Optional[int] = Field(
        None, ge=0, description="Prazo de entrega em dias"
    )
    observations: Optional[str] = Field(
        None, max_length=1000, description="Observações"
    )
    validity_days: Optional[int] = Field(
        None, ge=1, description="Validade da proposta em dias"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadados adicionais"
    )

    @field_validator("unit_price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Preço unitário deve ser maior que zero")
        return v


class QuotationResponseCreate(QuotationResponseBase):
    """Schema for creating quotation responses."""

    pass


class QuotationResponseUpdate(BaseModel):
    """Schema for updating quotation responses."""

    unit_price: Optional[Decimal] = Field(None, gt=0)
    quantity_available: Optional[Decimal] = Field(None, gt=0)
    delivery_time_days: Optional[int] = Field(None, ge=0)
    observations: Optional[str] = Field(None, max_length=1000)
    validity_days: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class QuotationResponse(QuotationResponseBase):
    """Full quotation response schema."""

    id: UUID
    total_price: Decimal = Field(..., description="Preço total (unit_price * quantity)")
    is_selected: bool = Field(default=False, description="Resposta selecionada")
    created_at: datetime
    updated_at: datetime

    # Related objects
    item: Optional[QuotationItem] = None
    supplier: Optional[Supplier] = None

    class Config:
        from_attributes = True


# Search and pagination schemas
class QuotationSearchFilters(BaseModel):
    """Filters for quotation search."""

    search: Optional[str] = Field(None, description="Busca textual")
    status: Optional[List[QuotationStatus]] = Field(
        None, description="Status da cotação"
    )
    priority: Optional[List[QuotationPriority]] = Field(None, description="Prioridade")
    tender_id: Optional[List[UUID]] = Field(None, description="IDs dos editais")
    created_by: Optional[List[UUID]] = Field(None, description="IDs dos criadores")
    deadline_from: Optional[date] = Field(None, description="Prazo inicial")
    deadline_to: Optional[date] = Field(None, description="Prazo final")
    min_value: Optional[Decimal] = Field(None, ge=0, description="Valor mínimo")
    max_value: Optional[Decimal] = Field(None, ge=0, description="Valor máximo")


class QuotationSearchParams(BaseModel):
    """Parameters for quotation search."""

    filters: Optional[QuotationSearchFilters] = None
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(20, ge=1, le=100, description="Itens por página")
    sort_by: str = Field("created_at", description="Campo para ordenação")
    sort_order: str = Field(
        "desc", pattern="^(asc|desc)$", description="Ordem da ordenação"
    )


class QuotationSearchResponse(BaseModel):
    """Response for quotation search."""

    items: List[QuotationSummary]
    total_items: int
    total_pages: int
    current_page: int
    page_size: int


# Update forward references
Quotation.update_forward_refs()
QuotationItem.update_forward_refs()
QuotationResponse.update_forward_refs()
