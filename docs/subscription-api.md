# NeuroTwin Subscription API Documentation

## Overview

The Subscription Service manages user subscription tiers, feature access control, and tier transitions for the NeuroTwin platform. It implements a tiered access model where features are progressively unlocked based on subscription level.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Subscription Service                        │
├─────────────────────────────────────────────────────────────────┤
│  SubscriptionService (services.py)                              │
│  ├── get_subscription()      → Get/create user subscription     │
│  ├── get_tier_features()     → Get features for a tier          │
│  ├── upgrade()               → Upgrade subscription tier        │
│  ├── downgrade()             → Downgrade subscription tier      │
│  ├── check_feature_access()  → Verify feature access            │
│  ├── can_access_model()      → Check AI model access            │
│  └── handle_lapsed_subscription() → Auto-downgrade expired      │
├─────────────────────────────────────────────────────────────────┤
│  Models (models.py)                                             │
│  ├── Subscription            → User subscription record         │
│  ├── SubscriptionTier        → Tier enum (FREE/PRO/TWIN+/EXEC)  │
│  └── SubscriptionHistory     → Audit trail for tier changes     │
├─────────────────────────────────────────────────────────────────┤
│  Data Classes (dataclasses.py)                                  │
│  └── TierFeatures            → Feature configuration per tier   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Subscription Tiers

| Tier | Level | Features |
|------|-------|----------|
| **FREE** | 0 | Basic chat, light memory, Gemini-3 Flash, Cerebras, Mistral |
| **PRO** | 1 | + Cognitive learning, Gemini-3 Pro, Autonomous workflows (50/month) |
| **TWIN+** | 2 | + Voice Twin (voice cloning), Autonomous workflows (200/month) |
| **EXECUTIVE** | 3 | + Custom models, Unlimited autonomous workflows |

### Feature Matrix

| Feature | FREE | PRO | TWIN+ | EXECUTIVE |
|---------|:----:|:---:|:-----:|:---------:|
| gemini-3-flash | ✅ | ✅ | ✅ | ✅ |
| cerebras | ✅ | ✅ | ✅ | ✅ |
| mistral | ✅ | ✅ | ✅ | ✅ |
| gemini-3-pro | ❌ | ✅ | ✅ | ✅ |
| cognitive_learning | ❌ | ✅ | ✅ | ✅ |
| voice_twin | ❌ | ❌ | ✅ | ✅ |
| autonomous_workflows | ❌ | ✅ (50/mo) | ✅ (200/mo) | ✅ (unlimited) |
| custom_models | ❌ | ❌ | ❌ | ✅ |

---

## User API Flow Roadmap

### 1. New User Registration Flow

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Signs  │────▶│  get_subscription() │────▶│  FREE Tier Auto  │
│     Up       │     │  (auto-creates)     │     │    Created       │
└──────────────┘     └─────────────────────┘     └──────────────────┘
```

**Code Example:**
```python
from apps.subscription.services import SubscriptionService

service = SubscriptionService()

# First call auto-creates FREE subscription
subscription = service.get_subscription(user_id="user_123")
# Returns: Subscription(tier='free', is_active=True)
```

---

### 2. Feature Access Check Flow

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Tries  │────▶│ check_feature_access│────▶│  Access Granted  │
│  Feature     │     │    (user, feature)  │     │   or Denied      │
└──────────────┘     └─────────────────────┘     └──────────────────┘
                              │
                              ▼
                     ┌─────────────────────┐
                     │  Check if Lapsed    │
                     │  (auto-downgrade)   │
                     └─────────────────────┘
```

**Code Example:**
```python
# Check if user can use voice twin
can_use_voice = service.check_feature_access("user_123", "voice_twin")
# FREE user: False
# TWIN+ user: True

# Check AI model access
can_use_gemini_pro = service.can_access_model("user_123", "gemini-3-pro")
# FREE user: False
# PRO+ user: True
```

---

### 3. Subscription Upgrade Flow

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Pays   │────▶│     upgrade()       │────▶│  New Tier Active │
│  for Tier    │     │ (user, new_tier)    │     │   Immediately    │
└──────────────┘     └─────────────────────┘     └──────────────────┘
                              │
                              ▼
                     ┌─────────────────────┐
                     │  History Recorded   │
                     │  (audit trail)      │
                     └─────────────────────┘
```

**Code Example:**
```python
from datetime import datetime, timedelta
from django.utils import timezone

# Upgrade from FREE to PRO (1 year subscription)
expires = timezone.now() + timedelta(days=365)

