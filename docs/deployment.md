# Руководство по развертыванию PulseEdu

## Обзор

PulseEdu — это система мониторинга образовательного процесса с автоматизированным развертыванием через Docker Compose.

## Быстрый старт

### Автоматическое развертывание (рекомендуется)

```bash
# Клонируем репозиторий
git clone https://github.com/your-org/PulseEdu.git
cd PulseEdu

# Запускаем автоматическое развертывание
./scripts/deploy.sh

# С тестовыми данными
./scripts/deploy.sh --with-test-data
```

### Ручное развертывание

```bash
# 1. Настройка окружения
cp env.example .env
# Отредактируйте .env файл при необходимости

# 2. Запуск инфраструктуры
docker-compose up -d db mq

# 3. Инициализация БД
python3 scripts/init_db.py

# 4. Запуск всех сервисов
docker-compose up -d

# 5. Проверка готовности
python3 scripts/health_check.py
```

## Компоненты системы

### Основные сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| **web** | 8000 | FastAPI веб-приложение |
| **db** | 5432 | PostgreSQL база данных |
| **mq** | 5672, 15672 | RabbitMQ брокер сообщений |

### Вспомогательные сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| **mailhog** | 8025 | Email тестирование |
| **adminer** | 8080 | Управление БД |
| **flower** | 5555 | Мониторинг Celery |

### Воркеры

| Воркер | Очередь | Описание |
|--------|---------|----------|
| **worker_ingest** | ingest | Импорт данных |
| **worker_cluster** | cluster | ML кластеризация |
| **worker_beat** | beat | Периодические задачи |
| **worker_auth** | auth | Аутентификация |
| **worker_email** | email | Отправка писем |
| **worker_llm** | llm | LLM рекомендации |

## Конфигурация

### Переменные окружения

Основные переменные в `.env`:

```bash
# База данных
DB_URL=postgresql://pulseedu:pulseedu@db:5432/pulseedu

# Брокер сообщений
RABBITMQ_URL=amqp://pulseedu:pulseedu@mq:5672//

# Приложение
APP_SECRET=your-secret-key-here
APP_BASE_URL=http://localhost:8000

# Email
SMTP_HOST=mailhog
SMTP_PORT=1025
FROM_EMAIL=noreply@pulseedu.local

# Флаги разработки
LOAD_TEST_DATA=false  # Загрузка тестовых данных
APP_NOW_MODE=real     # Реальное время / тестовое время
HERO_ENABLED=off      # Hero-экраны
```

### Настройка для продакшна

1. **Безопасность:**
   ```bash
   APP_SECRET=your-very-secure-secret-key
   DB_URL=postgresql://user:password@prod-db:5432/pulseedu
   ```

2. **Email (реальный SMTP):**
   ```bash
   SMTP_HOST=smtp.your-provider.com
   SMTP_PORT=587
   SMTP_USER=your-email@domain.com
   SMTP_PASS=your-password
   ```

3. **LLM интеграция:**
   ```bash
   LLM_API_KEY=your-yandex-cloud-api-key
   LLM_ENDPOINT=https://llm.api.cloud.yandex.net/foundationModels/v1/completion
   ```

## Управление системой

### Основные команды

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Перезапуск конкретного сервиса
docker-compose restart web

# Просмотр логов
docker-compose logs -f web
docker-compose logs -f worker_ingest

# Масштабирование воркеров
docker-compose up -d --scale worker_ingest=3
```

### Мониторинг

```bash
# Проверка статуса
docker-compose ps

# Проверка готовности системы
python3 scripts/health_check.py

# Мониторинг Celery
open http://localhost:5555

# Email тестирование
open http://localhost:8025

# Управление БД
open http://localhost:8080
```

### Резервное копирование

```bash
# Бэкап базы данных
docker-compose exec db pg_dump -U pulseedu pulseedu > backup.sql

# Восстановление
docker-compose exec -T db psql -U pulseedu pulseedu < backup.sql
```

## Устранение неполадок

### Частые проблемы

1. **Порт занят:**
   ```bash
   # Проверить занятые порты
   netstat -tulpn | grep :8000
   
   # Изменить порт в docker-compose.yml
   ports:
     - "8001:8000"  # Внешний порт 8001
   ```

2. **БД не подключается:**
   ```bash
   # Проверить логи БД
   docker-compose logs db
   
   # Пересоздать БД
   docker-compose down -v
   docker-compose up -d db
   ```

3. **Воркеры не работают:**
   ```bash
   # Проверить статус воркеров
   docker-compose logs worker_ingest
   
   # Перезапустить воркеры
   docker-compose restart worker_ingest
   ```

### Логи и диагностика

```bash
# Все логи
docker-compose logs

# Логи конкретного сервиса
docker-compose logs web
docker-compose logs worker_cluster

# Логи в реальном времени
docker-compose logs -f web

# Проверка здоровья
curl http://localhost:8000/healthz
```

## Обновление системы

### Обновление кода

```bash
# Получить последние изменения
git pull origin main

# Пересобрать образы
docker-compose build

# Перезапустить сервисы
docker-compose up -d
```

### Миграции базы данных

```bash
# Автоматически применяются при запуске
python3 scripts/init_db.py

# Ручное применение
alembic upgrade head
```

## Безопасность

### Рекомендации для продакшна

1. **Изменить пароли по умолчанию**
2. **Использовать HTTPS**
3. **Настроить файрвол**
4. **Регулярно обновлять зависимости**
5. **Мониторить логи на предмет атак**

### Переменные безопасности

```bash
# Обязательно изменить в продакшне
APP_SECRET=your-very-secure-secret-key
POSTGRES_PASSWORD=secure-db-password
RABBITMQ_DEFAULT_PASS=secure-mq-password
```

## Масштабирование

### Горизонтальное масштабирование

```bash
# Масштабирование воркеров
docker-compose up -d --scale worker_ingest=5
docker-compose up -d --scale worker_cluster=3

# Использование внешних сервисов
# - PostgreSQL: Amazon RDS, Google Cloud SQL
# - RabbitMQ: CloudAMQP, Amazon MQ
# - Redis: для кеширования (будущее)
```

### Вертикальное масштабирование

```bash
# Увеличение ресурсов в docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

## Поддержка

### Получение помощи

1. **Документация:** `docs/` директория
2. **Логи:** `docker-compose logs`
3. **Issues:** GitHub Issues
4. **Health Check:** `python3 scripts/health_check.py`

### Полезные ссылки

- [Docker Compose документация](https://docs.docker.com/compose/)
- [PostgreSQL документация](https://www.postgresql.org/docs/)
- [RabbitMQ документация](https://www.rabbitmq.com/documentation.html)
- [FastAPI документация](https://fastapi.tiangolo.com/)
