# Core Development Rules

These rules apply to all code in the repository.

## Code Style

- Follow the patterns established in `AGENTS.md`
- Use Python 3.10+ features
- Black formatting (line-length: 100)
- Ruff linting (target: py310)

## Exception Handling

- Prefer loud errors over silent failures
- Never use naked exceptions
- Avoid catching `Exception` unless absolutely necessary
- Use structured exception layer from `server.core.exceptions`
- Use `@handle_project_errors()` decorator for API endpoints

## Project Structure

- Stack-based Docker Compose architecture
- Monorepo with numbered stacks
- See `AGENTS.md` for detailed conventions
