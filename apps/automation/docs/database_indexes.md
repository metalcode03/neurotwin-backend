# Database Indexes for Scalable Integration Engine

This document defines all required database indexes for optimal query performance.

**Requirements: 31.7** - Use database indexing on frequently queried fields

## Index Strategy

### Single-Column Indexes
Used for simple lookups and filtering on individual columns.

### Composite Indexes
Used for queries that filter on multiple columns together. Order matters - most selective column first.

### Covering Indexes
Include additional columns to avoid table lookups (PostgreSQL INCLUDE clause).

## Model: IntegrationTypeModel

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['auth_type'], name='idx_inttype_auth_type'),
        models.Index(fields=['category'], name='idx_inttype_category'),
        models.Index(fields=['is_active'], name='idx_inttype_is_active'),
        
        # Composite indexes for common query patterns
        models.Index(
            fields=['auth_type', 'is_active'],
            name='idx_inttype_auth_active'
        ),
        models.Index(
            fields=['category', 'is_active'],
            name='idx_inttype_cat_active'
        ),
    ]
```

### Query Patterns Optimized
- `IntegrationTypeModel.objects.filter(auth_type='oauth')`
- `IntegrationTypeModel.objects.filter(is_active=True)`
- `IntegrationTypeModel.objects.filter(auth_type='meta', is_active=True)`
- `IntegrationTypeModel.objects.filter(category='messaging', is_active=True)`

## Model: Integration

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['user'], name='idx_integration_user'),
        models.Index(fields=['integration_type'], name='idx_integration_type'),
        models.Index(fields=['status'], name='idx_integration_status'),
        models.Index(fields=['health_status'], name='idx_integration_health'),
        models.Index(fields=['token_expires_at'], name='idx_integration_expires'),
        
        # Meta-specific fields
        models.Index(fields=['waba_id'], name='idx_integration_waba'),
        models.Index(fields=['phone_number_id'], name='idx_integration_phone'),
        models.Index(fields=['business_id'], name='idx_integration_business'),
        
        # Composite indexes for common query patterns
        models.Index(
            fields=['user', 'status'],
            name='idx_integration_user_status'
        ),
        models.Index(
            fields=['user', 'integration_type'],
            name='idx_integration_user_type'
        ),
        models.Index(
            fields=['health_status', 'consecutive_failures'],
            name='idx_integration_health_fails'
        ),
        models.Index(
            fields=['status', 'token_expires_at'],
            name='idx_integration_status_expires'
        ),
        
        # Covering index for token refresh queries
        models.Index(
            fields=['status', 'token_expires_at'],
            name='idx_integration_token_refresh',
            condition=models.Q(status='active'),  # Partial index
        ),
    ]
    
    # Unique constraint
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'integration_type'],
            name='unique_user_integration_type'
        ),
    ]
```

### Query Patterns Optimized
- `Integration.objects.filter(user=user)`
- `Integration.objects.filter(user=user, status='active')`
- `Integration.objects.filter(waba_id='123456')`
- `Integration.objects.filter(status='active', token_expires_at__lte=threshold)`
- `Integration.objects.filter(health_status='degraded')`

## Model: InstallationSession

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['user'], name='idx_session_user'),
        models.Index(fields=['oauth_state'], name='idx_session_state'),
        models.Index(fields=['status'], name='idx_session_status'),
        models.Index(fields=['expires_at'], name='idx_session_expires'),
        
        # Composite indexes
        models.Index(
            fields=['oauth_state', 'status'],
            name='idx_session_state_status'
        ),
        models.Index(
            fields=['user', 'status', 'expires_at'],
            name='idx_session_user_status_exp'
        ),
    ]
```

### Query Patterns Optimized
- `InstallationSession.objects.filter(oauth_state='abc123')`
- `InstallationSession.objects.filter(user=user, status='oauth_pending')`
- `InstallationSession.objects.filter(expires_at__lt=now())`

## Model: Conversation

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['integration'], name='idx_conv_integration'),
        models.Index(fields=['status'], name='idx_conv_status'),
        models.Index(fields=['last_message_at'], name='idx_conv_last_msg'),
        
        # Composite indexes for common query patterns
        models.Index(
            fields=['integration', 'status'],
            name='idx_conv_int_status'
        ),
        models.Index(
            fields=['integration', 'last_message_at'],
            name='idx_conv_int_last_msg'
        ),
        models.Index(
            fields=['integration', 'external_contact_id'],
            name='idx_conv_int_contact'
        ),
    ]
    
    # Unique constraint
    constraints = [
        models.UniqueConstraint(
            fields=['integration', 'external_contact_id'],
            name='unique_integration_contact'
        ),
    ]
```

### Query Patterns Optimized
- `Conversation.objects.filter(integration=integration).order_by('-last_message_at')`
- `Conversation.objects.filter(integration=integration, status='active')`
- `Conversation.objects.get(integration=integration, external_contact_id='123')`

