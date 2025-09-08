"""
Import service for processing Excel files.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.import_models import ImportJob, ImportErrorLog
from app.services.config_service import config_service
from app.services.attendance_import_service import AttendanceImportService
from app.services.learning_import_service import LearningImportService

logger = logging.getLogger("app.import")


class ImportService:
    """Service for processing Excel import jobs."""
    
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    def parse_excel(self, file_path: str, job_id: str, db: Session) -> Dict[str, Any]:
        """
        Parse Excel file and return structured data.
        
        Args:
            file_path: Path to Excel file
            job_id: Import job ID
            db: Database session
            
        Returns:
            Dictionary with parsed data and metadata
        """
        try:
            logger.info(f"Starting Excel parsing for job {job_id}")
            
            # Read Excel file to determine type
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Update job status
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if job:
                job.total_rows = len(df)
                job.status = "processing"
                job.started_at = datetime.utcnow()
                db.commit()
            
            # Determine file type and process accordingly
            file_type = self._determine_file_type(df.columns)
            logger.info(f"Detected file type: {file_type}")
            
            if file_type == "attendance":
                attendance_service = AttendanceImportService()
                result = attendance_service.process_attendance_file(file_path, job_id, db)
            elif file_type == "learning_process":
                learning_service = LearningImportService()
                result = learning_service.process_learning_file(file_path, job_id, db)
            else:
                # Fallback to generic processing
                result = self._process_generic_file(df, job_id, db)
            
            logger.info(f"Excel parsing completed for job {job_id}: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Excel parsing failed for job {job_id}: {e}")
            self._log_error(job_id, 0, None, "parsing", str(e), None, db)
            raise
    
    def _determine_file_type(self, columns: List[str]) -> str:
        """
        Determine file type based on column names.
        
        Args:
            columns: List of column names
            
        Returns:
            File type: "attendance", "learning_process", or "generic"
        """
        columns_str = " ".join(columns).lower()
        
        # Check for attendance file indicators
        if "студент" in columns_str and "курс" in columns_str and "занятие" in columns_str:
            return "attendance"
        
        # Check for learning process file indicators
        if "студент_id" in columns_str and "курс" in columns_str and "время выполнения" in columns_str:
            return "learning_process"
        
        return "generic"
    
    def _process_generic_file(self, df: pd.DataFrame, job_id: str, db: Session) -> Dict[str, Any]:
        """
        Process generic Excel file (fallback).
        
        Args:
            df: DataFrame with data
            job_id: Import job ID
            db: Database session
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing generic file for job {job_id}")
        
        # Simple processing - just count rows
        return {
            "total_rows": len(df),
            "imported_rows": len(df),
            "error_count": 0,
            "file_type": "generic"
        }
    
    def _get_field_mapping(self) -> Dict[str, str]:
        """
        Get field mapping configuration.
        
        Returns:
            Dictionary mapping Excel columns to database fields
        """
        # For now, return a simple mapping
        # In real implementation, this would come from config or database
        return {
            "student_id": "student_id",
            "name": "full_name", 
            "email": "email",
            "course": "course_name",
            "grade": "grade",
            "date": "date"
        }
    
    def _map_columns(self, df: pd.DataFrame, mapping: Dict[str, str], job_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Map Excel columns to database fields.
        
        Args:
            df: Pandas DataFrame
            mapping: Column mapping dictionary
            job_id: Import job ID
            db: Database session
            
        Returns:
            List of mapped records
        """
        mapped_data = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                mapped_row = {}
                
                # Map each column according to mapping
                for excel_col, db_field in mapping.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        
                        # Basic validation
                        if pd.isna(value):
                            value = None
                        elif isinstance(value, (int, float)):
                            value = str(value)
                        else:
                            value = str(value).strip()
                        
                        mapped_row[db_field] = value
                    else:
                        # Column not found in Excel
                        self._log_error(
                            job_id, 
                            index + 1, 
                            excel_col, 
                            "validation", 
                            f"Column '{excel_col}' not found in Excel file",
                            None,
                            db
                        )
                
                mapped_data.append(mapped_row)
                
            except Exception as e:
                self._log_error(
                    job_id,
                    index + 1,
                    None,
                    "mapping",
                    str(e),
                    str(row.to_dict()),
                    db
                )
        
        return mapped_data
    
    def _log_error(self, job_id: str, row_number: int, column_name: Optional[str], 
                   error_type: str, error_message: str, cell_value: Optional[str], db: Session):
        """
        Log import error to database.
        
        Args:
            job_id: Import job ID
            row_number: Row number where error occurred
            column_name: Column name (if applicable)
            error_type: Type of error
            error_message: Error message
            cell_value: Cell value that caused error
            db: Database session
        """
        try:
            error = ImportErrorLog(
                job_id=job_id,
                row_number=row_number,
                column_name=column_name,
                error_type=error_type,
                error_message=error_message,
                cell_value=cell_value
            )
            db.add(error)
            db.commit()
            
            logger.warning(f"Import error logged: {error_type} at row {row_number}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to log import error: {e}")
            db.rollback()
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        unique_filename = f"{timestamp}_{safe_filename}"
        
        file_path = self.upload_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"File saved: {file_path}")
        return str(file_path)
    
    def cleanup_file(self, file_path: str):
        """
        Clean up uploaded file.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
