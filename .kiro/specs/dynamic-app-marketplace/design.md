# Design Document: Dynamic App Marketplace

## Overview

The Dynamic App Marketplace transforms NeuroTwin's integration system from a hardcoded enum-based architecture into a flexible, database-driven marketplace. This design enables administrators to add new integration types through the Django admin interface without code deployments, while providing users with an app store experience for discovering, installing, and managing integrations.

### Key Design Goals

1. **Extensibility**: Enable new integrations without code changes
2. **User Experience**: Provide intuitive app discovery and installation
3. **Security**: Maintain OAuth token encryption and permission controls
4. **Backward Compatibility**: Migrate existing enum-based integrations seamlessly
5. **Automation**: Support pre-configured workflow templates per integration

### System Context

The marketplace sits at the intersection of several NeuroTwin subsystems:
- **Authentication**: JWT-based user authentication for all API endpoints
- **Automation**: Workflow engine that executes actions across integrations
- **Safety**: Permission controls and audit logging for Twin actions
- **Subscription**: Tier-based limits on integration installations

## Architecture

### High-Level Architecture


```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌──────────────────┐              ┌──────────────────────┐    │
│  │  App Marketplace │              │ Automation Dashboard │    │
│  │   (/apps)        │              │   (/automation)      │    │
│  └────────┬─────────┘              └──────────┬───────────┘    │
└───────────┼────────────────────────────────────┼────────────────┘
            │                                    │
            │ REST API (JWT Auth)                │
            │                                    │
┌───────────┼────────────────────────────────────┼────────────────┐
│           │         Backend Layer              │                │
│  ┌────────▼─────────┐              ┌──────────▼───────────┐    │
│  │ Marketplace API  │              │  Automation API      │    │
│  │  - List types    │              │  - List workflows    │    │
│  │  - Install       │              │  - CRUD workflows    │    │
│  │  - Uninstall     │              │  - Execute           │    │
│  └────────┬─────────┘              └──────────┬───────────┘    │
│           │                                    │                │
│  ┌────────▼────────────────────────────────────▼───────────┐   │
│  │              Service Layer                              │   │
│  │  - IntegrationTypeService                               │   │
│  │  - AppMarketplaceService                                │   │
│  │  - InstallationService                                  │   │
│  │  - AutomationTemplateService                            │   │
│  │  - WorkflowEngine (existing)                            │   │
│  └────────┬────────────────────────────────────────────────┘   │
│           │                                                     │
│  ┌────────▼────────────────────────────────────────────────┐   │
│  │              Data Layer                                 │   │
│  │  - IntegrationType (new)                                │   │
│  │  - Integration (modified)                               │   │
│  │  - AutomationTemplate (new)                             │   │
│  │  - InstallationSession (new)                            │   │
│  │  - Workflow (existing)                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Architectural Patterns

1. **Service Layer Pattern**: Business logic isolated in service classes
2. **Repository Pattern**: Data access through model managers and selectors
3. **Adapter Pattern**: OAuth providers abstracted through configuration
4. **Template Method Pattern**: Installation flow with customizable OAuth steps

### Key Architectural Decisions



**Decision 1: Database Model vs Enum**
- **Choice**: Replace IntegrationType enum with database model
- **Rationale**: Enables runtime extensibility without code deployments
- **Trade-off**: Slightly more complex queries, but gains flexibility

**Decision 2: Two-Phase Installation**
- **Choice**: Split installation into "downloading" and "oauth_setup" phases
- **Rationale**: Provides clear user feedback and separates concerns
- **Trade-off**: More complex state management, but better UX

**Decision 3: Template-Based Automation**
- **Choice**: Pre-configure workflows via AutomationTemplate model
- **Rationale**: Reduces user setup friction, provides best practices
- **Trade-off**: Requires admin configuration, but improves onboarding

**Decision 4: Polling vs WebSocket**
- **Choice**: Use HTTP polling for installation progress
- **Rationale**: Simpler implementation, adequate for 2-3 second installs
- **Trade-off**: More HTTP requests, but avoids WebSocket complexity

## Components and Interfaces

### Backend Components

#### 1. IntegrationTypeService

Manages CRUD operations for integration types (admin-only).

```python
class IntegrationTypeService:
    """Service for managing integration types."""
    
    @staticmethod
    def create_integration_type(
        type_identifier: str,
        name: str,
        icon: File,
        description: str,
        category: str,
        oauth_config: dict
    ) -> IntegrationType:
        """Create a new integration type with validation."""
        pass
    
    @staticmethod
    def update_integration_type(
        integration_type_id: UUID,
        **updates
    ) -> IntegrationType:
        """Update an existing integration type."""
        pass
    
    @staticmethod
    def deactivate_integration_type(
        integration_type_id: UUID
    ) -> IntegrationType:
        """Set integration type to inactive."""
        pass
    
    @staticmethod
    def validate_type_identifier(identifier: str) -> bool:
        """Validate kebab-case format and uniqueness."""
        pass
