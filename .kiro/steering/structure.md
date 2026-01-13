# Project Structure

```
neurotwin/
├── .env                 # Environment variables (secrets, config)
├── .gitignore           # Git ignore rules
├── .python-version      # Python version (3.13)
├── .venv/               # Virtual environment (managed by uv)
├── main.py              # Application entry point
├── pyproject.toml       # Project config and dependencies
├── uv.lock              # Locked dependencies
└── README.md            # Project documentation
```

## Current State
This is an early-stage project with minimal structure. As it grows, expect:

- `neurotwin/` - Django project root
- `apps/` - Django applications (csm, memory, automation, voice, etc.)
- `api/` - REST API endpoints
- `tests/` - Test suite

## Conventions
- Entry point: `main.py`
- Dependencies managed via `pyproject.toml` and `uv.lock`
- Virtual environment in `.venv/` (excluded from git)
- Configuration via environment variables in `.env`
