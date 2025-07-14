"""
Tender service layer - Business logic for tender operations
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, extract, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.tender import GovernmentEntity as GovernmentEntityModel
from app.models.tender import Tender as TenderModel
from app.models.tender import TenderCategory as TenderCategoryModel
from app.models.tender import TenderModalityType, TenderStatus, TenderType
from app.schemas.tender import (
    GovernmentEntityCreate,
    GovernmentEntityUpdate,
    TenderCategoryCreate,
    TenderCategoryUpdate,
    TenderCreate,
    TenderSearchParams,
    TenderSearchResponse,
    TenderSummary,
    TenderUpdate,
)


class TenderService:
    """Service class for tender-related operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_tender(self, tender_data: TenderCreate) -> TenderModel:
        """Create a new tender."""
        tender = TenderModel(**tender_data.dict())
        self.db.add(tender)
        self.db.commit()
        self.db.refresh(tender)
        return tender

    def get_tender(self, tender_id: UUID) -> Optional[TenderModel]:
        """Get tender by ID with all related data."""
        return (
            self.db.query(TenderModel)
            .options(
                joinedload(TenderModel.government_entity),
                joinedload(TenderModel.category),
            )
            .filter(TenderModel.id == tender_id)
            .first()
        )

    def update_tender(
        self, tender_id: UUID, tender_data: TenderUpdate
    ) -> Optional[TenderModel]:
        """Update tender."""
        tender = self.db.query(TenderModel).filter(TenderModel.id == tender_id).first()
        if not tender:
            return None

        for field, value in tender_data.dict(exclude_unset=True).items():
            setattr(tender, field, value)

        tender.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tender)
        return tender

    def delete_tender(self, tender_id: UUID) -> bool:
        """Delete tender."""
        tender = self.db.query(TenderModel).filter(TenderModel.id == tender_id).first()
        if not tender:
            return False

        self.db.delete(tender)
        self.db.commit()
        return True

    def search_tenders(self, search_params: TenderSearchParams) -> TenderSearchResponse:
        """Search tenders with filters and pagination."""
        query = self.db.query(TenderModel).options(
            joinedload(TenderModel.government_entity),
            joinedload(TenderModel.category),
        )

        # Apply filters
        if search_params.filters:
            if search_params.filters.search:
                search_term = f"%{search_params.filters.search}%"
                query = query.filter(
                    or_(
                        TenderModel.title.ilike(search_term),
                        TenderModel.description.ilike(search_term),
                        TenderModel.notice_number.ilike(search_term),
                    )
                )

            if search_params.filters.modality:
                query = query.filter(
                    TenderModel.modality.in_(search_params.filters.modality)
                )

            if search_params.filters.status:
                query = query.filter(
                    TenderModel.status.in_(search_params.filters.status)
                )

            if search_params.filters.government_entity_id:
                query = query.filter(
                    TenderModel.government_entity_id.in_(
                        search_params.filters.government_entity_id
                    )
                )

            if search_params.filters.category_id:
                query = query.filter(
                    TenderModel.category_id.in_(search_params.filters.category_id)
                )

            if search_params.filters.min_value is not None:
                query = query.filter(
                    TenderModel.estimated_value >= search_params.filters.min_value
                )

            if search_params.filters.max_value is not None:
                query = query.filter(
                    TenderModel.estimated_value <= search_params.filters.max_value
                )

        # Count total items
        total_items = query.count()

        # Apply sorting
        sort_column = getattr(
            TenderModel, search_params.sort_by, TenderModel.created_at
        )
        if search_params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (search_params.page - 1) * search_params.page_size
        tenders = query.offset(offset).limit(search_params.page_size).all()

        # Calculate pagination info
        total_pages = (
            total_items + search_params.page_size - 1
        ) // search_params.page_size

        return TenderSearchResponse(
            items=[TenderSummary.from_orm(tender) for tender in tenders],
            total_items=total_items,
            total_pages=total_pages,
            current_page=search_params.page,
            page_size=search_params.page_size,
        )

    def toggle_monitor(self, tender_id: UUID) -> Optional[TenderModel]:
        """Toggle tender monitoring status."""
        tender = self.db.query(TenderModel).filter(TenderModel.id == tender_id).first()
        if not tender:
            return None

        tender.is_monitored = not tender.is_monitored
        tender.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tender)
        return tender

    def toggle_favorite(self, tender_id: UUID) -> Optional[TenderModel]:
        """Toggle tender favorite status."""
        tender = self.db.query(TenderModel).filter(TenderModel.id == tender_id).first()
        if not tender:
            return None

        tender.is_favorite = not tender.is_favorite
        tender.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tender)
        return tender

    # Government Entity methods
    def list_government_entities(
        self, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> List[GovernmentEntityModel]:
        """List government entities with optional search."""
        query = self.db.query(GovernmentEntityModel)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    GovernmentEntityModel.name.ilike(search_term),
                    GovernmentEntityModel.acronym.ilike(search_term),
                )
            )

        return query.offset(skip).limit(limit).all()

    def create_government_entity(
        self, entity_data: GovernmentEntityCreate
    ) -> GovernmentEntityModel:
        """Create a new government entity."""
        entity = GovernmentEntityModel(**entity_data.dict())
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_government_entity(self, entity_id: UUID) -> Optional[GovernmentEntityModel]:
        """Get government entity by ID."""
        return (
            self.db.query(GovernmentEntityModel)
            .filter(GovernmentEntityModel.id == entity_id)
            .first()
        )

    def update_government_entity(
        self, entity_id: UUID, entity_data: GovernmentEntityUpdate
    ) -> Optional[GovernmentEntityModel]:
        """Update government entity."""
        entity = (
            self.db.query(GovernmentEntityModel)
            .filter(GovernmentEntityModel.id == entity_id)
            .first()
        )
        if not entity:
            return None

        for field, value in entity_data.dict(exclude_unset=True).items():
            setattr(entity, field, value)

        entity.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    # Tender Category methods
    def list_tender_categories(
        self, parent_id: Optional[UUID] = None
    ) -> List[TenderCategoryModel]:
        """List tender categories, optionally filtered by parent."""
        query = self.db.query(TenderCategoryModel)
        if parent_id:
            query = query.filter(TenderCategoryModel.parent_id == parent_id)
        else:
            query = query.filter(TenderCategoryModel.parent_id.is_(None))

        return query.order_by(TenderCategoryModel.name).all()

    def create_tender_category(
        self, category_data: TenderCategoryCreate
    ) -> TenderCategoryModel:
        """Create a new tender category."""
        category = TenderCategoryModel(**category_data.dict())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_tender_category(self, category_id: UUID) -> Optional[TenderCategoryModel]:
        """Get tender category by ID."""
        return (
            self.db.query(TenderCategoryModel)
            .filter(TenderCategoryModel.id == category_id)
            .first()
        )

    def update_tender_category(
        self, category_id: UUID, category_data: TenderCategoryUpdate
    ) -> Optional[TenderCategoryModel]:
        """Update tender category."""
        category = (
            self.db.query(TenderCategoryModel)
            .filter(TenderCategoryModel.id == category_id)
            .first()
        )
        if not category:
            return None

        for field, value in category_data.dict(exclude_unset=True).items():
            setattr(category, field, value)

        category.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(category)
        return category

    # Statistics methods
    def get_tender_statistics(self) -> Dict[str, Any]:
        """Get basic tender statistics."""
        total_tenders = self.db.query(TenderModel).count()

        # Count by status
        status_counts = (
            self.db.query(TenderModel.status, func.count(TenderModel.id))
            .group_by(TenderModel.status)
            .all()
        )

        # Recent tenders (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_tenders = (
            self.db.query(TenderModel)
            .filter(TenderModel.created_at >= thirty_days_ago)
            .count()
        )

        # Monitored tenders
        monitored_tenders = (
            self.db.query(TenderModel).filter(TenderModel.is_monitored == True).count()
        )

        # Total estimated value
        total_value = self.db.query(func.sum(TenderModel.estimated_value)).scalar() or 0

        return {
            "total_tenders": total_tenders,
            "status_distribution": {status: count for status, count in status_counts},
            "recent_tenders": recent_tenders,
            "monitored_tenders": monitored_tenders,
            "total_estimated_value": float(total_value),
        }

    def get_tenders_by_modality(self) -> Dict[str, int]:
        """Get tender count by modality."""
        modality_counts = (
            self.db.query(TenderModel.modality, func.count(TenderModel.id))
            .group_by(TenderModel.modality)
            .all()
        )

        return {modality.value: count for modality, count in modality_counts}

    def get_tenders_by_month(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get tender statistics by month for the last N months."""
        start_date = datetime.utcnow() - timedelta(days=30 * months)

        monthly_data = (
            self.db.query(
                extract("year", TenderModel.created_at).label("year"),
                extract("month", TenderModel.created_at).label("month"),
                func.count(TenderModel.id).label("count"),
                func.sum(TenderModel.estimated_value).label("total_value"),
            )
            .filter(TenderModel.created_at >= start_date)
            .group_by(
                extract("year", TenderModel.created_at),
                extract("month", TenderModel.created_at),
            )
            .order_by(
                extract("year", TenderModel.created_at),
                extract("month", TenderModel.created_at),
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
