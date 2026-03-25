# Twin Workflow Modification Implementation

## Overview

This document describes the implementation of Task 26: Twin workflow modification, which enables the Twin AI to modify user workflows with proper safety controls, permission checking, and audit logging.

## Implemented Features

### 1. Twin Permission Checking (Sub-task 26.1)

**Location:** `apps/automation/services/workflow.py`

The `WorkflowService.update_workflow()` method now includes:

- **Permission Flag Validation**: Requires `permission_flag=True` for all Twin modifications
- **Rejection Logging**: Logs all rejected Twin modification attempts with workflow ID and user ID
- **PermissionError**: Raises exception when Twin attempts modification without permission

**Safety Principle:** Enforces the core safety rule that Twin CANNOT modify workflows without explicit permission.

### 2. Cognitive Blend Validation (Sub-task 26.2)

**Location:** `apps/automation/services/workflow.py`

Enhanced the workflow update method to:

- **Auto-fetch Cognitive Blend**: Automatically retrieves `cognitive_blend` value from user's Twin profile if not provided
- **High Blend Detection**: Identifies when `cognitive_blend > 80%` and logs warning
- **Confirmation Requirement**: Documents that high blend modifications require explicit user confirmation (handled at API layer)
- **History Tracking**: Stores `cognitive_blend_value` in `WorkflowChangeHistory` for audit trail

**Safety Principle:** Implements the ai.rules.md requirement that actions with cognitive_blend > 80% require explicit confirmation.

### 3. Twin Suggestion Storage (Sub-task 26.3)

**New Components:**

#### Model: `TwinSuggestion`
**Location:** `apps/automation/models.py`

Stores Twin workflow modification suggestions with:
- `suggested_changes`: Dictionary of proposed field changes
- `reasoning`: Explanation for why Twin suggests this modification
- `cognitive_blend_value`: Cognitive blend at time of suggestion
- `based_on_pattern`: Description of learned pattern that triggered suggestion
- `status`: PENDING, APPROVED, REJECTED, or EXPIRED
- `expires_at`: Automatic expiration after 7 days (configurable)

**Methods:**
- `approve()`: Applies changes to workflow and creates change history
- `reject()`: Marks suggestion as rejected with optional notes
- `mark_expired()`: Marks expired suggestions
- `cleanup_expired()`: Class method to batch-expire old suggestions

#### Service: `TwinSuggestionService`
**Location:** `apps/automation/services/twin_suggestion.py`

Provides business logic for:
- `create_suggestion()`: Creates new Twin suggestions with validation
- `get_pending_suggestions()`: Retrieves pending suggestions for user
- `approve_suggestion()`: Approves and applies suggestion to workflow
- `reject_suggestion()`: Rejects suggestion with optional notes
- `cleanup_expired_suggestions()`: Periodic cleanup task

#### API Endpoints: `TwinSuggestionViewSet`
**Location:** `apps/automation/views/twin_suggestion.py`

REST API endpoints:
- `GET /api/v1/twin-suggestions/` - List pending suggestions
- `GET /api/v1/twin-suggestions/{id}/` - Get suggestion details
- `POST /api/v1/twin-suggestions/` - Create new suggestion (Twin AI)
- `POST /api/v1/twin-suggestions/{id}/review/` - Approve/reject suggestion
- `GET /api/v1/twin-suggestions/pending/` - Get all pending suggestions
- `POST /api/v1/twin-suggestions/cleanup_expired/` - Cleanup expired suggestions

#### Serializers
**Location:** `apps/automation/serializers/twin_suggestion.py`

- `TwinSuggestionSerializer`: Full suggestion details
- `CreateTwinSuggestionSerializer`: Create new suggestions
- `ReviewTwinSuggestionSerializer`: Approve/reject suggestions

**Safety Principle:** Enables Twin to suggest modifications without automatically applying them, giving users full control.

### 4. Change History Tracking (Sub-task 26.4)

**Enhanced Components:**

#### WorkflowChangeHistory Model
**Location:** `apps/automation/models.py` (already existed)

Tracks all workflow modifications with:
- `modified_by_twin`: Boolean flag for Twin vs User modifications
- `cognitive_blend_value`: Cognitive blend at time of Twin modification
- `changes_made`: JSON dictionary with before/after values
- `reasoning`: Explanation for changes (especially for Twin mods)
- `permission_flag`: Whether permission was granted
- `required_confirmation`: Whether confirmation was required (blend > 80%)

#### API Endpoint: Change History
**Location:** `apps/automation/views/automation.py`

New endpoint:
- `GET /api/v1/automations/{id}/change_history/` - Get complete change history for a workflow

Returns:
- All modifications ordered by most recent first
- Author attribution (User or Twin)
- Timestamp of each change
- Before/after values for all changed fields
- Reasoning for Twin modifications
- Cognitive blend value for Twin modifications
- Permission and confirmation flags

#### Serializer: `WorkflowChangeHistorySerializer`
**Location:** `apps/automation/serializers/workflow.py`

Serializes change history with:
- Human-readable author field ("User" or "Twin")
- User email for audit trail
- Workflow name for context
- All change metadata

**Safety Principle:** Provides complete audit trail for all workflow modifications, enabling transparency and accountability.

## Database Schema

### TwinSuggestion Table

```sql
CREATE TABLE twin_suggestions (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id),
    user_id UUID REFERENCES users(id),
    suggested_changes JSONB,
    reasoning TEXT,
    cognitive_blend_value INTEGER,
    based_on_pattern TEXT,
    status VARCHAR(20),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    INDEX idx_user_status (user_id, status),
    INDEX idx_workflow_status (workflow_id, status),
    INDEX idx_status_expires (status, expires_at)
);
```

