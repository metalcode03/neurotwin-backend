# Automation & Integrations Documentation

## Overview

The Automation system is the backbone of NeuroTwin's autonomous action capabilities. It manages how the Twin connects to external platforms, executes workflows, and tracks all modifications with full audit trails.

The system is split across:
- `apps/automation/` — Django backend (models, services, views, serializers)
- `neuro-frontend/src/app/dashboard/automation/` — Next.js dashboard UI
- `neuro-frontend/src/lib/api/` — TypeScript API clients (`automation.ts`, `marketplace.ts`, `twin-automation.ts`)

---

## Architecture

```
User
 │
 ├── App Marketplace (browse & install integrations)
 │     └── IntegrationTypeViewSet → AppMarketplaceService
 │
 ├── Installation Flow (OAuth 2.0)
 │     └── InstallationViewSet → InstallationService → OAuthClient
 │
 ├── Automation Dashboard (manage workflows)
 │     └── WorkflowViewSet → WorkflowService
 │
 └── Twin Suggestions (AI-proposed workflow changes)
       └── TwinSuggestionViewSet → TwinSuggestionService
```

---

## Data Models

### IntegrationTypeModel

Represents a supported external platform (e.g., Gmail, Slack). Dynamically managed — new types can be added at runtime without code changes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `type` | string | Kebab-case identifier (e.g., `google-calendar`) |
| `name` | string | Display name |
| `icon` | FileField | SVG/PNG icon (max 500KB) |
| `description` | text | Full description |
| `brief_description` | string (200) | Short card description |
| `category` | enum | `communication`, `productivity`, `crm`, `calendar`, `documents`, `video_conferencing`, `other` |
| `oauth_config` | JSON | OAuth 2.0 config — `client_id`, `client_secret_encrypted`, `authorization_url`, `token_url`, `scopes`, `revoke_url` |
| `default_permissions` | JSON | Default permission settings for new installs |
| `is_active` | bool | Visible in marketplace |
| `created_at` / `updated_at` | datetime | Timestamps |

The `client_secret` is AES-encrypted at rest via `TokenEncryption`. Never stored in plaintext.

Supported integration categories:

| Category | Examples |
|----------|---------|
| `communication` | WhatsApp, Telegram, Slack |
| `productivity` | Google Docs, Microsoft Office |
| `calendar` | Google Calendar |
| `documents` | Google Docs |
| `video_conferencing` | Zoom, Google Meet |
| `crm` | CRM tools |

---

### Integration

A user's installed instance of an `IntegrationTypeModel`. One per user per integration type (enforced by `unique_together`).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | FK → User | Owner |
| `integration_type` | FK → IntegrationTypeModel | The platform type |
| `oauth_token_encrypted` | BinaryField | Encrypted access token |
| `refresh_token_encrypted` | BinaryField | Encrypted refresh token |
| `scopes` | JSON | Granted OAuth scopes |
| `steering_rules` | JSON | Allowed action rules for this integration |
| `permissions` | JSON | Per-permission toggles |
| `token_expires_at` | datetime | Token expiry |
| `is_active` | bool | Active status |

Tokens are encrypted/decrypted transparently via Python properties:
```python
integration.oauth_token = "raw_token"   # encrypts on set
token = integration.oauth_token          # decrypts on get
```

---

### InstallationSession

Tracks the two-phase OAuth installation process.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | FK → User | Installer |
| `integration_type` | FK → IntegrationTypeModel | Target integration |
| `status` | enum | `downloading` → `oauth_setup` → `completed` / `failed` |
| `progress` | int | 0–100 percentage |
| `oauth_state` | string | CSRF protection token (unique) |
| `error_message` | text | Failure reason |
| `retry_count` | int | Max 3 retries |
| `completed_at` | datetime | Completion timestamp |

---

### AutomationTemplate

Pre-configured workflow blueprints attached to an `IntegrationTypeModel`. Instantiated automatically when a user installs an integration.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `integration_type` | FK → IntegrationTypeModel | Parent integration |
| `name` | string | Template name |
| `trigger_type` | enum | `scheduled`, `event_driven`, `manual` |
| `trigger_config` | JSON | Schedule/event configuration |
| `steps` | JSON | Array of `{action_type, integration_type_id, parameters}` |
| `is_enabled_by_default` | bool | Auto-enable on install |

---

### Workflow

