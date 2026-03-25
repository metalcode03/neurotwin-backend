# Core Module Architecture - Complete Explanation

## Overview

The `core/` directory contains **shared infrastructure and utilities** used across all NeuroTwin apps. Think of it as the foundation that all other modules build upon.

```
core/
├── ai/          # AI model interaction (Gemini, embeddings, blend logic)
├── api/         # REST API infrastructure (views, permissions, exceptions)
├── db/          # Database utilities (transactions, atomic operations)
└── tasks/       # Background task queue (async operations)
```

---

## 1. Core AI (`core/ai/`)

### Purpose
Centralized AI model interaction for the entire platform. Handles:
- Response generation with personality matching
- Cognitive blend application
- Feature extraction for learning
- Embedding generation for memory

### Key Components

#### `AIService` (`services.py`)
The main AI service that all apps use for AI operations.

**Key Methods:**
```python
# Apply cognitive blend to CSM profile
blended_profile = ai_service.apply_blend(csm_profile_data, blend=75)

# Generate response with personality
response = ai_service.generate_response(
    prompt="What's my schedule today?",
    csm_profile_data=profile_data,
    cognitive_blend=75,
    context_memories=[...],
)

# Extract learning features from actions
features = ai_service.extract_features(action_data)

# Generate embeddings for memory
embeddings = await ai_service.generate_embeddings("User prefers morning meetings")
```

**Why It's in Core:**
- Every app needs AI capabilities (Twin, Memory, Learning, Voice)
- Ensures consistent AI behavior across the platform
- Centralizes API key management and model configuration

#### `BlendMode` (`dataclasses.py`)
Enum defining the three cognitive blend modes:
- `AI_LOGIC` (0-30%): Pure AI logic, minimal personality
- `BALANCED` (31-70%): Blend of personality + AI reasoning
- `PERSONALITY_HEAVY` (71-100%): Heavy personality mimicry, requires confirmation

**Usage Example:**
```python
mode = BlendMode.from_blend_value(85)  # PERSONALITY_HEAVY
if mode.requires_confirmation():
    # Ask user before taking action
    pass
```

#### `AIModel` (`dataclasses.py`)
Enum of available AI models:
- `GEMINI_FLASH`: Free tier, fast responses
- `GEMINI_PRO`: Paid tier, better quality
- `QWEN`, `MISTRAL`: Alternative models

**Usage Example:**
```python
# Check if user's subscription allows this model
if model in AIModel.paid_tier_models():
    # Verify subscription tier
    pass
```

### Real-World Flow

```
User asks Twin a question
         ↓
Twin app calls AIService.generate_response()
         ↓
AIService applies cognitive blend to CSM profile
         ↓
AIService builds system prompt with personality instructions
         ↓
AIService calls Google GenAI API
         ↓
Response returned with blend metadata
         ↓
Twin app logs the interaction
         ↓
Memory app stores the conversation
```

---

## 2. Core API (`core/api/`)

### Purpose
Provides REST API infrastructure used by all endpoint views.

### Key Components

#### `BaseAPIView` (`views.py`)
Base class for all API views with consistent response formatting.

**Standard Response Format:**
```json
{
  "success": true,
  "data": {...},
  "message": "Optional message"
}
```

**Error Response Format:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {...}
  }
}
```

**Usage Example:**
```python
class MyView(BaseAPIView):
    def get(self, request):
        data = {"result": "success"}
        return self.success_response(data=data)
    
    def post(self, request):
        if error:
            return self.error_response(
                message="Invalid data",
                code="VALIDATION_ERROR",
                status_code=400
            )
```

**Why It's in Core:**
- Ensures consistent API responses across all endpoints
- Reduces code duplication
- Makes frontend integration easier (predictable format)

#### Permission Classes (`permissions.py`)

**`IsVerifiedUser`**
- Requires email verification
- Used on most protected endpoints

**`HasTwin`**
- Requires user to have created a Twin
- Used on Twin-specific features

**`HasVoiceTwinAccess`**
- Requires Twin+ or Executive subscription
- Used on voice features

**`HasFeatureAccess`**
- Base class for feature-based permissions
- Checks subscription tier for feature availability

**Usage Example:**
```python
class VoiceCallView(BaseAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasVoiceTwinAccess]
    
    def post(self, request):
        # Only users with Voice Twin access can reach here
        pass
