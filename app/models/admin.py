"""
Admin settings models.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class AdminSetting(SQLModel, table=True):
    """Admin configuration settings stored in database."""
    
    __tablename__ = "admin_settings"
    
    key: str = Field(primary_key=True, max_length=100)
    value: str = Field(max_length=1000)
    description: Optional[str] = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(default=None, max_length=100)
