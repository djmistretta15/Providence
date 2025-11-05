"""Database connection and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gatekeeper:gatekeeper_pass@localhost:5432/gatekeeper_db"
)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.getenv("DEBUG", "False").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from models import User, Dataset, Mapping, Export, Billing, Invoice, AuditLog
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def check_db_health() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
