#!/usr/bin/env python3
"""
E2E Test Runner - Single Entry Point
=====================================

KISS (Keep It Simple, Stupid) test runner for all E2E tests.

Usage:
    python run_tests.py                  # Run ALL backend E2E tests
    python run_tests.py --api            # API tests only
    python run_tests.py --frontend       # Frontend E2E tests only (Playwright)
    python run_tests.py --integration    # Integration tests only
    python run_tests.py --fast           # Fast tests only (skip slow)
    python run_tests.py --verbose        # Verbose output
    python run_tests.py --coverage       # With coverage report
    python run_tests.py --html-report    # Generate HTML report
    python run_tests.py --detailed       # MAXIMUM detail: full logs, tracebacks, local vars

Output Files:
    test_results.xml                     # JUnit XML (ALWAYS generated, for CI/CD)
    test_report.html                     # HTML report (if --html-report)
    htmlcov/index.html                   # Coverage report (if --coverage)
    test_log_TIMESTAMP.txt               # Detailed log file (if --detailed)

Detailed Mode (--detailed):
    - Full tracebacks with local variables
    - DEBUG-level logging to file
    - Timestamped output files
    - Perfect for debugging failing tests

Frontend Unit Tests (Jest):
    cd frontend && npm test              # Run Jest unit tests
    cd frontend && npm run test:watch    # Watch mode
    cd frontend && npm run test:coverage # With coverage

Examples:
    python run_tests.py --api --verbose
    python run_tests.py --frontend --coverage
    python run_tests.py --all --html-report
    python run_tests.py --api --detailed              # Maximum debug info
    python run_tests.py --detailed --html-report      # All reports + detailed logs

Notes:
    - This runner executes backend E2E tests (pytest) in tests_e2e/
    - Frontend unit tests (Jest) are in frontend/src/__tests__/
    - Run frontend tests separately: cd frontend && npm test
    - JUnit XML is ALWAYS generated for CI/CD compatibility
"""

import sys
import argparse
import subprocess
import os
from pathlib import Path
import time
from typing import List
from datetime import datetime

