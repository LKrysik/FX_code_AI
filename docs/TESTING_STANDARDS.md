# Testing Standards and Procedures

> **⚠️ DEPRECATED**: This document is outdated and no longer reflects the current testing approach.
>
> **✅ USE INSTEAD**:
> - **Quick Start**: `QUICK_START_TESTS.md` (3-minute setup)
> - **Complete Guide**: `README_TESTS.md` (full E2E test suite documentation)
> - **Agent Instructions**: `.claude/instructions.md` (Testing section)
>
> The project now uses a unified E2E test suite with 224 automated tests (213 API + 9 Frontend + 2 Integration).
>
> **Single command to run all tests**: `python run_tests.py`
>
> See the files above for current testing practices.

---

## ARCHIVED CONTENT (Historical Reference Only)

## 1. Overview

This document defines the mandatory testing standards for this project. Its purpose is to ensure that all code is rigorously tested, meets quality standards, and that the testing process is applied consistently across all development activities. All commands that involve testing (`/start_sprint`, `/work`, `/verify_implementation`, `/end_sprint`) must adhere to the standards defined herein.

## 2. Core Testing Requirements

### 2.1. Backend Testing

-   **Framework**: All backend tests must be written and executed using the `pytest` framework.
-   **Scope**: Every function, class, and API endpoint must have corresponding unit and integration tests.
-   **Command**: The standard command for running backend tests is:
    ```bash
    pytest tests/ --cov=src --cov-report=term-missing
    ```

### 2.2. Frontend Testing

-   **Framework**: All frontend, end-to-end, and user interaction tests must be written and executed using `pytest-playwright`.
-   **Scope**: Every user action, component, and workflow must be covered by `playwright` tests. This includes, but is not limited to, button clicks, form submissions, navigation, and dynamic content rendering.
-   **Command**: The standard command for running frontend tests is:
    ```bash
    pytest --playwright tests/frontend/
    ```

## 3. Test Structure

The `tests/` directory must be organized as follows to distinguish between different types of tests:

-   `tests/backend/`: Contains all `pytest` tests for the backend.
-   `tests/frontend/`: Contains all `pytest-playwright` tests for the frontend.
-   `tests/integration/`: Contains tests that verify the interaction between frontend and backend components.

## 4. Test Generation and Traceability

-   During the `/start_sprint` command, all generated test scenarios must be explicitly tagged as either `[backend-pytest]` or `[frontend-playwright]`.
-   Each test scenario must be traceable to a specific user requirement (`USER_REC_`) and a technical task.
-   The verification process (`/verify_implementation`) must confirm that the correct test framework was used for each implemented task.

## 5. Quality Gates

-   **Coverage**: A minimum of 85% test coverage is required for the backend. All frontend user actions must have 100% test coverage.
-   **Passing Tests**: No code can be merged or marked as "DONE" if any test is failing.
-   **Sprint Closure**: The `/end_sprint` command will fail if the testing standards for all completed tasks in the sprint have not been met.