subscription = service.upgrade(
    user_id="user_123",
    new_tier="pro",
    expires_at=expires
)
# Features unlocked immediately
# History entry created: FREE -> PRO (upgrade)
```

---

### 4. Subscription Downgrade Flow

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Cancels│────▶│    downgrade()      │────▶│  Lower Tier Set  │
│  or Requests │     │ (user, new_tier)    │     │  Data Preserved  │
└──────────────┘     └─────────────────────┘     └──────────────────┘
                              │
                              ▼
                     ┌─────────────────────┐
                     │  Premium Features   │
                     │     Disabled        │
                     └─────────────────────┘
```

**Code Example:**
```python
# Manual downgrade from EXECUTIVE to PRO
subscription = service.downgrade(
    user_id="user_123",
    new_tier="pro",
    reason="downgrade"
)
# User loses: autonomous_workflows, custom_models
# User keeps: cognitive_learning, voice_twin, all data
```

---

### 5. Lapsed Subscription Flow (Automatic)

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ Subscription │────▶│check_and_handle_    │────▶│  Auto-Downgrade  │
│   Expires    │     │    lapsed()         │     │    to FREE       │
└──────────────┘     └─────────────────────┘     └──────────────────┘
                              │
                              ▼
                     ┌─────────────────────┐
                     │  History: "lapsed"  │
                     │  Data Preserved     │
                     └─────────────────────┘
```

**Code Example:**
```python
# Called automatically during feature checks or explicitly
subscription = service.check_and_handle_lapsed("user_123")

# If subscription.expires_at < now:
#   - Tier changes to FREE
#   - History entry: PRO -> FREE (lapsed)
#   - All user data preserved
```

---

## Complete User Journey Example

```python
from apps.subscription.services import SubscriptionService
from django.utils import timezone
from datetime import timedelta

service = SubscriptionService()
user_id = "user_abc123"

# ═══════════════════════════════════════════════════════════════
# STEP 1: New user signs up → Auto FREE tier
# ═══════════════════════════════════════════════════════════════
sub = service.get_subscription(user_id)
print(f"Tier: {sub.tier}")  # "free"

# Check available features
features = service.get_tier_features(sub.tier)
print(f"Models: {features.available_models}")  
# ['gemini-3-flash', 'cerebras', 'mistral']

# ═══════════════════════════════════════════════════════════════
# STEP 2: User tries premium feature → Denied
# ═══════════════════════════════════════════════════════════════
can_learn = service.check_feature_access(user_id, "cognitive_learning")
print(f"Can use cognitive learning: {can_learn}")  # False

# ═══════════════════════════════════════════════════════════════
# STEP 3: User upgrades to PRO
# ═══════════════════════════════════════════════════════════════
expires = timezone.now() + timedelta(days=30)
sub = service.upgrade(user_id, "pro", expires_at=expires)

can_learn = service.check_feature_access(user_id, "cognitive_learning")
print(f"Can use cognitive learning: {can_learn}")  # True

# ═══════════════════════════════════════════════════════════════
# STEP 4: User upgrades to TWIN+
# ═══════════════════════════════════════════════════════════════
sub = service.upgrade(user_id, "twin_plus", expires_at=expires)

can_voice = service.check_feature_access(user_id, "voice_twin")
print(f"Can use voice twin: {can_voice}")  # True

# ═══════════════════════════════════════════════════════════════
# STEP 5: Subscription expires → Auto-downgrade to FREE
# ═══════════════════════════════════════════════════════════════
# (After expiration date passes)
sub = service.check_and_handle_lapsed(user_id)
print(f"Tier after lapse: {sub.tier}")  # "free"

# ═══════════════════════════════════════════════════════════════
# STEP 6: View subscription history
# ═══════════════════════════════════════════════════════════════
history = service.get_subscription_history(user_id)
for entry in history:
    print(f"{entry.from_tier} → {entry.to_tier} ({entry.reason})")
