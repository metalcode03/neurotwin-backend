# Integration Engine - Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when working with the Scalable Integration Engine, including authentication failures, webhook debugging, rate limiting, token refresh issues, and Celery worker problems.

## Table of Contents

- [Authentication Issues](#authentication-issues)
- [Webhook Debugging](#webhook-debugging)
- [Rate Limiting Issues](#rate-limiting-issues)
- [Token Refresh Failures](#token-refresh-failures)
- [Celery Worker Issues](#celery-worker-issues)
- [Database Issues](#database-issues)
- [Redis Connection Issues](#redis-connection-issues)
- [Message Delivery Failures](#message-delivery-failures)

---

## Authentication Issues

### OAuth Authorization Fails

**Symptom**: User redirected back with error after OAuth authorization

**Common Causes**:

1. **Invalid redirect_uri**
   ```
   Error: redirect_uri_mismatch
   ```
   
   **Solution**: Ensure redirect_uri in OAuth config matches exactly what's registered with provider
   
   ```python
   # Check integration type auth_config
   integration_type = IntegrationTypeModel.objects.get(type='gmail')
   print(integration_type.auth_config['redirect_uri'])
   
   # Should match: https://app.neurotwin.com/api/v1/integrations/oauth/callback/
   ```

2. **Invalid client credentials**
   ```
   Error: invalid_client
   ```
   
   **Solution**: Verify client_id and client_secret are correct
   
   ```python
   # Test decryption
   from apps.automation.utils.encryption import TokenEncryption
   encrypted = integration_type.auth_config['client_secret_encrypted']
   decrypted = TokenEncryption.decrypt(
       base64.b64decode(encrypted),
       auth_type='oauth'
   )
   print(f"Decrypted secret: {decrypted}")
   ```

3. **Expired or invalid state**
   ```
   Error: OAUTH_CALLBACK_INVALID_STATE
   ```
   
   **Solution**: State expires after 15 minutes. User must complete OAuth flow within this time.
   
   ```python
   # Check state in Redis
   from apps.automation.utils.oauth_state import get_oauth_state
   state_data = get_oauth_state('state_token_here')
   print(state_data)  # None if expired
   ```

### Meta Authentication Fails

**Symptom**: Meta callback returns error

**Common Causes**:

1. **Business account not found**
   ```
   Error: META_BUSINESS_FETCH_FAILED
   ```
   
   **Solution**: Ensure user has Meta Business account with WhatsApp Business API access
   
   - User must complete Meta Business verification
   - User must have admin access to WABA
   - Check Meta Business Manager settings

2. **Invalid app secret**
   ```
   Error: Invalid signature
   ```
   
   **Solution**: Verify META_APP_SECRET matches Meta app dashboard
   
   ```bash
   # Check environment variable
   echo $META_APP_SECRET
   
   # Should match Meta App Dashboard → Settings → Basic → App Secret
   ```

3. **Missing permissions**
   ```
   Error: Insufficient permissions
   ```
   
   **Solution**: Ensure Meta app has required permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`
   - `business_management`

### API Key Validation Fails

**Symptom**: API key completion returns invalid error

**Common Causes**:

1. **API endpoint unreachable**
   ```
   Error: API_KEY_INVALID
   ```
   
   **Solution**: Test API endpoint manually
   
   ```bash
   curl -H "X-API-Key: your_key_here" https://api.example.com/validate
   ```

2. **Wrong header name**
   ```
   Error: 401 Unauthorized
   ```
   
   **Solution**: Verify authentication_header_name in auth_config
   
   ```python
   # Check header name
   integration_type = IntegrationTypeModel.objects.get(type='custom-api')
   print(integration_type.auth_config['authentication_header_name'])
   # Should be: X-API-Key, Authorization, etc.
   ```

---

## Webhook Debugging

### Webhooks Not Received

**Symptom**: No webhook events in database

**Debugging Steps**:

1. **Check webhook URL is accessible**
   ```bash
   curl -X POST https://api.neurotwin.com/api/v1/webhooks/meta/ \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

2. **Verify webhook is registered with provider**
   
   For Meta:
   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/<APP_ID>/subscriptions" \
     -H "Authorization: Bearer <ACCESS_TOKEN>"
   ```

3. **Check firewall rules**
   - Ensure port 443 is open
   - Whitelist Meta IP ranges if using IP filtering

4. **Check webhook logs**
   ```bash
   # View webhook processing logs
   tail -f /var/log/neurotwin/webhooks.log
   
   # Or query database
   python manage.py shell
   >>> from apps.automation.models import WebhookEvent
   >>> WebhookEvent.objects.filter(status='failed').order_by('-created_at')[:10]
   ```

### Webhook Signature Verification Fails

**Symptom**: Webhooks rejected with signature error

**Common Causes**:

1. **Wrong app secret**
   ```
   Error: WEBHOOK_SIGNATURE_INVALID
   ```
   
   **Solution**: Verify META_APP_SECRET
   
   ```python
   # Test signature verification
   from apps.automation.utils.webhook_verifier import WebhookVerifier
   
   payload = b'{"test": "data"}'
   signature = "sha256=abc123..."
   
   verifier = WebhookVerifier()
   is_valid = verifier.verify_meta_signature(payload, signature)
   print(f"Valid: {is_valid}")
   ```

2. **Payload modification**
   
   **Solution**: Ensure payload is not modified before verification
   - Don't parse JSON before verification
   - Use raw request body
   - Preserve exact byte order

### Webhook Processing Slow

**Symptom**: Webhooks timing out (>5 seconds)

**Debugging Steps**:

1. **Check Celery queue length**
   ```bash
   celery -A neurotwin inspect active_queues
   ```

2. **Check worker status**
   ```bash
   celery -A neurotwin inspect stats
   ```

3. **Monitor task execution time**
   ```python
   # Check average processing time
   from apps.automation.services.task_monitoring import TaskMonitoringService
   
   stats = TaskMonitoringService.get_task_stats(
       task_name='process_incoming_message',
       period='hour'
   )
   print(f"Average duration: {stats['average_duration_ms']}ms")
   ```

**Solutions**:

- Add more Celery workers
- Increase worker concurrency
- Optimize database queries
- Add database indexes

---

## Rate Limiting Issues

### Rate Limit Exceeded

**Symptom**: API returns 429 Too Many Requests

**Common Causes**:

1. **Per-integration limit exceeded**
   ```
   Error: RATE_LIMIT_EXCEEDED
   Message: Rate limit exceeded. Please try again in 30 seconds.
   ```
   
   **Solution**: Check rate limit status
   
   ```python
   from apps.automation.utils.rate_limiter import RateLimiter
   
   limiter = RateLimiter(redis_client)
   status = limiter.get_rate_limit_status(
       integration_id='uuid',
       limit_per_minute=20
   )
   print(f"Current: {status['current']}, Remaining: {status['remaining']}")
   ```

2. **Global rate limit exceeded**
   
   **Solution**: Reduce request rate or increase global limit
   
   ```python
   # Check global rate limit in settings
   # DEFAULT: 100 requests per minute
   
   # Increase if needed
   GLOBAL_RATE_LIMIT_PER_MINUTE = 200
   ```

3. **Meta installation rate limit**
   ```
   Error: High demand for WhatsApp connections. Please try again in 60 seconds.
   ```
   
   **Solution**: Wait and retry. Meta installations limited to 5 per minute globally.

### Rate Limit Not Working

**Symptom**: Requests not being rate limited

**Debugging Steps**:

1. **Check Redis connection**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Check rate limit keys in Redis**
   ```bash
   redis-cli keys "rate_limit:*"
   ```

3. **Test rate limiter directly**
   ```python
   from apps.automation.utils.rate_limiter import RateLimiter
   import redis
   
   redis_client = redis.from_url(settings.REDIS_URL)
   limiter = RateLimiter(redis_client)
   
   # Test rate limit
   for i in range(25):
       allowed, wait = limiter.check_rate_limit(
           integration_id='test',
           limit_per_minute=20
       )
       print(f"Request {i+1}: Allowed={allowed}, Wait={wait}s")
   ```

---

## Token Refresh Failures

### OAuth Token Refresh Fails

**Symptom**: Integration marked as expired or disconnected

**Common Causes**:

1. **No refresh token**
   ```
   Error: No refresh token available
   ```
   
   **Solution**: Some OAuth providers don't issue refresh tokens. User must re-authenticate.
   
   ```python
   # Check if refresh token exists
   integration = Integration.objects.get(id='uuid')
   print(f"Has refresh token: {bool(integration.refresh_token)}")
   ```

2. **Refresh token expired**
   ```
   Error: invalid_grant
   ```
   
   **Solution**: Refresh tokens can expire. User must re-authenticate.
   
   - Google: Refresh tokens expire after 6 months of inactivity
   - Meta: Long-lived tokens expire after 60 days

3. **Invalid client credentials**
   ```
   Error: invalid_client
   ```
   
   **Solution**: Verify client_secret hasn't changed
   
   ```python
   # Update client_secret in integration type
   integration_type.auth_config['client_secret_encrypted'] = new_encrypted_secret
   integration_type.save()
   ```

### Meta Token Refresh Fails

**Symptom**: Meta integration disconnected after 60 days

**Debugging Steps**:

1. **Check token expiry**
   ```python
   integration = Integration.objects.get(id='uuid')
   print(f"Expires at: {integration.token_expires_at}")
   print(f"Days until expiry: {(integration.token_expires_at - timezone.now()).days}")
   ```

2. **Check refresh task is running**
   ```bash
   # Check Celery Beat is running
   ps aux | grep celery
   
   # Check scheduled tasks
   celery -A neurotwin inspect scheduled
   ```

3. **Manually trigger refresh**
   ```python
   from apps.automation.tasks.token_refresh import refresh_expiring_tokens
   
   # Trigger refresh task
   refresh_expiring_tokens.delay()
   ```

### Automatic Refresh Not Working

**Symptom**: Tokens expiring without refresh attempt

**Debugging Steps**:

1. **Check Celery Beat is running**
   ```bash
   systemctl status celery-beat
   ```

2. **Check beat schedule**
   ```python
   # In Django shell
   from django.conf import settings
   print(settings.CELERY_BEAT_SCHEDULE)
   ```

3. **Check task execution logs**
   ```bash
   tail -f /var/log/celery/beat.log
   ```

**Solution**: Ensure Celery Beat is running and scheduled task is configured

```bash
# Start Celery Beat
celery -A neurotwin beat --loglevel=info
```

---

## Celery Worker Issues

### Workers Not Processing Tasks

**Symptom**: Tasks stuck in queue

**Debugging Steps**:

1. **Check workers are running**
   ```bash
   celery -A neurotwin inspect active
   ```

2. **Check worker status**
   ```bash
   celery -A neurotwin inspect stats
   ```

3. **Check queue lengths**
   ```bash
   celery -A neurotwin inspect active_queues
   ```

**Common Causes**:

1. **Workers not started**
   
   **Solution**: Start workers
   ```bash
   celery -A neurotwin worker -Q incoming_messages,outgoing_messages,high_priority --loglevel=info
   ```

2. **Workers crashed**
   
   **Solution**: Check worker logs
   ```bash
   tail -f /var/log/celery/worker.log
   ```
   
   Restart workers:
   ```bash
   systemctl restart celery-worker-incoming
   systemctl restart celery-worker-outgoing
   ```

3. **Redis connection lost**
   
   **Solution**: Check Redis is running
   ```bash
   systemctl status redis
   redis-cli ping
   ```

### Tasks Failing Repeatedly

**Symptom**: Tasks retrying and failing

**Debugging Steps**:

1. **Check task error logs**
   ```python
   from django_celery_results.models import TaskResult
   
   failed_tasks = TaskResult.objects.filter(
       status='FAILURE',
       task_name='send_outgoing_message'
   ).order_by('-date_done')[:10]
   
   for task in failed_tasks:
       print(f"Task: {task.task_id}")
       print(f"Error: {task.result}")
   ```

2. **Check retry count**
   ```python
   from apps.automation.models import Message
   
   messages = Message.objects.filter(
       status='failed',
       retry_count__gte=5
   ).order_by('-created_at')[:10]
   
   for msg in messages:
       print(f"Message: {msg.id}, Retries: {msg.retry_count}")
   ```

**Common Causes**:

1. **Permanent error (401, 403, 400)**
   
   **Solution**: Check integration credentials
   ```python
   integration = Integration.objects.get(id='uuid')
   print(f"Status: {integration.status}")
   print(f"Health: {integration.health_status}")
   ```

2. **External API down**
   
   **Solution**: Check circuit breaker status
   ```python
   from apps.automation.utils.circuit_breaker_registry import CircuitBreakerRegistry
   
   registry = CircuitBreakerRegistry()
   status = registry.get_status('meta_api')
   print(f"Circuit breaker state: {status['state']}")
   ```

3. **Rate limit exceeded**
   
   **Solution**: Tasks will retry automatically when rate limit resets

### Worker Memory Issues

**Symptom**: Workers consuming too much memory

**Debugging Steps**:

1. **Check worker memory usage**
   ```bash
   ps aux | grep celery | awk '{print $2, $4, $11}'
   ```

2. **Check for memory leaks**
   ```bash
   # Monitor memory over time
   watch -n 5 'ps aux | grep celery'
   ```

**Solutions**:

1. **Restart workers periodically**
   ```bash
   # Add to worker config
   --max-tasks-per-child=1000
   ```

2. **Reduce concurrency**
   ```bash
   # Reduce from 4 to 2
   --concurrency=2
   ```

3. **Add more workers instead of increasing concurrency**

---

## Database Issues

### Connection Pool Exhausted

**Symptom**: `OperationalError: FATAL: remaining connection slots are reserved`

**Debugging Steps**:

1. **Check active connections**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

2. **Check max connections**
   ```sql
   SHOW max_connections;
   ```

**Solutions**:

1. **Increase max_connections in PostgreSQL**
   ```sql
   ALTER SYSTEM SET max_connections = 200;
   SELECT pg_reload_conf();
   ```

2. **Use connection pooling (PgBouncer)**
   ```bash
   sudo apt install pgbouncer
   ```

3. **Reduce CONN_MAX_AGE**
   ```python
   # settings.py
   DATABASES['default']['CONN_MAX_AGE'] = 300  # 5 minutes instead of 10
   ```

### Slow Queries

**Symptom**: API responses slow, database CPU high

**Debugging Steps**:

1. **Check slow queries**
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

2. **Check missing indexes**
   ```sql
   SELECT schemaname, tablename, attname, n_distinct, correlation
   FROM pg_stats
   WHERE schemaname = 'public'
   AND tablename IN ('automation_message', 'automation_conversation')
   ORDER BY n_distinct DESC;
   ```

**Solutions**:

1. **Add indexes**
   ```python
   # Create migration
   python manage.py makemigrations --empty automation
   
   # Add index in migration
   operations = [
       migrations.AddIndex(
           model_name='message',
           index=models.Index(fields=['conversation', 'created_at'], name='msg_conv_created_idx'),
       ),
   ]
   ```

2. **Use select_related and prefetch_related**
   ```python
   # Bad (N+1 query)
   messages = Message.objects.all()
   for msg in messages:
       print(msg.conversation.integration.name)
   
   # Good
   messages = Message.objects.select_related(
       'conversation__integration__integration_type'
   ).all()
   ```

---

## Redis Connection Issues

### Redis Connection Refused

**Symptom**: `ConnectionError: Error 111 connecting to localhost:6379. Connection refused.`

**Debugging Steps**:

1. **Check Redis is running**
   ```bash
   systemctl status redis
   ```

2. **Check Redis port**
   ```bash
   netstat -tlnp | grep 6379
   ```

3. **Test connection**
   ```bash
   redis-cli ping
   ```

**Solutions**:

1. **Start Redis**
   ```bash
   systemctl start redis
   ```

2. **Check Redis configuration**
   ```bash
   cat /etc/redis/redis.conf | grep bind
   # Should include: bind 127.0.0.1
   ```

### Redis Out of Memory

**Symptom**: `OOM command not allowed when used memory > 'maxmemory'`

**Debugging Steps**:

1. **Check memory usage**
   ```bash
   redis-cli info memory
   ```

2. **Check maxmemory setting**
   ```bash
   redis-cli config get maxmemory
   ```

**Solutions**:

1. **Increase maxmemory**
   ```bash
   redis-cli config set maxmemory 4gb
   ```

2. **Set eviction policy**
   ```bash
   redis-cli config set maxmemory-policy allkeys-lru
   ```

3. **Clear old data**
   ```bash
   # Clear rate limit keys older than 1 hour
   redis-cli --scan --pattern "rate_limit:*" | xargs redis-cli del
   ```

---

## Message Delivery Failures

### Messages Stuck in Pending

**Symptom**: Messages remain in pending status

**Debugging Steps**:

1. **Check Celery workers**
   ```bash
   celery -A neurotwin inspect active
   ```

2. **Check message status**
   ```python
   from apps.automation.models import Message
   
   pending = Message.objects.filter(status='pending').count()
   print(f"Pending messages: {pending}")
   ```

3. **Check task queue**
   ```bash
   celery -A neurotwin inspect active_queues
   ```

**Solutions**:

1. **Start workers if not running**
2. **Check rate limits**
3. **Manually trigger send task**
   ```python
   from apps.automation.tasks.message_tasks import send_outgoing_message
   
   send_outgoing_message.delay('message-uuid')
   ```

### Messages Failing After Retries

**Symptom**: Messages marked as failed after 5 retries

**Debugging Steps**:

1. **Check error message**
   ```python
   message = Message.objects.get(id='uuid')
   print(f"Status: {message.status}")
   print(f"Retry count: {message.retry_count}")
   print(f"Last retry: {message.last_retry_at}")
   ```

2. **Check integration health**
   ```python
   integration = message.conversation.integration
   print(f"Health: {integration.health_status}")
   print(f"Consecutive failures: {integration.consecutive_failures}")
   ```

**Common Causes**:

1. **Integration disconnected**
   
   **Solution**: User must re-authenticate
   ```python
   integration.status = 'disconnected'
   integration.save()
   # Notify user to reconnect
   ```

2. **Invalid message format**
   
   **Solution**: Check message content and metadata
   ```python
   print(f"Content: {message.content}")
   print(f"Metadata: {message.metadata}")
   ```

3. **External API error**
   
   **Solution**: Check external API status and logs

---

## Getting Help

### Collect Diagnostic Information

When reporting issues, include:

1. **System information**
   ```bash
   python --version
   redis-cli --version
   psql --version
   celery --version
   ```

2. **Error logs**
   ```bash
   tail -n 100 /var/log/neurotwin/app.log
   tail -n 100 /var/log/celery/worker.log
   ```

3. **Configuration**
   ```python
   # Django settings (sanitized)
   python manage.py diffsettings
   ```

4. **Database state**
   ```python
   from apps.automation.models import Integration, Message
   
   print(f"Total integrations: {Integration.objects.count()}")
   print(f"Active integrations: {Integration.objects.filter(status='active').count()}")
   print(f"Pending messages: {Message.objects.filter(status='pending').count()}")
   print(f"Failed messages: {Message.objects.filter(status='failed').count()}")
   ```

### Support Channels

- **Email**: support@neurotwin.com
- **Documentation**: https://docs.neurotwin.com
- **GitHub Issues**: https://github.com/neurotwin/neurotwin/issues

---

## Additional Resources

- [API Documentation](./integration-engine-api.md)
- [Developer Guide](./integration-engine-developer-guide.md)
- [Deployment Guide](./integration-engine-deployment.md)
- [Design Document](../.kiro/specs/scalable-integration-engine/design.md)
