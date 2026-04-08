# Security Features

This document describes the security features implemented in the automation system.

## Overview

The automation system implements comprehensive security measures to protect user data and prevent attacks:

- **CSRF Protection**: All state-changing endpoints are protected against CSRF attacks
- **Input Sanitization**: All user input is sanitized to prevent XSS and injection attacks
- **Rate Limiting**: Authentication endpoints are rate-limited to prevent brute force attacks
- **Security Event Logging**: All security-relevant events are logged for audit

## Requirements

These features satisfy the following requirements:
- **Requirement 33.1**: Webhook signature validation
- **Requirement 33.2**: HTTPS for all external API calls
- **Requirement 33.3**: Input sanitization before storage and display
- **Requirement 33.4**: CSRF protection for state-changing endpoints
- **Requirement 33.5**: Rate limiting on authentication endpoints
- **Requirement 33.6**: Security event logging for audit

## Components

### 1. Input Sanitization (`security.py`)

The `InputSanitizer` class provides methods to sanitize user input:

```python
from apps.automation.security import InputSanitizer

# Sanitize a string
clean_text = InputSanitizer.sanitize_string(user_input)

# Sanitize a dictionary
clean_data = InputSanitizer.sanitize_dict(request_data)

# Sanitize a list
clean_list = InputSanitizer.sanitize_list(items)
```

**Features:**
- Removes dangerous HTML elements (script, iframe, object, embed)
- Removes JavaScript event handlers
- Strips HTML tags (optional)
- Escapes HTML entities
- Validates against SQL injection patterns

### 2. Security Event Logging (`security.py`)

The `SecurityEventLogger` class logs all security-relevant events:

```python
from apps.automation.security import SecurityEventLogger

# Log authentication attempt
SecurityEventLogger.log_authentication_attempt(
    user_id=user_id,
    username=email,
    success=True,
    ip_address=get_client_ip(request),
    user_agent=get_user_agent(request)
)

# Log webhook signature failure
SecurityEventLogger.log_webhook_signature_failure(
    integration_type='meta',
    integration_id=integration_id,
    ip_address=get_client_ip(request),
    payload_hash=hash_value
)

# Log rate limit violation
SecurityEventLogger.log_rate_limit_violation(
    user_id=user_id,
    integration_id=integration_id,
    limit_type='authentication',
    attempted_rate=20,
    limit=10,
    ip_address=get_client_ip(request)
)

# Log integration deletion
SecurityEventLogger.log_integration_deletion(
    user_id=user_id,
    integration_id=integration_id,
    integration_type='whatsapp',
    revocation_success=True,
    ip_address=get_client_ip(request)
)
```

**Logged Events:**
- Authentication attempts (success and failure)
- Webhook signature verification failures
- Rate limit violations
- Integration deletions
- CSRF validation failures
- Permission denied events

### 3. Rate Limiting (`throttling.py`)

Custom throttling classes for different endpoint types:

```python
from apps.automation.throttling import (
    AuthenticationThrottle,
    InstallationThrottle,
    MetaInstallationThrottle
)

class LoginView(BaseAPIView):
    throttle_classes = [AuthenticationThrottle]  # 20 attempts per minute
```

**Throttle Classes:**
- `AuthenticationThrottle`: 20 attempts per minute for auth endpoints
- `InstallationThrottle`: 10 installations per hour per user
- `MetaInstallationThrottle`: 5 Meta installations per minute globally
- `APIThrottle`: 1000 requests per hour for general API
- `APIBurstThrottle`: 100 requests per minute for burst protection

### 4. Security Middleware (`middleware/security_middleware.py`)

Three middleware classes provide security features:

#### InputSanitizationMiddleware

Automatically sanitizes all POST, PUT, PATCH request data:

```python
MIDDLEWARE = [
    # ...
    'apps.automation.middleware.security_middleware.InputSanitizationMiddleware',
]
```

**Features:**
- Sanitizes JSON request bodies
- Sanitizes POST data
- Excludes webhook endpoints (need raw data)

#### CSRFLoggingMiddleware

Extends Django's CSRF middleware with logging:

```python
MIDDLEWARE = [
    # ...
    'apps.automation.middleware.security_middleware.CSRFLoggingMiddleware',
]
```

**Features:**
- Validates CSRF tokens on state-changing requests
- Logs all CSRF validation failures
- Respects `@csrf_exempt` decorator

#### SecurityHeadersMiddleware

Adds security headers to all responses:

```python
MIDDLEWARE = [
    # ...
    'apps.automation.middleware.security_middleware.SecurityHeadersMiddleware',
]
```

