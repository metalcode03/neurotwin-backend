# Requirements Document

## Introduction

This document defines the requirements for containerizing the NeuroTwin Django backend using Docker. The setup targets deployment on AWS EC2 instances with an external AWS RDS PostgreSQL database. Redis runs locally within Docker for caching and Celery broker/result backend. The configuration must produce a working deployment on first run, be production-ready, and support future scalability without over-engineering the initial setup.

## Glossary

- **Backend_Container**: The Docker container running the Django application served via Gunicorn WSGI server
- **Celery_Worker**: The Docker container running Celery worker processes that consume tasks from Redis queues
- **Celery_Beat**: The Docker container running the Celery Beat scheduler using Django database scheduler
- **Redis_Service**: The Docker container running Redis 7+ for caching (DB 0), Celery broker (DB 1), and result backend (DB 2)
- **Entrypoint_Script**: A shell script executed at container startup that runs migrations, collects static files, and starts the application process
- **Docker_Compose**: The orchestration file defining all services, networks, volumes, and health checks
- **Dockerfile**: The multi-stage build file that produces the production-ready backend image using uv package manager
- **Health_Check**: A periodic probe that verifies a service is operational and responsive

## Requirements

### Requirement 1: Multi-Stage Dockerfile with uv Package Manager

**User Story:** As a developer, I want a multi-stage Dockerfile that uses uv for dependency installation, so that the final image is minimal, secure, and builds quickly with cached layers.

#### Acceptance Criteria

1. THE Dockerfile SHALL use a multi-stage build with a builder stage for dependency installation and a final runtime stage
2. WHEN building the image, THE Dockerfile SHALL use `uv` to install Python dependencies from `pyproject.toml` and `uv.lock`
3. THE Dockerfile SHALL target Python 3.13 as the base runtime
4. THE Dockerfile SHALL separate dependency installation from application code copying to maximize Docker layer caching
5. THE Dockerfile SHALL create a non-root user for running the application process
6. THE Dockerfile SHALL set `DJANGO_SETTINGS_MODULE` environment variable to `neurotwin.settings`
7. THE Dockerfile SHALL expose port 8000 for the Gunicorn WSGI server
8. THE Dockerfile SHALL include a `logs/` directory with appropriate write permissions for the application user

### Requirement 2: Gunicorn WSGI Server Configuration

**User Story:** As a developer, I want the Django application served via Gunicorn with sensible production defaults, so that the backend handles concurrent requests reliably.

#### Acceptance Criteria

1. THE Backend_Container SHALL serve the Django application using Gunicorn bound to `0.0.0.0:8000`
2. THE Backend_Container SHALL configure Gunicorn with a configurable number of workers via environment variable with a sensible default
3. THE Backend_Container SHALL use the WSGI application at `neurotwin.wsgi.application`
4. WHEN the `gunicorn` package is not present in dependencies, THE Dockerfile SHALL ensure `gunicorn` is added as a project dependency
5. THE Backend_Container SHALL configure Gunicorn with a request timeout to prevent hung workers
6. THE Backend_Container SHALL log Gunicorn access and error output to stdout/stderr for Docker log collection

### Requirement 3: Docker Compose Service Orchestration

**User Story:** As a developer, I want a Docker Compose file that orchestrates all backend services with proper dependency ordering, so that a single `docker compose up` starts the entire stack correctly.

#### Acceptance Criteria

1. THE Docker_Compose SHALL define four services: `web` (Django/Gunicorn), `celery_worker`, `celery_beat`, and `redis`
2. THE Docker_Compose SHALL configure the `web` service to depend on `redis` with a health check condition
3. THE Docker_Compose SHALL configure `celery_worker` and `celery_beat` to depend on both `redis` and `web` with health check conditions
4. THE Docker_Compose SHALL use a shared `.env` file for environment variable injection across all services
5. THE Docker_Compose SHALL define a named volume for Redis data persistence
6. THE Docker_Compose SHALL define a named volume or bind mount for static files collected by Django
7. THE Docker_Compose SHALL define a bind mount for the `logs/` directory so logs persist on the host
8. THE Docker_Compose SHALL place all services on a shared bridge network named `neurotwin`
9. THE Docker_Compose SHALL map port 8000 on the host to port 8000 on the `web` container

### Requirement 4: Entrypoint Script for Container Initialization

**User Story:** As a developer, I want an entrypoint script that handles database migrations and static file collection before starting the main process, so that the application is ready to serve requests immediately after container startup.

#### Acceptance Criteria