```



#### 2. AppMarketplaceService

Handles app discovery, filtering, and search.

```python
class AppMarketplaceService:
    """Service for app marketplace operations."""
    
    @staticmethod
    def list_integration_types(
        user: User,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> QuerySet[IntegrationType]:
        """List active integration types with filtering."""
        pass
    
    @staticmethod
    def get_integration_type_detail(
        integration_type_id: UUID,
        user: User
    ) -> dict:
        """Get detailed integration type info with installation status."""
        pass
    
    @staticmethod
    def is_installed(
        user: User,
        integration_type_id: UUID
    ) -> bool:
        """Check if user has installed this integration type."""
        pass
    
    @staticmethod
    def get_categories_with_counts() -> dict[str, int]:
        """Get all categories with active integration counts."""
        pass
```

#### 3. InstallationService

Manages the two-phase installation process.

```python
class InstallationService:
    """Service for integration installation."""
    
    @staticmethod
    def start_installation(
        user: User,
        integration_type_id: UUID
    ) -> InstallationSession:
        """Start Phase 1: Create installation session."""
        pass
    
    @staticmethod
    def get_oauth_authorization_url(
        session_id: UUID
    ) -> str:
        """Get OAuth URL for Phase 2."""
        pass
    
    @staticmethod
    async def complete_oauth_flow(
        session_id: UUID,
        authorization_code: str,
        state: str
    ) -> Integration:
        """Exchange code for tokens and create Integration."""
        pass
    
    @staticmethod
    def get_installation_progress(
        session_id: UUID
    ) -> dict:
        """Get current installation status and progress."""
        pass
    
    @staticmethod
    def uninstall_integration(
        user: User,
        integration_id: UUID
    ) -> None:
        """Remove integration and disable dependent workflows."""
        pass
```



#### 4. AutomationTemplateService

Manages automation templates and workflow instantiation.

```python
class AutomationTemplateService:
    """Service for automation template management."""
    
    @staticmethod
    def create_template(
        integration_type_id: UUID,
        name: str,
        description: str,
        trigger_type: str,
        trigger_config: dict,
        steps: list[dict],
        is_enabled_by_default: bool = False
    ) -> AutomationTemplate:
        """Create a new automation template."""
        pass
    
    @staticmethod
    def instantiate_templates_for_user(
        user: User,
        integration: Integration
    ) -> list[Workflow]:
        """Create workflow instances from templates."""
        pass
    
    @staticmethod
    def parse_template_variables(
        template_config: dict,
        user: User,
        integration: Integration
    ) -> dict:
        """Replace template variables with actual values."""
        pass
    
    @staticmethod
    def validate_template_structure(template: dict) -> bool:
        """Validate template JSON structure."""
        pass
```

#### 5. WorkflowService (Enhanced)

Extended workflow management with Twin modification support.

```python
class WorkflowService:
    """Service for workflow management."""
    
    @staticmethod
    def create_workflow(
        user: User,
        name: str,
        trigger_config: dict,
        steps: list[dict],
        is_twin_generated: bool = False
    ) -> Workflow:
        """Create a new workflow with validation."""
        pass
    
    @staticmethod
    def update_workflow(
        workflow_id: UUID,
        user: User,
        updates: dict,
        modified_by_twin: bool = False,
        cognitive_blend: int = 50,
        permission_flag: bool = False
    ) -> Workflow:
        """Update workflow with Twin safety checks."""
        pass
    
    @staticmethod
    def validate_workflow_integrations(
        user: User,
        steps: list[dict]
    ) -> tuple[bool, list[str]]:
        """Validate all referenced integrations are installed."""
        pass
    
    @staticmethod
    def disable_workflows_for_integration(
        user: User,
        integration_type_id: UUID
    ) -> int:
        """Disable workflows that depend on an integration."""
        pass
```



### Frontend Components

#### 1. AppMarketplace Page

Main marketplace interface at `/dashboard/apps`.

```typescript
interface AppMarketplaceProps {
  // No props - fetches data internally
}

interface IntegrationType {
  id: string;
  type: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  isInstalled: boolean;
  automationTemplateCount: number;
}

// Component structure:
// - Search bar with debounced input
// - Category filter buttons
// - Grid of AppCard components
// - AppDetailModal for detailed view
```

#### 2. AppCard Component

Displays individual integration type in marketplace.

```typescript
interface AppCardProps {
  integrationType: IntegrationType;
  onInstall: (id: string) => void;
  onViewDetails: (id: string) => void;
}

// Visual elements:
// - Icon (SVG/PNG)
// - Name and category badge
// - Brief description (truncated)
// - Install button or "Installed" badge
```

#### 3. InstallationProgress Component

Two-phase progress indicator during installation.

```typescript
interface InstallationProgressProps {
  sessionId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

interface InstallationStatus {
  phase: 'downloading' | 'oauth_setup' | 'completed' | 'failed';
  progress: number; // 0-100
  message: string;
  errorMessage?: string;
}

// Behavior:
// - Polls /api/v1/integrations/install/{sessionId}/progress every 500ms
// - Shows animated progress bar
// - Redirects to OAuth when phase changes to oauth_setup
// - Displays success/error messages
```

#### 4. AutomationDashboard Page

Workflow management interface at `/dashboard/automation`.

```typescript
interface AutomationDashboardProps {
  // No props - fetches data internally
}

interface WorkflowGroup {
  integrationType: IntegrationType;
  workflows: Workflow[];
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  isEnabled: boolean;
  lastExecutedAt?: string;
  isCustom: boolean;
  stepCount: number;
}

// Component structure:
// - List of installed integrations
// - Expandable sections per integration
// - WorkflowList component for each section
// - WorkflowEditor modal
```



#### 5. WorkflowEditor Component

Edit workflow configuration.

```typescript
interface WorkflowEditorProps {
  workflowId: string;
  onSave: (workflow: Workflow) => void;
  onCancel: () => void;
}

interface WorkflowStep {
  actionType: string;
  integrationTypeId: string;
  parameters: Record<string, any>;
  requiresConfirmation: boolean;
}

// Features:
// - Edit workflow name and description
// - Configure trigger settings
// - Add/remove/reorder steps
// - Validate integration availability
// - Save/cancel actions
```

### API Endpoints

#### Integration Type Endpoints

```
GET /api/v1/integrations/types/
  Query params: category, search, page, page_size
  Response: Paginated list of IntegrationType
  Auth: JWT required

GET /api/v1/integrations/types/{id}/
  Response: Detailed IntegrationType with templates
  Auth: JWT required

POST /api/v1/integrations/types/ (Admin only)
  Body: IntegrationType data
  Response: Created IntegrationType
  Auth: JWT + admin required
```

#### Installation Endpoints

```
POST /api/v1/integrations/install/
  Body: { integration_type_id: UUID }
  Response: { session_id: UUID, oauth_url: string }
  Auth: JWT required

GET /api/v1/integrations/install/{session_id}/progress/
  Response: { phase, progress, message, error_message }
  Auth: JWT required

GET /api/v1/integrations/oauth/callback/
  Query params: code, state, session_id
  Response: Redirect to dashboard with success/error
  Auth: State validation

DELETE /api/v1/integrations/{id}/uninstall/
  Response: { success: bool, disabled_workflows: int }
  Auth: JWT required

GET /api/v1/integrations/installed/
  Response: List of user's Integration records
  Auth: JWT required
```

#### Automation Endpoints

```
GET /api/v1/automations/
  Query params: integration_type_id, is_enabled
  Response: List of Workflow grouped by integration
  Auth: JWT required

POST /api/v1/automations/
  Body: { name, trigger_config, steps }
  Response: Created Workflow
  Auth: JWT required

PATCH /api/v1/automations/{id}/
  Body: Partial workflow updates
  Response: Updated Workflow
  Auth: JWT required

DELETE /api/v1/automations/{id}/
  Response: { success: bool }
  Auth: JWT required
```



## Data Models

### 1. IntegrationType Model

Replaces the hardcoded enum with a database model.

```python
class IntegrationCategory(models.TextChoices):
    """Categories for organizing integration types."""
    COMMUNICATION = 'communication', 'Communication'
    PRODUCTIVITY = 'productivity', 'Productivity'
    CRM = 'crm', 'CRM'
    CALENDAR = 'calendar', 'Calendar'
    DOCUMENTS = 'documents', 'Documents'
    VIDEO_CONFERENCING = 'video_conferencing', 'Video Conferencing'
    OTHER = 'other', 'Other'


class IntegrationType(models.Model):
    """
    Dynamic integration type model.
    
    Replaces hardcoded IntegrationType enum to enable
    runtime addition of new integration types.
    
    Requirements: 1.1-1.7, 2.1-2.6
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Type identifier (kebab-case, unique)
    type = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique identifier in kebab-case (e.g., "gmail", "slack")'
    )
    
    # Display information
    name = models.CharField(
        max_length=255,
        help_text='Human-readable name (e.g., "Gmail", "Slack")'
    )
    icon = models.FileField(
        upload_to='integration_icons/',
        help_text='SVG or PNG icon (max 500KB)'
    )
    description = models.TextField(
        help_text='Full description of the integration'
    )
    brief_description = models.CharField(
        max_length=200,
        help_text='Short description for card display'
    )
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=IntegrationCategory.choices,
        default=IntegrationCategory.OTHER,
        db_index=True,
        help_text='Category for filtering and organization'
    )
    
    # OAuth configuration (encrypted)
    oauth_config = models.JSONField(
        default=dict,
        help_text='OAuth 2.0 configuration including client_id, '
                  'client_secret (encrypted), authorization_url, '
                  'token_url, scopes'
    )
    
    # Default permissions
    default_permissions = models.JSONField(
        default=dict,
        help_text='Default permission settings for new installations'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this integration type is visible in marketplace'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_integration_types'
    )
    
    class Meta:
        db_table = 'integration_types'
        verbose_name = 'integration type'
        verbose_name_plural = 'integration types'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['is_active', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type})"
    
    def clean(self):
        """Validate type identifier format."""
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', self.type):
            raise ValidationError(
                'Type must be in kebab-case format (lowercase, hyphens only)'
            )
    
    @property
    def oauth_client_id(self) -> str:
        """Get OAuth client ID."""
        return self.oauth_config.get('client_id', '')
    
    @property
    def oauth_client_secret(self) -> str:
        """Get decrypted OAuth client secret."""
        encrypted = self.oauth_config.get('client_secret_encrypted', '')
        if encrypted:
            return TokenEncryption.decrypt(base64.b64decode(encrypted))
        return ''
    
    def set_oauth_client_secret(self, secret: str):
        """Encrypt and store OAuth client secret."""
        if secret:
            encrypted = TokenEncryption.encrypt(secret)
            self.oauth_config['client_secret_encrypted'] = \
                base64.b64encode(encrypted).decode()
    
    @property
    def oauth_scopes(self) -> list[str]:
        """Get OAuth scopes as list."""
        scopes = self.oauth_config.get('scopes', [])
        if isinstance(scopes, str):
            return [s.strip() for s in scopes.split(',')]
        return scopes
```



### 2. Integration Model (Modified)

Updated to reference IntegrationType model instead of enum.

```python
class Integration(models.Model):
    """
    Integration model for connected applications.
    
    Modified to use ForeignKey to IntegrationType instead of enum.
    
    Requirements: 5.1-5.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    
    # Changed from CharField with choices to ForeignKey
    integration_type = models.ForeignKey(
        IntegrationType,
        on_delete=models.PROTECT,  # Prevent deletion if installed
        related_name='installations',
        db_index=True,
        help_text='The type of integration'
    )
    
    # Encrypted OAuth tokens (unchanged)
    oauth_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth access token'
    )
    refresh_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text='Encrypted OAuth refresh token'
    )
    
    # OAuth configuration (unchanged)
    scopes = models.JSONField(
        default=list,
        help_text='OAuth scopes granted for this integration'
    )
    
    # Integration configuration (unchanged)
    steering_rules = models.JSONField(
        default=dict,
        help_text='Rules defining allowed actions for this integration'
    )
    permissions = models.JSONField(
        default=dict,
        help_text='Permission settings for this integration'
    )
    
    # Token expiration (unchanged)
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When the OAuth token expires'
    )
    
    # Status (unchanged)
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this integration is active'
    )
    
    # Timestamps (unchanged)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'integrations'
        verbose_name = 'integration'
        verbose_name_plural = 'integrations'
        unique_together = [['user', 'integration_type']]
        indexes = [
            models.Index(fields=['user', 'integration_type']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['integration_type', 'is_active']),
            models.Index(fields=['token_expires_at']),
        ]
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.email}: {self.integration_type.name} ({status})"
    
    # Property methods remain the same (oauth_token, refresh_token, etc.)
```



### 3. AutomationTemplate Model

Pre-configured workflow templates for integration types.

```python
class TriggerType(models.TextChoices):
    """Types of workflow triggers."""
    SCHEDULED = 'scheduled', 'Scheduled'
    EVENT_DRIVEN = 'event_driven', 'Event-Driven'
    MANUAL = 'manual', 'Manual'


