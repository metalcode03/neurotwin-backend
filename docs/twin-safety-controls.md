# Twin Safety Controls Implementation

This document describes the Twin safety controls implemented in Task 28 of the Dynamic App Marketplace spec.

## Overview

The Twin safety controls provide three layers of protection:
1. **Permission Validation Middleware** - Validates permission_flag for Twin-initiated requests
2. **Integration Permission Checking** - Verifies integration permissions before workflow execution
3. **Kill-Switch Functionality** - Emergency stop for all Twin automations

## Components

### 1. Permission Validation Middleware

**File**: `apps/automation/middleware.py`

**Class**: `TwinPermissionMiddleware`

**Purpose**: Validates that Twin-initiated requests have explicit permission_flag set.

**How it works**:
- Checks for `X-Twin-Initiated: true` header
- For protected endpoints (`/api/v1/automations/`, `/api/v1/workflows/`, `/api/v1/integrations/`)
- For modifying methods (POST, PUT, PATCH, DELETE)
- Requires `permission_flag=true` in header, body, or query params
- Returns 403 Forbidden if permission not granted
- Logs all permission denials to audit log

**Usage**:
```python
# Frontend must include headers for Twin-initiated requests
headers = {
    'X-Twin-Initiated': 'true',
    'X-Permission-Flag': 'true',  # Required for modifying requests
}
```

### 2. Kill-Switch Middleware

**File**: `apps/automation/middleware.py`

**Class**: `KillSwitchMiddleware`

**Purpose**: Blocks all Twin-initiated requests when kill-switch is active.

**How it works**:
- Checks for `X-Twin-Initiated: true` header
- Checks user's Twin.kill_switch_active status
- Returns 403 Forbidden if kill-switch is active
- Logs blocked requests to audit log

### 3. Integration Permission Service

**File**: `apps/automation/services/permission.py`

**Class**: `PermissionService`

**Purpose**: Validates integration permissions before workflow execution.

**Key Methods**:

#### `check_integration_permission(integration, permission_name)`
Checks if an integration has a specific permission enabled.

#### `check_workflow_step_permission(user, step, workflow)`
Validates a single workflow step has required permissions.

#### `validate_workflow_permissions(user, workflow)`
Validates all steps in a workflow have required permissions.

#### `should_skip_step(execution, step_index, step)`
Determines if a step should be skipped due to missing permissions.

#### `get_missing_permissions(user, workflow)`
Returns list of missing permissions for a workflow.

**Usage**:
```python
from apps.automation.services.permission import PermissionService

# Check if workflow can execute
is_valid, errors = PermissionService.validate_workflow_permissions(
    user=request.user,
    workflow=workflow
)

if not is_valid:
    return error_response(errors)

# During execution, check if step should be skipped
should_skip, reason = PermissionService.should_skip_step(
    execution=execution,
    step_index=i,
    step=step
)

if should_skip:
    logger.info(f'Skipping step {i}: {reason}')
    continue
```

### 4. Kill-Switch Service

**File**: `apps/twin/services/kill_switch.py`

**Class**: `KillSwitchService`

**Purpose**: Manages kill-switch activation/deactivation.

**Key Methods**:

#### `activate_kill_switch(user, reason, ip_address, user_agent)`
Activates kill-switch for a user's Twin.
- Sets `Twin.kill_switch_active = True`
- Logs activation to audit log
- Optionally disables all workflows

#### `deactivate_kill_switch(user, reason, ip_address, user_agent)`
Deactivates kill-switch for a user's Twin.
- Sets `Twin.kill_switch_active = False`
- Logs deactivation to audit log

#### `get_kill_switch_status(user)`
Returns current kill-switch status and details.

#### `is_kill_switch_active(user)`
Quick check if kill-switch is active.

#### `disable_all_twin_automations(user)`
Disables all active workflows for a user.

#### `get_blocked_requests_count(user, since_hours)`
Returns count of requests blocked by kill-switch.