## Usage Examples

### Example 1: Twin Creates a Suggestion

```python
from apps.automation.services.twin_suggestion import TwinSuggestionService

# Twin AI creates a suggestion based on learned patterns
suggestion = TwinSuggestionService.create_suggestion(
    user=user,
    workflow_id=workflow.id,
    suggested_changes={
        'trigger_config': {
            'schedule': '0 9 * * *'  # Change to 9 AM daily
        }
    },
    reasoning='User typically checks email at 9 AM based on 30-day pattern analysis',
    cognitive_blend_value=65,
    based_on_pattern='Morning email check pattern: 9:00-9:15 AM (87% consistency)',
    expires_in_days=7
)
```

### Example 2: User Reviews Suggestion

```bash
# User approves suggestion
POST /api/v1/twin-suggestions/{id}/review/
{
    "action": "approve",
    "review_notes": "Good catch, I do prefer morning emails"
}

# User rejects suggestion
POST /api/v1/twin-suggestions/{id}/review/
{
    "action": "reject",
    "review_notes": "I want to keep the current schedule"
}
```

### Example 3: Twin Modifies Workflow (with permission)

```python
from apps.automation.services.workflow import WorkflowService

# Twin modifies workflow after user approval
workflow = WorkflowService.update_workflow(
    workflow_id=workflow.id,
    user=user,
    updates={
        'trigger_config': {'schedule': '0 9 * * *'},
        '_reasoning': 'Adjusted based on user morning routine pattern'
    },
    modified_by_twin=True,
    cognitive_blend=None,  # Will auto-fetch from Twin profile
    permission_flag=True  # User granted permission
)
```

### Example 4: View Change History

```bash
# Get complete change history for a workflow
GET /api/v1/automations/{workflow_id}/change_history/

Response:
{
    "workflow_id": "uuid",
    "workflow_name": "Morning Email Check",
    "change_history": [
        {
            "id": "uuid",
            "author": "Twin",
            "user_email": "user@example.com",
            "modified_by_twin": true,
            "cognitive_blend_value": 65,
            "changes_made": {
                "trigger_config": {
                    "before": {"schedule": "0 8 * * *"},
                    "after": {"schedule": "0 9 * * *"}
                }
            },
            "reasoning": "Adjusted based on user morning routine pattern",
            "permission_flag": true,
            "required_confirmation": false,
            "created_at": "2024-01-15T09:30:00Z"
        },
        {
            "id": "uuid",
            "author": "User",
            "user_email": "user@example.com",
            "modified_by_twin": false,
            "cognitive_blend_value": null,
            "changes_made": {
                "is_active": {
                    "before": false,
                    "after": true
                }
            },
            "reasoning": "",
            "permission_flag": false,
            "required_confirmation": false,
            "created_at": "2024-01-14T10:00:00Z"
        }
    ],
    "total_changes": 2
}
```

## Safety Controls

### 1. Permission-Based Execution
- All Twin modifications require `permission_flag=True`
- Rejected attempts are logged for security audit
- PermissionError raised for unauthorized attempts

### 2. Cognitive Blend Validation
- Automatically fetches current blend from Twin profile
- Logs high blend values (> 80%) for review
- Stores blend value in change history for audit
- Requires explicit confirmation for high blend modifications

### 3. Suggestion-Based Workflow
- Twin suggests modifications instead of applying directly
- User reviews and approves/rejects each suggestion
- Suggestions expire after 7 days if not reviewed
- Full reasoning provided for transparency

### 4. Complete Audit Trail
- Every modification tracked in WorkflowChangeHistory
- Before/after values stored for all changes
- Author attribution (User vs Twin)
- Timestamp, reasoning, and context preserved
- Cognitive blend value logged for Twin modifications

## Integration with AI Rules

This implementation follows the cognitive safety principles from `ai.rules.md`:

1. **Action Confirmation**: High blend (> 80%) modifications require confirmation
2. **Permission-Based Actions**: All Twin modifications require `permission_flag=True`
3. **Audit Trails**: Complete logging of all Twin actions with timestamp and outcome
4. **User Control**: Twin suggests rather than automatically applies changes
5. **Transparency**: Full reasoning provided for all Twin suggestions

## Future Enhancements

1. **Batch Suggestions**: Allow Twin to suggest multiple related changes
2. **Pattern Visualization**: Show learned patterns that triggered suggestions
3. **Suggestion Analytics**: Track approval/rejection rates to improve Twin learning
4. **Rollback Capability**: One-click rollback of Twin modifications
5. **Notification System**: Alert users of pending suggestions
6. **Scheduled Cleanup**: Automated cron job for expired suggestion cleanup

## Testing

To test the implementation:

```bash
# Run Django checks
uv run python manage.py check

# Run migrations
uv run python manage.py migrate automation

# Test API endpoints (requires authentication)
curl -X GET http://localhost:8000/api/v1/twin-suggestions/ \
  -H "Authorization: Bearer <token>"

# View change history
curl -X GET http://localhost:8000/api/v1/automations/{id}/change_history/ \
  -H "Authorization: Bearer <token>"
```

## Conclusion

Task 26 has been successfully implemented with all sub-tasks complete:

✅ 26.1 - Twin permission checking with rejection logging
✅ 26.2 - Cognitive blend validation with auto-fetch from Twin profile
✅ 26.3 - Twin suggestion storage with approval/rejection workflow
✅ 26.4 - Change history tracking with complete audit trail

The implementation provides robust safety controls, complete transparency, and user control over Twin workflow modifications, aligning with NeuroTwin's core safety principles.
