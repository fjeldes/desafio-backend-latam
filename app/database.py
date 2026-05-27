"""
Database configuration and session management.

This module sets up the SQLAlchemy engine and session factory. It reads the
database connection string from the DATABASE_URL environment variable and
provides a FastAPI dependency to inject database sessions into route handlers.

Environment variables
---------------------
DATABASE_URL : str
    Full SQLAlchemy connection string (default: sqlite:///./users.db).
    For Cloud SQL / PostgreSQL, use the format:
    postgresql+psycopg2://user:pass@/dbname?host=/cloudsql/<connection_name>
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Read the database URL from the environment; fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# SQLite requires check_same_thread=False for FastAPI's async/thread model
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create the global engine and session factory
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    FastAPI dependency that yields a SQLAlchemy database session.

    The session is automatically closed when the request finishes, even
    if an exception occurs during request processing.

    Yields
    ------
    Session
        A transactional SQLAlchemy session scoped to the current request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