class AutomationTemplate(models.Model):
    """
    Automation template for integration types.
    
    Defines pre-configured workflows that are instantiated
    when a user installs an integration type.
    
    Requirements: 6.1-6.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    integration_type = models.ForeignKey(
        IntegrationType,
        on_delete=models.CASCADE,
        related_name='automation_templates',
        help_text='The integration type this template belongs to'
    )
    
    # Template information
    name = models.CharField(
        max_length=255,
        help_text='Template name'
    )
    description = models.TextField(
        help_text='Description of what this automation does'
    )
    
    # Trigger configuration
    trigger_type = models.CharField(
        max_length=50,
        choices=TriggerType.choices,
        help_text='Type of trigger for this automation'
    )
    trigger_config = models.JSONField(
        default=dict,
        help_text='Trigger configuration (schedule, event filters, etc.)'
    )
    
    # Workflow steps
    steps = models.JSONField(
        default=list,
        help_text='Array of workflow steps with action_type, '
                  'integration_type_id, parameters'
    )
    
    # Default state
    is_enabled_by_default = models.BooleanField(
        default=False,
        help_text='Whether workflows created from this template '
                  'should be enabled by default'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this template is active'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_automation_templates'
    )
    
    class Meta:
        db_table = 'automation_templates'
        verbose_name = 'automation template'
        verbose_name_plural = 'automation templates'
        ordering = ['integration_type', 'name']
        indexes = [
            models.Index(fields=['integration_type', 'is_active']),
        ]
    
    def __str__(self) -> str:
        return f"{self.integration_type.name}: {self.name}"
    
    def get_steps_list(self) -> list[dict]:
        """Get steps as list."""
        if isinstance(self.steps, list):
            return self.steps
        return []
    
    def validate_steps(self) -> tuple[bool, list[str]]:
        """Validate step structure."""
        errors = []
        steps = self.get_steps_list()
        
        if not steps:
            errors.append('At least one step is required')
        
        for i, step in enumerate(steps):
            if 'action_type' not in step:
                errors.append(f'Step {i}: missing action_type')
            if 'integration_type_id' not in step:
                errors.append(f'Step {i}: missing integration_type_id')
        
        return len(errors) == 0, errors
```



### 4. InstallationSession Model

Tracks installation progress for real-time feedback.

```python
class InstallationStatus(models.TextChoices):
    """Status of an installation session."""
    DOWNLOADING = 'downloading', 'Downloading'
    OAUTH_SETUP = 'oauth_setup', 'OAuth Setup'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class InstallationSession(models.Model):
    """
    Installation session for tracking progress.
    
    Manages the two-phase installation process with
    real-time progress updates.
    
    Requirements: 4.1-4.11, 11.1-11.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    integration_type = models.ForeignKey(
        IntegrationType,
        on_delete=models.CASCADE,
        related_name='installation_sessions'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=50,
        choices=InstallationStatus.choices,
        default=InstallationStatus.DOWNLOADING,
        db_index=True,
        help_text='Current installation phase'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    
    # OAuth state for CSRF protection
    oauth_state = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='OAuth state parameter for validation'
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if installation failed'
    )
    retry_count = models.IntegerField(
        default=0,
        help_text='Number of retry attempts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When installation completed or failed'
    )
    
    class Meta:
        db_table = 'installation_sessions'
        verbose_name = 'installation session'
        verbose_name_plural = 'installation sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.integration_type.name} - {self.status}"
    
    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.status in [
            InstallationStatus.COMPLETED,
            InstallationStatus.FAILED
        ]
    
    @property
    def is_expired(self) -> bool:
        """Check if session is older than 24 hours."""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.created_at > timedelta(hours=24)
    
    def increment_retry(self):
        """Increment retry counter."""
        self.retry_count += 1
        self.save(update_fields=['retry_count', 'updated_at'])
    
    @property
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.retry_count < 3
```



### 5. Workflow Model (Enhanced)

Extended with template tracking and Twin modification history.

```python
class Workflow(models.Model):
    """
    Workflow model for automated task execution.
    
    Enhanced to track template origin and Twin modifications.
    
    Requirements: 7.1-7.9, 8.1-8.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflows'
    )
    
    # Template tracking (new)
    automation_template = models.ForeignKey(
        'AutomationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_instances',
        help_text='Template this workflow was created from (if any)'
    )
    is_custom = models.BooleanField(
        default=False,
        help_text='Whether this is a custom user-created workflow'
    )
    
    # Workflow information
    name = models.CharField(
        max_length=255,
        help_text='Human-readable name for the workflow'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Description of what this workflow does'
    )
    
    # Trigger configuration
    trigger_config = models.JSONField(
        default=dict,
        help_text='Configuration for when the workflow triggers'
    )
    
    # Workflow steps as JSON array
    steps = models.JSONField(
        default=list,
        help_text='List of workflow steps to execute'
    )
    
    # Status
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this workflow is enabled'
    )
    
    # Twin modification tracking (new)
    last_modified_by_twin = models.BooleanField(
        default=False,
        help_text='Whether last modification was by Twin'
    )
    twin_modification_count = models.IntegerField(
        default=0,
        help_text='Number of times Twin has modified this workflow'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this workflow was last executed'
    )
    
    class Meta:
        db_table = 'workflows'
        verbose_name = 'workflow'
        verbose_name_plural = 'workflows'
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['automation_template']),
        ]
    
    def __str__(self) -> str:
        status = 'enabled' if self.is_enabled else 'disabled'
        return f"{self.name} ({status})"
    
    def get_integration_types_used(self) -> list[UUID]:
        """Get list of integration type IDs used in steps."""
        integration_types = set()
        for step in self.get_steps_list():
            if 'integration_type_id' in step:
                integration_types.add(step['integration_type_id'])
        return list(integration_types)
```



### 6. WorkflowChangeHistory Model

Audit trail for workflow modifications.

```python
class WorkflowChangeHistory(models.Model):
    """
    Change history for workflow modifications.
    
    Tracks all changes to workflows with author attribution
    and reasoning for Twin modifications.
    
    Requirements: 8.2, 8.6, 8.7
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='change_history'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workflow_changes'
    )
    
    # Change tracking
    modified_by_twin = models.BooleanField(
        default=False,
        help_text='Whether this change was made by Twin'
    )
    cognitive_blend_value = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value at time of Twin modification'
    )
    
    # Change details
    changes_made = models.JSONField(
        default=dict,
        help_text='Dictionary of field changes (before/after)'
    )
    reasoning = models.TextField(
        blank=True,
        default='',
        help_text='Explanation for the change (especially for Twin mods)'
    )
    
    # Permission tracking
    permission_flag = models.BooleanField(
        default=False,
        help_text='Whether permission was granted for this change'
    )
    required_confirmation = models.BooleanField(
        default=False,
        help_text='Whether user confirmation was required'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'workflow_change_history'
        verbose_name = 'workflow change'
        verbose_name_plural = 'workflow change history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', 'created_at']),
            models.Index(fields=['user', 'modified_by_twin']),
        ]
    
    def __str__(self) -> str:
        author = 'Twin' if self.modified_by_twin else 'User'
        return f"{self.workflow.name} - {author} - {self.created_at}"
```



## Data Migration Strategy

### Migration Plan

The migration from enum-based to database-driven integration types must preserve all existing data and maintain backward compatibility.

#### Phase 1: Create New Models

```python
# Migration: 0001_create_integration_type_model.py

from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('automation', '0001_initial'),  # Previous migration
    ]
    
    operations = [
        # Create IntegrationType model
        migrations.CreateModel(
            name='IntegrationType',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4)),
                ('type', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('icon', models.FileField(upload_to='integration_icons/')),
                ('description', models.TextField()),
                ('brief_description', models.CharField(max_length=200)),
                ('category', models.CharField(max_length=50)),
                ('oauth_config', models.JSONField(default=dict)),
                ('default_permissions', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='integrationType',
            index=models.Index(fields=['is_active', 'category']),
        ),
    ]
```

#### Phase 2: Populate Integration Types

```python
# Migration: 0002_populate_integration_types.py

from django.db import migrations

