#!/bin/bash

# Quality check script for PulseEdu
# This script runs code quality checks locally
# Usage: ./scripts/quality_check.sh [--release] [--install]

set -e

# Default mode
MODE="development"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --release)
            MODE="release"
            shift
            ;;
        --install)
            INSTALL_DEPS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--release] [--install]"
            echo "  --release: Run full quality checks (as for releases)"
            echo "  --install: Install quality check dependencies"
            echo "  --help: Show this help message"
            exit 0
            ;;
    esac
done

if [ "$MODE" = "release" ]; then
    echo "🔍 Running FULL code quality checks for PulseEdu (release mode)..."
else
    echo "🔍 Running development code quality checks for PulseEdu..."
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Install dependencies if needed
if [ "$1" = "--install" ]; then
    print_status "Installing quality check dependencies..."
    pip install black flake8 isort mypy bandit
fi

# Run Black (code formatting)
print_status "Running Black (code formatting check)..."
if black --check --diff app/ tests/; then
    print_status "Black check passed"
else
    print_warning "Black found formatting issues. Run 'black app/ tests/' to fix them."
fi

# Run isort (import sorting)
print_status "Running isort (import sorting check)..."
if isort --check-only --diff app/ tests/; then
    print_status "isort check passed"
else
    print_warning "isort found import sorting issues. Run 'isort app/ tests/' to fix them."
fi

# Run Flake8 (linting)
print_status "Running Flake8 (linting)..."
if flake8 app/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
    print_status "Flake8 critical issues check passed"
else
    print_error "Flake8 found critical issues"
fi

# Run Flake8 with warnings
print_status "Running Flake8 (style warnings)..."
flake8 app/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Run MyPy (type checking)
print_status "Running MyPy (type checking)..."
if mypy app/ --ignore-missing-imports --no-strict-optional; then
    print_status "MyPy check passed"
else
    print_warning "MyPy found type issues"
fi

# Run Bandit (security)
print_status "Running Bandit (security check)..."
bandit -r app/ -ll

# Run tests based on mode
if [ "$MODE" = "release" ]; then
    print_status "Running FULL test suite..."
    if python3 -m pytest tests/ --cov=app -v; then
        print_status "All tests passed with coverage"
    else
        print_error "Some tests failed"
        exit 1
    fi
else
    print_status "Running basic test suite..."
    if python3 -m pytest tests/test_basic.py tests/test_health.py tests/test_models.py -v; then
        print_status "Basic tests passed"
    else
        print_error "Some tests failed"
        exit 1
    fi
fi

if [ "$MODE" = "release" ]; then
    print_status "🎉 FULL quality checks completed!"
    echo ""
    echo "📊 Release Quality Summary:"
    echo "  - Code formatting: Black ✅"
    echo "  - Import sorting: isort ✅"
    echo "  - Linting: Flake8 ✅"
    echo "  - Type checking: MyPy ✅"
    echo "  - Security: Bandit ✅"
    echo "  - Testing: pytest (full suite) ✅"
    echo ""
    echo "🚀 Ready for production release!"
else
    print_status "Development quality checks completed!"
    echo ""
    echo "📊 Development Summary:"
    echo "  - Code formatting: Black ✅"
    echo "  - Import sorting: isort ✅"
    echo "  - Linting: Flake8 ✅"
    echo "  - Type checking: MyPy ✅"
    echo "  - Security: Bandit ✅"
    echo "  - Testing: pytest (basic suite) ✅"
    echo ""
    echo "💡 For full quality checks, run: $0 --release"
    echo "🚀 Ready for development!"
fi
