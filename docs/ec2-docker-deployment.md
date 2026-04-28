# EC2 Docker Deployment Guide

This guide covers deploying the NeuroTwin backend on an AWS EC2 instance using Docker Compose, and outlines how to scale the architecture as traffic grows.

---

## Prerequisites

- An AWS account with access to EC2, RDS, and (optionally) ElastiCache
- An RDS PostgreSQL instance already provisioned and accessible from your VPC
- A domain name (optional but recommended for HTTPS)
- Your `.env` file with production values ready

---

## Part 1: Single EC2 Instance Deployment

This is the starting point — one EC2 instance running the full Docker Compose stack.

### 1.1 Launch an EC2 Instance

- **AMI**: Ubuntu 24.04 LTS (`ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*`)
- **Instance type**: `t3.small` (2 vCPU, 2 GB RAM) — sufficient for early-stage traffic running web + worker + beat + Redis. Upgrade to `t3.medium` (4 GB RAM) when you need more headroom for concurrent LLM tasks.
- **Storage**: 30 GB gp3 EBS minimum
- **Estimated cost**: ~$17.50/mo on-demand (t3.small + 30 GB gp3). A 1-year reserved instance drops this to ~$13/mo.
- **Security group inbound rules**:
  - SSH (port 22) from your IP
  - HTTP (port 80) from anywhere (or your load balancer SG later)
  - HTTPS (port 443) from anywhere
  - Port 8000 from anywhere (temporary, until you add a reverse proxy)
- Ensure the instance is in the same VPC/subnet as your RDS instance

### 1.2 Install Docker on the Instance

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker and Docker Compose
sudo apt-get install -y docker.io docker-compose-v2

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker

# Add your user to the docker group (avoids needing sudo for docker commands)
sudo usermod -aG docker ubuntu

# Log out and back in for group changes to take effect
exit
```

### 1.3 Deploy the Application

```bash
# Clone your repo (or use a deploy key / CI pipeline)
git clone https://github.com/your-org/neurotwin.git
cd neurotwin

# Create your production .env
cp .env.example .env
nano .env
```

Edit `.env` with production values:

```dotenv
# CRITICAL — change these for production
DJANGO_SECRET_KEY=<generate-a-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-ec2-public-ip

# Point to your RDS instance
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
DB_NAME=neurotwin
DB_USER=neurotwin_app
DB_PASSWORD=<your-rds-password>

# Redis runs locally in Docker for now
USE_REDIS=True
REDIS_HOST=redis
REDIS_PORT=6379

# Gunicorn tuning (for t3.small with 2 GB RAM, keep workers low)
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=120
CELERY_CONCURRENCY=2

# Generate encryption keys — one per type
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_ENCRYPTION_KEY=<generated-key>
META_ENCRYPTION_KEY=<generated-key>
API_KEY_ENCRYPTION_KEY=<generated-key>
ENCRYPTION_KEY=<generated-key>

# Frontend URL (wherever your Next.js app is hosted)
FRONTEND_URL=https://app.your-domain.com
```

### 1.4 Build and Start

```bash
# Build the images
docker compose build

# Start everything in detached mode
docker compose up -d

# Verify all services are healthy
docker compose ps