def populate_integration_types(apps, schema_editor):
    """Migrate enum values to database records."""
    IntegrationType = apps.get_model('automation', 'IntegrationType')
    
    # Map enum values to integration type records
    integration_types = [
        {
            'type': 'whatsapp',
            'name': 'WhatsApp',
            'category': 'communication',
            'description': 'Connect your WhatsApp account for messaging automation',
            'brief_description': 'Messaging automation',
        },
        {
            'type': 'telegram',
            'name': 'Telegram',
            'category': 'communication',
            'description': 'Connect your Telegram account for messaging automation',
            'brief_description': 'Messaging automation',
        },
        {
            'type': 'slack',
            'name': 'Slack',
            'category': 'communication',
            'description': 'Connect your Slack workspace for team communication',
            'brief_description': 'Team communication',
        },
        {
            'type': 'gmail',
            'name': 'Gmail',
            'category': 'communication',
            'description': 'Connect your Gmail account for email automation',
            'brief_description': 'Email automation',
        },
        {
            'type': 'outlook',
            'name': 'Outlook',
            'category': 'communication',
            'description': 'Connect your Outlook account for email automation',
            'brief_description': 'Email automation',
        },
        {
            'type': 'google_calendar',
            'name': 'Google Calendar',
            'category': 'calendar',
            'description': 'Connect your Google Calendar for scheduling automation',
            'brief_description': 'Calendar management',
        },
        {
            'type': 'google_docs',
            'name': 'Google Docs',
            'category': 'documents',
            'description': 'Connect Google Docs for document automation',
            'brief_description': 'Document automation',
        },
        {
            'type': 'microsoft_office',
            'name': 'Microsoft Office',
            'category': 'documents',
            'description': 'Connect Microsoft Office for document automation',
            'brief_description': 'Document automation',
        },
        {
            'type': 'zoom',
            'name': 'Zoom',
            'category': 'video_conferencing',
            'description': 'Connect Zoom for meeting automation',
            'brief_description': 'Video meetings',
        },
        {
            'type': 'google_meet',
            'name': 'Google Meet',
            'category': 'video_conferencing',
            'description': 'Connect Google Meet for meeting automation',
            'brief_description': 'Video meetings',
        },
        {
            'type': 'crm',
            'name': 'CRM',
            'category': 'crm',
            'description': 'Connect your CRM system for customer management',
            'brief_description': 'Customer management',
        },
    ]
    
    for it_data in integration_types:
        IntegrationType.objects.create(
            **it_data,
            is_active=True,
            oauth_config={},
            default_permissions={}
        )

def reverse_populate(apps, schema_editor):
    """Remove all integration types."""
    IntegrationType = apps.get_model('automation', 'IntegrationType')
    IntegrationType.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('automation', '0001_create_integration_type_model'),
    ]
    
    operations = [
        migrations.RunPython(populate_integration_types, reverse_populate),
    ]
```



#### Phase 3: Add Foreign Key to Integration

```python
# Migration: 0003_add_integration_type_fk.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('automation', '0002_populate_integration_types'),
    ]
    
    operations = [
        # Add new foreign key field (nullable initially)
        migrations.AddField(
            model_name='integration',
            name='integration_type_fk',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='installations',
                to='automation.integrationType'
            ),
        ),
    ]
```

#### Phase 4: Migrate Existing Data

```python
# Migration: 0004_migrate_integration_data.py

from django.db import migrations

def migrate_integration_data(apps, schema_editor):
    """Map existing Integration records to IntegrationType."""
    Integration = apps.get_model('automation', 'Integration')
    IntegrationType = apps.get_model('automation', 'IntegrationType')
    
    # Create mapping from old enum values to new records
    type_mapping = {}
    for it in IntegrationType.objects.all():
        type_mapping[it.type] = it
    
    # Update all Integration records
    for integration in Integration.objects.all():
        old_type = integration.type  # CharField with enum value
        if old_type in type_mapping:
            integration.integration_type_fk = type_mapping[old_type]
            integration.save(update_fields=['integration_type_fk'])

def reverse_migration(apps, schema_editor):
    """Clear foreign key references."""
    Integration = apps.get_model('automation', 'Integration')
    Integration.objects.all().update(integration_type_fk=None)

class Migration(migrations.Migration):
    dependencies = [
        ('automation', '0003_add_integration_type_fk'),
    ]
    
    operations = [
        migrations.RunPython(migrate_integration_data, reverse_migration),
    ]
```

#### Phase 5: Switch to Foreign Key

```python
# Migration: 0005_switch_to_foreign_key.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('automation', '0004_migrate_integration_data'),
    ]
    
    operations = [
        # Make foreign key non-nullable
        migrations.AlterField(
            model_name='integration',
            name='integration_type_fk',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='installations',
                to='automation.integrationType'
            ),
        ),
        # Rename field
        migrations.RenameField(
            model_name='integration',
            old_name='integration_type_fk',
            new_name='integration_type',
        ),
        # Remove old CharField
        migrations.RemoveField(
            model_name='integration',
            name='type',
        ),
        # Update unique_together constraint
        migrations.AlterUniqueTogether(
            name='integration',
            unique_together={('user', 'integration_type')},
        ),
    ]
