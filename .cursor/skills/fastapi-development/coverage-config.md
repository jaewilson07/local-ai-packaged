# Coverage Configuration

Templates and best practices for pytest-cov and coverage.py configuration.

## .coveragerc Configuration

Create a `.coveragerc` file in your project root:

```ini
[run]
source = src
branch = True
parallel = True
omit =
    */tests/*
    */__init__.py
    */migrations/*
    */conftest.py
    */_version.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == "__main__"
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod
    except ImportError
    pass

show_missing = True
precision = 2

[html]
directory = htmlcov
title = Project Coverage Report

[xml]
output = coverage.xml
```

## pyproject.toml Configuration

Alternative configuration in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
branch = true
parallel = true
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == \"__main__\"",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
show_missing = true
precision = 2
fail_under = 80

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

## pytest.ini / pyproject.toml pytest Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = """
    -v
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
"""
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

## Common Commands

### Basic Coverage

```bash
# Run tests with coverage
pytest --cov=src

# With terminal report showing missing lines
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View report

# Generate XML for CI tools
pytest --cov=src --cov-report=xml
```

### Coverage Thresholds

```bash
# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80

# Check specific modules
pytest --cov=src/capabilities --cov-fail-under=85
```

### Selective Coverage

```bash
# Cover only specific module
pytest --cov=src/services/auth tests/test_auth/

# Multiple source directories
pytest --cov=src/capabilities --cov=src/workflows

# Exclude files from coverage
pytest --cov=src --cov-omit="*/migrations/*,*/tests/*"
```

### Branch Coverage

```bash
# Enable branch coverage (recommended)
pytest --cov=src --cov-branch

# This measures:
# - Line coverage: which lines were executed
# - Branch coverage: which branches (if/else) were taken
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"

      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

## Coverage Best Practices

### 1. Focus on Meaningful Coverage

Don't chase 100% - focus on:
- Critical business logic
- Authentication/authorization
- Data validation
- Error handling paths

### 2. Exclude Generated Code

```ini
[run]
omit =
    */migrations/*
    */_generated/*
    */vendor/*
```

### 3. Mark Defensive Code

Use `# pragma: no cover` for defensive code that's hard to test:

```python
def process_data(data):
    if data is None:  # pragma: no cover
        raise ValueError("Data cannot be None")
    # ... rest of function
```

### 4. Coverage by Module

Track coverage per module to identify weak areas:

```bash
# Generate per-module report
pytest --cov=src --cov-report=term:skip-covered
```

### 5. Diff Coverage for PRs

Use `diff-cover` to check coverage on changed lines:

```bash
pip install diff-cover

# Generate coverage XML first
pytest --cov=src --cov-report=xml

# Check coverage on diff
diff-cover coverage.xml --compare-branch=origin/main --fail-under=80
```

## Troubleshooting

### Coverage Not Detecting Files

Ensure source is correct:
```bash
pytest --cov=. --cov-report=term-missing  # Cover everything
```

### Async Code Not Covered

Make sure pytest-asyncio is configured:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Missing Lines in Report

Check if files are being imported before coverage starts:
```bash
# Use --cov-config to specify config file explicitly
pytest --cov=src --cov-config=.coveragerc
```

## Target Coverage Levels

| Code Type | Recommended Coverage |
|-----------|---------------------|
| Core business logic | 90%+ |
| API endpoints | 85%+ |
| Utility functions | 80%+ |
| Configuration/setup | 60%+ |
| Overall project | 80%+ |
