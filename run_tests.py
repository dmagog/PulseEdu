#!/usr/bin/env python3
"""
Script to run tests for PulseEdu project.
"""
import subprocess
import sys
import os


def run_tests():
    """Run pytest with appropriate settings."""
    # Устанавливаем переменные окружения для тестов
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    
    # Команда для запуска pytest
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ]
    
    print("Running tests for PulseEdu...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ pytest not found. Please install it with: pip install pytest pytest-cov")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