```

### Rollback Strategy

Each migration is reversible:
1. Phase 5 reverse: Restore CharField, copy FK back to CharField
2. Phase 4 reverse: Clear FK references
3. Phase 3 reverse: Remove FK field
4. Phase 2 reverse: Delete IntegrationType records
5. Phase 1 reverse: Drop IntegrationType table



## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies and consolidations:

**Redundancy Group 1: Token Encryption**
- Requirements 2.2, 4.7, and 18.1 all specify token encryption
- Consolidated into single property covering all token storage

**Redundancy Group 2: Search and Filtering**
- Requirements 3.4, 3.5, 13.4, and 14.2 cover filtering and search
- Consolidated into comprehensive search/filter property

**Redundancy Group 3: Installation Status Transitions**
- Requirements 4.3, 11.3, 11.4, 11.5 cover status transitions
- Consolidated into state machine property

**Redundancy Group 4: Workflow Validation**
- Requirements 7.6, 7.8, 8.5 cover workflow validation
- Consolidated into comprehensive validation property

**Redundancy Group 5: Audit Logging**
- Requirements 8.2, 8.7, 15.6, 18.6 cover logging
- Consolidated into comprehensive audit logging property

### Property 1: Type Identifier Validation

For any string, if it is used as an integration type identifier, then it must match the kebab-case pattern (lowercase letters, numbers, and hyphens only, no leading/trailing hyphens).

**Validates: Requirements 1.2**

### Property 2: Icon File Validation

For any uploaded file intended as an integration type icon, the system shall accept it if and only if it is in SVG or PNG format and has a file size of 500KB or less.

**Validates: Requirements 1.3**

### Property 3: Inactive Integration Type Hiding

For any integration type, when its is_active field is set to false, it shall not appear in marketplace queries, but all existing user installations of that type shall remain in the database.

**Validates: Requirements 1.5**



### Property 4: Timestamp Field Population

For any integration type record, when it is created or updated, the system shall automatically populate created_at and updated_at timestamp fields with the current time.

**Validates: Requirements 1.6**

### Property 5: Protected Deletion

For any integration type, if one or more users have installed it (Integration records exist), then attempting to delete that integration type shall fail with a protection error.

**Validates: Requirements 1.7**

### Property 6: Token Encryption Round-Trip

For any OAuth token (access_token or refresh_token), when it is stored in the database, it shall be encrypted using Fernet symmetric encryption, and when retrieved, decryption shall produce the original token value.

**Validates: Requirements 2.2, 4.7, 18.1**

### Property 7: HTTPS URL Validation

For any OAuth configuration, the authorization_url and token_url fields shall be valid HTTPS URLs (not HTTP or other protocols).

**Validates: Requirements 2.3, 18.3**

### Property 8: OAuth Scope Format Parsing

For any OAuth scope configuration, the system shall correctly parse both comma-separated string format ("scope1,scope2,scope3") and JSON array format (["scope1", "scope2", "scope3"]) into the same list of scopes.

**Validates: Requirements 2.4**

### Property 9: OAuth Config Round-Trip

For any custom OAuth parameters stored as JSON in the oauth_config field, serializing then deserializing shall produce an equivalent configuration structure.

**Validates: Requirements 2.5**

### Property 10: Active-Only Marketplace Display

For any marketplace query, the returned integration types shall include only those where is_active equals true.

**Validates: Requirements 3.3, 10.1**

### Property 11: Search and Filter Correctness

For any search term and category filter, the returned integration types shall satisfy all of the following:
- If category filter is applied, all results belong to that category
- If search term is provided, all results contain the search term (case-insensitive) in either name or description
- All results have is_active equals true

**Validates: Requirements 3.4, 3.5, 10.2, 13.4, 14.2**

### Property 12: Installation Status Detection

For any user and integration type, the system shall correctly identify whether the user has installed that integration type by checking for an Integration record with matching user_id and integration_type_id.

**Validates: Requirements 3.8**

### Property 13: Installation State Machine

For any installation session, status transitions shall follow this state machine:
- Initial state: "downloading"
- Valid transitions: downloading → oauth_setup → completed
- Valid transitions: downloading → failed, oauth_setup → failed
- Invalid: Any transition from completed or failed states
- Progress shall be 0-100 and monotonically increasing within a phase

**Validates: Requirements 4.3, 11.1, 11.3, 11.4, 11.5**

### Property 14: Integration Record Creation

For any successful installation (token storage succeeds), the system shall create an Integration record with user_id, integration_type_id, encrypted tokens, and default permissions from the integration type.

**Validates: Requirements 4.8, 5.2, 12.2**

### Property 15: Template Instantiation

For any integration type with N automation templates, when a user installs that integration type, the system shall create exactly N workflow instances, one for each template, with is_enabled matching each template's is_enabled_by_default value.

**Validates: Requirements 4.11, 6.3, 6.4**

### Property 16: Multi-User Installation Independence

For any integration type, multiple users shall be able to install it independently, each with their own Integration record and encrypted tokens, without interference.

**Validates: Requirements 5.3**

### Property 17: Uninstallation Cleanup

For any user's integration, when it is uninstalled, the system shall delete the Integration record (including encrypted tokens) and disable all workflows that reference that integration type.

**Validates: Requirements 5.4, 5.5, 18.5**

### Property 18: Uninstallation Protection

For any integration with enabled workflows that depend solely on it, attempting to uninstall without confirmation shall fail with a validation error listing the dependent workflows.

**Validates: Requirements 5.6**

### Property 19: Template Structure Validation

For any automation template, it shall have all required fields (name, description, trigger_type, trigger_config, steps, is_enabled_by_default), and each step shall contain action_type and integration_type_id.

**Validates: Requirements 6.2, 6.6, 16.2, 16.3**

### Property 20: Trigger Type Support

For any automation template, the trigger_type field shall be one of the supported values: "scheduled", "event_driven", or "manual".

**Validates: Requirements 6.5**

### Property 21: Variable Substitution

For any automation template with variable placeholders (e.g., {{user.email}}, {{integration.user_id}}), when instantiated for a specific user and integration, all placeholders shall be replaced with actual values from the user and integration records.

**Validates: Requirements 6.7, 16.4**

### Property 22: Workflow Integration Validation

For any workflow, all integration_type_id references in its steps shall correspond to integration types that the user has installed (Integration records exist).

**Validates: Requirements 7.6, 8.5**

### Property 23: Workflow Step Requirement

For any custom workflow, it shall have at least one step defined in the steps array.

**Validates: Requirements 7.8**

### Property 24: Template Workflow Protection

For any workflow created from an automation template (automation_template field is not null), deletion shall require confirmation, whereas custom workflows (is_custom equals true) can be deleted without confirmation.

**Validates: Requirements 7.9**

### Property 25: Twin Permission Requirement

For any workflow modification initiated by the Twin, the request shall include permission_flag equals true, otherwise the modification shall be rejected.

**Validates: Requirements 8.1, 12.7**

### Property 26: Comprehensive Audit Logging

For any of the following events, the system shall create an audit log entry with timestamp, user_id, and event-specific details:
- Twin-initiated workflow modifications (includes workflow_id, changes_made, cognitive_blend_value)
- Integration installations (includes integration_type_id)
- Integration uninstallations (includes integration_type_id)
- Installation errors (includes integration_type_id, error_type, error_details)

**Validates: Requirements 8.2, 8.7, 15.6, 18.6**

### Property 27: High Blend Confirmation

For any Twin-suggested workflow modification, when the cognitive_blend value exceeds 80%, the system shall require explicit user confirmation before applying the modification.

**Validates: Requirements 8.3**

### Property 28: Twin Suggestion Storage

For any Twin-suggested workflow modification, the system shall store the suggestion with a reasoning explanation field populated before presenting it to the user for review.

**Validates: Requirements 8.6**

### Property 29: Migration Data Preservation

For any existing Integration record before migration, after running the migration to convert from enum to foreign key, an equivalent Integration record shall exist with the same user_id, tokens, and configuration, but referencing the corresponding IntegrationType record.

**Validates: Requirements 9.5, 9.7**

### Property 30: Migration Reversibility

For any database state, running the migration sequence followed by the reverse migration sequence shall restore the original state (round-trip property).

**Validates: Requirements 9.6**

### Property 31: User-Scoped Integration Query

For any user, querying their installed integrations shall return only Integration records where user_id matches that user, never returning other users' integrations.

**Validates: Requirements 10.6**

### Property 32: Workflow Grouping

For any user's workflows, when grouped by integration type, each workflow shall appear in exactly one group corresponding to the integration types referenced in its steps.

**Validates: Requirements 10.7**

### Property 33: Authentication Requirement

For any API endpoint in the marketplace or automation system, requests without valid JWT authentication shall return HTTP 401 Unauthorized.

**Validates: Requirements 10.10**

### Property 34: Session Cleanup

For any installation session, if it is older than 24 hours, it shall be automatically removed from the database during cleanup operations.

**Validates: Requirements 11.6**

### Property 35: Permission Enforcement

For any workflow step execution, if the required permission is not enabled in the Integration's permissions field, the step shall be skipped and a permission_denied event shall be logged.

**Validates: Requirements 12.4, 12.5**

### Property 36: Category Uniqueness

For any integration type, it shall belong to exactly one category from the predefined set: Communication, Productivity, CRM, Calendar, Documents, Video_Conferencing, or Other.

**Validates: Requirements 13.1, 13.5**

### Property 37: Token Refresh on Expiry

For any integration with an expired access_token and a valid refresh_token, the system shall attempt to refresh the access_token before marking the integration as disconnected.

**Validates: Requirements 15.7**

### Property 38: Retry Limit Enforcement

For any installation session, after 3 failed retry attempts, further retry attempts shall be rejected and the system shall suggest contacting support.

**Validates: Requirements 15.5**

### Property 39: Template Parser Round-Trip

For any valid automation template JSON, parsing it to a Workflow object, then serializing back to JSON, then parsing again shall produce an equivalent template structure.

**Validates: Requirements 16.6**

### Property 40: Parser Error Messages

For any invalid automation template JSON (missing required fields or invalid structure), the parser shall return descriptive error messages indicating which validation rules failed.

**Validates: Requirements 16.7**

### Property 41: Pagination Consistency

For any integration type listing with pagination, each page shall contain at most 20 items, and the union of all pages shall equal the complete result set with no duplicates or omissions.

**Validates: Requirements 17.3**

### Property 42: OAuth State Validation

For any OAuth callback, the state parameter shall match the oauth_state stored in the corresponding InstallationSession, otherwise the callback shall be rejected to prevent CSRF attacks.

**Validates: Requirements 18.4**

### Property 43: Rate Limiting

For any user, attempting to install more than 10 integration types within a 1-hour window shall be rejected with a rate limit error.

**Validates: Requirements 18.7**



## Error Handling

### Error Categories

#### 1. Validation Errors

**Scenarios:**
- Invalid type identifier format (not kebab-case)
- Icon file too large or wrong format
- Missing required fields in templates
- Workflow with no steps
- Integration type references in workflows not installed

**Handling:**
- Return HTTP 400 Bad Request
- Include specific validation error messages
- Log validation failures for monitoring
- Do not create partial records

#### 2. Authentication/Authorization Errors

**Scenarios:**
- Missing or invalid JWT token
- User attempting to access another user's integrations
- Non-admin attempting to create integration types
- Twin modification without permission_flag

**Handling:**
- Return HTTP 401 Unauthorized for authentication failures
- Return HTTP 403 Forbidden for authorization failures
- Log security-related failures
- Never expose sensitive information in error messages

#### 3. OAuth Errors

**Scenarios:**
- User cancels OAuth authorization
- OAuth provider returns error
- Token exchange fails
- Invalid OAuth state (CSRF attempt)
- Token refresh fails

**Handling:**
- Update InstallationSession status to "failed"
- Store error_message for user display
- Allow retry up to 3 attempts
- Log OAuth errors with provider response
- Validate state parameter before processing callback

#### 4. Data Integrity Errors

**Scenarios:**
- Attempting to delete integration type with installations
- Attempting to uninstall integration with dependent workflows
- Duplicate installation attempt
- Migration data loss

**Handling:**
- Return HTTP 409 Conflict
- Provide clear explanation of constraint violation
- Suggest resolution (e.g., disable workflows first)
- Never silently fail or corrupt data

#### 5. Rate Limiting Errors

**Scenarios:**
- User exceeds 10 installations per hour
- Excessive API requests

**Handling:**
- Return HTTP 429 Too Many Requests
- Include Retry-After header
- Log rate limit violations
- Consider temporary account restrictions for abuse



### Error Recovery Strategies

#### Installation Failures

```python
class InstallationRecovery:
    """Strategies for recovering from installation failures."""
    
    @staticmethod
    def handle_oauth_failure(session: InstallationSession, error: str):
        """Handle OAuth authorization failure."""
        session.status = InstallationStatus.FAILED
        session.error_message = error
        session.save()
        
        # Allow retry if under limit
        if session.can_retry:
            return {
                'can_retry': True,
                'retry_url': f'/api/v1/integrations/install/{session.id}/retry'
            }
        else:
            return {
                'can_retry': False,
                'support_reference': str(session.id)
            }
    
    @staticmethod
    def handle_token_exchange_failure(session: InstallationSession, error: str):
        """Handle token exchange failure."""
        # Log detailed error for debugging
        logger.error(
            f"Token exchange failed for session {session.id}: {error}",
            extra={
                'user_id': session.user_id,
                'integration_type_id': session.integration_type_id,
                'retry_count': session.retry_count
            }
        )
        
        # Update session
        session.status = InstallationStatus.FAILED
        session.error_message = "Failed to complete authentication. Please try again."
        session.increment_retry()
        session.save()
