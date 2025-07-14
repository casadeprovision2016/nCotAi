"""
Report API endpoints for generation, export, and management
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.auth import get_current_user
from app.models.report import (
    Report,
    ReportExport,
    ReportFormat,
    ReportFrequency,
    ReportSchedule,
    ReportStatus,
    ReportTemplate,
    ReportType,
)
from app.models.user import User
from app.services.report_service import ReportGenerationError, get_report_service

router = APIRouter()


# Pydantic models
class ReportCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    type: ReportType
    formats: List[ReportFormat] = Field(..., min_items=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ReportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: ReportType
    query_config: Dict[str, Any]
    layout_config: Dict[str, Any]
    chart_config: Optional[Dict[str, Any]] = None
    field_mappings: Dict[str, Any]
    is_public: bool = False
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ReportScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: UUID
    frequency: ReportFrequency
    cron_expression: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    export_formats: List[ReportFormat] = Field(..., min_items=1)
    recipients: List[str] = Field(..., min_items=1)
    delivery_method: str = "email"
    max_reports: int = Field(default=10, ge=1, le=100)
    auto_delete_days: int = Field(default=30, ge=1, le=365)


class ReportResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: ReportType
    status: ReportStatus
    progress: int
    error_message: Optional[str]
    data_rows: Optional[int]
    generation_time: Optional[float]
    created_by: UUID
    requested_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    exports: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    reports: List[ReportResponse]
    total: int
    page: int
    size: int


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new report with specified formats"""

    try:
        report_service = await get_report_service(db)

        # Generate report in background
        report = await report_service.generate_report(
            template_id=request.template_id,
            user_id=current_user.id,
            name=request.name,
            report_type=request.type,
            parameters=request.parameters,
            formats=request.formats,
        )

        # Convert to response format
        exports_data = []
        for export in report.exports:
            exports_data.append(
                {
                    "id": export.id,
                    "format": export.format.value,
                    "status": export.status.value,
                    "file_size": export.file_size,
                    "download_count": export.download_count,
                    "created_at": export.created_at,
                }
            )

        return ReportResponse(
            id=report.id,
            name=report.name,
            description=request.description,
            type=report.type,
            status=report.status,
            progress=100 if report.status == ReportStatus.COMPLETED else 0,
            error_message=report.error_message,
            data_rows=report.data_rows,
            generation_time=report.generation_time,
            created_by=report.created_by,
            requested_at=report.requested_at,
            started_at=report.started_at,
            completed_at=report.completed_at,
            exports=exports_data,
        )

    except ReportGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    type_filter: Optional[ReportType] = Query(None),
    status_filter: Optional[ReportStatus] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's reports with filtering and pagination"""

    query = db.query(Report).filter(Report.created_by == current_user.id)

    # Apply filters
    if type_filter:
        query = query.filter(Report.type == type_filter)

    if status_filter:
        query = query.filter(Report.status == status_filter)

    if search:
        query = query.filter(Report.name.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    reports = (
        query.order_by(Report.requested_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # Convert to response format
    reports_data = []
    for report in reports:
        exports_data = []
        for export in report.exports:
            exports_data.append(
                {
                    "id": export.id,
                    "format": export.format.value,
                    "status": export.status.value,
                    "file_size": export.file_size,
                    "download_count": export.download_count,
                    "created_at": export.created_at,
                }
            )

        reports_data.append(
            ReportResponse(
                id=report.id,
                name=report.name,
                description=report.description,
                type=report.type,
                status=report.status,
                progress=100 if report.status == ReportStatus.COMPLETED else 0,
                error_message=report.error_message,
                data_rows=report.data_rows,
                generation_time=report.generation_time,
                created_by=report.created_by,
                requested_at=report.requested_at,
                started_at=report.started_at,
                completed_at=report.completed_at,
                exports=exports_data,
            )
        )

    return ReportListResponse(reports=reports_data, total=total, page=page, size=size)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific report details"""

    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.created_by == current_user.id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert to response format
    exports_data = []
    for export in report.exports:
        exports_data.append(
            {
                "id": export.id,
                "format": export.format.value,
                "status": export.status.value,
                "file_size": export.file_size,
                "download_count": export.download_count,
                "created_at": export.created_at,
            }
        )

    return ReportResponse(
        id=report.id,
        name=report.name,
        description=report.description,
        type=report.type,
        status=report.status,
        progress=100 if report.status == ReportStatus.COMPLETED else 0,
        error_message=report.error_message,
        data_rows=report.data_rows,
        generation_time=report.generation_time,
        created_by=report.created_by,
        requested_at=report.requested_at,
        started_at=report.started_at,
        completed_at=report.completed_at,
        exports=exports_data,
    )


@router.get("/{report_id}/download/{format}")
async def download_report(
    report_id: UUID,
    format: ReportFormat,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a report in specified format"""

    # Verify report ownership
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.created_by == current_user.id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get file path
    report_service = await get_report_service(db)
    file_path = await report_service.get_report_file(report_id, format)

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    # Determine content type
    content_types = {
        ReportFormat.PDF: "application/pdf",
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.CSV: "text/csv",
        ReportFormat.JSON: "application/json",
        ReportFormat.XML: "application/xml",
        ReportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    content_type = content_types.get(format, "application/octet-stream")

    return FileResponse(
        path=str(file_path), media_type=content_type, filename=file_path.name
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a report and its files"""

    report_service = await get_report_service(db)
    success = await report_service.delete_report(report_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=404, detail="Report not found or cannot be deleted"
        )

    return {"message": "Report deleted successfully"}


# Template endpoints
@router.get("/templates/", response_model=List[Dict[str, Any]])
async def list_templates(
    type_filter: Optional[ReportType] = Query(None),
    include_system: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List available report templates"""

    query = db.query(ReportTemplate).filter(
        (ReportTemplate.is_public == True)
        | (ReportTemplate.created_by == current_user.id)
    )

    if type_filter:
        query = query.filter(ReportTemplate.type == type_filter)

    if include_system:
        query = query.filter(ReportTemplate.is_system == True)

    templates = query.order_by(ReportTemplate.name).all()

    result = []
    for template in templates:
        result.append(
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "type": template.type.value,
                "category": template.category,
                "tags": template.tags,
                "is_public": template.is_public,
                "is_system": template.is_system,
                "version": template.version,
                "created_at": template.created_at,
            }
        )

    return result


@router.post("/templates/", response_model=Dict[str, Any])
async def create_template(
    request: ReportTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new report template"""

    template = ReportTemplate(
        name=request.name,
        description=request.description,
        type=request.type,
        query_config=request.query_config,
        layout_config=request.layout_config,
        chart_config=request.chart_config,
        field_mappings=request.field_mappings,
        is_public=request.is_public,
        category=request.category,
        tags=request.tags,
        created_by=current_user.id,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "type": template.type.value,
        "created_at": template.created_at,
    }


# Report statistics
@router.get("/stats/summary")
async def get_report_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get report generation statistics"""

    date_from = datetime.utcnow() - timedelta(days=days)

    # Get basic counts
    total_reports = (
        db.query(Report)
        .filter(Report.created_by == current_user.id, Report.requested_at >= date_from)
        .count()
    )

    completed_reports = (
        db.query(Report)
        .filter(
            Report.created_by == current_user.id,
            Report.requested_at >= date_from,
            Report.status == ReportStatus.COMPLETED,
        )
        .count()
    )

    failed_reports = (
        db.query(Report)
        .filter(
            Report.created_by == current_user.id,
            Report.requested_at >= date_from,
            Report.status == ReportStatus.FAILED,
        )
        .count()
    )

    # Get format popularity
    format_stats = (
        db.query(ReportExport.format, db.func.count(ReportExport.id))
        .join(Report)
        .filter(Report.created_by == current_user.id, Report.requested_at >= date_from)
        .group_by(ReportExport.format)
        .all()
    )

    format_counts = {format_type.value: count for format_type, count in format_stats}

    # Get type popularity
    type_stats = (
        db.query(Report.type, db.func.count(Report.id))
        .filter(Report.created_by == current_user.id, Report.requested_at >= date_from)
        .group_by(Report.type)
        .all()
    )

    type_counts = {report_type.value: count for report_type, count in type_stats}

    return {
        "period_days": days,
        "total_reports": total_reports,
        "completed_reports": completed_reports,
        "failed_reports": failed_reports,
        "success_rate": round(
            (completed_reports / total_reports * 100) if total_reports > 0 else 0, 2
        ),
        "format_popularity": format_counts,
        "type_popularity": type_counts,
    }
