"""
Tender (Edital/Licitação) models
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


class TenderModalityType(str, PyEnum):
    """Modalidades de licitação conforme Lei 14.133/2021."""

    PREGAO = "pregao"
    CONCORRENCIA = "concorrencia"
    CONCURSO = "concurso"
    LEILAO = "leilao"
    DIALOGO_COMPETITIVO = "dialogo_competitivo"
    CREDENCIAMENTO = "credenciamento"
    MANIFESTACAO_INTERESSE = "manifestacao_interesse"


class TenderStatus(str, PyEnum):
    """Status do edital."""

    DRAFT = "draft"
    PUBLISHED = "published"
    OPEN = "open"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    CANCELED = "canceled"
    DESERTED = "deserted"
    ADJUDICATED = "adjudicated"
    HOMOLOGATED = "homologated"


class TenderType(str, PyEnum):
    """Tipo de objeto do edital."""

    GOODS = "goods"  # Bens
    SERVICES = "services"  # Serviços
    WORKS = "works"  # Obras
    MIXED = "mixed"  # Misto


class TenderCriteria(str, PyEnum):
    """Critério de julgamento."""

    LOWEST_PRICE = "lowest_price"
    BEST_TECHNIQUE = "best_technique"
    TECHNIQUE_AND_PRICE = "technique_and_price"
    HIGHEST_OFFER = "highest_offer"


class GovernmentEntity(Base):
    """Órgão público responsável pela licitação."""

    __tablename__ = "government_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False, index=True)
    code = Column(
        String(50), unique=True, nullable=True, index=True
    )  # CNPJ ou código oficial
    acronym = Column(String(20), nullable=True)
    type = Column(String(100), nullable=True)  # Municipal, Estadual, Federal
    sphere = Column(String(50), nullable=True)  # Executivo, Legislativo, Judiciário
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

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
    tenders = relationship("Tender", back_populates="government_entity")


class TenderCategory(Base):
    """Categoria/Classificação do edital."""

    __tablename__ = "tender_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)  # Código CATMAT/CATSER
    description = Column(Text, nullable=True)
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("tender_categories.id"), nullable=True
    )
    level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

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

    # Self-referential relationship
    parent = relationship("TenderCategory", remote_side=[id], back_populates="children")
    children = relationship("TenderCategory", back_populates="parent")

    # Relationships
    tenders = relationship("Tender", back_populates="category")


class Tender(Base):
    """Edital/Licitação principal."""

    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identificação
    number = Column(String(100), nullable=False, index=True)
    process_number = Column(String(100), nullable=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Classificação
    modality = Column(Enum(TenderModalityType), nullable=False, index=True)
    type = Column(Enum(TenderType), nullable=False, index=True)
    criteria = Column(Enum(TenderCriteria), nullable=False)
    status = Column(
        Enum(TenderStatus), default=TenderStatus.DRAFT, nullable=False, index=True
    )

    # Relacionamentos
    government_entity_id = Column(
        UUID(as_uuid=True), ForeignKey("government_entities.id"), nullable=False
    )
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("tender_categories.id"), nullable=True
    )

    # Valores
    estimated_value = Column(Float, nullable=True)
    minimum_value = Column(Float, nullable=True)
    maximum_value = Column(Float, nullable=True)

    # Datas importantes
    publication_date = Column(Date, nullable=True, index=True)
    opening_date = Column(DateTime(timezone=True), nullable=True, index=True)
    closing_date = Column(DateTime(timezone=True), nullable=True, index=True)
    delivery_deadline = Column(Date, nullable=True)

    # Localização
    delivery_location = Column(String(500), nullable=True)
    delivery_city = Column(String(100), nullable=True)
    delivery_state = Column(String(2), nullable=True)

    # Documentação
    notice_url = Column(String(500), nullable=True)
    edict_url = Column(String(500), nullable=True)
    attachments_urls = Column(JSON, nullable=True)  # Lista de URLs dos anexos

    # Participação
    requires_visit = Column(Boolean, default=False)
    visit_deadline = Column(Date, nullable=True)
    min_participants = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)

    # Metadados
    source = Column(String(100), nullable=True)  # Portal onde foi encontrado
    source_id = Column(String(100), nullable=True, index=True)  # ID no portal de origem
    source_url = Column(String(500), nullable=True)
    last_update_check = Column(DateTime(timezone=True), nullable=True)

    # Observações
    observations = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Flags
    is_monitored = Column(Boolean, default=False, index=True)
    is_favorite = Column(Boolean, default=False, index=True)
    is_relevant = Column(Boolean, default=True, index=True)

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
    government_entity = relationship("GovernmentEntity", back_populates="tenders")
    category = relationship("TenderCategory", back_populates="tenders")
    items = relationship(
        "TenderItem", back_populates="tender", cascade="all, delete-orphan"
    )
    documents = relationship(
        "TenderDocument", back_populates="tender", cascade="all, delete-orphan"
    )
    proposals = relationship("TenderProposal", back_populates="tender")


class TenderItem(Base):
    """Itens/Lotes do edital."""

    __tablename__ = "tender_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    # Identificação
    item_number = Column(String(20), nullable=False)
    lot_number = Column(String(20), nullable=True)
    description = Column(Text, nullable=False)

    # Especificações técnicas
    technical_specifications = Column(Text, nullable=True)
    unit = Column(String(50), nullable=True)  # Unidade de medida
    quantity = Column(Float, nullable=True)

    # Valores
    estimated_unit_price = Column(Float, nullable=True)
    estimated_total_price = Column(Float, nullable=True)

    # Classificação
    catmat_code = Column(String(20), nullable=True, index=True)
    catser_code = Column(String(20), nullable=True, index=True)

    # Metadados
    is_reserved_me_epp = Column(Boolean, default=False)  # Reservado para ME/EPP
    is_sustainable = Column(Boolean, default=False)

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
    tender = relationship("Tender", back_populates="items")


class TenderDocument(Base):
    """Documentos anexos ao edital."""

    __tablename__ = "tender_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    # Informações do documento
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, doc, xls, etc.
    file_size = Column(Integer, nullable=True)  # Em bytes

    # URLs e caminhos
    original_url = Column(String(500), nullable=True)
    local_path = Column(String(500), nullable=True)

    # Status do download/processamento
    is_downloaded = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), nullable=True)

    # Conteúdo extraído
    extracted_text = Column(Text, nullable=True)
    extracted_metadata = Column(JSON, nullable=True)

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
    tender = relationship("Tender", back_populates="documents")


class TenderProposal(Base):
    """Propostas enviadas para editais."""

    __tablename__ = "tender_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    # Identificação
    proposal_number = Column(String(100), nullable=True)
    company_name = Column(String(300), nullable=False)
    company_cnpj = Column(String(18), nullable=True)

    # Valores
    total_value = Column(Float, nullable=True)
    proposed_items = Column(JSON, nullable=True)  # Lista de itens com preços

    # Status
    status = Column(String(50), default="submitted", nullable=False)
    is_winner = Column(Boolean, default=False)
    classification = Column(Integer, nullable=True)

    # Observações
    observations = Column(Text, nullable=True)

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=True)
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
    tender = relationship("Tender", back_populates="proposals")