## Model: Message

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['conversation'], name='idx_msg_conversation'),
        models.Index(fields=['status'], name='idx_msg_status'),
        models.Index(fields=['external_message_id'], name='idx_msg_external_id'),
        models.Index(fields=['created_at'], name='idx_msg_created'),
        models.Index(fields=['direction'], name='idx_msg_direction'),
        
        # Composite indexes for common query patterns
        models.Index(
            fields=['conversation', 'created_at'],
            name='idx_msg_conv_created'
        ),
        models.Index(
            fields=['conversation', 'direction'],
            name='idx_msg_conv_direction'
        ),
        models.Index(
            fields=['status', 'retry_count'],
            name='idx_msg_status_retry'
        ),
        models.Index(
            fields=['status', 'last_retry_at'],
            name='idx_msg_status_last_retry'
        ),
        
        # Covering index for message listing
        models.Index(
            fields=['conversation', 'created_at'],
            name='idx_msg_conv_created_cover',
            include=['direction', 'status', 'content']  # PostgreSQL 11+
        ),
    ]
```

### Query Patterns Optimized
- `Message.objects.filter(conversation=conversation).order_by('created_at')`
- `Message.objects.filter(status='pending')`
- `Message.objects.filter(external_message_id='msg_123')`
- `Message.objects.filter(status='failed', retry_count__lt=5)`

## Model: WebhookEvent

### Required Indexes

```python
class Meta:
    indexes = [
        # Single-column indexes
        models.Index(fields=['integration_type'], name='idx_webhook_int_type'),
        models.Index(fields=['integration'], name='idx_webhook_integration'),
        models.Index(fields=['status'], name='idx_webhook_status'),
        models.Index(fields=['created_at'], name='idx_webhook_created'),
        models.Index(fields=['processed_at'], name='idx_webhook_processed'),
        
        # Composite indexes for common query patterns
        models.Index(
            fields=['status', 'created_at'],
            name='idx_webhook_status_created'
        ),
        models.Index(
            fields=['integration_type', 'status'],
            name='idx_webhook_type_status'
        ),
        models.Index(
            fields=['integration', 'created_at'],
            name='idx_webhook_int_created'
        ),
    ]
```

### Query Patterns Optimized
- `WebhookEvent.objects.filter(status='pending').order_by('created_at')`
- `WebhookEvent.objects.filter(integration_type=int_type, status='failed')`
- `WebhookEvent.objects.filter(created_at__gte=thirty_days_ago)`

## PostgreSQL-Specific Optimizations

### Partial Indexes
For queries that frequently filter on specific values:

```python
# Only index active integrations
models.Index(
    fields=['user', 'status'],
    name='idx_integration_active_user',
    condition=models.Q(status='active')
)

# Only index pending messages
models.Index(
    fields=['created_at'],
    name='idx_msg_pending_created',
    condition=models.Q(status='pending')
)
```

### GIN Indexes for JSONField
For queries on JSON fields:

```python
from django.contrib.postgres.indexes import GinIndex

class Meta:
    indexes = [
        GinIndex(fields=['metadata'], name='idx_msg_metadata_gin'),
        GinIndex(fields=['auth_config'], name='idx_inttype_config_gin'),
    ]
```

### BRIN Indexes for Time-Series Data
For large tables with sequential time-based data:

```python
from django.contrib.postgres.indexes import BrinIndex

class Meta:
    indexes = [
        BrinIndex(fields=['created_at'], name='idx_webhook_created_brin'),
    ]
```

## Index Maintenance

### Monitoring Index Usage
```sql
-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexname NOT LIKE 'pg_toast%'
    AND schemaname = 'public';
```

### Index Size Monitoring
```sql
-- Check index sizes
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Reindexing
```sql
-- Reindex a specific index
REINDEX INDEX CONCURRENTLY idx_integration_user;

-- Reindex entire table
REINDEX TABLE CONCURRENTLY automation_integration;
```

## Migration Template

When creating models, use this migration template:

```python
# Generated migration file
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('automation', '0001_initial'),
    ]

    operations = [
        # Add indexes
        migrations.AddIndex(
            model_name='integration',
            index=models.Index(fields=['user', 'status'], name='idx_integration_user_status'),
        ),
        
        # Add constraints
        migrations.AddConstraint(
            model_name='integration',
            constraint=models.UniqueConstraint(
                fields=['user', 'integration_type'],
                name='unique_user_integration_type'
            ),
        ),
    ]
```

## Performance Testing

After adding indexes, verify performance improvements:

```python
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase

class IndexPerformanceTest(TestCase):
    def test_integration_user_query_performance(self):
        """Test that user integration queries use indexes."""
        with self.assertNumQueries(1):
            list(Integration.objects.filter(user=self.user))
        
        # Check query plan
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN ANALYZE
                SELECT * FROM automation_integration
                WHERE user_id = %s
            """, [self.user.id])
            
            plan = cursor.fetchall()
            # Verify index scan is used
            self.assertIn('Index Scan', str(plan))
```

## Checklist

When implementing models, ensure:

- [ ] All foreign keys have indexes (Django creates these automatically)
- [ ] All fields used in `filter()` have indexes
- [ ] All fields used in `order_by()` have indexes
- [ ] Composite indexes match common query patterns
- [ ] Unique constraints are defined where needed
- [ ] Partial indexes are used for frequently filtered values
- [ ] GIN indexes are used for JSON field queries
- [ ] Index names follow naming convention: `idx_{table}_{columns}`
- [ ] Constraint names follow naming convention: `unique_{table}_{columns}`
- [ ] Migration includes all indexes and constraints
- [ ] Performance tests verify index usage