# Output:
# twin_plus → free (lapsed)
# pro → twin_plus (upgrade)
# free → pro (upgrade)
```

---

## API Integration Points

### For REST API Implementation (Future)

| Endpoint | Method | Service Method | Description |
|----------|--------|----------------|-------------|
| `/api/subscription/` | GET | `get_subscription()` | Get current subscription |
| `/api/subscription/features/` | GET | `get_tier_features()` | Get tier features |
| `/api/subscription/upgrade/` | POST | `upgrade()` | Upgrade tier |
| `/api/subscription/downgrade/` | POST | `downgrade()` | Downgrade tier |
| `/api/subscription/check-feature/` | GET | `check_feature_access()` | Check feature access |
| `/api/subscription/history/` | GET | `get_subscription_history()` | Get change history |

### Middleware Integration

```python
# Example: Feature gate middleware
def require_feature(feature_name):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            service = SubscriptionService()
            if not service.check_feature_access(request.user.id, feature_name):
                return JsonResponse(
                    {"error": f"Feature '{feature_name}' requires upgrade"},
                    status=403
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_feature('voice_twin')
def voice_clone_view(request):
    # Only TWIN+ and EXECUTIVE users reach here
    pass
```

---

## Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                        subscriptions                            │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                                   │
│ user_id (FK → auth_user, UNIQUE)                                │
│ tier (VARCHAR: free/pro/twin_plus/executive)                    │
│ started_at (DATETIME)                                           │
│ expires_at (DATETIME, nullable)                                 │
│ is_active (BOOLEAN)                                             │
│ previous_tier (VARCHAR, nullable)                               │
│ tier_changed_at (DATETIME, nullable)                            │
│ created_at (DATETIME)                                           │
│ updated_at (DATETIME)                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    subscription_history                         │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                                   │
│ subscription_id (FK → subscriptions)                            │
│ from_tier (VARCHAR)                                             │
│ to_tier (VARCHAR)                                               │
│ changed_at (DATETIME)                                           │
│ reason (VARCHAR: upgrade/downgrade/lapsed/manual)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

1. **Auto-creation**: First `get_subscription()` call creates FREE tier automatically
2. **Immediate activation**: Upgrades unlock features instantly
3. **Data preservation**: Downgrades never delete user data
4. **Audit trail**: All tier changes logged in `SubscriptionHistory`
5. **Lapse handling**: Expired premium subscriptions auto-downgrade to FREE
6. **Atomic transactions**: Tier changes are wrapped in database transactions


---

## CSM (Cognitive Signature Model) Creation

The CSM is the core personality profile that defines how the Twin mimics the user. It's created during onboarding and evolves over time.

### CSM Data Structure

```
CSMProfileData
├── personality (PersonalityTraits)
│   ├── openness (0.0-1.0)
│   ├── conscientiousness (0.0-1.0)
│   ├── extraversion (0.0-1.0)
│   ├── agreeableness (0.0-1.0)
│   └── neuroticism (0.0-1.0)
├── tone (TonePreferences)
│   ├── formality (0.0-1.0)
│   ├── warmth (0.0-1.0)
│   ├── directness (0.0-1.0)
│   └── humor_level (0.0-1.0)
├── communication (CommunicationHabits)
│   ├── preferred_greeting
│   ├── sign_off_style
│   ├── response_length (brief/moderate/detailed)
│   └── emoji_usage (none/minimal/moderate/frequent)
├── decision_style (DecisionStyle)
│   ├── risk_tolerance (0.0-1.0)
│   ├── speed_vs_accuracy (0.0-1.0)
│   └── collaboration_preference (0.0-1.0)
├── vocabulary_patterns (List[str])
└── custom_rules (Dict[str, str])
```

---

### CSM Creation Flow

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Completes  │────▶│ create_from_        │────▶│  CSMProfile v1   │
│  Questionnaire   │     │ questionnaire()     │     │    Created       │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │  Extract Traits:    │
                         │  - Personality      │
                         │  - Tone             │
                         │  - Communication    │
                         │  - Decision Style   │
                         │  - Vocabulary       │
                         └─────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │  CSMChangeLog       │
                         │  (audit: "create")  │
                         └─────────────────────┘
```

**Code Example:**
```python
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse

csm_service = CSMService()

# User completes onboarding questionnaire
questionnaire = QuestionnaireResponse(
    communication_style={
        'openness': 0.7,
        'extraversion': 0.6,
        'agreeableness': 0.8,
        'formality': 0.4,
        'warmth': 0.7,
        'directness': 0.6,
        'preferred_greeting': 'Hey',
        'sign_off_style': 'Cheers',
    },
    decision_patterns={
        'conscientiousness': 0.7,
        'risk_tolerance': 0.4,
        'speed_vs_accuracy': 0.6,
        'collaboration_preference': 0.7,
    },
    preferences={
        'neuroticism': 0.3,
        'humor_level': 0.5,
        'response_length': 'moderate',
        'emoji_usage': 'minimal',
        'vocabulary_patterns': ['awesome', 'sounds good', 'let me check'],
    }
)

# Create initial CSM profile
profile = csm_service.create_from_questionnaire(
    user_id="user_123",
    responses=questionnaire
)
# Returns: CSMProfile(version=1, is_current=True)
```

---

### CSM Update Flow (Versioned)

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Updates    │────▶│   update_profile()  │────▶│  New Version     │
│  Preferences     │     │  (user, updates)    │     │    Created       │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │  Previous Version   │
                         │  is_current=False   │
                         └─────────────────────┘
```

**Code Example:**
```python
# Update tone preferences
updated_profile = csm_service.update_profile(
    user_id="user_123",
    updates={
        'tone': {
            'formality': 0.7,  # More formal now
            'humor_level': 0.2,  # Less humor
        }
    }
)
# Creates: CSMProfile(version=2, is_current=True)
# Previous: CSMProfile(version=1, is_current=False)
```

---

### CSM Rollback Flow

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  User Requests   │────▶│ rollback_to_version │────▶│  New Version     │
│  Rollback to v1  │     │   (user, version)   │     │  (copy of v1)    │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │  CSMChangeLog       │
                         │  (audit: "rollback")│
                         └─────────────────────┘
```

**Code Example:**
```python
# Rollback to version 1
restored = csm_service.rollback_to_version(
    user_id="user_123",
    version=1
)
# Creates: CSMProfile(version=3, is_current=True) with v1's data
# History: v2 -> v3 (rollback to v1)
```

---

### Cognitive Blend Application

The Blend slider (0-100%) controls how much personality the Twin uses:

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Twin Generates  │────▶│    apply_blend()    │────▶│  Blended Profile │
│    Response      │     │  (profile, blend)   │     │   for Response   │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
```

| Blend Range | Mode | Personality Weight | Confirmation Required |
|-------------|------|-------------------|----------------------|
| 0-30% | `ai_logic` | 0.0 - 0.3 | No |
| 31-70% | `balanced` | 0.31 - 0.7 | No |
| 71-100% | `personality_heavy` | 0.71 - 1.0 | Yes |

**Code Example:**
```python
# Get current profile
profile = csm_service.get_profile("user_123")

# Apply 60% blend (balanced mode)
blended = csm_service.apply_blend(profile, blend=60)

# Result:
# {
#     'mode': 'balanced',
#     'blend_value': 60,
#     'personality_weight': 0.6,
#     'requires_confirmation': False,
#     'personality': {
#         'openness': 0.62,  # Blended toward user's 0.7
#         'extraversion': 0.56,  # Blended toward user's 0.6
#         ...
#     },
#     'tone': {...},
#     'communication': {...},
#     ...
# }

# Apply 85% blend (requires confirmation)
blended_heavy = csm_service.apply_blend(profile, blend=85)
# blended_heavy['requires_confirmation'] == True
```

---

### Complete User + CSM Journey

```python
from apps.subscription.services import SubscriptionService
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse

sub_service = SubscriptionService()
csm_service = CSMService()
user_id = "user_abc123"

# ═══════════════════════════════════════════════════════════════
# STEP 1: User signs up → FREE subscription created
# ═══════════════════════════════════════════════════════════════
subscription = sub_service.get_subscription(user_id)

# ═══════════════════════════════════════════════════════════════
# STEP 2: User completes onboarding questionnaire → CSM created
# ═══════════════════════════════════════════════════════════════
questionnaire = QuestionnaireResponse(
    communication_style={'formality': 0.3, 'warmth': 0.8},
    decision_patterns={'risk_tolerance': 0.5},
    preferences={'emoji_usage': 'moderate'}
)
csm = csm_service.create_from_questionnaire(user_id, questionnaire)

# ═══════════════════════════════════════════════════════════════
# STEP 3: User upgrades to PRO → Cognitive learning unlocked
# ═══════════════════════════════════════════════════════════════
subscription = sub_service.upgrade(user_id, "pro", expires_at=...)

# Check feature access
can_learn = sub_service.check_feature_access(user_id, "cognitive_learning")
# True - PRO tier has cognitive learning

# ═══════════════════════════════════════════════════════════════
# STEP 4: Twin generates response using CSM + Blend
# ═══════════════════════════════════════════════════════════════
profile = csm_service.get_profile(user_id)
blended = csm_service.apply_blend(profile, blend=50)

# Use blended profile for LLM prompt construction
# - personality traits influence response style
# - tone preferences shape language
# - communication habits define format

# ═══════════════════════════════════════════════════════════════
# STEP 5: CSM evolves over time (versioned updates)
# ═══════════════════════════════════════════════════════════════
csm_service.update_profile(user_id, {'tone': {'formality': 0.5}})

# ═══════════════════════════════════════════════════════════════
# STEP 6: User can rollback if Twin behavior changes unexpectedly
# ═══════════════════════════════════════════════════════════════
history = csm_service.get_version_history(user_id)
csm_service.rollback_to_version(user_id, version=1)
```

---

### CSM Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                        csm_profiles                             │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                                   │
│ user_id (FK → auth_user)                                        │
│ version (INT) ─────────────────┐                                │
│ profile_data (JSONB)           │ UNIQUE(user_id, version)       │
│ is_current (BOOLEAN, indexed)  │                                │
│ created_at (DATETIME)          │                                │
│ updated_at (DATETIME)          │                                │
└────────────────────────────────┴────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      csm_change_logs                            │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                                   │
│ profile_id (FK → csm_profiles)                                  │
│ from_version (INT, nullable)                                    │
│ to_version (INT)                                                │
│ change_type (VARCHAR: create/update/rollback)                   │
│ change_summary (JSONB)                                          │
│ changed_at (DATETIME)                                           │
└─────────────────────────────────────────────────────────────────┘
```
