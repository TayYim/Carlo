"""
Database configuration for experiment history storage.

Optional SQLite database for storing experiment metadata,
results, and historical data.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .config import get_settings

settings = get_settings()

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ExperimentRecord(Base):
    """Database model for experiment records."""
    
    __tablename__ = "experiments"
    
    id = Column(String, primary_key=True)
    route_id = Column(String, nullable=False)
    route_file = Column(String, nullable=False)
    search_method = Column(String, nullable=False)
    num_iterations = Column(Integer, nullable=False)
    timeout_seconds = Column(Integer, nullable=False)
    headless = Column(Boolean, default=False)
    random_seed = Column(Integer, default=42)
    reward_function = Column(String, default="ttc")
    
    # Status and timing
    status = Column(String, default="created")  # created, running, completed, failed, stopped
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    best_reward = Column(Float, nullable=True)
    total_iterations = Column(Integer, default=0)
    collision_found = Column(Boolean, default=False)
    
    # Metadata
    output_directory = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


def create_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database."""
    create_tables()


# Database utility functions
def save_experiment_record(
    experiment_id: str,
    route_id: str,
    route_file: str,
    search_method: str,
    **kwargs
) -> ExperimentRecord:
    """Save a new experiment record."""
    db = next(get_db())
    try:
        record = ExperimentRecord(
            id=experiment_id,
            route_id=route_id,
            route_file=route_file,
            search_method=search_method,
            **kwargs
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def update_experiment_status(
    experiment_id: str,
    status: str,
    **kwargs
) -> Optional[ExperimentRecord]:
    """Update experiment status and metadata."""
    db = next(get_db())
    try:
        record = db.query(ExperimentRecord).filter(
            ExperimentRecord.id == experiment_id
        ).first()
        
        if record:
            record.status = status
            if status == "running" and not record.started_at:
                record.started_at = datetime.utcnow()
            elif status in ["completed", "failed", "stopped"] and not record.completed_at:
                record.completed_at = datetime.utcnow()
            
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            
            db.commit()
            db.refresh(record)
            return record
    finally:
        db.close()
    
    return None


def get_experiment_record(experiment_id: str) -> Optional[ExperimentRecord]:
    """Get experiment record by ID."""
    db = next(get_db())
    try:
        return db.query(ExperimentRecord).filter(
            ExperimentRecord.id == experiment_id
        ).first()
    finally:
        db.close()


def list_experiment_records(limit: int = 100, offset: int = 0) -> list[ExperimentRecord]:
    """List experiment records with pagination."""
    db = next(get_db())
    try:
        return db.query(ExperimentRecord).order_by(
            ExperimentRecord.created_at.desc()
        ).offset(offset).limit(limit).all()
    finally:
        db.close() 