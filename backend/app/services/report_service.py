"""
Report Generation and Export Service
Handles dynamic report creation, data processing, and multi-format export
"""
import asyncio
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union
from uuid import UUID

# TODO: Install missing dependencies for report generation
# import matplotlib.pyplot as plt
# import numpy as np
# import openpyxl
# import pandas as pd
# import seaborn as sns
# from docx import Document

# Temporarily disable report functionality until dependencies are installed
plt = None
np = None
openpyxl = None
pd = None
sns = None
Document = None
# from docx.shared import Inches
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4, letter
# from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

# More missing dependencies
Inches = None
colors = None
A4 = None
letter = None
ParagraphStyle = None
getSampleStyleSheet = None
# from reportlab.lib.units import inch
# from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# More reportlab dependencies
inch = None
Paragraph = None
SimpleDocTemplate = None
Spacer = None
Table = None
TableStyle = None
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.models.report import (
    Report,
    ReportExport,
    ReportFormat,
    ReportSchedule,
    ReportStatus,
    ReportTemplate,
    ReportType,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class ReportGenerationError(Exception):
    """Custom exception for report generation errors"""

    pass


class ReportService:
    """Service for generating and exporting reports"""

    def __init__(self, db: Session):
        self.db = db
        self.temp_dir = Path(tempfile.gettempdir()) / "cotai_reports"
        self.temp_dir.mkdir(exist_ok=True)
        self.reports_dir = Path(settings.REPORTS_STORAGE_PATH or "./storage/reports")
        self.reports_dir.mkdir(exist_ok=True)

    async def generate_report(
        self,
        template_id: Optional[UUID],
        user_id: UUID,
        name: str,
        report_type: ReportType,
        parameters: Dict[str, Any],
        formats: List[ReportFormat],
    ) -> Report:
        """Generate a new report with multiple export formats"""

        try:
            # Create report record
            report = Report(
                name=name,
                template_id=template_id,
                type=report_type,
                format=formats[0],  # Primary format
                parameters=parameters,
                status=ReportStatus.PROCESSING,
                created_by=user_id,
                started_at=datetime.utcnow(),
            )

            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)

            # Load template if provided
            template = None
            if template_id:
                template = (
                    self.db.query(ReportTemplate)
                    .filter(ReportTemplate.id == template_id)
                    .first()
                )
                if not template:
                    raise ReportGenerationError(f"Template {template_id} not found")

            # Generate data
            start_time = datetime.utcnow()
            data = await self._generate_report_data(report_type, parameters, template)

            # Create exports for each format
            exports = []
            for format_type in formats:
                export = await self._create_export(report, data, format_type, template)
                exports.append(export)

            # Update report status
            end_time = datetime.utcnow()
            generation_time = (end_time - start_time).total_seconds()

            report.status = ReportStatus.COMPLETED
            report.completed_at = end_time
            report.generation_time = generation_time
            report.data_rows = (
                len(data)
                if isinstance(data, list)
                else data.shape[0]
                if hasattr(data, "shape")
                else 0
            )

            self.db.commit()

            return report

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            if "report" in locals():
                report.status = ReportStatus.FAILED
                report.error_message = str(e)
                self.db.commit()
            raise ReportGenerationError(f"Failed to generate report: {str(e)}")

    async def _generate_report_data(
        self,
        report_type: ReportType,
        parameters: Dict[str, Any],
        template: Optional[ReportTemplate] = None,
    ) -> Union[Any, List[Dict], Dict]:  # TODO: Use Any  # TODO: Use pd.DataFrame when pandas is installed when pandas is installed
        """Generate the underlying data for the report"""

        if template and template.query_config:
            # Use template-defined queries
            return await self._execute_template_queries(template, parameters)

        # Use predefined report type queries
        if report_type == ReportType.LICITACOES:
            return await self._generate_licitacoes_data(parameters)
        elif report_type == ReportType.COTACOES:
            return await self._generate_cotacoes_data(parameters)
        elif report_type == ReportType.TAREFAS:
            return await self._generate_tarefas_data(parameters)
        elif report_type == ReportType.FINANCEIRO:
            return await self._generate_financeiro_data(parameters)
        elif report_type == ReportType.DESEMPENHO:
            return await self._generate_desempenho_data(parameters)
        elif report_type == ReportType.AUDITORIA:
            return await self._generate_auditoria_data(parameters)
        else:
            raise ReportGenerationError(f"Unsupported report type: {report_type}")

    async def _execute_template_queries(
        self, template: ReportTemplate, parameters: Dict[str, Any]
    ) -> Any:  # TODO: Use pd.DataFrame when pandas is installed
        """Execute queries defined in template configuration"""

        query_config = template.query_config
        main_query = query_config.get("main_query")

        if not main_query:
            raise ReportGenerationError("Template missing main query")

        # Replace parameters in query
        formatted_query = self._format_query(main_query, parameters)

        # Execute query
        result = self.db.execute(text(formatted_query))
        data = result.fetchall()
        columns = result.keys()

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data, columns=columns)

    def _format_query(self, query: str, parameters: Dict[str, Any]) -> str:
        """Safely format SQL query with parameters"""
        # Basic parameter substitution - in production, use proper parameter binding
        formatted_query = query
        for key, value in parameters.items():
            if isinstance(value, str):
                formatted_query = formatted_query.replace(f":{key}", f"'{value}'")
            else:
                formatted_query = formatted_query.replace(f":{key}", str(value))

        return formatted_query

    async def _generate_licitacoes_data(
        self, parameters: Dict[str, Any]
    ) -> Any:  # TODO: Use pd.DataFrame when pandas is installed
        """Generate licitações report data"""

        date_from = parameters.get("date_from", datetime.utcnow() - timedelta(days=30))
        date_to = parameters.get("date_to", datetime.utcnow())
        status = parameters.get("status")

        query = """
        SELECT 
            t.id,
            t.title,
            t.description,
            t.status,
            t.value_estimate,
            t.deadline,
            t.created_at,
            t.agency_name,
            t.modality,
            COUNT(q.id) as cotacoes_count
        FROM tenders t
        LEFT JOIN quotations q ON q.tender_id = t.id
        WHERE t.created_at BETWEEN :date_from AND :date_to
        """

        if status:
            query += f" AND t.status = '{status}'"

        query += " GROUP BY t.id ORDER BY t.created_at DESC"

        result = self.db.execute(
            text(query), {"date_from": date_from, "date_to": date_to}
        )

        data = result.fetchall()
        columns = result.keys()

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data, columns=columns)

    async def _generate_cotacoes_data(self, parameters: Dict[str, Any]) -> Any  # TODO: Use pd.DataFrame when pandas is installed:
        """Generate cotações report data"""

        date_from = parameters.get("date_from", datetime.utcnow() - timedelta(days=30))
        date_to = parameters.get("date_to", datetime.utcnow())

        query = """
        SELECT 
            q.id,
            q.title,
            q.status,
            q.total_value,
            q.profit_margin,
            q.delivery_time,
            q.created_at,
            q.updated_at,
            t.title as tender_title,
            t.agency_name,
            COUNT(qi.id) as items_count
        FROM quotations q
        LEFT JOIN tenders t ON t.id = q.tender_id
        LEFT JOIN quotation_items qi ON qi.quotation_id = q.id
        WHERE q.created_at BETWEEN :date_from AND :date_to
        GROUP BY q.id, t.id
        ORDER BY q.created_at DESC
        """

        result = self.db.execute(
            text(query), {"date_from": date_from, "date_to": date_to}
        )

        data = result.fetchall()
        columns = result.keys()

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data, columns=columns)

    async def _generate_tarefas_data(self, parameters: Dict[str, Any]) -> Any  # TODO: Use pd.DataFrame when pandas is installed:
        """Generate tarefas report data - placeholder for task management system"""

        # This would connect to your task management system
        # For now, return sample data
        data = {
            "id": ["task-1", "task-2", "task-3"],
            "title": ["Análise Edital ABC", "Cotação XYZ", "Revisão Proposta"],
            "status": ["completed", "in_progress", "pending"],
            "priority": ["high", "medium", "low"],
            "assigned_to": ["user1", "user2", "user1"],
            "created_at": [
                datetime.utcnow() - timedelta(days=5),
                datetime.utcnow() - timedelta(days=3),
                datetime.utcnow() - timedelta(days=1),
            ],
        }

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data)

    async def _generate_financeiro_data(
        self, parameters: Dict[str, Any]
    ) -> Any:  # TODO: Use pd.DataFrame when pandas is installed
        """Generate financial report data"""

        # Sample financial data - would connect to financial system
        data = {
            "month": ["2024-01", "2024-02", "2024-03"],
            "revenue": [150000, 180000, 220000],
            "costs": [120000, 140000, 160000],
            "profit": [30000, 40000, 60000],
            "profit_margin": [20.0, 22.2, 27.3],
        }

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data)

    async def _generate_desempenho_data(
        self, parameters: Dict[str, Any]
    ) -> Any:  # TODO: Use pd.DataFrame when pandas is installed
        """Generate performance report data"""

        # Sample performance metrics
        data = {
            "metric": [
                "Conversion Rate",
                "Avg Response Time",
                "Success Rate",
                "User Satisfaction",
            ],
            "value": [15.5, 2.3, 85.2, 4.2],
            "unit": ["%", "hours", "%", "/5"],
            "target": [20.0, 2.0, 90.0, 4.5],
            "status": ["Below", "Above", "Below", "Below"],
        }

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data)

    async def _generate_auditoria_data(
        self, parameters: Dict[str, Any]
    ) -> Any:  # TODO: Use pd.DataFrame when pandas is installed
        """Generate audit report data"""

        date_from = parameters.get("date_from", datetime.utcnow() - timedelta(days=30))
        date_to = parameters.get("date_to", datetime.utcnow())

        # This would query your audit log system
        query = """
        SELECT 
            al.id,
            al.action,
            al.entity_type,
            al.entity_id,
            al.old_values,
            al.new_values,
            al.created_at,
            u.full_name as user_name,
            u.email as user_email
        FROM audit_logs al
        LEFT JOIN users u ON u.id = al.user_id
        WHERE al.created_at BETWEEN :date_from AND :date_to
        ORDER BY al.created_at DESC
        """

        result = self.db.execute(
            text(query), {"date_from": date_from, "date_to": date_to}
        )

        data = result.fetchall()
        columns = result.keys()

        return Any  # TODO: Use pd.DataFrame when pandas is installed(data, columns=columns)

    async def _create_export(
        self,
        report: Report,
        data: Union[Any, List[Dict], Dict],  # TODO: Use pd.DataFrame when pandas is installed
        format_type: ReportFormat,
        template: Optional[ReportTemplate] = None,
    ) -> ReportExport:
        """Create an export file in the specified format"""

        start_time = datetime.utcnow()

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.name}_{timestamp}.{format_type.value}"
        file_path = self.reports_dir / str(report.id) / filename
        file_path.parent.mkdir(exist_ok=True)

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, list):
                df = Any  # TODO: Use pd.DataFrame when pandas is installed(data)
            elif isinstance(data, dict):
                df = Any  # TODO: Use pd.DataFrame when pandas is installed([data])
            else:
                df = data

            # Generate file based on format
            if format_type == ReportFormat.CSV:
                df.to_csv(file_path, index=False, encoding="utf-8")
            elif format_type == ReportFormat.EXCEL:
                await self._create_excel_export(df, file_path, template)
            elif format_type == ReportFormat.PDF:
                await self._create_pdf_export(df, file_path, template, report)
            elif format_type == ReportFormat.JSON:
                df.to_json(file_path, orient="records", date_format="iso")
            elif format_type == ReportFormat.XML:
                df.to_xml(file_path, index=False)
            elif format_type == ReportFormat.DOCX:
                await self._create_docx_export(df, file_path, template, report)
            else:
                raise ReportGenerationError(f"Unsupported format: {format_type}")

            # Calculate file hash and size
            file_size = file_path.stat().st_size
            file_hash = self._calculate_file_hash(file_path)

            # Create export record
            export = ReportExport(
                report_id=report.id,
                format=format_type,
                file_path=str(file_path),
                file_size=file_size,
                file_hash=file_hash,
                status=ReportStatus.COMPLETED,
                generation_time=(datetime.utcnow() - start_time).total_seconds(),
            )

            self.db.add(export)
            self.db.commit()

            return export

        except Exception as e:
            logger.error(f"Error creating {format_type} export: {str(e)}")
            raise ReportGenerationError(
                f"Failed to create {format_type} export: {str(e)}"
            )

    async def _create_excel_export(
        self,
        df: Any  # TODO: Use pd.DataFrame when pandas is installed,
        file_path: Path,
        template: Optional[ReportTemplate] = None,
    ):
        """Create Excel export with formatting"""

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Data", index=False)

            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets["Data"]

            # Apply formatting
            header_font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            header_fill = openpyxl.styles.PatternFill(
                start_color="366092", end_color="366092", fill_type="solid"
            )

            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

    async def _create_pdf_export(
        self,
        df: Any  # TODO: Use pd.DataFrame when pandas is installed,
        file_path: Path,
        template: Optional[ReportTemplate] = None,
        report: Report = None,
    ):
        """Create PDF export with professional formatting"""

        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )

        elements.append(Paragraph(report.name if report else "Report", title_style))
        elements.append(Spacer(1, 12))

        # Report info
        info_data = [
            ["Generated on:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")],
            ["Report Type:", report.type.value if report else "N/A"],
            ["Total Records:", str(len(df))],
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 3 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.grey),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("BACKGROUND", (1, 0), (1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Data table
        if not df.empty:
            # Limit rows for PDF (pagination would be better)
            display_df = df.head(50)

            # Convert DataFrame to table data
            table_data = [display_df.columns.tolist()]
            for _, row in display_df.iterrows():
                table_data.append(
                    [
                        str(cell)[:50] + ("..." if len(str(cell)) > 50 else "")
                        for cell in row
                    ]
                )

            data_table = Table(table_data)
            data_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(data_table)

            if len(df) > 50:
                elements.append(Spacer(1, 12))
                elements.append(
                    Paragraph(
                        f"Showing first 50 of {len(df)} records", styles["Normal"]
                    )
                )

        doc.build(elements)

    async def _create_docx_export(
        self,
        df: Any  # TODO: Use pd.DataFrame when pandas is installed,
        file_path: Path,
        template: Optional[ReportTemplate] = None,
        report: Report = None,
    ):
        """Create Word document export"""

        document = Document()

        # Title
        title = document.add_heading(report.name if report else "Report", 0)

        # Report info
        document.add_heading("Report Information", level=1)
        info_para = document.add_paragraph()
        info_para.add_run("Generated on: ").bold = True
        info_para.add_run(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
        info_para.add_run("\nReport Type: ").bold = True
        info_para.add_run(report.type.value if report else "N/A")
        info_para.add_run("\nTotal Records: ").bold = True
        info_para.add_run(str(len(df)))

        # Data table
        if not df.empty:
            document.add_heading("Data", level=1)

            # Limit rows for document
            display_df = df.head(100)

            table = document.add_table(rows=1, cols=len(display_df.columns))
            table.style = "Grid Table 4 - Accent 1"

            # Header row
            hdr_cells = table.rows[0].cells
            for i, column in enumerate(display_df.columns):
                hdr_cells[i].text = str(column)

            # Data rows
            for _, row in display_df.iterrows():
                row_cells = table.add_row().cells
                for i, cell_value in enumerate(row):
                    row_cells[i].text = str(cell_value)[:100]  # Limit cell content

        document.save(file_path)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def get_report_file(
        self, report_id: UUID, format_type: ReportFormat
    ) -> Optional[Path]:
        """Get the file path for a specific report export"""

        export = (
            self.db.query(ReportExport)
            .filter(
                ReportExport.report_id == report_id,
                ReportExport.format == format_type,
                ReportExport.status == ReportStatus.COMPLETED,
            )
            .first()
        )

        if export and Path(export.file_path).exists():
            # Update download count
            export.download_count += 1
            export.last_downloaded_at = datetime.utcnow()
            self.db.commit()

            return Path(export.file_path)

        return None

    async def delete_report(self, report_id: UUID, user_id: UUID) -> bool:
        """Delete a report and its associated files"""

        report = (
            self.db.query(Report)
            .filter(Report.id == report_id, Report.created_by == user_id)
            .first()
        )

        if not report:
            return False

        try:
            # Delete files
            for export in report.exports:
                file_path = Path(export.file_path)
                if file_path.exists():
                    file_path.unlink()

            # Delete report directory if empty
            report_dir = self.reports_dir / str(report_id)
            if report_dir.exists() and not list(report_dir.iterdir()):
                report_dir.rmdir()

            # Delete database records
            self.db.delete(report)
            self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {str(e)}")
            return False


async def get_report_service(db: Session = None) -> ReportService:
    """Get report service instance"""
    if db is None:
        db = next(get_db())
    return ReportService(db)
