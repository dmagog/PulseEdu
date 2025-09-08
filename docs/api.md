# API Reference - Справочник по API

Версия: v0.1 · Дата: 2025-09-08

## Содержание

1. [Общая информация](#общая-информация)
2. [Аутентификация](#аутентификация)
3. [Роли и права доступа](#роли-и-права-доступа)
4. [Эндпоинты по ролям](#эндпоинты-по-ролям)
5. [Форматы данных](#форматы-данных)
6. [Коды ошибок](#коды-ошибок)
7. [Примеры запросов](#примеры-запросов)

---

## Общая информация

### Базовый URL
```
http://localhost:8000
```

### Форматы данных
- **Content-Type**: `application/json`
- **Response**: JSON
- **Кодировка**: UTF-8

### Аутентификация
Система использует cookie-based аутентификацию. После успешного входа через `/auth/verify` устанавливается сессионная cookie.

---

## Аутентификация

### POST /auth/verify
Вход в систему (создает пользователя при первом входе).

**Параметры:**
```json
{
  "login": "string",
  "password": "string"
}
```

**Ответ:**
```json
{
  "status": "success",
  "user": {
    "id": "string",
    "login": "string",
    "role": "string"
  }
}
```

**Пример:**
```bash
curl -X POST http://localhost:8000/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "any"}'
```

### GET /auth/verify
Проверка текущей сессии.

**Ответ:**
```json
{
  "authenticated": true,
  "user": {
    "id": "string",
    "login": "string",
    "role": "string"
  }
}
```

---

## Роли и права доступа

### Роли в системе

| Роль | Описание | Доступ |
|------|----------|--------|
| `admin` | Администратор | Все функции системы |
| `data_operator` | Оператор данных | Импорт данных, просмотр журналов |
| `teacher` | Преподаватель | Просмотр студентов, рекомендации |
| `rop` | Руководитель ОП | Дашборды, аналитика |
| `student` | Студент | Личный прогресс, рекомендации |

### Матрица доступа

| Эндпоинт | admin | data_operator | teacher | rop | student |
|----------|-------|---------------|---------|-----|---------|
| `/admin/*` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/import/*` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/teacher/*` | ✅ | ❌ | ✅ | ❌ | ❌ |
| `/rop/*` | ✅ | ❌ | ❌ | ✅ | ❌ |
| `/student/*` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `/api/llm/*` | ✅ | ❌ | ✅ | ❌ | ✅ |

---

## Эндпоинты по ролям

### Администратор (`admin`)

#### GET /admin/
Главная страница админ-панели.

#### GET /admin/settings
Настройки системы.

#### POST /admin/settings
Обновление настроек.

**Параметры:**
```json
{
  "LLM_API_KEY": "string",
  "LLM_FOLDER_ID": "string",
  "SMTP_HOST": "string",
  "SMTP_PORT": "number",
  "APP_NOW_MODE": "real|fake",
  "APP_FAKE_NOW": "YYYY-MM-DD"
}
```

#### GET /admin/import-jobs
Журнал импорта данных.

#### GET /admin/users
Управление пользователями.

#### GET /admin/llm
Мониторинг LLM.

#### GET /admin/llm/export
Экспорт логов LLM в CSV.

**Параметры:**
- `status` (optional): фильтр по статусу
- `course_id` (optional): фильтр по курсу

### Оператор данных (`data_operator`)

#### GET /import/
Страница импорта данных.

#### POST /import/upload
Загрузка Excel файла.

**Параметры:**
- `file`: Excel файл (multipart/form-data)

**Ответ:**
```json
{
  "status": "success",
  "job_id": "string",
  "message": "Import job created"
}
```

#### GET /import/jobs
Список задач импорта.

#### GET /import/jobs/{job_id}
Детали задачи импорта.

### Преподаватель (`teacher`)

#### GET /teacher/
Главная страница преподавателя.

#### GET /teacher/course/{course_id}
Детали курса.

#### GET /teacher/students
Список студентов.

#### GET /teacher/api/dashboard
API дашборда преподавателя.

**Ответ:**
```json
{
  "total_students": 150,
  "at_risk_students": 12,
  "courses": [
    {
      "id": "string",
      "name": "string",
      "students_count": 30,
      "at_risk_count": 3
    }
  ]
}
```

#### GET /teacher/api/course/{course_id}
API данных курса.

#### GET /teacher/api/course/{course_id}/clusters
Кластеры студентов по курсу.

#### GET /teacher/recommendations
Рекомендации для подтверждения.

### РОП (`rop`)

#### GET /rop/
Главная страница РОП.

#### GET /rop/course/{course_id}
Детали курса.

#### GET /rop/api/dashboard
API дашборда РОП.

**Ответ:**
```json
{
  "total_students": 500,
  "total_courses": 25,
  "overall_progress": 78.5,
  "at_risk_percentage": 8.2
}
```

#### GET /rop/api/trends/{days}
Тренды за указанное количество дней.

#### GET /rop/api/course/{course_id}/trends/{days}
Тренды по курсу.

### Студент (`student`)

#### GET /student/
Главная страница студента.

#### GET /student/courses
Список курсов студента.

#### GET /student/api/progress/{student_id}
Прогресс студента.

**Ответ:**
```json
{
  "student_id": "string",
  "overall_progress": 75.5,
  "courses": [
    {
      "id": "string",
      "name": "string",
      "progress": 80.0,
      "status": "on_track",
      "deadlines": [
        {
          "task": "string",
          "deadline": "2024-01-20",
          "status": "pending"
        }
      ]
    }
  ]
}
```

---

## LLM API

### GET /api/llm/recommendations/{student_id}/{course_id}
Запрос рекомендаций для студента.

**Параметры:**
- `force_refresh` (optional): принудительное обновление

**Ответ:**
```json
{
  "status": "processing|success|error",
  "task_id": "string",
  "message": "string"
}
```

### GET /api/llm/recommendations/{student_id}/{course_id}/result
Получение результата рекомендаций.

**Ответ:**
```json
{
  "status": "success",
  "recommendations": [
    "string"
  ],
  "cached": false,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

### POST /api/llm/recommendations/{student_id}/{course_id}/rate
Оценка рекомендаций.

**Параметры:**
```json
{
  "rating": 1-5,
  "feedback": "string"
}
```

### POST /api/llm/recommendations/{student_id}/{course_id}/approve
Подтверждение рекомендаций (преподаватель).

**Параметры:**
```json
{
  "approved": true,
  "comment": "string"
}
```

### GET /api/llm/stats
Статистика LLM.

**Ответ:**
```json
{
  "total_calls": 150,
  "success_rate": 95.5,
  "avg_response_time": 2.3,
  "cache_hit_rate": 60.0
}
```

### GET /api/llm/teacher/recommendations
Рекомендации для подтверждения преподавателем.

---

## Форматы данных

### Модель студента
```json
{
  "id": "string",
  "name": "string",
  "email": "string",
  "group_id": "string",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Модель курса
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "teacher_id": "string",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Модель задачи импорта
```json
{
  "id": "string",
  "status": "pending|processing|success|error",
  "file_name": "string",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "errors": [
    {
      "row": 5,
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

### Модель LLM вызова
```json
{
  "id": "string",
  "student_id": "string",
  "course_id": "string",
  "request_type": "recommendations",
  "status": "success|error|timeout",
  "response_time_ms": 2500,
  "created_at": "2024-01-15T10:30:00Z",
  "response_json": {}
}
```

---

## Коды ошибок

### HTTP статус коды

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Неверные параметры запроса |
| 401 | Не авторизован |
| 403 | Доступ запрещен |
| 404 | Ресурс не найден |
| 422 | Ошибка валидации |
| 500 | Внутренняя ошибка сервера |

### Формат ошибки
```json
{
  "detail": "Описание ошибки",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Типичные ошибки

| Код | Описание | Решение |
|-----|----------|---------|
| `STUDENT_NOT_FOUND` | Студент не найден | Проверить ID студента |
| `COURSE_NOT_FOUND` | Курс не найден | Проверить ID курса |
| `INSUFFICIENT_PERMISSIONS` | Недостаточно прав | Проверить роль пользователя |
| `INVALID_FILE_FORMAT` | Неверный формат файла | Загрузить Excel файл |
| `LLM_SERVICE_UNAVAILABLE` | LLM сервис недоступен | Повторить запрос позже |

---

## Примеры запросов

### Получение прогресса студента
```bash
curl -X GET "http://localhost:8000/student/api/progress/01" \
  -H "Cookie: session=your_session_cookie"
```

### Загрузка файла импорта
```bash
curl -X POST "http://localhost:8000/import/upload" \
  -H "Cookie: session=your_session_cookie" \
  -F "file=@students.xlsx"
```

### Запрос рекомендаций
```bash
curl -X GET "http://localhost:8000/api/llm/recommendations/01/1?force_refresh=true" \
  -H "Cookie: session=your_session_cookie"
```

### Оценка рекомендаций
```bash
curl -X POST "http://localhost:8000/api/llm/recommendations/01/1/rate" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{"rating": 5, "feedback": "Отличные рекомендации!"}'
```

### Получение статистики LLM
```bash
curl -X GET "http://localhost:8000/api/llm/stats" \
  -H "Cookie: session=your_session_cookie"
```

### Экспорт логов LLM
```bash
curl -X GET "http://localhost:8000/admin/llm/export?status=success" \
  -H "Cookie: session=your_session_cookie" \
  -o llm_logs.csv
```

---

## Health Check

### GET /healthz
Проверка работоспособности системы.

**Ответ:**
```json
{
  "status": "ok",
  "service": "PulseEdu",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /health
Расширенная проверка здоровья.

**Ответ:**
```json
{
  "status": "ok",
  "database": "connected",
  "rabbitmq": "connected",
  "services": {
    "web": "running",
    "worker_ingest": "running",
    "worker_llm": "running"
  }
}
```

---

## Rate Limiting

Система не имеет жестких ограничений по частоте запросов, но рекомендуется:

- Не более 10 запросов в секунду на пользователя
- Для LLM API - не более 1 запроса в 5 секунд на студента
- Для импорта - не более 1 файла в минуту

---

## Версионирование

Текущая версия API: **v0.1**

Изменения в API будут документироваться в [CHANGELOG.md](../CHANGELOG.md).

---

## Поддержка

Для вопросов по API:
- Создавайте issues в репозитории
- Изучайте [DevGuide](devguide.md) для разработчиков
- Проверяйте логи приложения для диагностики ошибок
