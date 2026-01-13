# Development Workflow

This document describes the development workflow, code quality tools, and CI/CD processes for the local-ai-packaged project.

## Code Quality Tools

### Pre-commit Hooks

Pre-commit hooks automatically run checks and fixes before each commit to ensure code quality and consistency.

#### Installation

```bash
# Install pre-commit (if not already installed)
pip install pre-commit
# or
uv pip install pre-commit

# Install the git hooks
pre-commit install
```

#### Running Hooks Manually

```bash
# Run hooks on all files
pre-commit run --all-files

# Run a specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files
```

#### What the Hooks Check

The pre-commit configuration (`.pre-commit-config.yaml`) includes:

- **Python Formatting**: Black automatically formats Python code (line-length: 100)
- **Python Linting**: Ruff checks for code quality issues and auto-fixes when possible
- **Type Checking**: Pyright validates type hints and catches type-related errors
- **Python Syntax**: Validates Python syntax using `py_compile` and AST parsing
- **AST Validation**: Enhanced AST validation catches more syntax issues than `py_compile`
- **YAML Validation**: yamllint checks YAML files for syntax and style
- **Docker Compose Validation**: Validates docker-compose files
- **Secret Detection**: Scans for accidentally committed secrets
- **File Checks**: Trailing whitespace, end-of-file newlines, large files, merge conflicts
- **Comprehensive Validation**: Manual hook for full codebase validation (run with `pre-commit run comprehensive-validation --all-files`)

#### Bypassing Hooks (Emergency Only)

If you need to bypass pre-commit hooks in an emergency:

```bash
git commit --no-verify
```

**Warning**: Only use this when absolutely necessary. The hooks are there to prevent errors and maintain code quality.

### Code Formatting

#### Python

We use **Black** for code formatting with a line length of 100 characters:

```bash
# Format all Python files
black --line-length=100 .

# Check formatting without making changes
black --check --line-length=100 .
```

#### Ruff

We use **Ruff** for linting and import sorting:

```bash
# Run linting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check import sorting
ruff check --select I .
```

Configuration is in `pyproject.toml` under `[tool.ruff]`.

#### Type Checking

We use **Pyright** for type checking:

```bash
# Run type checking
pyright --pythonversion=3.10 .
```

Pyright is automatically run via pre-commit hooks and will catch type-related errors before commits.

### Comprehensive Code Validation

A comprehensive validation script (`scripts/validate_code.py`) performs multiple checks:

- **Syntax Validation**: AST parsing to catch syntax errors
- **Import Syntax Validation**: Validates import statement syntax
- **Type Hints Validation**: Validates type hint syntax

```bash
# Run comprehensive validation
python3 scripts/validate_code.py

# Or via pre-commit (manual hook)
pre-commit run comprehensive-validation --all-files
```

This script validates all Python files in the project and provides detailed error reporting.

### YAML Linting

YAML files are validated using **yamllint**:

```bash
# Lint all YAML files
yamllint -c .yamllint.yml $(find . -name "*.yml" -o -name "*.yaml")
```

Configuration is in `.yamllint.yml`.

## GitHub Actions CI/CD

### Workflows

The project uses several GitHub Actions workflows for continuous integration:

#### 1. Python Code Quality (`python-quality.yml`)

Runs on: Push and pull requests affecting Python files

Checks:
- Python syntax validation (py_compile)
- Comprehensive AST validation (catches more syntax issues)
- Comprehensive code validation script
- Black formatting check
- Ruff linting
- Import sorting
- Runs for all Python projects (root, lambda-server, discord-bot)

#### 2. YAML and Docker Validation (`yaml-docker-validation.yml`)

Runs on: Push and pull requests affecting YAML or Docker files

Checks:
- YAML syntax validation with yamllint
- Docker Compose file validation
- Dockerfile linting with Hadolint

#### 3. Security Scanning (`security-scan.yml`)

Runs on: Push, pull requests, and weekly schedule

