"""
Import routes for file upload and processing.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.middleware.auth import require_import_access
from app.models.import_models import ImportErrorLog, ImportJob
from app.services.import_service import ImportService
from worker.tasks import process_import_job

router = APIRouter(prefix="/import", tags=["import"])
logger = logging.getLogger("app.import")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize import service
import_service = ImportService()


@router.get("/", response_class=HTMLResponse)
async def import_page(request: Request) -> HTMLResponse:
    """
    Import page for uploading Excel files.
    """
    logger.info("Import page requested")

    return templates.TemplateResponse("import/upload.html", {"request": request, "title": "Импорт данных"})


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Upload Excel file and start import job.

    Args:
        file: Uploaded Excel file
        db: Database session

    Returns:
        Import job information
    """
    logger.info(f"File upload requested: {file.filename}")

    # Validate file type
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")

    try:
        # Generate job ID
        job_id = f"import_{uuid.uuid4().hex[:12]}"

        # Read file content
        file_content = await file.read()

        # Save file
        file_path = import_service.save_uploaded_file(file_content, file.filename)

        # Create import job
        job = ImportJob(
            job_id=job_id,
            filename=file_path,
            original_filename=file.filename,
            status="pending",
            created_by="system",  # In real app, get from session
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Start background task
        task = process_import_job.delay(job_id)

        logger.info(f"Import job created: {job_id}, task: {task.id}")

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "job_id": job_id,
            "task_id": task.id,
            "filename": file.filename,
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/jobs")
async def list_jobs(request: Request, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    List all import jobs.

    Args:
        db: Database session

    Returns:
        List of import jobs
    """
    logger.info("Import jobs list requested")

    jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(50).all()

    jobs_data = []
    for job in jobs:
        jobs_data.append(
            {
                "job_id": job.job_id,
                "original_filename": job.original_filename,
                "status": job.status,
                "total_rows": job.total_rows,
                "processed_rows": job.processed_rows,
                "error_rows": job.error_rows,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
        )

    return {"status": "success", "jobs": jobs_data, "total": len(jobs_data)}


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str, request: Request, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Get detailed information about import job.

    Args:
        job_id: Import job ID
        db: Database session

    Returns:
        Job details with errors
    """
    logger.info(f"Job details requested: {job_id}")

    job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get errors
    errors = db.query(ImportErrorLog).filter(ImportErrorLog.job_id == job_id).all()

    errors_data = []
    for error in errors:
        errors_data.append(
            {
                "row_number": error.row_number,
                "column_name": error.column_name,
                "error_type": error.error_type,
                "error_message": error.error_message,
                "cell_value": error.cell_value,
                "created_at": error.created_at.isoformat(),
            }
        )

    return {
        "status": "success",
        "job": {
            "job_id": job.job_id,
            "original_filename": job.original_filename,
            "status": job.status,
            "total_rows": job.total_rows,
            "processed_rows": job.processed_rows,
            "error_rows": job.error_rows,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "errors_json": job.errors_json,
        },
        "errors": errors_data,
    }
