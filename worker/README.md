# YandexGPT LLM Worker

Воркер для интеграции с YandexGPT на основе наработок из Jupyter notebook.

## Возможности

- **Генерация обратной связи для студентов** - анализ успеваемости и персональные рекомендации
- **Сводка для преподавателей** - анализ проблемных студентов и советы по улучшению курса
- **Обратная связь по тестам** - анализ ответов студентов и рекомендации по улучшению

## Настройка

### Переменные окружения

Добавьте в `.env`:

```bash
# Yandex Cloud ML SDK Settings
YANDEX_CLOUD_FOLDER_ID=your_folder_id_here
YANDEX_CLOUD_API_KEY=your_api_key_here
```

### Установка зависимостей

```bash
pip install yandex-cloud-ml-sdk==0.15.0
```

## Использование

### 1. Тест подключения

```python
from worker.yandex_llm_tasks import test_yandex_connection

result = test_yandex_connection.delay()
connection_result = result.get(timeout=60)
print(connection_result)
```

### 2. Обратная связь для студента

```python
from worker.yandex_llm_tasks import generate_student_feedback
from worker.test_data import get_test_student_data

student_data = get_test_student_data("id_40")

result = generate_student_feedback.delay(
    student_id="id_40",
    student_data=student_data,
    model_type="yandexgpt"  # или "yandexgpt-lite"
)

feedback = result.get(timeout=120)
print(feedback)
```

## Модели

- **yandexgpt** - Полная модель YandexGPT (рекомендуется)
- **yandexgpt-lite** - Облегченная модель для быстрых запросов

## Формат данных

### Данные студента

```json
[
  {
    "Название": "Лекция 1.1. Начинаем с «Зачем?»",
    "Статус": "Выполнено",
    "Время выполнения": "04.15.25 15:23",
    "Дедлайн": "11.10.24 23:59"
  }
]
```

### Ответ обратной связи

```json
{
  "activity": "8",
  "homework": "9", 
  "tests": "10",
  "advice": "Вы хорошо справляетесь с выполнением заданий..."
}
```

## Интеграция с существующим кодом

Воркер интегрирован с `app/services/llm_provider.py`. При вызове `generate_recommendations()` система автоматически попытается использовать новый YandexGPT воркер, а при неудаче переключится на legacy метод.

## Логирование

Все операции логируются с уровнем INFO. Для отладки установите уровень DEBUG:

```python
import logging
logging.getLogger("worker.yandex_llm").setLevel(logging.DEBUG)
```

## Обработка ошибок

- Автоматические повторы при сбоях (до 3 раз)
- Экспоненциальная задержка между попытками
- Fallback на legacy метод при критических ошибках
- Подробное логирование всех операций
