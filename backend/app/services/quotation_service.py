"""
Quotation service layer - Business logic for quotation operations
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.quotation import Quotation as QuotationModel
from app.models.quotation import QuotationItem as QuotationItemModel
from app.models.quotation import QuotationPriority
from app.models.quotation import QuotationStatus
from app.models.quotation import Supplier as SupplierModel
# from app.models.quotation import SupplierQuote as SupplierQuoteModel  # Not implemented yet
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationSearchParams,
    QuotationSearchResponse,
    QuotationSummary,
    QuotationUpdate,
    SupplierCreate,
    SupplierUpdate,
    ItemStatus,
)


class QuotationService:
    """Service class for quotation-related operations."""

    def __init__(self, db: Session):
        self.db = db

    # Quotation methods
    def create_quotation(
        self, quotation_data: QuotationCreate, created_by: UUID
    ) -> QuotationModel:
        """Create a new quotation."""
        quotation_dict = quotation_data.dict()
        quotation_dict["created_by"] = created_by

        quotation = QuotationModel(**quotation_dict)
        self.db.add(quotation)
        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def get_quotation(self, quotation_id: UUID) -> Optional[QuotationModel]:
        """Get quotation by ID with all related data."""
        return (
            self.db.query(QuotationModel)
            .options(
                joinedload(QuotationModel.items),
                joinedload(QuotationModel.suppliers),
            )
            .filter(QuotationModel.id == quotation_id)
            .first()
        )

    def update_quotation(
        self, quotation_id: UUID, quotation_data: QuotationUpdate
    ) -> Optional[QuotationModel]:
        """Update quotation."""
        quotation = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.id == quotation_id)
            .first()
        )
        if not quotation:
            return None

        for field, value in quotation_data.dict(exclude_unset=True).items():
            setattr(quotation, field, value)

        quotation.updated_at = datetime.utcnow()
        self._update_quotation_totals(quotation)
        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    def delete_quotation(self, quotation_id: UUID) -> bool:
        """Delete quotation."""
        quotation = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.id == quotation_id)
            .first()
        )
        if not quotation:
            return False

        self.db.delete(quotation)
        self.db.commit()
        return True

    def search_quotations(
        self, search_params: QuotationSearchParams
    ) -> QuotationSearchResponse:
        """Search quotations with filters and pagination."""
        query = self.db.query(QuotationModel)

        # Apply filters
        if search_params.filters:
            if search_params.filters.search:
                search_term = f"%{search_params.filters.search}%"
                query = query.filter(
                    or_(
                        QuotationModel.title.ilike(search_term),
                        QuotationModel.description.ilike(search_term),
                    )
                )

            if search_params.filters.status:
                query = query.filter(
                    QuotationModel.status.in_(search_params.filters.status)
                )

            if search_params.filters.priority:
                query = query.filter(
                    QuotationModel.priority.in_(search_params.filters.priority)
                )

            if search_params.filters.tender_id:
                query = query.filter(
                    QuotationModel.tender_id.in_(search_params.filters.tender_id)
                )

            if search_params.filters.created_by:
                query = query.filter(
                    QuotationModel.created_by.in_(search_params.filters.created_by)
                )

            if search_params.filters.deadline_from:
                query = query.filter(
                    QuotationModel.deadline >= search_params.filters.deadline_from
                )

            if search_params.filters.deadline_to:
                query = query.filter(
                    QuotationModel.deadline <= search_params.filters.deadline_to
                )

            if search_params.filters.min_value is not None:
                query = query.filter(
                    QuotationModel.total_value >= search_params.filters.min_value
                )

            if search_params.filters.max_value is not None:
                query = query.filter(
                    QuotationModel.total_value <= search_params.filters.max_value
                )

        # Count total items
        total_items = query.count()

        # Apply sorting
        sort_column = getattr(
            QuotationModel, search_params.sort_by, QuotationModel.created_at
        )
        if search_params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (search_params.page - 1) * search_params.page_size
        quotations = query.offset(offset).limit(search_params.page_size).all()

        # Calculate pagination info
        total_pages = (
            total_items + search_params.page_size - 1
        ) // search_params.page_size

        return QuotationSearchResponse(
            items=[QuotationSummary.from_orm(quotation) for quotation in quotations],
            total_items=total_items,
            total_pages=total_pages,
            current_page=search_params.page,
            page_size=search_params.page_size,
        )

    # QuotationItem methods
    def list_quotation_items(self, quotation_id: UUID) -> List[QuotationItemModel]:
        """List items for a quotation."""
        return (
            self.db.query(QuotationItemModel)
            .filter(QuotationItemModel.quotation_id == quotation_id)
            .order_by(QuotationItemModel.created_at)
            .all()
        )

    def create_quotation_item(
        self, item_data: QuotationItemCreate
    ) -> QuotationItemModel:
        """Create a new quotation item."""
        item = QuotationItemModel(**item_data.dict())

        # Calculate total estimated value
        if item.estimated_price and item.quantity:
            item.total_estimated_value = item.estimated_price * item.quantity

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        # Update quotation totals
        quotation = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.id == item.quotation_id)
            .first()
        )
        if quotation:
            self._update_quotation_totals(quotation)
            self.db.commit()

        return item

    def get_quotation_item(self, item_id: UUID) -> Optional[QuotationItemModel]:
        """Get quotation item by ID."""
        return (
            self.db.query(QuotationItemModel)
            .filter(QuotationItemModel.id == item_id)
            .first()
        )

    def update_quotation_item(
        self, item_id: UUID, item_data: QuotationItemUpdate
    ) -> Optional[QuotationItemModel]:
        """Update quotation item."""
        item = (
            self.db.query(QuotationItemModel)
            .filter(QuotationItemModel.id == item_id)
            .first()
        )
        if not item:
            return None

        for field, value in item_data.dict(exclude_unset=True).items():
            setattr(item, field, value)

        # Recalculate total estimated value
        if item.estimated_price and item.quantity:
            item.total_estimated_value = item.estimated_price * item.quantity

        item.updated_at = datetime.utcnow()
        self.db.commit()

        # Update quotation totals
        quotation = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.id == item.quotation_id)
            .first()
        )
        if quotation:
            self._update_quotation_totals(quotation)
            self.db.commit()

        self.db.refresh(item)
        return item

    def delete_quotation_item(self, item_id: UUID, quotation_id: UUID) -> bool:
        """Delete quotation item."""
        item = (
            self.db.query(QuotationItemModel)
            .filter(
                and_(
                    QuotationItemModel.id == item_id,
                    QuotationItemModel.quotation_id == quotation_id,
                )
            )
            .first()
        )

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()

        # Update quotation totals
        quotation = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.id == quotation_id)
            .first()
        )
        if quotation:
            self._update_quotation_totals(quotation)
            self.db.commit()

        return True

    # Supplier methods
    def list_suppliers(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> List[SupplierModel]:
        """List suppliers with optional search."""
        query = self.db.query(SupplierModel)

        if active_only:
            query = query.filter(SupplierModel.is_active == True)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    SupplierModel.name.ilike(search_term),
                    SupplierModel.email.ilike(search_term),
                )
            )

        return query.offset(skip).limit(limit).all()

    def create_supplier(
        self, supplier_data: SupplierCreate, created_by: UUID
    ) -> SupplierModel:
        """Create a new supplier."""
        supplier_dict = supplier_data.dict()
        supplier_dict["created_by"] = created_by

        supplier = SupplierModel(**supplier_dict)
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def get_supplier(self, supplier_id: UUID) -> Optional[SupplierModel]:
        """Get supplier by ID."""
        return (
            self.db.query(SupplierModel).filter(SupplierModel.id == supplier_id).first()
        )

    def update_supplier(
        self, supplier_id: UUID, supplier_data: SupplierUpdate
    ) -> Optional[SupplierModel]:
        """Update supplier."""
        supplier = (
            self.db.query(SupplierModel).filter(SupplierModel.id == supplier_id).first()
        )
        if not supplier:
            return None

        for field, value in supplier_data.dict(exclude_unset=True).items():
            setattr(supplier, field, value)

        supplier.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    # QuotationResponse methods
    def list_item_responses(self, item_id: UUID):
        """List responses for a quotation item."""
        # TODO: Implement QuotationResponse model and relationships
        return []

    def create_quotation_response(self, response_data):
        """Create a new quotation response."""
        # TODO: Implement QuotationResponse model and creation logic
        raise NotImplementedError("QuotationResponse model not implemented yet")

    def update_quotation_response(self, response_id: UUID, response_data):
        """Update quotation response."""
        # TODO: Implement QuotationResponse model and update logic
        raise NotImplementedError("QuotationResponse model not implemented yet")

    def select_quotation_response(self, response_id: UUID, item_id: UUID):
        """Select a quotation response and deselect others for the same item."""
        # TODO: Implement QuotationResponse model and selection logic
        raise NotImplementedError("QuotationResponse model not implemented yet")

    # Statistics methods
    def get_quotation_statistics(self) -> Dict[str, Any]:
        """Get basic quotation statistics."""
        total_quotations = self.db.query(QuotationModel).count()

        # Count by status
        status_counts = (
            self.db.query(QuotationModel.status, func.count(QuotationModel.id))
            .group_by(QuotationModel.status)
            .all()
        )

        # Recent quotations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_quotations = (
            self.db.query(QuotationModel)
            .filter(QuotationModel.created_at >= thirty_days_ago)
            .count()
        )

        # Total value
        total_value = self.db.query(func.sum(QuotationModel.total_value)).scalar() or 0

        # Active suppliers
        active_suppliers = (
            self.db.query(SupplierModel).filter(SupplierModel.is_active == True).count()
        )

        return {
            "total_quotations": total_quotations,
            "status_distribution": {
                status.value: count for status, count in status_counts
            },
            "recent_quotations": recent_quotations,
            "total_estimated_value": float(total_value),
            "active_suppliers": active_suppliers,
        }

    def get_quotations_by_status(self) -> Dict[str, int]:
        """Get quotation count by status."""
        status_counts = (
            self.db.query(QuotationModel.status, func.count(QuotationModel.id))
            .group_by(QuotationModel.status)
            .all()
        )

        return {status.value: count for status, count in status_counts}

    def get_quotations_by_month(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get quotation statistics by month for the last N months."""
        start_date = datetime.utcnow() - timedelta(days=30 * months)

        monthly_data = (
            self.db.query(
                extract("year", QuotationModel.created_at).label("year"),
                extract("month", QuotationModel.created_at).label("month"),
                func.count(QuotationModel.id).label("count"),
                func.sum(QuotationModel.total_value).label("total_value"),
            )
            .filter(QuotationModel.created_at >= start_date)
            .group_by(
                extract("year", QuotationModel.created_at),
                extract("month", QuotationModel.created_at),
            )
            .order_by(
                extract("year", QuotationModel.created_at),
                extract("month", QuotationModel.created_at),
            )
            .all()
        )

        return [
            {
                "year": int(year),
                "month": int(month),
                "count": count,
                "total_value": float(total_value or 0),
            }
            for year, month, count, total_value in monthly_data
        ]

    # Helper methods
    def _update_quotation_totals(self, quotation: QuotationModel) -> None:
        """Update quotation totals based on items."""
        # Count items
        items_count = (
            self.db.query(func.count(QuotationItemModel.id))
            .filter(QuotationItemModel.quotation_id == quotation.id)
            .scalar()
            or 0
        )

        # Sum total estimated value
        total_value = self.db.query(
            func.sum(QuotationItemModel.total_estimated_value)
        ).filter(QuotationItemModel.quotation_id == quotation.id).scalar() or Decimal(
            "0"
        )

        # Count unique suppliers (placeholder until QuotationResponse is implemented)
        suppliers_count = 0

        quotation.items_count = items_count
        quotation.total_value = total_value
        quotation.suppliers_count = suppliers_count

    def _update_item_response_stats(self, item: QuotationItemModel) -> None:
        """Update item response statistics."""
        # TODO: Implement when QuotationResponse model is available
        item.responses_count = 0
        item.best_price = None