# Check logs
docker compose logs -f web
docker compose logs -f celery_worker
```

You should see:
- `redis` — healthy
- `web` — healthy (entrypoint runs migrations + collectstatic, then Gunicorn starts)
- `celery_worker` — healthy
- `celery_beat` — healthy

### 1.5 Add Nginx as a Reverse Proxy

Don't expose Gunicorn directly to the internet. Install Nginx on the host (outside Docker) to handle TLS termination and proxy to port 8000.

```bash
sudo apt-get install -y nginx
```

Create `/etc/nginx/conf.d/neurotwin.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS (after setting up Certbot)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /static/ {
        # Serve static files directly from the named volume
        # Mount the Docker volume to a host path, or use Django Whitenoise
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Set up TLS with Certbot:
```bash
sudo dnf install -y certbot python3-certbot-nginx   # Amazon Linux
# or
sudo apt install -y certbot python3-certbot-nginx    # Ubuntu

sudo certbot --nginx -d your-domain.com
```

After this, remove port 8000 from your security group — only Nginx (80/443) should be publicly accessible.

### 1.6 Production Django Settings Checklist

Make sure these are set in your `.env` for production:

| Variable | Production Value |
|---|---|
| `DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Strong random string (50+ chars) |
| `ALLOWED_HOSTS` | Your domain + EC2 IP |
| `DB_HOST` | RDS endpoint |
| `USE_REDIS` | `True` |
| `REDIS_HOST` | `redis` (Docker service name) |

### 1.7 Useful Operational Commands

```bash
# View real-time logs
docker compose logs -f

# Restart a single service
docker compose restart web

# Run a Django management command
docker compose exec web python manage.py createsuperuser

# Check Celery worker status
docker compose exec celery_worker celery -A neurotwin inspect active

# Scale workers (temporary, within single instance)
docker compose up -d --scale celery_worker=2

# Full restart
docker compose down && docker compose up -d

# Update deployment (after git pull)
docker compose build && docker compose up -d
```

---

## Part 2: Scaling Beyond a Single Instance

When a single EC2 instance isn't enough, here's the progression path. Each step is independent — adopt them as needed.

### 2.1 Move Redis to ElastiCache

The first bottleneck you'll hit when scaling to multiple instances is that each instance runs its own Redis. Workers on different instances won't share the same broker or cache.

**What to do:**
1. Create an ElastiCache Redis cluster (or Serverless) in the same VPC
2. Update `.env`:
   ```dotenv
   REDIS_HOST=your-cluster.cache.amazonaws.com
   REDIS_PORT=6379
   REDIS_USE_SSL=True
   REDIS_PASSWORD=your-auth-token
   ```
3. Remove the `redis` service from `docker-compose.yml`
4. Remove the `depends_on: redis` entries from web, celery_worker, and celery_beat
5. Remove the `redis_data` volume

Now all instances share the same Redis for caching, Celery broker, and result backend.

### 2.2 Push Images to ECR

Instead of building on each EC2 instance, push to Amazon ECR:

```bash
# Create an ECR repository
aws ecr create-repository --repository-name neurotwin-backend

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Build, tag, and push
docker build -t neurotwin-backend .
docker tag neurotwin-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
```

Then on each EC2 instance, pull instead of building:
```bash
docker pull 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
```

Update `docker-compose.yml` to use `image:` instead of `build:` for the web/worker/beat services.

### 2.3 Add an Application Load Balancer (ALB)

When you have multiple EC2 instances running the `web` service:

1. Create an ALB in your VPC
2. Create a target group pointing to port 8000 on your EC2 instances
3. Configure health check path: `/api/v1/health/`
4. Add HTTPS listener (443) with your ACM certificate
5. Add HTTP listener (80) that redirects to HTTPS
6. Point your domain's DNS (Route 53 or external) to the ALB

With an ALB in place, you can remove Nginx from individual instances — the ALB handles TLS termination and load distribution.

**Security group changes:**
- ALB SG: allow inbound 80/443 from anywhere
- EC2 SG: allow inbound 8000 only from the ALB security group

### 2.4 Separate Web and Worker Instances

At this point, split your workload:

**Web instances** (behind ALB):
- Run only the `web` service (Gunicorn)
- Horizontally scalable — add more instances as request volume grows
- `docker-compose.yml` with only the `web` service

**Worker instance(s)**:
- Run `celery_worker` and `celery_beat`
- Beat should only run on ONE instance (it's a scheduler, not a worker)
- Workers can scale horizontally — run multiple worker containers or instances
- `docker-compose.yml` with only celery_worker and celery_beat services

Example `docker-compose.web.yml`:
```yaml
services:
  web:
    image: 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - REDIS_HOST=your-cluster.cache.amazonaws.com
      - USE_REDIS=True
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

Example `docker-compose.worker.yml`:
```yaml
services:
  celery_worker:
    image: 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
    command: celery -A neurotwin worker -l info -Q default,high_priority,incoming_messages,outgoing_messages --concurrency 4
    env_file: .env
    environment:
      - REDIS_HOST=your-cluster.cache.amazonaws.com
      - USE_REDIS=True
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  celery_beat:
    image: 123456789.dkr.ecr.us-east-1.amazonaws.com/neurotwin-backend:latest
    command: celery -A neurotwin beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --pidfile /tmp/celerybeat.pid
    env_file: .env
    environment:
      - REDIS_HOST=your-cluster.cache.amazonaws.com
      - USE_REDIS=True
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### 2.5 Auto Scaling Group (ASG)

For automatic horizontal scaling of web instances:

1. Create a launch template from your configured EC2 instance (or use user data to pull from ECR and start Docker Compose on boot)
2. Create an ASG with:
   - Min: 1, Desired: 2, Max: 6 (adjust to your needs)
   - Target tracking scaling policy: average CPU > 60% → scale out
   - Attach the ALB target group
3. The ASG will automatically add/remove web instances based on load

**User data script** for the launch template:
```bash
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

# Install Docker Compose
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Pull and start
cd /opt/neurotwin
docker compose -f docker-compose.web.yml pull
docker compose -f docker-compose.web.yml up -d
```

### 2.6 Migrations Strategy for Multi-Instance

When multiple instances run the entrypoint (which runs `migrate`), you need to avoid race conditions:

**Option A — Run migrations as a one-off task before deployment:**
```bash
# Run migrations from one instance before updating the others
docker compose run --rm web python manage.py migrate --noinput
```

**Option B — Use a deploy container:**
Add a one-shot `migrate` service to your compose file that runs migrations and exits. Other services depend on it.

**Option C — Use a CI/CD pipeline step:**
Run migrations as a pipeline step (e.g., in GitHub Actions) before deploying new images to EC2/ASG.

For the single-instance setup, the entrypoint handles this automatically. Only worry about this when you scale to multiple web instances.

---

## Part 3: Future Architecture (ECS / Fargate)

When you outgrow Docker Compose on EC2, the natural next step is ECS (Elastic Container Service) with Fargate — no servers to manage at all.

### What changes:
- Push images to ECR (same as 2.2)
- Define ECS task definitions for web, worker, and beat
- Use ECS services with desired count and auto-scaling
- ALB integrates natively with ECS services
- Secrets managed via AWS Secrets Manager instead of `.env` files
- Logs go to CloudWatch automatically

### What stays the same:
- The Dockerfile doesn't change
- The entrypoint script doesn't change
- RDS and ElastiCache connections stay the same
- Environment variables are the same, just sourced from Secrets Manager

This is a bigger migration but the Docker image you've built is already ECS-compatible.

---

## Architecture Progression Summary

| Stage | Web | Workers | Redis | DB | Load Balancer |
|---|---|---|---|---|---|
| **1. Single EC2** | Docker Compose | Docker Compose | Docker (local) | RDS | Nginx on host |
| **2. Multi-EC2** | Multiple instances | Separate instance(s) | ElastiCache | RDS | ALB |
| **3. ECS/Fargate** | ECS Service (auto-scaled) | ECS Service | ElastiCache | RDS | ALB |

Each stage reuses the same Docker image and `.env` configuration pattern. The progression is incremental — you don't need to redesign anything, just move services to managed infrastructure as you grow.
