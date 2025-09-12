#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для PulseEdu
Автоматически создает структуру БД и загружает тестовые данные при первом запуске
"""

import logging
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlmodel import SQLModel, create_engine

from app.database.session import engine
from app.models import cluster, llm_models, student, user

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_database_exists():
    """Проверяет, существует ли база данных"""
    try:
        # Пытаемся подключиться к базе данных
        with engine.connect() as conn:
            # Проверяем наличие основных таблиц
            result = conn.execute(
                """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'roles', 'students')
            """
            )
            count = result.scalar()
            return count > 0
    except Exception as e:
        logger.info(f"База данных не найдена или недоступна: {e}")
        return False


def create_tables():
    """Создает все таблицы в базе данных"""
    try:
        logger.info("Создание таблиц в базе данных...")
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Таблицы созданы успешно")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        return False


def run_migrations():
    """Запускает миграции Alembic"""
    try:
        logger.info("Запуск миграций Alembic...")

        # Настройка Alembic
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "migrations")
        alembic_cfg.set_main_option(
            "sqlalchemy.url", os.getenv("DB_URL", "postgresql://pulseedu:pulseedu@localhost:5432/pulseedu")
        )

        # Проверяем текущую версию
        script = ScriptDirectory.from_config(alembic_cfg)

        # Получаем текущую версию БД
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()

        # Получаем последнюю версию
        head_rev = script.get_current_head()

        if current_rev != head_rev:
            logger.info(f"Применение миграций: {current_rev} -> {head_rev}")
            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Миграции применены успешно")
        else:
            logger.info("✅ База данных уже актуальна")

        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при применении миграций: {e}")
        return False


def load_test_data():
    """Загружает тестовые данные если установлен флаг LOAD_TEST_DATA"""
    if os.getenv("LOAD_TEST_DATA", "false").lower() != "true":
        logger.info("Загрузка тестовых данных отключена (LOAD_TEST_DATA=false)")
        return True

    try:
        logger.info("Загрузка тестовых данных...")

        # Импортируем сервисы для загрузки данных
        from app.database.session import get_session
        from app.services.admin_service import AdminService

        # Создаем сессию БД
        db = next(get_session())

        try:
            # Создаем администратора по умолчанию
            admin_service = AdminService()

            # Проверяем, есть ли уже пользователи
            from sqlmodel import select

            from app.models.user import User

            existing_users = db.exec(select(User)).first()
            if existing_users:
                logger.info("Пользователи уже существуют, пропускаем создание тестовых данных")
                return True

            # Создаем роли
            from app.models.user import Role

            roles_data = [
                {"name": "Администратор", "description": "Полный доступ к системе"},
                {"name": "Преподаватель", "description": "Доступ к курсам и студентам"},
                {"name": "РОП", "description": "Руководитель образовательной программы"},
                {"name": "Оператор данных", "description": "Импорт и управление данными"},
                {"name": "Студент", "description": "Просмотр своих данных"},
            ]

            for role_data in roles_data:
                role = Role(**role_data)
                db.add(role)

            db.commit()
            logger.info("✅ Роли созданы")

            # Создаем администратора по умолчанию
            admin_user = User(login="admin", email="admin@pulseedu.local", full_name="Системный администратор", is_active=True)
            db.add(admin_user)
            db.commit()

            # Назначаем роль администратора
            admin_role = db.exec(select(Role).where(Role.name == "Администратор")).first()
            if admin_role:
                from app.models.user import UserRole

                user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
                db.add(user_role)
                db.commit()

            logger.info("✅ Администратор создан (логин: admin)")
            logger.info("✅ Тестовые данные загружены успешно")

        finally:
            db.close()

        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке тестовых данных: {e}")
        return False


def main():
    """Основная функция инициализации"""
    logger.info("🚀 Запуск инициализации базы данных PulseEdu")

    # Проверяем переменные окружения
    db_url = os.getenv("DB_URL")
    if not db_url:
        logger.error("❌ Переменная DB_URL не установлена")
        sys.exit(1)

    logger.info(f"📊 Подключение к базе данных: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")

    # Проверяем существование БД
    if check_database_exists():
        logger.info("✅ База данных уже инициализирована")
        # Все равно запускаем миграции на случай обновлений
        if not run_migrations():
            sys.exit(1)
    else:
        logger.info("🆕 Инициализация новой базы данных")

        # Создаем таблицы
        if not create_tables():
            sys.exit(1)

        # Запускаем миграции
        if not run_migrations():
            sys.exit(1)

    # Загружаем тестовые данные если нужно
    if not load_test_data():
        sys.exit(1)

    logger.info("🎉 Инициализация базы данных завершена успешно!")


if __name__ == "__main__":
    main()
