"""
ML monitoring service for tracking clustering quality and performance.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.ml_metrics import ClusteringAlert, ClusteringQualityMetrics, MLModelPerformance
from app.services.config_service import config_service

logger = logging.getLogger("app.ml_monitoring")


class MLMonitoringService:
    """Service for monitoring ML clustering quality and performance."""

    def __init__(self):
        self.logger = logger
        self.quality_thresholds = {
            "silhouette_min": 0.2,
            "combined_min": 0.3,
            "processing_time_max": 300.0,  # 5 minutes
            "memory_usage_max": 1000.0,  # 1GB
        }

    def record_clustering_metrics(
        self,
        course_id: int,
        algorithm_used: str,
        algorithm_params: Dict[str, Any],
        quality_metrics: Dict[str, Any],
        clustering_results: Dict[str, Any],
        processing_time: float,
        db: Session,
        import_job_id: Optional[str] = None,
    ) -> bool:
        """
        Record clustering quality metrics for monitoring.

        Args:
            course_id: Course ID
            algorithm_used: Algorithm name used
            algorithm_params: Algorithm parameters
            quality_metrics: Quality metrics (silhouette, calinski_harabasz, etc.)
            clustering_results: Clustering results summary
            processing_time: Time taken for clustering
            db: Database session
            import_job_id: Optional import job ID

        Returns:
            True if metrics recorded successfully
        """
        try:
            # Get memory usage
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Create metrics record
            metrics = ClusteringQualityMetrics(
                course_id=course_id,
                algorithm_used=algorithm_used,
                algorithm_params=json.dumps(algorithm_params),
                silhouette_score=quality_metrics.get("silhouette_score", 0.0),
                calinski_harabasz_score=quality_metrics.get("calinski_harabasz_score", 0.0),
                combined_score=quality_metrics.get("combined_score", 0.0),
                n_clusters=quality_metrics.get("n_clusters", 0),
                total_students=clustering_results.get("total_students", 0),
                clustered_students=clustering_results.get("clustered_students", 0),
                processing_time_seconds=processing_time,
                memory_usage_mb=memory_usage,
                import_job_id=import_job_id,
                created_at=config_service.now(),
            )

            db.add(metrics)
            db.commit()

            # Update algorithm performance tracking
            self._update_algorithm_performance(
                algorithm_used, algorithm_params, quality_metrics, processing_time, memory_usage, db
            )

            # Check for quality alerts
            self._check_quality_alerts(course_id, quality_metrics, algorithm_used, db, import_job_id)

            self.logger.info(
                f"Recorded clustering metrics for course {course_id}: algorithm={algorithm_used}, quality={quality_metrics.get('silhouette_score', 0):.3f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error recording clustering metrics: {e}")
            db.rollback()
            return False

    def get_course_quality_history(self, course_id: int, days: int = 30, db: Session = None) -> List[Dict[str, Any]]:
        """
        Get quality metrics history for a course.

        Args:
            course_id: Course ID
            days: Number of days to look back
            db: Database session

        Returns:
            List of quality metrics records
        """
        try:
            if db is None:
                from app.database.session import get_session

                db = next(get_session())

            cutoff_date = config_service.now() - timedelta(days=days)

            metrics = (
                db.query(ClusteringQualityMetrics)
                .filter(
                    and_(ClusteringQualityMetrics.course_id == course_id, ClusteringQualityMetrics.created_at >= cutoff_date)
                )
                .order_by(desc(ClusteringQualityMetrics.created_at))
                .all()
            )

            return [
                {
                    "id": m.id,
                    "course_id": m.course_id,
                    "algorithm_used": m.algorithm_used,
                    "algorithm_params": json.loads(m.algorithm_params) if m.algorithm_params else {},
                    "silhouette_score": m.silhouette_score,
                    "calinski_harabasz_score": m.calinski_harabasz_score,
                    "combined_score": m.combined_score,
                    "n_clusters": m.n_clusters,
                    "total_students": m.total_students,
                    "clustered_students": m.clustered_students,
                    "processing_time_seconds": m.processing_time_seconds,
                    "memory_usage_mb": m.memory_usage_mb,
                    "import_job_id": m.import_job_id,
                    "created_at": m.created_at,
                }
                for m in metrics
            ]

        except Exception as e:
            self.logger.error(f"Error getting course quality history: {e}")
            return []

    def get_algorithm_performance_summary(self, days: int = 30, db: Session = None) -> Dict[str, Any]:
        """
        Get performance summary for all algorithms.

        Args:
            days: Number of days to look back
            db: Database session

        Returns:
            Dictionary with algorithm performance summary
        """
        try:
            if db is None:
                from app.database.session import get_session

                db = next(get_session())

            cutoff_date = config_service.now() - timedelta(days=days)

            # Get performance records
            performances = db.query(MLModelPerformance).filter(MLModelPerformance.updated_at >= cutoff_date).all()

            # Get recent quality metrics
            recent_metrics = (
                db.query(ClusteringQualityMetrics).filter(ClusteringQualityMetrics.created_at >= cutoff_date).all()
            )

            # Calculate summary statistics
            algorithm_stats = {}
            for perf in performances:
                algorithm_stats[perf.algorithm_name] = {
                    "avg_silhouette_score": perf.avg_silhouette_score,
                    "avg_calinski_harabasz_score": perf.avg_calinski_harabasz_score,
                    "avg_combined_score": perf.avg_combined_score,
                    "avg_processing_time": perf.avg_processing_time,
                    "avg_memory_usage": perf.avg_memory_usage,
                    "total_runs": perf.total_runs,
                    "successful_runs": perf.successful_runs,
                    "failed_runs": perf.failed_runs,
                    "success_rate": perf.successful_runs / max(perf.total_runs, 1),
                    "threshold_met_rate": perf.threshold_met_count / max(perf.total_runs, 1),
                    "last_used": perf.last_used,
                }

            # Calculate overall statistics
            total_runs = sum(perf.total_runs for perf in performances)
            total_successful = sum(perf.successful_runs for perf in performances)
            avg_quality = sum(m.silhouette_score for m in recent_metrics) / max(len(recent_metrics), 1)

            return {
                "summary": {
                    "total_runs": total_runs,
                    "total_successful": total_successful,
                    "overall_success_rate": total_successful / max(total_runs, 1),
                    "avg_quality_score": avg_quality,
                    "period_days": days,
                },
                "algorithms": algorithm_stats,
                "generated_at": config_service.now(),
            }

        except Exception as e:
            self.logger.error(f"Error getting algorithm performance summary: {e}")
            return {"error": str(e)}

    def get_active_alerts(self, course_id: Optional[int] = None, db: Session = None) -> List[Dict[str, Any]]:
        """
        Get active clustering quality alerts.

        Args:
            course_id: Optional course ID to filter by
            db: Database session

        Returns:
            List of active alerts
        """
        try:
            if db is None:
                from app.database.session import get_session

                db = next(get_session())

            query = db.query(ClusteringAlert).filter(ClusteringAlert.resolved == False)

            if course_id:
                query = query.filter(ClusteringAlert.course_id == course_id)

            alerts = query.order_by(desc(ClusteringAlert.created_at)).all()

            return [
                {
                    "id": a.id,
                    "course_id": a.course_id,
                    "alert_type": a.alert_type,
                    "alert_level": a.alert_level,
                    "message": a.message,
                    "details": json.loads(a.details) if a.details else {},
                    "silhouette_score": a.silhouette_score,
                    "combined_score": a.combined_score,
                    "threshold": a.threshold,
                    "import_job_id": a.import_job_id,
                    "created_at": a.created_at,
                }
                for a in alerts
            ]

        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []

    def resolve_alert(self, alert_id: int, resolution_notes: str, db: Session = None) -> bool:
        """
        Resolve a clustering quality alert.

        Args:
            alert_id: Alert ID to resolve
            resolution_notes: Notes about how the alert was resolved
            db: Database session

        Returns:
            True if alert resolved successfully
        """
        try:
            if db is None:
                from app.database.session import get_session

                db = next(get_session())

            alert = db.query(ClusteringAlert).filter(ClusteringAlert.id == alert_id).first()

            if not alert:
                self.logger.error(f"Alert {alert_id} not found")
                return False

            alert.resolved = True
            alert.resolved_at = config_service.now()
            alert.resolution_notes = resolution_notes

            db.commit()

            self.logger.info(f"Resolved alert {alert_id}: {resolution_notes}")
            return True

        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            db.rollback()
            return False

    def _update_algorithm_performance(
        self,
        algorithm_name: str,
        algorithm_params: Dict[str, Any],
        quality_metrics: Dict[str, Any],
        processing_time: float,
        memory_usage: float,
        db: Session,
    ) -> None:
        """Update algorithm performance tracking."""
        try:
            # Find existing performance record
            perf = (
                db.query(MLModelPerformance)
                .filter(
                    and_(
                        MLModelPerformance.algorithm_name == algorithm_name,
                        MLModelPerformance.algorithm_params == json.dumps(algorithm_params),
                    )
                )
                .first()
            )

            if perf:
                # Update existing record
                total_runs = perf.total_runs + 1
                successful_runs = perf.successful_runs + 1

                # Update averages
                perf.avg_silhouette_score = (
                    perf.avg_silhouette_score * perf.total_runs + quality_metrics.get("silhouette_score", 0)
                ) / total_runs
                perf.avg_calinski_harabasz_score = (
                    perf.avg_calinski_harabasz_score * perf.total_runs + quality_metrics.get("calinski_harabasz_score", 0)
                ) / total_runs
                perf.avg_combined_score = (
                    perf.avg_combined_score * perf.total_runs + quality_metrics.get("combined_score", 0)
                ) / total_runs
                perf.avg_processing_time = (perf.avg_processing_time * perf.total_runs + processing_time) / total_runs
                perf.avg_memory_usage = (perf.avg_memory_usage * perf.total_runs + memory_usage) / total_runs

                perf.total_runs = total_runs
                perf.successful_runs = successful_runs
                perf.last_used = config_service.now()
                perf.updated_at = config_service.now()

                # Check if quality threshold was met
                if quality_metrics.get("silhouette_score", 0) >= self.quality_thresholds["silhouette_min"]:
                    perf.threshold_met_count += 1
            else:
                # Create new performance record
                perf = MLModelPerformance(
                    algorithm_name=algorithm_name,
                    algorithm_params=json.dumps(algorithm_params),
                    avg_silhouette_score=quality_metrics.get("silhouette_score", 0),
                    avg_calinski_harabasz_score=quality_metrics.get("calinski_harabasz_score", 0),
                    avg_combined_score=quality_metrics.get("combined_score", 0),
                    avg_processing_time=processing_time,
                    avg_memory_usage=memory_usage,
                    total_runs=1,
                    successful_runs=1,
                    failed_runs=0,
                    quality_threshold=self.quality_thresholds["silhouette_min"],
                    threshold_met_count=(
                        1 if quality_metrics.get("silhouette_score", 0) >= self.quality_thresholds["silhouette_min"] else 0
                    ),
                    first_used=config_service.now(),
                    last_used=config_service.now(),
                    updated_at=config_service.now(),
                )
                db.add(perf)

            db.commit()

        except Exception as e:
            self.logger.error(f"Error updating algorithm performance: {e}")
            db.rollback()

    def _check_quality_alerts(
        self,
        course_id: int,
        quality_metrics: Dict[str, Any],
        algorithm_used: str,
        db: Session,
        import_job_id: Optional[str] = None,
    ) -> None:
        """Check for quality alerts and create them if necessary."""
        try:
            alerts_to_create = []

            # Check silhouette score
            silhouette_score = quality_metrics.get("silhouette_score", 0)
            if silhouette_score < self.quality_thresholds["silhouette_min"]:
                alerts_to_create.append(
                    {
                        "alert_type": "quality_low",
                        "alert_level": "warning" if silhouette_score > 0.1 else "error",
                        "message": f"Low clustering quality: silhouette score {silhouette_score:.3f} below threshold {self.quality_thresholds['silhouette_min']}",
                        "details": json.dumps(
                            {
                                "algorithm": algorithm_used,
                                "silhouette_score": silhouette_score,
                                "threshold": self.quality_thresholds["silhouette_min"],
                            }
                        ),
                        "silhouette_score": silhouette_score,
                        "threshold": self.quality_thresholds["silhouette_min"],
                    }
                )

            # Check combined score
            combined_score = quality_metrics.get("combined_score", 0)
            if combined_score < self.quality_thresholds["combined_min"]:
                alerts_to_create.append(
                    {
                        "alert_type": "combined_quality_low",
                        "alert_level": "warning",
                        "message": f"Low combined quality score: {combined_score:.3f} below threshold {self.quality_thresholds['combined_min']}",
                        "details": json.dumps(
                            {
                                "algorithm": algorithm_used,
                                "combined_score": combined_score,
                                "threshold": self.quality_thresholds["combined_min"],
                            }
                        ),
                        "combined_score": combined_score,
                        "threshold": self.quality_thresholds["combined_min"],
                    }
                )

            # Create alerts
            for alert_data in alerts_to_create:
                alert = ClusteringAlert(
                    course_id=course_id, import_job_id=import_job_id, created_at=config_service.now(), **alert_data
                )
                db.add(alert)

            if alerts_to_create:
                db.commit()
                self.logger.warning(f"Created {len(alerts_to_create)} quality alerts for course {course_id}")

        except Exception as e:
            self.logger.error(f"Error checking quality alerts: {e}")
            db.rollback()

    def update_quality_thresholds(self, thresholds: Dict[str, float]) -> bool:
        """
        Update quality thresholds for monitoring.

        Args:
            thresholds: Dictionary with new threshold values

        Returns:
            True if thresholds updated successfully
        """
        try:
            for key, value in thresholds.items():
                if key in self.quality_thresholds:
                    self.quality_thresholds[key] = value

            self.logger.info(f"Updated quality thresholds: {self.quality_thresholds}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating quality thresholds: {e}")
            return False

    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get current quality thresholds."""
        return self.quality_thresholds.copy()
