"""
Report models for dynamic report generation and export system
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ReportType(enum.Enum):
    """Types of reports available in the system"""

    LICITACOES = "licitacoes"
    COTACOES = "cotacoes"
    TAREFAS = "tarefas"
    FINANCEIRO = "financeiro"
    DESEMPENHO = "desempenho"
    AUDITORIA = "auditoria"
    CUSTOMIZADO = "customizado"


class ReportFormat(enum.Enum):
    """Export formats supported"""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    DOCX = "docx"


class ReportStatus(enum.Enum):
    """Report generation status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportFrequency(enum.Enum):
    """Schedule frequency for automated reports"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ReportTemplate(Base):
    """Template definitions for report generation"""

    __tablename__ = "report_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(SQLEnum(ReportType), nullable=False)

    # Template configuration
    query_config = Column(JSON, nullable=False)  # SQL queries and filters
    layout_config = Column(JSON, nullable=False)  # Layout and styling
    chart_config = Column(JSON)  # Chart configurations
    field_mappings = Column(JSON, nullable=False)  # Data field mappings

    # Template metadata
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System-provided templates
    category = Column(String(100))
    tags = Column(JSON)  # Search tags

    # Versioning
    version = Column(String(50), default="1.0")
    parent_template_id = Column(
        UUID(as_uuid=True), ForeignKey("report_templates.id"), nullable=True
    )

    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    parent_template = relationship("ReportTemplate", remote_side=[id])
    child_templates = relationship("ReportTemplate", remote_side=[parent_template_id])
    reports = relationship("Report", back_populates="template")
    schedules = relationship("ReportSchedule", back_populates="template")


class Report(Base):
    """Generated report instances"""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Report configuration
    template_id = Column(
        UUID(as_uuid=True), ForeignKey("report_templates.id"), nullable=True
    )
    type = Column(SQLEnum(ReportType), nullable=False)
    format = Column(SQLEnum(ReportFormat), nullable=False)

    # Generation parameters
    parameters = Column(JSON)  # Runtime parameters (date ranges, filters, etc.)
    data_source = Column(JSON)  # Data source configuration

    # Status and metadata
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    progress = Column(Integer, default=0)  # Percentage complete
    error_message = Column(Text)

    # File information
    file_path = Column(String(500))  # Path to generated file
    file_size = Column(Integer)  # File size in bytes
    file_hash = Column(String(128))  # File integrity hash

    # Export settings
    export_config = Column(JSON)  # Export-specific settings

    # Performance metrics
    generation_time = Column(Float)  # Time taken to generate (seconds)
    data_rows = Column(Integer)  # Number of data rows processed

    # Scheduling information
    schedule_id = Column(
        UUID(as_uuid=True), ForeignKey("report_schedules.id"), nullable=True
    )
    is_scheduled = Column(Boolean, default=False)

    # Sharing and permissions
    is_public = Column(Boolean, default=False)
    shared_with = Column(JSON)  # User IDs with access
    download_count = Column(Integer, default=0)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)  # Auto-deletion date

    # Relationships
    template = relationship("ReportTemplate", back_populates="reports")
    creator = relationship("User", foreign_keys=[created_by])
    schedule = relationship("ReportSchedule", back_populates="reports")
    exports = relationship(
        "ReportExport", back_populates="report", cascade="all, delete-orphan"
    )


class ReportSchedule(Base):
    """Scheduled report generation"""

    __tablename__ = "report_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Schedule configuration
    template_id = Column(
        UUID(as_uuid=True), ForeignKey("report_templates.id"), nullable=False
    )
    frequency = Column(SQLEnum(ReportFrequency), nullable=False)
    cron_expression = Column(String(100))  # For custom frequencies

    # Schedule parameters
    parameters = Column(JSON)  # Default parameters for scheduled reports
    export_formats = Column(JSON, nullable=False)  # List of formats to generate

    # Recipients and delivery
    recipients = Column(JSON)  # Email addresses and user IDs
    delivery_method = Column(String(50), default="email")  # email, download, webhook
    webhook_url = Column(String(500))

    # Schedule status
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    run_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Retention settings
    max_reports = Column(Integer, default=10)  # Keep last N reports
    auto_delete_days = Column(Integer, default=30)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template = relationship("ReportTemplate", back_populates="schedules")
    creator = relationship("User", foreign_keys=[created_by])
    reports = relationship("Report", back_populates="schedule")


class ReportExport(Base):
    """Individual export instances for different formats"""

    __tablename__ = "report_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)

    # Export details
    format = Column(SQLEnum(ReportFormat), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(128))

    # Export configuration
    export_config = Column(JSON)  # Format-specific settings

    # Status and metrics
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    generation_time = Column(Float)
    download_count = Column(Integer, default=0)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    last_downloaded_at = Column(DateTime)

    # Relationships
    report = relationship("Report", back_populates="exports")


class ReportShare(Base):
    """Report sharing and access control"""

    __tablename__ = "report_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)

    # Sharing details
    shared_with_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    shared_with_email = Column(String(255))  # For external sharing
    share_token = Column(String(255), unique=True)  # Public access token

    # Permissions
    can_download = Column(Boolean, default=True)
    can_share = Column(Boolean, default=False)
    can_modify = Column(Boolean, default=False)

    # Access control
    access_count = Column(Integer, default=0)
    max_access_count = Column(Integer)  # Limit access
    expires_at = Column(DateTime)
    password_hash = Column(String(255))  # Optional password protection

    # Audit fields
    shared_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime)

    # Relationships
    report = relationship("Report")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by])


class ReportMetric(Base):
    """Report performance and usage metrics"""

    __tablename__ = "report_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)

    # Performance metrics
    query_time = Column(Float)  # Database query time
    processing_time = Column(Float)  # Data processing time
    rendering_time = Column(Float)  # Report rendering time
    total_time = Column(Float)  # Total generation time

    # Resource usage
    memory_usage = Column(Integer)  # Peak memory usage in MB
    cpu_usage = Column(Float)  # CPU usage percentage

    # Data metrics
    rows_processed = Column(Integer)
    queries_executed = Column(Integer)
    cache_hits = Column(Integer)
    cache_misses = Column(Integer)

    # Audit fields
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("Report")
