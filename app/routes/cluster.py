"""
Cluster management API routes.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.middleware.auth import require_admin, require_teacher_access
from app.services.cluster_service import ClusterService


class ClusteringRequest(BaseModel):
    force_update: bool = False


logger = logging.getLogger("app.cluster")
router = APIRouter(prefix="/api/cluster", tags=["cluster"])

cluster_service = ClusterService()
# ml_cluster_service = MLClusterService()  # Removed to avoid sklearn import in web app


@router.post("/trigger-clustering")
async def trigger_clustering(
    request_data: ClusteringRequest, db: Session = Depends(get_session), _: None = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Trigger clustering recalculation for all courses.

    Args:
        force_update: Force update even if recent clustering exists
        db: Database session

    Returns:
        Dictionary with clustering result
    """
    try:
        force_update = request_data.force_update
        logger.info(f"Triggering clustering recalculation, force_update={force_update}")

        # Trigger ML clustering for all courses
        result = cluster_service.cluster_all_courses(db)

        return {"status": "success", "message": "Clustering recalculation triggered successfully", "result": result}

    except Exception as e:
        logger.error(f"Error triggering clustering: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-clustering-teacher")
async def trigger_clustering_teacher(request_data: ClusteringRequest, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Trigger clustering recalculation for all courses (teacher access).

    Args:
        force_update: Force update even if recent clustering exists
        db: Database session

    Returns:
        Dictionary with clustering result
    """
    try:
        force_update = request_data.force_update
        logger.info(f"Triggering clustering recalculation (teacher), force_update={force_update}")

        # Trigger ML clustering for all courses
        result = cluster_service.cluster_all_courses(db)

        return {"status": "success", "message": "Clustering recalculation triggered successfully", "result": result}

    except Exception as e:
        logger.error(f"Error triggering clustering: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-course-clustering/{course_id}")
async def trigger_course_clustering(
    course_id: int, request_data: ClusteringRequest, db: Session = Depends(get_session), _: None = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Trigger clustering recalculation for a specific course.

    Args:
        course_id: Course ID to cluster
        force_update: Force update even if recent clustering exists
        db: Database session

    Returns:
        Dictionary with clustering result
    """
    try:
        force_update = request_data.force_update
        logger.info(f"Triggering clustering for course {course_id}, force_update={force_update}")

        # Trigger ML clustering for specific course
        result = cluster_service.cluster_students_by_course(course_id, db)

        return {"status": "success", "message": f"Clustering triggered for course {course_id}", "result": result}

    except Exception as e:
        logger.error(f"Error triggering course clustering: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_clustering_status(db: Session = Depends(get_session), _: None = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get current clustering status and statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with clustering status
    """
    try:
        # Get clustering statistics
        from app.models.cluster import StudentCluster
        from app.models.student import Student

        total_students = db.query(Student).count()
        clustered_students = db.query(StudentCluster).count()

        # Get recent clustering jobs
        recent_clusters = db.query(StudentCluster).order_by(StudentCluster.created_at.desc()).limit(10).all()

        return {
            "status": "success",
            "statistics": {
                "total_students": total_students,
                "clustered_students": clustered_students,
                "clustering_coverage": (clustered_students / max(total_students, 1)) * 100,
            },
            "recent_clusters": [
                {
                    "id": cluster.id,
                    "course_id": cluster.course_id,
                    "student_id": cluster.student_id,
                    "cluster_group": cluster.cluster_group,
                    "created_at": cluster.created_at,
                }
                for cluster in recent_clusters
            ],
        }

    except Exception as e:
        logger.error(f"Error getting clustering status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
