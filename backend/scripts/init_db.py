#!/usr/bin/env python3
"""
Database initialization script for COTAI
Run this script to create all tables and initial data
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import Base
from app.models.user import User, UserRole


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    # Connect to PostgreSQL server (not specific database)
    server_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    engine = create_engine(server_url)

    with engine.connect() as conn:
        # Set autocommit to True for CREATE DATABASE
        conn.execute(text("COMMIT"))

        # Check if database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": settings.POSTGRES_DB},
        )

        if not result.fetchone():
            # Create database
            conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}"))
            print(f"Database '{settings.POSTGRES_DB}' created successfully.")
        else:
            print(f"Database '{settings.POSTGRES_DB}' already exists.")


def create_tables():
    """Create all tables."""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")


def create_superuser():
    """Create the initial superuser."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if superuser already exists
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


def main():
    """Main initialization function."""
    print("Starting database initialization...")

    try:
        # Step 1: Create database if it doesn't exist
        create_database_if_not_exists()

        # Step 2: Create all tables
        create_tables()

        # Step 3: Create superuser
        create_superuser()

        print("Database initialization completed successfully!")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
