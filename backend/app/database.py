"""Database configuration and session management."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database setup
DB_PATH = os.getenv("SQLITE_PATH", "./app.db")

# Create engine
engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """Get a database session."""
    return SessionLocal()
