"""
LLM tasks for generating recommendations and analysis.
"""
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from celery import Celery
from app.database.session import get_session
# from app.services.llm_provider import LLMProvider
from app.services.student_service import StudentService
from app.services.metrics_service import MetricsService
from worker.celery_app import celery_app

logger = logging.getLogger("worker.llm_tasks")
# llm_provider = LLMProvider()
student_service = StudentService()
metrics_service = MetricsService()

@celery_app.task(name="llm.generate_recommendations")
def generate_recommendations_task(student_id: str, course_id: str, force_refresh: bool = False):
    """
    Generate personalized recommendations for a student.
    Using mock data for testing.
    
    Args:
        student_id: Student ID
        course_id: Course ID
        force_refresh: Force regeneration even if cached
        
    Returns:
        Dict with status and recommendations
    """
    logger.info(f"Generating mock recommendations for student {student_id}, course {course_id}")
    
    try:
        # Simulate LLM processing time (5-8 seconds)
        import time
        import random
        processing_time = random.uniform(5, 8)
        logger.info(f"Simulating LLM processing for {processing_time:.1f} seconds...")
        time.sleep(processing_time)
        
        # Mock recommendations for testing
        mock_recommendations = [
            f"1. Увеличьте посещаемость занятий по курсу {course_id} до 90% и выше",
            f"2. Сдавайте задания вовремя, не откладывайте на последний момент",
            f"3. Обращайтесь за помощью к преподавателю при возникновении вопросов",
            f"4. Уделяйте больше времени самостоятельной работе по курсу {course_id}",
            f"5. Участвуйте активно в обсуждениях и групповых заданиях"
        ]
        
        # Log the LLM call for monitoring
        _log_llm_call(
            student_id=student_id,
            course_id=course_id,
            request_type="recommendations",
            status="success",
            recommendations=mock_recommendations,
            student_data={"mock": True}
        )
        
        logger.info(f"Successfully generated {len(mock_recommendations)} mock recommendations for student {student_id}, course {course_id}")
        return {
            "status": "success",
            "recommendations": mock_recommendations,
            "cached": False,
            "generated_at": datetime.utcnow().isoformat(),
            "mock": True,
            "processing_time": processing_time
        }
            
    except Exception as e:
        logger.error(f"Error generating recommendations for student {student_id}: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@celery_app.task(name="llm.bulk_generate_recommendations")
def bulk_generate_recommendations_task(student_course_pairs: List[Dict[str, str]]):
    """
    Generate recommendations for multiple students in batch.
    
    Args:
        student_course_pairs: List of {"student_id": str, "course_id": str}
        
    Returns:
        Dict with results summary
    """
    logger.info(f"Bulk generating recommendations for {len(student_course_pairs)} student-course pairs")
    
    results = {
        "total": len(student_course_pairs),
        "successful": 0,
        "failed": 0,
        "cached": 0,
        "errors": []
    }
    
    for pair in student_course_pairs:
        try:
            result = generate_recommendations_task.delay(
                pair["student_id"], 
                pair["course_id"]
            ).get(timeout=60)  # 60 second timeout per student
            
            if result["status"] == "success":
                results["successful"] += 1
                if result.get("cached", False):
                    results["cached"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "student_id": pair["student_id"],
                    "course_id": pair["course_id"],
                    "error": result.get("message", "Unknown error")
                })
                
        except Exception as e:
            logger.error(f"Error in bulk generation for {pair}: {e}")
            results["failed"] += 1
            results["errors"].append({
                "student_id": pair["student_id"],
                "course_id": pair["course_id"],
                "error": str(e)
            })
    
    logger.info(f"Bulk generation completed: {results['successful']} successful, {results['failed']} failed")
    return results

