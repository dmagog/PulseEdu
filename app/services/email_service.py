"""
Email service for sending notifications.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("app.email")


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "mailhog")
        self.smtp_port = int(os.getenv("SMTP_PORT", "1025"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@pulseedu.local")
        self.from_name = os.getenv("FROM_NAME", "Pulse.EDU")

        # Jinja2 environment for email templates
        # Use absolute path for Docker compatibility
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_dir = os.path.join(app_dir, "ui", "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                msg.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}, subject: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_import_completion(self, job_id: str, user_email: str, job_details: Dict[str, Any]) -> bool:
        """
        Send email notification about import completion.

        Args:
            job_id: Import job ID
            user_email: User email address
            job_details: Job details (rows processed, errors, etc.)

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.jinja_env.get_template("email/import_completion.html")
            html_content = template.render(job_id=job_id, user_email=user_email, **job_details)

            subject = f"Импорт данных завершён - {job_id}"
            return self._send_email(user_email, subject, html_content)

        except Exception as e:
            logger.error(f"Failed to send import completion email: {e}")
            return False

    def send_import_error(self, job_id: str, user_email: str, error_message: str) -> bool:
        """
        Send email notification about import error.

        Args:
            job_id: Import job ID
            user_email: User email address
            error_message: Error message

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.jinja_env.get_template("import_error.html")
            html_content = template.render(job_id=job_id, user_email=user_email, error_message=error_message)

            subject = f"Ошибка импорта данных - {job_id}"
            return self._send_email(user_email, subject, html_content)

        except Exception as e:
            logger.error(f"Failed to send import error email: {e}")
            return False

    def send_deadline_reminder(self, student_email: str, task_name: str, deadline: str, course_name: str) -> bool:
        """
        Send email reminder about approaching deadline.

        Args:
            student_email: Student email address
            task_name: Task name
            deadline: Deadline date
            course_name: Course name

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.jinja_env.get_template("deadline_reminder.html")
            html_content = template.render(
                student_email=student_email, task_name=task_name, deadline=deadline, course_name=course_name
            )

            subject = f"Напоминание о дедлайне: {task_name}"
            return self._send_email(student_email, subject, html_content)

        except Exception as e:
            logger.error(f"Failed to send deadline reminder email: {e}")
            return False

    def send_metrics_update(self, user_email: str, update_summary: Dict[str, Any]) -> bool:
        """
        Send email notification about metrics update.

        Args:
            user_email: User email address
            update_summary: Summary of metrics update

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.jinja_env.get_template("metrics_update.html")
            html_content = template.render(user_email=user_email, **update_summary)

            subject = "Обновление метрик системы"
            return self._send_email(user_email, subject, html_content)

        except Exception as e:
            logger.error(f"Failed to send metrics update email: {e}")
            return False
