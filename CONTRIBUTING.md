# Contributing to FX Cryptocurrency Trading System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and constructive
- Focus on what is best for the project
- Show empathy towards other contributors
- Accept constructive criticism gracefully

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- QuestDB 9.1.0+
- Git

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/FX_code_AI_v2.git
   cd FX_code_AI_v2
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Set up Frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Set up QuestDB**
   ```bash
   python database/questdb/install_questdb.py
   ```

5. **Read the documentation**
   - [README.md](README.md) - Quick start
   - [CLAUDE.md](CLAUDE.md) - Development guidelines
   - [docs/INDEX.md](docs/INDEX.md) - Full documentation map

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions/fixes

### 2. Make Changes

**MANDATORY: Follow Pre-Change Protocol**

Before making ANY code changes, you MUST:

1. **Analyze Architecture** - Read all relevant source files
2. **Assess Impact** - Analyze effects on entire program
3. **Verify Assumptions** - NEVER assume without validation
4. **Report Issues** - Document architectural problems BEFORE fixing

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for full protocol.

### 3. Write Tests

- Unit tests for new functions/classes
- Integration tests for component interactions
- Place tests in `tests/` mirroring `src/` structure

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/domain/services/test_my_feature.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### 4. Update Documentation

- Update relevant docs in `docs/`
- Update docstrings in code
- Update CHANGELOG.md if applicable

### 5. Commit Changes

```bash
git add .
git commit -m "feat: Add new indicator for volume analysis"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `docs:` - Documentation
- `test:` - Tests
- `chore:` - Maintenance

## Coding Standards

### Python

- **Formatter**: Black (line length 120)
- **Linter**: Ruff + Pylint
- **Type Hints**: Use type hints for all functions
- **Imports**: First-party → Third-party → Standard library (use isort)
- **Documentation**: Docstrings for all public functions/classes

Example:
```python
from src.domain.models import MarketData
from typing import List, Optional
import asyncio


async def process_market_data(
    data: List[MarketData],
    symbol: str
) -> Optional[float]:
    """
    Process market data and calculate average price.

    Args:
        data: List of market data points
        symbol: Trading symbol

    Returns:
        Average price or None if no data
    """
    if not data:
        return None

    prices = [d.price for d in data if d.symbol == symbol]
    return sum(prices) / len(prices) if prices else None
```

### TypeScript

- **Formatter**: Prettier
- **Linter**: ESLint (Next.js config)
- **Type Safety**: Strict mode enabled
- **Components**: Functional components with hooks

Example:
```typescript
interface MarketDataProps {
  symbol: string;
  onUpdate: (price: number) => void;
}

export const MarketDataDisplay: React.FC<MarketDataProps> = ({
  symbol,
  onUpdate
}) => {
  const [price, setPrice] = useState<number>(0);

  useEffect(() => {
    // Component logic
  }, [symbol]);

  return <div>{/* JSX */}</div>;
};
```

### Anti-Patterns (NEVER DO THIS)

- ❌ `defaultdict` for long-lived structures → memory leaks
- ❌ Global Container access → breaks DI
- ❌ Business logic in Container → belongs in domain
- ❌ Code duplication → extract to shared functions
- ❌ Hardcoded values → use configuration
- ❌ Skipping pre-change protocol

## Testing

### Test Organization

Tests are organized to mirror the source structure:

```
tests/
├── unit/           # Fast unit tests (<1s)
├── integration/    # Integration tests (<10s)
├── e2e/            # End-to-end tests (>10s)
├── api/            # Mirrors src/api/
├── domain/         # Mirrors src/domain/
└── fixtures/       # Shared test data
```

### Writing Tests

```python
import pytest
from tests.fixtures import sample_price_data


def test_indicator_calculation(sample_price_data):
    """Test that RSI indicator calculates correctly"""
    # Arrange
    indicator = RSIIndicator(period=14)

    # Act
    result = indicator.calculate(sample_price_data)

    # Assert
    assert 0 <= result <= 100
    assert result is not None


@pytest.mark.integration
async def test_data_collection_flow():
    """Integration test for complete data collection flow"""
    # Test implementation
    pass
```

### Test Markers

Use pytest markers to categorize tests:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow-running tests

## Documentation

### When to Update Documentation

- **Always**: When adding new features
- **Always**: When changing public APIs
- **Always**: When fixing bugs (update troubleshooting if applicable)
- **Consider**: When refactoring (if architecture changes)

### Documentation Structure

- **README.md** - Quick start and overview
- **CLAUDE.md** - Development guidelines for AI
- **docs/** - Detailed documentation (see docs/INDEX.md)

### Writing Good Documentation

✅ **Good**:
```markdown
## Adding a New Indicator

1. Create `src/domain/services/indicators/my_indicator.py`
2. Implement `IncrementalIndicator` interface
3. Register in `IndicatorCalculator`
4. Add tests in `tests/domain/services/indicators/`
5. Document in `docs/trading/INDICATORS.md`
```

❌ **Bad**:
```markdown
## Indicators

You can add indicators. See the code for examples.
```

## Pull Request Process

### Before Submitting

1. ✅ All tests pass (`pytest tests/`)
2. ✅ Code follows coding standards (Black, Ruff, ESLint)
3. ✅ Documentation updated
4. ✅ Commit messages follow convention
5. ✅ No merge conflicts with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

### Review Process

1. Submit PR with clear description
2. Automated checks run (tests, linting)
3. Code review by maintainer
4. Address feedback
5. Approval and merge

### After Merge

- Delete your branch
- Update your local main branch
- Close related issues

## Questions?

- Check [docs/INDEX.md](docs/INDEX.md) for documentation
- Review existing code for examples
- Ask in pull request comments

Thank you for contributing! 🎉
