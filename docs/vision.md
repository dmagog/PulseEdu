# Пульс.EDU — VISION

Версия: v0.3 (2025‑09‑06)
Автор(ы): команда проекта  
Статус: черновик; ведётся по принципу KISS (минимум необходимого)

> **Назначение.** Техническое видение MVP сервиса «Пульс.EDU»: технологии, подход к разработке, структура проекта, архитектура, модель данных, LLM и его мониторинг, сценарии работы, деплой, конфигурирование, логгирование. В эту версию перенесены технические детали из idea.md (модель данных, шаблон Excel и пр.).

Содержание: 1) Технологии · 2) Принцип разработки · 3) Структура проекта · 4) Архитектура · 5) Модель данных · 6) Работа с LLM · 7) Мониторинг LLM · 8) Сценарии работы · 9) Деплой · 10) Конфигурирование · 11) Логгирование · 12) Дашборды

---

## 1. Технологии (KISS, зафиксировано)

**Бэкенд**: Python 3.11; FastAPI + Uvicorn; Jinja2; Pydantic v2.  
**Данные**: PostgreSQL 15; **SQLModel** + Alembic; импорт Excel — pandas + openpyxl.  
**Очереди**: Celery + RabbitMQ + Flower; периодика — Celery Beat (Airflow вне MVP).  
**Уведомления**: SMTP; dev — MailHog.  
**Аутентификация**: фиктивная (логин + любой пароль) через `/auth/verify`; cookie‑сессии; RBAC.  
**UI**: Jinja2 + Bootstrap.  
**Контейнеризация/CI**: docker‑compose (web, db, mq, worker, beat, flower, mailhog); GitHub Actions (ruff+black → build → миграции).  
**LLM**: коннектор к Yandex.Cloud; при недоступности — warning + постановка задачи в Celery.

---

## 2. Принцип разработки (KISS, зафиксировано)
- Ветвление: `main`, `feat/*`, `fix/*`; PR с 1 апрувом; теги `v0.x.y`; `CHANGELOG.md`.
- Код‑стайл: black + ruff; pre‑commit. Типизация — точечно для внешних интерфейсов.
- Тесты‑дымовки: `/healthz`, happy‑path импорта Excel и пересчёта, письмо в MailHog.
- Миграции: Alembic (база + инкременты); в Excel — `template_version`.
- Документация: README, idea.md, vision.md; спорные решения — короткие ADR.
- DoD (MVP): доступность из UI, дымовой тест, описание в README/FAQ, не ломает импорт и e‑mail.

- Безопасность (минимум): секреты из ENV; RBAC‑гейт на роутерах; лимит Excel 10 МБ.
- Ошибки/UX: единый обработчик ошибок; предупреждение при LLM‑недоступности + постановка в очередь.

---

