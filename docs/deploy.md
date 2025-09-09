# Deploy Guide - Руководство по развертыванию

Версия: v0.1 · Дата: 2025-09-08

## Содержание

1. [Общая информация](#общая-информация)
2. [Требования к системе](#требования-к-системе)
3. [Развертывание в Docker](#развертывание-в-docker)
4. [Настройка окружения](#настройка-окружения)
5. [Миграции базы данных](#миграции-базы-данных)
6. [Настройка почты](#настройка-почты)
7. [Конфигурация воркеров](#конфигурация-воркеров)
8. [Мониторинг](#мониторинг)
9. [Безопасность](#безопасность)
10. [Резервное копирование](#резервное-копирование)
11. [Обновление системы](#обновление-системы)
12. [Устранение неполадок](#устранение-неполадок)

---

## Общая информация

PulseEdu - это веб-приложение для мониторинга образовательного процесса, построенное на FastAPI, PostgreSQL и Celery. Система развертывается с использованием Docker и docker-compose.

### Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Server    │    │   PostgreSQL    │    │   RabbitMQ      │
│   (FastAPI)     │◄──►│   (Database)    │    │   (Message      │
│   Port: 8000    │    │   Port: 5432    │    │    Broker)      │
└─────────────────┘    └─────────────────┘    │   Port: 5672    │
         │                                      └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Celery        │    │   Celery        │    │   Celery        │
│   Workers       │    │   Beat          │    │   Flower        │
│   (Background   │    │   (Scheduler)   │    │   (Monitoring)  │
│    Tasks)       │    │                 │    │   Port: 5555    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Требования к системе

### Минимальные требования

| Компонент | Требование |
|-----------|------------|
| **CPU** | 2 ядра |
| **RAM** | 4 GB |
| **Диск** | 20 GB свободного места |
| **ОС** | Linux (Ubuntu 20.04+, CentOS 8+) |
| **Docker** | 20.10+ |
| **Docker Compose** | 2.0+ |

### Рекомендуемые требования

| Компонент | Требование |
|-----------|------------|
| **CPU** | 4 ядра |
| **RAM** | 8 GB |
| **Диск** | 50 GB SSD |
| **ОС** | Ubuntu 22.04 LTS |
| **Docker** | 24.0+ |
| **Docker Compose** | 2.20+ |

### Сетевые требования

| Порт | Сервис | Назначение |
|------|--------|------------|
| 8000 | Web | HTTP API и веб-интерфейс |
| 5432 | PostgreSQL | База данных |
| 5672 | RabbitMQ | Брокер сообщений |
| 15672 | RabbitMQ Management | Веб-интерфейс управления |
| 5555 | Flower | Мониторинг Celery |
| 8025 | MailHog | Тестирование email (dev) |

---

## Развертывание в Docker

### 1. Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Клонирование репозитория

```bash
# Клонирование
git clone https://github.com/dmagog/PulseEdu.git
cd PulseEdu

# Создание файла окружения
cp env.example .env
```

### 3. Настройка переменных окружения

Отредактируйте файл `.env`:

```bash
# Основные настройки
APP_SECRET=your-super-secret-key-here
APP_BASE_URL=https://your-domain.com
DEBUG=false

# База данных
DB_URL=postgresql://pulseedu:pulseedu@db:5432/pulseedu

# Брокер сообщений
RABBITMQ_URL=amqp://pulseedu:pulseedu@mq:5672//

# LLM настройки
YANDEX_API_KEY=your-yandex-api-key
YANDEX_FOLDER_ID=your-folder-id
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=3

# Email настройки
SMTP_HOST=smtp.your-domain.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-email-password
SMTP_FROM_EMAIL=noreply@your-domain.com

# Мониторинг
LLM_MONITORING_ENABLED=true
LLM_ALERT_ERROR_RATE_PCT=10.0
LLM_ALERT_CONSECUTIVE_FAILS=5
LLM_ALERT_EMAIL_TO=admin@your-domain.com
LLM_LOG_RETENTION_DAYS=30
```

### 4. Запуск системы

```bash
# Сборка и запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### 5. Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/healthz

# Проверка базы данных
docker-compose exec db psql -U pulseedu -d pulseedu -c "SELECT version();"

# Проверка RabbitMQ
curl http://localhost:15672
```

---

## Настройка окружения

### Переменные окружения по средам

#### Development (разработка)

```bash
DEBUG=true
LOG_LEVEL=DEBUG
APP_NOW_MODE=fake
APP_FAKE_NOW=2024-01-15
SMTP_HOST=mailhog
SMTP_PORT=1025
```

#### Staging (тестирование)

```bash
DEBUG=false
LOG_LEVEL=INFO
APP_NOW_MODE=real
SMTP_HOST=smtp.staging.com
SMTP_PORT=587
```

#### Production (продакшн)

```bash
DEBUG=false
LOG_LEVEL=WARNING
APP_NOW_MODE=real
SMTP_HOST=smtp.production.com
SMTP_PORT=587
```

### Настройка домена

```bash
# В .env
APP_BASE_URL=https://pulseedu.your-domain.com

# В nginx (если используется)
server {
    listen 80;
    server_name pulseedu.your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Миграции базы данных

### Автоматическое применение миграций

```bash
# При первом запуске
docker-compose exec web alembic upgrade head

# Проверка текущей версии
docker-compose exec web alembic current

# Просмотр истории миграций
docker-compose exec web alembic history
```

### Создание новых миграций

```bash
# После изменения моделей
docker-compose exec web alembic revision --autogenerate -m "Описание изменений"

# Применение новой миграции
docker-compose exec web alembic upgrade head
```

### Откат миграций

```bash
# Откат на одну версию назад
docker-compose exec web alembic downgrade -1

# Откат до конкретной версии
docker-compose exec web alembic downgrade <revision_id>
```

### Резервное копирование перед миграциями

```bash
# Создание бэкапа
docker-compose exec db pg_dump -U pulseedu pulseedu > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker-compose exec -T db psql -U pulseedu pulseedu < backup_20240115_120000.sql
```

---

## Настройка почты

### SMTP конфигурация

#### Gmail

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

#### Yandex

```bash
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=587
SMTP_USER=your-email@yandex.ru
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=your-email@yandex.ru
```

#### Custom SMTP

```bash
SMTP_HOST=mail.your-domain.com
SMTP_PORT=587
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=noreply@your-domain.com
```

### Тестирование email

```bash
# Отправка тестового письма
docker-compose exec web python -c "
from app.services.email_service import email_service
email_service.send_test_email('test@example.com')
"
```

### Настройка SPF/DKIM

Для улучшения доставляемости писем настройте DNS записи:

```
# SPF запись
TXT @ "v=spf1 include:_spf.google.com ~all"

# DKIM запись (получите у провайдера почты)
TXT default._domainkey "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY"
```

---

## Конфигурация воркеров

### Настройка очередей

```yaml
# docker-compose.yml
services:
  worker_ingest:
    build: .
    command: celery -A worker.celery_app worker --loglevel=info --queues=ingest --concurrency=2
    environment:
      - CELERY_QUEUE=ingest
      - CELERY_CONCURRENCY=2

  worker_llm:
    build: .
    command: celery -A worker.celery_app worker --loglevel=info --queues=llm --concurrency=1
    environment:
      - CELERY_QUEUE=llm
      - CELERY_CONCURRENCY=1

  worker_email:
    build: .
    command: celery -A worker.celery_app worker --loglevel=info --queues=email --concurrency=3
    environment:
      - CELERY_QUEUE=email
      - CELERY_CONCURRENCY=3
```

### Масштабирование воркеров

```bash
# Увеличение количества воркеров
docker-compose up -d --scale worker_ingest=3 --scale worker_llm=2

# Проверка статуса
docker-compose ps | grep worker
```

### Мониторинг задач

```bash
# Просмотр активных задач
docker-compose exec worker_ingest celery -A worker.celery_app inspect active

# Просмотр статистики
docker-compose exec worker_ingest celery -A worker.celery_app inspect stats

# Очистка очередей
docker-compose exec worker_ingest celery -A worker.celery_app purge
```

---

## Мониторинг

### Health Checks

```bash
# Основной health check
curl http://localhost:8000/healthz

# Расширенный health check
curl http://localhost:8000/health

# Проверка базы данных
docker-compose exec db pg_isready -U pulseedu

# Проверка RabbitMQ
curl http://localhost:15672/api/overview
```

### Логирование

```bash
# Просмотр логов всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f web
docker-compose logs -f worker_llm

# Логи с фильтрацией
docker-compose logs web | grep ERROR
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
docker system df

# Очистка неиспользуемых ресурсов
docker system prune -a
```

### Настройка логирования

```bash
# В .env
LOG_LEVEL=INFO
LOG_FORMAT=json

# Ротация логов в docker-compose.yml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Безопасность

### Настройка SSL/TLS

```bash
# Использование Let's Encrypt
sudo apt install certbot nginx

# Получение сертификата
sudo certbot --nginx -d pulseedu.your-domain.com

# Автообновление
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Настройка файрвола

```bash
# UFW
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Блокируем прямой доступ к приложению
```

### Безопасность базы данных

```bash
# Смена паролей по умолчанию
# В .env
DB_URL=postgresql://pulseedu:STRONG_PASSWORD@db:5432/pulseedu
RABBITMQ_URL=amqp://pulseedu:STRONG_PASSWORD@mq:5672//

# Ограничение доступа к БД
# В docker-compose.yml
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "127.0.0.1:5432:5432"  # Только локальный доступ
```

### Безопасность приложения

```bash
# Секретный ключ
APP_SECRET=your-very-long-random-secret-key-here

# Отключение debug в продакшне
DEBUG=false

# Настройка CORS
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

---

## Резервное копирование

### Автоматическое резервное копирование

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="pulseedu"

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Бэкап базы данных
docker-compose exec -T db pg_dump -U pulseedu $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Бэкап файлов (если есть)
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz /path/to/uploaded/files

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Настройка cron для автоматических бэкапов

```bash
# Добавить в crontab
crontab -e

# Ежедневный бэкап в 2:00
0 2 * * * /path/to/backup.sh

# Еженедельный бэкап в воскресенье в 3:00
0 3 * * 0 /path/to/backup.sh
```

### Восстановление из бэкапа

```bash
# Остановка приложения
docker-compose down

# Восстановление базы данных
docker-compose up -d db
sleep 10
docker-compose exec -T db psql -U pulseedu pulseedu < backup_20240115_120000.sql

# Восстановление файлов
tar -xzf files_backup_20240115_120000.tar.gz -C /

# Запуск приложения
docker-compose up -d
```

---

## Обновление системы

### Обновление кода

```bash
# Создание бэкапа
./backup.sh

# Получение обновлений
git fetch origin
git checkout main
git pull origin main

# Пересборка образов
docker-compose build

# Применение миграций
docker-compose exec web alembic upgrade head

# Перезапуск сервисов
docker-compose up -d
```

### Обновление зависимостей

```bash
# Обновление Python пакетов
docker-compose exec web pip install --upgrade -r requirements.txt

# Пересборка образа
docker-compose build web
docker-compose up -d web
```

### Откат изменений

```bash
# Откат к предыдущей версии
git checkout <previous-commit-hash>

# Откат миграций
docker-compose exec web alembic downgrade -1

# Перезапуск
docker-compose up -d
```

---

## Устранение неполадок

### Частые проблемы

#### 1. Контейнеры не запускаются

```bash
# Проверка логов
docker-compose logs

# Проверка портов
netstat -tulpn | grep :8000

# Перезапуск
docker-compose down
docker-compose up -d
```

#### 2. Ошибки подключения к базе данных

```bash
# Проверка статуса БД
docker-compose exec db pg_isready -U pulseedu

# Проверка переменных окружения
docker-compose exec web env | grep DB_URL

# Перезапуск БД
docker-compose restart db
```

#### 3. Задачи Celery не выполняются

```bash
# Проверка статуса воркеров
docker-compose exec worker_ingest celery -A worker.celery_app inspect active

# Перезапуск воркеров
docker-compose restart worker_ingest worker_llm worker_email

# Очистка очередей
docker-compose exec worker_ingest celery -A worker.celery_app purge
```

#### 4. Проблемы с памятью

```bash
# Проверка использования памяти
docker stats

# Очистка неиспользуемых ресурсов
docker system prune -a

# Увеличение лимитов в docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Диагностические команды

```bash
# Проверка всех сервисов
docker-compose ps

# Проверка сетей
docker network ls
docker network inspect pulseedu_default

# Проверка томов
docker volume ls
docker volume inspect pulseedu_postgres_data

# Проверка образов
docker images
```

### Получение поддержки

При возникновении проблем:

1. **Соберите информацию**:
   ```bash
   docker-compose logs > logs.txt
   docker-compose ps > services.txt
   docker system info > system.txt
   ```

2. **Создайте issue** в репозитории с приложением логов

3. **Опишите проблему**:
   - Что делали
   - Что ожидали
   - Что получили
   - Версия системы и Docker

---

## Полезные команды

### Управление сервисами

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Перезапуск конкретного сервиса
docker-compose restart web

# Просмотр статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f web
```

### Управление данными

```bash
# Подключение к базе данных
docker-compose exec db psql -U pulseedu -d pulseedu

# Создание бэкапа
docker-compose exec db pg_dump -U pulseedu pulseedu > backup.sql

# Восстановление из бэкапа
docker-compose exec -T db psql -U pulseedu pulseedu < backup.sql
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose logs -f

# Статус Celery
curl http://localhost:5555
```

---

## Контакты

Для вопросов по развертыванию:
- Создавайте issues в репозитории
- Изучайте [DevGuide](devguide.md) для технических деталей
- Проверяйте [API Reference](api.md) для работы с API
