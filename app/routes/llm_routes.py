"""
LLM API routes for recommendations and feedback.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.llm_models import LLMFeedback, LLMRecommendation
from app.services.llm_provider import LLMProvider
from app.services.markdown_service import MarkdownService
from app.services.student_service import StudentService
from worker.llm_tasks import generate_recommendations_task

logger = logging.getLogger("app.llm_routes")

router = APIRouter(prefix="/api/llm", tags=["llm"])

llm_provider = LLMProvider()
markdown_service = MarkdownService()
student_service = StudentService()


@router.get("/recommendations/{student_id}/{course_id}")
async def get_recommendations(
    student_id: str, course_id: str, force_refresh: bool = False, db: Session = Depends(get_session)
):
    """
    Get LLM recommendations for a student in a specific course.

    Args:
        student_id: Student ID
        course_id: Course ID
        force_refresh: Force regeneration even if cached
        db: Database session

    Returns:
        Dict with recommendations and metadata
    """
    try:
        logger.info(f"Getting recommendations for student {student_id}, course {course_id}")

        # Check if student exists and has access to the course
        student_data = student_service.get_detailed_course_data(student_id, db)
        if not student_data:
            raise HTTPException(status_code=404, detail="Student or course not found")

        # Trigger async task to generate recommendations
        task = generate_recommendations_task.delay(student_id, course_id, force_refresh)

        # For now, return task ID (in production, you might want to poll or use WebSockets)
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Recommendations are being generated. Use the task_id to check status.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/{student_id}/{course_id}/result")
async def get_recommendations_result(student_id: str, course_id: str, db: Session = Depends(get_session)):
    """
    Get cached recommendations for a student in a specific course.

    Args:
        student_id: Student ID
        course_id: Course ID
        db: Database session

    Returns:
        Dict with recommendations and metadata
    """
    try:
        logger.info(f"Getting cached recommendations for student {student_id}, course {course_id}")

        # Get latest cached recommendations
        cached_rec = (
            db.query(LLMRecommendation)
            .filter(LLMRecommendation.student_id == student_id, LLMRecommendation.course_id == course_id)
            .order_by(LLMRecommendation.created_at.desc())
            .first()
        )

        if not cached_rec:
            return {"status": "not_found", "message": "No recommendations found. Please generate them first."}

        # Check if cache is expired
        from datetime import datetime

        if cached_rec.expires_at < datetime.utcnow():
            return {"status": "expired", "message": "Recommendations have expired. Please regenerate them."}

        # Get recommendations
        recommendations = cached_rec.get_recommendations()

        # Render with markdown
        rendered_recommendations = markdown_service.render_recommendations(recommendations)

        return {
            "status": "success",
            "recommendations": rendered_recommendations,
            "cached": True,
            "created_at": cached_rec.created_at.isoformat(),
            "expires_at": cached_rec.expires_at.isoformat(),
            "data_version": cached_rec.data_version,
        }

    except Exception as e:
        logger.error(f"Error getting recommendations result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{student_id}/{course_id}/rate")
async def rate_recommendation(
    student_id: str, course_id: str, rating_data: Dict[str, Any], db: Session = Depends(get_session)
):
    """
    Rate a recommendation (1-5 stars).

    Args:
        student_id: Student ID
        course_id: Course ID
        rating_data: Dict with 'rating' (1-5) and optional 'feedback_text'
        db: Database session

    Returns:
        Dict with success status
    """
    try:
        rating = rating_data.get("rating")
        feedback_text = rating_data.get("feedback_text", "")

        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be an integer between 1 and 5")

        # Get the latest recommendation for this student/course
        cached_rec = (
            db.query(LLMRecommendation)
            .filter(LLMRecommendation.student_id == student_id, LLMRecommendation.course_id == course_id)
            .order_by(LLMRecommendation.created_at.desc())
            .first()
        )

        if not cached_rec:
            raise HTTPException(status_code=404, detail="No recommendations found")

        # Create feedback entry
        feedback = LLMFeedback(
            recommendation_id=cached_rec.id,
            student_id=student_id,
            course_id=course_id,
            feedback_type="student_rating",
            rating=rating,
            feedback_text=feedback_text,
            created_by="student",
        )

        db.add(feedback)
        db.commit()

        logger.info(f"Student {student_id} rated recommendation {cached_rec.id} with {rating} stars")

        return {"status": "success", "message": "Rating saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{student_id}/{course_id}/approve")
async def approve_recommendation(
    student_id: str, course_id: str, approval_data: Dict[str, Any], db: Session = Depends(get_session)
):
    """
    Teacher approval/editing of recommendations.

    Args:
        student_id: Student ID
        course_id: Course ID
        approval_data: Dict with 'is_approved' (bool) and optional 'edited_recommendation'
        db: Database session

    Returns:
        Dict with success status
    """
    try:
        is_approved = approval_data.get("is_approved")
        edited_recommendation = approval_data.get("edited_recommendation", "")

        if is_approved is None:
            raise HTTPException(status_code=400, detail="is_approved field is required")

        # Get the latest recommendation for this student/course
        cached_rec = (
            db.query(LLMRecommendation)
            .filter(LLMRecommendation.student_id == student_id, LLMRecommendation.course_id == course_id)
            .order_by(LLMRecommendation.created_at.desc())
            .first()
        )

        if not cached_rec:
            raise HTTPException(status_code=404, detail="No recommendations found")

        # Create feedback entry
        feedback = LLMFeedback(
            recommendation_id=cached_rec.id,
            student_id=student_id,
            course_id=course_id,
            feedback_type="teacher_approval",
            is_approved=is_approved,
            edited_recommendation=edited_recommendation,
            created_by="teacher",
        )

        db.add(feedback)
        db.commit()

        action = "approved" if is_approved else "rejected"
        logger.info(f"Teacher {action} recommendation {cached_rec.id} for student {student_id}")

        return {"status": "success", "message": f"Recommendation {action} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_llm_stats(db: Session = Depends(get_session)):
    """
    Get LLM usage statistics.

    Returns:
        Dict with usage statistics
    """
    try:
        from datetime import datetime, timedelta

        from sqlalchemy import func

        # Get stats for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Count total recommendations
        total_recommendations = db.query(LLMRecommendation).count()

        # Count active (non-expired) recommendations
        active_recommendations = db.query(LLMRecommendation).filter(LLMRecommendation.expires_at > datetime.utcnow()).count()

        # Count feedback entries
        total_feedback = db.query(LLMFeedback).count()

        # Count student ratings
        student_ratings = db.query(LLMFeedback).filter(LLMFeedback.feedback_type == "student_rating").count()

        # Count teacher approvals
        teacher_approvals = db.query(LLMFeedback).filter(LLMFeedback.feedback_type == "teacher_approval").count()

        # Average rating
        avg_rating = (
            db.query(func.avg(LLMFeedback.rating))
            .filter(LLMFeedback.feedback_type == "student_rating", LLMFeedback.rating.isnot(None))
            .scalar()
            or 0
        )

        return {
            "total_recommendations": total_recommendations,
            "active_recommendations": active_recommendations,
            "total_feedback": total_feedback,
            "student_ratings": student_ratings,
            "teacher_approvals": teacher_approvals,
            "average_rating": round(avg_rating, 2) if avg_rating else 0,
            "period": "last_30_days",
        }

    except Exception as e:
        logger.error(f"Error getting LLM stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teacher/recommendations")
async def get_teacher_recommendations(
    course_id: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_session)
):
    """
    Get all recommendations for teacher review.

    Args:
        course_id: Optional course ID filter
        status: Optional status filter (pending, approved, rejected)
        db: Database session

    Returns:
        Dict with recommendations and metadata
    """
    try:
        logger.info("Getting teacher recommendations")

        # Build query
        query = db.query(LLMRecommendation)

        if course_id:
            query = query.filter(LLMRecommendation.course_id == course_id)

        # Get recommendations with feedback
        recommendations = query.order_by(LLMRecommendation.created_at.desc()).all()

        result = []
        for rec in recommendations:
            # Get student feedback
            student_feedback = (
                db.query(LLMFeedback)
                .filter(LLMFeedback.recommendation_id == rec.id, LLMFeedback.feedback_type == "student_rating")
                .first()
            )

            # Get teacher feedback
            teacher_feedback = (
                db.query(LLMFeedback)
                .filter(LLMFeedback.recommendation_id == rec.id, LLMFeedback.feedback_type == "teacher_approval")
                .first()
            )

            # Determine teacher status
            teacher_status = "pending"
            if teacher_feedback:
                teacher_status = "approved" if teacher_feedback.is_approved else "rejected"

            # Apply status filter
            if status and teacher_status != status:
                continue

            # Render recommendations with markdown
            recommendations_list = rec.get_recommendations()
            rendered_recommendations = markdown_service.render_recommendations(recommendations_list)

            result.append(
                {
                    "id": rec.id,
                    "student_id": rec.student_id,
                    "course_id": rec.course_id,
                    "course_name": f"Курс {rec.course_id}",  # TODO: Get actual course name
                    "text_content": recommendations_list[0] if recommendations_list else "",
                    "html_content": rendered_recommendations[0]["html"] if rendered_recommendations else "",
                    "student_rating": student_feedback.rating if student_feedback else None,
                    "teacher_status": teacher_status,
                    "created_at": rec.created_at.isoformat(),
                    "expires_at": rec.expires_at.isoformat(),
                }
            )

        return {"status": "success", "recommendations": result, "total": len(result)}

    except Exception as e:
        logger.error(f"Error getting teacher recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