## 3. Структура проекта (KISS, зафиксировано)
```
repo/
├─ app/
│  ├─ main.py                 # точка входа FastAPI, регистрация маршрутов
│  ├─ database/               # работа с БД (инициализация/сессии)
│  │  ├─ engine.py            # create_engine(), настройки пула
│  │  ├─ session.py           # SessionLocal, get_session()
│  │  └─ init_db.py           # первичная инициализация/фикстуры dev
│  ├─ models/                 # SQLModel-модели (данные)
│  │  ├─ user.py              # User, Role, UserRole
│  │  ├─ academic.py          # Program, Group, Course, Enrollment
│  │  ├─ assessment.py        # Assessment, Grade
│  │  ├─ recommend.py         # Recommendation, RecRating
│  │  ├─ jobs.py              # ImportJob и др. техн. сущности
│  │  └─ __init__.py          # metadata, импорт моделей
│  ├─ services/               # бизнес-логика
│  │  ├─ crud/                # CRUD-операции по доменам
│  │  │  ├─ users.py
│  │  │  ├─ grades.py
│  │  │  ├─ recommendations.py
│  │  │  └─ imports.py
│  │  ├─ auth_service.py      # заглушка внешней авторизации
│  │  ├─ import_service.py    # парсинг Excel, валидация, маппинг
│  │  ├─ metrics_service.py   # пересчёт метрик, дедлайны
│  │  ├─ cluster_service.py   # кластеризация студентов (перезапуск)
│  │  ├─ email_service.py     # SMTP-отправка
│  │  └─ llm_provider.py      # коннектор к Yandex.Cloud LLM
│  ├─ routes/                 # HTTP-эндпоинты (FastAPI routers)
│  │  ├─ auth.py              # /auth/verify (фиктивная авторизация)
│  │  ├─ students.py          # кабинет студента, лента, рекомендации
│  │  ├─ teachers.py          # очередь подтверждений, низкооценённые
│  │  ├─ rop.py               # обзоры программ/групп
│  │  ├─ data_import.py       # загрузка Excel (оператор данных)
│  │  ├─ admin.py             # пользователи/роли, системные параметры
│  │  └─ notify.py            # ручные триггеры уведомлений (dev)
│  ├─ ui/
│  │  ├─ templates/           # Jinja2-шаблоны страниц
│  │  └─ static/              # CSS/JS/иконки (Bootstrap)
│  └─ rbac.py                 # ролевая проверка/Depends
├─ migrations/                # Alembic
├─ worker/
│  ├─ celery_app.py           # конфиг Celery, Beat
│  └─ queues.py               # имена очередей: auth, ingest, email, llm, cluster
├─ tests/
│  ├─ test_health.py
│  ├─ test_import_happy.py
│  └─ test_email.py
├─ docker-compose.yml
├─ .env.example
├─ README.md
└─ docs/
   ├─ idea.md
   └─ vision.md
```

**Пояснения (KISS):**
- `models/` — единая точка правды для схем БД (SQLModel); один модуль на близкие домены.
- `routes/` — только HTTP-ручки и валидация входа/выхода, бизнес-логика вынесена в `services/`.
- `database/` — инициализация двигателя и фабрика сессий; зависимости FastAPI (`Depends`) объявляем локально рядом с доменом (в `database/session.py`, `rbac.py` или прямо в `routes/*`).
- `services/crud/` — тонкие CRUD-операции; сервисы верхнего уровня оркестрируют CRUD и очереди.
- Воркеры Celery используют те же `services/*` для повторного использования логики.
- Отдельного `deps.py` **нет** — KISS.

---

## 4. Архитектура (KISS, зафиксировано)
- **Web (FastAPI)** — HTTP/UI, Jinja2, авторизация, RBAC.
- **Workers (Celery)** — несколько отдельных воркеров по очередям:
  - `auth` — проверка существования логина во внешнем сервисе (заглушка);
  - `ingest` — импорт Excel и первичный валидационный пайплайн;
  - `email` — шаблонирование и отправка писем;
  - `llm` — обращения к внешней LLM (ретраи);
  - `cluster` — перезапуск кластеризации студентов после обновления данных.
- **Beat (Celery Beat)** — периодические задачи (дедлайны и т.п.).
- **Broker (RabbitMQ)** — очереди задач `auth`, `ingest`, `email`, `llm`, `cluster`.
- **DB (PostgreSQL)** — транзакционное хранилище.
- **Mail (SMTP/MailHog)** — уведомления.
- **LLM (Yandex.Cloud)** — внешний сервис рекомендаций через коннектор.

Потоки: UI/REST → Web → постановка задач в соответствующие очереди Celery; воркеры берут задачи из своих очередей и взаимодействуют с DB/SMTP/LLM. Обработчики пишут логи через стандартный `logging`.

---

## 5. Модель данных (MVP, зафиксировано)

> **Примечание:** шаблон Excel на этапе MVP считается **схематичным**. Формат листов и имена колонок могут отличаться у разных источников. Импорт реализуем через простое сопоставление колонок по alias‑спискам из конфига; жёсткой фиксации названий столбцов нет.