```

#### Token Expiry Recovery

```python
class TokenRefreshService:
    """Automatic token refresh on expiry."""
    
    @staticmethod
    async def refresh_if_expired(integration: Integration) -> bool:
        """Attempt to refresh expired token."""
        if not integration.is_token_expired:
            return True
        
        if not integration.has_refresh_token:
            integration.is_active = False
            integration.save()
            return False
        
        try:
            # Attempt refresh
            new_tokens = await oauth_client.refresh_token(
                integration.refresh_token,
                integration.integration_type.oauth_config
            )
            
            # Update tokens
            integration.oauth_token = new_tokens['access_token']
            if 'refresh_token' in new_tokens:
                integration.refresh_token = new_tokens['refresh_token']
            integration.token_expires_at = new_tokens['expires_at']
            integration.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed for integration {integration.id}: {e}")
            integration.is_active = False
            integration.save()
            return False
```

### Error Logging

All errors shall be logged with structured data for debugging and monitoring:

```python
# Example error log structure
{
    'timestamp': '2024-01-15T10:30:00Z',
    'level': 'ERROR',
    'event_type': 'installation_failed',
    'user_id': 'uuid',
    'integration_type_id': 'uuid',
    'session_id': 'uuid',
    'error_type': 'oauth_authorization_failed',
    'error_message': 'User denied authorization',
    'retry_count': 1,
    'can_retry': True
}
```



## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
**Property Tests**: Verify universal properties across all inputs through randomization

Together, these approaches provide complementary coverage—unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide input space.

### Property-Based Testing

#### Library Selection

**Python**: Use `hypothesis` library for property-based testing
- Mature, well-maintained library
- Excellent integration with pytest
- Rich strategy system for generating test data
- Stateful testing support for complex workflows

**Configuration**: Each property test shall run minimum 100 iterations

#### Test Organization

```python
# tests/test_marketplace_properties.py

import pytest
from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

# Property test example
@given(
    type_identifier=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
        min_size=1,
        max_size=50
    )
)
def test_property_1_type_identifier_validation(type_identifier):
    """
    Feature: dynamic-app-marketplace, Property 1: Type Identifier Validation
    
    For any string, if it is used as an integration type identifier,
    then it must match the kebab-case pattern.
    """
    # Test implementation
    pass
```

#### Property Test Tags

Each property test must include a comment tag referencing the design document:

```python
"""
Feature: dynamic-app-marketplace, Property {number}: {property_text}
"""
```

### Unit Testing

#### Test Categories

**1. Model Tests**
- Test model field validation
- Test model methods and properties
- Test model constraints (unique_together, foreign keys)
- Test encryption/decryption methods

**2. Service Tests**
- Test business logic in service classes
- Mock external dependencies (OAuth providers)
- Test error handling and edge cases
- Test transaction rollback on failures

**3. API Tests**
- Test endpoint authentication
- Test request/response serialization
- Test query parameter filtering
- Test pagination
- Test error responses

**4. Migration Tests**
- Test data migration correctness
- Test migration reversibility
- Test data preservation
- Test constraint enforcement after migration

**5. Integration Tests**
- Test complete installation flow
- Test workflow execution with integrations
- Test Twin modification workflow
- Test uninstallation cascade effects



### Test Coverage Requirements

**Minimum Coverage Targets:**
- Models: 95% line coverage
- Services: 90% line coverage
- API Views: 85% line coverage
- Overall: 85% line coverage

**Critical Paths (100% coverage required):**
- Token encryption/decryption
- OAuth state validation
- Permission checking
- Audit logging
- Data migration

### Example Test Implementations

#### Property Test Example

```python
from hypothesis import given, strategies as st
from apps.automation.services import IntegrationTypeService

@given(
    client_secret=st.text(min_size=10, max_size=100)
)
def test_property_6_token_encryption_round_trip(client_secret):
    """
    Feature: dynamic-app-marketplace, Property 6: Token Encryption Round-Trip
    
    For any OAuth token, when it is stored in the database,
    it shall be encrypted, and when retrieved, decryption
    shall produce the original token value.
    """
    # Create integration type with encrypted secret
    integration_type = IntegrationType.objects.create(
        type='test-integration',
        name='Test Integration',
        category='other',
        oauth_config={}
    )
    integration_type.set_oauth_client_secret(client_secret)
    integration_type.save()
    
    # Retrieve and decrypt
    integration_type.refresh_from_db()
    decrypted_secret = integration_type.oauth_client_secret
    
    # Verify round-trip
    assert decrypted_secret == client_secret
```

#### Unit Test Example

```python
import pytest
from apps.automation.models import IntegrationType, Integration
from apps.automation.services import InstallationService

@pytest.mark.django_db
def test_uninstallation_disables_dependent_workflows(user, integration_type):
    """Test that uninstalling an integration disables dependent workflows."""
    # Create installation
    integration = Integration.objects.create(
        user=user,
        integration_type=integration_type,
        is_active=True
    )
    
    # Create workflow that depends on this integration
    workflow = Workflow.objects.create(
        user=user,
        name='Test Workflow',
        is_enabled=True,
        steps=[{
            'action_type': 'send_message',
            'integration_type_id': str(integration_type.id),
            'parameters': {}
        }]
    )
    
    # Uninstall
    InstallationService.uninstall_integration(user, integration.id)
    
    # Verify workflow is disabled
    workflow.refresh_from_db()
    assert workflow.is_enabled is False
```

#### Stateful Property Test Example

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from hypothesis import strategies as st

class InstallationStateMachine(RuleBasedStateMachine):
    """
    Feature: dynamic-app-marketplace, Property 13: Installation State Machine
    
    Test that installation sessions follow valid state transitions.
    """
    
    def __init__(self):
        super().__init__()
        self.sessions = {}
    
    @rule(session_id=st.uuids())
    def start_installation(self, session_id):
        """Start a new installation."""
        session = InstallationSession.objects.create(
            id=session_id,
            user=self.user,
            integration_type=self.integration_type,
            status='downloading',
            progress=0
        )
        self.sessions[session_id] = session
    
    @rule(session_id=st.sampled_from(lambda self: list(self.sessions.keys())))
    def transition_to_oauth(self, session_id):
        """Transition to OAuth setup phase."""
        session = self.sessions[session_id]
        if session.status == 'downloading':
            session.status = 'oauth_setup'
            session.progress = 50
            session.save()
    
    @invariant()
    def valid_status_transitions(self):
        """Verify all sessions have valid status values."""
        for session in self.sessions.values():
            assert session.status in ['downloading', 'oauth_setup', 'completed', 'failed']
    
    @invariant()
    def progress_in_range(self):
        """Verify progress is always 0-100."""
        for session in self.sessions.values():
            assert 0 <= session.progress <= 100

TestInstallationStateMachine = InstallationStateMachine.TestCase
```

### Test Data Management

**Fixtures**: Use pytest fixtures for common test data
**Factories**: Use factory_boy for generating test objects
**Mocking**: Use unittest.mock for external dependencies

```python
# conftest.py

import pytest
from apps.authentication.models import User
from apps.automation.models import IntegrationType

@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def integration_type(db):
    """Create a test integration type."""
    return IntegrationType.objects.create(
        type='test-integration',
        name='Test Integration',
        category='communication',
        description='Test integration for unit tests',
        brief_description='Test integration',
        is_active=True,
        oauth_config={
            'client_id': 'test_client_id',
            'authorization_url': 'https://example.com/oauth/authorize',
            'token_url': 'https://example.com/oauth/token',
            'scopes': ['read', 'write']
        }
    )
```

### Continuous Integration

**Test Execution**: All tests run on every pull request
**Coverage Reporting**: Coverage reports generated and tracked
**Property Test Seeding**: Use fixed seeds for reproducibility in CI
**Performance Testing**: Monitor test execution time

### Manual Testing Checklist

**Installation Flow:**
- [ ] Install integration with valid OAuth
- [ ] Cancel OAuth authorization
- [ ] Retry failed installation
- [ ] Install same integration as different users
- [ ] Verify templates are instantiated

**Marketplace:**
- [ ] Browse all integration types
- [ ] Filter by category
- [ ] Search by name and description
- [ ] View integration details
- [ ] Verify installed badge appears

**Automation Management:**
- [ ] View workflows grouped by integration
- [ ] Enable/disable workflows
- [ ] Edit workflow configuration
- [ ] Create custom workflow
- [ ] Delete custom workflow

**Twin Modifications:**
- [ ] Twin modifies workflow with permission
- [ ] Twin modification rejected without permission
- [ ] High blend requires confirmation
- [ ] Change history is recorded

**Error Scenarios:**
- [ ] Invalid type identifier rejected
- [ ] Icon file too large rejected
- [ ] Uninstall with dependent workflows blocked
- [ ] Rate limit enforced
- [ ] Token refresh on expiry



## Security Considerations

### Authentication and Authorization

**JWT Token Validation:**
- All API endpoints require valid JWT tokens
- Token expiration enforced (default: 1 hour access, 7 days refresh)
- Token blacklisting on logout
- Refresh token rotation on use