Checks:
- Secret detection using detect-secrets
- Python dependency vulnerability scanning with pip-audit
- Docker image security scanning (optional, disabled by default)

#### 4. Test Suite (`test-suite.yml`)

Runs on: Push, pull requests, nightly schedule, and manual trigger

Executes:
- Lambda server pytest tests with coverage
- Discord bot pytest tests
- Sample file validation

### Required Checks

To require these checks to pass before merging PRs:

1. Go to repository Settings → Branches
2. Add a branch protection rule for `main` and `develop`
3. Enable "Require status checks to pass before merging"
4. Select the workflows you want to require:
   - `Python Code Quality`
   - `YAML and Docker Validation`
   - `Test Suite`

## Local Development

### Running Tests

#### Lambda Server

```bash
cd 04-lambda
uv run pytest tests/ -v
uv run pytest tests/ -v --cov=server --cov-report=term
```

#### Discord Bot

```bash
cd 03-apps/discord-bot
uv run pytest tests/ -v
```

### Validating Code Before Committing

1. **Run pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

2. **Format code**:
   ```bash
   black --line-length=100 .
   ruff format .
   ```

3. **Check linting**:
   ```bash
   ruff check .
   ```

4. **Validate YAML**:
   ```bash
   yamllint -c .yamllint.yml $(find . -name "*.yml" -o -name "*.yaml")
   ```

5. **Run tests**:
   ```bash
   # Lambda server
   cd 04-lambda && uv run pytest tests/ -v

   # Discord bot
   cd 03-apps/discord-bot && uv run pytest tests/ -v
   ```

## Common Issues and Fixes

### Pre-commit Hook Failures

#### Black Formatting Issues

```bash
# Auto-fix
black --line-length=100 .

# Then commit again
git add .
git commit
```

#### Ruff Linting Issues

```bash
# Auto-fix what can be fixed
ruff check --fix .

# Review remaining issues manually
ruff check .
```

#### YAML Linting Issues

```bash
# Check what's wrong
yamllint -c .yamllint.yml <file>

# Fix indentation issues (usually 2 spaces)
# Fix line length issues (max 100 characters)
```

#### Secret Detection False Positives

If detect-secrets flags something that's not actually a secret:

1. Update the baseline:
   ```bash
   detect-secrets scan --baseline .secrets.baseline
   ```

2. Commit the updated baseline:
   ```bash
   git add .secrets.baseline
   git commit -m "Update secrets baseline"
   ```

### CI/CD Failures

#### Python Tests Failing

1. Run tests locally to reproduce:
   ```bash
   cd 04-lambda
   uv run pytest tests/ -v
   ```

2. Check for missing dependencies or environment variables
3. Ensure all test files are properly formatted and linted

#### Docker Compose Validation Failing

1. Validate locally:
   ```bash
   docker compose -f <file> config
   ```

2. Check for missing environment variables (CI may not have all env vars)
3. Some validation failures may be warnings if env vars are missing

## Project Structure

### Python Projects

- **Root**: General utilities and orchestration (`start_services.py`)
- **Lambda Server** (`04-lambda/`): FastAPI server with MCP and REST APIs
- **Discord Bot** (`03-apps/discord-bot/`): Discord bot for Immich integration and AI character interactions

Each Python project has its own `pyproject.toml` with dependencies and tool configurations.

### Configuration Files

- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `.yamllint.yml`: YAML linting rules
- `pyproject.toml`: Python tool configuration (Black, Ruff)
- `.github/workflows/`: GitHub Actions workflows

## Best Practices

1. **Always run pre-commit hooks** before committing
2. **Fix formatting and linting issues** before pushing
3. **Write tests** for new features
4. **Keep commits focused** - one logical change per commit
5. **Update documentation** when adding new features or changing behavior
6. **Never commit secrets** - use environment variables or Infisical
7. **Review CI/CD results** before merging PRs

## Getting Help

- Check the [AGENTS.md](../AGENTS.md) for project-specific conventions
- Review existing code for patterns and style
- Ask in issues or discussions if you're unsure about something