### 5.1 Сущности (логическая модель)
- **User**(user_id, email, login, display_name, is_active)
- **Role**(role_id, name) — значения: student, teacher, rop, data_operator, admin
- **UserRole**(user_id, role_id)
- **Program**(program_id, program_name, rop_user_id)
- **Group**(group_id, program_id)
- **Course**(course_id, course_name, teacher_user_id)
- **Enrollment**(enrollment_id, student_id, course_id, group_id)
- **Assessment**(assessment_id, course_id, title, weight, due_date)
- **Grade**(grade_id, student_id, assessment_id, score, submitted_at, status)
- **Recommendation**(rec_id, student_id, course_id, text, created_at, verified_by_teacher, verified_at, avg_rating)
- **RecRating**(rating_id, rec_id, student_id, stars, created_at)
- **ImportJob**(job_id, started_at, finished_at, status, source_filename, template_version, errors_json)

> Примечания: `status` у Grade: `submitted` / `on_review` / `late` / `missing`; агрегации по группе и программе строятся SQL‑запросами.

### 5.2 Шаблон Excel (импорт) — схематично
Поддерживаем один файл с несколькими листами **или** несколько файлов. Сопоставление колонок — по alias из конфига (регистронезависимо; пробелы/подчёркивания игнорируем). Неизвестные колонки пропускаем с предупреждением.

**Минимальные обязательные поля (внутренние имена):**
- **Students:** `student_id`, `group_id`  
  _Опц.:_ `first_name`, `last_name`, `email`
- **Programs:** `program_id`, `program_name`  
  _Опц.:_ `rop_user_id`
- **Groups:** `group_id`, `program_id`
- **Courses:** `course_id`, `course_name`, `teacher_user_id`
- **Enrollments:** `student_id`, `course_id`, `group_id`
- **Assessments:** `assessment_id`, `course_id`, `due_date`, `weight`  
  _Опц.:_ `title`
- **Grades:** `student_id`, `assessment_id`, `score`  
  _Опц.:_ `submitted_at`, `status` (`submitted`/`on_review`/`late`/`missing`)

**Пример конфигурации alias (yaml, укорочено):**
```yaml
sheets:
  Students:
    required: [student_id, group_id]
    optional: [first_name, last_name, email]
    aliases:
      student_id: [student_id, "id студента", id]
      group_id: [group_id, группа]
      email: [email, e-mail]
  Grades:
    required: [student_id, assessment_id, score]
    aliases:
      score: [score, баллы, points]
      submitted_at: [submitted_at, дата сдачи]
      status: [status, статус]
```

**Валидация (минимум):**
- Обязательные поля присутствуют; `ID` уникальны; внешние ключи существуют.
- `score` в допустимом диапазоне; даты парсятся в ISO (поддерживаем `YYYY-MM-DD` и `DD.MM.YYYY`).
- При ошибках — `ImportJob.status = failed`, детали в `errors_json`; частичных загрузок на MVP нет.

**Эволюция:** alias‑списки можно дополнять без изменения кода (перечитываются при старте приложения/воркера).

---

## 6. Работа с LLM (зафиксировано)

**Цель (KISS):** получать короткие, конкретные текстовые рекомендации от внешней LLM (Yandex.Cloud) с простым кешированием и понятным поведением при сбоях.

### 6.1 Провайдер и вызов
- Абстракция `LLMProvider` (HTTP). Берёт `LLM_ENDPOINT`, `LLM_API_KEY` из ENV.
- Вызовы выполняются из воркера **`llm`** (Celery). Таймаут: **10 с**; ретраи: **3** попытки по расписанию **1м → 5м → 15м**.
- Язык ответа определяется языком пользователя (`User.profile_lang`), по умолчанию `ru`.

### 6.2 Кеширование (простая схема без «снепшотов»)
- Ключ кеша: **(`student_id`, `course_id`, `data_version`)**.
- `data_version` — это идентификатор последней успешной загрузки/пересчёта данных (например, `ImportJob.job_id`). При новом импорте версия меняется → кеш автоматически инвалидируется.
- TTL кеша на LLM‑ответ: по умолчанию **24 часа** (значение настраивается в админке).

