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
- 4GB свободного места на диске
- Порты 8000, 5432, 5672, 15672, 5555, 8025 должны быть свободны

### Запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/dmagog/PulseEdu.git
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

4. Дождитесь инициализации базы данных (30-60 секунд):
```bash
docker-compose logs db | grep "database system is ready"
```

5. Проверьте, что сервис работает:
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

### Первый запуск

После успешного запуска:

1. Откройте веб-интерфейс: http://localhost:8000
2. Войдите с любым логином (система создаст пользователя автоматически)
3. Перейдите в админ-панель: http://localhost:8000/admin
4. Импортируйте тестовые данные через раздел "Импорт"

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

### Основные переменные

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `DB_URL` | Строка подключения к PostgreSQL | `postgresql://pulseedu:pulseedu@db:5432/pulseedu` |
| `RABBITMQ_URL` | Строка подключения к RabbitMQ | `amqp://pulseedu:pulseedu@mq:5672//` |
| `APP_SECRET` | Секретный ключ приложения | `your-secret-key-here` |
| `APP_BASE_URL` | Базовый URL приложения | `http://localhost:8000` |

### Настройки LLM

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `YANDEX_API_KEY` | API ключ Yandex.Cloud | `""` (заглушка) |
| `YANDEX_FOLDER_ID` | ID папки Yandex.Cloud | `""` (заглушка) |
| `LLM_TIMEOUT_SECONDS` | Таймаут запросов к LLM | `30` |
| `LLM_MAX_RETRIES` | Максимальное количество повторов | `3` |

### Настройки email

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `SMTP_HOST` | SMTP сервер | `mailhog` |
| `SMTP_PORT` | Порт SMTP | `1025` |
| `SMTP_USER` | Пользователь SMTP | `""` |
| `SMTP_PASSWORD` | Пароль SMTP | `""` |
| `SMTP_FROM_EMAIL` | Email отправителя | `noreply@pulseedu.local` |

### Настройки разработки

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `APP_NOW_MODE` | Режим времени (`real`/`fake`) | `real` |
| `APP_FAKE_NOW` | Фиктивная дата для тестирования | `2024-01-15` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `DEBUG` | Режим отладки | `false` |

### Настройки мониторинга

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `LLM_MONITORING_ENABLED` | Включить мониторинг LLM | `true` |
| `LLM_ALERT_ERROR_RATE_PCT` | Порог ошибок для алерта (%) | `10.0` |
| `LLM_ALERT_CONSECUTIVE_FAILS` | Количество подряд ошибок для алерта | `5` |
| `LLM_ALERT_EMAIL_TO` | Email для алертов | `""` |
| `LLM_LOG_RETENTION_DAYS` | Дни хранения логов LLM | `30` |

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

#### Дымовые тесты

Запустите базовые тесты:
```bash
pytest tests/
```

#### Сценарии тестирования

1. **Проверка работоспособности системы:**
```bash
# Проверка health check
curl http://localhost:8000/healthz

# Проверка доступности админ-панели
curl http://localhost:8000/admin
```

2. **Тестирование импорта данных:**
   - Откройте http://localhost:8000/admin
   - Войдите с любым логином
   - Перейдите в раздел "Импорт"
   - Загрузите тестовый Excel файл
   - Проверьте статус импорта в журнале

3. **Тестирование LLM рекомендаций:**
```bash
# Запрос рекомендаций для студента
curl "http://localhost:8000/api/llm/recommendations/01/1"

# Проверка статуса задачи
curl "http://localhost:8000/api/llm/status/{task_id}"
```

4. **Тестирование email уведомлений:**
   - Откройте http://localhost:8025 (MailHog)
   - Сгенерируйте событие (импорт, дедлайн)
   - Проверьте получение письма в MailHog

5. **Тестирование мониторинга:**
   - Откройте http://localhost:8000/admin/llm
   - Проверьте отображение статистики LLM
   - Протестируйте CSV экспорт

6. **Тестирование ролей и доступа:**
   - Войдите как студент: http://localhost:8000/student
   - Войдите как преподаватель: http://localhost:8000/teacher
   - Войдите как РОП: http://localhost:8000/rop
   - Проверьте доступ к админ-панели: http://localhost:8000/admin

#### Мониторинг сервисов

- **Flower (Celery)**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672 (pulseedu/pulseedu)
- **MailHog**: http://localhost:8025
- **Логи контейнеров**: `docker-compose logs [service_name]`

## Статус проекта

Текущая версия: **v0.1.0** (MVP)

Проект находится в активной разработке. См. [план итераций](docs/tasklist.md) для подробной информации о текущем состоянии и планах.

## Документация

### Основная документация
- [Техническое видение](docs/vision.md) - архитектура и принципы системы
- [План итераций](docs/tasklist.md) - текущий статус разработки
- [Соглашения по коду](docs/conventions.md) - стандарты разработки

### Документация для разработчиков
- [DevGuide](docs/devguide.md) - руководство для разработчиков
- [API Reference](docs/api.md) - справочник по API
- [Deploy Guide](docs/deploy.md) - руководство по развертыванию
- [Excel Mapping](docs/excel-mapping.md) - описание импорта данных

## Лицензия

См. файл [LICENSE](LICENSE).

## Поддержка

Для вопросов и предложений создавайте issues в репозитории проекта.