**Headers Added:**
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` - Enables XSS protection
- `Strict-Transport-Security` - Enforces HTTPS
- `Content-Security-Policy` - Restricts resource loading
- `Referrer-Policy` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

## Configuration

### Django Settings

Add the middleware to `MIDDLEWARE` in `settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.automation.middleware.security_middleware.CSRFLoggingMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.automation.middleware.security_middleware.InputSanitizationMiddleware',
    'apps.automation.middleware.security_middleware.SecurityHeadersMiddleware',
    # ... other middleware
]
```

### Logging Configuration

Security events are logged to `logs/security_events.json.log`:

```python
LOGGING = {
    'handlers': {
        'security_events': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security_events.json.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 90,  # 90-day retention
            'formatter': 'json',
        },
    },
    'loggers': {
        'automation.security': {
            'handlers': ['console', 'security_events'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Rate Limiting Configuration

Configure rate limits in `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'auth': '20/minute',  # Authentication endpoints
        'installation': '10/hour',  # Installation endpoints
        'meta_installation': '5/minute',  # Meta installations (global)
        'api': '1000/hour',  # General API
        'api_burst': '100/minute',  # Burst protection
    },
}
```

## Usage Examples

### Protecting a View with Rate Limiting

```python
from rest_framework.permissions import AllowAny
from apps.automation.throttling import AuthenticationThrottle

class LoginView(BaseAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthenticationThrottle]
    
    def post(self, request):
        # Login logic here
        pass
```

### Logging Security Events

```python
from apps.automation.security import SecurityEventLogger, get_client_ip

# In your view
SecurityEventLogger.log_authentication_attempt(
    user_id=str(user.id) if success else None,
    username=email,
    success=success,
    ip_address=get_client_ip(request),
    user_agent=request.META.get('HTTP_USER_AGENT', 'unknown'),
    failure_reason=error_message if not success else None
)
```

### Sanitizing User Input

```python
from apps.automation.security import InputSanitizer

# Sanitize before saving to database
clean_data = InputSanitizer.sanitize_dict(request.data)
model.field = clean_data['field']
model.save()
```

## Security Best Practices

1. **Always use HTTPS in production** - Set `SECURE_SSL_REDIRECT = True`
2. **Keep encryption keys secure** - Store in environment variables, never in code
3. **Monitor security logs** - Regularly review `security_events.json.log`
4. **Update rate limits** - Adjust based on actual usage patterns
5. **Test CSRF protection** - Ensure all state-changing endpoints require CSRF tokens
6. **Validate webhook signatures** - Always verify signatures before processing
7. **Use strong passwords** - Enforce password complexity requirements
8. **Enable 2FA** - Implement two-factor authentication for sensitive operations

## Monitoring and Alerts

### Security Event Monitoring

Monitor the following metrics:
- Authentication failure rate (alert if > 10% of attempts)
- Rate limit violations (alert if > 100/hour)
- Webhook signature failures (alert on any occurrence)
- CSRF validation failures (alert on any occurrence)

### Log Analysis

Use log aggregation tools to analyze security events:

```bash
# Count authentication failures by IP
cat logs/security_events.json.log | jq 'select(.event_type=="authentication_attempt" and .success==false) | .ip_address' | sort | uniq -c | sort -rn

# Count rate limit violations by user
cat logs/security_events.json.log | jq 'select(.event_type=="rate_limit_violation") | .user_id' | sort | uniq -c | sort -rn

# Find webhook signature failures
cat logs/security_events.json.log | jq 'select(.event_type=="webhook_signature_failure")'
```

## Testing

### Testing CSRF Protection

```python
from django.test import TestCase, Client

class CSRFProtectionTest(TestCase):
    def test_post_without_csrf_fails(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post('/api/v1/integrations/', {})
        self.assertEqual(response.status_code, 403)
    
    def test_post_with_csrf_succeeds(self):
        client = Client(enforce_csrf_checks=True)
        # Get CSRF token
        response = client.get('/api/v1/csrf/')
        csrf_token = response.cookies['csrftoken'].value
        
        # Make POST with CSRF token
        response = client.post(
            '/api/v1/integrations/',
            {},
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertNotEqual(response.status_code, 403)
```

### Testing Rate Limiting

```python
from django.test import TestCase
from rest_framework.test import APIClient

class RateLimitingTest(TestCase):
    def test_authentication_rate_limit(self):
        client = APIClient()
        
        # Make 21 requests (limit is 20/minute)
        for i in range(21):
            response = client.post('/api/v1/auth/login/', {
                'email': 'test@example.com',
                'password': 'wrong'
            })
        
        # Last request should be rate limited
        self.assertEqual(response.status_code, 429)
```

### Testing Input Sanitization

```python
from apps.automation.security import InputSanitizer

class InputSanitizationTest(TestCase):
    def test_removes_script_tags(self):
        dirty = '<script>alert("xss")</script>Hello'
        clean = InputSanitizer.sanitize_string(dirty)
        self.assertNotIn('<script>', clean)
        self.assertIn('Hello', clean)
    
    def test_removes_event_handlers(self):
        dirty = '<div onclick="alert()">Click</div>'
        clean = InputSanitizer.sanitize_string(dirty)
        self.assertNotIn('onclick', clean)
```

## Troubleshooting

### CSRF Token Issues

**Problem**: Getting 403 CSRF verification failed

**Solution**:
1. Ensure frontend sends CSRF token in `X-CSRFToken` header
2. Check that `CSRF_COOKIE_HTTPONLY = False` for JavaScript access
3. Verify `CSRF_TRUSTED_ORIGINS` includes your frontend domain

### Rate Limiting Issues

**Problem**: Legitimate users getting rate limited

**Solution**:
1. Increase rate limits in `settings.py`
2. Use user-based throttling instead of IP-based
3. Implement exponential backoff on frontend

### Input Sanitization Issues

**Problem**: Valid HTML being stripped

**Solution**:
1. Use `strip_html=False` for fields that allow HTML
2. Whitelist specific HTML tags if needed
3. Exclude specific endpoints from sanitization middleware

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
- [CSRF Protection](https://docs.djangoproject.com/en/stable/ref/csrf/)
