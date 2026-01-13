---
inclusion: fileMatch
fileMatchPattern: ['**/voice/**', '**/telephony/**', '**/calls/**']
---

# Voice Twin Rules

Guidelines for implementing voice cloning, telephony, and call handling features.

## Voice Cloning

- Require explicit user approval before any voice cloning operation
- Store voice clone consent with timestamp and session ID
- Voice clone approval is per-session; do not persist across sessions
- Use ElevenLabs API via adapter pattern (no direct SDK calls in business logic)

## Call Recording

- All calls MUST be recorded for audit compliance
- Store recordings with: call_id, timestamp, duration, participants, consent_status
- Recordings must be retrievable for audit within 24 hours
- Implement async upload to avoid blocking call flow

## Kill-Switch Requirements

- Emergency kill-switch must terminate all active calls immediately
- Kill-switch must be accessible from any authenticated endpoint
- Log all kill-switch activations with: timestamp, triggered_by, affected_calls
- Kill-switch must work even if primary services are degraded

## Cognitive Blend Integration

- Fetch current Blend value before generating voice responses
- At Blend > 80%: require confirmation before placing calls
- Log Blend value used for each call in audit trail
- Voice personality matching must scale proportionally to Blend percentage

## Impersonation Safeguards

- Twin may NOT place calls as user without `permission_flag=True`
- Disclose Twin identity at call start when required by jurisdiction
- Never override user-defined voice boundaries
- Distinguish Twin-initiated calls from user-initiated in all logs
