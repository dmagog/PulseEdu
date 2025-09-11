"""
Cluster models for student clustering.
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class StudentCluster(SQLModel, table=True):
    """
    Model for storing student cluster assignments.
    
    Represents which cluster a student belongs to for a specific course.
    """
    __tablename__ = "student_clusters"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(index=True, description="Student ID")
    course_id: int = Field(index=True, description="Course ID")
    cluster_label: str = Field(description="Cluster label (A, B, C, etc.)")
    cluster_score: float = Field(description="Cluster assignment confidence score")
    
    # Clustering features used for assignment
    attendance_rate: float = Field(description="Attendance rate used for clustering")
    completion_rate: float = Field(description="Task completion rate used for clustering")
    overall_progress: float = Field(description="Overall progress used for clustering")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When cluster was assigned")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When cluster was last updated")
    
    # Import job that triggered this clustering
    import_job_id: Optional[str] = Field(default=None, index=True, description="Import job that triggered clustering")
    
    # ML metadata (algorithm used, quality metrics, etc.)
    ml_metadata: Optional[str] = Field(default=None, description="JSON metadata about ML clustering algorithm and quality metrics")
    
    class Config:
        indexes = [
            ("student_id", "course_id"),  # Composite index for fast lookups
        ]
