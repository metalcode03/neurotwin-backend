# 🧠 NeuroTwin — Your Cognitive Digital Twin

NeuroTwin is a platform that creates a **living digital twin of your mind**.  
It doesn’t just assist — it **learns how you think, decide, speak, prioritize and act**, then operates across your apps, chats, meetings and calls.

---

## 🚀 What NeuroTwin Does

- Learns your language style, productivity rhythm and decision behavior
- Acts autonomously across connected platforms
- Handles chats, documents, scheduling, reminders and meetings
- Answers phone calls using your cloned voice
- Lets you control how human or how AI your Twin behaves

---

## 🧬 Core Systems

| Module | Description |
|------|-------------|
| Cognitive Signature Model (CSM) | Stores your personality, tone, habits and decision patterns |
| Vector Memory Engine | Long-term memory using embeddings |
| Automation Brain | Executes workflows across connected apps |
| Voice Identity Engine | Handles real phone calls in your voice |
| Behavioral Safety Layer | Kill-switch, permissions, audit logs |

---

## 🎚 Cognitive Blend Slider

You decide how much of *you* vs *AI logic* your Twin should use.

| Level | Mode |
|------|------|
| 0% | Raw AI |
| 25% | Light Blend |
| 50% | Hybrid |
| 75% | Deep Twin |
| 100% | Full Cognitive Clone |

**Formula:**

```

Final_Output = (User_Profile × Blend_Level) + (AI_Reasoning × (1 - Blend_Level))

```

---

## 🧩 Automation Integrations

NeuroTwin features a **Scalable Integration Engine** that supports multiple authentication strategies and provides production-ready integration capabilities.

### Supported Platforms

- **Messaging**: WhatsApp (Meta WABA), Telegram, Slack
- **Email**: Gmail, Outlook
- **Meetings**: Google Meet, Zoom
- **Productivity**: Google Docs, Microsoft Office, Calendar
- **Business**: CRM tools, custom APIs

### Integration Features

- **Multi-Auth Support**: OAuth 2.0, Meta Business API, API Key authentication
- **Queue-Based Processing**: Celery + Redis for asynchronous message handling
- **Rate Limiting**: Redis-based sliding window to prevent API quota exhaustion
- **Fault Tolerance**: Exponential backoff retry with circuit breaker pattern
- **Security**: Fernet encryption for all credentials with separate keys per auth type
- **Health Monitoring**: Real-time integration health status and metrics

### Authentication Types

| Type | Use Case | Examples |
|------|----------|----------|
| OAuth 2.0 | Standard OAuth providers | Google, Slack, Microsoft |
| Meta Business | Meta platforms with WABA | WhatsApp Business API |
| API Key | Simple API authentication | Custom APIs, webhooks |

Each integration has configurable behavior rules and rate limits.

---

## 📞 Voice Twin

- Each Twin gets a virtual phone number
- Upload voice samples for cloning
- Twin answers real calls
- Full transcripts stored
- Emergency kill-switch always available

---

## 💳 Pricing Plans

| Plan | Price | Models | Features |
|------|------|--------|----------|
| Free | $0 | Gemini-3 Flash, Cerebras, Mistral | Chat, light memory |
| Pro | $19/mo | Gemini-3 Pro | Cognitive learning |
| Twin+ | $49/mo | Gemini-3 Pro | Voice Twin |
| Executive | $99/mo | Gemini-3 Pro + Custom | Autonomous workflows |

---

## 🛠 Tech Stack

### Backend
- **Framework**: Django 6.0+ with Django Rest Framework
- **Task Queue**: Celery + Redis for async processing
- **Database**: PostgreSQL with connection pooling
- **Cache & Rate Limiting**: Redis with sliding window algorithm
- **AI Models**: Gemini 3, Cerebras, Mistral
- **Vector DB**: For embeddings and long-term memory

### Integration Engine
- **Authentication**: OAuth 2.0, Meta Business API, API Key strategies
- **Message Processing**: Queue-based with rate limiting and retry logic
- **Security**: Fernet encryption, webhook signature verification
- **Monitoring**: Prometheus metrics, structured logging, health checks

### Voice & Communication
- **Telephony**: Twilio
- **Voice Cloning**: ElevenLabs

### Frontend
- **Framework**: Next.js
- **Styling**: Tailwind CSS

### Infrastructure
- **Deployment**: Docker, systemd services
- **Monitoring**: Prometheus, Grafana, Sentry
- **Secrets Management**: Environment variables, AWS Secrets Manager

---

