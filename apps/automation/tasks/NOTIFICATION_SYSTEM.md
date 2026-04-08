# Notification System for Integration Failures

## Overview

The notification system provides automated alerts to users when integration failures occur, helping them stay informed about issues with their connected platforms and take corrective action.

## Components

### 1. Notification Tasks (`notification_tasks.py`)

Two main Celery tasks handle user notifications:

#### `notify_message_failure`
- **Trigger**: Message fails after 5 retry attempts
- **Purpose**: Inform user about message delivery failure
- **Content**: 
  - Integration name and contact name
  - Message preview
  - Retry count and error details
  - Action buttons (Retry Message, View Integration)
- **Requirements**: 13.4

#### `notify_integration_disconnected`
- **Trigger**: Integration health_status becomes 'disconnected' (10+ consecutive failures)
- **Purpose**: Alert user about integration disconnection
- **Content**:
  - Integration name and failure count
  - Last successful sync timestamp
  - Auth-type-specific reconnection instructions
  - Action buttons (Reconnect, View Details, Remove)
- **Requirements**: 23.7

### 2. Integration Points

Notifications are triggered from multiple locations:

#### Message Processing (`message_tasks.py`)
- **Location**: `send_outgoing_message` task
- **Trigger**: After max retries (5) exceeded
- **Action**: Calls `notify_message_failure.delay(message_id)`

#### Health Monitoring (`integration_health.py`)
- **Location**: `IntegrationHealthService.record_failure()`
- **Trigger**: When status changes from non-disconnected to disconnected
- **Action**: Calls `notify_integration_disconnected.delay(integration_id)`

#### Token Refresh (`token_refresh.py`)
- **Location**: Celery task failure handler
- **Trigger**: When consecutive failures reach 10
- **Action**: Calls `notify_integration_disconnected.delay(integration_id)`

#### Token Refresh Service (`services/token_refresh.py`)
- **Location**: `IntegrationRefreshService._handle_refresh_failure()`
- **Trigger**: When consecutive failures reach 10
- **Action**: Calls `notify_integration_disconnected.delay(integration_id)`

## Reconnection Instructions

The system provides auth-type-specific reconnection instructions:

### OAuth Integrations
- Redirect to authorization flow
- Common causes: expired tokens, revoked access, API issues

### Meta (WhatsApp) Integrations
- Complete Meta Business verification again
- Common causes: 60-day token expiry, suspended account, removed phone number

### API Key Integrations
- Update API key through UI
- Common causes: revoked/expired key, unreachable endpoint, suspended account

## Notification Data Structure

```python
{
    'type': 'message_failure' | 'integration_disconnected',
    'title': 'Human-readable title',
    'message': 'Brief description',
    'details': {
        'integration_id': 'uuid',
        'integration_name': 'WhatsApp',
        # ... additional context
    },
    'actions': [
        {
            'label': 'Action Label',
            'action': 'action_type',
            'integration_id': 'uuid'
        }
    ]
}
```

## Future Enhancements

The current implementation includes TODO markers for:

1. **Database Storage**: Create `Notification` model to persist notifications
2. **Email Notifications**: Send email alerts via `EmailNotificationService`
3. **Push Notifications**: Send mobile/browser push via `PushNotificationService`
4. **User Preferences**: Respect user notification preferences per channel
5. **Notification History**: Allow users to view past notifications

## Testing

To test the notification system:

1. **Message Failure**:
   ```python
   # Simulate message failure after max retries
   from apps.automation.tasks import send_outgoing_message
   # Force 5 failures to trigger notification
   ```

2. **Integration Disconnection**:
   ```python
   # Simulate 10 consecutive failures
   from apps.automation.services import IntegrationHealthService
   for i in range(10):
       IntegrationHealthService.record_failure(integration)
   ```

## Monitoring

Key metrics to monitor:
- Notification delivery rate
- User response to notifications (reconnection rate)
- Time between notification and user action
- Notification preferences by user segment

## Related Requirements

- **Requirement 13.4**: Message failure notifications
- **Requirement 23.7**: Integration disconnection notifications
- **Requirement 29.1-29.7**: Error handling and user feedback
