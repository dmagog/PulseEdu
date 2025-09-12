"""
ML monitoring API routes for clustering quality tracking.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.middleware.auth import require_admin
from app.services.ml_monitoring_service import MLMonitoringService

logger = logging.getLogger("app.ml_monitoring")
router = APIRouter(prefix="/api/ml-monitoring", tags=["ml-monitoring"])

monitoring_service = MLMonitoringService()


@router.get("/course/{course_id}/quality-history")
async def get_course_quality_history(
    course_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get quality metrics history for a course.

    Args:
        course_id: Course ID
        days: Number of days to look back
        db: Database session

    Returns:
        Quality metrics history
    """
    try:
        history = monitoring_service.get_course_quality_history(course_id, days, db)

        return {
            "status": "success",
            "course_id": course_id,
            "period_days": days,
            "quality_history": history,
            "total_records": len(history),
        }

    except Exception as e:
        logger.error(f"Error getting course quality history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance-summary")
async def get_algorithm_performance_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get performance summary for all algorithms.

    Args:
        days: Number of days to look back
        db: Database session

    Returns:
        Algorithm performance summary
    """
    try:
        summary = monitoring_service.get_algorithm_performance_summary(days, db)

        return {"status": "success", "performance_summary": summary, "period_days": days}

    except Exception as e:
        logger.error(f"Error getting algorithm performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_active_alerts(
    course_id: Optional[int] = Query(default=None, description="Filter by course ID"),
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get active clustering quality alerts.

    Args:
        course_id: Optional course ID to filter by
        db: Database session

    Returns:
        List of active alerts
    """
    try:
        alerts = monitoring_service.get_active_alerts(course_id, db)

        # Group alerts by level for summary
        alert_summary = {"critical": 0, "error": 0, "warning": 0, "total": len(alerts)}

        for alert in alerts:
            level = alert.get("alert_level", "warning")
            if level in alert_summary:
                alert_summary[level] += 1

        return {"status": "success", "active_alerts": alerts, "alert_summary": alert_summary, "course_id": course_id}

    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolution_notes: str,
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Resolve a clustering quality alert.

    Args:
        alert_id: Alert ID to resolve
        resolution_notes: Notes about how the alert was resolved
        db: Database session

    Returns:
        Resolution result
    """
    try:
        success = monitoring_service.resolve_alert(alert_id, resolution_notes, db)

        if success:
            return {
                "status": "success",
                "alert_id": alert_id,
                "resolution_notes": resolution_notes,
                "message": "Alert resolved successfully",
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found or could not be resolved")

    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds")
async def get_quality_thresholds(
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get current quality thresholds.

    Returns:
        Current quality thresholds
    """
    try:
        thresholds = monitoring_service.get_quality_thresholds()

        return {"status": "success", "thresholds": thresholds}

    except Exception as e:
        logger.error(f"Error getting quality thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thresholds")
async def update_quality_thresholds(
    thresholds: Dict[str, float],
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Update monitoring quality thresholds.

    Args:
        thresholds: Dictionary with new threshold values

    Returns:
        Update result
    """
    try:
        success = monitoring_service.update_quality_thresholds(thresholds)

        if success:
            current_thresholds = monitoring_service.get_quality_thresholds()

            return {
                "status": "success",
                "updated_thresholds": thresholds,
                "current_thresholds": current_thresholds,
                "message": "Thresholds updated successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update thresholds")

    except Exception as e:
        logger.error(f"Error updating quality thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/course/{course_id}/monitoring-report")
async def get_course_monitoring_report(
    course_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get comprehensive monitoring report for a course.

    Args:
        course_id: Course ID
        days: Number of days to look back
        db: Database session

    Returns:
        Comprehensive monitoring report
    """
    try:
        # Get quality history
        quality_history = monitoring_service.get_course_quality_history(course_id, days, db)

        # Get active alerts for this course
        active_alerts = monitoring_service.get_active_alerts(course_id, db)

        # Get algorithm performance summary
        performance_summary = monitoring_service.get_algorithm_performance_summary(days, db)

        # Calculate summary statistics
        total_runs = len(quality_history)
        avg_quality = sum(m.get("silhouette_score", 0) for m in quality_history) / max(total_runs, 1)

        return {
            "status": "success",
            "course_id": course_id,
            "period_days": days,
            "summary": {"total_runs": total_runs, "avg_quality_score": avg_quality, "active_alerts_count": len(active_alerts)},
            "quality_history": quality_history,
            "active_alerts": active_alerts,
            "performance_summary": performance_summary,
        }

    except Exception as e:
        logger.error(f"Error getting course monitoring report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student-clusters")
async def get_student_clusters(
    course_id: Optional[int] = Query(default=None, description="Filter by course ID"),
    db: Session = Depends(get_session),
    # _: None = Depends(require_admin)  # Temporarily disabled for testing
) -> Dict[str, Any]:
    """
    Get student cluster assignments for dashboard display.

    Args:
        course_id: Optional course ID to filter by
        db: Database session

    Returns:
        Student cluster data for dashboard
    """
    try:
        from app.models.cluster import StudentCluster
        from app.models.student import Student

        # Get cluster assignments
        query = db.query(StudentCluster)
        if course_id:
            query = query.filter(StudentCluster.course_id == course_id)

        clusters = query.all()

        # Group by cluster label
        cluster_groups = {}
        for cluster in clusters:
            label = cluster.cluster_label
            if label not in cluster_groups:
                cluster_groups[label] = []
            cluster_groups[label].append(
                {
                    "student_id": cluster.student_id,
                    "cluster_score": cluster.cluster_score,
                    "attendance_rate": cluster.attendance_rate,
                    "completion_rate": cluster.completion_rate,
                    "overall_progress": cluster.overall_progress,
                }
            )

        # Calculate summary statistics
        total_students = len(clusters)
        cluster_summary = {}
        for label, students in cluster_groups.items():
            cluster_summary[label] = {
                "count": len(students),
                "avg_attendance": sum(s["attendance_rate"] for s in students) / len(students) if students else 0,
                "avg_completion": sum(s["completion_rate"] for s in students) / len(students) if students else 0,
                "avg_progress": sum(s["overall_progress"] for s in students) / len(students) if students else 0,
            }

        # Get last clustering time
        last_clustering_time = None
        if clusters:
            last_clustering_time = max(cluster.created_at for cluster in clusters)

        return {
            "status": "success",
            "total_students": total_students,
            "cluster_groups": cluster_groups,
            "cluster_summary": cluster_summary,
            "last_clustering_time": last_clustering_time.isoformat() if last_clustering_time else None,
        }

    except Exception as e:
        logger.error(f"Error getting student clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