```

#### Exception Handling (`exceptions.py`)

**Custom Exceptions:**
- `BusinessLogicError`: For business rule violations
- `ResourceConflictError`: For duplicate entries (409)
- `FeatureNotAvailableError`: For subscription tier restrictions
- `KillSwitchActiveError`: When kill switch is active
- `PermissionRequiredError`: When explicit permission needed

**Usage Example:**
```python
from core.api.exceptions import KillSwitchActiveError

if kill_switch_active:
    raise KillSwitchActiveError("All automations are halted")
```

**Why It's in Core:**
- Consistent error handling across all apps
- Proper HTTP status codes
- Frontend-friendly error messages

---

## 3. Core Tasks (`core/tasks/`)

### Purpose
Background task queue for async operations. Prevents blocking HTTP requests.

### Key Components

#### Task Queue (`queue.py`)

**`enqueue_task()`**
Generic function to enqueue any task for background execution.

```python
from core.tasks.queue import enqueue_task, TaskPriority

# Enqueue a task
task_id = enqueue_task(
    my_function,
    arg1, arg2,
    priority=TaskPriority.HIGH,
    timeout=300,
    retry=3,
    kwarg1=value1
)
```

**Specialized Enqueue Functions:**

```python
# Memory write (async to avoid blocking)
enqueue_memory_write(
    user_id="123",
    content="User prefers morning meetings",
    source="conversation",
    metadata={"topic": "scheduling"}
)

# Embedding generation (async, can be slow)
enqueue_embedding_generation(
    user_id="123",
    content="Long text to embed...",
    memory_id="mem-456"
)

# Email sending (async, external API)
enqueue_email(
    to_email="user@example.com",
    subject="Welcome to NeuroTwin",
    body="...",
    template="welcome_email.html"
)

# Learning profile update (async, complex computation)
enqueue_learning_update(
    user_id="123",
    features=extracted_features
)
```

**Task Priorities:**
- `CRITICAL`: Immediate execution (kill switch, security)
- `HIGH`: Important but not critical (user-facing actions)
- `NORMAL`: Standard operations (memory writes, emails)
- `LOW`: Background maintenance (cleanup, analytics)

#### Task Handlers (`handlers.py`)

The actual implementations that run in the background.

**`handle_memory_write()`**
```python
# Called by the queue worker
def handle_memory_write(user_id, content, source, metadata):
    engine = VectorMemoryEngine()
    memory = await engine.store_memory(...)
    return {'success': True, 'memory_id': memory.id}
```

**`handle_embedding_generation()`**
```python
# Generates embeddings without blocking HTTP request
def handle_embedding_generation(user_id, content, memory_id):
    ai_service = AIService()
    embeddings = ai_service.generate_embeddings_sync(content)
    # Update memory record
    return {'success': True, 'embedding_size': len(embeddings)}
```

**`handle_learning_update()`**
```python
# Updates CSM profile based on extracted features
def handle_learning_update(user_id, features):
    service = LearningService()
    result = await service.update_profile(user_id, features)
    return {'success': result.success, 'new_version': result.new_version}
```

#### Task Decorators (`decorators.py`)

**`@async_task`**
Decorator to automatically enqueue a function for background execution.

```python
from core.tasks.decorators import async_task, TaskPriority

@async_task(priority=TaskPriority.HIGH)
def send_notification(user_id: str, message: str):
    # This runs in the background
    notification_service.send(user_id, message)

# Calling it enqueues the task
task_id = send_notification(user_id="123", message="Hello")
```

**`@background_task`**
Attempts async execution but falls back to sync if queue unavailable.

```python
from core.tasks.decorators import background_task

