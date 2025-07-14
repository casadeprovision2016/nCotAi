"""
Quotation (Cotação) models
"""

import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class QuotationStatus(str, PyEnum):
    """Status da cotação."""

    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class QuotationType(str, PyEnum):
    """Tipo de cotação."""

    FORMAL = "formal"  # Cotação formal com processo estruturado
    INFORMAL = "informal"  # Cotação rápida/informal
    MARKET_RESEARCH = "market_research"  # Pesquisa de mercado


class QuotationPriority(str, PyEnum):
    """Prioridade da cotação."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupplierStatus(str, PyEnum):
    """Status do fornecedor."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    POTENTIAL = "potential"


class ProposalStatus(str, PyEnum):
    """Status da proposta do fornecedor."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Supplier(Base):
    """Fornecedores cadastrados."""

    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Dados básicos
    company_name = Column(String(300), nullable=False, index=True)
    trade_name = Column(String(300), nullable=True)
    cnpj = Column(String(18), nullable=True, unique=True, index=True)
    cpf = Column(String(14), nullable=True, unique=True, index=True)

    # Classificação
    company_size = Column(String(50), nullable=True)  # MEI, ME, EPP, Grande
    business_type = Column(String(100), nullable=True)
    main_activity = Column(String(200), nullable=True)

    # Contato
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    mobile = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)

    # Endereço
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zipcode = Column(String(10), nullable=True)

    # Dados bancários
    bank_name = Column(String(100), nullable=True)
    bank_agency = Column(String(20), nullable=True)
    bank_account = Column(String(20), nullable=True)
    pix_key = Column(String(100), nullable=True)

    # Avaliação e histórico
    rating = Column(Float, nullable=True)  # 0-5
    total_quotes = Column(Integer, default=0)
    successful_quotes = Column(Integer, default=0)
    average_response_time = Column(Integer, nullable=True)  # Em horas

    # Status e configurações
    status = Column(Enum(SupplierStatus), default=SupplierStatus.ACTIVE, nullable=False)
    is_verified = Column(Boolean, default=False)
    accepts_email_quotes = Column(Boolean, default=True)
    preferred_contact_method = Column(String(50), default="email")

    # Especialidades
    categories = Column(JSON, nullable=True)  # Lista de categorias que atende
    certifications = Column(JSON, nullable=True)  # Certificações

    # Observações
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_contact = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    quotes = relationship("SupplierQuote", back_populates="supplier")


class Quotation(Base):
    """Cotação principal."""

    __tablename__ = "quotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificação
    number = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Classificação
    type = Column(Enum(QuotationType), default=QuotationType.FORMAL, nullable=False)
    priority = Column(
        Enum(QuotationPriority), default=QuotationPriority.MEDIUM, nullable=False
    )
    status = Column(
        Enum(QuotationStatus), default=QuotationStatus.DRAFT, nullable=False, index=True
    )

    # Relacionado a edital
    related_tender_id = Column(
        UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=True
    )

    # Prazos
    response_deadline = Column(DateTime(timezone=True), nullable=True, index=True)
    delivery_deadline = Column(Date, nullable=True)
    validity_period = Column(Integer, nullable=True)  # Dias de validade da proposta

    # Localização e entrega
    delivery_location = Column(String(500), nullable=True)
    delivery_city = Column(String(100), nullable=True)
    delivery_state = Column(String(2), nullable=True)
    delivery_instructions = Column(Text, nullable=True)

    # Condições comerciais
    payment_terms = Column(String(200), nullable=True)
    payment_method = Column(String(100), nullable=True)
    requires_warranty = Column(Boolean, default=False)
    warranty_period = Column(Integer, nullable=True)  # Em meses

    # Valores estimados
    estimated_total_value = Column(Float, nullable=True)
    budget_limit = Column(Float, nullable=True)

    # Configurações
    allow_partial_quotes = Column(Boolean, default=True)
    require_technical_specs = Column(Boolean, default=False)
    require_samples = Column(Boolean, default=False)

    # Template e personalização
    email_template_id = Column(UUID(as_uuid=True), nullable=True)
    custom_instructions = Column(Text, nullable=True)

    # Análise e resultado
    total_responses = Column(Integer, default=0)
    best_price = Column(Float, nullable=True)
    selected_supplier_id = Column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True
    )
    closure_reason = Column(String(200), nullable=True)

    # Responsável
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Observações
    observations = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    related_tender = relationship("Tender")
    selected_supplier = relationship("Supplier")
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    items = relationship(
        "QuotationItem", back_populates="quotation", cascade="all, delete-orphan"
    )
    supplier_quotes = relationship(
        "SupplierQuote", back_populates="quotation", cascade="all, delete-orphan"
    )
    documents = relationship(
        "QuotationDocument", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationItem(Base):
    """Itens da cotação."""

    __tablename__ = "quotation_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id = Column(
        UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False
    )

    # Identificação
    item_number = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)

    # Especificações
    detailed_description = Column(Text, nullable=True)
    technical_specifications = Column(Text, nullable=True)
    brand_preference = Column(String(100), nullable=True)
    model_preference = Column(String(100), nullable=True)

    # Quantidade e unidade
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    # Preços de referência
    reference_price = Column(Float, nullable=True)
    estimated_price = Column(Float, nullable=True)
    maximum_price = Column(Float, nullable=True)

    # Classificação
    category = Column(String(100), nullable=True)
    catmat_code = Column(String(20), nullable=True)

    # Configurações do item
    is_mandatory = Column(Boolean, default=True)
    allow_substitutes = Column(Boolean, default=False)
    requires_sample = Column(Boolean, default=False)

    # Observações
    observations = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    quotation = relationship("Quotation", back_populates="items")
    supplier_quotes = relationship("SupplierQuoteItem", back_populates="quotation_item")


class SupplierQuote(Base):
    """Cotação de um fornecedor específico."""

    __tablename__ = "supplier_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id = Column(
        UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False
    )
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)

    # Status e controle
    status = Column(
        Enum(ProposalStatus), default=ProposalStatus.PENDING, nullable=False, index=True
    )
    invitation_sent_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # Proposta comercial
    total_value = Column(Float, nullable=True)
    delivery_time = Column(Integer, nullable=True)  # Dias para entrega
    payment_terms = Column(String(200), nullable=True)
    validity_days = Column(Integer, nullable=True)

    # Condições especiais
    observations = Column(Text, nullable=True)
    special_conditions = Column(Text, nullable=True)

    # Avaliação
    technical_score = Column(Float, nullable=True)  # 0-10
    commercial_score = Column(Float, nullable=True)  # 0-10
    final_score = Column(Float, nullable=True)  # 0-10
    evaluator_notes = Column(Text, nullable=True)

    # Documentos anexos
    has_technical_proposal = Column(Boolean, default=False)
    has_commercial_proposal = Column(Boolean, default=False)

    # Comunicação
    email_sent = Column(Boolean, default=False)
    email_opened = Column(Boolean, default=False)
    reminder_count = Column(Integer, default=0)
    last_reminder_sent = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    quotation = relationship("Quotation", back_populates="supplier_quotes")
    supplier = relationship("Supplier", back_populates="quotes")
    items = relationship(
        "SupplierQuoteItem",
        back_populates="supplier_quote",
        cascade="all, delete-orphan",
    )


class SupplierQuoteItem(Base):
    """Itens cotados pelo fornecedor."""

    __tablename__ = "supplier_quote_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_quote_id = Column(
        UUID(as_uuid=True), ForeignKey("supplier_quotes.id"), nullable=False
    )
    quotation_item_id = Column(
        UUID(as_uuid=True), ForeignKey("quotation_items.id"), nullable=False
    )

    # Proposta do fornecedor
    unit_price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)

    # Produto oferecido
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Especificações técnicas
    technical_details = Column(Text, nullable=True)
    warranty_period = Column(Integer, nullable=True)  # Em meses

    # Disponibilidade
    availability = Column(String(100), nullable=True)
    delivery_time = Column(Integer, nullable=True)  # Dias

    # Flags
    is_alternative = Column(Boolean, default=False)
    meets_specifications = Column(Boolean, default=True)

    # Observações
    observations = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    supplier_quote = relationship("SupplierQuote", back_populates="items")
    quotation_item = relationship("QuotationItem", back_populates="supplier_quotes")


class QuotationDocument(Base):
    """Documentos anexos à cotação."""

    __tablename__ = "quotation_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id = Column(
        UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False
    )

    # Informações do documento
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=True)  # technical_spec, terms, etc.

    # Arquivo
    file_name = Column(String(300), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Controle
    is_public = Column(Boolean, default=False)  # Visível para fornecedores
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    quotation = relationship("Quotation", back_populates="documents")
    uploaded_by = relationship("User")


class QuotationTemplate(Base):
    """Templates de cotação para reutilização."""

    __tablename__ = "quotation_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificação
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)

    # Template
    title_template = Column(String(300), nullable=True)
    description_template = Column(Text, nullable=True)
    instructions_template = Column(Text, nullable=True)

    # Configurações padrão
    default_validity_period = Column(Integer, nullable=True)
    default_delivery_time = Column(Integer, nullable=True)
    default_payment_terms = Column(String(200), nullable=True)

    # Items template
    template_items = Column(JSON, nullable=True)  # Lista de itens padrão

    # Configurações
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)

    # Criador
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Uso
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    created_by = relationship("User")
