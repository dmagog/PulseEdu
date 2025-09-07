"""
Import job models.
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ImportJob(SQLModel, table=True):
    """Import job tracking model."""
    
    __tablename__ = "import_jobs"
    
    job_id: str = Field(primary_key=True, max_length=50)
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    status: str = Field(max_length=20, default="pending")  # pending, processing, completed, failed
    total_rows: Optional[int] = Field(default=None)
    processed_rows: int = Field(default=0)
    error_rows: int = Field(default=0)
    errors_json: Optional[str] = Field(default=None, max_length=10000)  # JSON with error details
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None, max_length=50)
    
    # Relationships
    errors: List["ImportError"] = Relationship(back_populates="job")


class ImportError(SQLModel, table=True):
    """Import error details model."""
    
    __tablename__ = "import_errors"
    
    error_id: int = Field(primary_key=True)
    job_id: str = Field(foreign_key="import_jobs.job_id")
    row_number: int = Field()
    column_name: Optional[str] = Field(default=None, max_length=100)
    error_type: str = Field(max_length=50)  # validation, parsing, database, etc.
    error_message: str = Field(max_length=500)
    cell_value: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    job: ImportJob = Relationship(back_populates="errors")
