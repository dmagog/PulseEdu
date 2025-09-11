"""
ML metrics models for tracking clustering quality and performance.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Field, Relationship, SQLModel


class ClusteringQualityMetrics(SQLModel, table=True):
    """
    Model for storing clustering quality metrics.

    Tracks the quality of ML clustering results for monitoring and analysis.
    """

    __tablename__ = "clustering_quality_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True, description="Course ID")
    algorithm_used: str = Field(description="ML algorithm used for clustering")
    algorithm_params: str = Field(description="JSON string of algorithm parameters")

    # Quality metrics
    silhouette_score: float = Field(description="Silhouette score (higher is better)")
    calinski_harabasz_score: float = Field(description="Calinski-Harabasz score (higher is better)")
    combined_score: float = Field(description="Combined quality score")

    # Clustering results
    n_clusters: int = Field(description="Number of clusters found")
    total_students: int = Field(description="Total number of students clustered")
    clustered_students: int = Field(description="Number of students successfully clustered")

    # Performance metrics
    processing_time_seconds: float = Field(description="Time taken to process clustering")
    memory_usage_mb: float = Field(description="Memory usage during clustering")

    # Metadata
    import_job_id: Optional[str] = Field(default=None, index=True, description="Import job that triggered clustering")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When metrics were recorded")

    class Config:
        indexes = [
            ("course_id", "created_at"),  # For time-series queries
            ("algorithm_used", "created_at"),  # For algorithm performance analysis
        ]


class MLModelPerformance(SQLModel, table=True):
    """
    Model for tracking ML model performance over time.

    Stores aggregated performance metrics for different algorithms.
    """

    __tablename__ = "ml_model_performance"

    id: Optional[int] = Field(default=None, primary_key=True)
    algorithm_name: str = Field(index=True, description="Name of the ML algorithm")
    algorithm_params: str = Field(description="JSON string of algorithm parameters")

    # Performance metrics (averaged over multiple runs)
    avg_silhouette_score: float = Field(description="Average silhouette score")
    avg_calinski_harabasz_score: float = Field(description="Average Calinski-Harabasz score")
    avg_combined_score: float = Field(description="Average combined score")
    avg_processing_time: float = Field(description="Average processing time in seconds")
    avg_memory_usage: float = Field(description="Average memory usage in MB")

    # Usage statistics
    total_runs: int = Field(description="Total number of times this algorithm was used")
    successful_runs: int = Field(description="Number of successful runs")
    failed_runs: int = Field(description="Number of failed runs")

    # Quality thresholds
    quality_threshold: float = Field(description="Quality threshold used")
    threshold_met_count: int = Field(description="Number of times threshold was met")

    # Metadata
    first_used: datetime = Field(default_factory=datetime.utcnow, description="When algorithm was first used")
    last_used: datetime = Field(default_factory=datetime.utcnow, description="When algorithm was last used")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When metrics were last updated")

    class Config:
        indexes = [
            ("algorithm_name", "updated_at"),  # For algorithm performance tracking
        ]


class ClusteringAlert(SQLModel, table=True):
    """
    Model for storing clustering quality alerts.

    Tracks when clustering quality falls below acceptable thresholds.
    """

    __tablename__ = "clustering_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(index=True, description="Course ID")
    alert_type: str = Field(description="Type of alert (quality_low, algorithm_failed, etc.)")
    alert_level: str = Field(description="Alert level (warning, error, critical)")

    # Alert details
    message: str = Field(description="Alert message")
    details: str = Field(description="JSON string with additional alert details")

    # Quality metrics that triggered the alert
    silhouette_score: Optional[float] = Field(default=None, description="Silhouette score when alert was triggered")
    combined_score: Optional[float] = Field(default=None, description="Combined score when alert was triggered")
    threshold: float = Field(description="Threshold that was not met")

    # Resolution
    resolved: bool = Field(default=False, description="Whether alert has been resolved")
    resolved_at: Optional[datetime] = Field(default=None, description="When alert was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about how alert was resolved")

    # Metadata
    import_job_id: Optional[str] = Field(default=None, index=True, description="Import job that triggered alert")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When alert was created")

    class Config:
        indexes = [
            ("course_id", "created_at"),  # For course-specific alerts
            ("alert_type", "resolved"),  # For alert management
            ("alert_level", "resolved"),  # For priority-based alert handling
        ]
