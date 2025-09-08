"""
LLM Provider for generating student recommendations using Yandex.Cloud.
"""
import logging
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services.config_service import config_service

logger = logging.getLogger("app.llm")

class LLMProvider:
    def __init__(self):
        self.api_key = config_service.get_setting("YANDEX_CLOUD_API_KEY", "")
        self.folder_id = config_service.get_setting("YANDEX_CLOUD_FOLDER_ID", "")
        self.model = config_service.get_setting("YANDEX_CLOUD_MODEL", "yandexgpt")
        self.max_tokens = int(config_service.get_setting("YANDEX_CLOUD_MAX_TOKENS", "1000"))
        self.temperature = float(config_service.get_setting("YANDEX_CLOUD_TEMPERATURE", "0.7"))
        self.timeout = int(config_service.get_setting("YANDEX_CLOUD_TIMEOUT", "30"))
        self.max_retries = int(config_service.get_setting("YANDEX_CLOUD_MAX_RETRIES", "3"))
        
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    def _get_cache_key(self, student_id: str, course_id: str, data_version: str) -> str:
        """Generate cache key for recommendations."""
        cache_data = f"{student_id}:{course_id}:{data_version}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _make_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Make request to Yandex.Cloud LLM API."""
        if not self.api_key or not self.folder_id:
            logger.warning("Yandex.Cloud API key or folder ID not configured, using mock response")
            # Return mock response for testing
            return {
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "text": "1. Увеличьте посещаемость занятий до 90% и выше\n2. Сдавайте задания вовремя, не откладывайте на последний момент\n3. Обращайтесь за помощью к преподавателю при возникновении вопросов"
                            }
                        }
                    ]
                }
            }
            
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": self.max_tokens
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты - помощник преподавателя, который анализирует успеваемость студентов и дает персональные рекомендации для улучшения результатов обучения. Отвечай на русском языке."
                },
                {
                    "role": "user", 
                    "text": prompt
                }
            ]
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Making LLM request (attempt {attempt + 1}/{self.max_retries})")
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("LLM request successful")
                    return result
                else:
                    logger.warning(f"LLM request failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"LLM request timeout (attempt {attempt + 1})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"LLM request error (attempt {attempt + 1}): {e}")
                
            if attempt < self.max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
                
        logger.error("All LLM request attempts failed")
        return None
    
    def _extract_recommendations(self, response: Dict[str, Any]) -> List[str]:
        """Extract recommendations from LLM response."""
        try:
            if "result" in response and "alternatives" in response["result"]:
                alternatives = response["result"]["alternatives"]
                if alternatives and "message" in alternatives[0]:
                    text = alternatives[0]["message"]["text"]
                    
                    # Parse recommendations (assuming they are numbered or bulleted)
                    recommendations = []
                    lines = text.strip().split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if line and (line.startswith(('1.', '2.', '3.', '-', '•', '*')) or 
                                   any(keyword in line.lower() for keyword in ['рекоменд', 'совет', 'предлаг'])):
                            # Clean up the line
                            clean_line = line
                            for prefix in ['1.', '2.', '3.', '-', '•', '*']:
                                if clean_line.startswith(prefix):
                                    clean_line = clean_line[len(prefix):].strip()
                                    break
                            if clean_line:
                                recommendations.append(clean_line)
                    
                    # Limit to 3 recommendations
                    return recommendations[:3]
                    
        except Exception as e:
            logger.error(f"Error extracting recommendations: {e}")
            
        return []
    
    def generate_recommendations(self, student_id: str, course_id: str, student_data: Dict[str, Any]) -> List[str]:
        """
        Generate personalized recommendations for a student.
        
        Args:
            student_id: Student ID
            course_id: Course ID  
            student_data: Student performance data
            
        Returns:
            List of recommendation strings (max 3)
        """
        logger.info(f"Generating recommendations for student {student_id}, course {course_id}")
        
        # Build prompt with student data
        prompt = self._build_prompt(student_data)
        
        # Make LLM request
        response = self._make_request(prompt)
        if not response:
            return []
            
        # Extract recommendations
        recommendations = self._extract_recommendations(response)
        
        logger.info(f"Generated {len(recommendations)} recommendations for student {student_id}")
        return recommendations
    
    def _build_prompt(self, student_data: Dict[str, Any]) -> str:
        """Build prompt for LLM based on student data."""
        prompt_parts = [
            "Проанализируй успеваемость студента и дай 3 персональные рекомендации для улучшения результатов обучения.",
            "",
            "Данные студента:"
        ]
        
        # Add student performance metrics
        if "attendance_rate" in student_data:
            prompt_parts.append(f"- Посещаемость: {student_data['attendance_rate']:.1f}%")
            
        if "task_completion_rate" in student_data:
            prompt_parts.append(f"- Выполнение заданий: {student_data['task_completion_rate']:.1f}%")
            
        if "average_grade" in student_data:
            prompt_parts.append(f"- Средняя оценка: {student_data['average_grade']:.1f}")
            
        if "late_submissions" in student_data:
            prompt_parts.append(f"- Просроченные задания: {student_data['late_submissions']}")
            
        if "risk_level" in student_data:
            prompt_parts.append(f"- Уровень риска: {student_data['risk_level']}")
            
        if "recent_activity" in student_data:
            prompt_parts.append(f"- Последняя активность: {student_data['recent_activity']}")
        
        prompt_parts.extend([
            "",
            "Дай 3 конкретные, практические рекомендации для улучшения успеваемости. ",
            "Рекомендации должны быть:",
            "1. Конкретными и выполнимыми",
            "2. Адаптированными под текущую ситуацию студента", 
            "3. Направленными на улучшение слабых сторон",
            "",
            "Формат ответа: пронумерованный список из 3 рекомендаций."
        ])
        
        return "\n".join(prompt_parts)
    
    def get_cached_recommendations(self, student_id: str, course_id: str, data_version: str) -> Optional[List[str]]:
        """Get cached recommendations if available."""
        try:
            db = next(get_session())
            from app.models.llm_models import LLMRecommendation
            
            cache_key = self._get_cache_key(student_id, course_id, data_version)
            cached = db.query(LLMRecommendation).filter(
                LLMRecommendation.cache_key == cache_key,
                LLMRecommendation.expires_at > datetime.utcnow()
            ).first()
            
            if cached:
                logger.info(f"Found cached recommendations for student {student_id}")
                return json.loads(cached.recommendations_json)
                    
        except Exception as e:
            logger.error(f"Error getting cached recommendations: {e}")
            
        return None
    
    def cache_recommendations(self, student_id: str, course_id: str, data_version: str, 
                            recommendations: List[str], expires_hours: int = 24) -> bool:
        """Cache recommendations for future use."""
        try:
            db = next(get_session())
            from app.models.llm_models import LLMRecommendation
            
            cache_key = self._get_cache_key(student_id, course_id, data_version)
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            # Remove old cache entries
            db.query(LLMRecommendation).filter(
                LLMRecommendation.cache_key == cache_key
            ).delete()
            
            # Create new cache entry
            cached_rec = LLMRecommendation(
                student_id=student_id,
                course_id=course_id,
                cache_key=cache_key,
                data_version=data_version,
                recommendations_json=json.dumps(recommendations, ensure_ascii=False),
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
            
            db.add(cached_rec)
            db.commit()
            
            logger.info(f"Cached {len(recommendations)} recommendations for student {student_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error caching recommendations: {e}")
            return False
