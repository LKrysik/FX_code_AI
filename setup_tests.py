#!/usr/bin/env python3
"""
Test Environment Setup Script
==============================

Automatically installs all dependencies and verifies the test environment.

Usage:
    python setup_tests.py
"""

import sys
import subprocess
import time
from pathlib import Path


class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_step(message: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}▶ {message}{Colors.ENDC}")


def print_success(message: str):
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def run_command(cmd: list, description: str, timeout: int = 120) -> bool:
    """Run a command and return success status"""
    try:
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            print_success(description)
            return True
        else:
            print_error(f"{description} - Failed")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print_error(f"{description} - Timeout")
        return False
    except Exception as e:
        print_error(f"{description} - Error: {e}")
        return False


def install_dependencies():
    """Install all required dependencies"""
    print_step("Installing Dependencies")

    # Install test dependencies
    print("\n1️⃣ Installing test dependencies...")
    if not run_command(
        [sys.executable, '-m', 'pip', 'install', '-q', '-r', 'test_requirements.txt'],
        "Test dependencies installed",
        timeout=180
    ):
        print_warning("Some test dependencies may have failed to install")

    # Install project dependencies (might have conflicts, so ignore-installed)
    print("\n2️⃣ Installing project dependencies...")
    critical_deps = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pydantic-settings',
        'httpx',
        'asyncpg',
        'pytest',
        'pytest-asyncio'
    ]

    for dep in critical_deps:
        run_command(
            [sys.executable, '-m', 'pip', 'install', '-q', dep],
            f"{dep} installed",
            timeout=60
        )

    # Install Playwright browsers
    print("\n3️⃣ Installing Playwright browsers...")
    run_command(
        [sys.executable, '-m', 'playwright', 'install', 'chromium'],
        "Playwright chromium installed",
        timeout=300
    )


def verify_environment():
    """Verify the test environment is ready"""
    print_step("Verifying Environment")

    all_ok = True

    # Check Python version
    print(f"\n✓ Python version: {sys.version.split()[0]}")

    # Check critical imports
    print("\nChecking critical imports:")
    critical_modules = [
        'pytest',
        'fastapi',
        'httpx',
        'pydantic',
        'pydantic_settings',
        'playwright'
    ]

    for module in critical_modules:
        try:
            __import__(module)
            print_success(f"{module} ✓")
        except ImportError:
            print_error(f"{module} - NOT FOUND")
            all_ok = False

    # Check backend
    print("\nChecking backend server:")
    try:
        import httpx
        response = httpx.get('http://localhost:8080/health', timeout=2)
        if response.status_code == 200:
            print_success("Backend is running ✓")
        else:
            print_warning("Backend not responding properly")
            all_ok = False
    except Exception:
        print_warning("Backend not running (start with: .\\start_all.ps1)")
        print("  Note: Backend is required for integration tests")

    # Check frontend
    print("\nChecking frontend server:")
    try:
        import httpx
        response = httpx.get('http://localhost:3000', timeout=2)
        if response.status_code == 200:
            print_success("Frontend is running ✓")
        else:
            print_warning("Frontend not responding")
    except Exception:
        print_warning("Frontend not running")
        print("  Note: Frontend is required for UI tests")

    return all_ok


def main():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("=" * 80)
    print("Test Environment Setup".center(80))
    print("=" * 80)
    print(Colors.ENDC)

    # Install dependencies
    install_dependencies()

    # Verify environment
    print()
    env_ok = verify_environment()

    # Summary
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("=" * 80)
    print("Setup Summary".center(80))
    print("=" * 80)
    print(Colors.ENDC)

    if env_ok:
        print_success("\n✓ All dependencies installed and verified!")
        print(f"\n{Colors.OKGREEN}Ready to run tests:{Colors.ENDC}")
        print("  python run_tests.py")
        print("  python run_tests.py --api")
        print("  python run_tests.py --coverage")
    else:
        print_warning("\n⚠ Setup completed with warnings")
        print("\nYou may need to:")
        print("  1. Start backend:  .\\start_all.ps1  (or manually)")
        print("  2. Start frontend: cd frontend && npm run dev")
        print("\nThen run: python run_tests.py")

    return 0 if env_ok else 1


if __name__ == '__main__':
    sys.exit(main())
