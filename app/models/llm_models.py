"""
LLM-related models for recommendations and call logging.
"""

import json
from datetime import datetime
from typing import List, Optional

from sqlmodel import JSON, Column, Field, SQLModel, Text


class LLMRecommendation(SQLModel, table=True):
    """Cached LLM recommendations for students."""

    __tablename__ = "llm_recommendations"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(index=True)
    course_id: str = Field(index=True)
    cache_key: str = Field(index=True, unique=True)
    data_version: str = Field(index=True)
    recommendations_json: str = Field(sa_column=Column(Text))
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_recommendations(self) -> List[str]:
        """Get recommendations as list."""
        try:
            return json.loads(self.recommendations_json)
        except (json.JSONDecodeError, TypeError):
            return []


class LLMCallLog(SQLModel, table=True):
    """Log of LLM API calls for monitoring and debugging."""

    __tablename__ = "llm_call_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: Optional[str] = Field(index=True)
    course_id: Optional[str] = Field(index=True)
    request_type: str = Field(index=True)  # "recommendations", "analysis", etc.
    prompt_hash: str = Field(index=True)  # Hash of the prompt for deduplication
    request_tokens: Optional[int] = None
    response_tokens: Optional[int] = None
    response_time_ms: Optional[int] = None
    status: str = Field(index=True)  # "success", "error", "timeout"
    error_message: Optional[str] = None
    cost_usd: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Additional metadata
    model_used: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    retry_count: int = Field(default=0)

    # Response data (for debugging)
    response_preview: Optional[str] = None  # First 200 chars of response
    recommendations_count: Optional[int] = None


class LLMFeedback(SQLModel, table=True):
    """Student and teacher feedback on LLM recommendations."""

    __tablename__ = "llm_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    recommendation_id: int = Field(index=True)  # Reference to LLMRecommendation
    student_id: str = Field(index=True)
    course_id: str = Field(index=True)
    feedback_type: str = Field(index=True)  # "student_rating", "teacher_approval", "teacher_edit"
    rating: Optional[int] = None  # 1-5 stars for student ratings
    feedback_text: Optional[str] = None
    is_approved: Optional[bool] = None  # For teacher approval
    edited_recommendation: Optional[str] = None  # For teacher edits
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_by: str = Field(index=True)  # "student" or "teacher"


class LLMUsageStats(SQLModel, table=True):
    """Daily usage statistics for LLM monitoring."""

    __tablename__ = "llm_usage_stats"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    total_requests: int = Field(default=0)
    successful_requests: int = Field(default=0)
    failed_requests: int = Field(default=0)
    total_tokens_used: int = Field(default=0)
    total_cost_usd: float = Field(default=0.0)
    unique_students: int = Field(default=0)
    unique_courses: int = Field(default=0)
    avg_response_time_ms: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
