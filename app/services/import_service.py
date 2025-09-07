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

from app.models.import_models import ImportJob, ImportError
from app.services.config_service import config_service

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
            
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Get mapping configuration
            mapping = self._get_field_mapping()
            
            # Validate and map columns
            mapped_data = self._map_columns(df, mapping, job_id, db)
            
            # Update job status
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if job:
                job.total_rows = len(df)
                job.status = "processing"
                job.started_at = datetime.utcnow()
                db.commit()
            
            logger.info(f"Excel parsing completed for job {job_id}: {len(df)} rows")
            
            return {
                "total_rows": len(df),
                "mapped_data": mapped_data,
                "mapping": mapping
            }
            
        except Exception as e:
            logger.error(f"Excel parsing failed for job {job_id}: {e}")
            self._log_error(job_id, 0, None, "parsing", str(e), None, db)
            raise
    
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
            error = ImportError(
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