**Permission Levels:**
```python
class PermissionLevel:
    USER = 'user'           # Standard user operations
    ADMIN = 'admin'         # Integration type management
    TWIN = 'twin'           # Twin-initiated actions
```

**Authorization Matrix:**
| Operation | User | Admin | Twin |
|-----------|------|-------|------|
| View marketplace | ✓ | ✓ | ✗ |
| Install integration | ✓ | ✓ | ✗ |
| Create integration type | ✗ | ✓ | ✗ |
| Modify workflow | ✓ | ✓ | ✓* |
| Execute workflow | ✓ | ✓ | ✓* |

*Requires permission_flag=True

### OAuth Security

**State Parameter:**
- Generate cryptographically random state for each OAuth flow
- Store state in InstallationSession
- Validate state on callback to prevent CSRF
- State expires after 10 minutes

**Token Storage:**
- All tokens encrypted with Fernet (AES-128)
- Encryption key stored in environment variable
- Key rotation supported through migration
- Tokens never logged or exposed in API responses

**OAuth Configuration:**
```python
# Example secure OAuth config
{
    'client_id': 'public_client_id',
    'client_secret_encrypted': 'base64_encrypted_secret',
    'authorization_url': 'https://provider.com/oauth/authorize',
    'token_url': 'https://provider.com/oauth/token',
    'scopes': ['read', 'write'],
    'redirect_uri': 'https://neurotwin.com/api/v1/integrations/oauth/callback'
}
```

### Data Protection

**Encryption at Rest:**
- OAuth tokens: Fernet symmetric encryption
- Client secrets: Fernet symmetric encryption
- Database: PostgreSQL encryption (TDE recommended for production)

**Encryption in Transit:**
- All API endpoints: HTTPS only
- OAuth redirects: HTTPS only
- WebSocket connections: WSS only (if implemented)

**Data Isolation:**
- User data strictly scoped by user_id
- Database queries always filter by user
- No cross-user data leakage
- Integration tokens isolated per user

### Audit Logging

**Security Events Logged:**
- Authentication failures
- Authorization failures
- Integration installations/uninstallations
- Twin-initiated actions
- Permission changes
- OAuth failures
- Rate limit violations

**Log Structure:**
```python
{
    'timestamp': 'ISO8601',
    'event_type': 'security_event',
    'severity': 'INFO|WARNING|ERROR|CRITICAL',
    'user_id': 'uuid',
    'ip_address': 'x.x.x.x',
    'user_agent': 'string',
    'action': 'action_name',
    'resource': 'resource_identifier',
    'result': 'success|failure',
    'details': {}
}
```

### Rate Limiting

**Limits by Endpoint:**
- Installation: 10 per hour per user
- API requests: 1000 per hour per user
- OAuth callbacks: 5 per minute per session
- Admin operations: 100 per hour per admin

**Implementation:**
```python
from django.core.cache import cache
from rest_framework.throttling import UserRateThrottle

class InstallationRateThrottle(UserRateThrottle):
    rate = '10/hour'
    scope = 'installation'
    
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f'throttle_installation_{request.user.id}'
        return None
```

### Input Validation

**Validation Rules:**
- Type identifier: Regex `^[a-z0-9]+(-[a-z0-9]+)*$`
- URLs: Must be HTTPS with valid domain
- File uploads: Whitelist extensions, size limits
- JSON fields: Schema validation
- User input: Sanitize for XSS prevention

**DRF Serializer Example:**
```python
class IntegrationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationType
        fields = ['id', 'type', 'name', 'icon', 'description', 'category']
    
    def validate_type(self, value):
        """Validate kebab-case format."""
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', value):
            raise serializers.ValidationError(
                'Type must be in kebab-case format'
            )
        return value
    
    def validate_icon(self, value):
        """Validate icon file."""
        if value.size > 500 * 1024:  # 500KB
            raise serializers.ValidationError(
                'Icon file must be 500KB or less'
            )
        if not value.name.endswith(('.svg', '.png')):
            raise serializers.ValidationError(
                'Icon must be SVG or PNG format'
            )
        return value
```



## Performance Optimizations

### Database Optimization

**Indexing Strategy:**
```python
# IntegrationType indexes
- (is_active, category)  # Marketplace filtering
- (is_active, created_at)  # Sorting
- type (unique)  # Lookups

# Integration indexes
- (user, integration_type)  # User's installations
- (user, is_active)  # Active integrations
- (integration_type, is_active)  # Type usage stats
- token_expires_at  # Token refresh queries

# Workflow indexes
- (user, is_enabled)  # Active workflows
- (user, created_at)  # Sorting
- automation_template  # Template tracking

# InstallationSession indexes
- (user, status)  # Progress queries
- created_at  # Cleanup queries
- oauth_state (unique)  # Callback validation
```

**Query Optimization:**
```python
# Bad: N+1 query problem
integration_types = IntegrationType.objects.filter(is_active=True)
for it in integration_types:
    templates = it.automation_templates.all()  # N queries

# Good: Prefetch related
integration_types = IntegrationType.objects.filter(
    is_active=True
).prefetch_related('automation_templates')

# Good: Select related for foreign keys
integrations = Integration.objects.filter(
    user=user
).select_related('integration_type')
```

**Pagination:**
```python
from rest_framework.pagination import PageNumberPagination

class MarketplacePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
```

### Caching Strategy

**Cache Layers:**

1. **Integration Type Listings** (5 minutes)
```python
from django.core.cache import cache

def get_active_integration_types():
    cache_key = 'marketplace:active_types'
    cached = cache.get(cache_key)
    
    if cached is None:
        cached = list(IntegrationType.objects.filter(
            is_active=True
        ).values())
        cache.set(cache_key, cached, 300)  # 5 minutes
    
    return cached
```

2. **User Installation Status** (1 minute)
```python
def get_user_installed_types(user_id):
    cache_key = f'user:{user_id}:installed_types'
    cached = cache.get(cache_key)
    
    if cached is None:
        cached = set(Integration.objects.filter(
            user_id=user_id,
            is_active=True
        ).values_list('integration_type_id', flat=True))
        cache.set(cache_key, cached, 60)  # 1 minute
    
    return cached
```

3. **OAuth Configuration** (10 minutes)
```python
def get_oauth_config(integration_type_id):
    cache_key = f'oauth_config:{integration_type_id}'
    cached = cache.get(cache_key)
    
    if cached is None:
        it = IntegrationType.objects.get(id=integration_type_id)
        cached = it.oauth_config
        cache.set(cache_key, cached, 600)  # 10 minutes
    
    return cached
```

**Cache Invalidation:**
```python
# Invalidate on integration type changes
@receiver(post_save, sender=IntegrationType)
def invalidate_integration_type_cache(sender, instance, **kwargs):
    cache.delete('marketplace:active_types')
    cache.delete(f'oauth_config:{instance.id}')

# Invalidate on user installation changes
@receiver(post_save, sender=Integration)
@receiver(post_delete, sender=Integration)
def invalidate_user_installation_cache(sender, instance, **kwargs):
    cache.delete(f'user:{instance.user_id}:installed_types')
```

### Async Processing

**OAuth Token Exchange:**
```python
from asgiref.sync import sync_to_async
import httpx

async def exchange_oauth_code(
    code: str,
    oauth_config: dict
) -> dict:
    """Exchange authorization code for tokens asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            oauth_config['token_url'],
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': oauth_config['client_id'],
                'client_secret': oauth_config['client_secret'],
                'redirect_uri': oauth_config['redirect_uri']
            }
        )
        response.raise_for_status()
        return response.json()
```

**Template Instantiation:**
```python
from celery import shared_task

@shared_task
def instantiate_templates_async(user_id: str, integration_id: str):
    """Create workflow instances from templates in background."""
    user = User.objects.get(id=user_id)
    integration = Integration.objects.get(id=integration_id)
    
    templates = integration.integration_type.automation_templates.filter(
        is_active=True
    )
    
    workflows = []
    for template in templates:
        workflow = Workflow.objects.create(
            user=user,
            automation_template=template,
            name=template.name,
            description=template.description,
            trigger_config=template.trigger_config,
            steps=template.steps,
            is_enabled=template.is_enabled_by_default,
            is_custom=False
        )
        workflows.append(workflow)
    
    return len(workflows)
```

### Frontend Optimization

**Debounced Search:**
```typescript
import { debounce } from 'lodash';

const debouncedSearch = debounce((searchTerm: string) => {
  fetchIntegrationTypes({ search: searchTerm });
}, 300);
```

**Optimistic Updates:**
```typescript
const handleInstall = async (integrationTypeId: string) => {
  // Optimistically update UI
  setIntegrationTypes(prev => 
    prev.map(it => 
      it.id === integrationTypeId 
        ? { ...it, isInstalled: true } 
        : it
    )
  );
  
  try {
    await api.installIntegration(integrationTypeId);
  } catch (error) {
    // Revert on error
    setIntegrationTypes(prev => 
      prev.map(it => 
        it.id === integrationTypeId 
          ? { ...it, isInstalled: false } 
          : it
      )
    );
    showError(error.message);
  }
};
```