### 6.3 Форматы запроса/ответа (минимум)
**Запрос (JSON):**
```json
{
  "lang": "ru",
  "student_id": "S123",
  "course_id": "C45",
  "risk_reasons": ["низкий прогресс", "2 просрочки"],
  "facts": {
    "progress_pct": 42,
    "upcoming_deadlines": ["ЛР2 2025-09-12"],
    "weak_topics": ["Векторы", "Матрицы"]
  },
  "constraints": {
    "max_recs": 3,
    "style": "кратко, по делу",
    "tone": "поддерживающий",
    "max_chars_per_rec": 200
  }
}
```
**Ответ (JSON):**
```json
{
  "recommendations": [
    {"text": "Разберите примеры по матрицам из лекции 3 и решите 5 задач из практикума."},
    {"text": "Сдайте ЛР2 до 12.09 — начните с раздела ‘Определители’."}
  ]
}
```
- В текущей реализации рекомендации — **только текст** (без тегов/ссылок) — ок по согласованию.

### 6.4 Промпт (шаблон, укороченно)
```
Ты — ассистент преподавателя. Кратко сформулируй до 3 рекомендаций студенту.
Контекст: курс={course_name}, причины риска={risk_reasons}, прогресс={progress_pct}%, дедлайны={upcoming_deadlines}, слабые темы={weak_topics}.
Требования: дружелюбно, конкретно. Каждая рекомендация ≤ {max_chars_per_rec} символов. Не придумывай факты.
Выход: JSON {"recommendations": [{"text": "..."}, ...]}
```

### 6.5 Недоступность LLM
- Показываем **warning** в UI: «Рекомендации формируются, попробуем ещё раз». 
- Задача ставится в очередь `llm` на повтор согласно ретраям. Эвристических (правиловых) рекомендаций **не используем** на MVP.

### 6.6 Параметры генерации и лимиты (админ‑настройки)
- `llm_max_recs` (по умолчанию 3), `llm_rec_max_chars` (200), `llm_context_max_tokens` (1500), 
  `llm_timeout_seconds` (10), `llm_retry_schedule` ("60,300,900"), `llm_cache_ttl_hours` (24), `llm_default_lang` ("ru").
- Параметры изменяемы в админке; применяются без перезапуска (чтение из таблицы настроек).

### 6.7 Параметры генерации и лимиты (админ‑настройки)
- допускаем Markdown в ответах и санитизируем перед показом.
---

## 7. Мониторинг LLM (зафиксировано)

### 7.1 Что собираем (метаданные + текст ответа)
Сохраняем **метаданные вызовов** и **текст ответа LLM** (он короткий и нужен студенту/преподавателю и для агрегирования по курсам):
- `ts`, `provider` (`yacloud`), `student_id`, `course_id`, `data_version`, `lang`
- `status` (`success`/`failed`/`cached`), `duration_ms`, `attempt`, `retry_delay_s`, `cache_hit`
- `input_chars`, `output_chars` *(или токены, если доступны)*
- `response_json` *(TEXT; массив коротких рекомендаций)*
- `err_code`, `err_msg_short`

> Приватность: не сохраняем ПДн (ФИО/e-mail) в логах; `student_id` — внутренний идентификатор.

### 7.2 Хранение
- Таблица **`llm_call_log`** (индексы по `ts`, `status`, `(course_id, ts)`).
- Вьюхи:
  - `llm_stats_last_24h` — успехи/ошибки, error‑rate, p50/p95 latency.
  - `llm_stats_by_course` — сводка по курсам за 7 дней.
- **Retention**: значение по умолчанию 30 дней; управляется в админке (`llm_log_retention_days`). Ежедневная очистка через Celery Beat.

### 7.3 Админ‑страница `/admin/llm`
- Сводка за 24ч: `calls`, `success%`, `p95 latency`, `avg attempts`, `cache_hit%`.
- Таблица последних N вызовов (фильтры: статус/курс/период, пагинация).
- **Выгрузка CSV** по текущим фильтрам.
- (Опц.) Мини‑графики на Chart.js (через CDN), без сборки.

### 7.4 Сигнализация
- Письмо админу, если `error_rate > X%` за 30 минут **или** `N` подряд ошибок. 
- Пороговые значения управляются в админке: `llm_alert_error_rate_pct`, `llm_alert_consecutive_fails`, `llm_alert_email_to`.