## 🚀 Development Setup

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis (for Celery and caching)
- uv package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd neurotwin

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Generate encryption keys (IMPORTANT!)
# Generate separate keys for each credential type
python -c "from cryptography.fernet import Fernet; print('OAUTH_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "from cryptography.fernet import Fernet; print('META_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "from cryptography.fernet import Fernet; print('API_KEY_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Generate Meta webhook verify token
python -c "import secrets; print('META_WEBHOOK_VERIFY_TOKEN=' + secrets.token_urlsafe(32))"

# Add the generated keys to your .env file

# Run database migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Start Django development server
uv run python manage.py runserver
```

### Running Celery Workers

NeuroTwin uses Celery for asynchronous task processing (webhooks, message delivery, AI responses).

**Start Celery worker (all queues):**
```bash
uv run python manage.py celery_worker
```

**Start worker for specific queues:**
```bash
# High priority tasks only
uv run python manage.py celery_worker --queue high_priority

# Incoming messages only
uv run python manage.py celery_worker --queue incoming_messages

# Outgoing messages only
uv run python manage.py celery_worker --queue outgoing_messages

# Multiple queues
uv run python manage.py celery_worker --queue high_priority,incoming_messages
```

**Start worker with custom concurrency:**
```bash
uv run python manage.py celery_worker --concurrency 8
```

**Start worker with autoscaling:**
```bash
uv run python manage.py celery_worker --autoscale 10,3
```

**Start Celery Beat (scheduled tasks):**
```bash
uv run python manage.py celery_beat
```

**Production deployment:**
```bash
# Start multiple workers for different queues
uv run python manage.py celery_worker --queue high_priority --concurrency 2 &
uv run python manage.py celery_worker --queue incoming_messages --concurrency 4 &
uv run python manage.py celery_worker --queue outgoing_messages --concurrency 4 &
uv run python manage.py celery_beat &
```

### Queue Architecture

| Queue | Purpose | Priority |
|-------|---------|----------|
| `high_priority` | AI responses, token refresh | 10 |
| `incoming_messages` | Webhook processing | 5 |
| `outgoing_messages` | Message delivery | 5 |
| `default` | Other background tasks | 1 |

---

## 🔐 Security Configuration

### Encryption Keys

NeuroTwin uses **Fernet symmetric encryption** to protect integration credentials at rest. Different encryption keys are used for different credential types to enhance security.

**Requirements:**
- `OAUTH_ENCRYPTION_KEY` - Encrypts OAuth access/refresh tokens
- `META_ENCRYPTION_KEY` - Encrypts Meta WhatsApp Business API tokens
- `API_KEY_ENCRYPTION_KEY` - Encrypts API keys for third-party services

**Generate encryption keys:**

```bash
# Generate all required keys at once
python -c "from cryptography.fernet import Fernet; print('# Add these to your .env file:'); print('OAUTH_ENCRYPTION_KEY=' + Fernet.generate_key().decode()); print('META_ENCRYPTION_KEY=' + Fernet.generate_key().decode()); print('API_KEY_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

**IMPORTANT:**
- Use **different keys** for each credential type in production
- Store keys securely (environment variables, secrets manager)
- Never commit encryption keys to version control
- Rotate keys periodically using a key rotation strategy
- Back up keys securely - lost keys mean lost credentials

**Production deployment:**
- Use AWS Secrets Manager, HashiCorp Vault, or similar
- Set keys as environment variables in your deployment platform
- Ensure keys are at least 32 bytes (Fernet requirement)

### Meta Webhook Configuration

**Generate webhook verify token:**

```bash
python -c "import secrets; print('META_WEBHOOK_VERIFY_TOKEN=' + secrets.token_urlsafe(32))"
```

**Configure in Meta App Dashboard:**
1. Go to Meta App Dashboard > Webhooks
2. Set Callback URL: `https://your-domain.com/api/v1/webhooks/meta/`
3. Set Verify Token: Use the generated `META_WEBHOOK_VERIFY_TOKEN`
4. Subscribe to webhook events: `messages`, `message_status`

### Redis Configuration

**Development:**
```bash
# Install Redis
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis
redis-server

# Enable Redis in .env
USE_REDIS=True
```

**Production (AWS ElastiCache):**
```env
USE_REDIS=True
REDIS_HOST=your-elasticache-endpoint.cache.amazonaws.com
REDIS_USE_SSL=True
REDIS_PASSWORD=your_redis_password
```

---

## 🔐 Safety First

- Full audit logs
- Permission-based actions
- Kill-switch for all automations
- No financial or legal actions without explicit approval

---

## 📚 Documentation

### Integration Engine

- **[API Documentation](docs/integration-engine-api.md)** - Complete API reference with request/response examples
- **[Developer Guide](docs/integration-engine-developer-guide.md)** - How to add new authentication strategies and integration types
- **[Deployment Guide](docs/integration-engine-deployment.md)** - Production deployment, environment setup, and scaling
- **[Troubleshooting Guide](docs/integration-engine-troubleshooting.md)** - Common issues and solutions

### Additional Resources

- **[Redis Setup Guide](docs/redis-setup.md)** - Redis installation and configuration
- **[Celery Beat Setup](docs/celery-beat-setup.md)** - Scheduled task configuration
- **[Monitoring Setup](docs/monitoring-setup.md)** - Prometheus and Grafana configuration
- **[User Guide](docs/user-guide.md)** - End-user documentation

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps.automation

# Run specific test file
pytest apps/automation/tests/test_auth_strategies.py

# Run integration tests
pytest apps/automation/tests/test_installation_flows.py
```

### Test Coverage

The integration engine maintains **85%+ code coverage** with comprehensive unit, integration, and property-based tests.

**Test Categories:**
- Unit tests for authentication strategies
- Integration tests for complete installation flows
- Property-based tests for encryption and validation
- End-to-end tests for message processing pipeline

---

## 🔧 Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the engineering rules in `.kiro/steering/`:
- Business logic in services, not views
- Type hints for all function signatures
- Max 300 lines per file
- Comprehensive tests for new code

### 3. Run Tests

```bash
pytest
python manage.py check
```

### 4. Create Pull Request

Ensure all tests pass and code coverage meets requirements.

---

NeuroTwin is not an assistant.  
It is **your second brain.**
