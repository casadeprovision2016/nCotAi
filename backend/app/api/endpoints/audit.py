"""
Audit and Security Monitoring endpoints
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.auth import get_current_user
from app.models.user import User, UserRole
from app.services.audit_service import AuditService

router = APIRouter()


# Pydantic models
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_path: Optional[str]
    request_method: Optional[str]
    details: Dict[str, Any]
    status: str
    timestamp: str
    duration_ms: Optional[int]
    severity: str


class AuditLogsListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    size: int
    pages: int


class SecurityDashboardResponse(BaseModel):
    period_days: int
    login_statistics: Dict[str, Any]
    security_events: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]
    geographic_distribution: Dict[str, int]
    failed_logins_by_ip: List[Dict[str, Any]]
    generated_at: str


def check_admin_access(current_user: User = Depends(get_current_user)):
    """Check if user has admin access for audit endpoints."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem acessar logs de auditoria.",
        )
    return current_user


@router.get("/logs", response_model=AuditLogsListResponse)
async def get_audit_logs(
    start_date: Optional[datetime] = Query(
        None, description="Data inicial (ISO format)"
    ),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO format)"),
    user_id: Optional[str] = Query(None, description="ID do usuário"),
    action: Optional[str] = Query(None, description="Ação realizada"),
    resource_type: Optional[str] = Query(None, description="Tipo de recurso"),
    status: Optional[str] = Query(None, description="Status da ação"),
    severity: Optional[str] = Query(None, description="Nível de severidade"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(50, ge=1, le=1000, description="Tamanho da página"),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get audit logs with filtering and pagination."""

    try:
        audit_service = AuditService(db)

        # Parse user_id if provided
        parsed_user_id = None
        if user_id:
            try:
                from uuid import UUID

                parsed_user_id = UUID(user_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID do usuário inválido",
                )

        result = await audit_service.get_audit_logs(
            user_id=parsed_user_id,
            start_date=start_date,
            end_date=end_date,
            action=action,
            resource_type=resource_type,
            status=status,
            severity=severity,
            page=page,
            size=size,
        )

        # Convert to response format
        logs = []
        for log_data in result["logs"]:
            logs.append(AuditLogResponse(**log_data))

        return AuditLogsListResponse(
            logs=logs,
            total=result["total"],
            page=result["page"],
            size=result["size"],
            pages=result["pages"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter logs de auditoria",
        )


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard(
    days: int = Query(7, ge=1, le=90, description="Número de dias para análise"),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get security dashboard with statistics and alerts."""

    try:
        audit_service = AuditService(db)
        dashboard_data = await audit_service.get_security_dashboard(days=days)

        return SecurityDashboardResponse(**dashboard_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar dashboard de segurança",
        )


@router.get("/user-activity/{user_id}")
async def get_user_activity(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Número de dias para análise"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get activity logs for specific user."""

    try:
        from uuid import UUID

        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ID do usuário inválido"
        )

    # Check permissions
    if (
        current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
        and current_user.id != target_user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você só pode ver sua própria atividade.",
        )

    try:
        audit_service = AuditService(db)

        start_date = datetime.utcnow() - timedelta(days=days)
        result = await audit_service.get_audit_logs(
            user_id=target_user_id,
            start_date=start_date,
            page=1,
            size=1000,  # Get more records for user activity
        )

        # Group by action type
        activity_summary = {}
        for log in result["logs"]:
            action = log["action"]
            activity_summary[action] = activity_summary.get(action, 0) + 1

        return {
            "user_id": user_id,
            "period_days": days,
            "total_activities": result["total"],
            "activity_summary": activity_summary,
            "recent_activities": result["logs"][:50],  # Last 50 activities
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter atividade do usuário",
        )


@router.get("/security-alerts")
async def get_security_alerts(
    hours: int = Query(24, ge=1, le=168, description="Horas para buscar alertas"),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get recent security alerts."""

    try:
        audit_service = AuditService(db)

        start_date = datetime.utcnow() - timedelta(hours=hours)

        # Get security-related logs
        result = await audit_service.get_audit_logs(
            start_date=start_date, status="SECURITY_INCIDENT", page=1, size=100
        )

        # Also get security warnings
        warnings_result = await audit_service.get_audit_logs(
            start_date=start_date, status="SECURITY_WARNING", page=1, size=100
        )

        all_alerts = result["logs"] + warnings_result["logs"]

        # Sort by timestamp
        all_alerts.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "period_hours": hours,
            "total_alerts": len(all_alerts),
            "alerts": all_alerts[:50],  # Return top 50 alerts
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter alertas de segurança",
        )


@router.get("/compliance-report")
async def generate_compliance_report(
    start_date: datetime = Query(..., description="Data inicial (ISO format)"),
    end_date: datetime = Query(..., description="Data final (ISO format)"),
    format_type: str = Query("json", description="Formato do relatório"),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Generate compliance report for auditing."""

    try:
        audit_service = AuditService(db)

        report_data = await audit_service.export_compliance_report(
            start_date=start_date, end_date=end_date, format_type=format_type
        )

        return report_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar relatório de compliance",
        )


@router.get("/login-attempts")
async def get_login_attempts(
    email: Optional[str] = Query(None, description="Email para filtrar"),
    ip_address: Optional[str] = Query(None, description="IP para filtrar"),
    success: Optional[bool] = Query(None, description="Filtrar por sucesso/falha"),
    hours: int = Query(24, ge=1, le=720, description="Horas para buscar tentativas"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get login attempts with filtering."""

    try:
        from sqlalchemy import and_, desc

        from app.models.user import LoginAttempt

        # Build query
        query = db.query(LoginAttempt)

        # Apply time filter
        start_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(LoginAttempt.attempted_at >= start_time)

        # Apply filters
        if email:
            query = query.filter(LoginAttempt.email.ilike(f"%{email}%"))

        if ip_address:
            query = query.filter(LoginAttempt.ip_address == ip_address)

        if success is not None:
            query = query.filter(LoginAttempt.success == success)

        # Get total count
        total = query.count()

        # Apply pagination
        attempts = (
            query.order_by(desc(LoginAttempt.attempted_at))
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        # Format response
        attempts_data = []
        for attempt in attempts:
            attempts_data.append(
                {
                    "id": str(attempt.id),
                    "email": attempt.email,
                    "ip_address": attempt.ip_address,
                    "user_agent": attempt.user_agent,
                    "success": attempt.success,
                    "failure_reason": attempt.failure_reason,
                    "attempted_at": attempt.attempted_at.isoformat(),
                    "details": attempt.details,
                }
            )

        return {
            "attempts": attempts_data,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
            "period_hours": hours,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter tentativas de login",
        )


@router.get("/statistics")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="Número de dias para estatísticas"),
    current_user: User = Depends(check_admin_access),
    db: Session = Depends(get_db),
):
    """Get comprehensive audit statistics."""

    try:
        from sqlalchemy import and_, func

        from app.models.user import AuditLog, LoginAttempt

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get audit log statistics
        audit_stats = (
            db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
            .filter(AuditLog.timestamp >= start_date)
            .group_by(AuditLog.action)
            .all()
        )

        # Get status distribution
        status_stats = (
            db.query(AuditLog.status, func.count(AuditLog.id).label("count"))
            .filter(AuditLog.timestamp >= start_date)
            .group_by(AuditLog.status)
            .all()
        )

        # Get resource type distribution
        resource_stats = (
            db.query(AuditLog.resource_type, func.count(AuditLog.id).label("count"))
            .filter(
                and_(
                    AuditLog.timestamp >= start_date, AuditLog.resource_type.isnot(None)
                )
            )
            .group_by(AuditLog.resource_type)
            .all()
        )

        # Get daily activity
        daily_activity = (
            db.query(
                func.date(AuditLog.timestamp).label("date"),
                func.count(AuditLog.id).label("count"),
            )
            .filter(AuditLog.timestamp >= start_date)
            .group_by(func.date(AuditLog.timestamp))
            .all()
        )

        return {
            "period_days": days,
            "action_distribution": {action: count for action, count in audit_stats},
            "status_distribution": {status: count for status, count in status_stats},
            "resource_distribution": {
                resource: count for resource, count in resource_stats
            },
            "daily_activity": [
                {"date": date.isoformat(), "count": count}
                for date, count in daily_activity
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter estatísticas de auditoria",
        )