### 5. Kill-Switch API Endpoints

**File**: `apps/twin/views.py`

**Endpoints**:

#### `POST /api/v1/twin/kill-switch/activate`
Activates kill-switch.

**Request**:
```json
{
  "reason": "User-initiated emergency stop",
  "disable_workflows": true
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "twin_id": "uuid",
    "kill_switch_active": true,
    "workflows_disabled": 5
  },
  "message": "Kill-switch activated. All Twin automations are now disabled."
}
```

#### `POST /api/v1/twin/kill-switch/deactivate`
Deactivates kill-switch.

**Request**:
```json
{
  "reason": "Resuming normal operations"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "twin_id": "uuid",
    "kill_switch_active": false
  },
  "message": "Kill-switch deactivated. Twin automations are now enabled."
}
```

#### `GET /api/v1/twin/kill-switch/status`
Gets current kill-switch status.

**Response**:
```json
{
  "success": true,
  "data": {
    "active": false,
    "twin_id": "uuid",
    "twin_active": true,
    "cognitive_blend": 50,
    "last_updated": "2026-03-08T13:14:00Z",
    "blocked_requests_24h": 0
  }
}
```

## Configuration

The middleware is automatically enabled in `neurotwin/settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    'apps.automation.middleware.KillSwitchMiddleware',  # Check kill-switch first
    'apps.automation.middleware.TwinPermissionMiddleware',  # Then check permissions
]
```

## Security Considerations

1. **Permission Flag Required**: All Twin-initiated modifying requests must include `permission_flag=true`
2. **Kill-Switch Priority**: Kill-switch is checked before permission validation
3. **Audit Logging**: All permission denials and kill-switch activations are logged
4. **IP Tracking**: Client IP and user agent are logged for security auditing
5. **User Control**: Only the user can activate/deactivate their own kill-switch

## Testing

To test the safety controls:

1. **Test Permission Middleware**:
```bash
# Should fail without permission_flag
curl -X POST http://localhost:8000/api/v1/automations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Twin-Initiated: true" \
  -H "Content-Type: application/json"

# Should succeed with permission_flag
curl -X POST http://localhost:8000/api/v1/automations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Twin-Initiated: true" \
  -H "X-Permission-Flag: true" \
  -H "Content-Type: application/json"
```

2. **Test Kill-Switch**:
```bash
# Activate kill-switch
curl -X POST http://localhost:8000/api/v1/twin/kill-switch/activate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Testing", "disable_workflows": true}'

# Try Twin request (should fail)
curl -X POST http://localhost:8000/api/v1/automations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Twin-Initiated: true" \
  -H "X-Permission-Flag: true"

# Deactivate kill-switch
curl -X POST http://localhost:8000/api/v1/twin/kill-switch/deactivate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Testing complete"}'
```

3. **Test Integration Permissions**:
```python
from apps.automation.services.permission import PermissionService

# Validate workflow permissions
is_valid, errors = PermissionService.validate_workflow_permissions(
    user=user,
    workflow=workflow
)

# Get missing permissions
missing = PermissionService.get_missing_permissions(
    user=user,
    workflow=workflow
)
```

## Requirements Satisfied

- **Requirement 8.1**: Permission validation for Twin-initiated requests ✓
- **Requirement 12.7**: Permission flag checking and logging ✓
- **Requirement 12.4-12.5**: Integration permission verification ✓
- **Safety Principles**: Kill-switch for all automations ✓

## Future Enhancements

1. **Notification Service**: Send notifications when kill-switch is activated
2. **Workflow Auto-Resume**: Option to automatically re-enable workflows when kill-switch is deactivated
3. **Scheduled Kill-Switch**: Allow users to schedule kill-switch activation (e.g., during vacation)
4. **Permission Templates**: Pre-defined permission sets for common use cases
5. **Granular Kill-Switch**: Kill-switch per integration type or workflow
