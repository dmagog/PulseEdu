# Пульс.EDU

Система аналитики и рекомендаций для образовательного процесса.

## Описание

Пульс.EDU — это MVP сервиса для мониторинга успеваемости студентов, генерации рекомендаций с помощью LLM и управления образовательным процессом. Система предназначена для студентов, преподавателей и руководителей образовательных программ (РОП).

## Технологии

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **База данных**: PostgreSQL 15, SQLModel, Alembic
- **Очереди**: Celery, RabbitMQ, Flower
- **UI**: Jinja2, Bootstrap
- **LLM**: Yandex.Cloud (внешний сервис)
- **Контейнеризация**: Docker, docker-compose

## Быстрый старт

### Предварительные требования

- Docker и docker-compose
- Git

### Запуск

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd PulseEdu
```

2. Скопируйте файл с переменными окружения:
```bash
cp env.example .env
```

3. Запустите все сервисы:
```bash
docker-compose up -d
```

4. Проверьте, что сервис работает:
```bash
curl http://localhost:8000/healthz
```

Ожидаемый ответ:
```json
{
  "status": "ok",
  "service": "PulseEdu",
  "version": "0.1.0"
}
```

### Доступные сервисы

- **Web приложение**: http://localhost:8000
- **Flower (мониторинг Celery)**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672 (pulseedu/pulseedu)
- **MailHog (тестирование email)**: http://localhost:8025

## Структура проекта

```
app/
├── main.py              # Точка входа FastAPI
├── database/            # Работа с БД
├── models/              # SQLModel модели
├── routes/              # HTTP эндпоинты
├── services/            # Бизнес-логика
└── ui/                  # Шаблоны и статика

worker/
├── celery_app.py        # Конфигурация Celery
└── tasks.py             # Фоновые задачи

docs/                    # Документация проекта
migrations/              # Миграции Alembic
tests/                   # Тесты
```

## Переменные окружения

Основные переменные (см. `.env.example`):

- `DB_URL` - строка подключения к PostgreSQL
- `RABBITMQ_URL` - строка подключения к RabbitMQ
- `APP_SECRET` - секретный ключ приложения
- `APP_BASE_URL` - базовый URL приложения

## Разработка

### Локальная разработка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите только базу данных и брокер сообщений:
```bash
docker-compose up -d db mq
```

3. Запустите приложение локально:
```bash
uvicorn app.main:app --reload
```

### Тестирование

Запустите дымовые тесты:
```bash
pytest tests/
```

## Статус проекта

Текущая версия: **v0.1.0** (MVP)

Проект находится в активной разработке. См. [план итераций](docs/tasklist.md) для подробной информации о текущем состоянии и планах.

## Документация

- [Техническое видение](docs/vision.md)
- [План итераций](docs/tasklist.md)
- [Соглашения по коду](docs/conventions.md)

## Лицензия

См. файл [LICENSE](LICENSE).

## Поддержка

Для вопросов и предложений создавайте issues в репозитории проекта.