A user's workflow instance, either created from a template or custom-built.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | FK → User | Owner |
| `automation_template` | FK → AutomationTemplate (nullable) | Source template |
| `is_custom` | bool | User-created vs template-derived |
| `name` | string | Display name |
| `trigger_config` | JSON | Trigger settings |
| `steps` | JSON | `[{action_type, integration_type_id, parameters, requires_confirmation}]` |
| `is_active` | bool | Enabled/disabled |
| `last_modified_by_twin` | bool | Whether Twin made the last change |
| `twin_modification_count` | int | Total Twin modifications |

---

### WorkflowExecution

Audit record for each workflow run.

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `pending`, `running`, `completed`, `failed`, `awaiting_confirmation`, `cancelled` |
| `permission_flag` | bool | Whether permission was granted |
| `cognitive_blend` | int | Blend value used (0–100) |
| `is_twin_generated` | bool | Twin-initiated vs user-initiated |
| `step_results` | JSON | Per-step outcomes |
| `error_message` / `error_step` | text/int | Failure details |

---

### WorkflowChangeHistory

Immutable audit log of every workflow modification.

| Field | Type | Description |
|-------|------|-------------|
| `modified_by_twin` | bool | Twin vs user change |
| `cognitive_blend_value` | int | Blend at time of Twin change |
| `changes_made` | JSON | `{field: {before, after}}` diff |
| `reasoning` | text | Twin's explanation for the change |
| `permission_flag` | bool | Permission granted |
| `required_confirmation` | bool | Whether confirmation was needed |

---

## API Endpoints

Base path: `/api/v1/`

### Integration Types (Marketplace)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/integrations/types/` | User | List active integration types |
| `GET` | `/integrations/types/{id}/` | User | Get type detail + install status |
| `GET` | `/integrations/types/categories/` | User | Category counts |
| `POST` | `/integrations/types/` | Admin | Create new integration type |
| `PATCH` | `/integrations/types/{id}/` | Admin | Update integration type |
| `DELETE` | `/integrations/types/{id}/` | Admin | Delete (blocked if installs exist) |

Query params for `GET /integrations/types/`:
- `category` — filter by category slug
- `search` — search name/description
- `page`, `page_size` — pagination (default 20, max 100)

---

### Installation

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/integrations/install/` | User | Start installation (Phase 1) |
| `GET` | `/integrations/install/{session_id}/progress/` | User | Poll installation progress |
| `GET` | `/integrations/install/oauth/callback/` | User | OAuth callback handler |
| `DELETE` | `/integrations/{id}/uninstall/` | User | Uninstall integration |
| `GET` | `/integrations/installed/` | User | List user's installed integrations |

Rate limit: 10 installations per user per hour.

---

### Workflows

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/automations/` | User | List workflows (grouped by integration) |
| `POST` | `/automations/` | User | Create custom workflow |
| `GET` | `/automations/{id}/` | User | Get workflow detail |
| `PATCH` | `/automations/{id}/` | User/Twin | Update workflow |
| `DELETE` | `/automations/{id}/` | User | Delete workflow |
| `GET` | `/automations/{id}/change_history/` | User | Full change audit log |

Query params for `GET /automations/`:
- `integration_type_id` — filter by integration
- `is_enabled` — `true`/`false`
- `is_custom` — `true`/`false`
- `grouped` — `true` (default) returns grouped by integration type

---

### Twin Suggestions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/twin-suggestions/` | User | List suggestions |
| `GET` | `/twin-suggestions/pending/` | User | Pending suggestions only |
| `POST` | `/twin-suggestions/{id}/review/` | User | Approve or reject suggestion |

Review body:
```json
{
  "action": "approve" | "reject",
  "review_notes": "optional"
}
```

---

### OAuth Callbacks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/oauth/callback/` | Browser redirect handler (redirects to dashboard) |
| `GET` | `/oauth/callback/api/` | JSON response handler (for SPAs/mobile) |

---

## Installation Flow

The integration installation is a two-phase OAuth 2.0 flow:

```
1. POST /integrations/install/
   └── Creates InstallationSession (status: downloading)
   └── Generates cryptographic oauth_state (CSRF token)
   └── Returns: { session_id, oauth_url }

2. User redirected to OAuth provider (Google, Slack, etc.)

3. Provider redirects to GET /oauth/callback/?code=...&state=...&session_id=...
   └── Validates oauth_state matches session (CSRF check)
   └── Exchanges authorization code for access + refresh tokens
   └── Encrypts tokens and creates Integration record
   └── Triggers AutomationTemplate instantiation (async)
   └── Session status → completed

4. Frontend polls GET /integrations/install/{session_id}/progress/
   └── Returns { phase, progress (0-100), message }
```

Error handling:
- OAuth provider errors (user cancelled) → session marked failed
- Token exchange failures → logged, session failed, retry available (max 3)
- State mismatch → `OAuthStateValidationError`, session failed immediately