@celery_app.task(name="llm.cleanup_old_cache")
def cleanup_old_cache_task():
    """Clean up expired recommendation cache entries."""
    logger.info("Cleaning up old LLM cache entries")
    
    try:
        db = next(get_session())
        from app.models.llm_models import LLMRecommendation
        
        # Delete expired cache entries
        expired_count = db.query(LLMRecommendation).filter(
            LLMRecommendation.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {expired_count} expired cache entries")
        return {"status": "success", "cleaned_count": expired_count}
            
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        return {"status": "error", "message": str(e)}

def _get_student_data_for_llm(student_id: str, course_id: str, db) -> Optional[Dict[str, Any]]:
    """Get student performance data formatted for LLM."""
    try:
        # Get student progress
        progress = student_service.get_student_progress(student_id, db)
        if not progress:
            return None
            
        # Get course-specific data
        course_data = student_service.get_detailed_course_data(student_id, db)
        
        # Calculate metrics
        attendance_rate = 0.0
        task_completion_rate = 0.0
        average_grade = 0.0
        late_submissions = 0
        risk_level = "low"
        
        if course_data:
            attendance_rate = course_data.get("attendance_rate", 0.0)
            task_completion_rate = course_data.get("task_completion_rate", 0.0)
            average_grade = course_data.get("average_grade", 0.0)
            late_submissions = course_data.get("late_submissions", 0)
            risk_level = course_data.get("risk_level", "low")
        
        # Get recent activity
        activity_feed = student_service.get_activity_feed(student_id, db)
        recent_activity = "Нет недавней активности"
        if activity_feed and len(activity_feed) > 0:
            recent_activity = activity_feed[0].get("description", "Нет недавней активности")
        
        return {
            "student_id": student_id,
            "course_id": course_id,
            "attendance_rate": attendance_rate,
            "task_completion_rate": task_completion_rate,
            "average_grade": average_grade,
            "late_submissions": late_submissions,
            "risk_level": risk_level,
            "recent_activity": recent_activity,
            "total_courses": len(progress.get("courses", [])),
            "overall_progress": progress.get("overall_progress", 0.0)
        }
        
    except Exception as e:
        logger.error(f"Error getting student data for LLM: {e}")
        return None

def _generate_data_version(student_data: Dict[str, Any]) -> str:
    """Generate data version hash for cache invalidation."""
    # Include key metrics that affect recommendations
    key_data = {
        "attendance_rate": student_data.get("attendance_rate", 0),
        "task_completion_rate": student_data.get("task_completion_rate", 0),
        "average_grade": student_data.get("average_grade", 0),
        "late_submissions": student_data.get("late_submissions", 0),
        "risk_level": student_data.get("risk_level", "low")
    }
    
    data_str = str(sorted(key_data.items()))
    return hashlib.md5(data_str.encode()).hexdigest()[:8]

def _log_llm_call(student_id: str, course_id: str, request_type: str, 
                 status: str, recommendations: Optional[List[str]] = None,
                 student_data: Optional[Dict[str, Any]] = None,
                 error_message: Optional[str] = None):
    """Log LLM API call for monitoring."""
    try:
        db = next(get_session())
        from app.models.llm_models import LLMCallLog
        
        # Generate prompt hash for deduplication
        prompt_hash = ""
        if student_data:
            prompt_data = f"{student_id}:{course_id}:{student_data.get('attendance_rate', 0)}:{student_data.get('task_completion_rate', 0)}"
            prompt_hash = hashlib.md5(prompt_data.encode()).hexdigest()
        
        # Create log entry
        log_entry = LLMCallLog(
            student_id=student_id,
            course_id=course_id,
            request_type=request_type,
            prompt_hash=prompt_hash,
            status=status,
            error_message=error_message,
            recommendations_count=len(recommendations) if recommendations else None,
            response_preview=recommendations[0][:200] if recommendations and len(recommendations) > 0 else None,
            model_used="mock",
            temperature=0.7,
            max_tokens=1000
        )
        
        db.add(log_entry)
        db.commit()
            
    except Exception as e:
        logger.error(f"Error logging LLM call: {e}")
