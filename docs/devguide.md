# DevGuide - Руководство для разработчиков

Версия: v0.1 · Дата: 2025-09-08

## Содержание

1. [Структура проекта](#структура-проекта)
2. [Настройка окружения](#настройка-окружения)
3. [Работа с базой данных](#работа-с-базой-данных)
4. [Архитектура приложения](#архитектура-приложения)
5. [Стиль кода](#стиль-кода)
6. [Логирование](#логирование)
7. [Очереди и задачи](#очереди-и-задачи)
8. [Тестирование](#тестирование)
9. [Отладка](#отладка)

---

## Структура проекта

```
PulseEdu/
├── app/                    # Основное приложение
│   ├── __init__.py
│   ├── main.py            # Точка входа FastAPI
│   ├── database/          # Работа с БД
│   │   ├── __init__.py
│   │   ├── engine.py      # Настройка подключения к БД
│   │   └── session.py     # Сессии SQLAlchemy
│   ├── models/            # SQLModel модели
│   │   ├── __init__.py
│   │   ├── user.py        # Пользователи и роли
│   │   ├── student.py     # Студенты и курсы
│   │   ├── import.py      # Импорт данных
│   │   └── llm_models.py  # LLM и рекомендации
│   ├── routes/            # HTTP эндпоинты
│   │   ├── __init__.py
│   │   ├── health.py      # Health check
│   │   ├── auth.py        # Авторизация
│   │   ├── admin.py       # Админ-панель
│   │   ├── student.py     # Интерфейс студента
│   │   ├── teacher.py     # Интерфейс преподавателя
│   │   ├── rop.py         # Интерфейс РОП
│   │   ├── import.py      # Импорт данных
│   │   └── llm_routes.py  # LLM API
│   ├── services/          # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── config_service.py      # Конфигурация
│   │   ├── rbac_service.py        # Роли и права
│   │   ├── student_service.py     # Логика студентов
│   │   ├── teacher_service.py     # Логика преподавателей
│   │   ├── metrics_service.py     # Метрики и дедлайны
│   │   ├── cluster_service.py     # Кластеризация
│   │   ├── import_service.py      # Импорт данных
│   │   ├── email_service.py       # Email уведомления
│   │   ├── llm_provider.py        # LLM интеграция
│   │   └── llm_monitoring_service.py # Мониторинг LLM
│   ├── middleware/        # Middleware
│   │   ├── __init__.py
│   │   └── auth.py        # Авторизация
│   └── ui/               # UI компоненты
│       ├── static/       # CSS, JS, изображения
│       └── templates/    # Jinja2 шаблоны
├── worker/               # Celery воркеры
│   ├── __init__.py
│   ├── celery_app.py     # Конфигурация Celery
│   ├── tasks.py          # Основные задачи
│   ├── ingest_tasks.py   # Импорт данных
│   ├── email_tasks.py    # Email задачи
│   ├── llm_tasks.py      # LLM задачи
│   ├── cluster_tasks.py  # Кластеризация
│   └── beat_tasks.py     # Периодические задачи
├── migrations/           # Миграции Alembic
├── tests/               # Тесты
├── docs/               # Документация
├── docker-compose.yml  # Docker конфигурация
├── Dockerfile         # Docker образ
├── requirements.txt   # Python зависимости
└── .env.example      # Пример переменных окружения
```

---

## Настройка окружения

### Локальная разработка

1. **Клонирование и настройка:**
```bash
git clone https://github.com/dmagog/PulseEdu.git
cd PulseEdu
cp env.example .env
```

2. **Запуск зависимостей:**
```bash
# Только БД и брокер сообщений
docker-compose up -d db mq

# Или все сервисы
docker-compose up -d
```

3. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

4. **Запуск приложения:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Переменные окружения

Основные переменные для разработки:

```bash
# База данных
DB_URL=postgresql://pulseedu:pulseedu@localhost:5432/pulseedu

# Брокер сообщений
RABBITMQ_URL=amqp://pulseedu:pulseedu@localhost:5672//

# Приложение
APP_SECRET=dev-secret-key
APP_BASE_URL=http://localhost:8000
DEBUG=true
LOG_LEVEL=DEBUG

# Тестовые часы
APP_NOW_MODE=fake
APP_FAKE_NOW=2024-01-15
```

---

## Работа с базой данных

### Миграции Alembic

1. **Создание миграции:**
```bash
# После изменения моделей
alembic revision --autogenerate -m "Описание изменений"
```

2. **Применение миграций:**
```bash
# В Docker
docker-compose exec web alembic upgrade head

# Локально
alembic upgrade head
```

3. **Откат миграции:**
```bash
alembic downgrade -1
```

### Модели SQLModel

Пример создания модели:

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Student(SQLModel, table=True):
    id: Optional[str] = Field(primary_key=True)
    name: str
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Связи
    courses: List["Course"] = Relationship(back_populates="students")
```

### Работа с сессиями

```python
from app.database.session import get_session
from sqlalchemy.orm import Session

def some_function(db: Session = Depends(get_session)):
    # Использование сессии
    students = db.query(Student).all()
    return students
```

---

## Архитектура приложения

### Слои приложения

1. **Routes** - HTTP эндпоинты, валидация входных данных
2. **Services** - Бизнес-логика, работа с данными
3. **Models** - Модели данных, связи
4. **Workers** - Фоновые задачи, интеграции

### Принципы

- **KISS** - простота и понятность
- **Разделение ответственности** - каждый модуль имеет четкую роль
- **Dependency Injection** - зависимости через FastAPI Depends
- **Асинхронность** - для I/O операций

### Пример структуры роута

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_session
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["students"])

@router.get("/{student_id}")
async def get_student(
    student_id: str,
    db: Session = Depends(get_session)
):
    try:
        student = StudentService.get_by_id(student_id, db)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student
    except Exception as e:
        logger.error(f"Error getting student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Стиль кода

### Python

- **PEP 8** - стандартный стиль Python
- **Type hints** - обязательны для всех функций
- **Docstrings** - для публичных функций и классов
- **Именование** - snake_case для переменных и функций, PascalCase для классов

### Примеры

```python
def calculate_student_progress(
    student_id: str, 
    course_id: str, 
    db: Session
) -> Dict[str, Any]:
    """
    Вычисляет прогресс студента по курсу.
    
    Args:
        student_id: ID студента
        course_id: ID курса
        db: Сессия базы данных
        
    Returns:
        Словарь с метриками прогресса
        
    Raises:
        ValueError: Если студент или курс не найдены
    """
    # Реализация
    pass
```

### Импорты

```python
# Стандартная библиотека
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Сторонние библиотеки
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Локальные импорты
from app.database.session import get_session
from app.services.student_service import StudentService
```

---

## Логирование

### Конфигурация

```python
import logging

logger = logging.getLogger(__name__)

# В функциях
logger.info(f"Processing student {student_id}", extra={
    "student_id": student_id,
    "request_id": request_id
})
```

### Уровни логирования

- **DEBUG** - детальная информация для отладки
- **INFO** - общая информация о работе
- **WARNING** - предупреждения о потенциальных проблемах
- **ERROR** - ошибки, не прерывающие работу
- **CRITICAL** - критические ошибки

### Структурированное логирование

```python
logger.info("Student progress calculated", extra={
    "student_id": student_id,
    "course_id": course_id,
    "progress_percent": 75.5,
    "request_id": request_id
})
```

---

## Очереди и задачи

### Celery конфигурация

```python
from celery import Celery

celery_app = Celery("pulseedu")

celery_app.conf.update(
    broker_url="amqp://pulseedu:pulseedu@mq:5672//",
    result_backend="rpc://",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

### Создание задачи

```python
@celery_app.task(name="student.calculate_progress")
def calculate_student_progress_task(student_id: str, course_id: str):
    """
    Фоновая задача для вычисления прогресса студента.
    """
    logger.info(f"Calculating progress for student {student_id}")
    
    try:
        db = next(get_session())
        result = StudentService.calculate_progress(student_id, course_id, db)
        
        logger.info(f"Progress calculated successfully", extra={
            "student_id": student_id,
            "course_id": course_id,
            "progress": result["progress_percent"]
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating progress: {e}")
        raise
```

### Маршрутизация задач

```python
celery_app.conf.task_routes = {
    'worker.ingest_tasks.*': {'queue': 'ingest'},
    'worker.email_tasks.*': {'queue': 'email'},
    'worker.llm_tasks.*': {'queue': 'llm'},
    'worker.cluster_tasks.*': {'queue': 'cluster'},
}
```

---

## Тестирование

### Структура тестов

```
tests/
├── __init__.py
├── conftest.py          # Фикстуры pytest
├── test_models.py       # Тесты моделей
├── test_services.py     # Тесты сервисов
├── test_routes.py       # Тесты API
└── test_workers.py      # Тесты задач
```

### Пример теста

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_student_not_found():
    response = client.get("/api/students/nonexistent")
    assert response.status_code == 404
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app

# Конкретный файл
pytest tests/test_models.py

# С verbose выводом
pytest -v
```

---

## Отладка

### Логи контейнеров

```bash
# Все сервисы
docker-compose logs

# Конкретный сервис
docker-compose logs web
docker-compose logs worker_llm

# Следить за логами
docker-compose logs -f web
```

### Отладка в коде

```python
import logging
import pdb

logger = logging.getLogger(__name__)

def debug_function():
    logger.debug("Debug point reached")
    
    # Точка останова
    pdb.set_trace()
    
    # Продолжение выполнения
    pass
```

### Мониторинг задач

- **Flower**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672
- **MailHog**: http://localhost:8025

### Частые проблемы

1. **Ошибки подключения к БД** - проверьте переменные окружения
2. **Задачи не выполняются** - проверьте статус воркеров в Flower
3. **Ошибки миграций** - убедитесь, что БД запущена
4. **Проблемы с правами** - проверьте RBAC конфигурацию

---

## Полезные команды

### Docker

```bash
# Перезапуск сервиса
docker-compose restart web

# Пересборка образа
docker-compose build web

# Очистка контейнеров
docker-compose down -v
```

### База данных

```bash
# Подключение к БД
docker-compose exec db psql -U pulseedu -d pulseedu

# Сброс БД
docker-compose exec db psql -U pulseedu -d pulseedu -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Celery

```bash
# Запуск воркера
docker-compose exec worker_llm celery -A worker.celery_app worker --loglevel=info

# Мониторинг задач
docker-compose exec worker_llm celery -A worker.celery_app inspect active
```

---

## Контакты

Для вопросов по разработке:
- Создавайте issues в репозитории
- Следуйте [соглашениям по коду](conventions.md)
- Изучайте [техническое видение](vision.md)
