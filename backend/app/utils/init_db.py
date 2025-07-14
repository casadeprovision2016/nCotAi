"""
Database initialization utilities
"""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def init_db() -> None:
    """Initialize database with initial data."""
    db = SessionLocal()

    try:
        # Create first superuser if it doesn't exist
        user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                first_name="Super",
                last_name="Admin",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Superuser created: {settings.FIRST_SUPERUSER}")
        else:
            print(f"Superuser already exists: {settings.FIRST_SUPERUSER}")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