---

## Workflow Execution & Twin Safety

All Twin-initiated workflow modifications enforce these safety rules:

```
Twin wants to modify workflow
        │
        ├── permission_flag == True?  ──No──→ PermissionError (403)
        │
        ├── Fetch cognitive_blend from Twin profile
        │
        ├── cognitive_blend > 80%?  ──Yes──→ Requires user confirmation
        │
        └── Apply changes + create WorkflowChangeHistory record
```

PATCH `/automations/{id}/` supports Twin modification fields:
```json
{
  "modified_by_twin": true,
  "permission_flag": true,
  "cognitive_blend": 75,
  "steps": [...],
  "_reasoning": "Optimized schedule based on user patterns"
}
```

Deleting a template-derived workflow requires `?force=true` query param.

---

## Frontend API Clients

### `lib/api/automation.ts`

Handles workflow CRUD. All functions return typed responses.

```typescript
getWorkflows(filters?)          // → WorkflowGroup[]
createWorkflow(data)            // → Workflow
updateWorkflow(id, updates)     // → Workflow
deleteWorkflow(id)              // → void
toggleWorkflow(id, isEnabled)   // → Workflow (shorthand for updateWorkflow)
```

`getWorkflows()` returns workflows grouped by integration type:
```typescript
interface WorkflowGroup {
  integration_type: IntegrationType;
  workflows: Workflow[];
}
```

---

### `lib/api/marketplace.ts`

Handles integration discovery and installation lifecycle.

```typescript
getIntegrationTypes(params?)         // → paginated IntegrationType[]
getIntegrationTypeDetail(id)         // → IntegrationType + is_installed + templates
installIntegration(integrationTypeId) // → InstallationSession { session_id, oauth_url }
getInstallationProgress(sessionId)   // → InstallationProgress { phase, progress, message }
uninstallIntegration(integrationId)  // → UninstallResult { success, disabled_workflows }
getInstalledIntegrations()           // → Integration[]
retryInstallation(sessionId)         // → InstallationSession
```

Also exported as `marketplaceApi` namespace for convenience.

---

### `lib/api/twin-automation.ts`

Handles Twin suggestion review and workflow change history.

```typescript
getTwinSuggestions(params?)              // → WorkflowSuggestion[]
approveTwinSuggestion(suggestionId)      // → ApproveSuggestionResponse
rejectTwinSuggestion(suggestionId, reason?) // → RejectSuggestionResponse
getWorkflowChangeHistory(params?)        // → { changes, total, page }
getWorkflowChanges(workflowId)           // → WorkflowChange[]
```

---

## Automation Dashboard UI

Located at `neuro-frontend/src/app/dashboard/automation/page.tsx`.

The page renders workflows grouped by integration type using collapsible `GlassPanel` sections. Each group shows:
- Integration icon + name
- Workflow count and active count
- Expandable list via `WorkflowList` component

State management is local (`useState`) — no global store. All mutations call the API then update local state optimistically.

Key handlers:
- `handleToggleWorkflow` — enable/disable via `toggleWorkflow()`
- `handleEditWorkflow` — opens `WorkflowEditor` modal with selected workflow
- `handleSaveWorkflow` — calls `updateWorkflow()` and syncs local state
- `handleDeleteWorkflow` — confirms then calls `deleteWorkflow()`

Empty state links to `/dashboard/apps` (App Marketplace).

---

## Caching

The `MarketplaceCache` utility manages Redis-backed caches:

| Cache Key | TTL | Content |
|-----------|-----|---------|
| `marketplace:active_types` | 5 min | Active integration types list |
| `marketplace:categories` | 10 min | Category counts |
| `marketplace:user_installed:{user_id}` | 2 min | User's installed integration IDs |
| `oauth_config:{integration_type_id}` | 5 min | OAuth config per type |

Caches are invalidated on:
- Integration type create/update/delete → `invalidate_marketplace_cache()`
- Integration install/uninstall → `invalidate_user_installed_cache(user_id)`

---

## Security

- OAuth tokens encrypted at rest using AES via `TokenEncryption` utility
- OAuth state parameter validated on every callback (CSRF protection)
- Token revocation attempted on uninstall (best-effort, non-blocking)
- All Twin actions require `permission_flag=True`
- Cognitive blend > 80% requires explicit user confirmation
- Every workflow change logged to `WorkflowChangeHistory` with full diff
- Integration type deletion blocked if any user has it installed
- Rate limiting: 10 installs/hour per user (`InstallationRateThrottle`)
- Admin-only endpoints for creating/modifying integration types