---

## 8. Сценарии работы (зафиксировано)
1) Импорт Excel → очередь `ingest` → пересчёт метрик → генерация рекомендаций (очередь `llm`) → e‑mail студентам/преподавателям (очередь `email`).  
2) LLM недоступен → warning в UI → задача в `llm` на повтор → оповещение при успехе.  
3) После успешного импорта и пересчёта → задача в очередь `cluster` для **перезапуска кластеризации** студентов по курсу.

---

## 9. Деплой (зафиксировано)
- Локально: `docker-compose up -d`. Сервисы: `web`, `db`, `mq`, `worker_auth`, `worker_ingest`, `worker_email`, `worker_llm`, `worker_cluster`, `beat`, `flower`, `mailhog`.
- Каждому воркеру указываем ключ `-Q` с именем очереди; масштабирование — через `--concurrency`.
- Миграции: `alembic upgrade head` (автоматически в CI/при первом старте контейнера web/worker_ingest).

---

## 10. Конфигурирование (зафиксировано)
`.env` (локально) / GitHub Secrets (CI):
- DB_URL, RABBITMQ_URL, SMTP_HOST/PORT/USER/PASS, MAIL_FROM
- LLM_ENDPOINT, LLM_API_KEY
- APP_SECRET, APP_BASE_URL
- EXCEL_MAPPING_FILE — путь к yaml с alias‑списками
- есть флаги llm_allow_markdown и llm_allowed_tags

**Админ‑настройки (хранятся в БД, редактируются через `/admin`):**
- LLM: `llm_max_recs`, `llm_rec_max_chars`, `llm_context_max_tokens`, `llm_timeout_seconds`, `llm_retry_schedule`, `llm_cache_ttl_hours`, `llm_default_lang`
- Мониторинг LLM: `llm_monitoring_enabled`, `llm_log_retention_days`, `llm_alert_error_rate_pct`, `llm_alert_consecutive_fails`, `llm_alert_email_to`
- Аудит: `auth_log_retention_days`

Применение настроек — без перезапуска.

---

## 11. Логгирование (зафиксировано)
- Используем стандартный модуль **logging**; вывод в **STDOUT**; уровни: INFO/ERROR (в dev можно DEBUG). Формат key=value (timestamp, level, logger, msg, request_id, user_id?).
- **request_id** через middleware (contextvar) + Filter, прокидывается в все логи запроса; доменные логгеры: `app.import`, `app.recommend`, `app.notify`, `app.auth`, `app.cluster`, `app.llm`.
- Протокол загрузок — таблица **ImportJob** (errors_json, статусы). 
- **Аудит авторизаций**: таблица **`user_auth_log`** (ts, login, outcome `success|fail`, ip?, user_agent?, reason?). Retention управляется в админке (`auth_log_retention_days`).
- Для Celery — добавляем в логи `job_id`, `queue`, `task_name`.

---

### Изменения
- **v0.2 (2025‑09‑06):** перенёс технические детали (модель данных, шаблон Excel) из idea.md; расширил каркас vision.md.

## 12. Дашборды (MVP, зафиксировано)
**Цель:** отобразить ключевые показатели ролям без SPA, средствами Jinja2 + Chart.js (CDN).

- **Студент**: прогресс по курсам (progress‑bar), лента событий; виджет дедлайнов; последние рекомендации.
- **Преподаватель**: список «в зоне внимания»; распределение статусов работ; топ‑темы со слабыми результатами; очередь рекомендаций на подтверждение; блок низкооценённых рекомендаций.
- **РОП**: свод по программам/группам; «тепловая карта» курсов (процент просрочек/прогресса); тренд рисков 7/30 дней.

**Технически:**
- Шаблоны Jinja2; данные — простые агрегирующие SQL-запросы.
- Мини‑графики на **Chart.js** через CDN (линии/столбцы/теплокарта через плагин или простые таблицы).
- Без сборки фронта и state‑менеджмента; всё KISS.

---

