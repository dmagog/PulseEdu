"""
LLM Monitoring Service for alerts and statistics.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database.session import get_session
from app.models.llm_models import LLMCallLog
from app.services.config_service import config_service
from app.services.email_service import EmailService

logger = logging.getLogger("app.llm_monitoring")

class LLMMonitoringService:
    def __init__(self):
        self.email_service = EmailService()
        
    def get_llm_statistics(self, hours: int = 24, db: Session = None) -> Dict[str, Any]:
        """
        Get LLM statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            db: Database session
            
        Returns:
            Dictionary with statistics
        """
        if db is None:
            db = next(get_session())
            
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Total calls
            total_calls = db.query(LLMCallLog).filter(
                LLMCallLog.created_at >= since
            ).count()
            
            if total_calls == 0:
                return {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "success_rate": 100.0,
                    "error_rate": 0.0,
                    "avg_response_time": 0,
                    "cache_hit_rate": 0.0,
                    "consecutive_failures": 0
                }
            
            # Successful calls
            successful_calls = db.query(LLMCallLog).filter(
                and_(
                    LLMCallLog.created_at >= since,
                    LLMCallLog.status == "success"
                )
            ).count()
            
            # Failed calls
            failed_calls = db.query(LLMCallLog).filter(
                and_(
                    LLMCallLog.created_at >= since,
                    or_(
                        LLMCallLog.status == "failed",
                        LLMCallLog.status == "error"
                    )
                )
            ).count()
            
            # Calculate rates
            success_rate = (successful_calls / total_calls) * 100
            error_rate = (failed_calls / total_calls) * 100
            
            # Average response time
            avg_response_time = db.query(func.avg(LLMCallLog.response_time_ms)).filter(
                and_(
                    LLMCallLog.created_at >= since,
                    LLMCallLog.response_time_ms.isnot(None)
                )
            ).scalar() or 0
            
            # Cache hit rate
            cached_calls = db.query(LLMCallLog).filter(
                and_(
                    LLMCallLog.created_at >= since,
                    LLMCallLog.status == "cached"
                )
            ).count()
            cache_hit_rate = (cached_calls / total_calls) * 100
            
            # Consecutive failures (last 10 calls)
            recent_calls = db.query(LLMCallLog).filter(
                LLMCallLog.created_at >= since
            ).order_by(LLMCallLog.created_at.desc()).limit(10).all()
            
            consecutive_failures = 0
            for call in recent_calls:
                if call.status in ["failed", "error"]:
                    consecutive_failures += 1
                else:
                    break
            
            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": round(success_rate, 1),
                "error_rate": round(error_rate, 1),
                "avg_response_time": round(avg_response_time, 0),
                "cache_hit_rate": round(cache_hit_rate, 1),
                "consecutive_failures": consecutive_failures
            }
            
        except Exception as e:
            logger.error(f"Error getting LLM statistics: {e}")
            return {}
    
    def check_alerts(self, db: Session = None) -> List[Dict[str, Any]]:
        """
        Check for LLM alerts based on configured thresholds.
        
        Args:
            db: Database session
            
        Returns:
            List of alert dictionaries
        """
        if db is None:
            db = next(get_session())
            
        alerts = []
        
        try:
            # Get configuration
            error_rate_threshold = float(config_service.get_setting("LLM_ALERT_ERROR_RATE_PCT", "10.0"))
            consecutive_failures_threshold = int(config_service.get_setting("LLM_ALERT_CONSECUTIVE_FAILS", "5"))
            alert_email = config_service.get_setting("LLM_ALERT_EMAIL_TO", "")
            monitoring_enabled = config_service.get_setting("LLM_MONITORING_ENABLED", "true").lower() == "true"
            
            if not monitoring_enabled:
                logger.info("LLM monitoring is disabled")
                return alerts
            
            # Get statistics for last 30 minutes
            stats = self.get_llm_statistics(hours=0.5, db=db)
            
            if not stats or stats["total_calls"] == 0:
                logger.info("No LLM calls in the last 30 minutes")
                return alerts
            
            # Check error rate alert
            if stats["error_rate"] > error_rate_threshold:
                alert = {
                    "type": "error_rate",
                    "severity": "high",
                    "message": f"Высокий процент ошибок LLM: {stats['error_rate']}% (порог: {error_rate_threshold}%)",
                    "details": {
                        "error_rate": stats["error_rate"],
                        "threshold": error_rate_threshold,
                        "total_calls": stats["total_calls"],
                        "failed_calls": stats["failed_calls"]
                    }
                }
                alerts.append(alert)
                logger.warning(f"LLM error rate alert: {stats['error_rate']}% > {error_rate_threshold}%")
            
            # Check consecutive failures alert
            if stats["consecutive_failures"] >= consecutive_failures_threshold:
                alert = {
                    "type": "consecutive_failures",
                    "severity": "critical",
                    "message": f"Подряд идущие ошибки LLM: {stats['consecutive_failures']} (порог: {consecutive_failures_threshold})",
                    "details": {
                        "consecutive_failures": stats["consecutive_failures"],
                        "threshold": consecutive_failures_threshold
                    }
                }
                alerts.append(alert)
                logger.warning(f"LLM consecutive failures alert: {stats['consecutive_failures']} >= {consecutive_failures_threshold}")
            
            # Send email alerts if configured
            if alerts and alert_email:
                self._send_alert_email(alerts, alert_email, stats)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking LLM alerts: {e}")
            return []
    
    def _send_alert_email(self, alerts: List[Dict[str, Any]], email: str, stats: Dict[str, Any]):
        """
        Send alert email to administrator.
        
        Args:
            alerts: List of alerts
            email: Email address to send to
            stats: Current LLM statistics
        """
        try:
            # Build email content
            subject = f"Pulse.EDU: LLM Alert - {len(alerts)} проблем обнаружено"
            
            html_content = f"""
            <h2>🚨 Алерты мониторинга LLM</h2>
            <p>Обнаружены проблемы в работе LLM системы:</p>
            
            <h3>Текущая статистика (30 минут):</h3>
            <ul>
                <li>Всего вызовов: {stats.get('total_calls', 0)}</li>
                <li>Успешных: {stats.get('successful_calls', 0)}</li>
                <li>Ошибок: {stats.get('failed_calls', 0)}</li>
                <li>Процент ошибок: {stats.get('error_rate', 0)}%</li>
                <li>Подряд ошибок: {stats.get('consecutive_failures', 0)}</li>
            </ul>
            
            <h3>Алерты:</h3>
            <ul>
            """
            
            for alert in alerts:
                severity_icon = "🔴" if alert["severity"] == "critical" else "🟡"
                html_content += f'<li>{severity_icon} {alert["message"]}</li>'
            
            html_content += """
            </ul>
            
            <p><a href="http://localhost:8000/admin/llm">Перейти к мониторингу LLM</a></p>
            
            <p><small>Это автоматическое сообщение от системы Pulse.EDU</small></p>
            """
            
            self.email_service.send_email(email, subject, html_content)
            logger.info(f"LLM alert email sent to {email}")
            
        except Exception as e:
            logger.error(f"Error sending LLM alert email: {e}")
    
    def get_recent_errors(self, limit: int = 10, db: Session = None) -> List[LLMCallLog]:
        """
        Get recent LLM errors for debugging.
        
        Args:
            limit: Number of recent errors to return
            db: Database session
            
        Returns:
            List of recent error logs
        """
        if db is None:
            db = next(get_session())
            
        try:
            return db.query(LLMCallLog).filter(
                or_(
                    LLMCallLog.status == "failed",
                    LLMCallLog.status == "error"
                )
            ).order_by(LLMCallLog.created_at.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting recent LLM errors: {e}")
            return []