@background_task(run_sync_if_unavailable=True)
def process_data(data: dict):
    # Runs async if possible, sync otherwise
    # Good for development/testing
    pass
```

### Why Tasks Are in Core

**Problem Without Async Tasks:**
```python
# BAD: Blocks HTTP request for 2+ seconds
def create_memory_view(request):
    content = request.data['content']
    
    # Generate embedding (slow, 1-2 seconds)
    embeddings = generate_embeddings(content)
    
    # Store in vector DB (slow, network call)
    vector_db.store(embeddings)
    
    # User waits 2+ seconds for response
    return Response({"status": "created"})
```

**Solution With Async Tasks:**
```python
# GOOD: Returns immediately
def create_memory_view(request):
    content = request.data['content']
    
    # Enqueue for background processing
    enqueue_memory_write(
        user_id=request.user.id,
        content=content,
        source="conversation"
    )
    
    # User gets immediate response
    return Response({"status": "processing"})
```

**Operations That MUST Be Async:**
1. **Memory writes** - Embedding generation is slow
2. **Email sending** - External API calls
3. **Learning updates** - Complex CSM calculations
4. **Integration token refresh** - External OAuth calls
5. **Webhook processing** - Can be slow/unreliable

---

## 4. Core DB (`core/db/`)

### Purpose
Database transaction utilities to ensure data integrity.

### Key Components

#### `@atomic_operation` Decorator

Wraps functions in database transactions - all succeed or all rollback.

```python
from core.db.transactions import atomic_operation

@atomic_operation()
def create_user_with_twin(user_data, twin_data):
    # Both operations succeed or both rollback
    user = User.objects.create(**user_data)
    twin = Twin.objects.create(user=user, **twin_data)
    return user
```

**With Retry Logic:**
```python
@atomic_operation(max_retries=3, retry_on=(DatabaseError,))
def update_with_retry(data):
    # Retries up to 3 times on database errors
    # Useful for handling transient connection issues
    pass
```

#### `ensure_atomic` Context Manager

For explicit transaction blocks.

```python
from core.db.transactions import ensure_atomic

with ensure_atomic():
    user = User.objects.create(email='test@example.com')
    Profile.objects.create(user=user)
    # Both operations are atomic
```

#### `TransactionManager` Class

For complex multi-step transactions with rollback support.

```python
from core.db.transactions import TransactionManager

manager = TransactionManager()

with manager.begin():
    # Add steps
    manager.add_step('create_user', lambda: User.objects.create(...))
    manager.add_step('create_profile', lambda: Profile.objects.create(...))
    manager.add_step('send_email', lambda: send_welcome_email(...))
    
    # Execute all steps atomically
    results = manager.execute_all()
    
    # Access results
    user = manager.get_result('create_user')
```

### Why Transactions Are Critical

**Without Transactions (BAD):**
```python
def create_twin_with_profile(user_id, data):
    # Create twin
    twin = Twin.objects.create(user_id=user_id, **data)
    
    # Create CSM profile
    csm = CSMProfile.objects.create(user_id=user_id, ...)
    
    # If this fails, twin exists but CSM doesn't!
    # Database is now in inconsistent state
    memory = MemoryRecord.objects.create(...)
```

**With Transactions (GOOD):**
```python
@atomic_operation()
def create_twin_with_profile(user_id, data):
    twin = Twin.objects.create(user_id=user_id, **data)
    csm = CSMProfile.objects.create(user_id=user_id, ...)
    memory = MemoryRecord.objects.create(...)
    
    # If ANY operation fails, ALL are rolled back
    # Database stays consistent
```

---

## How Core Modules Work Together

### Example: User Sends Message to Twin

```
1. Request arrives at Twin API endpoint
   ↓
2. BaseAPIView validates authentication (core/api)
   ↓
3. Permission check: IsVerifiedUser, HasTwin (core/api)
   ↓
4. Twin service calls AIService.generate_response() (core/ai)
   ↓
5. AIService applies cognitive blend (core/ai)
   ↓
6. Response generated with personality matching (core/ai)
   ↓
