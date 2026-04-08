# NeuroTwin User Guide

A complete guide for users to register, set up their cognitive twin, and use the platform.

---

## Overview

NeuroTwin creates a digital twin of your mind that can:
- Communicate in your style across platforms (email, chat, calls)
- Learn your decision patterns and preferences
- Automate tasks while mimicking your personality
- Handle phone calls using your cloned voice

---

## Getting Started

### Step 1: Register an Account

```
POST /api/v1/auth/register
```

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": { "user_id": "uuid-here" },
  "message": "Account created. Please check your email for verification link."
}
```

---

### Step 2: Verify Your Email

Click the verification link in your email, or call:

```
POST /api/v1/auth/verify
```

```json
{
  "token": "verification-token-from-email"
}
```

---

### Step 3: Login

```
POST /api/v1/auth/login
```

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid-here",
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

Use the `access_token` in all subsequent requests:
```
Authorization: Bearer eyJ...
```

---

## Setting Up Your Twin

### Step 4: Complete the Onboarding Questionnaire

The questionnaire captures your communication style, decision patterns, and preferences to create your Cognitive Signature Model (CSM).

```
POST /api/v1/csm/questionnaire
```

```json
{
  "communication_style": {
    "formality": 0.3,
    "warmth": 0.8,
    "directness": 0.6,
    "openness": 0.7,
    "extraversion": 0.5,
    "preferred_greeting": "Hey",
    "sign_off_style": "Cheers"
  },
  "decision_patterns": {
    "risk_tolerance": 0.4,
    "speed_vs_accuracy": 0.6,
    "collaboration_preference": 0.7,
    "conscientiousness": 0.8
  },
  "preferences": {
    "humor_level": 0.5,
    "response_length": "moderate",
    "emoji_usage": "minimal",
    "vocabulary_patterns": ["sounds good", "let me check", "awesome"]
  }
}
```

This creates your initial CSM profile (version 1).

---

### Step 5: View Your CSM Profile

```
GET /api/v1/csm/profile
```

**Response:**
```json
{
  "success": true,
  "data": {
    "version": 1,
    "personality": {
      "openness": 0.7,
      "conscientiousness": 0.8,
      "extraversion": 0.5,
      "agreeableness": 0.6,
      "neuroticism": 0.3
    },
    "tone": {
      "formality": 0.3,
      "warmth": 0.8,
      "directness": 0.6,
      "humor_level": 0.5
    },
    "communication": {
      "preferred_greeting": "Hey",
      "sign_off_style": "Cheers",
      "response_length": "moderate",
      "emoji_usage": "minimal"
    }
  }
}
```

---

## Using Your Twin

### Cognitive Blend Slider

Control how much "you" vs "AI logic" your Twin uses:

| Blend | Mode | Behavior |
|-------|------|----------|
| 0-30% | AI Logic | Neutral, professional responses |
| 31-70% | Balanced | Mix of your personality + AI reasoning |
| 71-100% | Personality Heavy | Strong mimicry, requires confirmation |

```
POST /api/v1/twin/chat
```

```json
{
  "message": "Draft a reply to John about the project deadline",
  "blend": 60
}
```

---

### Chat with Your Twin

```
POST /api/v1/twin/chat
```

```json
{
  "message": "What should I say to decline this meeting politely?",
  "context": {
    "platform": "email",
    "recipient": "colleague"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "response": "Hey, thanks for the invite! I'm swamped this week - can we reschedule to next Tuesday? Cheers",
    "blend_used": 60,
    "requires_confirmation": false
  }
}
```

---

## Subscription Tiers

### Check Your Current Tier

```
GET /api/v1/subscription
```

### Available Tiers

| Tier | Price | Features |
|------|-------|----------|
| **FREE** | $0 | Basic chat, Gemini Flash/Cerebras/Mistral models |
| **PRO** | $19/mo | + Cognitive learning, Gemini Pro |
| **TWIN+** | $49/mo | + Voice Twin (voice cloning) |
| **EXECUTIVE** | $99/mo | + Autonomous workflows, Custom models |

### Upgrade Your Subscription

```
POST /api/v1/subscription/upgrade
```

```json
{
  "tier": "pro",
  "payment_method_id": "pm_..."
}
```

---

## Feature Access by Tier

### FREE Tier
- ✅ Basic chat with Twin
- ✅ Light memory (recent conversations)
- ✅ Gemini Flash, Cerebras, Mistral models
- ❌ Cognitive learning
- ❌ Voice Twin
- ❌ Autonomous workflows

### PRO Tier
- ✅ Everything in FREE
- ✅ Full cognitive learning (Twin improves over time)
- ✅ Gemini Pro model
- ✅ Extended memory
- ❌ Voice Twin
- ❌ Autonomous workflows

### TWIN+ Tier
- ✅ Everything in PRO
- ✅ Voice Twin (clone your voice)
- ✅ Handle phone calls as you
- ❌ Autonomous workflows

### EXECUTIVE Tier
- ✅ Everything in TWIN+
- ✅ Autonomous workflows (email, calendar, tasks)
- ✅ Custom model fine-tuning
- ✅ Priority support

---

## Voice Twin (TWIN+ and above)

### Set Up Voice Cloning

```
POST /api/v1/voice/setup
```

Upload voice samples (minimum 30 seconds of clear speech).

### Enable Voice Calls

```
POST /api/v1/voice/enable
```

```json
{
  "phone_number": "+1234567890",
  "approval_confirmed": true
}
```

⚠️ Voice cloning requires explicit approval per session.

---

## Autonomous Workflows (EXECUTIVE only)

### Create an Automation

```
POST /api/v1/automation/workflows
```

```json
{
  "name": "Auto-reply to meeting requests",
  "trigger": {
    "type": "email_received",
    "filter": "subject contains 'meeting'"
  },
  "action": {
    "type": "draft_reply",
    "template": "Check calendar and suggest times"
  },
  "requires_approval": true
}
```

### Safety Controls

All automations have:
- ✅ Kill-switch (disable instantly)
- ✅ Approval required for external actions
- ✅ Full audit logs
- ❌ No financial/legal actions without explicit approval

---

## Memory & Learning

### View Your Twin's Memory

```
GET /api/v1/memory
```

### Add a Memory

```
POST /api/v1/memory
```

```json
{
  "content": "I prefer morning meetings before 10am",
  "category": "preferences"
}
```

### Memory is Used For:
- Personalizing responses
- Remembering your preferences
- Learning your communication patterns
- Improving over time (PRO+ only)

---

## Account Management

### Refresh Your Token

```
POST /api/v1/auth/refresh
```

```json
{
  "refresh_token": "eyJ..."
}
```

### Logout

```
POST /api/v1/auth/logout
```

```json
{
  "refresh_token": "eyJ..."
}
```

### Logout from All Devices

```
POST /api/v1/auth/logout-all
```

### Reset Password

```
POST /api/v1/auth/password-reset
```

```json
{
  "email": "user@example.com"
}
```

---

## Safety & Privacy

### Your Data
- All cognitive data is encrypted
- You own your data
- Export or delete anytime

### Twin Boundaries
- Twin drafts content, you approve before sending
- Voice calls require per-session approval
- No financial/legal actions without explicit consent
- Full audit trail of all Twin actions

### Kill Switch
Instantly disable all Twin automations:

```
POST /api/v1/safety/kill-switch
```

---

## Quick Reference

| Action | Endpoint | Auth Required |
|--------|----------|---------------|
| Register | `POST /api/v1/auth/register` | No |
| Login | `POST /api/v1/auth/login` | No |
| Get Profile | `GET /api/v1/csm/profile` | Yes |
| Chat with Twin | `POST /api/v1/twin/chat` | Yes |
| Check Subscription | `GET /api/v1/subscription` | Yes |
| Upgrade | `POST /api/v1/subscription/upgrade` | Yes |
| View Memory | `GET /api/v1/memory` | Yes |
| Kill Switch | `POST /api/v1/safety/kill-switch` | Yes |
