"""
Course detail page routes.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case

from app.database.session import get_session
from app.models.student import Course, Lesson, Task, Attendance, TaskCompletion, Student

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")

@router.get("/course/{course_id}", response_class=HTMLResponse)
async def course_detail(
    request: Request,
    course_id: int,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Детальная страница курса с составом, датами и мероприятиями.
    """
    logger.info(f"Rendering course detail page for course {course_id}")
    
    # Получаем информацию о курсе
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Получаем уроки курса
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).order_by(Lesson.lesson_number).all()
    
    # Получаем задания курса
    tasks = db.query(Task).filter(Task.course_id == course_id).order_by(Task.deadline).all()
    
    # Получаем статистику посещаемости
    attendance_stats = db.query(
        func.count(Attendance.id).label('total_attendances'),
        func.sum(case((Attendance.attended == True, 1), else_=0)).label('attended_count')
    ).join(Lesson).filter(Lesson.course_id == course_id).first()
    
    # Получаем статистику выполнения заданий
    task_stats = db.query(
        func.count(TaskCompletion.id).label('total_completions'),
        func.sum(case((TaskCompletion.status == "Выполнено", 1), else_=0)).label('completed_count')
    ).join(Task).filter(Task.course_id == course_id).first()
    
    # Получаем список студентов курса
    students = db.query(Student).join(Attendance).join(Lesson).filter(
        Lesson.course_id == course_id
    ).distinct().all()
    
    # Вычисляем проценты
    attendance_rate = 0
    if attendance_stats and attendance_stats.total_attendances > 0:
        attendance_rate = (attendance_stats.attended_count / attendance_stats.total_attendances) * 100
    
    completion_rate = 0
    if task_stats and task_stats.total_completions > 0:
        completion_rate = (task_stats.completed_count / task_stats.total_completions) * 100
    
    # Подготавливаем данные для хронологии
    timeline_events = []
    
    # Добавляем уроки
    for lesson in lessons:
        timeline_events.append({
            'type': 'lesson',
            'title': lesson.title,
            'date': lesson.date,
            'number': lesson.lesson_number,
            'icon': 'bi-book',
            'color': 'primary'
        })
    
    # Добавляем задания
    for task in tasks:
        timeline_events.append({
            'type': 'task',
            'title': task.name,
            'date': task.deadline,
            'task_type': task.task_type,
            'icon': 'bi-clipboard-check',
            'color': 'warning' if task.task_type == 'assignment' else 'info'
        })
    
    # Сортируем по дате
    timeline_events.sort(key=lambda x: x['date'] if x['date'] else datetime.max)
    
    return templates.TemplateResponse("course/detail.html", {
        "request": request,
        "title": f"Курс: {course.name}",
        "course": course,
        "lessons": lessons,
        "tasks": tasks,
        "students": students,
        "attendance_rate": round(attendance_rate, 1),
        "completion_rate": round(completion_rate, 1),
        "timeline_events": timeline_events,
        "stats": {
            "total_lessons": len(lessons),
            "total_tasks": len(tasks),
            "total_students": len(students),
            "attendance_count": attendance_stats.attended_count if attendance_stats else 0,
            "total_attendances": attendance_stats.total_attendances if attendance_stats else 0,
            "completed_tasks": task_stats.completed_count if task_stats else 0,
            "total_completions": task_stats.total_completions if task_stats else 0
        }
    })

@router.get("/course/{course_id}/students", response_class=HTMLResponse)
async def course_students(
    request: Request,
    course_id: int,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Список студентов курса с их статистикой.
    """
    logger.info(f"Rendering course students page for course {course_id}")
    
    # Получаем информацию о курсе
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Получаем студентов с их статистикой
    students_data = []
    students = db.query(Student).join(Attendance).join(Lesson).filter(
        Lesson.course_id == course_id
    ).distinct().all()
    
    for student in students:
        # Статистика посещаемости студента
        student_attendance = db.query(
            func.count(Attendance.id).label('total'),
            func.sum(case((Attendance.attended == True, 1), else_=0)).label('attended')
        ).join(Lesson).filter(
            and_(Lesson.course_id == course_id, Attendance.student_id == student.id)
        ).first()
        
        # Статистика выполнения заданий
        student_tasks = db.query(
            func.count(TaskCompletion.id).label('total'),
            func.sum(case((TaskCompletion.status == "Выполнено", 1), else_=0)).label('completed')
        ).join(Task).filter(
            and_(Task.course_id == course_id, TaskCompletion.student_id == student.id)
        ).first()
        
        attendance_rate = 0
        if student_attendance and student_attendance.total > 0:
            attendance_rate = (student_attendance.attended / student_attendance.total) * 100
        
        completion_rate = 0
        if student_tasks and student_tasks.total > 0:
            completion_rate = (student_tasks.completed / student_tasks.total) * 100
        
        students_data.append({
            'student': student,
            'attendance_rate': round(attendance_rate, 1),
            'completion_rate': round(completion_rate, 1),
            'total_attendances': student_attendance.total if student_attendance else 0,
            'attended_count': student_attendance.attended if student_attendance else 0,
            'total_tasks': student_tasks.total if student_tasks else 0,
            'completed_tasks': student_tasks.completed if student_tasks else 0
        })
    
    return templates.TemplateResponse("course/students.html", {
        "request": request,
        "title": f"Студенты курса: {course.name}",
        "course": course,
        "students_data": students_data
    })
