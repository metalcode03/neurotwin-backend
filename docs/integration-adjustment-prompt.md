Refactor the integration system to support multiple authentication strategies (OAuth, Meta, API Key) and extend IntegrationTypeModel to properly handle platforms like WhatsApp, Instagram, Slack, Google, and future integrations.

## Core Objective
Upgrade the integration architecture to support different authentication flows instead of assuming all integrations use OAuth. Ensure backward compatibility while enabling Meta (WhatsApp/Instagram) onboarding and future extensibility.

---

## 1. Update IntegrationTypeModel

Add a new field:

- `auth_type` (string enum)

Values:
- "oauth" → standard OAuth 2.0 (Google, Slack, etc.)
- "meta" → Meta onboarding (WhatsApp, Instagram)
- "api_key" → API key-based integrations (future)

Default:
- "oauth"

---

## 2. Refactor oauth_config → auth_config

Rename:
- `oauth_config` → `auth_config`

Update structure to be flexible:

Example (OAuth):
```json
{
  "client_id": "...",
  "client_secret_encrypted": "...",
  "authorization_url": "...",
  "token_url": "...",
  "scopes": [...]
}
````

Example (Meta):

```json
{
  "app_id": "...",
  "app_secret_encrypted": "...",
  "redirect_uri": "https://yourapp.com/integrations/meta/callback/",
  "scopes": [
    "whatsapp_business_management",
    "whatsapp_business_messaging"
  ]
}
```

Example (API Key):

```json
{
  "api_key_label": "User API Key",
  "instructions": "Paste your API key from provider dashboard"
}
```

Ensure:

* Encryption still applies to secrets
* Backward compatibility migration for existing oauth_config

---

## 3. Add Auth Strategy Layer

Create a new service abstraction:

### AuthStrategy (base class)

Methods:

* `generate_auth_url()`
* `handle_callback(request)`
* `exchange_token()`
* `validate()`

---

### Implement:

#### OAuthStrategy

* Existing OAuth logic (Google, Slack)
* Uses authorization_url + token_url

#### MetaStrategy

* Handles Meta onboarding flow
* Generates Meta OAuth URL
* Handles callback at `/integrations/meta/callback/`
* Exchanges code for access token via Meta Graph API
* Fetches:

  * business_id
  * phone_number_id
* Stores data in Integration model

#### APIKeyStrategy

* Accepts user-provided API key
* Validates format (optional)
* Stores encrypted key

---

## 4. Update Installation Flow

Refactor InstallationService:

Replace:

```python
OAuthClient
```

With:

```python
AuthStrategyFactory.get_strategy(integration_type.auth_type)
```

---

### Installation Flow Changes

If `auth_type == "oauth"`:

* Use existing OAuth redirect + callback

If `auth_type == "meta"`:

* Generate Meta onboarding URL
* Redirect user
* Handle callback via `/integrations/meta/callback/`

If `auth_type == "api_key"`:

* Skip redirect
* Accept API key input from frontend

---

## 5. Add Meta Callback Endpoint

Create new endpoint:

* `GET /integrations/meta/callback/`

Responsibilities:

* Validate `state` (InstallationSession)
* Extract `code`
* Exchange code for access token (Meta Graph API)
* Fetch account info
* Create Integration instance
* Store:

  * access_token
  * meta_business_id
  * meta_phone_number_id
* Mark InstallationSession as completed

---

## 6. Extend Integration Model

Add fields:

* `meta_business_id` (nullable)
* `meta_phone_number_id` (nullable)
* `meta_waba_id` (nullable)
* `api_key_encrypted` (nullable)

Ensure:

* Proper encryption/decryption methods
* Backward compatibility

---

## 7. Update OAuthClient → Generalize

Rename:

* `OAuthClient` → `AuthClient` (or remove if redundant)

Move logic into strategies.

---

## 8. Update API Endpoints

Ensure these endpoints support all auth types:

* `POST /integrations/install/`
* `GET /integrations/install/{session_id}/progress/`

Behavior:

* Return correct auth URL depending on auth_type
* Support non-redirect flows (API key)

---

## 9. Frontend Adjustments (Next.js)

### Installation Flow UI

* Detect `auth_type` from IntegrationType

If:

* "oauth" → redirect to OAuth URL
* "meta" → redirect to Meta onboarding
* "api_key" → show input modal

---

### API Key Input UI

* Modal form:

  * Input field
  * Submit to backend

---

### Callback Handling

* Ensure frontend handles redirect back to dashboard
* Poll installation progress as currently implemented

---

## 10. Webhook Preparation (Meta)

Prepare system for:

* `POST /webhooks/meta/`

(No full implementation required now, but scaffold endpoint)

---

## 11. Migration Plan

* Migrate `oauth_config` → `auth_config`
* Set existing integrations:

  * auth_type = "oauth"

---

## 12. Deliverables

Generate:

1. Updated Django models
2. Migration scripts
3. AuthStrategy classes
4. Refactored InstallationService
5. Meta callback endpoint
6. Updated API endpoints
7. Frontend integration flow updates
8. Clean modular architecture

---

Focus on:

* Extensibility (future integrations)
* Clean separation of auth logic
* Backward compatibility
* Security (token encryption)

Avoid:

* Hardcoding logic per integration
* Mixing auth flows together

```

---

# 🧠 Why This Is Powerful

This turns your system into:

✅ **Pluggable integration engine**  
✅ Supports **any future platform**  
✅ Clean separation (very important at scale)  
✅ Matches how real platforms (Zapier, n8n) are built  

---

# 🚀 What You’ve Just Built (Big Picture)

You now have:

- App Marketplace ✅  
- Installation Engine ✅  
- Workflow Automation ✅  
- AI Brain System ✅  

👉 You’re basically building a **next-gen AI-powered Zapier + Personal OS**

---

If you want next:

We can design:
- 🔌 **Integration SDK (so others build plugins for you)**
- 🧠 **AI decides which integration to trigger (autonomous mode)**
- 💰 **Monetization for marketplace integrations**

Just say 👍
```
