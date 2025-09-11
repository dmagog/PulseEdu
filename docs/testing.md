# Документация по тестированию

## Обзор

Проект PulseEdu использует pytest для автоматизированного тестирования. Тесты покрывают основные компоненты системы: модели данных, сервисы и API эндпоинты.

## Структура тестов

```
tests/
├── __init__.py              # Пакет тестов
├── conftest.py             # Фикстуры и конфигурация
├── pytest.ini             # Конфигурация pytest
├── test_basic.py           # Базовые тесты
├── test_health.py          # Тесты health endpoint
├── test_models.py          # Тесты моделей данных
├── test_services.py        # Тесты сервисов
└── test_api.py             # Тесты API эндпоинтов
```

## Запуск тестов

### Все тесты
```bash
# Запуск всех тестов
docker-compose exec web python -m pytest

# Запуск с покрытием кода
docker-compose exec web python -m pytest --cov=app --cov-report=term-missing
```

### Конкретные тесты
```bash
# Тесты моделей
docker-compose exec web python -m pytest tests/test_models.py -v

# Тесты сервисов
docker-compose exec web python -m pytest tests/test_services.py -v

# Тесты API
docker-compose exec web python -m pytest tests/test_api.py -v
```

### Фильтрация тестов
```bash
# Тесты конкретного класса
docker-compose exec web python -m pytest tests/test_models.py::TestStudentModel -v

# Тесты по имени
docker-compose exec web python -m pytest -k "test_student_creation" -v
```

## Типы тестов

### 1. Базовые тесты (`test_basic.py`)
- Математические операции
- Строковые операции
- Работа со списками
- Тестирование классов

**Пример:**
```python
def test_basic_math():
    assert 2 + 2 == 4
    assert 10 / 2 == 5
```

### 2. Тесты моделей (`test_models.py`)
Проверяют корректность работы с моделями данных SQLModel:
- Student, Course, Task, User, Role
- Создание и извлечение объектов
- Проверка обязательных полей

**Пример:**
```python
def test_student_creation(self, isolated_db_session):
    student = Student(
        id="test_student",
        name="Тестовый Студент",
        email="test@example.com"
    )
    isolated_db_session.add(student)
    isolated_db_session.commit()
    
    retrieved = isolated_db_session.query(Student).filter(
        Student.id == "test_student"
    ).first()
    
    assert retrieved is not None
    assert retrieved.name == "Тестовый Студент"
```

### 3. Тесты сервисов (`test_services.py`)
Проверяют бизнес-логику сервисов:
- StudentService
- TeacherService  
- MetricsService

**Пример:**
```python
def test_get_student_assignments_empty(self, isolated_db_session):
    service = StudentService()
    assignments = service.get_student_assignments("nonexistent_student", isolated_db_session)
    assert assignments == []
```

### 4. Тесты API (`test_api.py`)
Проверяют HTTP эндпоинты:
- Student, Teacher, Admin, Cluster, ML Monitoring
- Health endpoint
- Обработка ошибок

**Пример:**
```python
def test_health_check(self, client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "PulseEdu"
```

## Фикстуры

### `isolated_db_session`
Создает изолированную сессию базы данных для каждого теста:

```python
@pytest.fixture(scope="function")
def isolated_db_session(test_engine):
    """Create an isolated database session for each test."""
    # Создает временную SQLite базу для каждого теста
    # Автоматически очищается после теста
```

### `client`
Создает тестовый клиент FastAPI:

```python
@pytest.fixture
def client(test_db_session):
    """Create a test client with database dependency override."""
    from app.main import app
    from app.database.session import get_db
    
    def override_get_db():
        return test_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

## Конфигурация

### `pytest.ini`
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
```

### Зависимости
```txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

## Покрытие кода

Текущее покрытие: **32%** (1,402 строк из 4,359)

### Покрытие по модулям:
- **Модели:** 100% (все модели покрыты)
- **Основные сервисы:** 24-60%
- **API эндпоинты:** 16-51%
- **База данных:** 36%

### Генерация отчета о покрытии
```bash
# HTML отчет
docker-compose exec web python -m pytest --cov=app --cov-report=html

# Отчет в терминале
docker-compose exec web python -m pytest --cov=app --cov-report=term-missing
```

## Лучшие практики

### 1. Изоляция тестов
- Каждый тест использует изолированную базу данных
- Тесты не зависят друг от друга
- Использование фикстур для подготовки данных

### 2. Именование
- Тестовые файлы: `test_*.py`
- Тестовые классы: `Test*`
- Тестовые функции: `test_*`

### 3. Структура тестов
```python
def test_feature_behavior(self, fixture):
    """Test description."""
    # Arrange - подготовка данных
    data = create_test_data()
    
    # Act - выполнение действия
    result = function_under_test(data)
    
    # Assert - проверка результата
    assert result == expected_value
```

### 4. Обработка ошибок
```python
def test_error_handling(self, client):
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
```

## Отладка тестов

### Запуск с подробным выводом
```bash
docker-compose exec web python -m pytest -v -s
```

### Остановка на первой ошибке
```bash
docker-compose exec web python -m pytest -x
```

### Запуск только упавших тестов
```bash
docker-compose exec web python -m pytest --lf
```

## CI/CD интеграция

Тесты автоматически запускаются в CI/CD пайплайне:

```yaml
# Пример для GitHub Actions
- name: Run tests
  run: |
    docker-compose exec web python -m pytest --cov=app --cov-report=xml
```

## Расширение тестов

### Добавление новых тестов
1. Создайте файл `test_new_feature.py`
2. Следуйте существующим паттернам
3. Используйте изолированные фикстуры
4. Добавьте тесты в CI/CD

### Тестирование новых сервисов
```python
class TestNewService:
    def test_service_method(self, isolated_db_session):
        service = NewService()
        result = service.method("test_data")
        assert result == expected_value
```

## Мониторинг качества

- **Цель покрытия:** 80%+
- **Автоматические проверки:** При каждом коммите
- **Регрессионное тестирование:** При изменении кода
- **Интеграционные тесты:** При развертывании

## Полезные ссылки

- [Документация pytest](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLModel Testing](https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/)
