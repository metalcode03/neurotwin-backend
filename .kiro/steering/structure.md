# Project Structure

```
neurotwin/                        # Repo root
├── .env                          # Environment variables (secrets, config)
├── .env.example                  # Example env template
├── .gitignore
├── .python-version               # Python 3.13
├── .venv/                        # Virtual environment (managed by uv)
├── manage.py                     # Django management entry point
├── main.py                       # Alternative entry point
├── pyproject.toml                # Project config and dependencies
├── uv.lock                       # Locked dependencies
├── docker-compose.yml            # Local services (PostgreSQL, Redis)
├── pytest.ini                    # Test configuration
├── README.md
│
├── neurotwin/                    # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/                         # Django applications
│   ├── authentication/           # Custom user model, JWT auth, email verification
│   ├── subscription/             # Subscription tiers, plan management
│   ├── credits/                  # Credit-based AI usage tracking & routing
│   │   └── providers/            # LLM provider adapters (gemini, mistral, cerebras)
│   ├── csm/                      # Cognitive Signature Model (personality, tone, habits)
│   ├── twin/                     # Twin core logic, dataclasses, views
│   ├── memory/                   # Vector memory engine
│   ├── learning/                 # Behavioral learning and profile updates
│   ├── safety/                   # Kill-switch, permissions, audit logs
│   ├── automation/               # Workflow engine, middleware, webhooks
│   │   └── middleware/           # KillSwitch, TwinPermission, security middleware
│   ├── voice/                    # Voice Twin (Twilio/ElevenLabs, planned)
│   └── core/                     # Shared app-level utilities
│
├── core/                         # Project-level shared utilities
│   ├── ai/                       # LLM adapter interfaces
│   ├── api/                      # Shared API helpers
│   ├── db/                       # DB utilities
│   └── tasks/                    # Shared Celery task helpers
│
├── tests/                        # Backend test suite (pytest)
│
├── docs/                         # Developer documentation
│   ├── integration-engine-api.md
│   ├── integration-engine-developer-guide.md
│   ├── subscription-api.md
│   ├── redis-setup.md
│   └── user-guide.md
│
├── scripts/                      # Utility scripts
├── logs/                         # Rotating log files (gitignored)
│
└── neuro-frontend/               # Next.js frontend
    └── src/
        ├── app/                  # App Router pages
        │   ├── auth/             # Login, register, password reset
        │   ├── dashboard/        # Main dashboard (twin, memory, automation, security, apps)
        │   ├── onboarding/       # Onboarding wizard
        │   └── oauth/            # OAuth callback handling
        ├── components/           # UI components
        │   ├── apps/             # App marketplace components
        │   ├── auth/
        │   ├── automation/       # Workflow editor, node builder
        │   ├── brain/            # AI brain / Twin chat
        │   ├── credits/          # Credit usage display
        │   ├── layout/           # Sidebar, DashboardLayout
        │   ├── marketplace/      # App install/configure flows
        │   ├── memory/           # Memory panel
        │   ├── onboarding/       # Onboarding wizard
        │   ├── profile/          # User profile
        │   ├── security/         # Audit log, data export
        │   ├── twin/             # Twin overview, blend slider
        │   ├── ui/               # Primitives (GlassPanel, etc.)
        │   └── voice/            # Voice Twin UI
        ├── hooks/                # Custom React hooks (useAuth, etc.)
        ├── lib/
        │   └── api/              # Typed API clients (auth, twin, automation, marketplace, credits, brain)
        └── types/                # TypeScript type definitions
```

## Conventions
- Backend entry point: `manage.py` (Django) / `main.py` (standalone)
- All business logic in `services.py`, never in views or serializers
- Use `selectors.py` for complex DB queries
- LLM calls go through adapters in `apps/credits/providers/` or `core/ai/`
- Frontend API clients live in `neuro-frontend/src/lib/api/`
- Dependencies managed via `pyproject.toml` + `uv.lock`
- Virtual environment in `.venv/` (excluded from git)
- Configuration via environment variables in `.env`
