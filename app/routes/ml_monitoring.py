"""
ML monitoring API routes for clustering quality tracking.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services.ml_monitoring_service import MLMonitoringService
from app.middleware.auth import require_admin

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
            "total_records": len(history)
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
        
        return {
            "status": "success",
            "performance_summary": summary,
            "period_days": days
        }
        
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
        alert_summary = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "total": len(alerts)
        }
        
        for alert in alerts:
            level = alert.get("alert_level", "warning")
            if level in alert_summary:
                alert_summary[level] += 1
        
        return {
            "status": "success",
            "active_alerts": alerts,
            "alert_summary": alert_summary,
            "course_id": course_id
        }
        
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
                "message": "Alert resolved successfully"
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
        
        return {
            "status": "success",
            "thresholds": thresholds
        }
        
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
                "message": "Thresholds updated successfully"
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
            "summary": {
                "total_runs": total_runs,
                "avg_quality_score": avg_quality,
                "active_alerts_count": len(active_alerts)
            },
            "quality_history": quality_history,
            "active_alerts": active_alerts,
            "performance_summary": performance_summary
        }
        
    except Exception as e:
        logger.error(f"Error getting course monitoring report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
