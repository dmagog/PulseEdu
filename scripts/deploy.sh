#!/bin/bash

# Скрипт полного развертывания PulseEdu
# Автоматически инициализирует систему и проверяет готовность

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}🚀 $1${NC}"
    echo "=================================="
}

# Проверка зависимостей
check_dependencies() {
    print_header "Проверка зависимостей"
    
    # Проверяем Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен"
        exit 1
    fi
    print_success "Docker установлен"
    
    # Проверяем Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен"
        exit 1
    fi
    print_success "Docker Compose установлен"
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 не установлен"
        exit 1
    fi
    print_success "Python 3 установлен"
}

# Создание .env файла
setup_environment() {
    print_header "Настройка окружения"
    
    if [ ! -f .env ]; then
        print_info "Создание .env файла из env.example"
        cp env.example .env
        print_success ".env файл создан"
        print_warning "Не забудьте настроить переменные окружения в .env файле"
    else
        print_info ".env файл уже существует"
    fi
}

# Остановка существующих контейнеров
stop_containers() {
    print_header "Остановка существующих контейнеров"
    
    if docker-compose ps | grep -q "Up"; then
        print_info "Остановка запущенных контейнеров..."
        docker-compose down
        print_success "Контейнеры остановлены"
    else
        print_info "Контейнеры не запущены"
    fi
}

# Запуск инфраструктурных сервисов
start_infrastructure() {
    print_header "Запуск инфраструктурных сервисов"
    
    print_info "Запуск PostgreSQL и RabbitMQ..."
    docker-compose up -d db mq
    
    # Ждем готовности БД
    print_info "Ожидание готовности базы данных..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T db pg_isready -U pulseedu &> /dev/null; then
            print_success "База данных готова"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Таймаут ожидания базы данных"
        exit 1
    fi
    
    # Ждем готовности RabbitMQ
    print_info "Ожидание готовности RabbitMQ..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T mq rabbitmq-diagnostics ping &> /dev/null; then
            print_success "RabbitMQ готов"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Таймаут ожидания RabbitMQ"
        exit 1
    fi
}

# Инициализация базы данных
init_database() {
    print_header "Инициализация базы данных"
    
    print_info "Запуск инициализации БД..."
    python3 scripts/init_db.py
    
    if [ $? -eq 0 ]; then
        print_success "База данных инициализирована"
    else
        print_error "Ошибка инициализации базы данных"
        exit 1
    fi
}

# Запуск приложения
start_application() {
    print_header "Запуск приложения"
    
    print_info "Запуск всех сервисов..."
    docker-compose up -d
    
    # Ждем готовности веб-приложения
    print_info "Ожидание готовности веб-приложения..."
    timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8000/healthz &> /dev/null; then
            print_success "Веб-приложение готово"
            break
        fi
        sleep 3
        timeout=$((timeout - 3))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Таймаут ожидания веб-приложения"
        print_info "Проверьте логи: docker-compose logs web"
        exit 1
    fi
}

# Проверка готовности системы
health_check() {
    print_header "Проверка готовности системы"
    
    print_info "Запуск проверки компонентов..."
    python3 scripts/health_check.py
    
    if [ $? -eq 0 ]; then
        print_success "Система готова к работе"
    else
        print_warning "Некоторые компоненты недоступны"
    fi
}

# Показ информации о доступе
show_access_info() {
    print_header "Информация о доступе"
    
    echo "🌐 Веб-приложение: http://localhost:8000"
    echo "📧 MailHog (email): http://localhost:8025"
    echo "🗄️  Adminer (БД): http://localhost:8080"
    echo "🌺 Flower (Celery): http://localhost:5555"
    echo "🐰 RabbitMQ: http://localhost:15672 (pulseedu/pulseedu)"
    echo ""
    echo "👤 Администратор по умолчанию:"
    echo "   Логин: admin"
    echo "   Пароль: любой (для разработки)"
    echo ""
    echo "📋 Полезные команды:"
    echo "   docker-compose logs -f web     # Логи веб-приложения"
    echo "   docker-compose logs -f worker_ingest  # Логи воркера импорта"
    echo "   docker-compose restart web     # Перезапуск веб-приложения"
    echo "   docker-compose down            # Остановка всех сервисов"
}

# Обработка аргументов командной строки
MODE="full"
LOAD_TEST_DATA="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            MODE="quick"
            shift
            ;;
        --with-test-data)
            LOAD_TEST_DATA="true"
            shift
            ;;
        --help)
            echo "Использование: $0 [--quick] [--with-test-data]"
            echo ""
            echo "Опции:"
            echo "  --quick           Быстрое развертывание (без полной проверки)"
            echo "  --with-test-data  Загрузить тестовые данные"
            echo "  --help            Показать эту справку"
            exit 0
            ;;
        *)
            print_error "Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

# Устанавливаем переменную для тестовых данных
if [ "$LOAD_TEST_DATA" = "true" ]; then
    export LOAD_TEST_DATA=true
    print_info "Включена загрузка тестовых данных"
fi

# Основной процесс развертывания
main() {
    print_header "Развертывание PulseEdu"
    
    check_dependencies
    setup_environment
    stop_containers
    start_infrastructure
    init_database
    start_application
    
    if [ "$MODE" = "full" ]; then
        health_check
    else
        print_info "Пропуск полной проверки (режим --quick)"
    fi
    
    show_access_info
    
    print_success "🎉 Развертывание завершено успешно!"
    print_info "Система готова к использованию"
}

# Запуск
main "$@"
