#!/usr/bin/env python3
"""
Скрипт проверки готовности системы PulseEdu
Проверяет доступность всех компонентов системы
"""

import logging
import os
import sys
import time
from pathlib import Path

import requests

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_database():
    """Проверяет доступность базы данных"""
    try:
        from app.database.session import engine

        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()

        logger.info("✅ База данных доступна")
        return True
    except Exception as e:
        logger.error(f"❌ База данных недоступна: {e}")
        return False


def check_rabbitmq():
    """Проверяет доступность RabbitMQ"""
    try:
        import pika

        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://pulseedu:pulseedu@localhost:5672//")
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        connection.close()

        logger.info("✅ RabbitMQ доступен")
        return True
    except Exception as e:
        logger.error(f"❌ RabbitMQ недоступен: {e}")
        return False


def check_web_app():
    """Проверяет доступность веб-приложения"""
    try:
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # Проверяем health endpoint
        response = requests.get(f"{base_url}/healthz", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Веб-приложение доступно")
            return True
        else:
            logger.error(f"❌ Веб-приложение недоступно: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Веб-приложение недоступно: {e}")
        return False


def check_celery_workers():
    """Проверяет доступность Celery workers"""
    try:
        # Проверяем Flower если доступен
        flower_url = "http://localhost:5555"
        try:
            response = requests.get(f"{flower_url}/api/workers", timeout=5)
            if response.status_code == 200:
                workers = response.json()
                active_workers = [w for w in workers.values() if w.get("status")]
                if active_workers:
                    logger.info(f"✅ Celery workers активны: {len(active_workers)} воркеров")
                    return True
                else:
                    logger.warning("⚠️ Celery workers неактивны")
                    return False
        except:
            logger.warning("⚠️ Flower недоступен, пропускаем проверку workers")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки Celery workers: {e}")
        return False


def check_mailhog():
    """Проверяет доступность MailHog"""
    try:
        response = requests.get("http://localhost:8025", timeout=5)
        if response.status_code == 200:
            logger.info("✅ MailHog доступен")
            return True
        else:
            logger.warning("⚠️ MailHog недоступен")
            return False
    except Exception as e:
        logger.warning(f"⚠️ MailHog недоступен: {e}")
        return False


def check_adminer():
    """Проверяет доступность Adminer"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Adminer доступен")
            return True
        else:
            logger.warning("⚠️ Adminer недоступен")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Adminer недоступен: {e}")
        return False


def main():
    """Основная функция проверки"""
    logger.info("🔍 Запуск проверки готовности системы PulseEdu")

    checks = [
        ("База данных", check_database),
        ("RabbitMQ", check_rabbitmq),
        ("Веб-приложение", check_web_app),
        ("Celery workers", check_celery_workers),
        ("MailHog", check_mailhog),
        ("Adminer", check_adminer),
    ]

    results = []
    for name, check_func in checks:
        logger.info(f"Проверка {name}...")
        result = check_func()
        results.append((name, result))

        if not result and name in ["База данных", "RabbitMQ", "Веб-приложение"]:
            logger.error(f"❌ Критический компонент {name} недоступен")
            sys.exit(1)

    # Выводим итоговый отчет
    logger.info("\n📊 Результаты проверки:")
    for name, result in results:
        status = "✅ OK" if result else "❌ FAIL"
        logger.info(f"  {name}: {status}")

    failed_checks = [name for name, result in results if not result]
    if failed_checks:
        logger.warning(f"⚠️ Недоступные компоненты: {', '.join(failed_checks)}")
    else:
        logger.info("🎉 Все компоненты системы готовы к работе!")


if __name__ == "__main__":
    main()