1. WHEN the Backend_Container starts, THE Entrypoint_Script SHALL wait for the database to be reachable before proceeding
2. WHEN the database is reachable, THE Entrypoint_Script SHALL run Django database migrations
3. WHEN migrations complete, THE Entrypoint_Script SHALL run `collectstatic --noinput` to gather static files
4. IF a migration or collectstatic command fails, THEN THE Entrypoint_Script SHALL exit with a non-zero status code
5. WHEN initialization completes successfully, THE Entrypoint_Script SHALL execute the command passed as arguments (Gunicorn, Celery worker, or Celery beat)
6. THE Entrypoint_Script SHALL print timestamped log messages for each initialization step

### Requirement 5: Redis Service Configuration

**User Story:** As a developer, I want Redis running in Docker with persistence and memory limits, so that caching and Celery message brokering work reliably in local and deployed environments.

#### Acceptance Criteria

1. THE Redis_Service SHALL use the `redis:7-alpine` image
2. THE Redis_Service SHALL enable append-only file (AOF) persistence
3. THE Redis_Service SHALL set a maximum memory limit of 256MB with `allkeys-lru` eviction policy
4. THE Redis_Service SHALL expose port 6379 to the host for local development tooling access
5. THE Redis_Service SHALL include a health check using `redis-cli ping` with a 10-second interval
6. THE Redis_Service SHALL store data in a named Docker volume for persistence across container restarts

### Requirement 6: Health Checks for All Services

**User Story:** As a developer, I want health checks on all containers, so that Docker Compose can manage service dependencies and restart unhealthy containers automatically.

#### Acceptance Criteria

1. THE Backend_Container SHALL include a health check that probes the `/api/v1/health/` endpoint via HTTP
2. THE Redis_Service SHALL include a health check using `redis-cli ping`
3. THE Celery_Worker SHALL include a health check using `celery inspect ping`
4. THE Celery_Beat SHALL include a health check that verifies the beat process is running
5. WHEN a health check fails beyond the configured retry count, THE Docker_Compose SHALL restart the failed service

### Requirement 7: Environment Configuration for Docker Deployment

**User Story:** As a developer, I want environment variables properly configured for Docker networking, so that services can communicate with each other and with external AWS RDS without manual intervention.

#### Acceptance Criteria

1. THE Docker_Compose SHALL set `REDIS_HOST` to the Redis service name (`redis`) for inter-container communication
2. THE Docker_Compose SHALL allow `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` to be configured via the `.env` file for AWS RDS connectivity
3. THE Docker_Compose SHALL set `USE_REDIS=True` for all services that require Redis access
4. THE Docker_Compose SHALL pass all required environment variables from `.env` to each service
5. WHEN `ALLOWED_HOSTS` is not set in the environment, THE Backend_Container SHALL default to allowing the EC2 instance hostname and `localhost`

### Requirement 8: Static Files Configuration

**User Story:** As a developer, I want Django static files properly collected and served, so that the admin interface and API documentation render correctly in the containerized environment.

#### Acceptance Criteria

1. THE Backend_Container SHALL configure `STATIC_ROOT` to a directory within the container for collected static files
2. WHEN the Entrypoint_Script runs `collectstatic`, THE Backend_Container SHALL write static files to the configured `STATIC_ROOT` path
3. THE Docker_Compose SHALL persist the static files directory via a named volume shared between container restarts

### Requirement 9: Celery Worker and Beat Configuration

**User Story:** As a developer, I want Celery worker and beat services properly configured in Docker, so that background task processing and scheduled tasks run reliably alongside the web server.

#### Acceptance Criteria

1. THE Celery_Worker SHALL start with the command `celery -A neurotwin worker -l info -Q default,high_priority,incoming_messages,outgoing_messages`
2. THE Celery_Beat SHALL start with the command `celery -A neurotwin beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
3. THE Celery_Worker SHALL use the same Docker image as the Backend_Container
4. THE Celery_Beat SHALL use the same Docker image as the Backend_Container
5. WHILE the Redis_Service is unavailable, THE Celery_Worker SHALL retry connecting to the broker using Celery's built-in retry mechanism
6. THE Celery_Worker SHALL configure a concurrency level via environment variable with a sensible default

### Requirement 10: Production Readiness and Restart Policies

**User Story:** As a developer, I want all services configured with restart policies and resource awareness, so that the deployment recovers from transient failures without manual intervention.

#### Acceptance Criteria

1. THE Docker_Compose SHALL configure all services with `restart: unless-stopped` policy
2. THE Docker_Compose SHALL configure the `web` service with a graceful shutdown timeout
3. THE Backend_Container SHALL handle SIGTERM gracefully by allowing in-flight requests to complete
4. THE Celery_Worker SHALL handle SIGTERM gracefully by completing in-progress tasks before shutting down