7. Enqueue memory write for async processing (core/tasks)
   ↓
8. Return response immediately (core/api)
   ↓
9. Background: handle_memory_write() runs (core/tasks)
   ↓
10. Background: Generate embeddings (core/ai)
    ↓
11. Background: Store in vector DB (atomic transaction, core/db)
    ↓
12. Background: Enqueue learning update (core/tasks)
    ↓
13. Background: Update CSM profile (atomic transaction, core/db)
```

### Example: Memory Creation Flow

```
Frontend: POST /api/v1/csm/memories
         ↓
MemoryCreateView (apps/memory/views.py)
         ↓
Validates with MemoryCreateSerializer
         ↓
Calls enqueue_memory_write() (core/tasks/queue.py)
         ↓
Returns 201 Created immediately
         ↓
[Background Worker Picks Up Task]
         ↓
handle_memory_write() (core/tasks/handlers.py)
         ↓
VectorMemoryEngine.store_memory()
         ↓
AIService.generate_embeddings() (core/ai/services.py)
         ↓
@atomic_operation ensures consistency (core/db/transactions.py)
         ↓
Store in PostgreSQL + Vector DB
         ↓
Log access in MemoryAccessLog
```

---

## Core Module Benefits

### 1. Code Reuse
- AI logic written once, used everywhere
- API response format consistent across all endpoints
- Transaction handling standardized

### 2. Consistency
- All apps use same AI service → consistent behavior
- All apps use same error format → easier frontend integration
- All apps use same async pattern → predictable performance

### 3. Maintainability
- Update AI model in one place → affects entire platform
- Fix transaction bug once → all apps benefit
- Change error format once → all endpoints updated

### 4. Performance
- Async tasks prevent blocking HTTP requests
- Transactions ensure data integrity without sacrificing speed
- Centralized AI service can implement caching

### 5. Security
- Permission classes enforce access control consistently
- Transaction rollback prevents partial data corruption
- Error handling prevents information leakage

---

## When to Use Each Core Module

### Use `core/ai` When:
- Generating AI responses
- Applying cognitive blend
- Extracting learning features
- Generating embeddings
- Any AI model interaction

### Use `core/api` When:
- Creating new API endpoints (inherit from BaseAPIView)
- Adding permission checks
- Handling errors consistently
- Formatting API responses

### Use `core/tasks` When:
- Operation takes > 500ms
- External API calls (email, webhooks, OAuth)
- Embedding generation
- Memory writes
- Learning profile updates
- Any operation that shouldn't block HTTP requests

### Use `core/db` When:
- Multiple database operations must succeed together
- Creating related records (user + profile + twin)
- Updating multiple tables atomically
- Need rollback capability
- Ensuring data consistency

---

## Configuration

### Environment Variables

```env
# AI Service
GOOGLE_API_KEY=your-api-key
GEMINI_API_KEY=your-api-key  # Alternative
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768

# Task Queue (Django-Q2)
Q_CLUSTER = {
    'name': 'neurotwin',
    'workers': 4,
    'timeout': 300,
    'retry': 3,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
}

# Database
DATABASE_URL=postgresql://...
```

### Django Settings

```python
# settings.py

INSTALLED_APPS = [
    # ...
    'django_q',  # Task queue
    'core',
    'core.ai',
    'core.api',
    'core.tasks',
    'core.db',
]

# Exception handler
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'core.api.exceptions.custom_exception_handler',
}
```

---

## Summary

**Core is the foundation:**
- `core/ai` → AI model interaction
- `core/api` → REST API infrastructure
- `core/tasks` → Background job queue
- `core/db` → Transaction management

**Every app depends on core:**
- Twin app uses AI service for responses
- Memory app uses task queue for async writes
- CSM app uses transactions for atomic updates
- All apps use BaseAPIView for consistent APIs

**Core ensures:**
- ✅ Consistent behavior across platform
- ✅ Code reuse and maintainability
- ✅ Performance (async operations)
- ✅ Data integrity (transactions)
- ✅ Security (permissions, error handling)