# ANSI color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def check_prerequisites() -> bool:
    """Check if all prerequisites are met"""
    print_header("Checking Prerequisites")

    all_ok = True

    # Check pytest installed
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"pytest installed: {result.stdout.strip()}")
        else:
            print_error("pytest not found")
            all_ok = False
    except Exception as e:
        print_error(f"pytest not installed. Run: pip install pytest pytest-asyncio")
        all_ok = False

    # Check if backend is running (optional warning)
    try:
        import httpx
        response = httpx.get('http://localhost:8080/health', timeout=2)
        if response.status_code == 200:
            print_success("Backend server is running (localhost:8080)")
        else:
            print_warning("Backend server not responding properly")
    except Exception:
        print_warning("Backend server not running. Start with: .\\start_all.ps1")
        print_info("Some integration tests may fail without running backend")

    # Check if frontend is running (optional warning)
    try:
        import httpx
        response = httpx.get('http://localhost:3000', timeout=2)
        if response.status_code == 200:
            print_success("Frontend server is running (localhost:3000)")
        else:
            print_warning("Frontend server not responding")
    except Exception:
        print_warning("Frontend server not running")
        print_info("Frontend E2E tests require running frontend")

    # Check Playwright for frontend tests
    playwright_installed = False
    try:
        result = subprocess.run([sys.executable, '-m', 'playwright', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Playwright installed: {result.stdout.strip()}")
            playwright_installed = True
        else:
            print_warning("Playwright not found (needed for frontend tests)")
    except Exception:
        print_warning("Playwright not installed. Run: pip install playwright && playwright install")

    return all_ok


def build_pytest_command(args, timestamp: str = None) -> tuple[List[str], dict]:
    """Build pytest command based on arguments

    Returns:
        tuple: (command list, dict of generated file paths)
    """
    cmd = [sys.executable, '-m', 'pytest']
    generated_files = {}

    # Determine test path
    if args.api:
        cmd.append('tests_e2e/api')
    elif args.frontend:
        cmd.append('tests_e2e/frontend')
    elif args.integration:
        cmd.append('tests_e2e/integration')
    else:
        cmd.append('tests_e2e')  # All tests

    # Add markers for fast tests
    if args.fast:
        cmd.extend(['-m', 'not slow'])

    # Verbosity
    if args.verbose or args.detailed:
        cmd.append('-vv')
    else:
        cmd.append('-v')

    # Coverage
    if args.coverage:
        cmd.extend([
            '--cov=src',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov',
            '--cov-report=xml:coverage.xml',  # For CI/CD
        ])
        generated_files['coverage_html'] = 'htmlcov/index.html'
        generated_files['coverage_xml'] = 'coverage.xml'

    # Use provided timestamp or generate new one
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # HTML report
    if args.html_report:
        html_file = f'test_report_{timestamp}.html' if args.detailed else 'test_report.html'
        cmd.extend([
            f'--html={html_file}',
            '--self-contained-html'
        ])
        generated_files['html_report'] = html_file

    # JUnit XML report (always generate for CI/CD compatibility)
    junit_file = f'test_results_{timestamp}.xml' if args.detailed else 'test_results.xml'
    cmd.extend([
        f'--junitxml={junit_file}',
    ])
    generated_files['junit_xml'] = junit_file

    # Detailed logging
    if args.detailed:
        log_file = f'test_log_{timestamp}.txt'
        cmd.extend([
            f'--log-file={log_file}',
            '--log-file-level=DEBUG',
            '--log-cli=true',
            '--log-cli-level=INFO',
            '--tb=long',  # Full traceback
            '--showlocals',  # Show local variables in traceback
            '-vv',  # Very verbose
        ])
        generated_files['detailed_log'] = log_file
    else:
        # Output formatting
        cmd.extend([
            '--tb=short',  # Shorter traceback
        ])

    # Always colored output
    cmd.append('--color=yes')

    # Timeout (10 minutes max)
    cmd.extend(['--timeout=600'])

    # Parallel execution (if pytest-xdist installed)
    try:
        subprocess.run([sys.executable, '-m', 'pytest', '--help'], capture_output=True, text=True, check=True)
        # Check if -n flag is available (pytest-xdist)
        help_output = subprocess.run([sys.executable, '-m', 'pytest', '--help'], capture_output=True, text=True).stdout
        if '-n' in help_output:
            # Use auto-detect number of CPUs
            cmd.extend(['-n', 'auto'])
            print_info("Parallel execution enabled (pytest-xdist)")
    except Exception:
        pass

    return cmd, generated_files


def run_tests(cmd: List[str]) -> int:
    """Run pytest with the given command"""
    print_header("Running Tests")

    # Debug: Show Python executable
    print_info(f"Python: {sys.executable}")
    print_info(f"Command: {' '.join(cmd)}\n")

    start_time = time.time()

    # Run pytest
    try:
        result = subprocess.run(cmd)
        exit_code = result.returncode
    except FileNotFoundError as e:
        print_error(f"Failed to run pytest: {e}")
        print_error("\nThis usually means pytest has wrong shebang (old virtualenv path).")
        print_warning("FIX: Reinstall pytest in current virtualenv:")
        print(f"  pip uninstall pytest -y")
        print(f"  pip install pytest pytest-asyncio pytest-timeout")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1

    elapsed_time = time.time() - start_time

    print(f"\n{Colors.BOLD}Time elapsed: {elapsed_time:.2f}s{Colors.ENDC}\n")

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description='E2E Test Runner - Single Entry Point',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                     # Run all backend E2E tests
  python run_tests.py --api               # API tests only
  python run_tests.py --frontend          # Frontend E2E tests only (Playwright)
  python run_tests.py --integration       # Integration tests only
  python run_tests.py --fast              # Fast tests only
  python run_tests.py --api --verbose     # API tests with verbose output
  python run_tests.py --all --coverage    # All tests with coverage

Frontend Unit Tests (Jest):
  cd frontend && npm test                 # Run Jest unit tests
  cd frontend && npm run test:coverage    # With coverage report
        """
    )

    # Test selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--api', action='store_true', help='Run API tests only')
    test_group.add_argument('--frontend', action='store_true', help='Run frontend tests only')
    test_group.add_argument('--integration', action='store_true', help='Run integration tests only')
    test_group.add_argument('--all', action='store_true', help='Run all tests (default)')

    # Test options
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--html-report', action='store_true', help='Generate HTML test report')
    parser.add_argument('--detailed', action='store_true', help='Maximum detail: full logs, tracebacks, local vars (generates timestamped files)')
    parser.add_argument('--skip-prereq', action='store_true', help='Skip prerequisite checks')

    args = parser.parse_args()

    # Print banner
    print_header("FX Code AI - E2E Test Suite")

    # Check prerequisites
    if not args.skip_prereq:
        prereq_ok = check_prerequisites()
        if not prereq_ok:
            print_error("Prerequisites not met. Install required packages or use --skip-prereq")
            return 1

    # Generate timestamp once for consistency
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build and run pytest command
    cmd, generated_files = build_pytest_command(args, timestamp)
    exit_code = run_tests(cmd)

    # Print summary
    print_header("Test Run Summary")

    if exit_code == 0:
        print_success("All tests passed! ✓")
    else:
        print_error(f"Tests failed with exit code {exit_code}")
        if not args.verbose and not args.detailed:
            print_info("Run with --verbose or --detailed for more information")

    # Show generated reports
    print("\n" + Colors.BOLD + "Generated Reports:" + Colors.ENDC)

    # Display all generated files
    for file_type, file_path in generated_files.items():
        if os.path.exists(file_path):
            if file_type == 'detailed_log':
                print_success(f"Detailed Log: {file_path}")
                print_info("  → Full tracebacks, local variables, DEBUG logs")
            elif file_type == 'junit_xml':
                print_info(f"JUnit XML: {file_path}")
            elif file_type == 'html_report':
                print_info(f"HTML Report: {file_path}")
            elif file_type == 'coverage_html':
                print_info(f"Coverage HTML: {file_path}")
            elif file_type == 'coverage_xml':
                print_info(f"Coverage XML: {file_path}")

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
