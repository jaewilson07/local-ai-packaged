# Sample Files Rules

Applies to files in the `sample/` directory.

## Sample File Guidelines

- Sample files should be created in the `sample/` directory
- Sample capability tests go in `sample/capability/`
- Keep sample files self-contained and well-documented
- Sample files are for testing, demonstration, and learning purposes

## Authentication Pattern

Use shared helpers from `sample/shared/auth_helpers.py`:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email

api_base_url = get_api_base_url()
headers = get_auth_headers()
cloudflare_email = get_cloudflare_email()
```

## Testing Patterns

- Use `create_run_context()` for direct tool testing
- Use `agent.run(deps=deps)` for full agent workflow testing
