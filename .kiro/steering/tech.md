# Tech Stack & Build System

## Language & Runtime
- Python 3.13+
- Package manager: uv

## Backend Framework
- Django 6.0+
- Django Rest Framework (planned)

## AI/ML
- Google GenAI SDK (`google-genai`)
- Models: Gemini 3, Qwen, Mistral

## Database (planned)
- PostgreSQL
- Vector DB for embeddings

## Voice Services (planned)
- Twilio for telephony
- ElevenLabs for voice cloning

## Frontend (planned)
- Next.js
- Tailwind CSS

## Common Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py

# Add a new dependency
uv add <package-name>

# Run Django management commands (when configured)
uv run python manage.py <command>
```

## Environment
- Use `.env` file for secrets and configuration
- Never commit `.env` to version control
