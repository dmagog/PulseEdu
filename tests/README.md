# Тесты PulseEdu

Этот каталог содержит автоматизированные тесты для проекта PulseEdu.

## Быстрый старт

```bash
# Запуск всех тестов
docker-compose exec web python -m pytest

# Запуск с покрытием кода
docker-compose exec web python -m pytest --cov=app --cov-report=term-missing
```

## Структура

- `test_basic.py` - Базовые тесты (11 тестов)
- `test_health.py` - Тесты health endpoint (2 теста)
- `test_models.py` - Тесты моделей данных (6 тестов)
- `test_services.py` - Тесты сервисов (6 тестов)
- `test_api.py` - Тесты API эндпоинтов (19 тестов)

**Всего:** 42 теста, покрытие кода: 32%

## Документация

Подробная документация по тестированию находится в [docs/testing.md](../docs/testing.md).

## Статус

✅ Все тесты проходят успешно  
✅ Изолированная база данных для каждого теста  
✅ Покрытие основных компонентов системы  