**Lazy Loading:**
```typescript
// Load integration details only when needed
const AppDetailModal = lazy(() => import('./AppDetailModal'));

// Load automation templates on demand
const loadTemplates = async (integrationTypeId: string) => {
  const response = await api.getIntegrationTypeDetail(integrationTypeId);
  return response.automationTemplates;
};
```

### Monitoring and Metrics

**Key Metrics to Track:**
- API response times (p50, p95, p99)
- Database query times
- Cache hit rates
- OAuth success/failure rates
- Installation completion times
- Workflow execution times
- Error rates by endpoint

**Performance Budgets:**
- Marketplace page load: < 2 seconds
- API response time: < 200ms (p95)
- Installation flow: < 5 seconds (excluding OAuth)
- Database queries: < 50ms (p95)
- Cache hit rate: > 80%



## Implementation Guidance

### Development Phases

#### Phase 1: Foundation (Week 1-2)
1. Create new models (IntegrationType, AutomationTemplate, InstallationSession, WorkflowChangeHistory)
2. Write and test data migrations
3. Update Integration model to use foreign key
4. Create service layer classes
5. Set up encryption utilities

**Deliverables:**
- All models created and migrated
- Unit tests for models (95% coverage)
- Migration tests passing

#### Phase 2: Backend API (Week 3-4)
1. Implement IntegrationTypeService
2. Implement AppMarketplaceService
3. Implement InstallationService
4. Implement AutomationTemplateService
5. Create DRF serializers and viewsets
6. Add authentication and permissions

**Deliverables:**
- All API endpoints functional
- API tests passing (85% coverage)
- Postman/OpenAPI documentation

#### Phase 3: OAuth Integration (Week 5)
1. Implement OAuth state generation
2. Create OAuth callback handler
3. Implement token exchange
4. Add token refresh logic
5. Test with real OAuth providers

**Deliverables:**
- OAuth flow working end-to-end
- Token encryption verified
- Error handling tested

#### Phase 4: Frontend (Week 6-7)
1. Create AppMarketplace page
2. Create AppCard and AppDetailModal components
3. Create InstallationProgress component
4. Create AutomationDashboard page
5. Create WorkflowEditor component
6. Integrate with backend APIs

**Deliverables:**
- All UI components functional
- Frontend tests passing
- User flows tested

#### Phase 5: Twin Integration (Week 8)
1. Implement Twin workflow modification
2. Add cognitive blend checking
3. Create change history tracking
4. Add audit logging
5. Test Twin safety controls

**Deliverables:**
- Twin can modify workflows safely
- Audit logs complete
- Safety tests passing

#### Phase 6: Polish and Deploy (Week 9-10)
1. Performance optimization
2. Security audit
3. Load testing
4. Documentation
5. Deployment to staging
6. User acceptance testing
7. Production deployment

**Deliverables:**
- Performance targets met
- Security review passed
- Documentation complete
- Feature live in production

### File Structure

```
apps/automation/
├── models.py                    # All models
├── services/
│   ├── __init__.py
│   ├── integration_type.py      # IntegrationTypeService
│   ├── marketplace.py           # AppMarketplaceService
│   ├── installation.py          # InstallationService
│   ├── automation_template.py   # AutomationTemplateService
│   └── workflow.py              # WorkflowService (enhanced)
├── serializers/
│   ├── __init__.py
│   ├── integration_type.py
│   ├── integration.py
│   ├── workflow.py
│   └── installation.py
├── views/
│   ├── __init__.py
│   ├── marketplace.py           # Marketplace viewsets
│   ├── installation.py          # Installation viewsets
│   └── automation.py            # Automation viewsets
├── admin.py                     # Django admin config
├── urls.py                      # URL routing
├── migrations/
│   ├── 0001_create_integration_type_model.py
│   ├── 0002_populate_integration_types.py
│   ├── 0003_add_integration_type_fk.py
│   ├── 0004_migrate_integration_data.py
│   └── 0005_switch_to_foreign_key.py
└── tests/
    ├── test_models.py
    ├── test_services.py
    ├── test_api.py
    ├── test_migrations.py
    ├── test_properties.py       # Property-based tests
    └── conftest.py              # Pytest fixtures

neuro-frontend/src/
├── app/
│   └── dashboard/
│       ├── apps/
│       │   └── page.tsx         # App Marketplace
│       └── automation/
│           └── page.tsx         # Automation Dashboard
├── components/
│   ├── marketplace/
│   │   ├── AppCard.tsx
│   │   ├── AppDetailModal.tsx
│   │   └── InstallationProgress.tsx
│   └── automation/
│       ├── WorkflowList.tsx
│       ├── WorkflowEditor.tsx
│       └── WorkflowCard.tsx
├── lib/
│   └── api/
│       ├── marketplace.ts
│       ├── installation.ts
│       └── automation.ts
└── types/
    ├── integration.ts
    └── workflow.ts
```

### Code Style Guidelines

**Service Layer Pattern:**
```python
class IntegrationTypeService:
    """Service for integration type operations."""
    
    @staticmethod
    def create_integration_type(
        type_identifier: str,
        name: str,
        **kwargs
    ) -> IntegrationType:
        """
        Create a new integration type.
        
        Args:
            type_identifier: Unique kebab-case identifier
            name: Display name
            **kwargs: Additional fields
        
        Returns:
            Created IntegrationType instance
        
        Raises:
            ValidationError: If validation fails
        """
        # Validation
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', type_identifier):
            raise ValidationError('Invalid type identifier format')
        
        # Business logic
        integration_type = IntegrationType.objects.create(
            type=type_identifier,
            name=name,
            **kwargs
        )
        
        # Post-creation actions
        cache.delete('marketplace:active_types')
        
        return integration_type
```

**View Layer Pattern:**
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class IntegrationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for integration types (read-only for users)."""
    
    serializer_class = IntegrationTypeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MarketplacePagination
    
    def get_queryset(self):
        """Get active integration types with filtering."""
        queryset = IntegrationType.objects.filter(is_active=True)
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset.prefetch_related('automation_templates')
    
    @action(detail=True, methods=['get'])
    def templates(self, request, pk=None):
        """Get automation templates for an integration type."""
        integration_type = self.get_object()
        templates = integration_type.automation_templates.filter(is_active=True)
        serializer = AutomationTemplateSerializer(templates, many=True)
        return Response(serializer.data)
```

### Environment Variables

Add to `.env`:
```bash
# Token encryption
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# OAuth settings
OAUTH_CALLBACK_BASE_URL=https://neurotwin.com

# Rate limiting
INSTALLATION_RATE_LIMIT=10/hour
API_RATE_LIMIT=1000/hour

# Caching
CACHE_INTEGRATION_TYPES_TTL=300
CACHE_USER_INSTALLATIONS_TTL=60

# Session cleanup
INSTALLATION_SESSION_CLEANUP_HOURS=24
```

### Dependencies to Add

```bash
# Backend
uv add cryptography  # For Fernet encryption
uv add hypothesis  # For property-based testing
uv add celery  # For async tasks
uv add redis  # For caching and Celery broker
uv add httpx  # For async HTTP requests

# Frontend (if not already present)
npm install lodash  # For debounce
npm install @tanstack/react-query  # For data fetching
```

### Common Pitfalls to Avoid

1. **N+1 Queries**: Always use select_related/prefetch_related
2. **Token Exposure**: Never log or return decrypted tokens
3. **State Validation**: Always validate OAuth state parameter
4. **Cache Invalidation**: Invalidate caches on data changes
5. **Permission Checks**: Always check permission_flag for Twin actions
6. **Error Messages**: Don't expose internal details in user-facing errors
7. **Migration Order**: Follow the 5-phase migration sequence exactly
8. **Async Context**: Use sync_to_async when calling Django ORM from async code



## Summary

The Dynamic App Marketplace transforms NeuroTwin's integration system from a rigid, code-dependent architecture into a flexible, runtime-extensible platform. This design enables:

**For Administrators:**
- Add new integration types through Django admin without code deployments
- Configure OAuth settings and automation templates per integration
- Monitor installation success rates and usage metrics

**For Users:**
- Discover and install integrations through an intuitive marketplace
- Receive pre-configured automation workflows upon installation
- Manage workflows with granular permission controls
- Safely allow Twin to modify workflows with audit trails

**For Developers:**
- Clean separation of concerns through service layer
- Comprehensive test coverage with property-based testing
- Secure token handling with encryption
- Scalable architecture with caching and async processing

**Key Technical Achievements:**
- Backward-compatible migration from enum to database model
- Two-phase installation with OAuth integration
- Template-based workflow instantiation
- Twin safety controls with cognitive blend awareness
- Comprehensive audit logging for compliance

**Success Metrics:**
- Installation success rate > 95%
- Marketplace page load < 2 seconds
- API response time < 200ms (p95)
- Zero token exposure incidents
- 100% audit trail coverage for Twin actions

This design provides a solid foundation for NeuroTwin's integration ecosystem to grow dynamically while maintaining security, performance, and user experience standards.

